-- PostgreSQL schema for AI Recruitment & Talent Management Copilot
-- Milestone 1: Resume Parser and Candidate Profiling

CREATE TABLE IF NOT EXISTS candidates (
    id              SERIAL PRIMARY KEY,
    full_name       VARCHAR(255),
    email           VARCHAR(255),
    phone           VARCHAR(50),
    skills          TEXT,
    education       TEXT,
    experience      TEXT,
    certifications  TEXT,
    projects        TEXT,
    raw_text        TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Optional index for faster lookups by email and recent records
CREATE INDEX IF NOT EXISTS idx_candidates_email ON candidates (email);
CREATE INDEX IF NOT EXISTS idx_candidates_created_at ON candidates (created_at DESC);
