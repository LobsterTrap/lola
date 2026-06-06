@marketplace
Feature: Marketplace removal
  As a user, I want to remove marketplaces
  so that I can clean up catalogs I no longer need.

  Scenario: Remove a marketplace
    Given a marketplace catalog served at "/catalog.yml" with modules
      | module    | version |
      | my-module | 1.0.0   |
    When I run lola "market add community {server_url}/catalog.yml"
    And I run lola "market rm community"
    Then the exit code should be 0
    And the output should contain "Removed"
