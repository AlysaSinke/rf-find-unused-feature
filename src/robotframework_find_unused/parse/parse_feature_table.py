from pathlib import Path


def get_feature_table_cells(file_path: Path) -> list[str]:
    """
    Return all non-empty cell values from Gherkin table rows.

    Table rows in feature files start with `|` and can appear in Examples blocks
    and step data tables.
    """
    with file_path.open(encoding="utf8") as f:
        raw_lines = f.readlines()

    cells: list[str] = []
    for raw_line in raw_lines:
        row_cells = _get_cells_from_table_row(raw_line)
        if len(row_cells) == 0:
            continue
        cells.extend(row_cells)

    return cells


def _get_cells_from_table_row(raw_line: str) -> list[str]:
    line = raw_line.strip()
    if not line.startswith("|"):
        return []

    row = line.strip("|")
    if row == "":
        return []

    cells = [cell.strip() for cell in row.split("|")]
    return [cell for cell in cells if cell != ""]
