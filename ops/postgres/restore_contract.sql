-- All writes are temporary or rolled back. Archived rows remain unchanged.
BEGIN;
DO $$ BEGIN
  IF current_setting('server_version_num')::int / 10000 <> 17 THEN
    RAISE EXCEPTION 'PostgreSQL major contract mismatch';
  END IF;
  IF (SELECT extversion FROM pg_extension WHERE extname = 'vector') IS DISTINCT FROM '0.8.6' THEN
    RAISE EXCEPTION 'pgvector contract mismatch';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_database WHERE datname=current_database()
      AND datcollversion IS DISTINCT FROM pg_database_collation_actual_version(oid)) THEN
    RAISE EXCEPTION 'Collation version mismatch: rebuild affected indexes before acceptance';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_index i JOIN pg_class c ON c.oid=i.indexrelid
      JOIN pg_namespace n ON n.oid=c.relnamespace
      WHERE n.nspname='public' AND (NOT i.indisvalid OR NOT i.indisready)) THEN
    RAISE EXCEPTION 'Invalid or unready application index';
  END IF;
END $$;
CREATE TEMP TABLE pr5_restore_contract (
  id integer PRIMARY KEY, payload jsonb, amount numeric(28,8), embedding vector(3)
);
INSERT INTO pr5_restore_contract VALUES
  (1, '{"nested":{"valid":true}}', 42.12345678, '[1,0,0]'),
  (2, '{"nested":{"valid":false}}', -0.00000001, '[0,1,0]');
CREATE INDEX ON pr5_restore_contract USING hnsw (embedding vector_l2_ops);
CREATE INDEX ON pr5_restore_contract USING gin (payload);
-- Different textual offsets must preserve the same instant, independently of
-- host/DB timezone. A major upgrade uses logical dump/restore, never old volumes.
CREATE TEMP TABLE pr7_timestamp_contract (instant timestamptz NOT NULL);
INSERT INTO pr7_timestamp_contract VALUES ('2026-10-25T02:30:00+02:00');
SET LOCAL TIME ZONE 'Pacific/Honolulu';
DO $$ BEGIN
  IF (SELECT instant FROM pr7_timestamp_contract) <> '2026-10-25T00:30:00Z'::timestamptz
      OR (SELECT instant AT TIME ZONE 'UTC' FROM pr7_timestamp_contract)
         <> '2026-10-25 00:30:00'::timestamp THEN
    RAISE EXCEPTION 'UTC instant / timezone contract failed';
  END IF;
END $$;
DO $$ DECLARE rejected boolean := false; BEGIN
  IF (SELECT amount FROM pr5_restore_contract WHERE id=1) <> 42.12345678
     OR (SELECT payload #>> '{nested,valid}' FROM pr5_restore_contract WHERE id=1) <> 'true'
     OR (SELECT embedding <-> '[1,0,0]' FROM pr5_restore_contract WHERE id=1) <> 0 THEN
    RAISE EXCEPTION 'Numeric/JSONB/vector contract failed';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM dataset_versions) THEN
    RAISE EXCEPTION 'Explicit PIT fixture missing';
  END IF;
  BEGIN
    UPDATE dataset_versions SET content_hash=content_hash WHERE id=(SELECT id FROM dataset_versions LIMIT 1);
  EXCEPTION WHEN raise_exception THEN
    IF SQLERRM NOT LIKE '%immutable%' THEN RAISE; END IF;
    rejected := true;
  END;
  IF NOT rejected THEN RAISE EXCEPTION 'PIT update unexpectedly accepted'; END IF;
END $$;
SELECT json_build_object('server_version', current_setting('server_version'),
  'lc_collate', (SELECT datcollate FROM pg_database WHERE datname=current_database()),
  'lc_ctype', (SELECT datctype FROM pg_database WHERE datname=current_database()),
  'vector', (SELECT extversion FROM pg_extension WHERE extname='vector'),
  'collation_provider', (SELECT datlocprovider FROM pg_database WHERE datname=current_database()),
  'recorded_collation_version', (SELECT datcollversion FROM pg_database WHERE datname=current_database()),
  'actual_collation_version', (SELECT pg_database_collation_actual_version(oid) FROM pg_database WHERE datname=current_database()),
  'timezone_contract', 'UTC_INSTANT_PRESERVED');
ROLLBACK;
