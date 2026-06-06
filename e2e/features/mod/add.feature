Feature: Module registration
  As a user, I want to register modules from various sources
  so that I can install them to my AI assistants.

  Scenario: Add a module from a local folder
    Given a module "my-module" with skills, commands, and agents
    When I run lola "mod add {module_path}"
    Then the exit code should be 0
    And the output should contain "Added my-module"
    And the directory "{lola_home}/modules/my-module" should exist
