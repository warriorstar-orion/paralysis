import importlib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

import click
import largestinteriorrectangle
import numpy as np
import rasterio
import rasterio.features
from avulto import DMM
from avulto import Path as p
from loguru import logger
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon


class LabelType(Enum):
    NONE = 0
    POLYGONS = 1
    ROOMS = 2


class OutputType(Enum):
    WIKI = 0
    WEBMAP = 1


@dataclass(frozen=True)
class Area:
    area: p
    color: str
    text: Optional[str] = ""
    # Colors.alts: Optional[dict[int, str]] = None
    map_color_overrides: Optional[dict[str, str]] = None


class Colors:
    AI_SAT = "#00ffff"
    ARRIVALS = "#b6ff00"
    ATMOS = "#00ff90"
    BOTANY = "#43db00"
    COMMAND = "#0094ff"
    ENGINEERING = "#ffd800"
    ESCAPE_POD = "#47687f"
    HALLWAY = "#fff1ad"
    MAINTS = "#808080"
    MEDBAY = "#6cadd2"
    PUBLIC = "#bfffff"
    SCIENCE = "#b200ff"
    SECURITY = "#e20000"
    SERVICE = "#ffb787"
    SOLARS = "#005491"
    SUPPLY = "#ff6a00"
    DISPOSALS = "#dbaf6d"
    QUANTUMPAD = "#dbaf6d"  # same as above at the moment
    ASTEROID = "#a09078"
    EMERALD_PLASMA = "#bd5d9c"


# The lists of areas are not necessarily in alphabetical order. They may be
# arranged in certain ways because of inner polygon holes having to be drawn in
# a specific order because of specific map layouts.
ASTEROID_AREAS = [
    Area("/area/mine/unexplored/cere/civilian", Colors.ASTEROID),
    Area("/area/mine/unexplored/cere/research", Colors.ASTEROID),
    Area("/area/mine/unexplored/cere/command", Colors.ASTEROID),
    Area("/area/mine/unexplored/cere/ai", Colors.ASTEROID),
    Area("/area/mine/unexplored/cere/cargo", Colors.ASTEROID),
    Area("/area/mine/unexplored/cere/engineering", Colors.ASTEROID),
    Area("/area/mine/unexplored/cere/orbiting", Colors.ASTEROID),
    Area("/area/station/service/clown/secret", Colors.ASTEROID),
    Area("/area/mine/unexplored/cere/engineering", Colors.ASTEROID),
    Area("/area/mine/unexplored/cere/medical", Colors.ASTEROID),
    Area("/area/station/engineering/atmos/asteroid", Colors.ASTEROID),
]

SUPPLY_AREAS = [
    Area("/area/station/maintenance/disposal", Colors.SUPPLY, "Disposals"),
    Area("/area/station/supply/miningdock", Colors.SUPPLY, "Mining"),
    Area("/area/station/supply/office", Colors.SUPPLY, "Cargo"),
    Area("/area/station/supply/qm", Colors.SUPPLY, "QM"),
    Area("/area/station/supply/storage", Colors.SUPPLY, "Cargo\nBay"),
    Area("/area/station/supply/sorting", Colors.SUPPLY),
    Area("/area/station/supply/expedition", Colors.SUPPLY),
    Area("/area/station/supply/warehouse", Colors.SUPPLY),
    Area("/area/station/supply/break_room", Colors.SUPPLY),
]


COMMAND_AREAS = [
    Area("/area/station/ai_monitored/storage/eva", Colors.COMMAND, "EVA"),
    Area("/area/station/command/bridge", Colors.COMMAND, "Bridge"),
    Area("/area/station/command/meeting_room", Colors.COMMAND),
    Area(
        "/area/station/command/office/blueshield",
        Colors.COMMAND,
        "Blue.",
    ),
    Area("/area/station/command/office/captain", Colors.COMMAND, "Cptn."),
    Area("/area/station/command/office/captain/bedroom", Colors.COMMAND),
    Area("/area/station/command/office/hop", Colors.COMMAND, "HoP"),
    Area("/area/station/command/office/ntrep", Colors.COMMAND, "NT\nRep"),
    Area("/area/station/command/server", Colors.COMMAND),
    Area("/area/station/command/teleporter", Colors.COMMAND),
    Area("/area/station/command/vault", Colors.COMMAND, "Vlt."),
    Area("/area/station/turret_protected/ai_upload", Colors.COMMAND, "AI\nUpl."),
    Area("/area/station/turret_protected/ai_upload/foyer", Colors.COMMAND),
]


