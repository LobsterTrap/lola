Feature: Module installation
  As a user, I want to install modules to AI assistants
  so that skills, commands, and agents are available in my workflow.

  Scenario: Install a module to Claude Code
    Given a module "my-module" with skills, commands, and agents
    And the module "my-module" is registered
    When I run lola "install my-module -a claude-code"
    Then the exit code should be 0
    And the output should contain "claude-code"
    And the directory "{project}/.claude/skills/skill1" should exist
