from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator
from pydantic.alias_generators import to_camel
from typing_extensions import Annotated


TeamCode = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10)]
TextEntry = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class BattingEntryInput(BaseModel):
    model_config = ConfigDict(extra="forbid", alias_generator=to_camel, populate_by_name=True)

    player: TextEntry
    dismissal: Annotated[str, StringConstraints(max_length=150)]
    runs: int = Field(ge=0)
    balls: int = Field(ge=0)
    fours: int = Field(ge=0)
    sixes: int = Field(ge=0)


class BowlingEntryInput(BaseModel):
    model_config = ConfigDict(extra="forbid", alias_generator=to_camel, populate_by_name=True)

    player: TextEntry
    overs: Annotated[str, StringConstraints(pattern=r"^\d+(\.\d)?$", max_length=40)]
    maidens: int = Field(ge=0)
    runs: int = Field(ge=0)
    wickets: int = Field(ge=0)


class InningsInput(BaseModel):
    model_config = ConfigDict(extra="forbid", alias_generator=to_camel, populate_by_name=True)

    team_code: TeamCode
    total: Annotated[str, StringConstraints(max_length=40)] = ""
    overs: Annotated[str, StringConstraints(max_length=40)] = ""
    batting: list[BattingEntryInput] = Field(default_factory=list, max_length=30)
    bowling: list[BowlingEntryInput] = Field(default_factory=list, max_length=20)


class MatchInput(BaseModel):
    model_config = ConfigDict(extra="forbid", alias_generator=to_camel, populate_by_name=True)

    id: str | None = None
    series: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
    stage: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
    status: Literal["Upcoming", "Completed"]
    team1: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    team1_code: TeamCode
    team2: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    team2_code: TeamCode
    date: date
    time: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
    venue: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
    format: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
    result: Annotated[str, StringConstraints(max_length=500)] = ""
    toss: Annotated[str, StringConstraints(max_length=500)] = ""
    innings: list[InningsInput] = Field(default_factory=list, max_length=4)
    commentary: list[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]] = Field(default_factory=list, max_length=200)

    @model_validator(mode="after")
    def validate_match_details(self):
        if self.team1_code == self.team2_code:
            raise ValueError("A match must have two different teams")
        if any(innings.team_code not in (self.team1_code, self.team2_code) for innings in self.innings):
            raise ValueError("Each innings team must be one of the match teams")
        return self


class LoginInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=254)]
    password: Annotated[str, StringConstraints(min_length=1, max_length=256)]


class BattingEntryOut(BattingEntryInput):
    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel, populate_by_name=True)


class BowlingEntryOut(BowlingEntryInput):
    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel, populate_by_name=True)


class InningsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel, populate_by_name=True)

    team_code: str
    total: str
    overs: str
    batting: list[BattingEntryOut]
    bowling: list[BowlingEntryOut]


class MatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel, populate_by_name=True)

    id: str
    series: str
    stage: str
    status: str
    team1: str
    team1_code: str
    team2: str
    team2_code: str
    date: date
    time: str
    venue: str
    format: str
    result: str
    toss: str
    innings: list[InningsOut]
    commentary: list[str]

    @field_validator("commentary", mode="before")
    @classmethod
    def flatten_commentary(cls, value):
        return [entry if isinstance(entry, str) else entry.text for entry in value]
