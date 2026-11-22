"""
DisasterOps AI — Autonomous Disaster Response Cloud Backend
Framework: FastAPI (Python 3.11)
Features:
- Shake-to-SOS Telemetry Ingestion
- Supabase / PostgreSQL Persistence with graceful fallback
- 5-Minute Scheduled Rescue Batch Sync Worker
- Rescue Department Map Telemetry API (rescue123 / RSC123)
  * Red dots: In danger (Active SOS)
  * Yellow dots: Unresponsive (Expired check-ins)
  * Green dots: Safe
  * Grey dots: Unregistered victims detected via Find My Device API
- Offline SMS Inbound Fallback Webhook
"""

import asyncio
import hashlib
import hmac
import json
import os
import re
import time

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    pass  # pip install python-dotenv to load .env automatically
from datetime import datetime, timezone
from typing import Dict, List, Literal, Optional, Any, Union
import httpx
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, Header, Depends, status, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# ==============================================================
# ENVIRONMENT & CONFIGURATION
# ==============================================================
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")
RESCUE_ADMIN_USER = os.getenv("RESCUE_ADMIN_USER", "rescue123")
RESCUE_ADMIN_PASSWORD = os.getenv("RESCUE_ADMIN_PASSWORD", "RSC123")
FIND_MY_DEVICE_API_KEY = os.getenv("FIND_MY_DEVICE_API_KEY", "")
DISPATCH_INTERVAL = int(os.getenv("DISPATCH_TIMER_INTERVAL_SECONDS", "300")) # 5 minutes

# Android SMS Gateway (https://github.com/capcom6/android-sms-gateway)
ANDROID_SMS_GATEWAY_ENABLED = os.getenv("ANDROID_SMS_GATEWAY_ENABLED", "false").lower() in ["true", "1", "yes"]
ANDROID_SMS_GATEWAY_URL = os.getenv("ANDROID_SMS_GATEWAY_URL", "http://192.168.1.100:8080")
ANDROID_SMS_GATEWAY_USER = os.getenv("ANDROID_SMS_GATEWAY_USER", "admin")
ANDROID_SMS_GATEWAY_PASSWORD = os.getenv("ANDROID_SMS_GATEWAY_PASSWORD", "admin")
ANDROID_SMS_GATEWAY_WEBHOOK_SECRET = os.getenv("ANDROID_SMS_GATEWAY_WEBHOOK_SECRET", "")
SERVER_PUBLIC_URL = os.getenv("SERVER_PUBLIC_URL", "http://localhost:8000")
# SIM number of the Android phone running capcom6 -- citizens' offline SMS go HERE
EMERGENCY_SMS_GATEWAY_NUMBER = os.getenv("EMERGENCY_SMS_GATEWAY_NUMBER", "")
ALLOW_SMS_SIMULATOR = os.getenv("ALLOW_SMS_SIMULATOR", "true").lower() in ["true", "1", "yes"]

app = FastAPI(
    title="DisasterOps AI Cloud Server",
    description="Emergency Multi-Agent Backend with Scheduled 5-Minute Rescue Coordinate Sync",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================================================
# WEB APPLICATION FRONTEND SERVING
# ==============================================================
@app.get("/", response_class=FileResponse)
async def serve_index():
    """Serves the DisasterOps AI Web Application directly on localhost:8000"""
    index_path = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "DisasterOps AI Server Online. Open /docs for API schema."}

@app.get("/registration", response_class=FileResponse)
async def serve_registration():
    reg_path = os.path.join(os.path.dirname(__file__), "registration.html")
    if os.path.exists(reg_path):
        return FileResponse(reg_path)
    return FileResponse(os.path.join(os.path.dirname(__file__), "index.html"))

