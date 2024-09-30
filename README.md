# Paralysis

Paralysis is `Para`dise Ana`lysis` and associated tools.

It uses [uv][] as an overall tooling/publishing/script manager.

[uv]: https://docs.astral.sh/uv/

## Webmaps / Wikimaps
To create wiki maps:

```shell
$ uv run wiki_areamap D:\ExternalRepos\third_party\Paradise\_maps\map_files\stations\boxstation.dmm D:\wiki_maps
```

To create webmap legends:

```shell
$ uv run wiki_areamap --output_type=WEBMAP --labels=ROOMS D:\ExternalRepos\third_party\Paradise\_maps\map_files\stations\boxstation.dmm D:\web_maps
```

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
