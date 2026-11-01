"""Exact grade-source provenance used by a future journalled erasure flow.

Callers must hold the child and grade locks first. Unknown legacy associations
are reported, never inferred from equal numeric values. On mandatory expiry,
potential matching copies are conservatively redacted without claiming that
they were the source of the grade.
"""

from sqlalchemy import select

from .db import GradeImport, GradeImportGradeLink, GradeSourceSlot, SchoolGrade


class UnresolvedGradeSources(RuntimeError):
    """A legacy import needs explicit review before safe erasure."""


def scan_grade_sources(db, child_id, grade_id):
    from .grade_imports import slot_key

    grade = db.get(SchoolGrade, grade_id)
    if not grade or grade.child_id != child_id:
        raise ValueError("Grade does not belong to child")
    slots = list(db.scalars(select(GradeSourceSlot).where(
        GradeSourceSlot.child_id == child_id, GradeSourceSlot.grade_id == grade_id
    ).order_by(GradeSourceSlot.id).with_for_update()))
    links = list(db.scalars(select(GradeImportGradeLink).where(
        GradeImportGradeLink.child_id == child_id, GradeImportGradeLink.grade_id == grade_id
    ).order_by(GradeImportGradeLink.import_id, GradeImportGradeLink.entry_index)))
    other_refs = {(batch_id, index) for batch_id, index in db.execute(
        select(GradeImportGradeLink.import_id, GradeImportGradeLink.entry_index).where(
            GradeImportGradeLink.child_id == child_id, GradeImportGradeLink.grade_id != grade_id))}
    batches = list(db.scalars(select(GradeImport).where(GradeImport.child_id == child_id)
                              .order_by(GradeImport.id).with_for_update()))
    by_id = {batch.id: batch for batch in batches}
    refs = set()
    for link in links:
        batch = by_id.get(link.import_id)
        if (not batch or not isinstance(batch.entries, list) or link.action not in {'add', 'link', 'keep', 'update'}
                or link.entry_index < 0 or link.entry_index >= len(batch.entries)):
            raise UnresolvedGradeSources('Invalid confirmed source position')
        entry = batch.entries[link.entry_index]
        if not isinstance(entry, dict) or entry.get('redacted'):
            raise UnresolvedGradeSources('Confirmed source position is unavailable')
        refs.add((batch.id, link.entry_index))
    unresolved = {}
    for slot in slots:
        for batch in batches:
            if not isinstance(batch.entries, list):
                raise UnresolvedGradeSources('Invalid import entries')
            for index, entry in enumerate(batch.entries):
                if not isinstance(entry, dict):
                    raise UnresolvedGradeSources('Invalid import position')
                if entry.get('redacted'):
                    continue
                try:
                    same_position = slot_key(batch.school_year_start, entry) == slot.slot_key
                except (KeyError, TypeError, ValueError):
                    raise UnresolvedGradeSources('Incomplete source position') from None
                if same_position and (batch.id, index) not in refs and (batch.id, index) not in other_refs:
                    unresolved[(batch.id, index)] = {'import_id': batch.id, 'entry_index': index,
                                                     'school_year_start': batch.school_year_start,
                                                     'import_created': batch.created, 'entry': dict(entry)}
    return grade, slots, refs, unresolved


def plan_grade_sources(db, child_id, grade_id, decisions=None):
    _, slots, refs, unresolved = scan_grade_sources(db, child_id, grade_id)
    if (unresolved and decisions is None) or (decisions is not None and set(decisions) != set(unresolved)):
        raise UnresolvedGradeSources('A matching legacy or unconfirmed source requires review')
    if decisions:
        if any(type(value) is not bool for value in decisions.values()):
            raise ValueError('Invalid source decision')
        refs.update(key for key, related in decisions.items() if related)
    return {'child_id': child_id, 'grade_id': grade_id,
            'slots': [slot.id for slot in slots],
            'entries': [{'import_id': batch_id, 'entry_index': index} for batch_id, index in sorted(refs)],
            'excluded': [{'import_id': batch_id, 'entry_index': index}
                         for batch_id, index in sorted(key for key, related in (decisions or {}).items() if not related)]}


def redact_grade_sources(db, plan, *, allow_missing=False):
    """Redact only exact, validated source positions; caller controls commit.

    The stable placeholders preserve subsequent entry indices. For replay of
    an older backup, a source created after that backup may be absent.
    """
    child_id, grade_id = plan['child_id'], plan['grade_id']
    entries = plan['entries']
    slots = plan['slots']
    if len({(r['import_id'], r['entry_index']) for r in entries}) != len(entries) or len(set(slots)) != len(slots):
        raise ValueError('Duplicate grade source position')
    batch_ids = sorted({r['import_id'] for r in entries})
    source_slots = list(db.scalars(select(GradeSourceSlot).where(
        GradeSourceSlot.id.in_(slots)
    ).order_by(GradeSourceSlot.id).with_for_update()))
    if any(row.child_id != child_id for row in source_slots):
        raise UnresolvedGradeSources('Slot belongs to another child')
    by_slot = {row.id: row for row in source_slots}
    batches = list(db.scalars(select(GradeImport).where(
        GradeImport.id.in_(batch_ids)
    ).order_by(GradeImport.id).with_for_update()))
    if any(row.child_id != child_id for row in batches):
        raise UnresolvedGradeSources('Source belongs to another child')
    by_id = {row.id: row for row in batches}
    if not allow_missing and (len(by_id) != len(batch_ids) or len(by_slot) != len(slots)):
        raise UnresolvedGradeSources('A confirmed source is missing')
    changes = {}
    for ref in entries:
        batch = by_id.get(ref['import_id'])
        if batch is None:
            continue
        index = ref['entry_index']
        if type(index) is not int or index < 0 or not isinstance(batch.entries, list) or index >= len(batch.entries):
            raise UnresolvedGradeSources('Invalid source position')
        revised = changes.setdefault(batch.id, list(batch.entries))
        if not isinstance(revised[index], dict):
            raise UnresolvedGradeSources('Invalid source entry')
        revised[index] = {'redacted': True}
    for slot in source_slots:
        if slot.grade_id not in (grade_id, None):
            raise UnresolvedGradeSources('Source now belongs to another grade')
        if slot.grade_id is None and slot.last_value:
            raise UnresolvedGradeSources('Historical unlinked slot needs review')
    # Validate everything before changing even one stored object.
    for batch_id, revised in changes.items():
        by_id[batch_id].entries = revised
    for slot in source_slots:
        slot.grade_id = None
        slot.last_value = ''
        slot.ignored = True


