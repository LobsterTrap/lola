@smoke
Feature: List registered modules
  As a user, I want to list modules in the lola registry
  so that I can see what modules are available for installation.

  Scenario: List modules when none are registered
    When I run lola "mod ls"
    Then the exit code should be 0
    And the output should contain "No modules found"

  Scenario: List modules with a registered module
    Given a module "my-module" with skills, commands, and agents
    And the module "my-module" is registered
    When I run lola "mod ls"
    Then the exit code should be 0
    And the output should contain "my-module"
    And the output should contain "1 skill"
    And the output should contain "1 command"
    And the output should contain "1 agent"
