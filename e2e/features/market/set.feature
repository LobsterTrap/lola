@marketplace
Feature: Marketplace enable/disable
  As a user, I want to enable or disable marketplaces
  so that I can control which catalogs are searched.

  Scenario: Disable a marketplace
    Given a marketplace catalog served at "/catalog.yml" with modules
      | module    | version |
      | my-module | 1.0.0   |
    When I run lola "market add community {server_url}/catalog.yml"
    And I run lola "market set community --disable"
    Then the exit code should be 0
    And the output should contain "disabled"
