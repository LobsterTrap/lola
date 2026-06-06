Feature: Module removal
  As a user, I want to remove modules from the lola registry
  so that I can clean up modules I no longer need.

  Scenario: Remove a registered module
    Given a module "my-module" with skills, commands, and agents
    And the module "my-module" is registered
    When I run lola "mod rm my-module --force"
    Then the exit code should be 0
    And the output should contain "Removed my-module"
    And the directory "{lola_home}/modules/my-module" should not exist

  Scenario: Remove a module that does not exist
    When I run lola "mod rm nonexistent --force"
    Then the exit code should be 1
    And the output should contain "not found"
