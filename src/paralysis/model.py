from functools import cache
import json
from typing import List, Optional

# coding: utf-8
from sqlalchemy import (
    CHAR,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.mysql import INTEGER, JSON, MEDIUMTEXT, SMALLINT, TINYINT
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, mapped_column, relationship, Session
from sqlalchemy import Engine

from paralysis.network import CachedLimiterSession

Base = declarative_base()
metadata = Base.metadata


class Death(Base):
    __tablename__ = "death"

    id = Column(INTEGER(11), primary_key=True)
    pod = Column(Text, nullable=False, comment="Place of death")
    coord = Column(Text, nullable=False, comment="X, Y, Z POD")
    tod = Column(DateTime, nullable=False, comment="Time of death")
    death_rid = Column(INTEGER(11))
    server_id = Column(Text)
    job = Column(Text, nullable=False)
    special = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
    byondkey = Column(Text, nullable=False)
    laname = Column(Text, nullable=False, comment="Last attacker name")
    lakey = Column(Text, nullable=False, comment="Last attacker key")
    gender = Column(Text, nullable=False)
    bruteloss = Column(INTEGER(11), nullable=False)
    brainloss = Column(INTEGER(11), nullable=False)
    fireloss = Column(INTEGER(11), nullable=False)
    oxyloss = Column(INTEGER(11), nullable=False)


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(INTEGER(11), primary_key=True)
    datetime = Column(DateTime, nullable=False)
    round_id: Mapped[int] = mapped_column(ForeignKey("round.id"))
    key_name = Column(String(32), nullable=False)
    key_type = Column(
        Enum(
            "text",
            "amount",
            "tally",
            "nested tally",
            "associative",
            "ledger",
            "nested ledger",
        ),
        nullable=False,
    )
    version = Column(TINYINT(3), nullable=False)
    json = Column(JSON, nullable=False)

    round: Mapped["Round"] = relationship(back_populates="feedbacks")

    def __str__(self):
        return f"<Fdbk Rnd#{self.round_id} {self.key_name}>"

    def __repr__(self):
        return self.__str__()

    def __getitem__(self, key):
        return self.json["data"].__getitem__(key)

    def get(self, key, default=None):
        return self.json["data"].get(key, default)

    @cache
    def json_data(self):
        return self.json["data"]

    def keys(self):
        return self.json_data().keys()

    def values(self):
        return self.json_data().values()

    def items(self):
        return self.json_data().items()


class LegacyPopulation(Base):
    __tablename__ = "legacy_population"

    id = Column(INTEGER(11), primary_key=True)
    playercount = Column(INTEGER(11))
    admincount = Column(INTEGER(11))
    server_id = Column(String(50))
    time = Column(DateTime, nullable=False)
    round = relationship(
        "Round",
        primaryjoin="and_(LegacyPopulation.time>=foreign(Round.initialize_datetime), LegacyPopulation.time<=foreign(Round.shutdown_datetime))",
        back_populates="populations",
        viewonly=True,
        uselist=False,
    )

    def __str__(self):
        return f"<Players {self.playercount: >3}@{self.time.strftime('%Y-%m-%d %H:%M:%S')}>"

    def __repr__(self):
        return self.__str__()


class Library(Base):
    __tablename__ = "library"

    id = Column(INTEGER(11), primary_key=True)
    author = Column(MEDIUMTEXT, nullable=False)
    title = Column(MEDIUMTEXT, nullable=False)
    content = Column(MEDIUMTEXT, nullable=False)
    ckey = Column(String(32, "utf8mb4_unicode_ci"), nullable=False, index=True)
    reports = Column(MEDIUMTEXT, nullable=False, index=True)
    summary = Column(MEDIUMTEXT, nullable=False)
    rating = Column(Float(asdecimal=True), server_default=text("0"))
    raters = Column(MEDIUMTEXT, nullable=False)
    primary_category = Column(INTEGER(11), server_default=text("0"))
    secondary_category = Column(INTEGER(11), nullable=False, server_default=text("0"))
    tertiary_category = Column(INTEGER(11), server_default=text("0"))


class Round(Base):
    __tablename__ = "round"

    id: Mapped[int] = mapped_column(primary_key=True)
    initialize_datetime = Column(DateTime, nullable=False)
    start_datetime = Column(DateTime)
    shutdown_datetime = Column(DateTime)
    end_datetime = Column(DateTime)
    server_ip = Column(INTEGER(10), nullable=False)
    server_port = Column(SMALLINT(5), nullable=False)
    commit_hash = Column(CHAR(40))
    game_mode = Column(String(32))
    game_mode_result = Column(String(64))
    end_state = Column(String(64))
    shuttle_name = Column(String(64))
    map_name = Column(String(32))
    station_name = Column(String(80))
    server_id = Column(String(50))

    feedbacks: Mapped[List["Feedback"]] = relationship(
        back_populates="round", innerjoin=True, lazy="joined"
    )
    populations: Mapped[List["LegacyPopulation"]] = relationship(
        "LegacyPopulation",
        primaryjoin="and_(LegacyPopulation.time>=Round.initialize_datetime, LegacyPopulation.time<=Round.shutdown_datetime)",
        foreign_keys=[initialize_datetime, shutdown_datetime],
        viewonly=True,
        uselist=True,
    )

    def __repr__(self):
        return f"<Round#{self.id} [{self.start_datetime.strftime('%Y-%m-%d')}] {self.game_mode}/{self.map_name}>"

    @staticmethod
    def download(
        engine: Engine, round_id: str, rq_session: CachedLimiterSession, api_url: str
    ) -> Optional["Round"]:
        with Session(engine, expire_on_commit=False) as session:
            if session.get(Round, round_id):
                return False

            mtd = rq_session.get(f"{api_url}/stats/metadata/{round_id}").json()
            pct = rq_session.get(f"{api_url}/stats/playercounts/{round_id}").json()
            bbl = rq_session.get(f"{api_url}/stats/blackbox/{round_id}").json()

            rnd = Round(
                id=mtd["round_id"],
                initialize_datetime=mtd["init_datetime"],
                start_datetime=mtd["start_datetime"],
                shutdown_datetime=mtd["shutdown_datetime"],
                end_datetime=mtd["end_datetime"],
                commit_hash=mtd["commit_hash"],
                game_mode=mtd["game_mode"],
                game_mode_result=mtd["game_mode_result"],
                end_state=mtd["end_state"],
                map_name=mtd["map_name"],
                server_id=mtd["server_id"],
                server_ip=0,
                server_port=0,
            )
            pcts = list()
            for dt, ct in pct.items():
                lp = LegacyPopulation(
                    playercount=ct, admincount=0, server_id=mtd["server_id"], time=dt
                )
                pcts.append(lp)
            data = list()
            for row in bbl:
                fb = Feedback(
                    round_id=mtd["round_id"],
                    key_name=row["key_name"],
                    key_type=row["key_type"],
                    version=row["version"],
                    json=json.loads(row["raw_data"]),
                    datetime=mtd["init_datetime"],
                )
                data.append(fb)

            session.add_all([rnd] + pcts + data)
            session.commit()

            return rnd

    def feedback(self, k):
        for x in self.feedbacks:
            if x.key_name == k:
                return x

    def has_feedback(self, name):
        return any(x.key_name == name for x in self.feedbacks)

    def roundstart_ready_count(self, with_assts=False):
        if not self.has_feedback("job_preferences"):
            return None

        if with_assts:
            return self.feedback("job_preferences")["Nanotrasen Navy Officer"]["never"]

        return self.feedback("job_preferences")["Assistant"]["never"]

    def has_testmerge(self, pr_id):
        if self.has_feedback("testmerged_prs"):
            tprs = self.feedback("testmerged_prs")
            for pr in tprs.values():
                if pr["number"] == str(pr_id):
                    return True

        return False

    @property
    def roundstart_client_count(self):
        return sorted(self.populations, key=lambda x: x.time)[0].playercount

    @property
    def highest_player_count(self):
        return max(p.playercount for p in self.populations)

    def roundstart_job_count(self, with_assts=False):
        if with_assts:
            return sum(
                [y.get("roundstart", 0) for x, y in self.feedback("manifest").items()]
            )
        return sum(
            [
                y.get("roundstart", 0)
                for x, y in self.feedback("manifest").items()
                if x != "Assistant"
            ]
        )