# ==============================================================
# IN-MEMORY & SUPABASE HYBRID DATA STORE
# ==============================================================
# Thread-safe in-memory store initialized with realistic seed telemetry
citizens_db: Dict[str, dict] = {
    "keshav45": {
        "username": "keshav45",
        "phone": "9876543210",
        "status": "SAFE",
        "latitude": 28.6190,
        "longitude": 77.2150,
        "last_update": datetime.now(timezone.utc).isoformat(),
        "battery": 95,
        "trigger": "REGISTRATION",
        "addr1": "Citizen Dashboard Session",
        "village": ""
    },
    "keshav99": {
        "username": "keshav99",
        "phone": "9876543210",
        "status": "SAFE",
        "latitude": 28.6139,
        "longitude": 77.2090,
        "last_update": datetime.now(timezone.utc).isoformat(),
        "battery": 88,
        "addr1": "Civil Lines, New Delhi",
        "village": "Kasan, Gurugram"
    },
    "rahul_delhi": {
        "username": "rahul_delhi",
        "phone": "9811223344",
        "status": "HELP",
        "latitude": 28.6289,
        "longitude": 77.2185,
        "last_update": datetime.now(timezone.utc).isoformat(),
        "battery": 14,
        "trigger": "SHAKE_DEVICE",
        "addr1": "Connaught Place, New Delhi",
        "village": "Alwar, Rajasthan"
    },
    "priya_sharma": {
        "username": "priya_sharma",
        "phone": "9871122334",
        "status": "UNRESPONSIVE",
        "latitude": 28.5921,
        "longitude": 77.2280,
        "last_update": "2026-11-21T08:00:00Z", # > 6 hours old (Yellow dot)
        "battery": 22,
        "addr1": "Lajpat Nagar, New Delhi",
        "village": ""
    }
}

# Unregistered devices detected via Google Find My Device API (Grey dots)
unregistered_devices_db: List[dict] = [
    {
        "id": "fmd_device_01",
        "source": "FIND_MY_DEVICE_API",
        "latitude": 28.6350,
        "longitude": 77.2250,
        "estimated_accuracy": 20.0,
        "note": "Unregistered mobile signal detected in water-logged sector"
    },
    {
        "id": "fmd_device_02",
        "source": "FIND_MY_DEVICE_API",
        "latitude": 28.6010,
        "longitude": 77.2110,
        "estimated_accuracy": 35.0,
        "note": "Acoustic ping detected near metro underpass"
    }
]

sos_history: List[dict] = []
rescue_dispatch_logs: List[dict] = []

# ==============================================================
# PYDANTIC SCHEMAS
# ==============================================================
class CitizenRegisterRequest(BaseModel):
    username: str
    password: str
    phone: str

class CitizenLoginRequest(BaseModel):
    username: str
    password: str

class SOSUpdateRequest(BaseModel):
    username: str
    phone: str
    status: Literal["SAFE", "HELP"]
    latitude: float
    longitude: float
    trigger_method: Literal["BUTTON", "SHAKE_DEVICE", "SMS_FALLBACK"] = "BUTTON"
    battery_percentage: Optional[int] = 100
    accuracy_meters: Optional[float] = None

class CitizenLocationUpdate(BaseModel):
    username: str
    phone: str
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    accuracy_meters: Optional[float] = None
    battery_percentage: Optional[int] = None

class RescueLoginRequest(BaseModel):
    username: str
    password: str

class SMSInboundPayload(BaseModel):
    sender_phone: str
    message_body: str
    raw_timestamp: Optional[str] = None

# capcom6/android-sms-gateway Webhook Payload Models
class AndroidSMSPayload(BaseModel):
    messageId: Optional[str] = None
    message: str
    sender: Optional[str] = None
    phoneNumber: Optional[str] = None
    recipient: Optional[str] = None
    simNumber: Optional[int] = 1
    receivedAt: Optional[str] = None

class AndroidSMSGatewayWebhook(BaseModel):
    deviceId: Optional[str] = None
    event: Optional[str] = "sms:received"
    id: Optional[str] = None
    payload: Optional[AndroidSMSPayload] = None
    webhookId: Optional[str] = None

class OutboundSMSRequest(BaseModel):
    recipient_phone: str
    message: str

class RegisterWebhookRequest(BaseModel):
    gateway_url: Optional[str] = None
    webhook_target_url: Optional[str] = None
    secret: Optional[str] = None

class FindMyDevicePayload(BaseModel):
    device_id: str
    latitude: float
    longitude: float
    accuracy_meters: float = 25.0
    telemetry_notes: Optional[str] = "Find My Device beacon"

