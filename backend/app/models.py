import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base


class AdminUser(Base):
    __tablename__ = "admin_users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)


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
    date: Mapped[date] = mapped_column(Date, nullable=False)
    time: Mapped[str] = mapped_column(String(50), nullable=False)
    venue: Mapped[str] = mapped_column(String(160), nullable=False)
    format: Mapped[str] = mapped_column(String(40), nullable=False)
    result: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    toss: Mapped[str] = mapped_column(String(500), nullable=False, default="")

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
