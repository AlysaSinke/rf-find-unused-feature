from robotframework_find_unused.common.const import KeywordData
from robotframework_find_unused.common.normalize import normalize_keyword_name
from robotframework_find_unused.convert.convert_keyword import (
    get_keyword_name_match_pattern,
    get_keyword_name_parts,
)
from robotframework_find_unused.visitors.robot.keyword_visitor import (
    keyword_definition_manager,
)

KeywordDefinitionManager = keyword_definition_manager.KeywordDefinitionManager


def _make_embedded_keyword(library: str) -> KeywordData:
    name = 'A Warning Message With The Text "${warning_text}" Should Pop Up'
    normalized_name = normalize_keyword_name(name)
    name_parts = get_keyword_name_parts(normalized_name)

    return KeywordData(
        name=name,
        normalized_name=normalized_name,
        name_parts=name_parts,
        name_match_pattern=get_keyword_name_match_pattern(name_parts),
        type="CUSTOM_RESOURCE",
        argument_use_count={},
        deprecated=False,
        private=False,
        use_count=0,
        returns=None,
        return_use_count=0,
        arguments=None,
        library=library,
    )


def test_embedded_keyword_match_uses_canonical_definition_instance() -> None:
    stale_duplicate = _make_embedded_keyword("assertions")
    canonical_definition = _make_embedded_keyword(
        "batch_processing_assertions",
    )

    manager = KeywordDefinitionManager(
        [stale_duplicate, canonical_definition],
        [],
    )

    keyword = manager.get_keyword_definition(
        (
            'Then a warning message with the text '
            '"Niet alle transacties geboekt" should pop up'
        ),
    )
    keyword.use_count += 1

    counted_keywords = list(manager.keywords.values())
    assert len(counted_keywords) == 1
    assert counted_keywords[0] is canonical_definition
    assert counted_keywords[0].use_count == 1
    assert stale_duplicate.use_count == 0


def _make_plain_keyword(name: str, library: str) -> KeywordData:
    normalized_name = normalize_keyword_name(name)
    return KeywordData(
        name=name,
        normalized_name=normalized_name,
        name_parts=[normalized_name],
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


def test_same_normalized_keyword_name_can_be_selected_by_library_prefix() -> None:
    run_batch_definition = _make_plain_keyword("Run Batch Process", "run_batch")
    imported_definition = _make_plain_keyword(
        "Run Batch Process",
        "run_journalising_batches",
    )

    manager = KeywordDefinitionManager(
        [run_batch_definition, imported_definition],
        [],
    )

    keyword = manager.get_keyword_definition("run_batch.Run Batch Process")

    assert keyword is run_batch_definition


def test_same_normalized_keyword_name_keeps_canonical_when_unqualified() -> None:
    first_definition = _make_plain_keyword("Run Batch Process", "run_batch")
    later_definition = _make_plain_keyword(
        "Run Batch Process",
        "run_journalising_batches",
    )

    manager = KeywordDefinitionManager(
        [first_definition, later_definition],
        [],
    )

    keyword = manager.get_keyword_definition("Run Batch Process")

    assert keyword is later_definition
