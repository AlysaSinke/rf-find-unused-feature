from robotframework_find_unused.resolve.resolve_import_string import resolve_import_string


def test_resolve_import_string_from_workspace_resources_dir(tmp_path):
    root = tmp_path
    importer_dir = root / "Tests" / "feature" / "domain" / "steps"
    importer_dir.mkdir(parents=True)

    expected_file = root / "Resources" / "shared" / "selectors" / "widget.yaml"
    expected_file.parent.mkdir(parents=True)
    expected_file.write_text("sample key: sample value\n", encoding="utf8")

    resolved = resolve_import_string(
        "shared/selectors/widget.yaml",
        importer_dir,
        root,
        set(),
    )

    assert resolved is not None
    assert resolved.path == expected_file


def test_resolve_import_string_from_workspace_root_path(tmp_path):
    root = tmp_path
    importer_dir = root / "Resources" / "suite" / "component"
    importer_dir.mkdir(parents=True)

    expected_file = root / "Resources" / "suite" / "component" / "config" / "labels.yaml"
    expected_file.parent.mkdir(parents=True)
    expected_file.write_text("label: value\n", encoding="utf8")

    resolved = resolve_import_string(
        "Resources/suite/component/config/labels.yaml",
        importer_dir,
        root,
        set(),
    )

    assert resolved is not None
    assert resolved.path == expected_file
