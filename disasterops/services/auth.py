import hashlib
import secrets
from datetime import timedelta
from typing import Annotated

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Depends, HTTPException, Request
from sqlalchemy import delete, select

from ..db import DB
from ..models import Account, LoginSession, now

COOKIE = "disasterops_session"
password_hasher = PasswordHasher()
dummy_hash = password_hasher.hash(secrets.token_urlsafe(32))


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def authenticate(db: DB, username: str, password: str, seconds: int) -> str:
    account = db.scalar(select(Account).where(Account.username == username))
    try:
        password_hasher.verify(
            account.password_hash if account else dummy_hash, password
        )
    except (VerificationError, InvalidHashError):
        raise HTTPException(401, "Invalid credentials") from None
    if not account:
        raise HTTPException(401, "Invalid credentials")
    if password_hasher.check_needs_rehash(account.password_hash):
        account.password_hash = password_hasher.hash(password)
    token = secrets.token_urlsafe(32)
    db.execute(delete(LoginSession).where(LoginSession.expires_at <= now()))
    db.add(
        LoginSession(
            token_hash=token_digest(token),
            account_id=account.id,
            expires_at=now() + timedelta(seconds=seconds),
        )
    )
    db.commit()
    return token


def current_account(request: Request, db: DB) -> Account:
    token = request.cookies.get(COOKIE, "")
    if 0 < len(token) <= 64:
        account = db.scalar(
            select(Account)
            .join(LoginSession)
            .where(
                LoginSession.token_hash == token_digest(token),
                LoginSession.expires_at > now(),
            )
        )
        if account:
            return account
    raise HTTPException(401, "Authentication required")


CurrentAccount = Annotated[Account, Depends(current_account)]


def require_role(role: str):
    def authorized(account: CurrentAccount) -> Account:
        if account.role != role:
            raise HTTPException(403, "Insufficient permissions")
        return account

    return Depends(authorized)


Citizen = Annotated[Account, require_role("citizen")]
Dispatcher = Annotated[Account, require_role("dispatcher")]
Responder = Annotated[Account, require_role("responder")]
