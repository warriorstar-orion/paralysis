from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy import Engine
import typed_settings as ts

@ts.settings(frozen=True)
class ParalysisSettings:
    api_url: str
    working_directory: Path
    log_tasks: bool
    paradise_root: Path
    connection_string: str = ts.secret()
    profile_proc_paths: list[str]
    cache_db: Path


def make_engine(config_file: str | Path) -> Engine:
    settings = ts.load(ParalysisSettings, appname="paralysis", config_files=[config_file])
    return create_engine(settings.connection_string)
