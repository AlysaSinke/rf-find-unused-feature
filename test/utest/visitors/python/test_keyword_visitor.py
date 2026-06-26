from pathlib import Path

from robot.libdoc import LibraryDocumentation

from robotframework_find_unused.common.normalize import normalize_keyword_name
from robotframework_find_unused.resolve.resolve_python_keyword_data import (
    enrich_python_keyword_data,
)


def test_enrich_python_keywords_includes_internal_call_targets(tmp_path: Path) -> None:
    source = tmp_path / "keywords.py"
    source.write_text(
        (
            "def parse_csv_to_dataframe(path):\n"
            "    return path\n\n"
            "def get_cell_value_from_dataframe(path):\n"
            "    value = parse_csv_to_dataframe(path)\n"
            "    return value\n"
        ),
        encoding="utf8",
    )

    libdoc = LibraryDocumentation(source.as_posix())
    enriched = enrich_python_keyword_data(libdoc)

    by_name = {kw.doc.name: kw for kw in enriched}
    caller = by_name["Get Cell Value From Dataframe"]

    assert (
        normalize_keyword_name("Parse Csv To Dataframe")
        in caller.python_call_targets_normalized
    )


def test_enrich_python_keywords_marks_imported_proxies_as_non_local(
    tmp_path: Path,
) -> None:
    helper = tmp_path / "helper_lib.py"
    helper.write_text(
        (
            "def send_alert(subject, message):\n"
            "    return None\n"
        ),
        encoding="utf8",
    )

    source = tmp_path / "listener.py"
    source.write_text(
        (
            "import helper_lib as alert\n\n"
            "def trigger_alert(subject, message):\n"
            "    alert.send_alert(subject, message)\n"
        ),
        encoding="utf8",
    )

    libdoc = LibraryDocumentation(source.as_posix())
    enriched = enrich_python_keyword_data(libdoc)
    by_name = {kw.doc.name: kw for kw in enriched}

    assert by_name["Trigger Alert"].is_local_definition is True
    assert "Send Alert" not in by_name
