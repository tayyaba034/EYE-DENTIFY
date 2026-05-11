-- Generated from local postgres for Supabase bootstrap

create table if not exists public.users (
  user_id integer default nextval('users_user_id_seq'::regclass) not null,
  email varchar(255) not null,
  password_hash varchar(255) not null,
  full_name varchar(255) not null,
  phone_number varchar(20),
  role user_role default 'guardian'::user_role not null,
  profile_image text,
  status varchar(20) default 'active'::character varying,
  failed_login_attempts integer default 0,
  account_locked_until timestamp without time zone,
  refresh_token text,
  created_at timestamp without time zone default CURRENT_TIMESTAMP,
  last_login timestamp without time zone,
  primary key (user_id)
);

create table if not exists public.missing_persons (
  missing_person_id integer default nextval('missing_persons_missing_person_id_seq'::regclass) not null,
  user_id integer not null,
  full_name varchar(255) not null,
  age integer,
  gender gender_type,
  height_cm numeric(5,2),
  height_range_min numeric(5,2),
  height_range_max numeric(5,2),
  last_seen_location text,
  last_seen_datetime timestamp without time zone,
  clothing_description text,
  additional_notes text,
  status case_status default 'active'::case_status,
  created_at timestamp without time zone default CURRENT_TIMESTAMP,
  updated_at timestamp without time zone default CURRENT_TIMESTAMP,
  primary key (missing_person_id)
);

create table if not exists public.media (
  media_id integer default nextval('media_media_id_seq'::regclass) not null,
  missing_person_id integer not null,
  file_path text not null,
  s3_key text,
  file_type varchar(10) not null,
  file_size_bytes bigint,
  upload_timestamp timestamp without time zone default CURRENT_TIMESTAMP,
  description varchar(500),
  primary key (media_id)
);

create table if not exists public.detections (
  detection_id integer default nextval('detections_detection_id_seq'::regclass) not null,
  missing_person_id integer not null,
  camera_id integer not null,
  detection_timestamp timestamp without time zone default CURRENT_TIMESTAMP,
  face_match_score numeric(5,4) not null,
  color_match_score numeric(5,4),
  height_match_score numeric(5,4),
  combined_score numeric(5,4) not null,
  image_snapshot_path text,
  s3_snapshot_key text,
  verified boolean default false,
  verification_timestamp timestamp without time zone,
  verified_by integer,
  notes text,
  camera_id_text text,
  track_id text,
  embedding float8[],
  confidence numeric,
  snapshot_url text,
  bbox jsonb,
  face_score numeric,
  clothing_score numeric,
  primary key (detection_id)
);

create table if not exists public.alerts (
  alert_id integer default nextval('alerts_alert_id_seq'::regclass) not null,
  detection_id integer not null,
  user_id integer not null,
  alert_timestamp timestamp without time zone default CURRENT_TIMESTAMP,
  message text not null,
  status alert_status default 'sent'::alert_status,
  priority alert_priority default 'medium'::alert_priority,
  read_timestamp timestamp without time zone,
  acknowledged_timestamp timestamp without time zone,
  fcm_token text,
  sightings_count integer default 1,
  first_seen_time timestamp without time zone default CURRENT_TIMESTAMP,
  last_seen_time timestamp without time zone default CURRENT_TIMESTAMP,
  alert_level character varying default 'preliminary'::character varying,
  camera_id_text text,
  track_id text,
  confidence numeric,
  primary key (alert_id)
);

create table if not exists public.system_logs (
  log_id integer default nextval('system_logs_log_id_seq'::regclass) not null,
  user_id integer,
  action_type varchar(100) not null,
  action_details text,
  ip_address varchar(45),
  timestamp timestamp without time zone default CURRENT_TIMESTAMP,
  primary key (log_id)
);

create table if not exists public.cameras (
  camera_id integer default nextval('cameras_camera_id_seq'::regclass) not null,
  camera_name varchar(255) not null,
  location_name varchar(500),
  latitude numeric(10,8),
  longitude numeric(11,8),
  status camera_status default 'active'::camera_status,
  ip_address varchar(45),
  installation_date date,
  last_maintenance timestamp without time zone,
  last_ping timestamp without time zone,
  camera_reliability_score numeric default 1.0,
  primary key (camera_id)
);


-- ensure cameras UUID column required by current code
alter table public.cameras add column if not exists id uuid default gen_random_uuid();
alter table public.cameras add column if not exists name text;
update public.cameras set name = coalesce(name, camera_name);
