from fastapi import APIRouter, HTTPException, Request, Response
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError

from ..db import DB
from ..models import Account, CitizenSafety, LoginSession
from ..schemas import Login, Register
from ..services.auth import (
    COOKIE,
    CurrentAccount,
    authenticate,
    password_hasher,
    token_digest,
)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", status_code=201)
def register(data: Register, db: DB):
    account = Account(
        username=data.username,
        password_hash=password_hasher.hash(data.password),
        phone=data.phone,
        role="citizen",
    )
    db.add(account)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Username unavailable") from None
    return {"username": account.username}


@router.post("/login", status_code=204)
def login(data: Login, request: Request, db: DB, response: Response):
    config = request.app.state.settings
    token = authenticate(db, data.username, data.password, config.session_seconds)
    response.set_cookie(
        COOKIE,
        token,
        max_age=config.session_seconds,
        httponly=True,
        secure=config.secure_cookies,
        samesite="strict",
        path="/",
    )


@router.get("/me")
def me(account: CurrentAccount, db: DB):
    checkin = db.get(CitizenSafety, account.id) if account.role == "citizen" else None
    return {
        "username": account.username,
        "role": account.role,
        "safety_status": checkin.status if checkin else None,
        "safety_updated_at": checkin.updated_at if checkin else None,
    }


@router.post("/logout", status_code=204)
def logout(request: Request, db: DB, response: Response):
    token = request.cookies.get(COOKIE, "")
    if 0 < len(token) <= 64:
        db.execute(
            delete(LoginSession).where(LoginSession.token_hash == token_digest(token))
        )
        db.commit()
    response.delete_cookie(
        COOKIE,
        httponly=True,
        secure=request.app.state.settings.secure_cookies,
        samesite="strict",
        path="/",
    )
