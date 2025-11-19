import nbformat
import subprocess as subp
from pathlib import Path
import json
import datetime

front_matter_template = """---
date: {date}
categories: {categories}
---
"""


def get_date(fn: Path) -> str:
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
    return dates[-1] if dates else datetime.date.today().strftime("%Y-%m-%d")


with open("tag_db.json", encoding="utf-8") as f:
    tag_db = json.load(f)


output_path = Path("posts")
output_path.mkdir(exist_ok=True)

input_files = [Path(fn) for fn in Path("_posts").rglob("*.*")]

for fn in input_files:
    if fn.suffix not in (".ipynb", ".md"):
        continue

    categories = tag_db.get(fn.name, [])

    front_matter = front_matter_template.format(
        date=get_date(fn),
        categories=json.dumps(categories),
    )

    fn_out = output_path / fn.name
    with open(fn, encoding="utf-8") as f:
        if fn.suffix == ".ipynb":
            doc = nbformat.read(f, as_version=4)
            # insert frontmatter
            if doc.cells and doc.cells[0].cell_type != "raw":
                doc.cells = [nbformat.v4.new_raw_cell(front_matter)] + doc.cells
            nbformat.write(doc, fn_out)
        elif fn.suffix == ".md":
            content = f.read()
            # insert frontmatter
            content = front_matter + content
            with open(fn_out, "w", encoding="utf-8") as f:
                f.write(content)
