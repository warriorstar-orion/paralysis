import click
from loguru import logger

from paralysis.model import Base
from paralysis.settings import make_engine


@click.command()
@click.option("--settings", required=True, help="Location of your settings.toml file.")
def main(settings):
    logger.info("Attempting to create database tables.")
    engine = make_engine(settings)
    Base.metadata.create_all(engine)
    logger.info("Created database tables.")
