@marketplace
Feature: Module search
  As a user, I want to search for modules across marketplaces
  so that I can discover available skills to install.

  Scenario: Search for a module across marketplaces
    Given a marketplace catalog served at "/catalog.yml" with modules
      | module      | version |
      | git-tools   | 1.0.0   |
      | python-lint | 2.0.0   |
    When I run lola "market add community {server_url}/catalog.yml"
    And I run lola "mod search git"
    Then the exit code should be 0
    And the output should contain "git-tools"
    And the output should not contain "python-lint"