# ==============================================================
# 5-MINUTE SCHEDULED BACKGROUND WORKER (FastAPI Lifecycle Task)
# ==============================================================
async def scheduled_rescue_sync_worker():
    """
    Background worker running every 5 minutes (300 seconds).
    Batches distress coordinates and dispatches them to the rescue department.
    """
    while True:
        try:
            await asyncio.sleep(DISPATCH_INTERVAL)
            now = datetime.now(timezone.utc).isoformat()
            
            # Identify victims
            red_victims = [c for c in citizens_db.values() if c.get("status") == "HELP"]
            yellow_victims = [c for c in citizens_db.values() if c.get("status") == "UNRESPONSIVE"]
            green_citizens = [c for c in citizens_db.values() if c.get("status") == "SAFE"]
            grey_victims = unregistered_devices_db

            batch_summary = {
                "batch_id": f"SYNC-{int(time.time())}",
                "timestamp": now,
                "shared_with": RESCUE_ADMIN_USER,
                "counts": {
                    "red_in_danger": len(red_victims),
                    "yellow_unresponsive": len(yellow_victims),
                    "green_safe": len(green_citizens),
                    "grey_unregistered_fmd": len(grey_victims)
                },
                "priority_dispatch_coordinates": [
                    {
                        "username": v.get("username"),
                        "phone": v.get("phone"),
                        "lat": v.get("latitude"),
                        "lon": v.get("longitude"),
                        "trigger": v.get("trigger", "MANUAL"),
                        "battery": v.get("battery", 100)
                    }
                    for v in red_victims
                ]
            }

            rescue_dispatch_logs.append(batch_summary)
            print(f"\n[5-MIN SCHEDULED SYNC @ {now}] Dispatched {len(red_victims)} RED distress coordinates to Rescue Team ({RESCUE_ADMIN_USER}).")
            
        except Exception as e:
            print(f"[Scheduled Worker Error]: {e}")

@app.on_event("startup")
async def startup_event():
    # Start the 5-minute scheduled sync loop
    asyncio.create_task(scheduled_rescue_sync_worker())
    print("[SERVER STARTUP] DisasterOps AI FastAPI Server is online. 5-minute rescue coordinate timer active.")

# ==============================================================
# API ROUTES: CITIZEN PORTAL
# ==============================================================
@app.post("/api/v1/citizen/register")
async def register_citizen(req: CitizenRegisterRequest):
    if req.username in citizens_db:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    citizens_db[req.username] = {
        "username": req.username,
        "password": req.password,
        "phone": req.phone,
        "status": "SAFE",
        "latitude": 28.6139,
        "longitude": 77.2090,
        "last_update": datetime.now(timezone.utc).isoformat(),
        "battery": 100
    }
    return {"status": "success", "message": f"Citizen @{req.username} registered successfully"}

@app.get("/api/v1/citizens")
async def list_registered_citizens():
    """Returns all registered citizens and their contact phone numbers"""
    return [
        {
            "username": c.get("username"),
            "phone": c.get("phone"),
            "status": c.get("status"),
            "last_update": c.get("last_update")
        }
        for c in citizens_db.values()
    ]

@app.post("/api/v1/citizen/sos")
async def update_sos_status(req: SOSUpdateRequest):
    """
    Endpoint receiving SOS updates from web app buttons or Phone Shake accelerometer trigger.
    """
    now = datetime.now(timezone.utc).isoformat()
    if req.username in citizens_db:
        citizens_db[req.username].update({
            "status": req.status,
            "latitude": req.latitude,
            "longitude": req.longitude,
            "last_update": now,
            "trigger": req.trigger_method,
            "battery": req.battery_percentage
        })
    else:
        citizens_db[req.username] = {
            "username": req.username,
            "phone": req.phone,
            "status": req.status,
            "latitude": req.latitude,
            "longitude": req.longitude,
            "last_update": now,
            "trigger": req.trigger_method,
            "battery": req.battery_percentage
        }

    sos_record = {
        "username": req.username,
        "phone": req.phone,
        "status": req.status,
        "trigger": req.trigger_method,
        "latitude": req.latitude,
        "longitude": req.longitude,
        "timestamp": now,
        "battery": req.battery_percentage
    }
    sos_history.append(sos_record)
    citizens_db[req.username].update({
        "accuracy_meters": req.accuracy_meters,
        "location_source": "APP_GPS",
        "location_time": now,
    })
    _resolve_location_requests(req.phone, req.latitude, req.longitude, req.accuracy_meters, "APP_GPS")

    return {
        "status": "acknowledged",
        "user_status": req.status,
        "trigger": req.trigger_method,
        "recorded_at": now
    }

