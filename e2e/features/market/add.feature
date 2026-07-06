@marketplace
Feature: Marketplace registration
  As a user, I want to register marketplaces
  so I can discover and install modules from curated catalogs.

  Scenario: Add a marketplace
    Given a marketplace catalog served at "/catalog.yml" with modules
      | module     | version |
      | my-module  | 1.0.0   |
    When I run lola "market add community {server_url}/catalog.yml"
    Then the exit code should be 0
    And the output should contain "Added marketplace"
    And the file "{lola_home}/market/community.yml" should exist
    And the file "{lola_home}/market/cache/community.yml" should exist
