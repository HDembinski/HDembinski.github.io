import sys
import nbformat
import subprocess as subp
from pathlib import Path
import os


def get_date(fn: Path):
    r = subp.run(
        [
            "git",
            "log",
            "--find-renames=90%",
            "--follow",
            "--format=%ad",
            "--date=short",
            str(fn),
        ],
        stdout=subp.PIPE,
    )
    dates = [x for x in r.stdout.decode().split("\n") if x]
    return dates[-1]


output_path = Path("posts_preprocessed")

input_files = [Path(fn) for fn in Path("posts").rglob("*.*")]

for fn in input_files:
    if fn.suffix not in (".ipynb", ".md"):
        continue

    date = get_date(fn)

    front_matter = f"""---
date: {date}
---
"""

    with open(fn, encoding="utf-8") as f:
        doc = nbformat.read(f, as_version=4)
        if doc.cells and doc.cells[0].cell_type != "raw":
            doc.cells = [nbformat.v4.new_raw_cell(front_matter)] + doc.cells
        nbformat.write(doc, output_path / fn.name)
