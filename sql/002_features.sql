-- 機能拡張用 DDL（既存データを消さずに追加）
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

DO $$ BEGIN CREATE TYPE audiencetype AS ENUM ('individual', 'corporate', 'both'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE applicationstatus AS ENUM ('inquiry', 'applied', 'converted', 'lost'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE inquirystatus AS ENUM ('open', 'answered', 'closed'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE materialtype AS ENUM ('paper', 'pdf', 'digital'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE mediatype AS ENUM ('vod', 'live', 'replay'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE examstatus AS ENUM ('draft', 'open', 'closed'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE attemptstatus AS ENUM ('in_progress', 'submitted', 'passed', 'failed'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- userrole に corporate_manager を追加（存在すればスキップ）
DO $$ BEGIN
  ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'corporate_manager';
EXCEPTION WHEN others THEN NULL;
END $$;

-- enrollmentstatus に renewed を追加
DO $$ BEGIN
  ALTER TYPE enrollmentstatus ADD VALUE IF NOT EXISTS 'renewed';
EXCEPTION WHEN others THEN NULL;
END $$;

ALTER TABLE users ADD COLUMN IF NOT EXISTS organization_name VARCHAR(255);

ALTER TABLE courses ADD COLUMN IF NOT EXISTS audience audiencetype DEFAULT 'individual';
ALTER TABLE courses ADD COLUMN IF NOT EXISTS service_types VARCHAR[] DEFAULT '{}';
ALTER TABLE courses ADD COLUMN IF NOT EXISTS price NUMERIC(12,2);
ALTER TABLE courses ADD COLUMN IF NOT EXISTS qualification_name VARCHAR(255);
ALTER TABLE courses ADD COLUMN IF NOT EXISTS draft_started_at TIMESTAMPTZ;
ALTER TABLE courses ADD COLUMN IF NOT EXISTS published_at TIMESTAMPTZ;

ALTER TABLE lessons ADD COLUMN IF NOT EXISTS has_correction BOOLEAN DEFAULT FALSE;

ALTER TABLE enrollments ADD COLUMN IF NOT EXISTS renewed_at TIMESTAMPTZ;

ALTER TABLE assignment_submissions ADD COLUMN IF NOT EXISTS corrector_id UUID;
ALTER TABLE assignment_submissions ADD COLUMN IF NOT EXISTS turnaround_hours INTEGER;

CREATE TABLE IF NOT EXISTS applications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  email VARCHAR(255) NOT NULL,
  full_name VARCHAR(255) NOT NULL,
  organization_name VARCHAR(255),
  status applicationstatus NOT NULL DEFAULT 'applied',
  source VARCHAR(64),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  converted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS materials (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  title VARCHAR(255) NOT NULL,
  material_type materialtype NOT NULL DEFAULT 'paper',
  shipping_required BOOLEAN NOT NULL DEFAULT TRUE,
  stock_quantity INTEGER,
  download_url VARCHAR(512),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS media_contents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  title VARCHAR(255) NOT NULL,
  media_type mediatype NOT NULL DEFAULT 'vod',
  stream_url VARCHAR(512),
  duration_seconds INTEGER,
  scheduled_at TIMESTAMPTZ,
  is_live_now BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS exams (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  title VARCHAR(255) NOT NULL,
  passing_score INTEGER NOT NULL DEFAULT 70,
  status examstatus NOT NULL DEFAULT 'draft',
  questions JSONB NOT NULL DEFAULT '[]',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS exam_attempts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  exam_id UUID NOT NULL REFERENCES exams(id) ON DELETE CASCADE,
  enrollment_id UUID NOT NULL REFERENCES enrollments(id) ON DELETE CASCADE,
  score INTEGER,
  status attemptstatus NOT NULL DEFAULT 'in_progress',
  answers JSONB,
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  submitted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS certificates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  enrollment_id UUID NOT NULL REFERENCES enrollments(id) ON DELETE CASCADE,
  certificate_no VARCHAR(64) NOT NULL UNIQUE,
  title VARCHAR(255) NOT NULL,
  issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS inquiries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  email VARCHAR(255) NOT NULL,
  subject VARCHAR(255) NOT NULL,
  body TEXT NOT NULL,
  category VARCHAR(64) NOT NULL DEFAULT 'general',
  status inquirystatus NOT NULL DEFAULT 'open',
  resolved_by_faq BOOLEAN NOT NULL DEFAULT FALSE,
  answer TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  answered_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS faq_articles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  category VARCHAR(64) NOT NULL,
  question VARCHAR(512) NOT NULL,
  answer TEXT NOT NULL,
  view_count INTEGER NOT NULL DEFAULT 0,
  helpful_count INTEGER NOT NULL DEFAULT 0,
  is_published BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
