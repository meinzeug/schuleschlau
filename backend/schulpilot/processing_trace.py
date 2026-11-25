"""Bounded, read-only provenance for an authorized family's processing job.

This is operational metadata, not a learning result or a retry mechanism.
Never include raw provider responses, source text, answers, or opaque telemetry.
"""

import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from .db import Job, LanguageProject, LearningUnit, Material, TutorTurn, Usage, VocabularyImport, get_db
from .job_failures import CODES
from .security import child_access, parent
from .source_lineage_models import SourceRevision
from .visual_reference_models import UnitVisualSnapshot, VisualReference

router = APIRouter(tags=["Materialien und KI-Aufträge"])
ID = re.compile(r"^[a-f0-9]{32}$")
SHA256 = re.compile(r"^[a-f0-9]{64}$")
SAFE_LABEL = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._/:+\-]{0,159}$")
LIMIT = 32


def safe_id(value):
    return isinstance(value, str) and bool(ID.fullmatch(value))


def label(value):
    return value if isinstance(value, str) and SAFE_LABEL.fullmatch(value) else None


def sha256(value):
    return value if isinstance(value, str) and SHA256.fullmatch(value) else None


@router.get("/jobs/{job_id}/trace")
def processing_trace(job_id: str, p=Depends(parent), db=Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Auftrag nicht gefunden.")
    child = child_access(db, p, job.child_id)
    payload = job.payload if isinstance(job.payload, dict) else {}
    result = job.result if isinstance(job.result, dict) else {}
    kinds = {
        "extract": "countercheck" if payload.get("material_check") else "recognition",
        "unit": "generation",
        "package": "generation",
        "study_block": "generation",
        "coach_practice": "generation",
        "controller_check": "generation",
        "coach": "feedback",
        "decision": "decision",
        "unit_visuals": "visual",
        "learning_asset": "visual",
        "public_image": "visual",
        "public_image_review": "visual_review",
        "exam_review": "exam_review",
        "vocabulary_import": "vocabulary",
        "language_project": "language",
        "tutor": "tutor",
        "schulbuddy": "tutor",
        "parent_review": "parent_review",
    }
    usages = list(
        db.scalars(
            select(Usage)
            .where(Usage.job_id == job.id, Usage.child_id == child.id, Usage.family_id == child.family_id)
            .order_by(Usage.id)
            .limit(2)
        )
    )
    model = None
    failure_detail = None
    request_schema_sha256 = None
    if len(usages) == 1:
        usage = usages[0]
        model = {
            "provider": label(usage.provider),
            "model": label(usage.model),
            "config_revision": usage.config_revision if type(usage.config_revision) is int else None,
        }
        telemetry = usage.telemetry if isinstance(usage.telemetry, dict) else {}
        request_schema_sha256 = sha256(telemetry.get("request_schema_sha256"))
        if job.status == "failed" and telemetry.get("finish_reason") == "length":
            failure_detail = "output_length"
        elif job.status == "failed":
            validation = telemetry.get("validation")
            if isinstance(validation, dict) and type(validation.get("version")) is int and validation["version"] == 1:
                errors = validation.get("errors")
                if isinstance(errors, list):
                    for entry in errors[:3]:
                        reason = entry.get("reason") if isinstance(entry, dict) else None
                        if isinstance(reason, str) and reason in {"question_fraction_ambiguous", "question_fraction_result", "question_fraction_form"}:
                            failure_detail = reason
                            break

    proposed = payload.get("sources") if isinstance(payload.get("sources"), list) else []
    if not proposed and job.kind == "tutor" and safe_id(payload.get("turn_id")):
        turn = db.get(TutorTurn, payload["turn_id"])
        if turn and turn.job_id == job.id and turn.child_id == child.id and isinstance(turn.source_revisions, list):
            proposed = turn.source_revisions
    linked = {"vocabulary_import": (VocabularyImport, "import_id"),
              "language_project": (LanguageProject, "project_id")}.get(job.kind)
    if not proposed and linked and safe_id(payload.get(linked[1])):
        row = db.get(linked[0], payload[linked[1]])
        if row and row.job_id == job.id and row.child_id == child.id and isinstance(row.source_revisions, list):
            proposed = row.source_revisions
    if not proposed and job.kind == "exam_review" and isinstance(payload.get("material_revisions"), list):
        proposed = payload["material_revisions"]
    # Single-page extraction and unit jobs bind the source in scalar fields.
    # Older or malformed jobs without an explicit revision must not acquire the
    # current revision retroactively. The common loop still checks ownership.
    if not proposed and safe_id(payload.get("material_id")):
        proposed = [{"id": payload["material_id"], "revision": payload.get("material_revision")}]
    sources, seen = [], set()
    for item in proposed[:LIMIT]:
        if not isinstance(item, dict) or not safe_id(item.get("id")):
            continue
        revision = item.get("revision")
        if type(revision) is not int or revision < 1 or item["id"] in seen:
            continue
        material = db.get(Material, item["id"])
        if not material or material.child_id != child.id:
            continue
        seen.add(item["id"])
        sources.append({"id": material.id, "revision": revision, "current_revision": material.revision})

    snapshot = None
    snapshot_id = result.get("source_snapshot_id")
    if job.status == "completed" and safe_id(snapshot_id):
        saved = db.get(SourceRevision, snapshot_id)
        material = db.get(Material, saved.material_id) if saved else None
        if (
            saved
            and saved.child_id == child.id
            and material
            and material.child_id == child.id
            and payload.get("material_id") == material.id
            and isinstance(saved.receipt, dict)
            and saved.receipt.get("job_id") == job.id
        ):
            snapshot = {
                "id": saved.id,
                "revision": saved.revision,
                "sequence": saved.sequence,
                "cause": label(saved.cause),
            }
            receipt = saved.receipt
            # A countercheck job points to the merged snapshot; its receipt
            # retains the same base hashes as the second literal reading.
            expected_cause = "auto_check" if payload.get("material_check") else "extraction"
            if (job.kind == "extract" and saved.cause == expected_cause
                    and type(receipt.get("version")) is int and receipt["version"] == 1):
                snapshot["template"] = {
                    "prompt_sha256": sha256(receipt.get("base_prompt_digest")),
                    "schema_sha256": sha256(receipt.get("base_schema_digest")),
                }

    raw_units = result.get("unit_ids") if isinstance(result.get("unit_ids"), list) else [result.get("unit_id")]
    units, seen_units = [], set()
    reference_budget = LIMIT
    if job.status == "completed":
        for identifier in raw_units[:LIMIT]:
            if not safe_id(identifier) or identifier in seen_units:
                continue
            unit = db.get(LearningUnit, identifier)
            if not unit or unit.child_id != child.id:
                continue
            seen_units.add(identifier)
            visual = db.get(UnitVisualSnapshot, identifier)
            references, seen_references = [], set()
            receipts = visual.receipts if visual and isinstance(visual.receipts, list) else []
            inspected = min(len(receipts), reference_budget)
            reference_budget -= inspected
            for receipt in receipts[:inspected]:
                ref = receipt.get("reference") if isinstance(receipt, dict) else None
                if not isinstance(ref, dict) or not label(ref.get("id")) or type(ref.get("version")) is not int:
                    continue
                key = (ref["id"], ref["version"])
                if key in seen_references or not db.get(VisualReference, key):
                    continue
                seen_references.add(key)
                references.append({"id": key[0], "version": key[1]})
            units.append(
                {
                    "id": unit.id,
                    "visual_status": visual.status if visual and visual.status in ("ready", "incomplete") else None,
                    "references": references,
                    "references_truncated": len(receipts) > inspected,
                }
            )
    return {
        "job_id": job.id,
        "phase": kinds.get(job.kind, "other"),
        "status": job.status,
        "error_code": (job.error_code if job.error_code in CODES else "unknown") if job.status == "failed" else None,
        "failure_detail": failure_detail,
        "model": model,
        "model_ambiguous": len(usages) > 1,
        "request_schema_sha256": request_schema_sha256,
        "sources": sources,
        "sources_truncated": len(proposed) > LIMIT,
        "source_snapshot": snapshot,
        "units": units,
        "units_truncated": len(raw_units) > LIMIT,
    }