HALLWAY_AREAS = [
    Area("/area/station/hallway/primary/aft", Colors.HALLWAY),
    Area("/area/station/hallway/primary/central/ne", Colors.HALLWAY),
    Area("/area/station/hallway/primary/central/north", Colors.HALLWAY),
    Area("/area/station/hallway/primary/central/nw", Colors.HALLWAY),
    Area("/area/station/hallway/primary/central/se", Colors.HALLWAY),
    Area("/area/station/hallway/primary/central/sw", Colors.HALLWAY),
    Area("/area/station/hallway/primary/central/west", Colors.HALLWAY),
    Area("/area/station/hallway/primary/central/east", Colors.HALLWAY),
    Area("/area/station/hallway/primary/fore", Colors.HALLWAY),
    Area("/area/station/hallway/primary/port", Colors.HALLWAY),
    Area("/area/station/hallway/primary/starboard/east", Colors.HALLWAY),
    Area("/area/station/hallway/primary/starboard/west", Colors.HALLWAY),
    Area("/area/station/security/lobby", Colors.HALLWAY),
    Area("/area/station/hallway/primary/central", Colors.HALLWAY),
    Area("/area/station/hallway/secondary/bridge", Colors.HALLWAY),
    Area("/area/station/hallway/primary/central/south", Colors.HALLWAY),
    Area("/area/station/hallway/primary/starboard", Colors.HALLWAY),
    # Cargo lobby extends into hallway on Metastation
    Area("/area/station/supply/lobby", Colors.HALLWAY),
    Area("/area/station/hallway/primary/port/north", Colors.HALLWAY),
    Area("/area/station/hallway/primary/port/east", Colors.HALLWAY),
    Area("/area/station/hallway/primary/port/west", Colors.HALLWAY),
    Area("/area/station/hallway/primary/port/south", Colors.HALLWAY),
    Area("/area/station/hallway/primary/aft/north", Colors.HALLWAY),
    Area("/area/station/hallway/primary/aft/south", Colors.HALLWAY),
    Area("/area/station/hallway/primary/aft/west", Colors.HALLWAY),
    Area("/area/station/hallway/primary/fore", Colors.HALLWAY),
    Area("/area/station/hallway/primary/fore/north", Colors.HALLWAY),
    Area("/area/station/hallway/primary/fore/east", Colors.HALLWAY),
    Area("/area/station/hallway/primary/fore/west", Colors.HALLWAY),
    Area("/area/station/hallway/primary/aft/east", Colors.HALLWAY),
    Area("/area/station/hallway/primary/starboard/south", Colors.HALLWAY),
    Area("/area/station/hallway/spacebridge/servsci", Colors.HALLWAY),
    Area("/area/station/hallway/spacebridge/serveng", Colors.HALLWAY),
    Area("/area/station/hallway/spacebridge/sercom", Colors.HALLWAY),
    Area("/area/station/hallway/spacebridge/medcargo", Colors.HALLWAY),
    Area("/area/station/hallway/spacebridge/dockmed", Colors.HALLWAY),
    Area("/area/station/hallway/spacebridge/comeng", Colors.HALLWAY),
    Area("/area/station/hallway/spacebridge/scidock", Colors.HALLWAY),
    Area("/area/station/hallway/spacebridge/engmed", Colors.HALLWAY),
    Area("/area/station/hallway/spacebridge/cargocom", Colors.HALLWAY),
    Area("/area/station/hallway/spacebridge/security/south", Colors.HALLWAY),
    Area("/area/station/hallway/spacebridge/security/west", Colors.HALLWAY),
    Area("/area/station/hallway/primary/starboard/north", Colors.HALLWAY),
]

