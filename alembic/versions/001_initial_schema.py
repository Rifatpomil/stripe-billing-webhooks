"""Initial schema with tables and subscription state transition trigger.

Revision ID: 001
Revises:
Create Date: 2024-01-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Valid subscription state transitions (from -> to)
VALID_TRANSITIONS_SQL = """
(
    ('incomplete', 'active'),
    ('incomplete', 'canceled'),
    ('incomplete', 'incomplete_expired'),
    ('trialing', 'active'),
    ('trialing', 'canceled'),
    ('trialing', 'past_due'),
    ('active', 'past_due'),
    ('active', 'canceled'),
    ('active', 'trialing'),
    ('past_due', 'active'),
    ('past_due', 'canceled'),
    ('past_due', 'unpaid'),
    ('unpaid', 'canceled'),
    ('unpaid', 'active')
)
"""


def upgrade() -> None:
    op.create_table(
        "webhook_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.String(255), nullable=False),
        sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column("raw_payload", sa.Text(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processing_status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_webhook_events_event_id", "webhook_events", ["event_id"], unique=True)
    op.create_index("ix_webhook_events_event_type", "webhook_events", ["event_type"], unique=False)

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("stripe_subscription_id", sa.String(255), nullable=False),
        sa.Column("stripe_customer_id", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("previous_status", sa.String(32), nullable=True),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_subscriptions_stripe_subscription_id", "subscriptions", ["stripe_subscription_id"], unique=True)
    op.create_index("ix_subscriptions_stripe_customer_id", "subscriptions", ["stripe_customer_id"], unique=False)
    op.create_index("ix_subscriptions_status", "subscriptions", ["status"], unique=False)

    op.create_table(
        "subscription_state_transitions",
        sa.Column("from_status", sa.String(32), nullable=False),
        sa.Column("to_status", sa.String(32), nullable=False),
        sa.PrimaryKeyConstraint("from_status", "to_status"),
    )
    op.execute(
        f"""
        INSERT INTO subscription_state_transitions (from_status, to_status) VALUES
        ('incomplete', 'active'),
        ('incomplete', 'canceled'),
        ('incomplete', 'incomplete_expired'),
        ('trialing', 'active'),
        ('trialing', 'canceled'),
        ('trialing', 'past_due'),
        ('active', 'past_due'),
        ('active', 'canceled'),
        ('active', 'trialing'),
        ('past_due', 'active'),
        ('past_due', 'canceled'),
        ('past_due', 'unpaid'),
        ('unpaid', 'canceled'),
        ('unpaid', 'active')
        """
    )

    op.create_table(
        "ledger_entries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("subscription_id", sa.Integer(), nullable=True),
        sa.Column("stripe_customer_id", sa.String(255), nullable=False),
        sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column("stripe_event_id", sa.String(255), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=True),
        sa.Column("currency", sa.String(3), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["subscription_id"], ["subscriptions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ledger_entries_subscription_id", "ledger_entries", ["subscription_id"], unique=False)
    op.create_index("ix_ledger_entries_stripe_customer_id", "ledger_entries", ["stripe_customer_id"], unique=False)
    op.create_index("ix_ledger_entries_event_type", "ledger_entries", ["event_type"], unique=False)
    op.create_index("ix_ledger_entries_stripe_event_id", "ledger_entries", ["stripe_event_id"], unique=False)

    op.create_table(
        "webhook_retry_queue",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.String(255), nullable=False),
        sa.Column("raw_payload", sa.Text(), nullable=False),
        sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_webhook_retry_queue_event_id", "webhook_retry_queue", ["event_id"], unique=True)
    op.create_index("ix_webhook_retry_queue_next_retry_at", "webhook_retry_queue", ["next_retry_at"], unique=False)

    op.create_table(
        "webhook_dlq",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.String(255), nullable=False),
        sa.Column("raw_payload", sa.Text(), nullable=False),
        sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column("final_error", sa.Text(), nullable=True),
        sa.Column("failed_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_webhook_dlq_event_id", "webhook_dlq", ["event_id"], unique=True)

    op.create_table(
        "usage_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("stripe_customer_id", sa.String(255), nullable=False),
        sa.Column("stripe_subscription_item_id", sa.String(255), nullable=False),
        sa.Column("meter_name", sa.String(128), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_usage_records_stripe_customer_id", "usage_records", ["stripe_customer_id"], unique=False)
    op.create_index("ix_usage_records_stripe_subscription_item_id", "usage_records", ["stripe_subscription_item_id"], unique=False)
    op.create_index("ix_usage_records_meter_name", "usage_records", ["meter_name"], unique=False)

    # Trigger: validate subscription state transitions
    op.execute("""
        CREATE OR REPLACE FUNCTION validate_subscription_state_transition()
        RETURNS TRIGGER AS $$
        BEGIN
            -- INSERT: allow any valid status (first state)
            IF TG_OP = 'INSERT' THEN
                IF NEW.status NOT IN (
                    'trialing', 'active', 'past_due', 'canceled', 'unpaid',
                    'incomplete', 'incomplete_expired'
                ) THEN
                    RAISE EXCEPTION 'Invalid subscription status: %', NEW.status
                        USING ERRCODE = 'check_violation';
                END IF;
                RETURN NEW;
            END IF;

            -- UPDATE: validate transition
            IF TG_OP = 'UPDATE' AND OLD.status IS DISTINCT FROM NEW.status THEN
                IF NOT EXISTS (
                    SELECT 1 FROM subscription_state_transitions
                    WHERE from_status = OLD.status AND to_status = NEW.status
                ) THEN
                    RAISE EXCEPTION 'Invalid subscription status transition: % -> %',
                        OLD.status, NEW.status
                        USING ERRCODE = 'check_violation';
                END IF;
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER validate_subscription_state_transition_trigger
        BEFORE INSERT OR UPDATE ON subscriptions
        FOR EACH ROW
        EXECUTE FUNCTION validate_subscription_state_transition();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS validate_subscription_state_transition_trigger ON subscriptions;")
    op.execute("DROP FUNCTION IF EXISTS validate_subscription_state_transition();")

    op.drop_table("usage_records")
    op.drop_table("webhook_dlq")
    op.drop_table("webhook_retry_queue")
    op.drop_table("ledger_entries")
    op.drop_table("subscription_state_transitions")
    op.drop_table("subscriptions")
    op.drop_table("webhook_events")
