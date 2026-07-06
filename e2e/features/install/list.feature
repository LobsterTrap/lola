Feature: List installed modules
  As a user, I want to list all installed modules
  so that I can see what is currently active.

  Scenario: List installed modules when none are installed
    When I run lola "list"
    Then the exit code should be 0
    And the output should contain "No modules installed"

  Scenario: List installed modules with an active installation
    Given a module "my-module" with skills, commands, and agents
    And the module "my-module" is installed to "claude-code"
    When I run lola "list"
    Then the exit code should be 0
    And the output should contain "my-module"
    And the output should contain "claude-code"
