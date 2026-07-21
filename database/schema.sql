-- ============================================================================
-- Cloud-Based Multi-Agent AI Student Help Desk  -- PostgreSQL 15 Schema
-- Normalized to 3NF. Uses pgvector for embeddings on the KnowledgeBase.
-- ============================================================================
CREATE EXTENSION IF NOT EXISTS "pgcrypto";       -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS vector;           -- pgvector (embeddings)

-- ---------- Departments -----------------------------------------------------
CREATE TABLE departments (
    department_id     SERIAL PRIMARY KEY,
    department_name   VARCHAR(120) NOT NULL UNIQUE,
    contact_email     VARCHAR(160),
    sla_hours         INT NOT NULL DEFAULT 48,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------- Students --------------------------------------------------------
CREATE TABLE students (
    student_id        VARCHAR(20) PRIMARY KEY,          -- e.g. 21CS7042
    name              VARCHAR(120) NOT NULL,
    email             VARCHAR(160) NOT NULL UNIQUE,
    department_id     INT NOT NULL REFERENCES departments(department_id),
    semester          SMALLINT NOT NULL CHECK (semester BETWEEN 1 AND 10),
    password_hash     VARCHAR(255) NOT NULL,
    preferred_lang    VARCHAR(8) NOT NULL DEFAULT 'en',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------- Faculty ---------------------------------------------------------
CREATE TABLE faculty (
    faculty_id        VARCHAR(20) PRIMARY KEY,
    name              VARCHAR(120) NOT NULL,
    email             VARCHAR(160) NOT NULL UNIQUE,
    department_id     INT NOT NULL REFERENCES departments(department_id),
    role              VARCHAR(30) NOT NULL DEFAULT 'faculty',  -- faculty|hod|admin
    password_hash     VARCHAR(255) NOT NULL,
    is_available      BOOLEAN NOT NULL DEFAULT TRUE,
    open_ticket_count INT NOT NULL DEFAULT 0,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------- Knowledge Base --------------------------------------------------
CREATE TABLE knowledge_base (
    knowledge_id      BIGSERIAL PRIMARY KEY,
    question          TEXT NOT NULL,
    answer            TEXT NOT NULL,
    department_id     INT NOT NULL REFERENCES departments(department_id),
    source_url        TEXT,
    status            VARCHAR(15) NOT NULL DEFAULT 'draft',    -- draft|approved|archived
    version           INT NOT NULL DEFAULT 1,
    approved_by       VARCHAR(20) REFERENCES faculty(faculty_id),
    embedding         vector(384),                             -- MiniLM dim
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------- Tickets ---------------------------------------------------------
CREATE TABLE tickets (
    ticket_id         VARCHAR(24) PRIMARY KEY,          -- TKT-2026-000123
    student_id        VARCHAR(20) NOT NULL REFERENCES students(student_id),
    department_id     INT NOT NULL REFERENCES departments(department_id),
    faculty_id        VARCHAR(20) REFERENCES faculty(faculty_id),
    query             TEXT NOT NULL,
    intent            VARCHAR(40),
    ai_draft_answer   TEXT,
    faculty_answer    TEXT,
    confidence        NUMERIC(4,3),
    status            VARCHAR(15) NOT NULL DEFAULT 'open', -- open|assigned|answered|resolved|closed
    priority          VARCHAR(10) NOT NULL DEFAULT 'medium',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    assigned_at       TIMESTAMPTZ,
    resolved_at       TIMESTAMPTZ
);

-- ---------- Chat History ----------------------------------------------------
CREATE TABLE chat_history (
    chat_id           BIGSERIAL PRIMARY KEY,
    student_id        VARCHAR(20) NOT NULL REFERENCES students(student_id),
    session_id        UUID NOT NULL,
    message           TEXT NOT NULL,
    response          TEXT,
    intent            VARCHAR(40),
    confidence        NUMERIC(4,3),
    answered_by       VARCHAR(15),                       -- ai|ticket
    ticket_id         VARCHAR(24) REFERENCES tickets(ticket_id),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------- Notifications ---------------------------------------------------
CREATE TABLE notifications (
    notification_id   BIGSERIAL PRIMARY KEY,
    user_id           VARCHAR(20) NOT NULL,
    user_type         VARCHAR(10) NOT NULL,              -- student|faculty|admin
    channel           VARCHAR(10) NOT NULL DEFAULT 'email',
    subject           VARCHAR(200),
    message           TEXT NOT NULL,
    status            VARCHAR(12) NOT NULL DEFAULT 'queued', -- queued|sent|failed
    ticket_id         VARCHAR(24) REFERENCES tickets(ticket_id),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    sent_at           TIMESTAMPTZ
);

-- ---------- Audit Logs ------------------------------------------------------
CREATE TABLE audit_logs (
    log_id            BIGSERIAL PRIMARY KEY,
    actor_id          VARCHAR(40),
    actor_type        VARCHAR(15),
    action            VARCHAR(80) NOT NULL,
    entity            VARCHAR(40),
    entity_id         VARCHAR(40),
    detail            JSONB,
    ip_address        INET,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------- Indexes ---------------------------------------------------------
CREATE INDEX idx_students_dept       ON students(department_id);
CREATE INDEX idx_faculty_dept        ON faculty(department_id);
CREATE INDEX idx_kb_dept_status      ON knowledge_base(department_id, status);
CREATE INDEX idx_kb_embedding        ON knowledge_base USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_tickets_student     ON tickets(student_id);
CREATE INDEX idx_tickets_dept_status ON tickets(department_id, status);
CREATE INDEX idx_tickets_faculty     ON tickets(faculty_id, status);
CREATE INDEX idx_chat_student        ON chat_history(student_id, created_at DESC);
CREATE INDEX idx_notif_user          ON notifications(user_id, status);
CREATE INDEX idx_audit_entity        ON audit_logs(entity, entity_id);
CREATE INDEX idx_audit_created       ON audit_logs(created_at DESC);