# ==============================================================
# API ROUTES: OFFLINE SMS FALLBACK (capcom6/android-sms-gateway)
# ==============================================================
COORD_RE = r'(-?\d{1,3}\.\d{3,8})'

def extract_sms_telemetry(body: str):
    """
    Parses coordinates and metadata from an SMS sent by a citizen's phone.
    Returns (lat, lon, username, accuracy_m, battery). lat/lon are None when the
    SMS contains no coordinates -- we never guess a location.
    Accepted formats:
    - App format: 'DISASTEROPS SOS @keshav45 Lat: 28.628912 Lon: 77.218544 Acc: 8m Bat: 40%'
    - Maps link:  'https://maps.google.com/?q=28.6289,77.2185'
    - Plain pair: '28.6289, 77.2185' or '28.6289 77.2185'
    """
    username = None
    m = re.search(r'@([a-zA-Z0-9_]+)', body)
    if m:
        username = m.group(1).lower()

    acc = None
    m = re.search(r'\b(?:acc|accuracy)[:\s]*(\d+(?:\.\d+)?)', body, re.IGNORECASE)
    if m:
        acc = float(m.group(1))

    battery = None
    m = re.search(r'\b(?:bat|battery)[:\s]*(\d{1,3})\s*%?', body, re.IGNORECASE)
    if m:
        battery = min(int(m.group(1)), 100)

    patterns = [
        r'q=' + COORD_RE + r'[,/]' + COORD_RE,
        r'(?:lat|latitude)[:\s]*' + COORD_RE + r'[\s,]+(?:lon|lng|long|longitude)[:\s]*' + COORD_RE,
        COORD_RE + r'\s*,\s*' + COORD_RE,
        COORD_RE + r'\s+' + COORD_RE,
    ]
    for p in patterns:
        m = re.search(p, body, re.IGNORECASE)
        if m:
            lat, lon = float(m.group(1)), float(m.group(2))
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return lat, lon, username, acc, battery
    return None, None, username, acc, battery

async def send_sms_via_android_gateway(recipient: str, message: str) -> dict:
    """
    Sends outbound SMS via capcom6/android-sms-gateway REST API (POST /message).
    Endpoint: http://<device-ip>:8080/message
    """
    if not ANDROID_SMS_GATEWAY_ENABLED or not ANDROID_SMS_GATEWAY_URL:
        return {"status": "skipped", "reason": "ANDROID_SMS_GATEWAY_ENABLED is false in .env"}
    
    url = f"{ANDROID_SMS_GATEWAY_URL.rstrip('/')}/message"
    auth = (ANDROID_SMS_GATEWAY_USER, ANDROID_SMS_GATEWAY_PASSWORD) if ANDROID_SMS_GATEWAY_USER else None
    clean_phone = re.sub(r'[^0-9+]', '', str(recipient))
    # capcom6 local-server API body (docs.sms-gate.app): textMessage.text + phoneNumbers
    payload = {
        "textMessage": {"text": message},
        "phoneNumbers": [clean_phone]
    }
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.post(url, json=payload, auth=auth)
            return {
                "status": "success" if resp.status_code in [200, 201, 202] else "gateway_error",
                "http_status": resp.status_code,
                "response": resp.json() if "application/json" in resp.headers.get("content-type", "") else resp.text
            }
    except Exception as e:
        return {"status": "unreachable", "error": str(e)}

processed_webhook_ids: set = set()

def verify_gateway_signature(raw_body: bytes, signature: Optional[str], timestamp: Optional[str]) -> bool:
    """
    capcom6 signs webhooks: X-Signature = hex(HMAC-SHA256(signing_key, raw_body + X-Timestamp)).
    The signing key is in the Android app: Settings -> Webhooks -> Signing Key.
    Verification is skipped only when ANDROID_SMS_GATEWAY_WEBHOOK_SECRET is empty.
    """
    if not ANDROID_SMS_GATEWAY_WEBHOOK_SECRET:
        return True
    if not signature or not timestamp:
        return False
    try:
        if abs(time.time() - int(timestamp)) > 300:
            return False
    except ValueError:
        return False
    expected = hmac.new(ANDROID_SMS_GATEWAY_WEBHOOK_SECRET.encode(), raw_body + timestamp.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature.strip().lower())

