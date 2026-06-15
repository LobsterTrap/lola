package cmd

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"

	"github.com/LobsterTrap/lola/internal/modules"
)

var modCmd = &cobra.Command{
	Use:   "mod",
	Short: "Manage lola modules",
}

var modAddCmd = &cobra.Command{
	Use:   "add <source>",
	Short: "Add a module from a source",
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		if err := modules.Add(args[0]); err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
	},
}

var modRmCmd = &cobra.Command{
	Use:   "rm <name>",
	Short: "Remove a registered module",
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		if err := modules.Remove(args[0]); err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
	},
}

var modLsCmd = &cobra.Command{
	Use:   "ls",
	Short: "List registered modules",
	Args:  cobra.NoArgs,
	Run: func(cmd *cobra.Command, args []string) {
		if err := modules.List(); err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
	},
}

var modInfoCmd = &cobra.Command{
	Use:   "info [name]",
	Short: "Show detailed info for a module",
	Args:  cobra.MaximumNArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		name := ""
		if len(args) > 0 {
			name = args[0]
		}
		if err := modules.Info(name); err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
	},
}

var modUpdateCmd = &cobra.Command{
	Use:   "update [name]",
	Short: "Update a module from its source",
	Args:  cobra.MaximumNArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		name := ""
		if len(args) > 0 {
			name = args[0]
		}
		if err := modules.Update(name); err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
	},
}

var modInitCmd = &cobra.Command{
	Use:   "init <name>",
	Short: "Scaffold a new module",
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		if err := modules.Init(args[0]); err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
	},
}

func init() {
	modCmd.AddCommand(modAddCmd, modRmCmd, modLsCmd, modInfoCmd, modUpdateCmd, modInitCmd)
	rootCmd.AddCommand(modCmd)
}
