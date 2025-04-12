import importlib
import math
from dataclasses import dataclass
from pathlib import Path

import click
from avulto import DMM
from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import typed_settings as ts

from paralysis.settings import ParalysisSettings
from paralysis.model import Round

ZOOM_LEVEL = 4

dmm_cache: dict[str, DMM] = dict()

TRANSITZONE_COLOR = "#440000ff"
RUIN_PADDING_COLOR = "#0000aaff"
SAFE_ZONE_COLOR = "#000000ff"

RUIN_RECT_COLOR = "#444444ff"
RUIN_WALL_COLOR = "#8080ffff"
RUIN_FLOOR_COLOR = "#7070ccff"
RUIN_TILE_COLOR = "#8080ffff"
RUIN_NEARSPACE_COLOR = "#6060a0ff"
TEXT_COLOR = "#ffffffff"


@dataclass(frozen=True)
class RuinPlacement:
    map: str
    coords: tuple[int, int, int]

    def ruin_rect(self):
        ruin_map = dmm_cache[self.map]
        ruin_width = ruin_map.size.x
        ruin_height = ruin_map.size.y
        translated_coords = DMCOORD(self.coords[0], self.coords[1])
        ruin_x0 = translated_coords[0] - math.floor(ruin_width / 2)
        ruin_y0 = translated_coords[1] - math.floor(ruin_height / 2)
        ruin_x1 = ruin_x0 + ruin_width
        ruin_y1 = ruin_y0 + ruin_height

        return [(ruin_x0, ruin_y0), (ruin_x1, ruin_y1)]


@dataclass
class ZLevel:
    level: int
    # TODO: Reintroduce budget/cost parsing from DME
    budget: int = 0


@dataclass
class Zlevels:
    levels: list[ZLevel]

    def __init__(self):
        self.levels = list()

    def get_zlevel(self, zlevel):
        for level in self.levels:
            if level.level == zlevel:
                return level
        newlevel = ZLevel(zlevel)
        self.levels.append(newlevel)
        return newlevel

    def ruin_level(self, zlevel):
        zmax = max(z.level for z in self.levels)
        return zlevel - zmax + len(self.levels)

    def total_budget(self):
        return sum(z.budget for z in self.levels)


def DMCOORD(x, y):
    return (x - 1, (255 - y - 1))


