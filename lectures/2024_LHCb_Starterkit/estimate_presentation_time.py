import nbformat
import sys

MINUTES_PER_MARKDOWN_CELL = 1
MINUTES_PER_CODE_CELL = 2


def count_cell_types(notebook_path):
    with open(notebook_path, "r", encoding="utf-8") as f:
        nb = nbformat.read(f, as_version=nbformat.NO_CONVERT)

    markdown_cells = 0
    code_cells = 0

    for cell in nb.cells:
        if cell.cell_type == "markdown":
            markdown_cells += 1
        elif cell.cell_type == "code":
            code_cells += 1

    return markdown_cells, code_cells


for arg in sys.argv[1:]:
    markdown_cells, code_cells = count_cell_types(arg)
    est_time = (
        markdown_cells * MINUTES_PER_MARKDOWN_CELL + code_cells * MINUTES_PER_CODE_CELL
    )
    print(
        f"Estimated time = {est_time} "
        f"(markdown {markdown_cells}, "
        f"code {code_cells})"
    )
