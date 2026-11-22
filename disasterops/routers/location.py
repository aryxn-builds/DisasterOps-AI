import re
import secrets
from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select, update

from ..db import DB
from ..models import LocationRequest, SOSReport, now
from ..schemas import ShareRequest, ShareSubmit
from ..services.auth import Dispatcher, token_digest
from ..services.sms import send_location_request

router = APIRouter(prefix="/locate", tags=["consent-based location"])


@router.post("/request", status_code=201)
def request_location(
    data: ShareRequest, request: Request, db: DB, dispatcher: Dispatcher
):
    report = db.get(SOSReport, str(data.report_id))
    if report is None:
        raise HTTPException(404, "Report not found")
    phone = report.phone
    if not phone or not re.fullmatch(r"\+[1-9][0-9]{6,14}", phone):
        raise HTTPException(409, "This report has no international callback number")
    settings = request.app.state.settings
    if not (
        settings.android_sms_gateway_url
        and settings.android_sms_gateway_user
        and settings.android_sms_gateway_password
    ):
        raise HTTPException(503, "Outbound SMS is disabled")
    token = secrets.token_urlsafe(32)
    entry = LocationRequest(
        report_id=report.id,
        requested_by=dispatcher.id,
        token_hash=token_digest(token),
        expires_at=now() + timedelta(minutes=30),
    )
    db.add(entry)
    db.commit()
    accepted = send_location_request(settings, phone, token)
    return {
        "request_id": entry.id,
        "status": "accepted_by_gateway" if accepted else "delivery_unconfirmed",
    }


@router.post("/submit")
def submit_location(data: ShareSubmit, db: DB):
    result = db.execute(
        update(LocationRequest)
        .where(
            LocationRequest.token_hash == token_digest(data.token),
            LocationRequest.expires_at > now(),
            LocationRequest.submitted_at.is_(None),
        )
        .values(submitted_at=now(), **data.model_dump(exclude={"token"}))
    )
    if not result.rowcount:
        raise HTTPException(404, "Invalid, expired or used share link")
    db.commit()
    return {"status": "received"}


@router.get("/status/{request_id}")
def location_status(request_id: UUID, db: DB, dispatcher: Dispatcher):
    entry = db.scalar(
        select(LocationRequest).where(
            LocationRequest.id == str(request_id),
            LocationRequest.requested_by == dispatcher.id,
        )
    )
    if entry is None:
        raise HTTPException(404, "Location request not found")
    expiry = (
        entry.expires_at.replace(tzinfo=now().tzinfo)
        if entry.expires_at.tzinfo is None
        else entry.expires_at
    )
    if entry.submitted_at:
        return {
            "status": "LOCATED",
            "latitude": entry.latitude,
            "longitude": entry.longitude,
            "accuracy_meters": entry.accuracy_meters,
            "submitted_at": entry.submitted_at,
        }
    return {"status": "EXPIRED" if expiry <= now() else "PENDING"}
