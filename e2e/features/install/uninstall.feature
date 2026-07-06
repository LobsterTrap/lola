Feature: Module uninstallation
  As a user, I want to uninstall modules from AI assistants
  so that I can remove skills I no longer need.

  Scenario: Uninstall a previously installed module
    Given a module "my-module" with skills, commands, and agents
    And the module "my-module" is installed to "claude-code"
    When I run lola "uninstall my-module -a claude-code"
    Then the exit code should be 0
    And the output should contain "Uninstalled"
    And the directory "{project}/.claude/skills/skill1" should not exist
