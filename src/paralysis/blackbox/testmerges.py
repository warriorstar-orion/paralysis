from sqlalchemy import create_engine, and_
from sqlalchemy.orm import Session
import pandas as pd
import click
import typed_settings as ts

from paralysis.settings import ParalysisSettings
from paralysis.model import Feedback


def filter_pr(pr):
    def apply(x):
        return {
            "pr": testmerge
            for testmerge in x["data"].values()
            if str(testmerge["number"]) == str(pr)
        }

    return apply


def get_tm_rounds(engine, pr):
    with Session(engine) as session:
        query = (
            session.query(Feedback.round_id, Feedback.json, Feedback.datetime)
            .where(
                and_(
                    Feedback.key_name == "testmerged_prs",
                    Feedback.json["data"].regexp_match(f'"number": "{pr}"'),
                )
            )
            .order_by(Feedback.round_id)
        )
        testmerged_rounds = pd.read_sql_query(query.statement, session.connection())

        return testmerged_rounds


def get(pr: str, connection_string: str):
    engine = create_engine(connection_string)
    tm_rounds = get_tm_rounds(engine, pr)
    tm_rounds = tm_rounds.join(
        pd.json_normalize(tm_rounds.json.map(filter_pr(pr)))
    ).drop(["json"], axis=1)
    unique_rounds = len(tm_rounds.round_id.unique())
    print(tm_rounds.round_id.unique())
    print(f"{unique_rounds} rounds.")


@click.command()
@click.option("--settings", required=True, help="Location of your settings.toml file.")
@click.option("--pr", required=True)
def main(settings: str, pr: str):
    settings: ParalysisSettings = ts.load(
        ParalysisSettings, appname="paralysis", config_files=[settings]
    )

    get(pr, settings.connection_string)
