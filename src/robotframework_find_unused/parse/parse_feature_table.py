from pathlib import Path

from robotframework_find_unused.common.normalize import normalize_variable_name


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


def get_feature_table_selector_value_map(file_path: Path) -> dict[str, list[str]]:
    """
    Return selector-specific values from Gherkin table blocks.

    Each contiguous table block is interpreted with its first row as header and
    following rows as values. Header cells are normalized so they can be matched
    against normalized dynamic selector variable names.
    """
    with file_path.open(encoding="utf8") as f:
        raw_lines = f.readlines()

    table_rows: list[list[str]] = []
    selector_values: dict[str, list[str]] = {}

    for raw_line in raw_lines:
        row_cells = _get_cells_from_table_row(raw_line)
        if len(row_cells) == 0:
            _flush_table_block_into_selector_values(table_rows, selector_values)
            table_rows = []
            continue

        table_rows.append(row_cells)

    _flush_table_block_into_selector_values(table_rows, selector_values)
    return selector_values


def _get_cells_from_table_row(raw_line: str) -> list[str]:
    line = raw_line.strip()
    if not line.startswith("|"):
        return []

    row = line.strip("|")
    if row == "":
        return []

    cells = [cell.strip() for cell in row.split("|")]
    return [cell for cell in cells if cell != ""]


def _flush_table_block_into_selector_values(
    table_rows: list[list[str]],
    selector_values: dict[str, list[str]],
) -> None:
    if len(table_rows) < 2:
        return

    header = table_rows[0]
    width = len(header)
    if width == 0:
        return

    data_rows = [row for row in table_rows[1:] if len(row) == width]
    if len(data_rows) == 0:
        return

    for index, header_cell in enumerate(header):
        normalized_header = normalize_variable_name(
            header_cell,
            strip_decoration=False,
        )
        if normalized_header == "":
            continue

        values = selector_values.setdefault(normalized_header, [])
        for row in data_rows:
            value = row[index].strip()
            if value == "":
                continue
            values.append(value)