async def process_inbound_sms(body_json: dict, source: str) -> dict:
    """
    Turns an inbound SMS into a map update.
    - 'DISASTEROPS SOS ...' -> status HELP (red dot) with the SMS coordinates
    - 'DISASTEROPS LOC ...' -> location update only (status unchanged)
    - anything else from a phone -> treated as a distress message (HELP)
    """
    event_type = body_json.get("event", "sms:received")
    payload = body_json.get("payload") or {}

    if not payload and "message_body" in body_json:          # simulator / flat format
        raw_message = body_json.get("message_body", "")
        sender = body_json.get("sender_phone", "Unknown")
        sim_num, device_id = 1, "test_simulator"
    else:                                                     # capcom6 sms:received
        raw_message = payload.get("message", "")
        sender = payload.get("sender") or payload.get("phoneNumber") or "Unknown"
        sim_num = payload.get("simNumber", 1)
        device_id = body_json.get("deviceId", "android_gateway_device")

    if not raw_message:
        return {"status": "ignored", "reason": "Empty message body"}

    webhook_event_id = body_json.get("id")
    if webhook_event_id:
        if webhook_event_id in processed_webhook_ids:        # capcom6 retries on timeouts
            return {"status": "duplicate_ignored", "id": webhook_event_id}
        processed_webhook_ids.add(webhook_event_id)

    now = datetime.now(timezone.utc).isoformat()
    lat, lon, parsed_user, acc, battery = extract_sms_telemetry(raw_message)
    has_coords = lat is not None
    is_location_only = "DISASTEROPS LOC" in raw_message.upper()

    # Identify the citizen: the real sender number first, then an @username in the text
    matched_user = _find_citizen_by_phone(sender)
    if not matched_user and parsed_user and parsed_user in citizens_db:
        matched_user = parsed_user

    if matched_user:
        target_username = matched_user
        citizen = citizens_db[target_username]
    else:
        clean_sender = _digits(sender)
        target_username = f"sms_{clean_sender[-4:] if len(clean_sender) >= 4 else 'anon'}"
        citizen = citizens_db.setdefault(target_username, {
            "username": target_username,
            "phone": sender,
            "status": "HELP",
            "latitude": None,
            "longitude": None,
            "addr1": "Unregistered sender via Android SMS Gateway",
            "village": "",
        })

    citizen["last_update"] = now
    citizen["trigger"] = "SMS_GATEWAY_ANDROID"
    if not is_location_only:
        citizen["status"] = "HELP"
    if battery is not None:
        citizen["battery"] = battery
    if has_coords:
        citizen.update({
            "latitude": lat,
            "longitude": lon,
            "accuracy_meters": acc,
            "location_source": "SMS",
            "location_time": now,
        })
        _resolve_location_requests(citizen.get("phone") or sender, lat, lon, acc, "SMS")

    sos_history.append({
        "username": target_username,
        "phone": sender,
        "status": citizen.get("status"),
        "trigger": "SMS_GATEWAY_ANDROID",
        "latitude": lat,
        "longitude": lon,
        "accuracy_meters": acc,
        "timestamp": now,
        "battery": battery,
        "device_id": device_id,
        "sim_number": sim_num,
        "raw_sms": raw_message,
        "source": source,
    })

    coord_txt = f"{lat:.6f}, {lon:.6f}" if has_coords else "NONE"
    print(f"\n[SMS GATEWAY] {sender} -> @{target_username} | coords={coord_txt} acc={acc}")

    if has_coords:
        ack_text = f"DisasterOps: location received ({lat:.5f}, {lon:.5f}). Rescue team notified. Stay where you are if safe."
    else:
        ack_text = ("DisasterOps: message received but NO location. Open the DisasterOps app and tap "
                    "'Send location by SMS' (works without internet), or reply: LAT 28.123456 LON 77.123456")
    if ANDROID_SMS_GATEWAY_ENABLED and source == "capcom6":
        asyncio.create_task(send_sms_via_android_gateway(sender, ack_text))
        ack_res = {"status": "queued_for_dispatch"}
    else:
        ack_res = {"status": "skipped", "text": ack_text}

    if has_coords:
        map_status = "RED_DOT_PINNED" if citizen.get("status") == "HELP" else "LOCATION_UPDATED"
    else:
        map_status = "LOCATION_UNKNOWN"

    return {
        "status": "sms_logged",
        "source": source,
        "event": event_type,
        "sender": sender,
        "citizen": target_username,
        "coordinates": [lat, lon] if has_coords else None,
        "map_status": map_status,
        "automated_reply": ack_res,
    }

