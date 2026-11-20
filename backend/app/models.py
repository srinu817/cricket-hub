import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base


class AdminUser(Base):
    __tablename__ = "admin_users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)


class Team(Base):
    __tablename__ = "teams"
    __table_args__ = (
        Index("uq_teams_name_lower", text("lower(name)"), unique=True),
        Index("uq_teams_short_name_lower", text("lower(short_name)"), unique=True),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    short_name: Mapped[str] = mapped_column(String(10), nullable=False)
    country: Mapped[str | None] = mapped_column(String(100))
    category: Mapped[str | None] = mapped_column(String(60))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    player_memberships: Mapped[list["PlayerTeamMembership"]] = relationship(back_populates="team")


class Series(Base):
    __tablename__ = "series"
    __table_args__ = (Index("uq_series_name_lower", text("lower(name)"), unique=True),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str | None] = mapped_column(String(60))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    team_memberships: Mapped[list["SeriesTeamMembership"]] = relationship(back_populates="series")

    @property
    def team_ids(self) -> list[str]:
        return [membership.team_id for membership in self.team_memberships if membership.is_active]


class Player(Base):
    __tablename__ = "players"
    __table_args__ = (Index("ix_players_full_name_lower", text("lower(full_name)")),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(100))
    playing_role: Mapped[str] = mapped_column(String(30), nullable=False)
    batting_style: Mapped[str | None] = mapped_column(String(60))
    bowling_style: Mapped[str | None] = mapped_column(String(80))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    team_memberships: Mapped[list["PlayerTeamMembership"]] = relationship(back_populates="player")

    @property
    def team_ids(self) -> list[str]:
        return [membership.team_id for membership in self.team_memberships if membership.is_active]


class PlayerTeamMembership(Base):
    __tablename__ = "player_team_memberships"
    __table_args__ = (
        Index(
            "uq_player_team_active_membership",
            "player_id",
            "team_id",
            unique=True,
            postgresql_where=text("is_active"),
            sqlite_where=text("is_active = 1"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    player_id: Mapped[str] = mapped_column(
        ForeignKey("players.id", name="fk_player_team_memberships_player_id_players", ondelete="RESTRICT"),
        nullable=False,
    )
    team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.id", name="fk_player_team_memberships_team_id_teams", ondelete="RESTRICT"),
        nullable=False,
    )
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    player: Mapped[Player] = relationship(back_populates="team_memberships")
    team: Mapped[Team] = relationship(back_populates="player_memberships")


class SeriesTeamMembership(Base):
    __tablename__ = "series_team_memberships"
    __table_args__ = (
        Index(
            "uq_series_team_active_membership",
            "series_id",
            "team_id",
            unique=True,
            postgresql_where=text("is_active"),
            sqlite_where=text("is_active = 1"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    series_id: Mapped[str] = mapped_column(
        ForeignKey("series.id", name="fk_series_team_memberships_series_id_series", ondelete="RESTRICT"),
        nullable=False,
    )
    team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.id", name="fk_series_team_memberships_team_id_teams", ondelete="RESTRICT"),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    series: Mapped[Series] = relationship(back_populates="team_memberships")


class Match(Base):
    __tablename__ = "matches"
    __table_args__ = (
        Index("ix_matches_date_status", "date", "status"),
        Index("ix_matches_team1_code", "team1_code"),
        Index("ix_matches_team2_code", "team2_code"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    series: Mapped[str] = mapped_column(String(160), nullable=False)
    stage: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    team1: Mapped[str] = mapped_column(String(100), nullable=False)
    team1_code: Mapped[str] = mapped_column(String(10), nullable=False)
    team2: Mapped[str] = mapped_column(String(100), nullable=False)
    team2_code: Mapped[str] = mapped_column(String(10), nullable=False)
    series_id: Mapped[str | None] = mapped_column(
        ForeignKey("series.id", name="fk_matches_series_id_series", ondelete="RESTRICT"),
        index=True,
    )
    team1_id: Mapped[str | None] = mapped_column(
        ForeignKey("teams.id", name="fk_matches_team1_id_teams", ondelete="RESTRICT"),
        index=True,
    )
    team2_id: Mapped[str | None] = mapped_column(
        ForeignKey("teams.id", name="fk_matches_team2_id_teams", ondelete="RESTRICT"),
        index=True,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    time: Mapped[str] = mapped_column(String(50), nullable=False)
    venue: Mapped[str] = mapped_column(String(160), nullable=False)
    format: Mapped[str] = mapped_column(String(40), nullable=False)
    result: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    toss: Mapped[str] = mapped_column(String(500), nullable=False, default="")

    series_master: Mapped[Series | None] = relationship()
    team1_master: Mapped[Team | None] = relationship(foreign_keys=[team1_id])
    team2_master: Mapped[Team | None] = relationship(foreign_keys=[team2_id])
    innings: Mapped[list["Innings"]] = relationship(
        back_populates="match",
        cascade="all, delete-orphan",
        order_by="Innings.innings_number",
    )
    commentary: Mapped[list["Commentary"]] = relationship(
        back_populates="match",
        cascade="all, delete-orphan",
        order_by="Commentary.position",
    )


class Innings(Base):
    __tablename__ = "innings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[str] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"), nullable=False)
    innings_number: Mapped[int] = mapped_column(Integer, nullable=False)
    team_code: Mapped[str] = mapped_column(String(10), nullable=False)
    total: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    overs: Mapped[str] = mapped_column(String(40), nullable=False, default="")

    match: Mapped[Match] = relationship(back_populates="innings")
    batting: Mapped[list["BattingEntry"]] = relationship(
        back_populates="innings",
        cascade="all, delete-orphan",
        order_by="BattingEntry.position",
    )
    bowling: Mapped[list["BowlingEntry"]] = relationship(
        back_populates="innings",
        cascade="all, delete-orphan",
        order_by="BowlingEntry.position",
    )


class BattingEntry(Base):
    __tablename__ = "batting_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    innings_id: Mapped[int] = mapped_column(ForeignKey("innings.id", ondelete="CASCADE"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    player: Mapped[str] = mapped_column(String(100), nullable=False)
    player_id: Mapped[str | None] = mapped_column(
        ForeignKey("players.id", name="fk_batting_entries_player_id_players", ondelete="RESTRICT"),
        index=True,
    )
    dismissal: Mapped[str] = mapped_column(String(150), nullable=False)
    runs: Mapped[int] = mapped_column(Integer, nullable=False)
    balls: Mapped[int] = mapped_column(Integer, nullable=False)
    fours: Mapped[int] = mapped_column(Integer, nullable=False)
    sixes: Mapped[int] = mapped_column(Integer, nullable=False)

    innings: Mapped[Innings] = relationship(back_populates="batting")


class BowlingEntry(Base):
    __tablename__ = "bowling_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    innings_id: Mapped[int] = mapped_column(ForeignKey("innings.id", ondelete="CASCADE"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    player: Mapped[str] = mapped_column(String(100), nullable=False)
    player_id: Mapped[str | None] = mapped_column(
        ForeignKey("players.id", name="fk_bowling_entries_player_id_players", ondelete="RESTRICT"),
        index=True,
    )
    overs: Mapped[str] = mapped_column(String(40), nullable=False)
    maidens: Mapped[int] = mapped_column(Integer, nullable=False)
    runs: Mapped[int] = mapped_column(Integer, nullable=False)
    wickets: Mapped[int] = mapped_column(Integer, nullable=False)

    innings: Mapped[Innings] = relationship(back_populates="bowling")


class Commentary(Base):
    __tablename__ = "commentary"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[str] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(String(500), nullable=False)

    match: Mapped[Match] = relationship(back_populates="commentary")
