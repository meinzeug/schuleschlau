import hashlib
import secrets
import threading
import time
from dataclasses import dataclass

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from cryptography.fernet import Fernet
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import OperationalError

from .config import settings
from .db import Audit, Child, Family, Membership, RateBucket, Session, User, get_db, now

hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)
dummy_hash = hasher.hash(secrets.token_urlsafe(24))
password_slots = threading.BoundedSemaphore(2)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def password_hash(value):
    if len(value.strip()) < 12 or len(value) > 128:
        raise HTTPException(422, "Passwort muss 12 bis 128 Zeichen lang sein.")
    with password_slots:
        return hasher.hash(value)


def verify_password(value, encoded):
    try:
        with password_slots:
            return hasher.verify(encoded or dummy_hash, value)
    except (VerificationError, InvalidHashError):
        return False


def crypt():
    if not settings.master_key:
        raise HTTPException(503, "MASTER_KEY ist nicht eingerichtet.")
    return Fernet(settings.master_key.encode())


def encrypt(value):
    return crypt().encrypt(value.encode()).decode()


def decrypt(value):
    return crypt().decrypt(value.encode()).decode()


def insert_ignore(db, model, values, key="id"):
    insert = sqlite_insert if db.bind.dialect.name == "sqlite" else pg_insert
    db.execute(insert(model).values(**values).on_conflict_do_nothing(index_elements=[key]))


def rate_limit(db, key, maximum, seconds=60, *, commit=True):
    tick = int(time.time()) // seconds
    name = f"{key}:{tick}"
    insert_ignore(db, RateBucket, {"id": name, "count": 0, "expires": (tick + 1) * seconds})
    result = db.execute(
        update(RateBucket).where(RateBucket.id == name, RateBucket.count < maximum).values(count=RateBucket.count + 1)
    )
    if commit:
        db.commit()
    if not result.rowcount:
        raise HTTPException(429, "Zu viele Anfragen. Bitte später erneut versuchen.")


@dataclass
class Principal:
    user: User
    session: Session


def authenticated(request: Request, db=Depends(get_db)):
    header = request.headers.get("authorization", "")
    token = header[7:] if header.startswith("Bearer ") else request.cookies.get("sp_session", "")
    session = db.scalar(
        select(Session).where(
            Session.token_hash == digest(token), Session.revoked.is_(False), Session.expires > int(now())
        )
    )
    if not session or int(now()) - session.seen > 7 * 86400:
        raise HTTPException(401, "Bitte erneut anmelden.")
    user = db.get(User, session.user_id)
    if not user or user.disabled or not user.verified:
        raise HTTPException(401, "Zugang ist nicht freigeschaltet.")
    # The optional assertion only denies access if a shared browser cookie
    # changed underneath the displayed account. It never selects an account,
    # grants access, or replaces the independently authenticated session.
    expected_account = request.headers.get("X-Schulpilot-Account")
    if expected_account is not None and expected_account != user.id:
        raise HTTPException(
            409,
            "Das Konto auf diesem Gerät hat sich geändert. Bitte melde dich erneut an.",
            headers={"X-Schulpilot-Account-Changed": "1"},
        )
    if session.seen < int(now()) - 300:
        session.seen = int(now())
        db.commit()
    request.state.actor = user.id
    # Request-local rendering capability only, never a stored privilege or a
    # cross-session opt-in. Explicit jobs may retain this origin snapshot.
    session.request_capabilities = frozenset(request.headers.get("X-Schulpilot-Capabilities", "").split(","))
    return Principal(user, session)


def lock_session_after_child(db, user_id, session_id):
    """Revalidate and serialize a mutation against revocation after Child.

    PostgreSQL must never wait here: family-call acceptance takes Session
    before Unit/Child.  A busy session aborts this entire transaction and the
    user can explicitly retry the action. SQLite already holds its database writer lock
    through the caller's Child update, so its subsequent read is serialized.
    """
    statement = select(Session).where(Session.id == session_id).execution_options(populate_existing=True)
    dialect = db.bind.dialect.name
    if dialect == "postgresql":
        statement = statement.with_for_update(nowait=True)
    elif dialect != "sqlite":
        raise RuntimeError("Session serialization is supported only on PostgreSQL and SQLite")
    try:
        session = db.scalar(statement)
    except OperationalError as error:
        if getattr(error.orig, "sqlstate", None) != "55P03":
            raise
        db.rollback()
        raise HTTPException(409, "Eine andere Kontoaktion läuft. Bitte erneut versuchen.") from None
    user = db.get(User, user_id, populate_existing=True)
    if (not session or session.user_id != user_id or session.revoked or session.expires <= now()
            or now() - session.seen > 7 * 86400 or not user or user.disabled or not user.verified):
        raise HTTPException(401, "Bitte erneut anmelden und die Aktion neu auswählen.")
    return session


def parent(p=Depends(authenticated)):
    if p.user.role != "parent":
        raise HTTPException(403, "Nur für Eltern verfügbar.")
    return p


def child_user(p=Depends(authenticated)):
    if p.user.role != "child":
        raise HTTPException(403, "Nur mit einem Kinderzugang verfügbar.")
    return p


def admin(p=Depends(authenticated)):
    if p.user.role != "admin":
        raise HTTPException(403, "Nur für Administratoren verfügbar.")
    return p


def family_access(db, p, family_id=None, write=False, owner=False):
    if p.user.role != "parent":
        raise HTTPException(403, "Nur für Eltern verfügbar.")
    query = select(Membership).where(Membership.user_id == p.user.id)
    if family_id:
        query = query.where(Membership.family_id == family_id)
    memberships = list(db.scalars(query))
    if len(memberships) != 1:
        raise HTTPException(404, "Familie nicht gefunden; gegebenenfalls Familie auswählen.")
    membership = memberships[0]
    if (owner and membership.permission != "owner") or (write and membership.permission == "view"):
        raise HTTPException(403, "Diese Familienberechtigung erlaubt keine Änderung.")
    family = db.get(Family, membership.family_id)
    if family.expires and family.expires < now():
        raise HTTPException(410, "Dieser synthetische Testraum ist abgelaufen.")
    return family, membership


def child_access(db, p, child_id, write=False):
    child = db.get(Child, child_id)
    if not child:
        raise HTTPException(404, "Kind nicht gefunden.")
    if p.user.role == "child":
        if child.user_id != p.user.id:
            raise HTTPException(404, "Kind nicht gefunden.")
    elif p.user.role == "parent":
        family_access(db, p, child.family_id, write=write)
    else:
        audit(db, p.user.id, "admin.private_access_denied", "private-learning-resource")
        db.commit()
        raise HTTPException(403, "Administratoren haben keinen Zugriff auf private Lerninhalte.")
    family = db.get(Family, child.family_id)
    if family.expires and family.expires < now():
        raise HTTPException(410, "Dieser Testraum ist abgelaufen.")
    return child


def own_child(db, p):
    child = db.scalar(select(Child).where(Child.user_id == p.user.id))
    if not child:
        raise HTTPException(403, "Kein Kinderzugang.")
    return child_access(db, p, child.id)


def audit(db, actor, action, target):
    db.add(Audit(actor=actor, action=action, target=target))