@app.post("/api/v1/sms/gateway/webhook")
async def handle_android_sms_gateway_webhook(
    request: Request,
    x_signature: Optional[str] = Header(None),
    x_timestamp: Optional[str] = Header(None),
):
    """Webhook receiver for capcom6/android-sms-gateway (event: 'sms:received')."""
    raw = await request.body()
    if not verify_gateway_signature(raw, x_signature, x_timestamp):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    try:
        body_json = json.loads(raw)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    return await process_inbound_sms(body_json, "capcom6")

@app.post("/api/v1/sms/inbound")
async def handle_inbound_sms(request: Request):
    """
    Test/simulator endpoint (unsigned). Real phones must come through
    /api/v1/sms/gateway/webhook, which verifies the capcom6 signature.
    Disable in production with ALLOW_SMS_SIMULATOR=false.
    """
    if not ALLOW_SMS_SIMULATOR:
        raise HTTPException(status_code=403, detail="SMS simulator disabled")
    try:
        body_json = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    return await process_inbound_sms(body_json, "simulator")

@app.post("/api/v1/sms/gateway/send")
async def send_sms_endpoint(req: OutboundSMSRequest):
    """
    Sends an outbound SMS to a citizen via the connected Android Gateway device.
    """
    return await send_sms_via_android_gateway(req.recipient_phone, req.message)

@app.get("/api/v1/sms/gateway/status")
async def get_android_gateway_status():
    """
    Checks the status and reachability of the configured Android SMS Gateway.
    """
    if not ANDROID_SMS_GATEWAY_URL:
        return {"status": "unconfigured", "message": "ANDROID_SMS_GATEWAY_URL not set in .env"}
    
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(ANDROID_SMS_GATEWAY_URL)
            return {
                "status": "online",
                "gateway_url": ANDROID_SMS_GATEWAY_URL,
                "http_status": resp.status_code
            }
    except Exception as e:
        return {
            "status": "offline_or_unreachable",
            "gateway_url": ANDROID_SMS_GATEWAY_URL,
            "error": str(e),
            "hint": "Ensure your Android phone running android-sms-gateway is connected and server started."
        }

@app.post("/api/v1/sms/gateway/register-webhook")
async def register_gateway_webhook(req: RegisterWebhookRequest):
    """
    Registers our DisasterOps webhook endpoint on the Android device with one click.
    Calls POST {gateway_url}/webhooks with event 'sms:received'.
    """
    gw_url = req.gateway_url or ANDROID_SMS_GATEWAY_URL
    target = req.webhook_target_url or f"{SERVER_PUBLIC_URL.rstrip('/')}/api/v1/sms/gateway/webhook"
    
    url = f"{gw_url.rstrip('/')}/webhooks"
    auth = (ANDROID_SMS_GATEWAY_USER, ANDROID_SMS_GATEWAY_PASSWORD) if ANDROID_SMS_GATEWAY_USER else None
    payload = {
        "id": "disasterops-sms-received",
        "url": target,
        "event": "sms:received"
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url, json=payload, auth=auth)
            return {
                "status": "registered" if resp.status_code in [200, 201, 202] else "error",
                "http_status": resp.status_code,
                "target_url": target,
                "response": resp.json() if "application/json" in resp.headers.get("content-type", "") else resp.text
            }
    except Exception as e:
        return {"status": "failed", "error": str(e), "target_url": target}

# ==============================================================
# API ROUTES: FIND MY DEVICE UNREGISTERED DETECTIONS (Grey Dots)
# ==============================================================
@app.post("/api/v1/devices/find-my-device")
async def ingest_find_my_device_ping(payload: FindMyDevicePayload, x_api_key: Optional[str] = Header(None)):
    """
    Ingests unregistered device coordinates detected via Find My Device APIs.
    """
    entry = {
        "id": payload.device_id,
        "source": "FIND_MY_DEVICE_API",
        "latitude": payload.latitude,
        "longitude": payload.longitude,
        "estimated_accuracy": payload.accuracy_meters,
        "note": payload.telemetry_notes
    }
    unregistered_devices_db.append(entry)
    return {"status": "registered_grey_ping", "device_id": payload.device_id}

