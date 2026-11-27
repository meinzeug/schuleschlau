"""Literal source provenance and conservative, non-generative learning filters.

A readable/confirmed transcript is not a factual certificate. Original text is
never rewritten. Only finite exact rational and unit checks make mathematical claims;
unknown notation remains unknown. All helpers are local and do not call AI.
"""

import ast
import copy
import hashlib
import io
import json
import math
import re
from fractions import Fraction
from types import SimpleNamespace

from PIL import Image
from sqlalchemy import func, select

from .db import Job, LearningUnit, UnitSource, Usage
from .source_lineage_models import SourceImageReceipt, SourceInvalidation, SourceRevision
from .subject_content import SourceBlock

POLICY_VERSION = "literal-safety-8"
PREPROCESS_VERSION = "exif-rgb-max3200-jpeg95-1"
AUTO_CONFLICT_SUMMARY = "Abweichender Schüler-/Korrekturbereich bleibt ungeklärt."
AUTO_CONFLICT_LOCAL = "Die beiden Abschriften dieses Schüler-/Korrekturbereichs unterscheiden sich; Original erhalten."
REASONS = {
    "exam_only": "Eine korrigierte Arbeit ist keine allgemeine Lernstoffquelle.",
    "unreadable": "Der Wortlaut ist nicht lesbar.",
    "unconfirmed": "Die Abschrift wurde noch nicht bestätigt.",
    "revision_changed": "Die Quellenfassung wurde geändert.",
    "reading_uncertain": "Mindestens ein Zeichen oder eine Lesestelle ist ungeklärt.",
    "student_work": "Die Schülerrechnung ist noch keine geprüfte fachliche Regel.",
    "visible_annotation": "Eine sichtbare Korrektur, Einfügung oder Streichung muss getrennt geprüft werden.",
    "false_equality": "Diese wörtliche rationale Gleichung ist rechnerisch falsch; sie bleibt im Original erhalten.",
    "ambiguous_numeric": "Die Zahlenschreibweise ist mehrdeutig; die Gleichung bleibt im Original erhalten und muss geprüft werden.",
    "false_divisibility": "Diese wörtliche Teilbarkeitsaussage ist rechnerisch falsch; sie bleibt im Original erhalten.",
    "false_unit_conversion": "Diese wörtliche Einheitenumrechnung ist rechnerisch falsch; sie bleibt im Original erhalten.",
    "false_gcd_lcm": "Diese wörtliche ggT-/kgV-Angabe ist rechnerisch falsch; sie bleibt im Original erhalten.",
    "unstructured_annotations": "Die Abschrift enthält nicht mehr zuordenbare Quellenmarkierungen.",
}

