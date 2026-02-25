CREATE TABLE IF NOT EXISTS uploaded_documents (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL UNIQUE,
    user_id BIGINT NOT NULL,
    storage_disk VARCHAR(10) NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    mime_type VARCHAR(50) NOT NULL,
    file_hash_sha256 CHAR(64) NOT NULL,
    parsed_result TEXT NULL,
    anonymised_result TEXT NULL,
    anonymised_artifacts JSONB NULL,
    transliteration_mapping JSONB NULL,
    normalized_result JSONB NULL,
    processed_at TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pdf_jobs (
    id BIGSERIAL PRIMARY KEY,
    uploaded_document_id BIGINT NOT NULL REFERENCES uploaded_documents(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    error_message TEXT NULL,
    locked_at TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT pdf_jobs_status_check CHECK (status IN ('pending', 'processing', 'done', 'failed'))
);

CREATE TABLE IF NOT EXISTS accounts (
    id BIGSERIAL PRIMARY KEY,
    sensitive_words TEXT NULL
);