# ==============================================================
# API ROUTES: RESCUE DEPARTMENT ADMIN PORTAL (rescue123 / RSC123)
# ==============================================================
@app.post("/api/v1/rescue/login")
async def rescue_admin_login(req: RescueLoginRequest):
    if req.username == RESCUE_ADMIN_USER and req.password == RESCUE_ADMIN_PASSWORD:
        return {
            "status": "authenticated",
            "role": "RESCUE_COMMAND_OFFICER",
            "token": "rescue_session_token_xyz999"
        }
    raise HTTPException(status_code=401, detail="Invalid Rescue Team Credentials")

@app.get("/api/v1/rescue/live-map")
async def get_rescue_live_map():
    """
    Returns full marker dataset color-coded for Leaflet Map:
    - Red: Danger (Active SOS)
    - Yellow: Unresponsive (>6 hours since last ping)
    - Green: Confirmed Safe
    - Grey: Unregistered devices (Find My Device)
    """
    markers = []

    # 1. Registered Citizens
    for c in citizens_db.values():
        st = c.get("status", "SAFE")
        color = "green"
        category = "Safe"
        
        if st == "HELP":
            color = "red"
            category = "In Danger (SOS Active)"
        elif st == "UNRESPONSIVE":
            color = "yellow"
            category = "Unresponsive / Expired"

        markers.append({
            "id": c.get("username"),
            "name": c.get("username"),
            "phone": c.get("phone"),
            "color": color,
            "category": category,
            "latitude": c.get("latitude"),
            "longitude": c.get("longitude"),
            "accuracy_meters": c.get("accuracy_meters"),
            "location_source": c.get("location_source"),
            "location_time": c.get("location_time"),
            "location_known": c.get("latitude") is not None,
            "battery": c.get("battery", 100),
            "trigger": c.get("trigger", "TAP"),
            "last_update": c.get("last_update")
        })

    # 2. Unregistered Devices (Grey dots)
    for dev in unregistered_devices_db:
        markers.append({
            "id": dev.get("id"),
            "name": "Unregistered Device (Find My Device)",
            "phone": "Unknown / Non-User",
            "color": "grey",
            "category": "Unregistered Device Telemetry",
            "latitude": dev.get("latitude"),
            "longitude": dev.get("longitude"),
            "battery": "Unknown",
            "trigger": "FIND_MY_DEVICE_API",
            "last_update": "Live Ping"
        })

    # Tallies
    tally = {
        "red_danger": len([m for m in markers if m["color"] == "red"]),
        "yellow_unresponsive": len([m for m in markers if m["color"] == "yellow"]),
        "green_safe": len([m for m in markers if m["color"] == "green"]),
        "grey_unregistered": len([m for m in markers if m["color"] == "grey"]),
        "total_tracked": len(markers),
        "last_5min_sync_batches": len(rescue_dispatch_logs)
    }

    return {"tally": tally, "markers": markers}

@app.get("/api/v1/rescue/dispatch-logs")
async def get_rescue_dispatch_logs():
    return {"logs": rescue_dispatch_logs[-10:]} # Return last 10 5-minute batches

# ==============================================================
# API ROUTES: LOCATE A PHONE NUMBER (consent-based live location)
# ==============================================================
# Flow: rescue enters phone -> server SMSes a one-time link -> person opens it ->
# browser Geolocation API reads GPS -> page POSTs coords -> rescue map shows pin.
LOCATION_REQUEST_TTL_SECONDS = 30 * 60
location_requests: Dict[str, dict] = {}

class LocateRequest(BaseModel):
    phone: str

class LocationSubmit(BaseModel):
    token: str
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    accuracy_meters: Optional[float] = None

def _digits(s: str) -> str:
    return re.sub(r'[^0-9]', '', str(s or ""))

def _resolve_location_requests(phone: str, lat: float, lon: float, acc: Optional[float], source: str):
    """Marks any pending 'Request Live Location' for this phone as LOCATED."""
    target = _digits(phone)[-10:]
    now = datetime.now(timezone.utc).isoformat()
    for r in location_requests.values():
        if r["status"] == "PENDING" and r["phone"][-10:] == target:
            r.update({"status": "LOCATED", "latitude": lat, "longitude": lon,
                      "accuracy_meters": acc, "located_at": now, "source": source})

