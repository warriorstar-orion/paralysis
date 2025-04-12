# This script processes screenshots from the Mass-Screenshot Debug verb in SS13
# into a full map image. Loosely based on
# https://github.com/vortex1942/telescience/blob/master/src/tools/PhotoProcessor.py
# All .pngs in the rawimages folder will be processed. Exported file may be
# overwritten in the output.

from pathlib import Path

import click
from PIL import Image


@click.command()
@click.option("--input_dir", required=True, type=Path)
@click.option("--output_dir", required=True, type=Path)
@click.option("--output_filename", required=True)
@click.option("--verb_values", nargs=4, type=int)
def main(input_dir, output_dir, output_filename, verb_values):
    pixel_size = verb_values[3]
    half_chunk_size = verb_values[2]
    width = verb_values[0] + half_chunk_size - 2
    height = verb_values[1] + half_chunk_size - 2
    if (
        width < 1
        or height < 1
        or pixel_size < 1
        or half_chunk_size < 1
        or half_chunk_size * 2 >= width
        or half_chunk_size * 2 >= height
    ):
        print("Invalid arguments!")
        exit(1)
    width *= pixel_size
    height *= pixel_size
    half_chunk_size *= pixel_size

    masterexport = Image.new("RGBA", (width, height), color=(0, 0, 0, 255))
    imagelist = sorted(input_dir.glob("*.png"), key=lambda x: x.stat().st_mtime)
    imagecount = len(imagelist)
    chunk_size = half_chunk_size * 2 - pixel_size
    x = fc = 0
    y = height - chunk_size

    # For loop stitches raw images together
    for image_file in imagelist:
        photo = Image.open(image_file).convert("RGBA")
        masterexport.paste(photo, (x, y))
        x += chunk_size
        fc += 1
        if x >= width:
            x = 0
            y -= chunk_size
            y = max(y, 0)
            progress = fc / imagecount * 100
            print("%.1f" % progress, "%")
        x = min(x, width - chunk_size)

    output_filepath = output_dir / output_filename
    print(output_filepath)
    masterexport.save(output_filepath)
