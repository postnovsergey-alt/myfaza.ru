"""initial schema — все таблицы из раздела 6 ТЗ

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-26

Схема сгенерирована напрямую из SQLAlchemy-моделей и поэтому гарантированно
им соответствует. Последующие миграции создавайте обычным способом:
    alembic revision --autogenerate -m "описание"
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""CREATE TYPE link_direction AS ENUM ('tg_to_web', 'web_to_tg')""")

    op.execute("""CREATE TYPE source AS ENUM ('telegram', 'web', 'system')""")

    op.execute("""CREATE TYPE flow_level AS ENUM ('spotting', 'light', 'medium', 'heavy')""")

    op.execute("""CREATE TYPE mood AS ENUM ('great', 'good', 'neutral', 'low', 'bad')""")

    op.execute("""CREATE TYPE notification_type AS ENUM ('period_upcoming', 'period_start', 'period_end', 'ovulation', 'log_reminder')""")

    op.execute("""CREATE TYPE channel AS ENUM ('telegram', 'web')""")

    op.execute("""CREATE TYPE notification_status AS ENUM ('pending', 'sent', 'failed', 'skipped')""")

    op.execute("""CREATE TYPE notify_channel AS ENUM ('telegram', 'web', 'both', 'none')""")

    op.execute("""CREATE TYPE theme AS ENUM ('auto', 'light', 'dark')""")

    op.execute("""CREATE TABLE audit_log (
	id BIGSERIAL NOT NULL, 
	user_id UUID, 
	action VARCHAR(64) NOT NULL, 
	ip_hash VARCHAR(64), 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
)""")

    op.execute("""CREATE TABLE users (
	telegram_id BIGINT, 
	telegram_username VARCHAR(64), 
	email VARCHAR(255), 
	password_hash VARCHAR(255), 
	email_verified_at TIMESTAMP WITH TIME ZONE, 
	display_name VARCHAR(64), 
	locale VARCHAR(5) DEFAULT 'ru' NOT NULL, 
	timezone VARCHAR(64) DEFAULT 'Europe/Moscow' NOT NULL, 
	consent_given_at TIMESTAMP WITH TIME ZONE, 
	consent_version VARCHAR(16), 
	onboarding_completed BOOLEAN DEFAULT 'false' NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_users_has_auth_method CHECK (telegram_id IS NOT NULL OR email IS NOT NULL)
)""")

    op.execute("""CREATE UNIQUE INDEX ix_users_email ON users (email)""")

    op.execute("""CREATE UNIQUE INDEX ix_users_telegram_id ON users (telegram_id)""")

    op.execute("""CREATE TABLE account_link_tokens (
	token VARCHAR(64) NOT NULL, 
	user_id UUID NOT NULL, 
	direction link_direction NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	used_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (token), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)""")

    op.execute("""CREATE TABLE cycles (
	user_id UUID NOT NULL, 
	start_date DATE NOT NULL, 
	end_date DATE, 
	cycle_length INTEGER, 
	period_length INTEGER, 
	is_predicted BOOLEAN DEFAULT 'false' NOT NULL, 
	is_anomaly BOOLEAN DEFAULT 'false' NOT NULL, 
	source source NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_cycles_user_start UNIQUE (user_id, start_date), 
	CONSTRAINT ck_cycles_dates CHECK (end_date IS NULL OR end_date >= start_date), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)""")

    op.execute("""CREATE INDEX ix_cycles_user_start_desc ON cycles (user_id, start_date)""")

    op.execute("""CREATE TABLE daily_logs (
	user_id UUID NOT NULL, 
	date DATE NOT NULL, 
	flow flow_level, 
	mood mood, 
	symptoms TEXT[], 
	note VARCHAR(1024), 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_daily_logs_user_date UNIQUE (user_id, date), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)""")

    op.execute("""CREATE INDEX ix_daily_logs_user_date_desc ON daily_logs (user_id, date)""")

    op.execute("""CREATE TABLE notifications (
	user_id UUID NOT NULL, 
	type notification_type NOT NULL, 
	target_date DATE NOT NULL, 
	channel channel NOT NULL, 
	status notification_status DEFAULT 'pending' NOT NULL, 
	error TEXT, 
	sent_at TIMESTAMP WITH TIME ZONE, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_notifications_dedup UNIQUE (user_id, type, target_date, channel), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)""")

    op.execute("""CREATE TABLE push_subscriptions (
	user_id UUID NOT NULL, 
	endpoint TEXT NOT NULL, 
	p256dh TEXT NOT NULL, 
	auth TEXT NOT NULL, 
	user_agent VARCHAR(255), 
	is_active BOOLEAN DEFAULT 'true' NOT NULL, 
	last_success_at TIMESTAMP WITH TIME ZONE, 
	failure_count INTEGER DEFAULT '0' NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	UNIQUE (endpoint)
)""")

    op.execute("""CREATE TABLE sessions (
	user_id UUID NOT NULL, 
	refresh_token_hash VARCHAR(64) NOT NULL, 
	channel channel NOT NULL, 
	device_label VARCHAR(128), 
	ip_hash VARCHAR(64), 
	last_used_at TIMESTAMP WITH TIME ZONE, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	revoked_at TIMESTAMP WITH TIME ZONE, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	UNIQUE (refresh_token_hash)
)""")

    op.execute("""CREATE INDEX ix_sessions_user_active ON sessions (user_id, revoked_at)""")

    op.execute("""CREATE TABLE user_settings (
	user_id UUID NOT NULL, 
	avg_cycle_length INTEGER DEFAULT '28' NOT NULL, 
	avg_period_length INTEGER DEFAULT '5' NOT NULL, 
	luteal_phase_length INTEGER DEFAULT '14' NOT NULL, 
	notify_before_days INTEGER DEFAULT '3' NOT NULL, 
	notify_time TIME WITHOUT TIME ZONE DEFAULT '10:00' NOT NULL, 
	notify_on_start_day BOOLEAN DEFAULT 'true' NOT NULL, 
	notify_period_end BOOLEAN DEFAULT 'true' NOT NULL, 
	notify_ovulation BOOLEAN DEFAULT 'false' NOT NULL, 
	notify_channel notify_channel DEFAULT 'both' NOT NULL, 
	discreet_mode BOOLEAN DEFAULT 'true' NOT NULL, 
	theme theme DEFAULT 'auto' NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (user_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)""")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS user_settings CASCADE")
    op.execute("DROP TABLE IF EXISTS sessions CASCADE")
    op.execute("DROP TABLE IF EXISTS push_subscriptions CASCADE")
    op.execute("DROP TABLE IF EXISTS notifications CASCADE")
    op.execute("DROP TABLE IF EXISTS daily_logs CASCADE")
    op.execute("DROP TABLE IF EXISTS cycles CASCADE")
    op.execute("DROP TABLE IF EXISTS account_link_tokens CASCADE")
    op.execute("DROP TABLE IF EXISTS users CASCADE")
    op.execute("DROP TABLE IF EXISTS audit_log CASCADE")
    op.execute("DROP TYPE IF EXISTS link_direction")
    op.execute("DROP TYPE IF EXISTS source")
    op.execute("DROP TYPE IF EXISTS flow_level")
    op.execute("DROP TYPE IF EXISTS mood")
    op.execute("DROP TYPE IF EXISTS notification_type")
    op.execute("DROP TYPE IF EXISTS channel")
    op.execute("DROP TYPE IF EXISTS notification_status")
    op.execute("DROP TYPE IF EXISTS notify_channel")
    op.execute("DROP TYPE IF EXISTS theme")
