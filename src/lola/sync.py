"""Sync modules from configuration file."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from packaging.specifiers import SpecifierSet, InvalidSpecifier
from packaging.version import Version


@dataclass
class ModuleSpec:
    """Specification for a module to install."""

    raw_line: str
    module_ref: str  # Could be name, marketplace ref, or URL
    version_spec: Optional[str] = None  # e.g., ">=1.0.0,<2.0"
    assistant: Optional[str] = None  # Specific assistant or None for all

    @property
    def module_name_only(self) -> str:
        """Extract module name without version spec."""
        # Remove version operators - module_ref should already be clean
        # but this ensures we get just the name part
        return self.module_ref.strip()

    @property
    def specifier(self) -> Optional[SpecifierSet]:
        """Parse version spec into SpecifierSet."""
        if not self.version_spec:
            return None
        try:
            return SpecifierSet(self.version_spec)
        except InvalidSpecifier:
            return None

    def matches_version(self, version: str) -> bool:
        """Check if version satisfies the specifier."""
        if not self.version_spec:
            return True  # No constraint means any version
        specifier = self.specifier
        if not specifier:
            return False
        try:
            return Version(version) in specifier
        except Exception:
            return False


def convert_tilde_spec(version_part: str) -> str:
    """
    Convert tilde version spec to standard specifier.

    ~1.2 means >=1.2,<1.3
    ~1.2.3 means >=1.2.3,<1.3.0
    """
    version_part = version_part.strip()
    parts = version_part.split(".")

    if len(parts) < 2:
        # Invalid tilde spec, return as-is and let packaging handle error
        return f"~={version_part}"

    # Get major.minor
    major = parts[0]
    minor = parts[1]

    # Create range: >=version, <next_minor
    next_minor = str(int(minor) + 1)
    return f">={version_part},<{major}.{next_minor}"


def convert_caret_spec(version_part: str) -> str:
    """
    Convert caret version spec to standard specifier.

    ^1.2 means >=1.2,<2.0
    ^1.2.3 means >=1.2.3,<2.0.0
    ^0.2.3 means >=0.2.3,<0.3.0 (special handling for 0.x)
    """
    version_part = version_part.strip()
    parts = version_part.split(".")

    if len(parts) < 1:
        # Invalid caret spec, return as-is
        return f"^{version_part}"

    major = parts[0]

    # For 0.x versions, lock to minor version
    if major == "0" and len(parts) >= 2:
        minor = parts[1]
        next_minor = str(int(minor) + 1)
        return f">={version_part},<0.{next_minor}"

    # For 1.x and above, lock to major version
    next_major = str(int(major) + 1)
    return f">={version_part},<{next_major}"


def parse_lolareq_line(line: str, line_num: int) -> Optional[ModuleSpec]:
    """
    Parse a single line from .lola-req.

    Returns None for blank lines or comments.
    Raises ValueError for invalid lines.
    """
    # Strip whitespace
    line = line.strip()

    # Skip blank lines and comments
    if not line or line.startswith("#"):
        return None

    # Split on '>>' to extract assistant (accept both '>>agent' and '>> agent')
    assistant = None
    if ">>" in line:
        parts = line.split(">>", 1)
        module_part = parts[0].strip()
        assistant = parts[1].strip()
    else:
        module_part = line

    # Extract version spec from module_ref
    module_ref = module_part
    version_spec = None

    # Try to split on version operators (order matters - check longer operators first)
    operators = ["==", ">=", "<=", "~=", "!=", ">", "<", "~", "^"]
    for op in operators:
        if op in module_part:
            idx = module_part.find(op)
            module_ref = module_part[:idx].strip()
            raw_version_spec = module_part[idx:].strip()

            # Convert ~ and ^ to standard operators
            if raw_version_spec.startswith("~") and not raw_version_spec.startswith(
                "~="
            ):
                # Tilde operator ~1.2
                version_spec = convert_tilde_spec(raw_version_spec[1:])
            elif raw_version_spec.startswith("^"):
                # Caret operator ^1.2
                version_spec = convert_caret_spec(raw_version_spec[1:])
            else:
                # Standard operator
                version_spec = raw_version_spec

            break

    if not module_ref:
        raise ValueError(f"Line {line_num}: Empty module reference")

    return ModuleSpec(
        raw_line=line,
        module_ref=module_ref,
        version_spec=version_spec,
        assistant=assistant,
    )


def load_lolareq(lolareq_path: Path) -> list[ModuleSpec]:
    """Load and parse .lola-req."""
    if not lolareq_path.exists():
        raise FileNotFoundError(f"Config file not found: {lolareq_path}")

    specs = []
    with open(lolareq_path, encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            try:
                spec = parse_lolareq_line(line, line_num)
                if spec:
                    specs.append(spec)
            except ValueError as e:
                # Re-raise with context
                raise ValueError(f"Error parsing {lolareq_path.name}: {e}") from e

    return specs
