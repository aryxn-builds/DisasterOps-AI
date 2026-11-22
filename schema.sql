-- Historical prototype schema, retained for reference only.
-- For Phase 0, initialize a fresh database with Alembic migrations.

-- 1. CITIZENS TABLE (Registered Users)
CREATE TABLE IF NOT EXISTS citizens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    phone VARCHAR(20) UNIQUE NOT NULL,
    status VARCHAR(20) DEFAULT 'SAFE' CHECK (status IN ('SAFE', 'HELP', 'UNRESPONSIVE')),
    latitude DOUBLE PRECISION DEFAULT 28.6139,
    longitude DOUBLE PRECISION DEFAULT 77.2090,
    address_residence TEXT,
    address_village TEXT,
    govt_id_type VARCHAR(50),
    govt_id_number VARCHAR(100),
    parent_name VARCHAR(150),
    parent_phone VARCHAR(20),
    parent_address TEXT,
    guardian_name VARCHAR(150),
    guardian_phone VARCHAR(20),
    guardian_relation VARCHAR(50),
    guardian_address TEXT,
    last_status_update TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. SOS SIGNALS TABLE (Live & Historical Distress Telemetry)
CREATE TABLE IF NOT EXISTS sos_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    citizen_id UUID REFERENCES citizens(id) ON DELETE SET NULL,
    phone VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('HELP', 'SAFE')),
    trigger_method VARCHAR(30) DEFAULT 'BUTTON' CHECK (trigger_method IN ('BUTTON', 'SHAKE_DEVICE', 'SMS_FALLBACK', 'LAST_GASP_BATTERY')),
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    accuracy_meters DOUBLE PRECISION DEFAULT 10.0,
    battery_percentage INT DEFAULT 100,
    is_network_fallback BOOLEAN DEFAULT FALSE,
    dispatched_to_rescue BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. UNREGISTERED FIND-MY-DEVICE TELEMETRY (Grey Dot Detections)
CREATE TABLE IF NOT EXISTS unregistered_device_pings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_fingerprint VARCHAR(100) NOT NULL,
    api_source VARCHAR(50) DEFAULT 'FIND_MY_DEVICE_API',
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    estimated_accuracy DOUBLE PRECISION DEFAULT 25.0,
    last_ping_time TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. RESCUE DISPATCH LOGS (5-minute batch reports)
CREATE TABLE IF NOT EXISTS rescue_batch_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_timestamp TIMESTAMPTZ DEFAULT NOW(),
    red_count INT DEFAULT 0,
    yellow_count INT DEFAULT 0,
    green_count INT DEFAULT 0,
    grey_count INT DEFAULT 0,
    shared_with_team VARCHAR(100) DEFAULT 'rescue123',
    batch_payload JSONB
);

-- Indexes for lightning-fast geospatial lookups during crisis
CREATE INDEX IF NOT EXISTS idx_citizens_status ON citizens(status);
CREATE INDEX IF NOT EXISTS idx_citizens_coords ON citizens(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_sos_status ON sos_signals(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_unregistered_coords ON unregistered_device_pings(latitude, longitude);