ENGINEERING_AREAS = [
    Area("/area/station/command/office/ce", Colors.ENGINEERING, "CE"),
    Area("/area/station/engineering/break_room", Colors.ENGINEERING),
    Area("/area/station/engineering/control", Colors.ENGINEERING),
    Area("/area/station/engineering/controlroom", Colors.ENGINEERING),
    Area("/area/station/engineering/equipmentstorage", Colors.ENGINEERING),
    Area("/area/station/engineering/gravitygenerator", Colors.ENGINEERING),
    Area("/area/station/engineering/hardsuitstorage", Colors.ENGINEERING),
    Area("/area/station/engineering/secure_storage", Colors.ENGINEERING),
    Area("/area/station/engineering/smes", Colors.ENGINEERING),
    Area("/area/station/engineering/tech_storage", Colors.ENGINEERING),
    Area("/area/station/engineering/engine", Colors.ENGINEERING),
    Area("/area/station/maintenance/assembly_line", Colors.ENGINEERING),
    Area("/area/station/maintenance/electrical", Colors.ENGINEERING),
    Area("/area/station/public/construction", Colors.ENGINEERING),
    Area("/area/station/engineering/ai_transit_tube", Colors.ENGINEERING),
    Area("/area/station/engineering/engine/supermatter", Colors.ENGINEERING),
    Area("/area/station/maintenance/electrical_shop", Colors.ENGINEERING),
    Area("/area/station/engineering/break_room/secondary", Colors.ENGINEERING),
    Area("/area/station/engineering/atmos/asteroid_filtering", Colors.ENGINEERING),
    Area("/area/station/engineering/atmos/asteroid_maint", Colors.ENGINEERING),
    Area("/area/station/engineering/atmos/storage", Colors.ENGINEERING),
    Area("/area/station/engineering/transmission_laser", Colors.ENGINEERING),
]

ATMOS_AREAS = [
    Area("/area/station/engineering/atmos", Colors.ATMOS),
    Area("/area/station/engineering/atmos/control", Colors.ATMOS),
    Area("/area/station/engineering/atmos/distribution", Colors.ATMOS),
    Area("/area/station/engineering/atmos/distribution", Colors.ATMOS),
    Area("/area/station/maintenance/turbine", Colors.ATMOS),
    Area("/area/station/maintenance/incinerator", Colors.ATMOS, "Incin."),
]

MAINTS_AREAS = [
    Area("/area/station/maintenance/abandonedbar", Colors.MAINTS),
    Area("/area/station/maintenance/aft", Colors.MAINTS),
    Area("/area/station/maintenance/apmaint", Colors.MAINTS),
    Area("/area/station/maintenance/apmaint2", Colors.MAINTS),
    Area("/area/station/maintenance/asmaint", Colors.MAINTS),
    Area("/area/station/maintenance/asmaint2", Colors.MAINTS),
    Area("/area/station/maintenance/fore", Colors.MAINTS),
    Area("/area/station/maintenance/fpmaint", Colors.MAINTS),
    Area("/area/station/maintenance/fpmaint2", Colors.MAINTS),
    Area("/area/station/maintenance/fsmaint", Colors.MAINTS),
    Area("/area/station/maintenance/fsmaint2", Colors.MAINTS),
    Area("/area/station/maintenance/port", Colors.MAINTS),
    Area("/area/station/maintenance/port2", Colors.MAINTS),
    Area("/area/station/maintenance/storage", Colors.MAINTS),
    Area("/area/station/maintenance/maintcentral", Colors.MAINTS),
    Area("/area/station/maintenance/starboard", Colors.MAINTS),
    Area("/area/station/maintenance/starboard2", Colors.MAINTS),
    Area("/area/station/maintenance/medmaint", Colors.MAINTS),
    Area("/area/station/maintenance/xenobio_north", Colors.MAINTS),
    Area("/area/station/maintenance/xenobio_south", Colors.MAINTS),
    Area("/area/station/maintenance/fore2", Colors.MAINTS),
    Area("/area/station/maintenance/spacehut", Colors.MAINTS),
    Area("/area/station/maintenance/engimaint", Colors.MAINTS),
    Area("/area/station/maintenance/abandoned_garden", Colors.MAINTS),
    Area("/area/station/maintenance/gambling_den", Colors.MAINTS),
    Area("/area/station/maintenance/library", Colors.MAINTS),
    Area("/area/station/maintenance/theatre", Colors.MAINTS),
    Area("/area/station/maintenance/disposal/north", Colors.MAINTS),
    Area("/area/station/maintenance/dorms/port", Colors.MAINTS),
    Area("/area/station/maintenance/dorms/aft", Colors.MAINTS),
    Area("/area/station/maintenance/dorms/fore", Colors.MAINTS),
    Area("/area/station/maintenance/dorms/starboard", Colors.MAINTS),
    Area("/area/station/maintenance/security", Colors.MAINTS),
    Area("/area/station/maintenance/security/aft_port", Colors.MAINTS),
    Area("/area/station/maintenance/security/aft_starboard", Colors.MAINTS),
    Area("/area/station/maintenance/security/fore", Colors.MAINTS),
]

