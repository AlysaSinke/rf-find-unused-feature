Feature: YAML variable files with feature usage

  Scenario: Use variables in feature steps
    Given I log ${resource_used}
    And I log ${yaml_step_used}

  Scenario Outline: Use YAML variable in examples table
    Given I log <table_value>

    Examples:
      | table_value         |
      | ${yaml_table_used}  |
      | literal             |
