Feature: Module information
  As a user, I want to view detailed information about a module
  so that I can understand its contents before installing.

  Scenario: Show info for a registered module
    Given a module "my-module" with skills, commands, and agents
    And the module "my-module" is registered
    When I run lola "mod info my-module"
    Then the exit code should be 0
    And the output should contain "my-module"
    And the output should contain "skill1"
    And the output should contain "cmd1"
    And the output should contain "agent1"

  Scenario: Show info for a module that does not exist
    When I run lola "mod info nonexistent"
    Then the exit code should be 1
    And the output should contain "not found"