PUBLIC_AREAS = [
    Area("/area/station/public/fitness", Colors.PUBLIC),
    Area("/area/station/hallway/secondary/garden", Colors.PUBLIC, "Garden"),
    Area("/area/station/public/arcade", Colors.PUBLIC),
    Area(
        "/area/station/public/dorms",
        Colors.PUBLIC,
        "Dorms",
        map_color_overrides={
            "emeraldstation": Colors.HALLWAY,
        },
    ),
    Area("/area/station/public/locker", Colors.PUBLIC, "Lockers"),
    Area("/area/station/public/mrchangs", Colors.PUBLIC),
    Area("/area/station/public/sleep", Colors.PUBLIC, "Cryo"),
    Area("/area/station/public/sleep/secondary", Colors.PUBLIC, "Cryo"),
    Area("/area/station/public/storage/emergency/port", Colors.PUBLIC, "Tools"),
    Area("/area/station/public/storage/tools", Colors.PUBLIC, "Tools"),
    Area("/area/station/public/storage/tools/auxiliary", Colors.PUBLIC),
    Area("/area/station/public/toilet/lockerroom", Colors.PUBLIC),
    Area("/area/station/public/toilet/unisex", Colors.PUBLIC),
    Area("/area/station/public/toilet", Colors.PUBLIC),
    Area("/area/station/public/vacant_office", Colors.PUBLIC),
    Area("/area/station/public/storefront", Colors.PUBLIC),
    Area("/area/station/service/barber", Colors.PUBLIC),
    Area("/area/station/science/robotics/showroom", Colors.PUBLIC),
    Area("/area/station/service/cafeteria", Colors.PUBLIC),
    Area("/area/station/public/storage/office", Colors.PUBLIC),
    Area("/area/holodeck/alphadeck", Colors.PUBLIC),
    Area("/area/station/public/shops", Colors.PUBLIC),
    Area("/area/station/public/park", Colors.PUBLIC),
    Area("/area/station/maintenance/abandoned_office", Colors.PUBLIC),
]

SECURITY_AREAS = [
    Area("/area/station/command/office/hos", Colors.SECURITY, "HoS"),
    Area("/area/station/legal/courtroom", Colors.SECURITY, "Court"),
    Area("/area/station/legal/lawoffice", Colors.SECURITY, "IAA"),
    Area("/area/station/legal/magistrate", Colors.SECURITY, "Magi."),
    Area("/area/station/security/armory/secure", Colors.SECURITY, "Armory"),
    Area("/area/station/security/brig", Colors.SECURITY),
    Area("/area/station/security/checkpoint", Colors.SECURITY),
    Area("/area/station/security/checkpoint/secondary", Colors.SECURITY, "Chk."),
    Area("/area/station/security/armory", Colors.SECURITY),
    Area("/area/station/security/detective", Colors.SECURITY),
    Area("/area/station/security/evidence", Colors.SECURITY),
    Area("/area/station/security/execution", Colors.SECURITY),
    Area("/area/station/security/interrogation", Colors.SECURITY),
    Area("/area/station/security/main", Colors.SECURITY),
    Area(
        "/area/station/security/permabrig",
        Colors.SECURITY,
        "Permabrig",
    ),
    Area("/area/station/security/prison", Colors.SECURITY),
    Area("/area/station/security/prison/cell_block", Colors.SECURITY),
    Area("/area/station/security/prison/cell_block/A", Colors.SECURITY),
    Area("/area/station/security/prisonlockers", Colors.SECURITY),
    Area("/area/station/security/processing", Colors.SECURITY),
    Area("/area/station/security/range", Colors.SECURITY),
    Area("/area/station/security/storage", Colors.SECURITY),
    Area("/area/station/security/warden", Colors.SECURITY, "Wrdn."),
    Area("/area/station/security/permasolitary", Colors.SECURITY),
    Area("/area/station/command/customs", Colors.SECURITY),
    Area("/area/station/security/prisonershuttle", Colors.SECURITY),
    Area("/area/station/legal/courtroom/gallery", Colors.SECURITY),
]

