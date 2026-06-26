from pathlib import Path

from robotframework_find_unused.commands.step.keyword_count_uses import (
    _count_python_imported_keyword_uses,
    _count_python_internal_keyword_uses,
)
from robotframework_find_unused.common.const import KeywordData
from robotframework_find_unused.common.normalize import normalize_keyword_name


def _make_python_keyword(name: str, library: str) -> KeywordData:
    return KeywordData(
        name=name,
        normalized_name=normalize_keyword_name(name),
        name_parts=[normalize_keyword_name(name)],
        name_match_pattern=None,
        type="CUSTOM_LIBRARY",
        argument_use_count={},
        deprecated=False,
        private=False,
        use_count=0,
        returns=None,
        return_use_count=0,
        arguments=None,
        library=library,
    )


def test_python_internal_keyword_helpers_are_marked_used() -> None:
    parser = _make_python_keyword("Parse Csv To Dataframe", "csv_parser")
    getter = _make_python_keyword("Get Cell Value From Dataframe", "csv_parser")
    getter.use_count = 3
    getter.python_call_targets_normalized = {
        normalize_keyword_name("Parse Csv To Dataframe"),
    }

    _count_python_internal_keyword_uses([parser, getter])

    assert parser.use_count == 1
    assert getter.use_count == 3


def test_python_internal_keyword_usage_propagates_transitively() -> None:
    first = _make_python_keyword("First", "demo_lib")
    second = _make_python_keyword("Second", "demo_lib")
    third = _make_python_keyword("Third", "demo_lib")

    first.use_count = 1
    first.python_call_targets_normalized = {normalize_keyword_name("Second")}
    second.python_call_targets_normalized = {normalize_keyword_name("Third")}

    _count_python_internal_keyword_uses([first, second, third])

    assert second.use_count == 1
    assert third.use_count == 1


def test_python_internal_keyword_usage_propagates_across_libraries() -> None:
    orchestrator = _make_python_keyword("Run Journals", "journal_runner")
    run_batch = _make_python_keyword("Run Batch Process", "run_batch")
    batch_id = _make_python_keyword("Get New Batch Job Id", "run_batch")

    orchestrator.use_count = 1
    orchestrator.python_call_targets_normalized = {
        normalize_keyword_name("Run Batch Process"),
    }
    run_batch.python_call_targets_normalized = {
        normalize_keyword_name("Get New Batch Job Id"),
    }

    _count_python_internal_keyword_uses([orchestrator, run_batch, batch_id])

    assert run_batch.use_count == 1
    assert batch_id.use_count == 1


def test_python_imported_calls_mark_keywords_as_used(tmp_path: Path) -> None:
    send_alert = _make_python_keyword("Send Alert", "send_alert")
    listener = tmp_path / "alert_listener.py"
    listener.write_text(
        (
            "import send_alert as alert\n\n"
            "def close():\n"
            "    alert.send_alert('subject', 'message')\n"
        ),
        encoding="utf8",
    )

    _count_python_imported_keyword_uses([listener], [send_alert])

    assert send_alert.use_count == 1


def test_python_module_level_local_calls_mark_keywords_as_used(
    tmp_path: Path,
) -> None:
    main_keyword = _make_python_keyword("Main", "script_tool")

    script = tmp_path / "script_tool.py"
    script.write_text(
        (
            "def main():\n"
            "    return 0\n\n"
            "if __name__ == '__main__':\n"
            "    main()\n"
        ),
        encoding="utf8",
    )

    _count_python_imported_keyword_uses([script], [main_keyword])

    assert main_keyword.use_count == 1


def test_python_module_level_call_propagates_to_local_helper(
    tmp_path: Path,
) -> None:
    helper_keyword = _make_python_keyword(
        "Import Features To Test Plan",
        "test_plan_manager",
    )

    script = tmp_path / "test_plan_manager.py"
    script.write_text(
        (
            "def import_features_to_test_plan():\n"
            "    return 0\n\n"
            "def main():\n"
            "    import_features_to_test_plan()\n"
            "    return 0\n\n"
            "if __name__ == '__main__':\n"
            "    main()\n"
        ),
        encoding="utf8",
    )

    _count_python_imported_keyword_uses([script], [helper_keyword])

    assert helper_keyword.use_count == 1
