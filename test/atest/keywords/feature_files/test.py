from test.atest.utils import AcceptanceTest


class TestCommandAcceptance(AcceptanceTest):
    def test_keywords_feature_files_with_count(self):
        """
        Test that keywords used in .feature files are correctly counted.

        This verifies:
        - Feature files are discovered and parsed
        - Steps in feature files count as keyword calls
        - BDD prefixes (Given/When/Then) are properly stripped for matching
        - Unused keywords are still correctly identified
        """
        self.run_test(
            ["keywords", "./robot", "--show-count", "--library", "include"],
            "./expected_output_count.log",
            __file__,
            expected_exit_code=2,  # 2 unused keywords
        )
