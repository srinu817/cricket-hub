"""add reusable team, player, and series master data

Revision ID: d3a9c1e7f421
Revises: b6689a49b090
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d3a9c1e7f421"
down_revision: Union[str, Sequence[str], None] = "b6689a49b090"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "teams",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("short_name", sa.String(length=10), nullable=False),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("category", sa.String(length=60), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_teams_name_lower", "teams", [sa.text("lower(name)")], unique=True)
    op.create_index("uq_teams_short_name_lower", "teams", [sa.text("lower(short_name)")], unique=True)

    op.create_table(
        "series",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("category", sa.String(length=60), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_series_name_lower", "series", [sa.text("lower(name)")], unique=True)

    op.create_table(
        "players",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=True),
        sa.Column("playing_role", sa.String(length=30), nullable=False),
        sa.Column("batting_style", sa.String(length=60), nullable=True),
        sa.Column("bowling_style", sa.String(length=80), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_players_full_name_lower", "players", [sa.text("lower(full_name)")], unique=False)

    op.create_table(
        "player_team_memberships",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("team_id", sa.String(length=36), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["player_id"],
            ["players.id"],
            name="fk_player_team_memberships_player_id_players",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["teams.id"],
            name="fk_player_team_memberships_team_id_teams",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_player_team_active_membership",
        "player_team_memberships",
        ["player_id", "team_id"],
        unique=True,
        postgresql_where=sa.text("is_active"),
        sqlite_where=sa.text("is_active = 1"),
    )

    op.create_table(
        "series_team_memberships",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("series_id", sa.String(length=36), nullable=False),
        sa.Column("team_id", sa.String(length=36), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["series_id"],
            ["series.id"],
            name="fk_series_team_memberships_series_id_series",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["teams.id"],
            name="fk_series_team_memberships_team_id_teams",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_series_team_active_membership",
        "series_team_memberships",
        ["series_id", "team_id"],
        unique=True,
        postgresql_where=sa.text("is_active"),
        sqlite_where=sa.text("is_active = 1"),
    )

    with op.batch_alter_table("matches") as batch_op:
        batch_op.add_column(sa.Column("series_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("team1_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("team2_id", sa.String(length=36), nullable=True))
        batch_op.create_foreign_key(
            "fk_matches_series_id_series",
            "series",
            ["series_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_foreign_key(
            "fk_matches_team1_id_teams",
            "teams",
            ["team1_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_foreign_key(
            "fk_matches_team2_id_teams",
            "teams",
            ["team2_id"],
            ["id"],
            ondelete="RESTRICT",
        )
    op.create_index("ix_matches_series_id", "matches", ["series_id"])
    op.create_index("ix_matches_team1_id", "matches", ["team1_id"])
    op.create_index("ix_matches_team2_id", "matches", ["team2_id"])

    with op.batch_alter_table("batting_entries") as batch_op:
        batch_op.add_column(sa.Column("player_id", sa.String(length=36), nullable=True))
        batch_op.create_foreign_key(
            "fk_batting_entries_player_id_players",
            "players",
            ["player_id"],
            ["id"],
            ondelete="RESTRICT",
        )
    op.create_index("ix_batting_entries_player_id", "batting_entries", ["player_id"])

    with op.batch_alter_table("bowling_entries") as batch_op:
        batch_op.add_column(sa.Column("player_id", sa.String(length=36), nullable=True))
        batch_op.create_foreign_key(
            "fk_bowling_entries_player_id_players",
            "players",
            ["player_id"],
            ["id"],
            ondelete="RESTRICT",
        )
    op.create_index("ix_bowling_entries_player_id", "bowling_entries", ["player_id"])


def downgrade() -> None:
    raise RuntimeError("This master-data migration is forward-only to protect linked cricket records.")
