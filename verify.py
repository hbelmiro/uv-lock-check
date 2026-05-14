#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shlex
import subprocess
from typing import Optional


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify that lock/requirements files are in sync.",
    )
    parser.add_argument("--command", required=True, help="The uv command to run.")
    return parser.parse_args(argv)


def _get_repo_root() -> str:
    workspace = os.environ.get("GITHUB_WORKSPACE")
    if workspace:
        return workspace
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        # Fallback to current directory if not in a git repository
        return os.getcwd()


def _resolve_directory_in_command(command: str, repo_root: str) -> str:
    try:
        args = shlex.split(command)
    except ValueError:
        # If we can't parse the command, return it unchanged
        return command

    modified = False
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--directory" and i + 1 < len(args):
            # Handle "--directory value" case
            dir_value = args[i + 1]
            if not os.path.isabs(dir_value):
                args[i + 1] = os.path.normpath(os.path.join(repo_root, dir_value))
                modified = True
            i += 2
        elif arg.startswith("--directory="):
            # Handle "--directory=value" case
            dir_value = arg[12:]  # Remove "--directory="
            if not os.path.isabs(dir_value):
                args[i] = f"--directory={os.path.normpath(os.path.join(repo_root, dir_value))}"
                modified = True
            i += 1
        else:
            i += 1

    return shlex.join(args) if modified else command


def main(argv: Optional[list[str]] = None) -> int:
    args = _parse_args(argv)
    command = _resolve_directory_in_command(args.command, _get_repo_root())

    print(f"Resolved COMMAND: {command}")
    print(f"Running command: {command}")

    try:
        result = subprocess.run(shlex.split(command))
        if result.returncode != 0:
            return 1
    except ValueError:
        print(f"❌ Invalid command format: {command}")
        return 1
    except FileNotFoundError:
        print(f"❌ Command not found: {command}")
        return 1

    diff = subprocess.run(["git", "diff", "--exit-code", "--quiet"])
    if diff.returncode != 0:
        try:
            names = subprocess.run(
                ["git", "diff", "--name-only"],
                capture_output=True,
                text=True,
                check=True,
            )
            print("❌ Existing files have been modified by sync:")
            print(names.stdout)
        except subprocess.CalledProcessError:
            print("❌ Existing files have been modified by sync (unable to list files)")
        print("This indicates that your lock files or requirements files are out of sync.")
        print("Please run the sync command and commit the changes.")
        return 1

    print("✅ All files are in sync")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
