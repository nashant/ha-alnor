#!/usr/bin/env python3
"""Update version in manifest.json."""
import json
import sys
from pathlib import Path


def update_version(version: str) -> None:
    """Update the version in manifest.json."""
    manifest_path = Path("custom_components/alnor/manifest.json")

    if not manifest_path.exists():
        print(f"Error: {manifest_path} not found")
        sys.exit(1)

    # Read manifest
    with open(manifest_path, "r") as f:
        manifest = json.load(f)

    # Update version
    manifest["version"] = version

    # Write manifest
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")

    print(f"Updated manifest.json to version {version}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: update_version.py <version>")
        sys.exit(1)

    update_version(sys.argv[1])
