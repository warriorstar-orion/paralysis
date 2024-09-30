import json

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from paralysis.model import Feedback, LegacyPopulation, Round
from paralysis.network import CachedLimiterSession


class Download:
    @staticmethod
    def download(
        engine: Engine, round_id: str, rq_session: CachedLimiterSession, api_url: str
    ) -> Round | None:
        with Session(engine, expire_on_commit=False) as session:
            if session.get(Round, round_id):
                return False

            mtd = rq_session.get(f"{api_url}/metadata/{round_id}").json()
            pct = rq_session.get(f"{api_url}/playercounts/{round_id}").json()
            bbl = rq_session.get(f"{api_url}/blackbox/{round_id}").json()

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
