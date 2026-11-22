import hashlib
import hmac
import re
import time

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import Settings
from ..models import SOSReport
from ..schemas import GatewayEvent


def signature_valid(raw: bytes, signature: str, timestamp: str, secret: str) -> bool:
    if not re.fullmatch(r"[0-9]{1,12}", timestamp) or not re.fullmatch(
        r"[a-fA-F0-9]{64}", signature
    ):
        return False
    if abs(time.time() - int(timestamp)) > 300:
        return False
    expected = hmac.new(
        secret.encode(), raw + timestamp.encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature.lower())


def extract_sms_telemetry(body: str) -> dict:
    # Keep the app format, Google Maps q= links, and plain coordinate pairs.
    number = r"([+-]?[0-9]{1,3}\.[0-9]{3,8})(?![0-9.])"
    patterns = (
        r"\bq=" + number + r"[,/]" + number,
        r"\b(?:lat|latitude)[:\s]*"
        + number
        + r"[\s,]+(?:lon|lng|long|longitude)[:\s]*"
        + number,
        r"(?<![\w.+-])" + number + r"(?:\s*,\s*|\s+)" + number,
    )
    data = {}
    for pattern in patterns:
        match = re.search(pattern, body, re.IGNORECASE)
        if match:
            lat, lon = map(float, match.groups())
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                accuracy = re.search(
                    r"\b(?:acc|accuracy)[:\s]*(\d{1,6}(?:\.\d+)?)", body, re.IGNORECASE
                )
                data.update(latitude=lat, longitude=lon)
                if accuracy and float(accuracy[1]) <= 100000:
                    data["accuracy_meters"] = float(accuracy[1])
            break
    battery = re.search(
        r"\b(?:bat|battery)[:\s]*([0-9]{1,3})(?![0-9])", body, re.IGNORECASE
    )
    if battery and int(battery[1]) <= 100:
        data["battery_percentage"] = int(battery[1])
    return data


def record_sms(db: Session, event: GatewayEvent) -> str:
    message = event.payload.message.replace("\x00", "\ufffd")
    sender = event.payload.sender or event.payload.phoneNumber
    report = SOSReport(
        gateway_event_id=event.id,
        source="SMS",
        message=message,
        phone=sender.replace("\x00", "\ufffd") if sender else None,
        **extract_sms_telemetry(message),
    )
    db.add(report)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if db.scalar(
            select(SOSReport.id).where(SOSReport.gateway_event_id == event.id)
        ):
            return "duplicate_ignored"
        raise
    return "acknowledged"


def send_location_request(settings: Settings, phone: str, token: str) -> bool:
    if not (
        settings.android_sms_gateway_url
        and settings.android_sms_gateway_user
        and settings.android_sms_gateway_password
    ):
        return False
    link = f"{settings.server_public_url}/share-location#t={token}"
    try:
        with httpx.Client(timeout=5, trust_env=False) as client:
            response = client.post(
                settings.android_sms_gateway_url.rstrip("/") + "/message",
                auth=(
                    settings.android_sms_gateway_user,
                    settings.android_sms_gateway_password.get_secret_value(),
                ),
                json={
                    "textMessage": {
                        "text": f"DisasterOps location request. Share only if you choose: {link}"
                    },
                    "phoneNumbers": [phone],
                },
            )
        return response.is_success
    except httpx.HTTPError:
        return False
