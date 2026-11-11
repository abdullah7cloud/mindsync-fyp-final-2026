-- MindSync database schema (PostgreSQL).
--
-- This is the raw DDL equivalent of backend/app/models.py. Both are kept
-- in sync deliberately: the ORM models are what SQLAlchemy/Alembic use at
-- runtime, and this file is a plain, reviewable reference of the same
-- constraints (NOT NULL, CHECK, foreign keys with ON DELETE CASCADE) for
-- anyone inspecting the database directly, per the contract's requirement
-- for database-level constraint validation as a defence layer independent
-- of application-level (Pydantic) validation.
--
-- For local development the backend can create these tables automatically
-- (app.database.init_models, dev-only). For anything beyond local dev, run
-- this file directly (or use Alembic migrations) instead.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";  -- provides gen_random_uuid()

CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) NOT NULL UNIQUE,
    -- Argon2id hash string (includes salt + parameters). Never store or
    -- log the raw password anywhere.
    password_hash   VARCHAR(255) NOT NULL,
    display_name    VARCHAR(100) NOT NULL,
    email_alerts    BOOLEAN NOT NULL DEFAULT TRUE,   -- 2-day deadline e-mail on/off
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_users_email ON users (email);

CREATE TYPE task_status AS ENUM ('pending', 'completed');

CREATE TABLE IF NOT EXISTS tasks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id        UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    title           VARCHAR(200) NOT NULL,
    description     VARCHAR(2000) NOT NULL DEFAULT '',
    category        VARCHAR(100) NOT NULL DEFAULT 'general',
    -- 1 (very easy) .. 5 (very hard) — user-assigned, fed directly into the
    -- local recommendation heuristic.
    difficulty      INTEGER NOT NULL DEFAULT 3 CHECK (difficulty BETWEEN 1 AND 5),
    deadline        TIMESTAMPTZ NOT NULL,
    status          task_status NOT NULL DEFAULT 'pending',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    reminder_sent_at TIMESTAMPTZ NULL,               -- set when the deadline e-mail was sent
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at    TIMESTAMPTZ NULL                 -- set when marked done (progress charts)
);

CREATE INDEX IF NOT EXISTS ix_tasks_owner_id ON tasks (owner_id);

