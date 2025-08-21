from datetime import timedelta

import click
import typed_settings as ts
from loguru import logger
from sqlalchemy import create_engine

from paralysis.model import ProfilerSample, Round
from paralysis.network import make_cached_limiter_session
from paralysis.settings import ParalysisSettings

from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy.orm import Session

@click.command()
@click.option(
    "--settings_file", required=True, help="Location of your settings.toml file."
)
@logger.catch
def main(settings_file):
    settings: ParalysisSettings = ts.load(
        ParalysisSettings, appname="paralysis", config_files=[settings_file]
    )

    logger.add(
        "task_update_profilesamples.log",
        rotation="weekly",
        retention="10 days",
        serialize=True,
    )

    engine = create_engine(settings.connection_string)

    logger.info("getting profile data...")

    with Session(engine, expire_on_commit=False) as session:
        get_profile_data(session, settings)


def get_profile_data(session: Session, settings: ParalysisSettings):
    rq_session = make_cached_limiter_session(settings.cache_db)

    api_url = settings.api_url
    latest_rounds = session.scalars(
        select(Round).order_by(Round.id.desc()).limit(10)
    ).unique()
    latest_round_ids = [x.id for x in latest_rounds]

    for round_id in latest_round_ids:
        for proc_name in settings.profile_proc_paths:
            response = rq_session.get(
                f"{api_url}/profiler/getproc",
                params={"procname": proc_name, "roundid": str(round_id)},
                expire_after=timedelta(hours=1),
            )

            if response.status_code == 200:
                for data in response.json():
                    sample = ProfilerSample(
                        round_id=data["roundId"],
                        sample_time=data["sampleTime"],
                        proc_path=data["procpath"],
                        self_cpu=data["self"],
                        total_cpu=data["total"],
                        real_time=data["real"],
                        overtime=data["over"],
                        proc_calls=data["calls"],
                    )
                    session.add(sample)
                    session.commit()

                logger.info(f"downloaded round_id={round_id} proc_name={proc_name}")
            elif response.status_code == 404:
                logger.info(f"round_id={round_id} missing proc_name={proc_name}")


if __name__ == "__main__":
    main()