ARRIVALS_AREAS = [
    Area("/area/shuttle/arrival/station", Colors.ARRIVALS),
    Area(
        "/area/station/hallway/secondary/entry",
        Colors.ARRIVALS,
        "Arrivals",
    ),
    Area(
        "/area/station/hallway/secondary/exit",
        Colors.ARRIVALS,
        "Escape",
    ),
    Area("/area/station/hallway/entry/south", Colors.ARRIVALS),
    Area("/area/station/hallway/entry/north", Colors.ARRIVALS),
    Area("/area/station/hallway/secondary/entry/north", Colors.ARRIVALS),
    Area("/area/station/hallway/secondary/entry/south", Colors.ARRIVALS),
    Area("/area/station/hallway/secondary/entry/lounge", Colors.ARRIVALS),
    Area("/area/station/hallway/secondary/entry/east", Colors.ARRIVALS),
    Area("/area/station/hallway/secondary/entry/west", Colors.ARRIVALS),
]

MEDBAY_AREAS = [
    Area(
        "/area/station/maintenance/aft2",
        Colors.MEDBAY,
        map_color_overrides={
            "metastation": Colors.MAINTS,
        },
    ),
    Area("/area/station/medical/chemistry", Colors.MEDBAY, "Chem"),
    Area("/area/station/medical/coldroom", Colors.MEDBAY),
    Area("/area/station/medical/cryo", Colors.MEDBAY),
    Area("/area/station/medical/medbay", Colors.MEDBAY),
    Area("/area/station/medical/medbay2", Colors.MEDBAY),
    Area("/area/station/medical/medbay3", Colors.MEDBAY),
    Area("/area/station/medical/morgue", Colors.MEDBAY),
    Area("/area/station/medical/paramedic", Colors.MEDBAY),
    Area("/area/station/medical/psych", Colors.MEDBAY),
    Area("/area/station/medical/reception", Colors.MEDBAY),
    Area("/area/station/medical/sleeper", Colors.MEDBAY),
    Area("/area/station/medical/storage", Colors.MEDBAY),
    Area("/area/station/medical/storage/secondary", Colors.MEDBAY),
    Area("/area/station/medical/surgery", Colors.MEDBAY),
    Area("/area/station/medical/surgery/observation", Colors.MEDBAY),
    Area("/area/station/medical/surgery/primary", Colors.MEDBAY, "OR1"),
    Area("/area/station/medical/surgery/secondary", Colors.MEDBAY, "OR2"),
    Area("/area/station/medical/cloning", Colors.MEDBAY),
    Area("/area/station/medical/virology", Colors.MEDBAY, "Virology"),
    Area("/area/station/medical/virology/lab", Colors.MEDBAY, "Virology"),
    Area("/area/station/command/office/cmo", Colors.MEDBAY, "CMO"),
    Area("/area/station/medical/exam_room", Colors.MEDBAY),
    Area("/area/station/medical/break_room", Colors.MEDBAY),
    Area("/area/station/medical/patients_rooms", Colors.MEDBAY),
    Area("/area/station/medical/patients_rooms_secondary", Colors.MEDBAY),
    Area("/area/station/medical/patients_rooms1", Colors.MEDBAY),
    Area("/area/station/public/storage/emergency", Colors.MEDBAY),
]

SCIENCE_AREAS = [
    Area("/area/station/science/lobby", Colors.SCIENCE),
    Area("/area/station/science/hallway", Colors.SCIENCE),
    Area("/area/station/science/rnd", Colors.SCIENCE, "R&D"),
    Area("/area/station/science/robotics/chargebay", Colors.SCIENCE),
    Area("/area/station/science/robotics", Colors.SCIENCE, "Robotics"),
    Area("/area/station/command/office/rd", Colors.SCIENCE, "RD"),
    Area("/area/station/science/genetics", Colors.SCIENCE, "Genetics"),
    Area("/area/station/science/server", Colors.SCIENCE),
    Area("/area/station/science/server/coldroom", Colors.SCIENCE),
    Area("/area/station/science/misc_lab", Colors.SCIENCE, "Chem"),
    Area("/area/station/science/explab/chamber", Colors.SCIENCE),
    Area("/area/station/science/explab", Colors.SCIENCE),
    Area("/area/station/science/storage", Colors.SCIENCE),
    Area("/area/station/science/test_chamber", Colors.SCIENCE),
    Area("/area/station/science/xenobiology", Colors.SCIENCE, "Xenobio"),
    Area("/area/station/science/toxins/launch", Colors.SCIENCE),
    Area(
        "/area/station/science/toxins/test",
        Colors.SCIENCE,
        "Toxins\nTesting",
    ),
    Area("/area/station/science/toxins/mixing", Colors.SCIENCE, "Toxins"),
    Area("/area/station/science/research", Colors.SCIENCE),
    Area("/area/station/science/break_room", Colors.SCIENCE),
]

