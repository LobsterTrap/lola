# CLI Reference

Complete command reference for the Lola CLI. Use `lola --help` or `lola <command> --help` for detailed usage.

## Module Management (`lola mod`)

| Command                   | Description                                    |
| ------------------------- | ---------------------------------------------- |
| `lola mod add <source>`   | Add a module from git, folder, zip, or tar     |
| `lola mod ls`             | List registered modules                        |
| `lola mod info <name>`    | Show module details                            |
| `lola mod search <query>` | Search registered modules in the local registry |
| `lola mod init [name]`    | Initialize a new module                        |
| `lola mod update [name]`  | Update module(s) from source                   |
| `lola mod rm <name>`      | Remove a module                                |

## Marketplace Management (`lola market`)

| Command                            | Description                                   |
| ---------------------------------- | --------------------------------------------- |
| `lola market add <name> <url>`     | Register a marketplace                        |
| `lola market ls`                   | List registered marketplaces                  |
| `lola market search <query>`       | Search across enabled marketplaces            |
| `lola market update [name]`        | Update marketplace cache                      |
| `lola market set --enable <name>`  | Enable a marketplace                          |
| `lola market set --disable <name>` | Disable a marketplace                         |
| `lola market rm <name>`            | Remove a marketplace                          |

## Installation

| Command                                | Description                                   |
| -------------------------------------- | --------------------------------------------- |
| `lola install <module>`                | Install to all detected assistants             |
| `lola install <module> -a <assistant>` | Install to specific assistant                 |
| `lola install <module> --append-context <path>` | Append context reference                          |
| `lola uninstall <module>`              | Uninstall module                              |
| `lola list`                            | List all installations                        |
| `lola update`                          | Regenerate assistant files                    |
| `lola sync`                            | Install modules from `.lola-req`              |
