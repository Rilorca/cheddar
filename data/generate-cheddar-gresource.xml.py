#!/usr/bin/env python3

import sys
from pathlib import Path

infile = sys.argv[1]
outfile = sys.argv[2]
svgdir = sys.argv[3]
print(f"Using input file: {infile}")
print(f"Writing to output file: {outfile}")
print(f"SVG directory: {svgdir}")

with open(infile) as f_in, open(outfile, "w") as f_out:
    for line in f_in:
        if "@SVG_FILES@" in line:
            for svg in sorted(Path(svgdir).glob("*.svg")):
                f_out.write(
                    line.replace("@SVG_FILES@", f"{svg.parent.name}/{svg.name}")
                )
            continue

        f_out.write(line)
