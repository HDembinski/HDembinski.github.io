import nbformat
import subprocess as subp
from pathlib import Path


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


output_path = Path("posts")
output_path.mkdir(exist_ok=True)

input_files = [Path(fn) for fn in Path("_posts").rglob("*.*")]

for fn in input_files:
    if fn.suffix not in (".ipynb", ".md"):
        continue

    fn_out = output_path / fn.name
    date = get_date(fn)
    front_matter = f"""---
date: {date}
---
"""
    with open(fn, encoding="utf-8") as f:
        if fn.suffix == ".ipynb":
            doc = nbformat.read(f, as_version=4)
            if doc.cells and doc.cells[0].cell_type != "raw":
                doc.cells = [nbformat.v4.new_raw_cell(front_matter)] + doc.cells
            nbformat.write(doc, fn_out)
        elif fn.suffix == ".md":
            content = f.read()
            with open(fn_out, "w", encoding="utf-8") as f:
                f.write(front_matter + content)