def render_z_levels(ruin_data, output_path: Path, round_id: int, env_root: Path):
    ruin_root = env_root / "_maps/map_files/RandomRuins/SpaceRuins"
    ZLEVELS = Zlevels()

    font_size = 48
    font_file = importlib.resources.files("paralysis.resources").joinpath(
        "Minimal5x7.ttf"
    )
    fnt = ImageFont.truetype(font_file, size=font_size)

    space_ruins: list[RuinPlacement] = list()

    transition_border = 6
    safe_border = 14  # TRANSITIONEDGE + SPACERUIN_MAP_EDGE_PAD
    transition_rect = (
        transition_border,
        transition_border,
        255 - transition_border,
        255 - transition_border,
    )

    safe_rect = (
        transition_border + safe_border,
        transition_border + safe_border,
        255 - transition_border - safe_border,
        255 - transition_border - safe_border,
    )

    for ruin in ruin_data.values():
        coords = [int(c) for c in ruin["coords"].split(",")]
        if not (ruin_root / ruin["map"]).exists():
            continue

        space_ruins.append(RuinPlacement(ruin["map"], coords))
        ZLEVELS.get_zlevel(coords[2])

    for z_level in ZLEVELS.levels:
        image = Image.new(
            size=(255, 255),
            mode="RGBA",
        )
        draw = ImageDraw.Draw(image)
        draw.fontmode = "1"

        draw.rectangle([0, 0, 255, 255], fill=TRANSITZONE_COLOR)

        draw.rectangle(transition_rect, fill=RUIN_PADDING_COLOR)
        draw.rectangle(safe_rect, fill=SAFE_ZONE_COLOR)

        for ruin in space_ruins:
            if ruin.coords[2] != z_level.level:
                continue

            if ruin.map not in dmm_cache:
                dmm_cache[ruin.map] = DMM.from_file(ruin_root / ruin.map)

            ruin_rect = ruin.ruin_rect()
            print(f"ruin={ruin.map}, coords={ruin.coords}")

            topleft, bottom_right = ruin_rect
            draw.rectangle(
                (topleft[0], topleft[1], bottom_right[0] - 1, bottom_right[1] - 1),
                fill=RUIN_RECT_COLOR,
                outline=None,
            )

            ruin_map = dmm_cache[ruin.map]
            ruin_xy0, ruin_xy1 = ruin_rect
            for coord in ruin_map.coords():
                tile = ruin_map.tiledef(*coord)
                is_space = tile.area_path.child_of("/area/space")
                is_noop = tile.area_path.child_of("/area/template_noop")
                is_nearstation = tile.area_path.child_of("/area/space/nearstation")
                is_floor = tile.turf_path.child_of("/turf/simulated/floor")
                if not is_nearstation and (is_space or is_noop):
                    continue
                if not is_nearstation and tile.turf_path.child_of(
                    "/turf/template_noop"
                ):
                    continue

                color = RUIN_TILE_COLOR
                if is_nearstation:
                    color = RUIN_NEARSPACE_COLOR

                if is_floor:
                    color = RUIN_FLOOR_COLOR

                translated_coord = DMCOORD(coord[0], coord[1])
                draw.point(
                    [translated_coord[0] + ruin_xy0[0], ruin_xy1[1] - coord[1]],
                    fill=color,
                )

        # Scale up after we draw the rectangles because fuck dealing with trying
        # to calculate offsets of rectangles while drawing them zoomed in
        image = image.resize(
            (255 * ZOOM_LEVEL, 255 * ZOOM_LEVEL), resample=Image.Resampling.NEAREST
        )

        draw = ImageDraw.Draw(image)
        draw.fontmode = "1"

        draw.rectangle(
            (0, 0, 255 * ZOOM_LEVEL - 1, 255 * ZOOM_LEVEL - 1),
            outline=(255, 255, 255),
            fill=None,
        )

        for ruin in space_ruins:
            if ruin.coords[2] != z_level.level:
                continue

            msg = ruin.map.replace(".dmm", "")
            textbox_center = list(
                p * ZOOM_LEVEL for p in DMCOORD(ruin.coords[0], ruin.coords[1])
            )
            rect = draw.textbbox(xy=textbox_center, text=msg, font=fnt, align="center")

            (left, top, right, bottom) = rect
            text_xy = (
                left - ((right - left) / 2),
                top - ((bottom - top) / 2),
            )

            draw.text(text_xy, msg, fill=TEXT_COLOR, font=fnt, align="center")

            print(
                f"ruin ruin_rect={ruin_rect} center={ruin.coords} textbox_center={textbox_center} msg={msg} rect={rect} text_xy={text_xy}"
            )

        s = f"ROUND #{round_id}: Z-LEVEL {ZLEVELS.ruin_level(z_level.level)} / {len(ZLEVELS.levels)}"

        for msg, y_pos in (
            ("TRANSITION EDGE", font_size / 2 - 10),
            ("RUIN PLACEMENT PADDING", 56),
            (s, 255 * ZOOM_LEVEL - 56),
        ):
            rect = draw.textbbox(xy=(255 * ZOOM_LEVEL / 2, y_pos), text=msg, font=fnt)
            (left, top, right, bottom) = rect
            text_xy = (
                left - ((right - left) / 2),
                top - ((bottom - top) / 2),
            )

            draw.text(text_xy, msg, fill=TEXT_COLOR, font=fnt)

        image.save(output_path / f"space_ruin_{z_level.level}@4x.png")


@click.command()
@click.option("--settings", required=True, help="Location of your settings.toml file.")
@click.option(
    "--output_path",
    required=True,
    help="The output path where per-round directories are created.",
)
@click.option("--round_id", required=True, help="The round ID to create maps from.")
def main(settings, output_path: Path, round_id: int):
    settings: ParalysisSettings = ts.load(
        ParalysisSettings, appname="paralysis", config_files=[settings]
    )

    engine = create_engine(settings.connection_string)
    with Session(engine) as session:
        round = session.get(Round, int(round_id))
        if not round.has_feedback("ruin_placement"):
            raise RuntimeError(f"no ruin placement found for round ID {round.id}")

        ruin_placements = round.feedback("ruin_placement")
        output_path = Path(output_path) / str(round.id)
        output_path.mkdir(parents=True, exist_ok=True)
        render_z_levels(ruin_placements, output_path, round_id, settings.paradise_root)
