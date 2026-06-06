Feature: Installation scopes
  As a user, I want to install modules at different scopes
  so that I can choose between project-local and user-wide installations.

  Scenario: Install with project scope by default
    Given a module "my-module" with skills, commands, and agents
    And the module "my-module" is registered
    When I run lola "install my-module -a claude-code"
    Then the exit code should be 0
    And the directory "{project}/.claude/skills/skill1" should exist
