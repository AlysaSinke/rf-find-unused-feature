from test.atest.utils import AcceptanceTest


class TestCommandAcceptance(AcceptanceTest):
    def test_variables_feature_yaml_variable_files(self):
        self.run_test(
            ["variables", "./robot"],
            "./expected_output.log",
            __file__,
            expected_exit_code=2,
        )
