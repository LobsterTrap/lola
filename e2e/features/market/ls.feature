@marketplace
Feature: List marketplaces
  As a user, I want to list registered marketplaces
  so that I can see which module catalogs are available.

  Scenario: List marketplaces
    Given a marketplace catalog served at "/catalog.yml" with modules
      | module    | version |
      | my-module | 1.0.0   |
    When I run lola "market add community {server_url}/catalog.yml"
    And I run lola "market ls"
    Then the exit code should be 0
    And the output should contain "community"
