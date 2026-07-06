Feature: Installation update
  As a user, I want to regenerate assistant files from source modules
  so that changes to modules are reflected in my assistants.

  Scenario: Update when no modules are installed
    When I run lola "update"
    Then the exit code should be 0
    And the output should contain "No installations to update"

  Scenario: Update an installed module
    Given a module "my-module" with skills, commands, and agents
    And the module "my-module" is installed to "claude-code"
    When I run lola "update my-module"
    Then the exit code should be 0
    And the output should contain "Update complete"
