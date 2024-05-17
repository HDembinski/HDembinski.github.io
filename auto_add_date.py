import sys
import nbformat
import subprocess as subp

for fn in sys.argv[1:]:
    with open(fn) as f:
        nb = nbformat.read(f, as_version=4)

    r = subp.run(
        ["git", "log", "--follow", "--format=%ad", "--date=short", fn], stdout=subp.PIPE
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

    with open(fn, "w") as f:
        nbformat.write(nb, f)