AI_SAT_AREAS = [
    Area("/area/station/aisat", Colors.AI_SAT),
    Area("/area/station/aisat/atmos", Colors.AI_SAT),
    Area("/area/station/aisat/hall", Colors.AI_SAT, "AI Sat."),
    Area("/area/station/aisat/service", Colors.AI_SAT),
    Area("/area/station/telecomms/chamber", Colors.AI_SAT),
    Area("/area/station/turret_protected/ai", Colors.AI_SAT),
    Area("/area/station/turret_protected/aisat", Colors.AI_SAT),
    Area("/area/station/turret_protected/aisat/interior", Colors.AI_SAT),
    Area("/area/station/telecomms/computer", Colors.AI_SAT),
    Area("/area/station/engineering/ai_transit_tube", Colors.AI_SAT),
    Area("/area/station/aisat/breakroom", Colors.AI_SAT),
    Area(
        "/area/station/turret_protected/aisat/interior/secondary",
        Colors.AI_SAT,
    ),
]

SERVICE_AREAS = [
    Area("/area/station/service/expedition", Colors.SERVICE, "Expl."),
    Area("/area/station/service/janitor", Colors.SERVICE, "Jani."),
    Area("/area/station/service/bar", Colors.SERVICE, "Bar"),
    Area("/area/station/service/kitchen", Colors.SERVICE, "Kitchen"),
    Area("/area/station/service/clown", Colors.SERVICE),
    Area("/area/station/service/mime", Colors.SERVICE),
    Area("/area/station/service/library", Colors.SERVICE, "Library"),
    Area("/area/station/service/chapel", Colors.SERVICE, "Chapel"),
    Area(
        "/area/station/service/chapel/funeral",
        Colors.SERVICE,
        "Chapel",
    ),
    Area("/area/station/service/chapel/office", Colors.SERVICE),
    Area("/area/station/service/hydroponics", Colors.BOTANY, "Botany"),
    Area("/area/station/public/pet_store", Colors.SERVICE),
    Area("/area/station/public/storage/art", Colors.SERVICE),
    Area("/area/station/service/theatre", Colors.SERVICE),
]

SOLARS_AREAS = [
    Area("/area/station/maintenance/solar_maintenance", Colors.SOLARS),
    Area("/area/station/maintenance/solar_maintenance/aft", Colors.SOLARS),
    Area("/area/station/maintenance/solar_maintenance/aft_port", Colors.SOLARS),
    Area("/area/station/maintenance/solar_maintenance/aft_starboard", Colors.SOLARS),
    Area("/area/station/maintenance/solar_maintenance/fore", Colors.SOLARS),
    Area("/area/station/maintenance/solar_maintenance/fore_port", Colors.SOLARS),
    Area("/area/station/maintenance/solar_maintenance/fore_starboard", Colors.SOLARS),
    Area("/area/station/maintenance/solar_maintenance/port", Colors.SOLARS),
    Area("/area/station/maintenance/solar_maintenance/starboard", Colors.SOLARS),
    Area("/area/station/engineering/solar", Colors.SOLARS),
    Area("/area/station/engineering/solar/aft", Colors.SOLARS),
    Area("/area/station/engineering/solar/aft_port", Colors.SOLARS),
    Area("/area/station/engineering/solar/aft_starboard", Colors.SOLARS),
    Area("/area/station/engineering/solar/fore", Colors.SOLARS),
    Area("/area/station/engineering/solar/fore_port", Colors.SOLARS),
    Area("/area/station/engineering/solar/fore_starboard", Colors.SOLARS),
    Area("/area/station/engineering/solar/port", Colors.SOLARS),
    Area("/area/station/engineering/solar/starboard", Colors.SOLARS),
]

