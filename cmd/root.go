package cmd

import (
	"os"

	"github.com/spf13/cobra"
)

var rootCmd = &cobra.Command{
	Use:   "lola",
	Short: "AI Context Package Manager",
	Long: `lola - Universal AI Context Package Manager

Lola is a universal AI Context Package Manager, for skills, plugins,
profiles or Context Modules. Lola strives for AI sovereignty without
vendor lock-in. Write your AI Skills once, run anywhere.

Quick start:
  lola mod add [git-url|folder|zip|tar]    Add a module
  lola mod ls                               List modules
  lola install [module] -a [assistant]     Install skills`,
}

func Execute() {
	err := rootCmd.Execute()
	if err != nil {
		os.Exit(1)
	}
}

func init() {
	rootCmd.Version = currentVersion()
}
