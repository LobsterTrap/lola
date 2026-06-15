// Copyright © 2026 LobsterTrap Contributors
// SPDX-License-Identifier: Apache-2.0

package main

import (
	"os"

	"github.com/LobsterTrap/lola/cmd"
)

func main() {
	if err := cmd.Execute(); err != nil {
		os.Exit(1)
	}
}
