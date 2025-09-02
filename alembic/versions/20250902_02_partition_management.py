"""partition management function and seed partitions

Revision ID: 20250902_02
Revises: 20250902_01
Create Date: 2025-09-02
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250902_02'
down_revision = '20250902_01'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create helper function to ensure daily range partitions for traffic_rollups_hourly
    op.execute(
        """
        CREATE OR REPLACE FUNCTION ensure_traffic_rollups_hourly_partitions(start_date date, end_date date)
        RETURNS void LANGUAGE plpgsql AS $$
        DECLARE
            d date;
            part_name text;
        BEGIN
            IF end_date <= start_date THEN
                RAISE EXCEPTION 'end_date must be greater than start_date';
            END IF;
            d := start_date;
            WHILE d < end_date LOOP
                part_name := format('traffic_rollups_hourly_%s', to_char(d, 'YYYYMMDD'));
                EXECUTE format(
                    'CREATE TABLE IF NOT EXISTS %I PARTITION OF traffic_rollups_hourly FOR VALUES FROM (%L) TO (%L);',
                    part_name,
                    d,
                    d + 1
                );
                d := d + 1;
            END LOOP;
        END;
        $$;
        """
    )

    # Seed partitions: yesterday (for late arriving) through +30 days
    op.execute(
        "SELECT ensure_traffic_rollups_hourly_partitions(CURRENT_DATE - INTERVAL '1 day', CURRENT_DATE + INTERVAL '31 days');"
    )

    # (Optional) Create a simple view listing existing partitions for observability
    op.execute(
        """
        CREATE OR REPLACE VIEW traffic_rollups_hourly_partitions AS
        SELECT inhrelid::regclass AS partition_table,
               pg_catalog.pg_get_expr(pg_class.relpartbound, pg_class.oid) AS bounds
        FROM pg_inherits
        JOIN pg_class ON pg_class.oid = inhrelid
        JOIN pg_class parent ON parent.oid = inhparent
        WHERE parent.relname = 'traffic_rollups_hourly';
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS traffic_rollups_hourly_partitions;")
    op.execute("DROP FUNCTION IF EXISTS ensure_traffic_rollups_hourly_partitions(date, date);")
    # NOTE: Partitions themselves are left in place (safe); remove manually if required.

