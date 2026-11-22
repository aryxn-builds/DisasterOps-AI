# 🛡️ DisasterOps AI — Autonomous Disaster Response & Crisis Command System

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Leaflet](https://img.shields.io/badge/Leaflet-199900?style=for-the-badge&logo=Leaflet&logoColor=white)](https://leafletjs.com)
[![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)](https://tailwindcss.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

> **DisasterOps AI** is an emergency response and crisis operations platform engineered for real-world disaster scenarios (floods, cyclones, earthquakes). It bridges the gap between stranded citizens and field rescue teams through real-time telemetry, sensor triggers, and zero-cost offline GSM/SMS gateway fallback.

---

## 🌟 Key Highlights & Innovations

### 1. 📳 Shake-to-SOS (Device Accelerometer)
Stranded victims can trigger an emergency distress signal by **vigorously shaking their smartphone 3 times**. Powered by the browser's hardware `DeviceMotionEvent` accelerometer API with haptic vibration feedback.

### 2. 🗺️ Rescue Command Center & 4-Color Live Map
A dedicated dashboard for field disaster management authorities (`rescue123` / `RSC123`) featuring interactive Leaflet geospatial intelligence:
* 🔴 **Red Dots**: In Danger (Active SOS Triggered via Button, Shake, or SMS).
* 🟡 **Yellow Dots**: Unresponsive (Check-in expired > 6 hours).
* 🟢 **Green Dots**: Confirmed Safe (Citizen check-in verified).
* ⚪ **Grey Dots**: Unregistered victims detected via Find My Device telemetry.

### 3. 📱 Offline GSM / SMS Fallback (via [android-sms-gateway](https://github.com/capcom6/android-sms-gateway))
During network blackouts when 4G/5G/Wi-Fi dies, the app auto-formats and drafts an emergency SMS with exact satellite GPS coordinates to emergency dispatch. An ordinary spare Android phone running `capcom6/android-sms-gateway` acts as a zero-cost local GSM gateway station, ingests the SMS via webhooks, plots a Red Dot on the map, and fires an automated confirmation text back to the victim.

### 4. ⏱️ 5-Minute Autonomous Rescue Batch Worker
An `asyncio` background task automatically batches distress coordinates every 300 seconds and transmits priority rescue packages to field officers.

### 5. 🏥 Regional Hospital & Resource Enquiry
Live registry of medical facilities filtered by state and region, tracking available general beds, ICU units, active ambulances, food packages, and emergency medicines.

---

## 🏗️ System Architecture: 5 Core Modules

```
                           ┌──────────────────────────────┐
                           │      CITIZEN INTERFACE       │
                           │  - Express Setup + OTP       │
                           │  - Shake-to-SOS Sensor       │
                           │  - Offline SMS Auto-Draft    │
                           └──────────────┬───────────────┘
                                          │
                  ┌───────────────────────┴───────────────────────┐
                  ▼                                               ▼
         [Online HTTP REST]                              [Offline Cellular SMS]
                  │                                               │
                  │                                               ▼
                  │                                  ┌───────────────────────────┐
                  │                                  │  Rescue Desk Android GSM  │
                  │                                  │    (android-sms-gateway)  │
                  │                                  └────────────┬──────────────┘
                  │                                               │ Webhook: sms:received
                  ▼                                               ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   DisasterOps AI Cloud Backend (FastAPI)               │
│  - Scheduled 5-Min Coordinate Batching                                  │
│  - Multi-pattern GPS Coordinate & Regex Parser                          │
│  - In-memory cache + PostgreSQL/Supabase Persistence                    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                     RESCUE COMMAND CENTER (Admin)                      │
│  - Leaflet 4-Color Map (🔴 Red, 🟡 Yellow, 🟢 Green, ⚪ Grey)          │
│  - Search by Registered Phone Number or Username                       │
│  - Direct Field Team Dispatch Queue                                    │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start Guide

### Prerequisites
* Python 3.10 or higher
* Modern web browser (Chrome, Edge, Firefox, Safari)

### 1. Clone the Repository
```bash
git clone https://github.com/keshav316/DisasterOps-AI.git
cd DisasterOps-AI
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
*(Optional: add Supabase, PostgreSQL, or Android SMS Gateway settings if connecting external hardware).*

### 4. Run the Cloud Server
```bash
python server.py
```
Open your browser at **[http://localhost:8000](http://localhost:8000)**.

---

## 🔑 Demo Access Credentials

| Role | Username | Password | Notes |
| :--- | :--- | :--- | :--- |
| **Rescue Command Officer** | `rescue123` | `RSC123` | Full access to Live Leaflet Map, phone search, & dispatch queue |
| **Registered Citizen** | `keshav45` | `password123` | Status check-in, Shake-to-SOS, Hospital search |
| **Demo Citizen** | `keshav99` | `password123` | Pre-configured citizen profile |

---

## 📂 Project Structure

```
├── index.html            # Single-Page Web App (Landing, Citizen Dashboard & Rescue Command Portal)
├── registration.html     # Progressive anti-fatigue citizen registration interface
├── share_location.html   # Lightweight emergency one-tap GPS locator link
├── server.py             # FastAPI cloud server with 5-min batch sync and SMS webhook receiver
├── sw.js                 # Service Worker providing offline web app caching
├── schema.sql            # PostgreSQL & Supabase database schema
├── requirements.txt      # Python runtime dependencies
├── MODULES.md            # In-depth architectural specification of the 5 disaster modules
├── .env.example          # Environment variables template
└── README.md             # Project documentation
```

---

## 🛰️ Android GSM SMS Gateway Setup (Optional)

To connect a physical Android device to receive emergency SMS during total internet outages:

1. Download the open-source APK from [capcom6/android-sms-gateway releases](https://github.com/capcom6/android-sms-gateway/releases).
2. Install it on an Android phone with a physical SIM card.
3. Open the app, grant SMS permissions, and tap **Start Server**.
4. Register the webhook to forward incoming text messages to DisasterOps:
   ```bash
   curl -X POST -u admin:admin \
     -H "Content-Type: application/json" \
     -d '{
       "id": "disasterops-sms-received",
       "url": "http://<YOUR_SERVER_IP>:8000/api/v1/sms/gateway/webhook",
       "event": "sms:received"
     }' \
     http://<PHONE_IP>:8080/webhooks
   ```

---

## 📄 License
This project is licensed under the [MIT License](LICENSE).