CREATE TABLE IF NOT EXISTS energy_checkins (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    -- 1 (exhausted) .. 5 (energised)
    energy_level    INTEGER NOT NULL CHECK (energy_level BETWEEN 1 AND 5),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_energy_checkins_user_id ON energy_checkins (user_id);

-- Wellbeing check: questionnaire answers + trained-model prediction (added Oct 2026)
CREATE TABLE IF NOT EXISTS wellbeing_checks (
    id            UUID PRIMARY KEY,
    user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    answers       JSONB NOT NULL,
    risk_label    VARCHAR(10) NOT NULL CHECK (risk_label IN ('Low', 'Medium', 'High')),
    probabilities JSONB NOT NULL,
    model_version VARCHAR(40) NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_wellbeing_checks_user_id ON wellbeing_checks (user_id);
CREATE INDEX IF NOT EXISTS ix_wellbeing_checks_created_at ON wellbeing_checks (created_at);

-- "Was this recommendation helpful?" answers (added Oct 2026). Situation numbers only, no task text.
CREATE TABLE IF NOT EXISTS recommendation_feedback (
    id            UUID PRIMARY KEY,
    user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    helpful       BOOLEAN NOT NULL,
    energy_level  INTEGER NOT NULL CHECK (energy_level BETWEEN 1 AND 5),
    difficulty    INTEGER NOT NULL CHECK (difficulty BETWEEN 1 AND 5),
    hours_left    DOUBLE PRECISION NOT NULL,
    burnout_mode  BOOLEAN NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_recommendation_feedback_user_id ON recommendation_feedback (user_id);
CREATE INDEX IF NOT EXISTS ix_recommendation_feedback_created_at ON recommendation_feedback (created_at);

-- "Forgot password" links (added Oct 2026). Only a SHA-256 hash of the secret is stored; a link works once.
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id          UUID PRIMARY KEY,
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  VARCHAR(64) NOT NULL UNIQUE,
    expires_at  TIMESTAMPTZ NOT NULL,
    used_at     TIMESTAMPTZ NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_password_reset_tokens_user_id ON password_reset_tokens (user_id);

-- ===================================================================
-- Update 20: connected Smart Planner tables (generated from app/assist/models.py
-- with SQLAlchemy's PostgreSQL dialect on 29 October 2026). The app also creates them
-- automatically on start-up (create_all); no existing table is altered.
-- ===================================================================
CREATE TABLE user_settings (
	user_id UUID NOT NULL, 
	data JSON NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (user_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE TABLE user_profiles (
	user_id UUID NOT NULL, 
	data JSON NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (user_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE TABLE task_meta (
	task_id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	kind VARCHAR(20) NOT NULL, 
	intrinsic_difficulty FLOAT NOT NULL, 
	personal_difficulty FLOAT NOT NULL, 
	est_low INTEGER NOT NULL, 
	est_likely INTEGER NOT NULL, 
	est_high INTEGER NOT NULL, 
	done_minutes INTEGER NOT NULL, 
	stages JSON NOT NULL, 
	extra JSON NOT NULL, 
	source VARCHAR(20) NOT NULL, 
	priority INTEGER NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (task_id), 
	CONSTRAINT ck_taskmeta_priority CHECK (priority BETWEEN 1 AND 3), 
	FOREIGN KEY(task_id) REFERENCES tasks (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX ix_task_meta_user_id ON task_meta (user_id);
CREATE TABLE study_plans (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	status VARCHAR(12) NOT NULL, 
	reason VARCHAR(30) NOT NULL, 
	summary JSON NOT NULL, 
	inputs JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX ix_study_plans_created_at ON study_plans (created_at);
CREATE INDEX ix_study_plans_user_id ON study_plans (user_id);
CREATE TABLE plan_sessions (
	id UUID NOT NULL, 
	plan_id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	task_id UUID, 
	day DATE NOT NULL, 
	position INTEGER NOT NULL, 
	minutes INTEGER NOT NULL, 
	break_after INTEGER NOT NULL, 
	label VARCHAR(200) NOT NULL, 
	method VARCHAR(400) NOT NULL, 
	start_hint VARCHAR(5), 
	status VARCHAR(10) NOT NULL, 
	actual_minutes INTEGER NOT NULL, 
	title VARCHAR(200), 
	subject VARCHAR(100), 
	manual BOOLEAN NOT NULL, 
	original_day DATE, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	felt VARCHAR(10), 
	PRIMARY KEY (id), 
	CONSTRAINT ck_plansession_minutes CHECK (minutes BETWEEN 5 AND 600), 
	FOREIGN KEY(plan_id) REFERENCES study_plans (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(task_id) REFERENCES tasks (id) ON DELETE CASCADE
);
CREATE INDEX ix_plan_sessions_day ON plan_sessions (day);
CREATE INDEX ix_plan_sessions_plan_id ON plan_sessions (plan_id);
CREATE INDEX ix_plan_sessions_task_id ON plan_sessions (task_id);
CREATE INDEX ix_plan_sessions_user_id ON plan_sessions (user_id);
CREATE TABLE plan_events (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	plan_session_id UUID, 
	kind VARCHAR(20) NOT NULL, 
	detail JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX ix_plan_events_created_at ON plan_events (created_at);
CREATE INDEX ix_plan_events_plan_session_id ON plan_events (plan_session_id);
CREATE INDEX ix_plan_events_user_id ON plan_events (user_id);
CREATE TABLE notifications (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	kind VARCHAR(12) NOT NULL, 
	key VARCHAR(160) NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	body VARCHAR(600) NOT NULL, 
	task_id UUID, 
	due_on DATE, 
	data JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	read_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_notification_key UNIQUE (user_id, key), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX ix_notifications_task_id ON notifications (task_id);
CREATE INDEX ix_notifications_user_id ON notifications (user_id);
CREATE TABLE task_sessions (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	task_id UUID, 
	plan_session_id UUID, 
	kind VARCHAR(20) NOT NULL, 
	planned_minutes INTEGER NOT NULL, 
	actual_minutes INTEGER NOT NULL, 
	completed BOOLEAN NOT NULL, 
	focus INTEGER, 
	felt_difficulty INTEGER, 
	energy_after INTEGER, 
	length_feel VARCHAR(8), 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_tasksession_minutes CHECK (actual_minutes BETWEEN 1 AND 600), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(task_id) REFERENCES tasks (id) ON DELETE SET NULL
);
CREATE INDEX ix_task_sessions_created_at ON task_sessions (created_at);
CREATE INDEX ix_task_sessions_task_id ON task_sessions (task_id);
CREATE INDEX ix_task_sessions_user_id ON task_sessions (user_id);
CREATE TABLE ai_usage (
	id UUID NOT NULL, 
	user_id UUID, 
	purpose VARCHAR(20) NOT NULL, 
	provider VARCHAR(20) NOT NULL, 
	model VARCHAR(60) NOT NULL, 
	input_tokens INTEGER NOT NULL, 
	output_tokens INTEGER NOT NULL, 
	cost_usd FLOAT NOT NULL, 
	latency_ms INTEGER NOT NULL, 
	outcome VARCHAR(20) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX ix_ai_usage_created_at ON ai_usage (created_at);
CREATE INDEX ix_ai_usage_user_id ON ai_usage (user_id);
CREATE TABLE reminder_log (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	task_id UUID, 
	kind VARCHAR(20) NOT NULL, 
	dedupe_key VARCHAR(120) NOT NULL, 
	status VARCHAR(10) NOT NULL, 
	attempts INTEGER NOT NULL, 
	detail VARCHAR(200) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_reminder_dedupe UNIQUE (user_id, dedupe_key), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(task_id) REFERENCES tasks (id) ON DELETE CASCADE
);
CREATE INDEX ix_reminder_log_created_at ON reminder_log (created_at);
CREATE INDEX ix_reminder_log_task_id ON reminder_log (task_id);
CREATE INDEX ix_reminder_log_user_id ON reminder_log (user_id);
CREATE TABLE weekly_reviews (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	week_start DATE NOT NULL, 
	stats JSON NOT NULL, 
	text VARCHAR(3000) NOT NULL, 
	source VARCHAR(10) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_review_week UNIQUE (user_id, week_start), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX ix_weekly_reviews_user_id ON weekly_reviews (user_id);

-- Added in update 22: tables for skill ratings, task outcomes (estimate vs actual) and logged sessions.
CREATE TABLE user_skills (
	user_id UUID NOT NULL, 
	kind VARCHAR(20) NOT NULL, 
	level INTEGER NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (user_id, kind), 
	CONSTRAINT ck_skill_level_range CHECK (level BETWEEN 1 AND 5), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE TABLE task_outcomes (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	kind VARCHAR(20) NOT NULL, 
	raw_minutes INTEGER NOT NULL, 
	actual_minutes INTEGER NOT NULL, 
	felt INTEGER, 
	predicted_personal FLOAT, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_outcome_actual CHECK (actual_minutes BETWEEN 1 AND 6000), 
	CONSTRAINT ck_outcome_raw CHECK (raw_minutes BETWEEN 1 AND 6000), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX ix_task_outcomes_created_at ON task_outcomes (created_at);
CREATE INDEX ix_task_outcomes_user_id ON task_outcomes (user_id);
CREATE TABLE session_logs (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	kind VARCHAR(20) NOT NULL, 
	minutes INTEGER NOT NULL, 
	completed BOOLEAN NOT NULL, 
	focus INTEGER, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_session_minutes CHECK (minutes BETWEEN 5 AND 600), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX ix_session_logs_created_at ON session_logs (created_at);
CREATE INDEX ix_session_logs_user_id ON session_logs (user_id);

-- AI Learning Studio (update 24): packs are written once, then only read and practised
CREATE TABLE learning_packs (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	title VARCHAR(120) NOT NULL, 
	source_name VARCHAR(200) NOT NULL, 
	source VARCHAR(10) NOT NULL, 
	content_hash VARCHAR(64) NOT NULL, 
	status VARCHAR(12) NOT NULL, 
	error VARCHAR(200) NOT NULL, 
	provider VARCHAR(20) NOT NULL, 
	model VARCHAR(60) NOT NULL, 
	lessons JSON NOT NULL, 
	input_chars INTEGER NOT NULL, 
	input_tokens INTEGER NOT NULL, 
	output_tokens INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	ready_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_pack_user_hash UNIQUE (user_id, content_hash), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX ix_learning_packs_created_at ON learning_packs (created_at);
CREATE INDEX ix_learning_packs_user_id ON learning_packs (user_id);
CREATE TABLE pack_questions (
	id UUID NOT NULL, 
	pack_id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	position INTEGER NOT NULL, 
	difficulty VARCHAR(8) NOT NULL, 
	lesson INTEGER, 
	question VARCHAR(400) NOT NULL, 
	options JSON NOT NULL, 
	answer_index INTEGER NOT NULL, 
	explanation VARCHAR(600) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_packq_answer CHECK (answer_index BETWEEN 0 AND 3), 
	FOREIGN KEY(pack_id) REFERENCES learning_packs (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX ix_pack_questions_pack_id ON pack_questions (pack_id);
CREATE INDEX ix_pack_questions_user_id ON pack_questions (user_id);
CREATE TABLE pack_cards (
	id UUID NOT NULL, 
	pack_id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	position INTEGER NOT NULL, 
	lesson INTEGER, 
	front VARCHAR(300) NOT NULL, 
	back VARCHAR(600) NOT NULL, 
	box INTEGER NOT NULL, 
	due_on DATE, 
	reviews INTEGER NOT NULL, 
	lapses INTEGER NOT NULL, 
	last_rating VARCHAR(10), 
	last_reviewed_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_packcard_box CHECK (box BETWEEN 0 AND 5), 
	FOREIGN KEY(pack_id) REFERENCES learning_packs (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX ix_pack_cards_due_on ON pack_cards (due_on);
CREATE INDEX ix_pack_cards_pack_id ON pack_cards (pack_id);
CREATE INDEX ix_pack_cards_user_id ON pack_cards (user_id);
CREATE TABLE quiz_attempts (
	id UUID NOT NULL, 
	pack_id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	difficulty VARCHAR(8) NOT NULL, 
	total INTEGER NOT NULL, 
	correct INTEGER NOT NULL, 
	answers JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(pack_id) REFERENCES learning_packs (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX ix_quiz_attempts_created_at ON quiz_attempts (created_at);
CREATE INDEX ix_quiz_attempts_pack_id ON quiz_attempts (pack_id);
CREATE INDEX ix_quiz_attempts_user_id ON quiz_attempts (user_id);

-- Simplified MindSync (update 26): study plans, tasks, notebook notes and stored documents
CREATE TABLE s_plans (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	subject VARCHAR(80) NOT NULL, 
	topic VARCHAR(120) NOT NULL, 
	goal TEXT NOT NULL, 
	target_date DATE NOT NULL, 
	mood VARCHAR(10) NOT NULL, 
	stress VARCHAR(10) NOT NULL, 
	roadmap JSON NOT NULL, 
	source VARCHAR(10) NOT NULL, 
	note VARCHAR(300) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX ix_s_plans_created_at ON s_plans (created_at);
CREATE INDEX ix_s_plans_user_id ON s_plans (user_id);
CREATE TABLE s_tasks (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	plan_id UUID NOT NULL, 
	position INTEGER NOT NULL, 
	title VARCHAR(160) NOT NULL, 
	details VARCHAR(400) NOT NULL, 
	due_date DATE NOT NULL, 
	start_time VARCHAR(5), 
	minutes INTEGER NOT NULL, 
	done BOOLEAN NOT NULL, 
	done_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(plan_id) REFERENCES s_plans (id) ON DELETE CASCADE
);
CREATE INDEX ix_s_tasks_due_date ON s_tasks (due_date);
CREATE INDEX ix_s_tasks_plan_id ON s_tasks (plan_id);
CREATE INDEX ix_s_tasks_user_id ON s_tasks (user_id);
CREATE TABLE s_notes (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	title VARCHAR(120) NOT NULL, 
	body TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX ix_s_notes_updated_at ON s_notes (updated_at);
CREATE INDEX ix_s_notes_user_id ON s_notes (user_id);
CREATE TABLE s_documents (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	ext VARCHAR(8) NOT NULL, 
	size INTEGER NOT NULL, 
	data BYTEA NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX ix_s_documents_created_at ON s_documents (created_at);
CREATE INDEX ix_s_documents_user_id ON s_documents (user_id);

-- Update 28: My Profile and Settings (new tables only; no existing table is changed)
CREATE TABLE u28_pictures (
	user_id UUID NOT NULL, 
	data BYTEA NOT NULL, 
	mime VARCHAR(20) NOT NULL, 
	version INTEGER NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (user_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE TABLE u28_preferences (
	user_id UUID NOT NULL, 
	remind_enabled BOOLEAN NOT NULL, 
	remind_percent INTEGER NOT NULL, 
	timezone VARCHAR(64) NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (user_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE TABLE u28_email_changes (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	new_email VARCHAR(255) NOT NULL, 
	code_hash VARCHAR(64) NOT NULL, 
	attempts INTEGER NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX ix_u28_email_changes_user_id ON u28_email_changes (user_id);
CREATE INDEX ix_u28_email_changes_created_at ON u28_email_changes (created_at);
CREATE TABLE u28_task_reminders (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	task_id UUID NOT NULL, 
	due_key VARCHAR(10) NOT NULL, 
	percent INTEGER NOT NULL, 
	status VARCHAR(10) NOT NULL, 
	attempts INTEGER NOT NULL, 
	detail VARCHAR(80) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_u28_reminder_task_due UNIQUE (task_id, due_key), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX ix_u28_task_reminders_user_id ON u28_task_reminders (user_id);
CREATE INDEX ix_u28_task_reminders_task_id ON u28_task_reminders (task_id);
