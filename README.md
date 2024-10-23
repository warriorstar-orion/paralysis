# Paralysis

Paralysis is `Para`dise Ana`lysis` and associated tools.

It uses [uv][] as an overall tooling/publishing/script manager.

[uv]: https://docs.astral.sh/uv/

## Settings

Most Paralysis commands operate with the same set of settings. To make using
these commands easier, these settings are specified in TOML file that these
commands take as input. An example file is at `settings.example.toml`. The
following settings are used and should be specified:

- `connection_string`: The connection string to the database where round data
from the Parastats API is being stored. This is expected to be a MySQL or
MariaDB database.
- `api_url`: The URL to the Parastats API.
- `working_directory`: Where logs and API request cache databases should be stored.
- `log_tasks`: Whether the tool commands should log their output to a file.
- `cache_db`: The name of the SQLite database where API request caches are stored.
- `paradise_root`: The path of the Paradise repository you are operating on.
- `profile_proc_paths`: The names of procs you are mirroring for profiler data.

## Synchronizing Parastats Data

To retrieve the latest round feedback and population data and store it locally,
you must first create the database, and then run `uv run create_tables` to
populate the database with the parastats schema. This schema largely resembles
the one used in Paradise for production storage, although many tables are not
included.

Once you have confirmed the database and table is working as expected, you can
begin synchronizing Parastats data.

Currently the only available synchronization is to sync the last 50 rounds of
blackbox feedback data. To do so, run `uv run sync_blackbox` with `--settings`
set to the location of the TOML file you created above. This uses a cached and
rate-limited instance of the requests API that complies with the request limits
specified by the Parastats API.

Once you have downloaded this data, you can then operate on it with the analysis
tools of your choice.

## Tasks

### Webmaps / Wikimaps

The command for creating webmaps or wikimaps is `uv run wiki_areamap`. The
following command line options are required:

- `--dmm_file`: The path to the map you are rendering.
- `--output_path`: The path to where generated images will be saved to.

The following command line options are optional:

- `--output_type`: `wiki` or `webmap` for the desired output. Defaults to `wiki`.
- `--labels`: `rooms`, `polygons`, or `none`. The desired labels for the rendered
  output. Rooms are room names, polygons are used for debugging.

### Space Ruin Maps

The command for generating rendered maps of space ruin placement is `uv run space_ruin_map`. The following command line options are required:

- `--settings`: The location of the settings file containing the configuration
  values described in [Settings](#settings).
- `--output_path`: The path where ruin maps are placed. Each set of ruin maps is
  created within a directory named after the round.
- `--round_id`: The ID of the round you are generating ruin maps for.

## License

Paralysis is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Paralysis is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Paralysis. If not, see http://www.gnu.org/licenses/.
