"""Immutable public image versions. No provider calls or learning evidence."""
import hashlib
import re

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from .db import now
from .public_image_contract import FORMAT_VERSION, MAX_IMAGE_BYTES, ImageContractError, ImageReceipt, public_prompt
from .public_image_models import PublicImage
from .visual_references import digest

PROMPT_VERSION = "public-image-prompt-1"


def lookup_key(specification):
    return digest({"specification": specification, "format": FORMAT_VERSION, "prompt": PROMPT_VERSION})


def publish(db, selector, requested_spec, receipt, *, model, upstream, region):
    """Persist one decoded image after a caller's final authority checks.

    This does not commit, reserve, call a provider or establish factual truth.
    The caller must serialize and recheck its job, budget and authority first.
    Different outputs are each kept; an exact repeat is idempotent.
    """
    spec, _ = public_prompt(db, selector)
    if spec != requested_spec:
        raise ImageContractError("public_basis_changed")
    if (not isinstance(receipt, ImageReceipt) or not isinstance(receipt.png, bytes)
            or not receipt.png.startswith(b"\x89PNG\r\n\x1a\n") or len(receipt.png) > MAX_IMAGE_BYTES
            or not 64 <= receipt.width <= 4096 or not 64 <= receipt.height <= 4096
            or receipt.width * receipt.height > 4_194_304):
        raise ImageContractError("invalid_image_receipt")
    if (not isinstance(model, str) or not re.fullmatch(r"[a-z0-9_.-]+/[a-z0-9_.-]+", model)
            or not isinstance(upstream, str) or not re.fullmatch(r"[a-z0-9_.-]+(?:/[a-z0-9_.-]+)*", upstream)
            or region not in ("standard", "eu")):
        raise ImageContractError("invalid_route")
    image_hash = hashlib.sha256(receipt.png).hexdigest()
    lookup = lookup_key(spec)
    key = digest({"lookup": lookup, "sha256": image_hash, "model": model,
                  "upstream": upstream, "region": region})
    values = {"cache_key": key, "lookup_key": lookup, "specification": spec,
        "format_version": FORMAT_VERSION, "model": model, "upstream": upstream, "region": region,
        "png": receipt.png, "png_sha256": image_hash, "width": receipt.width, "height": receipt.height,
        "factual_status": "unassessed", "created": int(now())}
    insert = pg_insert if db.bind.dialect.name == "postgresql" else sqlite_insert
    db.execute(insert(PublicImage).values(**values).on_conflict_do_nothing(index_elements=["cache_key"]))
    return db.get(PublicImage, key)


def find_current(db, selector):
    """Read only current public versions; never generate, reserve or touch time."""
    spec, _ = public_prompt(db, selector)
    rows = db.scalars(select(PublicImage).where(PublicImage.lookup_key == lookup_key(spec))
                      .order_by(PublicImage.created, PublicImage.cache_key))
    for row in rows:
        if (row.specification == spec and row.format_version == FORMAT_VERSION
                and row.factual_status == "unassessed" and isinstance(row.png, bytes)
                and len(row.png) <= MAX_IMAGE_BYTES and hashlib.sha256(row.png).hexdigest() == row.png_sha256):
            return row
    return None
