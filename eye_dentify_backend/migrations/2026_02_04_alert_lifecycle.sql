-- Alert lifecycle + detection ingest upgrade
ALTER TABLE alerts
    ADD COLUMN IF NOT EXISTS sightings_count integer DEFAULT 1,
    ADD COLUMN IF NOT EXISTS first_seen_time timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    ADD COLUMN IF NOT EXISTS last_seen_time timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    ADD COLUMN IF NOT EXISTS alert_level character varying DEFAULT 'preliminary',
    ADD COLUMN IF NOT EXISTS camera_id_text text,
    ADD COLUMN IF NOT EXISTS track_id text,
    ADD COLUMN IF NOT EXISTS confidence numeric;

ALTER TABLE detections
    ADD COLUMN IF NOT EXISTS camera_id_text text,
    ADD COLUMN IF NOT EXISTS track_id text,
    ADD COLUMN IF NOT EXISTS embedding double precision[],
    ADD COLUMN IF NOT EXISTS confidence numeric,
    ADD COLUMN IF NOT EXISTS snapshot_url text,
    ADD COLUMN IF NOT EXISTS bbox jsonb,
    ADD COLUMN IF NOT EXISTS detection_timestamp timestamp without time zone,
    ADD COLUMN IF NOT EXISTS face_score numeric,
    ADD COLUMN IF NOT EXISTS clothing_score numeric;

ALTER TABLE cameras
    ADD COLUMN IF NOT EXISTS camera_reliability_score numeric DEFAULT 1.0;

CREATE INDEX IF NOT EXISTS idx_alerts_last_seen ON alerts(last_seen_time);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);
CREATE INDEX IF NOT EXISTS idx_alerts_track_camera ON alerts(track_id, camera_id_text);
CREATE INDEX IF NOT EXISTS idx_detections_track_camera ON detections(track_id, camera_id_text);
CREATE INDEX IF NOT EXISTS idx_detections_camera_time ON detections(camera_id, detection_timestamp);

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'alert_status') THEN
        BEGIN
            ALTER TYPE alert_status ADD VALUE IF NOT EXISTS 'expired';
        EXCEPTION WHEN duplicate_object THEN
            NULL;
        END;
    END IF;
END $$;
