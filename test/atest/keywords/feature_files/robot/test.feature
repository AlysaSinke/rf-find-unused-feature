@smoke
Feature: Smoke Tests
  Test basic functionality

  Scenario: Login and navigate
    When I log in to Epic
    Then the Epic home screen should be loaded

  Scenario: Product navigation
    Given I log in to Epic
    When I navigate to product
    Then the product page should load
