Feature: Module sync
  As a user, I want to sync module installations from a config file
  so that I can declaratively manage my module setup.

  Scenario: Sync when config file does not exist
    When I run lola "sync"
    Then the exit code should be 1
    And the output should contain "Config file not found"
