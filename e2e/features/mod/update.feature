Feature: Module update
  As a user, I want to update modules from their original sources
  so that I can get the latest versions.

  Scenario: Update when no modules are registered
    When I run lola "mod update"
    Then the exit code should be 0
    And the output should contain "No modules to update"