ESCAPE_POD_AREAS = [
    Area("/area/shuttle/pod_1", Colors.ESCAPE_POD),
    Area("/area/shuttle/pod_2", Colors.ESCAPE_POD),
    Area("/area/shuttle/pod_3", Colors.ESCAPE_POD),
    Area("/area/shuttle/pod_4", Colors.ESCAPE_POD),
]


MISC_AREAS = [
    Area("/area/space/nearstation/disposals", Colors.DISPOSALS),
    Area(
        "/area/station/maintenance/disposal/northwest",
        Colors.DISPOSALS,
    ),
    Area("/area/station/maintenance/disposal/west", Colors.DISPOSALS),
    Area(
        "/area/station/maintenance/disposal/northeast",
        Colors.DISPOSALS,
    ),
    Area("/area/station/maintenance/disposal/east", Colors.DISPOSALS),
    Area(
        "/area/station/maintenance/disposal/southeast",
        Colors.DISPOSALS,
    ),
    Area("/area/station/maintenance/disposal/south", Colors.DISPOSALS),
    Area(
        "/area/station/maintenance/disposal/southwest",
        Colors.DISPOSALS,
    ),
    Area(
        "/area/station/maintenance/disposal/external/east",
        Colors.DISPOSALS,
    ),
    Area(
        "/area/station/maintenance/disposal/external/north",
        Colors.DISPOSALS,
    ),
    Area(
        "/area/station/maintenance/disposal/external/southeast",
        Colors.DISPOSALS,
    ),
    Area(
        "/area/station/maintenance/disposal/external/southwest",
        Colors.DISPOSALS,
    ),
    Area("/area/station/maintenance/disposal/westalt", Colors.DISPOSALS),
    Area(
        "/area/station/engineering/atmos/asteroid_core",
        Colors.EMERALD_PLASMA,
    ),
]

QUANTUMPAD_AREAS = [
    Area("/area/station/public/quantum/cargo", Colors.QUANTUMPAD),
    Area("/area/station/public/quantum/docking", Colors.QUANTUMPAD),
    Area("/area/station/public/quantum/medbay", Colors.QUANTUMPAD),
    Area("/area/station/public/quantum/science", Colors.QUANTUMPAD),
    Area("/area/station/public/quantum/security", Colors.QUANTUMPAD),
    Area("/area/station/public/quantum/service", Colors.QUANTUMPAD),
]

AREAS = (
    HALLWAY_AREAS
    + SUPPLY_AREAS
    + COMMAND_AREAS
    + ATMOS_AREAS
    + MAINTS_AREAS
    + ENGINEERING_AREAS
    + PUBLIC_AREAS
    + SECURITY_AREAS
    + ARRIVALS_AREAS
    + MEDBAY_AREAS
    + SCIENCE_AREAS
    + AI_SAT_AREAS
    + SERVICE_AREAS
    + SOLARS_AREAS
    + ESCAPE_POD_AREAS
    + MISC_AREAS
    + QUANTUMPAD_AREAS
    + ASTEROID_AREAS
)


