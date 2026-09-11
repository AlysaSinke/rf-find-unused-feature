from test.atest.utils import AcceptanceTest


class TestCommandAcceptance(AcceptanceTest):
    def test_variables_feature_yaml_variable_files_exclude(self):
        self.run_test(
            ["variables", "./robot"],
            "./expected_output.log",
            __file__,
            expected_exit_code=1,
        )

    def test_variables_feature_yaml_variable_files_include(self):
        self.run_test(
            [
                "variables",
                "./robot",
                "--yaml-variable-files",
                "include",
            ],
            "./expected_output_include_yaml.log",
            __file__,
            expected_exit_code=2,
        )
