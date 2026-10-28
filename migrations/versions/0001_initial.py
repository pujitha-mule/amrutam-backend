"""initial schema"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("mfa_secret_encrypted", sa.String(255)),
        sa.Column("mfa_enabled", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "profiles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("phone", sa.String(20)),
        sa.Column("city", sa.String(100)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_profiles_city", "profiles", ["city"])

    op.create_table(
        "doctors",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("specialty", sa.String(100), nullable=False),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column(
            "languages",
            postgresql.ARRAY(sa.String),
            nullable=False,
            server_default=sa.text("'{}'::varchar[]"),
        ),
        sa.Column("consultation_type", sa.String(20), nullable=False, server_default="video"),
        sa.Column("license_number", sa.String(100), nullable=False),
        sa.Column("is_verified", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("bio", sa.String(1000)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_doctors_specialty", "doctors", ["specialty"])
    op.create_index("ix_doctors_city", "doctors", ["city"])

    op.create_table(
        "availability_slots",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "doctor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("doctors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_booked", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("version", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("end_time > start_time", name="ck_slot_times"),
        sa.UniqueConstraint("doctor_id", "start_time", name="uq_doctor_start"),
    )
    op.execute(
        "ALTER TABLE availability_slots ADD CONSTRAINT ex_slot_overlap "
        "EXCLUDE USING gist (doctor_id WITH =, "
        "tstzrange(start_time, end_time) WITH &&)"
    )
    op.create_index("ix_slots_doctor_start", "availability_slots", ["doctor_id", "start_time"])

    op.create_table(
        "consultations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column(
            "doctor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("doctors.id"), nullable=False
        ),
        sa.Column(
            "slot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("availability_slots.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="BOOKED"),
        sa.Column("status_updated_at", sa.DateTime(timezone=True)),
        sa.Column("status_updated_by", postgresql.UUID(as_uuid=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_consult_patient", "consultations", ["patient_id"])
    op.create_index("ix_consult_doctor", "consultations", ["doctor_id"])
    op.create_index("ix_consult_status", "consultations", ["status"])
    op.execute(
        "CREATE UNIQUE INDEX ux_slot_active_consultation ON consultations (slot_id) "
        "WHERE status IN ('BOOKED','CONFIRMED','IN_PROGRESS')"
    )

    op.create_table(
        "prescriptions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "consultation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("consultations.id"),
            nullable=False,
        ),
        sa.Column(
            "patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column(
            "doctor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("doctors.id"), nullable=False
        ),
        sa.Column("medication", sa.String(200), nullable=False),
        sa.Column("strength", sa.String(50), nullable=False),
        sa.Column("dosage", sa.String(100), nullable=False),
        sa.Column("frequency", sa.String(100), nullable=False),
        sa.Column("duration", sa.String(100), nullable=False),
        sa.Column("instructions", sa.Text),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column(
            "issued_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_rx_patient", "prescriptions", ["patient_id"])

    op.create_table(
        "payments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "consultation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("consultations.id"),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("provider_reference", sa.String(200)),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("amount > 0", name="ck_payment_amount"),
    )
    op.create_index("ix_payments_status", "payments", ["status"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True)),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True)),
        sa.Column("outcome", sa.String(20), nullable=False),
        sa.Column("request_id", sa.String(100)),
        sa.Column("metadata", postgresql.JSONB),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_audit_action", "audit_logs", ["action"])

    op.create_table(
        "idempotency_keys",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("key", sa.String(200), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("response_status", sa.Integer),
        sa.Column("response_body", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "key", name="uq_idem_user_key"),
    )

    op.create_table(
        "outbox_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("aggregate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("processed_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_outbox_processed", "outbox_events", ["processed_at"])

    op.create_table(
        "refresh_tokens",
        sa.Column("jti", sa.String(64), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("revoked", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "processed_webhooks",
        sa.Column("provider_event_id", sa.String(200), primary_key=True),
        sa.Column(
            "received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )


def downgrade() -> None:
    for t in [
        "processed_webhooks",
        "refresh_tokens",
        "outbox_events",
        "idempotency_keys",
        "audit_logs",
        "payments",
        "prescriptions",
        "consultations",
        "availability_slots",
        "doctors",
        "profiles",
        "users",
    ]:
        op.drop_table(t)