REVIEW_MARKS_AFTER_EDIT = (
    "Nach der Textänderung sind frühere Markierungen nicht mehr sicher zugeordnet. "
    "Deine Eltern können den ursprünglichen Text in der Elternansicht eingeben. "
    "Oder fotografiere die Seite neu und lade sie erneut hoch."
)


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def _number(expression):
    """Bounded rational arithmetic, no eval/names/calls/comparison guessing."""
    expression = expression.strip().replace("−", "-").replace("·", "*").replace("×", "*")
    for old, new in ((r"\cdot", "*"), (r"\times", "*"), (r"\(", ""), (r"\)", ""), (r"\[", ""), (r"\]", "")):
        expression = expression.replace(old, new)
    expression = expression.strip("$").strip()
    expression = re.sub(r"\\(?:d?frac)\{([+-]?\d{1,9})\}\{([+-]?\d{1,9})\}", r"(\1/\2)", expression)
    if not expression or len(expression) > 160 or not re.fullmatch(r"[0-9 .,+*/()\-]+", expression):
        raise ValueError("not bounded arithmetic")
    expression = expression.replace(",", ".")
    tree = ast.parse(expression, mode="eval")
    if len(list(ast.walk(tree))) > 40:
        raise ValueError("too many nodes")

    def value(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            result = Fraction(ast.get_source_segment(expression, node))
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            result = (-1 if isinstance(node.op, ast.USub) else 1) * value(node.operand)
        elif isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            left, right = value(node.left), value(node.right)
            if isinstance(node.op, ast.Add):
                result = left + right
            elif isinstance(node.op, ast.Sub):
                result = left - right
            elif isinstance(node.op, ast.Mult):
                result = left * right
            else:
                result = left / right
        else:
            raise ValueError("unknown expression")
        if max(abs(result.numerator), result.denominator) > 10**18:
            raise ValueError("unbounded result")
        return result

    return value(tree.body)


# Deliberately small arithmetic grammar for equations embedded in prose.  It
# does not interpret words, units, variables, mixed fractions, or parentheses.
# The complete-line parser below retains support for richer bounded notation.
_EMBEDDED_NUMBER = r"\d{1,9}(?:[.,]\d{1,9})?"
_EMBEDDED_EXPR = rf"[+-]?\s*{_EMBEDDED_NUMBER}(?:\s*(?:[+*/·×−-]|\bmal\b)\s*{_EMBEDDED_NUMBER}){{0,20}}"
_EMBEDDED_EQUATION = re.compile(
    rf"(?<![\w./])({_EMBEDDED_EXPR}(?:\s*=\s*{_EMBEDDED_EXPR}){{1,7}})(?![\w/=])",
    flags=re.IGNORECASE,
)


def _embedded_false_equality(line):
    """Check isolated numeric spans only; never parse a fragment of algebra."""
    if '=' not in line or len(line) > 12000:
        return False
    # The bounded input and term count avoid pathological scans; normalization
    # leaves all numeric characters and token order intact.
    line = re.sub(r'\s+', ' ', line)
    for match in _EMBEDDED_EQUATION.finditer(line):
        before, after = line[:match.start()].rstrip(), line[match.end():].lstrip()
        # A candidate after an operator or another equality is only a suffix
        # of a larger expression (e.g. x + 2 = 3). A leading signed value can
        # similarly be the end of x-2. Reject both without guessing x.
        if before and (before[-1] in '+-−*/·×÷^%=([{\\' or
                       (before[-1] == ':' and re.search(r'(?:\d|\))\s*:$', before)) or
                       (match.group(0).lstrip().startswith(('+', '-', '−')) and
                        (before[-1].isalnum() or before[-1] in ')]}'))):
            continue
        # A bare integer immediately before the candidate can be the whole
        # part of a mixed number, not a separate problem.
        if re.search(r'(?<![\w./])\d+\s+$', line[:match.start()]):
            continue
        # Likewise an expression ending immediately before a continued
        # operation, identifier, or unit is not self-contained.
        if after and (after[0] in '+-−*/·×÷:^%=)]}\\' or after[0].isalpha()):
            continue
        expression = re.sub(r'\bmal\b', '*', match.group(1), flags=re.IGNORECASE)
        # A separator followed by three digits can be a thousands separator
        # or a decimal mark; OCR alone cannot choose the intended locale.
        if re.search(r'(?<![\d.,])\d{1,3}[.,]\d{3}(?!\d)', expression):
            continue
        terms = expression.split('=')
        # A*b/c*d is often an OCR-flattened stacked fraction; interpreting
        # operator order as the photographed grouping would be speculation.
        if any('/' in term and term.count('*') + term.count('·') + term.count('×') > 1
               for term in terms):
            continue
        try:
            values = [_number(term) for term in terms]
        except (ValueError, SyntaxError, ZeroDivisionError, OverflowError):
            continue
        if any(left != right for left, right in zip(values, values[1:])):
            return True
    return False


_AMBIGUOUS_SEPARATOR = re.compile(r"(?<![\d.,])[1-9]\d{0,2}[.,]\d{3}(?![\d.,])")


def ambiguous_numeric_equality(text):
    """A fully numeric equation can use a decimal or thousands separator.

    This does not establish either interpretation or transcription accuracy.
    Only syntax the bounded arithmetic parser understands is recognized here;
    unfamiliar notation stays outside this check.
    """
    for line in text.splitlines():
        terms = line.strip().split('=')
        if not 2 <= len(terms) <= 8 or not _AMBIGUOUS_SEPARATOR.search(line):
            continue
        try:
            for term in terms:
                _number(term)
        except (ValueError, SyntaxError, ZeroDivisionError, OverflowError):
            continue
        return True
    return False


def false_equality(text, *, include_embedded=False):
    """Only self-contained numeric equations; never repair or infer variables."""
    for line in text.splitlines():
        terms = line.strip().split("=")
        if 2 <= len(terms) <= 8:
            try:
                values = [_number(term) for term in terms]
            except (ValueError, SyntaxError, ZeroDivisionError, OverflowError):
                pass
            else:
                if any(left != right for left, right in zip(values, values[1:])):
                    return True
        if include_embedded and _embedded_false_equality(line):
            return True
    return False


def false_divisibility(text):
    """Check only complete, literal integer divisibility statements.

    A bare ASCII bar can be a table separator, so only the explicit German
    wording or mathematical divisibility symbols are recognized. Zero as
    divisor and all other notation remain unassessed.
    """
    for line in text.splitlines():
        if len(line) > 80:
            continue
        word = re.fullmatch(r"\s*([0-9]{1,9})\s+teilt\s+([0-9]{1,9})(?:\s+(nicht))?\s*[.!]?\s*", line, re.IGNORECASE)
        symbol = re.fullmatch(r"\s*([0-9]{1,9})\s*([∣∤])\s*([0-9]{1,9})\s*[.!]?\s*", line)
        if word:
            divisor, dividend = int(word[1]), int(word[2])
            says_divides = word[3] is None
        elif symbol:
            divisor, dividend = int(symbol[1]), int(symbol[3])
            says_divides = symbol[2] == "∣"
        else:
            continue
        if divisor and (dividend % divisor == 0) != says_divides:
            return True
    return False


_GCD_LCM = re.compile(
    r"\s*(ggT|kgV)\s*\(\s*([0-9]{1,7})\s*[,;]\s*([0-9]{1,7})\s*\)\s*=\s*([0-9]{1,14})\s*[.!]?\s*",
    re.IGNORECASE,
)


def false_gcd_lcm(text):
    """Recognize complete, explicit positive-integer ggT/kgV equations only.

    Notation with variables, calculations, zero or surrounding explanation is
    unassessed. A positive result quarantines the literal block; it never
    rewrites a pupil's work or proves that its transcription is faithful.
    """
    for line in text.splitlines():
        if len(line) > 160:
            continue
        match = _GCD_LCM.fullmatch(line)
        if not match:
            continue
        operation, first, second, claimed = match.groups()
        first, second, claimed = int(first), int(second), int(claimed)
        if not first or not second:
            continue
        actual = math.gcd(first, second) if operation.casefold() == "ggt" else math.lcm(first, second)
        if actual != claimed:
            return True
    return False


# Restrict conversion checks to complete, independently interpretable lines.
# Unknown symbols, dimensions and ambiguous decimal/thousands notation are
# intentionally not interpreted as evidence for or against the transcription.
_UNIT_VALUES = {
    **{unit: ("time", factor) for factor, units in (
        (1, ("s", "Sekunde", "Sekunden")),
        (60, ("min", "Minute", "Minuten")),
        (3600, ("h", "Stunde", "Stunden")),
    ) for unit in units},
    **{unit: ("length", factor) for factor, units in (
        (1, ("mm", "Millimeter")), (10, ("cm", "Zentimeter")),
        (1000, ("m", "Meter")), (1000000, ("km", "Kilometer")),
    ) for unit in units},
    **{unit: ("mass", factor) for factor, units in (
        (1, ("mg", "Milligramm")), (1000, ("g", "Gramm")),
        (1000000, ("kg", "Kilogramm")), (1000000000, ("t", "Tonne", "Tonnen")),
    ) for unit in units},
    **{unit: ("volume", factor) for factor, units in (
        (1, ("ml", "mL", "Milliliter")), (1000, ("l", "L", "Liter")),
    ) for unit in units},
}
_VULGAR_FRACTIONS = {
    "½": Fraction(1, 2), "¼": Fraction(1, 4), "¾": Fraction(3, 4),
    "⅓": Fraction(1, 3), "⅔": Fraction(2, 3), "⅛": Fraction(1, 8),
    "⅜": Fraction(3, 8), "⅝": Fraction(5, 8), "⅞": Fraction(7, 8),
}
_UNIT_NUMBER = r"(?:[0-9]{1,9}(?:[.,][0-9]{1,2})?|[0-9]{1,9}\s*/\s*[0-9]{1,9}|\\(?:d?frac)\{[0-9]{1,9}\}\{[0-9]{1,9}\}|[½¼¾⅓⅔⅛⅜⅝⅞])"
_UNIT_NAMES = "|".join(map(re.escape, sorted(_UNIT_VALUES, key=len, reverse=True)))
_CONVERSION = re.compile(
    rf"\s*({_UNIT_NUMBER})\s*({_UNIT_NAMES})\s*=\s*({_UNIT_NUMBER})\s*({_UNIT_NAMES})\s*[.!]?\s*"
)


def false_unit_conversion(text):
    """Flag only a complete, unambiguous false same-dimension conversion.

    An unflagged line is not proof of transcription or factual correctness.
    The function never infers source text or changes a pupil's calculation.
    """
    for raw in text.splitlines():
        line = raw.strip()
        if len(line) > 160:
            continue
        if line.startswith(r"\(") and line.endswith(r"\)"):
            line = line[2:-2].strip()
        elif line.startswith("$") and line.endswith("$") and len(line) >= 2:
            line = line[1:-1].strip()
        match = _CONVERSION.fullmatch(line)
        if not match:
            continue
        left, left_unit, right, right_unit = match.groups()
        left_dimension, left_factor = _UNIT_VALUES[left_unit]
        right_dimension, right_factor = _UNIT_VALUES[right_unit]
        if left_dimension != right_dimension:
            continue

        def number(value):
            if value in _VULGAR_FRACTIONS:
                return _VULGAR_FRACTIONS[value]
            latex = re.fullmatch(r"\\(?:d?frac)\{([0-9]{1,9})\}\{([0-9]{1,9})\}", value)
            if latex:
                return Fraction(int(latex[1]), int(latex[2]))
            return Fraction(value.replace(" ", "").replace(",", "."))

        try:
            if number(left) * left_factor != number(right) * right_factor:
                return True
        except (ValueError, ZeroDivisionError):
            continue
    return False


def literal_blocks(material):
    values = material.source_blocks or []
    if not isinstance(values, list) or len(values) > 80:
        return []
    try:
        blocks = [
            SourceBlock.model_validate(value).model_dump(exclude_none=True)
            for value in values
        ]
    except (ValueError, TypeError):
        return []
    return blocks if "\n\n".join(block["text"] for block in blocks) == material.content else []


def blocks_after_text_edit(material, new_text):
    """Keep unchanged literal metadata; quarantine unplaceable markings.

    This deliberately does not infer where a changed correction or student
    answer moved. Old blocks remain only as an internal quarantine marker;
    public material projections already hide blocks that no longer reproduce
    the saved text. Unmarked text continues to be editable normally.
    """
    previous = material.source_blocks if material.source_blocks is not None else []
    if not isinstance(previous, list) or len(previous) > 80:
        return copy.deepcopy(previous), True

    def protected(block):
        if not isinstance(block, dict):
            return True
        try:
            SourceBlock.model_validate(block)
        except (ValueError, TypeError):
            return True
        if block.get("literal_role") in ("student_work", "annotation"):
            return True
        warnings = block.get("reading_uncertainties", [])
        if not isinstance(warnings, list) or any(not isinstance(item, str) or not item.strip() for item in warnings):
            return True
        marks = block.get("annotations", [])
        return not isinstance(marks, list) or any(
            not isinstance(mark, dict) or mark.get("kind") not in ("ink", "highlight") for mark in marks
        )

    sensitive = any(protected(block) or (isinstance(block, dict) and block.get("reading_uncertainties"))
        for block in previous)
    try:
        restored = [SourceBlock.model_validate(value).model_dump(exclude_none=True) for value in previous[:80]]
    except (ValueError, TypeError):
        restored = []
    if restored and "\n\n".join(block["text"] for block in restored) == new_text:
        return restored, False
    old = literal_blocks(material)
    pieces = new_text.split("\n\n")
    if (old and len(old) == len(pieces) and all("\n\n" not in block["text"] for block in old)
            and all(piece.strip() and len(piece) <= 12000 for piece in pieces)):
        if all(old_block["text"] == piece or not protected(old_block) for old_block, piece in zip(old, pieces)):
            return [copy.deepcopy(old_block) if old_block["text"] == piece else {
                "kind": "paragraph", "text": piece, "purpose": "unknown",
                "reading_uncertainties": copy.deepcopy(old_block.get("reading_uncertainties", []))}
                for old_block, piece in zip(old, pieces)], False
    if sensitive:
        return copy.deepcopy(previous), True
    return [], False


def block_data(material):
    result = []
    for index, block in enumerate(literal_blocks(material)):
        block_id = digest([material.id, material.revision, index, block])[:32]
        result.append(
            {
                **block,
                "block_id": block_id,
                "block_index": index,
                "annotations": [
                    {**mark, "annotation_id": digest([block_id, i, mark])[:32]}
                    for i, mark in enumerate(block.get("annotations", []))
                ],
            }
        )
    return result


def _auto_conflict_summary_is_local(db, material, blocks):
    """Recognize only an exactly reproducible automatic merge, never model-supplied warnings."""
    if (db is None or not material.image_digest
            or not any(AUTO_CONFLICT_LOCAL in block.get("reading_uncertainties", []) for block in blocks)):
        return False
    auto = db.scalar(select(SourceRevision).where(
        SourceRevision.material_id == material.id, SourceRevision.child_id == material.child_id,
        SourceRevision.revision == material.revision, SourceRevision.cause == "auto_check",
    ).order_by(SourceRevision.sequence.desc()).limit(1))
    if not auto or auto.snapshot != source_snapshot(material) or not isinstance(auto.receipt, dict):
        return False
    receipt = auto.receipt
    if receipt.get("origin") != "automatic_image_countercheck" or receipt.get("check_status") != "checked":
        return False
    first = db.get(SourceRevision, receipt.get("first_snapshot_id"))
    second = db.get(SourceRevision, receipt.get("second_snapshot_id"))
    if not first or not second:
        return False
    for row, cause in ((first, "extraction"), (second, "auto_check_reading"), (auto, "auto_check")):
        if (not isinstance(row.snapshot, dict) or not isinstance(row.receipt, dict)
                or row.material_id != material.id or row.child_id != material.child_id or row.cause != cause
                or row.digest != digest({"literal": row.snapshot, "receipt": row.receipt})):
            return False
    if (first.revision != material.revision - 1 or second.revision != first.revision
            or first.digest != receipt.get("first_snapshot_digest")
            or first.receipt.get("job_id") != receipt.get("first_job_id")
            or second.receipt.get("job_id") != receipt.get("job_id")
            or any(row.snapshot.get("image_digest") != material.image_digest for row in (first, second))):
        return False
    if any(not isinstance(row.snapshot.get("uncertainties"), list)
           or AUTO_CONFLICT_SUMMARY in row.snapshot["uncertainties"] for row in (first, second)):
        return False
    try:
        from .extraction import validate_material
        from .material_review import _protected_readings
        from .schemas import ExtractionOutput

        raw = {key: second.snapshot[key] for key in ExtractionOutput.model_fields if key in second.snapshot}
        merged = validate_material(_protected_readings(raw, first))
        keys = ("subject", "topic", "content", "source_blocks", "uncertainties", "homework", "legibility")
        return all(merged[key] == auto.snapshot.get(key) for key in keys)
    except (ValueError, TypeError, KeyError, AttributeError):
        return False


def learning_source(db, material, revision=None):
    """Read-only projection: exact eligible block text + explicit exclusions.

    Legacy unmarked text is 'not_assessed', never 'correct'. A missing structured
    reading of a page with warnings cannot silently become learning groundtruth.
    ``db`` is accepted for common callsites; no writes/backfill occur on GET.
    """
    mid, current = material.id, material.revision
    result = {
        "material_id": mid,
        "revision": current,
        "content": "",
        "source_blocks": [],
        "source_refs": [],
        "exclusions": [],
        "factual_status": "not_assessed",
        "policy_version": POLICY_VERSION,
    }
    reason = (
        "exam_only"
        if material.purpose == "exam"
        else "revision_changed"
        if revision is not None and revision != current
        else "unconfirmed"
        if not material.confirmed
        else "unreadable"
        if material.legibility == "unreadable"
        else None
    )
    blocks = literal_blocks(material)
    # OCR also copies each block-local warning to the page list. Only exact
    # copies are known to be scoped; every other page warning could concern
    # any block and must remain conservative until explicit confirmation.
    local_warnings = {warning for block in blocks for warning in block.get("reading_uncertainties", [])}
    warnings = material.uncertainties
    scoped_auto_summary = (
        isinstance(warnings, list) and AUTO_CONFLICT_SUMMARY in warnings
        and _auto_conflict_summary_is_local(db, material, blocks)
    )
    page_warning = not isinstance(warnings, list) or any(
        not isinstance(warning, str) or not warning.strip() or (
            warning not in local_warnings and not (warning == AUTO_CONFLICT_SUMMARY and scoped_auto_summary)
        ) for warning in warnings
    )
    has_reading_warning = page_warning or bool(local_warnings)
    reading_confirmed = False
    if has_reading_warning and db is not None and material.confirmed and getattr(material, "confirmation_digest", None):
        confirmation = db.scalar(select(SourceRevision).where(
            SourceRevision.material_id == material.id, SourceRevision.revision == material.revision,
            SourceRevision.cause == "confirmation").order_by(SourceRevision.sequence.desc()).limit(1))
        reading_confirmed = bool(confirmation and confirmation.snapshot == source_snapshot(material)
            and confirmation.receipt.get("reading_resolution") == "explicit_user_confirmation"
            and confirmation.receipt.get("confirmed_literal_digest") == digest(source_snapshot(material)))
    result["reading_status"] = "explicitly_confirmed" if reading_confirmed else "unresolved" if has_reading_warning else "not_reported"
    saved_blocks = material.source_blocks
    malformed_container = saved_blocks is not None and (
        not isinstance(saved_blocks, list) or len(saved_blocks) > 80)
    if isinstance(saved_blocks, list) and not malformed_container:
        try:
            for block in saved_blocks:
                SourceBlock.model_validate(block)
        except (ValueError, TypeError):
            malformed_container = True
    raw_marks = any(
        not isinstance(block, dict)
        or (
            block.get("annotations")
            or block.get("reading_uncertainties")
            or block.get("literal_role") in ("student_work", "annotation")
        )
        for block in (saved_blocks if isinstance(saved_blocks, list) else [])
    )
    if not blocks and (raw_marks or malformed_container):
        reason = reason or "unstructured_annotations"
    if not blocks and material.content.strip():
        blocks = [
            {
                "kind": "paragraph",
                "text": material.content,
                "literal_role": "unknown",
                "annotations": [],
                "reading_uncertainties": [],
            }
        ]
    for index, block in enumerate(blocks):
        block_id = digest([mid, current, index, block])[:32]
        item = {**block, "block_id": block_id}
        item["annotations"] = [
            {**mark, "annotation_id": digest([block_id, i, mark])[:32]}
            for i, mark in enumerate(block.get("annotations", []))
        ]
        blocked = reason
        if not blocked and not reading_confirmed and (
            block.get("reading_uncertainties")
            or page_warning
        ):
            blocked = "reading_uncertain"
        if not blocked and ambiguous_numeric_equality(block["text"]):
            blocked = "ambiguous_numeric"
        if not blocked and false_equality(block["text"], include_embedded=True):
            blocked = "false_equality"
        if not blocked and false_divisibility(block["text"]):
            blocked = "false_divisibility"
        if not blocked and false_unit_conversion(block["text"]):
            blocked = "false_unit_conversion"
        if not blocked and false_gcd_lcm(block["text"]):
            blocked = "false_gcd_lcm"
        if not blocked and block.get("literal_role") == "student_work":
            blocked = "student_work"
        if not blocked and (
            block.get("literal_role") == "annotation"
            or any(
                mark["kind"] in ("crossout", "insertion", "correction", "comment", "unknown")
                for mark in block.get("annotations", [])
            )
        ):
            blocked = "visible_annotation"
        if blocked:
            result["exclusions"].append({"block_id": block_id, "reason": blocked, "message": REASONS[blocked]})
        else:
            result["source_blocks"].append(item)
            result["source_refs"].append({"material_id": mid, "revision": current, "block_id": block_id})
    result["content"] = "\n\n".join(block["text"] for block in result["source_blocks"])
    if result["exclusions"]:
        result["factual_status"] = "partly_excluded" if result["content"] else "blocked"
    if not blocks and reason:
        result["factual_status"] = "blocked"
        result["exclusions"].append({"block_id": None, "reason": reason, "message": REASONS[reason]})
    return result


def usable_source(db, material, revision=None):
    return bool(material is not None and learning_source(db, material, revision)["content"].strip())


def source_snapshot(material):
    snapshot = {
        key: copy.deepcopy(getattr(material, key))
        for key in (
            "subject",
            "topic",
            "content",
            "source_blocks",
            "uncertainties",
            "homework",
            "legibility",
            "confirmed",
            "purpose",
            "image_digest",
        )
    }
    if getattr(material, "visual_observations", None):
        snapshot["visual_observations"] = copy.deepcopy(material.visual_observations)
    return snapshot


def extraction_receipt(db, job, config, image_bytes, result=None):
    from .extraction import OCR_SYSTEM, TranscriptionOutput
    from .material_review import CHECK_SYSTEM

    prompt = CHECK_SYSTEM if job.payload.get("material_check") else OCR_SYSTEM

    width = height = None
    if image_bytes:
        with Image.open(io.BytesIO(image_bytes)) as image:
            width, height = image.size
    usage = db.scalar(select(Usage).where(Usage.job_id == job.id))
    origin = (
        db.get(SourceImageReceipt, (job.payload or {}).get("material_id"))
        if (job.payload or {}).get("material_id")
        else None
    )
    telemetry = getattr(result, "telemetry", None) or {}
    # Whitelist operational scalars: never arbitrary upstream JSON/reasoning.
    metrics = {
        key: telemetry[key]
        for key in ("upstream", "actual_model", "latency_ms", "reasoning_tokens", "cached_tokens", "attempt")
        if key in telemetry and isinstance(telemetry[key], (str, int, type(None)))
    }
    return {
        "version": 1,
        "job_id": job.id,
        "usage_id": usage.id if usage else None,
        "image_digest": hashlib.sha256(image_bytes).hexdigest() if image_bytes else None,
        "width": width,
        "height": height,
        "coordinate_space": "stored_normalized_image_0_1000",
        "preprocessing_version": origin.normalization_version if origin else "historical_unknown",
        "upload_geometry": origin.geometry if origin else None,
        "client_preprocessing": "not_reported",
        "base_prompt_digest": hashlib.sha256(prompt.encode()).hexdigest(),
        "base_schema_digest": digest(TranscriptionOutput.model_json_schema()),
        "provider": config["provider"],
        "model": config["model"],
        "effective_request": getattr(result, "request_receipt", None) or {"status": "not_reported"},
        "configured_max_output_tokens": config.get("max_output_tokens"),
        "metrics": metrics,
        "factual_validation": "not_assessed",
        "literal_checks": "applied_when_projecting_learning_source",
        "policy_version": POLICY_VERSION,
    }


def save_snapshot(db, material, cause, receipt=None, *, allow_empty=False):
    """Immutable (including unconfirmed retry snapshots); caller owns transaction."""
    if not allow_empty and (not material.content or not material.content.strip()):
        return None
    snapshot = source_snapshot(material)
    latest = db.scalar(
        select(SourceRevision)
        .where(SourceRevision.material_id == material.id, SourceRevision.revision == material.revision)
        .order_by(SourceRevision.sequence.desc())
        .limit(1)
    )
    if receipt is None and latest is not None and latest.snapshot == snapshot:
        return latest
    fingerprint = digest({"literal": snapshot, "receipt": receipt or {"origin": "legacy_or_manual"}})
    existing = db.scalar(
        select(SourceRevision).where(
            SourceRevision.material_id == material.id,
            SourceRevision.revision == material.revision,
            SourceRevision.digest == fingerprint,
        )
    )
    if existing:
        return existing
    row = SourceRevision(
        material_id=material.id,
        child_id=material.child_id,
        revision=material.revision,
        sequence=(
            db.scalar(select(func.max(SourceRevision.sequence)).where(SourceRevision.material_id == material.id)) or 0
        )
        + 1,
        digest=fingerprint,
        cause=cause,
        snapshot=snapshot,
        receipt=copy.deepcopy(receipt) or {"version": 1, "origin": "legacy_or_manual", "factual_validation": "not_assessed"},
    )
    db.add(row)
    db.flush()
    return row


def snapshot_data(row):
    return {
        "id": row.id,
        "material_id": row.material_id,
        "revision": row.revision,
        "sequence": row.sequence,
        "digest": row.digest,
        "cause": row.cause,
        "created": row.created,
        "literal": row.snapshot,
        "receipt": row.receipt,
    }


def invalidate_dependents(db, material, previous_revision):
    """Keep attempts/unit text; add a review receipt rather than deleting work."""
    rows = list(
        db.scalars(
            select(LearningUnit).where(
                LearningUnit.child_id == material.child_id,
                (LearningUnit.material_id == material.id)
                | LearningUnit.id.in_(select(UnitSource.unit_id).where(UnitSource.material_id == material.id)),
            )
        )
    )
    for unit in rows:
        if not db.scalar(
            select(SourceInvalidation.id).where(
                SourceInvalidation.unit_id == unit.id,
                SourceInvalidation.material_id == material.id,
                SourceInvalidation.current_revision == material.revision,
            )
        ):
            ref = db.get(UnitSource, (unit.id, material.id))
            db.add(
                SourceInvalidation(
                    material_id=material.id,
                    child_id=material.child_id,
                    unit_id=unit.id,
                    source_revision=ref.revision if ref else previous_revision,
                    current_revision=material.revision,
                    reason="source_revised",
                )
            )


def unit_source_status(db, unit):
    rows = list(
        db.scalars(
            select(SourceInvalidation).where(
                SourceInvalidation.unit_id == unit.id, SourceInvalidation.child_id == unit.child_id
            )
        )
    )
    return {
        "needs_source_review": bool(rows),
        "changed_sources": [
            {
                "material_id": row.material_id,
                "source_revision": row.source_revision,
                "current_revision": row.current_revision,
                "reason": row.reason,
            }
            for row in rows
        ],
    }


def export_sources(db, child_id):
    from .db import Material

    return {
        "source_image_receipts": [
            {
                "material_id": row.material_id,
                "image_digest": row.image_digest,
                "geometry": row.geometry,
                "normalization_version": row.normalization_version,
                "created": row.created,
            }
            for row in db.scalars(select(SourceImageReceipt).join(Material).where(Material.child_id == child_id))
        ],
        "source_revisions": [
            snapshot_data(row)
            for row in db.scalars(
                select(SourceRevision)
                .where(SourceRevision.child_id == child_id)
                .order_by(SourceRevision.material_id, SourceRevision.sequence)
            )
        ],
        "source_invalidations": [
            {
                key: getattr(row, key)
                for key in ("unit_id", "material_id", "source_revision", "current_revision", "reason", "created")
            }
            for row in db.scalars(select(SourceInvalidation).where(SourceInvalidation.child_id == child_id))
        ],
    }


def crop_snapshot(row):
    return SimpleNamespace(content=row.snapshot["content"], source_blocks=row.snapshot["source_blocks"])


def purge_diagnostic_outputs(db, material_ids, *, unlink_files=True):
    """Call before material deletion; only our bounded private diagnostic files."""
    from .config import settings
    from .source_evaluation import WORK_ID
    from .source_lineage_models import SourceEvaluationCase, SourceEvaluationGrant

    directory = settings.data_dir / "operator-diagnostics" / WORK_ID
    selected = set(material_ids)
    for row in db.scalars(select(SourceEvaluationCase).where(SourceEvaluationCase.material_id.in_(selected))):
        if unlink_files:
            (directory / (row.id + ".json")).unlink(missing_ok=True)
        if row.job_id and (job := db.get(Job, row.job_id)):
            job.payload = {"operator_evaluation": row.id, "diagnostic_only": True, "source_removed": True}
            if job.status == "operator_held":
                job.status = "failed"
                job.error = "Die Diagnosequelle wurde entfernt. Kein automatischer Wiederholungsaufruf."
    for grant in db.scalars(select(SourceEvaluationGrant)):
        remaining = [source for source in grant.sources if source["material_id"] not in selected]
        if remaining != grant.sources:
            if remaining:
                grant.sources = remaining
            else:
                db.delete(grant)


def expire_diagnostic_outputs(db, cutoff):
    from .config import settings
    from .source_evaluation import WORK_ID
    from .source_lineage_models import SourceEvaluationCase, SourceEvaluationGrant

    directory = settings.data_dir / "operator-diagnostics" / WORK_ID
    for row in db.scalars(select(SourceEvaluationCase).where(SourceEvaluationCase.created < cutoff)):
        (directory / (row.id + ".json")).unlink(missing_ok=True)
    # A grant is authority only, never a financial receipt. Charges/holds remain.
    for row in db.scalars(select(SourceEvaluationGrant).where(SourceEvaluationGrant.expires < cutoff)):
        db.delete(row)
