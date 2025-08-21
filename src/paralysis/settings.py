from pathlib import Path
import urllib

from sqlalchemy import create_engine
from sqlalchemy import Engine
import typed_settings as ts


@ts.settings(frozen=True)
class ParalysisSettings:
    api_url: str
    working_directory: Path
    log_tasks: bool
    paradise_root: Path
    profile_proc_paths: list[str]
    cache_db: Path
    connection_string: str = ts.secret()

    def parastats(self, endpoint, **kwargs):
        return self.api_url + endpoint + '?' + urllib.parse.urlencode(kwargs)

def make_engine(config_file: str | Path) -> Engine:
    settings = ts.load(
        ParalysisSettings, appname="paralysis", config_files=[config_file]
    )
    return create_engine(settings.connection_string)
