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