def render_map(
    dmm_filename: Path,
    output_path: Path,
    output_type: OutputType = OutputType.WIKI,
    labels: LabelType = LabelType.NONE,
):
    alpha = "ff"
    zoom_level = 8
    font_size = 16
    outline = "#00000000"

    if output_type == OutputType.WEBMAP:
        alpha = "35"
        zoom_level = 32
        font_size = 64
        outline = None

    dmm = DMM.from_file(dmm_filename)
    font_file = importlib.resources.files("paralysis.resources").joinpath(
        "Minimal5x7.ttf"
    )

    fnt = ImageFont.truetype(font_file, font_size)
    image = Image.new(
        size=(int(dmm.extents[0] * zoom_level), int(dmm.extents[1] * zoom_level)),
        mode="RGBA",
    )
    draw = ImageDraw.Draw(image)
    if output_type == OutputType.WIKI:
        draw.fontmode = "1"
    for Area in AREAS:
        area_points = set()
        for coord in dmm.coords():
            tile = dmm.tiledef(*coord)
            if tile.area_path() == Area.area:
                area_points.add((coord[0], coord[1]))

        myarray = np.zeros((256, 256))
        for point in area_points:
            myarray[point] = 1
        myarray = myarray.astype(np.int32)
        polygons = [p[0]["coordinates"] for p in rasterio.features.shapes(myarray)]

        polygon_process_order = list()
        dupe_polygons = set()

        # The last polygon is usually fucked up
        polygons.pop()

        for polygon in polygons:
            first_coordinate = [int(x) for x in reversed(polygon[0][0])]
            # print(f"area={Area.area} polygon={polygon} first_coordinate={first_coordinate}")
            tiledef = dmm.tiledef(*[int(x) for x in reversed(polygon[0][0])], 1)

            if 0 in first_coordinate:
                continue

            # If our first coordinate is space, this is an inner hole in a
            # polygon that's just space. We want to render them last because
            # transparent polygons will still replace filled polygons
            if tiledef.area_path().child_of("/area/space"):
                polygon_process_order.append(polygon)
            else:
                polygon_process_order.insert(0, polygon)

        for idx, polygon in enumerate(polygon_process_order):
            tupled_polygon = tuple(x for xs in polygon for x in xs)
            if tupled_polygon in dupe_polygons:
                continue
            dupe_polygons.add(tupled_polygon)
            color = f"{Area.color}{alpha}"

            tiledef = dmm.tiledef(*[int(x) for x in reversed(polygon[0][0])], 1)
            if tiledef.area_path().child_of(
                "/area/space"
            ) and not tiledef.area_path().child_of("/area/space/nearstation/disposals"):
                color = "#00000000"
            elif tiledef.area_path() != Area.area:
                # We can't just skip polygons whose first coordinates don't
                # contain the same area because we might be looking at the
                # outside of a polygon which has an inner hole that isn't the
                # same area, and this won't get matched here.
                #
                # In general these areas are hallways that form loops, which is
                # why hallways are drawn first.
                color = "#00000000"
            elif (
                Area.map_color_overrides
                and dmm.filepath.stem in Area.map_color_overrides
            ):
                color = Area.map_color_overrides[dmm.filepath.stem]
                color = f"{color}{alpha}"

            flipped = [
                (int((y - 1) * zoom_level), int((255 - x + 1) * zoom_level))
                for (x, y) in polygon[0]
            ]
            draw.polygon(flipped, fill=color, outline=outline)

            print(f"polygon area={Area.area} idx={idx} => {polygon} => {color}")

            msg = None

            # Put the text label on the first polygon, this may be wrong
            # at some point but then we can configure it
            if labels == LabelType.ROOMS and Area.text and idx == 0:
                msg = Area.text
            elif labels == LabelType.POLYGONS:
                path_leaf = str(Area.area).split("/")[-1]
                msg = f"{path_leaf}{idx}"

            if not labels or not msg:
                continue
            lir = largestinteriorrectangle.lir(np.array([flipped], np.int32))
            x, y, width, height = lir
            best_fit_rect = [
                [x, y],
                [x + width, y],
                [x + width, y + height],
                [x, y + height],
            ]
            shapely_poly = Polygon(best_fit_rect)
            centroid = shapely_poly.centroid
            rect = draw.textbbox(xy=(centroid.x, centroid.y), text=msg)
            (left, top, right, bottom) = rect
            text_xy = (
                left - ((right - left) / 2),
                top - ((bottom - top) / 2),
            )
            if output_type == OutputType.WEBMAP:
                draw.text(
                    text_xy,
                    msg,
                    fill="white",
                    font=fnt,
                    stroke_fill="black",
                    stroke_width=2,
                )
            elif output_type == OutputType.WIKI:
                draw.text(
                    text_xy,
                    msg,
                    fill="white",
                    font=fnt,
                )

    output_path.mkdir(parents=True, exist_ok=True)
    image.save(output_path / dmm.filepath.with_suffix(f".{output_type.name}.png").name)


@click.command()
@click.option("--dmm_file", required=True)
@click.option("--output_path", required=True)
@click.option("--output_type", type=click.Choice(["wiki", "webmap"]), default="wiki")
@click.option(
    "--labels", type=click.Choice(["rooms", "polygons", "none"]), default="none"
)
@logger.catch
def main(dmm_file: str, output_path: str, output_type: str, labels: str):
    render_map(Path(dmm_file), Path(output_path), OutputType[output_type.upper()], LabelType[labels.upper()])

