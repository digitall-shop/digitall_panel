-- PostgreSQL Schema DDL (Initial)
-- NOTE: Run via Alembic migrations in practice; this file is a reference baseline.
-- UUID primary keys; timestamps in UTC; soft deletes avoided except where noted.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pgcrypto; -- optional for future encryption
CREATE EXTENSION IF NOT EXISTS citext; -- for case-insensitive usernames/email

-- Enumerations
DO $$ BEGIN
    CREATE TYPE engine_enum AS ENUM ('xray','wireguard');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Tenancy & RBAC ----------------------------------------------------------
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    username CITEXT NOT NULL,
    email CITEXT,
    password_hash TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_superuser BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, username)
);

CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, name)
);

-- Seed roles per tenant: owner, admin, operator, auditor (via migration logic)
CREATE TABLE role_assignments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, role_id)
);

-- Nodes & tagging ---------------------------------------------------------
CREATE TABLE nodes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    public_address TEXT NOT NULL,
    grpc_endpoint TEXT NOT NULL, -- host:port for mTLS gRPC
    status TEXT NOT NULL DEFAULT 'unknown', -- enum candidate: active, degraded, offline
    last_heartbeat TIMESTAMPTZ,
    capacity_score INT DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, name)
);

CREATE TABLE node_tags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    tag TEXT NOT NULL,
    UNIQUE (tenant_id, tag)
);

CREATE TABLE node_tag_map (
    node_id UUID NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    tag_id UUID NOT NULL REFERENCES node_tags(id) ON DELETE CASCADE,
    PRIMARY KEY (node_id, tag_id)
);

-- Plans & Subscriptions ---------------------------------------------------
CREATE TABLE plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    quota_bytes BIGINT, -- NULL => unlimited
    duration_days INT, -- NULL => no expiry
    allow_engines engine_enum[] NOT NULL,
    price_cents INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, name)
);

CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, -- owner / customer
    plan_id UUID REFERENCES plans(id) ON DELETE SET NULL,
    quota_bytes BIGINT, -- snapshot of plan (or override)
    quota_used_bytes BIGINT NOT NULL DEFAULT 0, -- fast path cache (updated async)
    expiry_at TIMESTAMPTZ, -- snapshot of plan
    status TEXT NOT NULL DEFAULT 'active', -- active, exhausted, expired, suspended
    engines engine_enum[] NOT NULL, -- chosen subset
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON subscriptions (tenant_id, status);
CREATE INDEX ON subscriptions (expiry_at);

-- Credentials (per engine per subscription) ------------------------------
CREATE TABLE credentials (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    subscription_id UUID NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
    engine engine_enum NOT NULL,
    username TEXT, -- e.g. for wireguard peer name or xray email field
    secret TEXT,   -- xray uuid, or wireguard private key (encrypted if needed)
    public_key TEXT, -- wireguard public key (if engine=wireguard)
    meta JSONB, -- extra engine-specific fields
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (subscription_id, engine)
);

-- Xray inbounds -----------------------------------------------------------
CREATE TABLE xray_inbounds (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    node_id UUID NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    tag TEXT NOT NULL,
    listen TEXT,
    port INT NOT NULL,
    protocol TEXT NOT NULL, -- vmess, vless, trojan, etc
    settings JSONB NOT NULL, -- raw inbound settings snippet
    stream_settings JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (node_id, tag)
);

-- WireGuard peers (shadow state, source of truth is subscription+credential)
CREATE TABLE wg_peers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    subscription_id UUID NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
    node_id UUID NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    public_key TEXT NOT NULL,
    allowed_ips TEXT[] NOT NULL,
    endpoint TEXT,
    persistent_keepalive INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (subscription_id, node_id)
);

-- Assignment of subscriptions to nodes (per engine) ----------------------
CREATE TABLE assignments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    subscription_id UUID NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
    node_id UUID NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    engine engine_enum NOT NULL,
    role TEXT NOT NULL DEFAULT 'primary', -- primary, secondary
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (subscription_id, node_id, engine)
);
CREATE INDEX ON assignments (node_id, engine);

-- Traffic Raw Events (Daily Partitioned) ---------------------------------
CREATE TABLE traffic_events (
    id BIGSERIAL NOT NULL,
    event_end_ts TIMESTAMPTZ NOT NULL,
    subscription_id UUID NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
    node_id UUID NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    engine engine_enum NOT NULL,
    bytes_up BIGINT NOT NULL,
    bytes_down BIGINT NOT NULL,
    sample_interval_secs INT NOT NULL,
    counter_seq BIGINT NOT NULL, -- monotonically increasing per (node,subscription,engine)
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (id, event_end_ts)
) PARTITION BY RANGE (event_end_ts);

-- Template / first partition (today)
CREATE TABLE traffic_events_p0 PARTITION OF traffic_events
    FOR VALUES FROM (DATE_TRUNC('day', now())) TO (DATE_TRUNC('day', now()) + INTERVAL '1 day');
CREATE UNIQUE INDEX traffic_events_dedupe_idx ON traffic_events (subscription_id, node_id, engine, event_end_ts, counter_seq);
CREATE INDEX traffic_events_lookup_idx ON traffic_events (subscription_id, event_end_ts);

-- Hourly Rollups (Monthly Partitioned) -----------------------------------
CREATE TABLE traffic_rollups_hourly (
    hour_start_ts TIMESTAMPTZ NOT NULL,
    subscription_id UUID NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
    node_id UUID NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    engine engine_enum NOT NULL,
    bytes_up BIGINT NOT NULL,
    bytes_down BIGINT NOT NULL,
    samples INT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (hour_start_ts, subscription_id, node_id, engine)
) PARTITION BY RANGE (hour_start_ts);

CREATE TABLE traffic_rollups_hourly_p0 PARTITION OF traffic_rollups_hourly
    FOR VALUES FROM (DATE_TRUNC('month', now())) TO (DATE_TRUNC('month', now()) + INTERVAL '1 month');

-- Audit Logs --------------------------------------------------------------
CREATE TABLE audit_logs (
    id BIGSERIAL PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id) ON DELETE SET NULL,
    actor_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    entity_type TEXT,
    entity_id UUID,
    ip_address INET,
    user_agent TEXT,
    details JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON audit_logs (tenant_id, created_at);

-- Helper function example (partition creation) ---------------------------
-- (Optional) A scheduler job calls a stored proc to create partitions ahead.
/*
CREATE OR REPLACE FUNCTION ensure_traffic_partitions(days_ahead INT) RETURNS VOID LANGUAGE plpgsql AS $$
DECLARE d DATE; start_ts TIMESTAMPTZ; end_ts TIMESTAMPTZ; tbl TEXT;
BEGIN
  FOR d IN SELECT generate_series(current_date, current_date + (days_ahead ||' days')::INTERVAL, INTERVAL '1 day')::date LOOP
    start_ts := d; end_ts := d + INTERVAL '1 day';
    tbl := 'traffic_events_'|| to_char(d,'YYYYMMDD');
    EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF traffic_events FOR VALUES FROM (%L) TO (%L);', tbl, start_ts, end_ts);
  END LOOP;
END; $$;
*/

-- Index tuning & retention policies handled by scheduler (drop old parts).
