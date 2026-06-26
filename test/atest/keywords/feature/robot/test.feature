Feature: Login

  Scenario: Successful login
    Given I Open Login Page
    When I Type <username> Into Username
    Then I Should See Home
