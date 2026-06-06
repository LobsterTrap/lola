Feature: Module initialization
  As a module author, I want to scaffold a new module
  so that I have a complete template to customize.

  Scenario: Initialize a new module
    When I run lola "mod init test-module"
    Then the exit code should be 0
    And the output should contain "Initialized module test-module"
    And the directory "{project}/test-module" should exist
