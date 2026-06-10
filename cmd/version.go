package cmd

import (
	"fmt"
	"runtime"
	"runtime/debug"

	"github.com/spf13/cobra"
)

// version is injected at build time:
// -ldflags "-X github.com/LobsterTrap/lola/cmd.version=v1.2.0"
var version string

// resolveVersion determines the version string based on available version sources
// in order of priority: build-time injection, go install module version, git commit hash, or default dev version.
//
// Parameters:
//   - version: version injected at build time via ldflags
//   - moduleVersion: version from debug.ReadBuildInfo().Main.Version
//   - vcsRevision: git commit hash from debug.ReadBuildInfo().Settings
//
// Returns the resolved version string following the fallback chain:
// 1. If version is set (build-time injection) → return it
// 2. If moduleVersion is set and not "(devel)" → return it
// 3. If vcsRevision is set → return "0.0.0-dev+" with first 7 chars of commit hash
// 4. Default → return "0.0.0-dev"
func resolveVersion(version, moduleVersion, vcsRevision string) string {
	switch {
	case version != "":
		return version
	case moduleVersion != "" && moduleVersion != "(devel)":
		return moduleVersion
	case vcsRevision != "":
		return "0.0.0-dev+" + vcsRevision[:min(7, len(vcsRevision))]
	default:
		return "0.0.0-dev"
	}
}

// currentVersion queries runtime build info and returns the resolved version.
// It extracts moduleVersion and vcsRevision from debug.ReadBuildInfo() and passes
// them to resolveVersion along with the build-time injected version variable.
func currentVersion() string {
	var moduleVersion, vcsRevision string
	if bi, ok := debug.ReadBuildInfo(); ok {
		moduleVersion = bi.Main.Version
		for _, s := range bi.Settings {
			if s.Key == "vcs.revision" {
				vcsRevision = s.Value
				break
			}
		}
	}
	return resolveVersion(version, moduleVersion, vcsRevision)
}

// versionCmd represents the version command.
var versionCmd = &cobra.Command{
	Use:   "version",
	Short: "Print lola version and platform info",
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Printf("lola version %s %s/%s\n", currentVersion(), runtime.GOOS, runtime.GOARCH)
	},
}

func init() {
	rootCmd.AddCommand(versionCmd)
	rootCmd.SetVersionTemplate("{{.Version}}\n")
}
