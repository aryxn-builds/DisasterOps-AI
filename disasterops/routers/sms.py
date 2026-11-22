from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from ..db import DB
from ..schemas import GatewayEvent
from ..services.sms import record_sms, signature_valid

router = APIRouter(prefix="/sms", tags=["SMS"])


@router.post("/gateway/webhook")
async def gateway_webhook(
    request: Request,
    db: DB,
    signature: Annotated[str, Header(alias="X-Signature")] = "",
    timestamp: Annotated[str, Header(alias="X-Timestamp")] = "",
):
    secret = request.app.state.settings.android_sms_gateway_webhook_secret
    if not secret or not secret.get_secret_value():
        raise HTTPException(503, "SMS intake is disabled")
    raw = bytearray()
    async for chunk in request.stream():
        if len(raw) + len(chunk) > 32768:
            raise HTTPException(413, "Webhook request too large")
        raw.extend(chunk)
    if not signature_valid(bytes(raw), signature, timestamp, secret.get_secret_value()):
        raise HTTPException(401, "Invalid webhook signature")
    try:
        data = GatewayEvent.model_validate_json(raw)
    except ValidationError:
        raise HTTPException(400, "Invalid SMS event") from None
    return {"status": await run_in_threadpool(record_sms, db, data)}
