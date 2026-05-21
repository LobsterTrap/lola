"""
config:
    Configuration and paths for the lola package manager
"""

from pathlib import Path
import os
from platformdirs import PlatformDirs

# Base lola directory
LOLA_HOME = Path(os.environ.get("LOLA_HOME", Path.home() / ".lola"))

# Where modules are stored after being added
MODULES_DIR = LOLA_HOME / "modules"

# Installation tracking file
INSTALLED_FILE = LOLA_HOME / "installed.yml"

# Marketplace directories
MARKET_DIR = LOLA_HOME / "market"
CACHE_DIR = MARKET_DIR / "cache"

# Skill definition filename
SKILL_FILE = "SKILL.md"

# MCP servers definition filename
MCPS_FILE = "mcps.json"

# Platform-specific directories for user-scope installations
_PLATFORM_DIRS = PlatformDirs("opencode", appauthor=False)


def get_user_config_dir() -> Path:
    """Get user configuration directory for OpenCode using platform conventions.

    Returns platform-appropriate app-specific config directory:
    - Linux/Unix: ~/.config/opencode
    - macOS: ~/Library/Application Support/opencode
    - Windows: %APPDATA%/opencode
    """
    return Path(_PLATFORM_DIRS.user_config_dir)
