@smoke
Feature: Top-level CLI behavior
  As a user, I want basic CLI commands to work
  so that I can verify my lola installation.

  Scenario Outline: Show version
    When I run lola "<flag>"
    Then the exit code should be 0
    And the output should match /lola \d+\.\d+/

    Examples:
      | flag      |
      | --version |
      | -v        |

  Scenario Outline: Show help with flag
    When I run lola "<flag>"
    Then the exit code should be 0
    And the output should contain "AI Skills Package Manager"

    Examples:
      | flag   |
      | --help |
      | -h     |

  Scenario: Show help when invoked without arguments
    When I run lola with no arguments
    Then the exit code should be 2
    And the output should contain "AI Skills Package Manager"

  Scenario: No arguments lists available subcommands
    When I run lola with no arguments
    Then the exit code should be 2
    And the output should contain "mod"
    And the output should contain "install"
    And the output should contain "market"

  Scenario: Show subcommand help
    When I run lola "mod --help"
    Then the exit code should be 0
    And the output should contain "add"
    And the output should contain "ls"
    And the output should contain "rm"

  Scenario: Reject unknown subcommand
    When I run lola "nonexistent"
    Then the exit code should be 2
    And the output should contain "No such command"