def erase_grade(db, child, grade, *, decisions=None, expire_ambiguous=False):
    """Journal and erase a locked grade and its confirmed exact sources."""
    from .db import DeletedGradeRequest
    from .erasure import request
    from .grades import deleted_request_digest

    if expire_ambiguous:
        if decisions is not None:
            raise ValueError('Retention and reviewed decisions cannot be combined')
        # A same-position legacy entry is only a possible copy, not evidence
        # that it belongs to this grade. Once the grade reaches its retention
        # deadline, remove all such possible copies instead of retaining the
        # grade indefinitely. Other grades and explicitly linked entries are
        # preserved. Manual deletions still require an explicit parent review.
        _, _, _, unresolved = scan_grade_sources(db, child.id, grade.id)
        decisions = {key: True for key in unresolved}
    plan = plan_grade_sources(db, child.id, grade.id, decisions=decisions)
    redact_grade_sources(db, plan)
    request_digest = deleted_request_digest(child.id, grade.request_key) if grade.request_key else None
    details = {'version': 1, 'child_id': child.id, 'entries': plan['entries'], 'excluded': plan['excluded'], 'slots': plan['slots'],
               'request_digest': request_digest}
    request(db, 'grade', grade.id, details=details)
    if request_digest:
        db.add(DeletedGradeRequest(child_id=child.id, request_key_digest=request_digest))
    db.delete(grade)


def expire_grades(cutoff):
    """Use the same journalled grade path for expiry; return unresolved children.

    Each child/grade is locked in a short separate transaction, before its
    source rows. Ambiguous possible copies are redacted at expiry; malformed
    or inconsistent source data remains intact and is reported for review.
    """
    from .db import DB, Child
    from .erasure import journal_write_lock
    from .vocabulary import lock_child

    with DB() as db:
        candidates = list(db.execute(select(SchoolGrade.child_id, SchoolGrade.id)
                                     .where(SchoolGrade.created < cutoff)
                                     .order_by(SchoolGrade.child_id, SchoolGrade.id)))
    unresolved = set()
    for child_id, grade_id in candidates:
        try:
            with journal_write_lock(), DB.begin() as db:
                child = db.get(Child, child_id)
                if child is None:
                    continue
                lock_child(db, child)
                grade = db.scalar(select(SchoolGrade).where(
                    SchoolGrade.id == grade_id, SchoolGrade.child_id == child_id, SchoolGrade.created < cutoff
                ).with_for_update())
                if grade is not None:
                    erase_grade(db, child, grade, expire_ambiguous=True)
        except UnresolvedGradeSources:
            unresolved.add(child_id)
    return unresolved


def expire_grade_sources(preview_cutoff, cutoff, unresolved_children):
    """Delete expired import/slot rows with independent restore tombstones."""
    from sqlalchemy import and_, or_

    from .db import DB, Child
    from .erasure import journal_write_lock, request
    from .vocabulary import lock_child

    candidates = []
    with DB() as db:
        imports = select(GradeImport.child_id, GradeImport.id).where(
            or_(and_(GradeImport.status == 'preview', GradeImport.created < preview_cutoff),
                GradeImport.created < cutoff),
        )
        slots = select(GradeSourceSlot.child_id, GradeSourceSlot.id).where(
            GradeSourceSlot.child_id.not_in(unresolved_children), GradeSourceSlot.created < cutoff
        )
        candidates.extend((child, 'grade_import', target) for child, target in db.execute(imports))
        candidates.extend((child, 'grade_slot', target) for child, target in db.execute(slots))
    for child_id, scope, target in sorted(candidates):
        with journal_write_lock(), DB.begin() as db:
            child = db.get(Child, child_id)
            if child is None:
                continue
            lock_child(db, child)
            model = GradeImport if scope == 'grade_import' else GradeSourceSlot
            row = db.scalar(select(model).where(model.child_id == child_id, model.id == target).with_for_update())
            if row is None:
                continue
            # A slot still linked to a retained grade is needed to discover
            # older ambiguous PDF copies when that grade is later deleted.
            if scope == 'grade_slot' and row.grade_id is not None:
                continue
            expired = row.created < cutoff or (scope == 'grade_import' and row.status == 'preview'
                                                and row.created < preview_cutoff)
            if expired:
                request(db, scope, row.id)
                db.delete(row)