@app.get("/api/v1/config")
async def public_config():
    """Non-secret settings the citizen app caches for offline use."""
    return {"gateway_number": EMERGENCY_SMS_GATEWAY_NUMBER}

@app.get("/sw.js")
async def serve_service_worker():
    return FileResponse(os.path.join(os.path.dirname(__file__), "sw.js"),
                        media_type="application/javascript",
                        headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-cache"})

@app.post("/api/v1/citizen/location")
async def update_citizen_location(req: CitizenLocationUpdate):
    """
    Background GPS heartbeat from the citizen app (online). Updates the map
    position without changing SAFE/HELP status.
    """
    now = datetime.now(timezone.utc).isoformat()
    uname = req.username.lower()
    c = citizens_db.setdefault(uname, {"username": uname, "phone": req.phone, "status": "SAFE"})
    c.update({
        "phone": req.phone or c.get("phone"),
        "latitude": req.latitude,
        "longitude": req.longitude,
        "accuracy_meters": req.accuracy_meters,
        "location_source": "APP_GPS",
        "location_time": now,
        "last_update": now,
    })
    if req.battery_percentage is not None:
        c["battery"] = req.battery_percentage
    _resolve_location_requests(req.phone, req.latitude, req.longitude, req.accuracy_meters, "APP_GPS")
    return {"status": "ok", "recorded_at": now}

def _find_citizen_by_phone(phone: str) -> Optional[str]:
    target = _digits(phone)[-10:]
    if not target:
        return None
    for uname, c in citizens_db.items():
        if _digits(c.get("phone", ""))[-10:] == target:
            return uname
    return None

@app.post("/api/v1/locate/request")
async def request_phone_location(req: LocateRequest):
    """Sends a one-time location-share link by SMS to the given phone number."""
    import secrets
    phone = _digits(req.phone)
    if len(phone) < 10:
        raise HTTPException(status_code=400, detail="Enter a valid phone number")

    token = secrets.token_urlsafe(12)
    link = f"{SERVER_PUBLIC_URL.rstrip('/')}/share-location?t={token}"
    location_requests[token] = {
        "token": token,
        "phone": phone,
        "username": _find_citizen_by_phone(phone),
        "status": "PENDING",
        "created_at": time.time(),
        "latitude": None,
        "longitude": None,
        "accuracy_meters": None,
        "located_at": None,
    }
    sms_text = (f"DisasterOps Rescue needs your exact location. With mobile data open: {link} "
                f"-- No data? Open the DisasterOps app and tap 'Send location by SMS'.")
    sms_result = await send_sms_via_android_gateway(phone, sms_text)
    return {"token": token, "link": link, "sms": sms_result}

@app.get("/share-location", response_class=FileResponse)
async def serve_share_location():
    return FileResponse(os.path.join(os.path.dirname(__file__), "share_location.html"))

@app.post("/api/v1/locate/submit")
async def submit_phone_location(data: LocationSubmit):
    """Called by share_location.html with the phone's Geolocation API reading."""
    r = location_requests.get(data.token)
    if not r or time.time() - r["created_at"] > LOCATION_REQUEST_TTL_SECONDS:
        raise HTTPException(status_code=404, detail="Link expired or invalid")

    now = datetime.now(timezone.utc).isoformat()
    r.update({
        "status": "LOCATED",
        "latitude": data.latitude,
        "longitude": data.longitude,
        "accuracy_meters": data.accuracy_meters,
        "located_at": now,
    })
    uname = r.get("username")
    if uname and uname in citizens_db:
        citizens_db[uname].update({
            "latitude": data.latitude,
            "longitude": data.longitude,
            "accuracy_meters": data.accuracy_meters,
            "last_update": now,
            "trigger": "LOCATION_LINK",
        })
    return {"status": "received"}

@app.get("/api/v1/locate/status/{token}")
async def get_phone_location_status(token: str):
    r = location_requests.get(token)
    if not r:
        raise HTTPException(status_code=404, detail="Unknown request")
    if r["status"] == "PENDING" and time.time() - r["created_at"] > LOCATION_REQUEST_TTL_SECONDS:
        r["status"] = "EXPIRED"
    return r

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)

