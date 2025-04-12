from datetime import timedelta

import click
from loguru import logger
from sqlalchemy import create_engine
import typed_settings as ts

from paralysis.model import Round
from paralysis.network import make_cached_limiter_session
from paralysis.settings import ParalysisSettings


def sync_blackbox_database(
    connection_string: str, api_url: str, cache_db: str, enable_logging: bool
):
    if enable_logging:
        logger.add(
            "paralysis_sync_blackbox.log",
            rotation="weekly",
            retention="10 days",
            serialize=True,
        )
    rq_session = make_cached_limiter_session(cache_db)

    engine = create_engine(connection_string)
    logger.info("getting roundstats...")
    rounds = rq_session.get(
        f"{api_url}/stats/roundlist", expire_after=timedelta(hours=1)
    ).json()
    for round in rounds:
        round_id = round["round_id"]
        logger.info(f"round_id={round_id}")
        downloaded = Round.download(engine, round_id, rq_session, api_url)
        if downloaded:
            logger.info(f"downloaded round_id={round_id}")


@click.command()
@click.option("--settings", required=True, help="Location of your settings.toml file.")
@logger.catch
def main(settings):
    settings: ParalysisSettings = ts.load(
        ParalysisSettings, appname="paralysis", config_files=[settings]
    )

    sync_blackbox_database(
        settings.connection_string,
        settings.api_url,
        settings.cache_db,
        settings.log_tasks,
    )
