-- Initialize ACRaaS PostgreSQL database

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Consents table
CREATE TABLE IF NOT EXISTS consents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    consent_type VARCHAR(50) NOT NULL,
    granted BOOLEAN NOT NULL DEFAULT false,
    granted_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_consents_user_id ON consents(user_id);
CREATE INDEX idx_consents_consent_type ON consents(consent_type);

-- Advertisers table
CREATE TABLE IF NOT EXISTS advertisers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    stripe_customer_id VARCHAR(255),
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_advertisers_email ON advertisers(email);

-- Billing events table
CREATE TABLE IF NOT EXISTS billing_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    advertiser_id UUID NOT NULL REFERENCES advertisers(id),
    event_type VARCHAR(50) NOT NULL,
    amount_cents BIGINT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_billing_events_advertiser_id ON billing_events(advertiser_id);
CREATE INDEX idx_billing_events_created_at ON billing_events(created_at);

-- API Keys table
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    advertiser_id UUID NOT NULL REFERENCES advertisers(id),
    key_hash VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_api_keys_advertiser_id ON api_keys(advertiser_id);
