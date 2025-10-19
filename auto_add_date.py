import sys
import nbformat
import subprocess as subp
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--dry-run", action="store_true")
parser.add_argument("file", nargs="+")

args = parser.parse_args()

for fn in args.file:
    with open(fn) as f:
        nb = nbformat.read(f, as_version=4)

    r = subp.run(
        [
            "git",
            "log",
            "--find-renames=90%",
            "--follow",
            "--format=%ad",
            "--date=short",
            fn,
        ],
        stdout=subp.PIPE,
    )
    dates = [x for x in r.stdout.decode().split("\n") if x]
    date = dates[-1]

    if nb.cells and nb.cells[0].cell_type != "raw":
        front_matter = f"""
---
date: {date}
---
"""
        print(f"adding frontmatter to {fn}\n{front_matter}")

        nb.cells = [nbformat.v4.new_raw_cell(front_matter)] + nb.cells

    if not args.dry_run:
        with open(fn, "w") as f:
            nbformat.write(nb, f)
