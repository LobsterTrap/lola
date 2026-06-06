@marketplace
Feature: Marketplace update
  As a user, I want to update marketplace catalogs
  so that I can discover newly published modules.

  Scenario: Update a marketplace
    Given a marketplace catalog served at "/catalog.yml" with modules
      | module    | version |
      | my-module | 1.0.0   |
    When I run lola "market add community {server_url}/catalog.yml"
    And I run lola "market update community"
    Then the exit code should be 0
    And the output should contain "Updated"
