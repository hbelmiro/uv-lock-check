"""Tests for verify.py."""

from __future__ import annotations

import subprocess
from typing import Any
from unittest.mock import MagicMock

import pytest

import verify


def _make_mock(
    *,
    command_rc: int = 0,
    diff_rc: int = 0,
    diff_names: str = "",
) -> MagicMock:
    """Build a subprocess.run mock that dispatches on the command."""

    def _side_effect(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        cmd: str | list[str] = args[0] if args else kwargs.get("args", "")

        if isinstance(cmd, list) and cmd[:2] == ["git", "diff"]:
            if "--name-only" in cmd:
                return subprocess.CompletedProcess(cmd, 0, stdout=diff_names)
            return subprocess.CompletedProcess(cmd, diff_rc)

        if isinstance(cmd, list) and cmd[:2] == ["git", "rev-parse"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="/fallback/root")

        return subprocess.CompletedProcess(cmd, command_rc)

    mock = MagicMock(side_effect=_side_effect)
    return mock


# --- directory resolution ---


class TestResolveDirectory:
    def test_no_directory_arg_command_unchanged(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_WORKSPACE", "/workspace")
        mock = _make_mock()
        monkeypatch.setattr(subprocess, "run", mock)

        verify.main(["--command", "uv sync"])

        user_call = mock.call_args_list[0]
        assert user_call[0][0] == ["uv", "sync"]

    def test_relative_directory_resolved_to_absolute(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GITHUB_WORKSPACE", "/workspace")
        mock = _make_mock()
        monkeypatch.setattr(subprocess, "run", mock)

        verify.main(["--command", "uv sync --directory relative/path"])

        user_call = mock.call_args_list[0]
        assert user_call[0][0] == ["uv", "sync", "--directory", "/workspace/relative/path"]

    def test_relative_directory_equals_syntax_resolved(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GITHUB_WORKSPACE", "/workspace")
        mock = _make_mock()
        monkeypatch.setattr(subprocess, "run", mock)

        verify.main(["--command", "uv sync --directory=relative/path"])

        user_call = mock.call_args_list[0]
        assert user_call[0][0] == ["uv", "sync", "--directory=/workspace/relative/path"]

    def test_absolute_directory_unchanged(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_WORKSPACE", "/workspace")
        mock = _make_mock()
        monkeypatch.setattr(subprocess, "run", mock)

        verify.main(["--command", "uv sync --directory /absolute/path"])

        user_call = mock.call_args_list[0]
        assert user_call[0][0] == ["uv", "sync", "--directory", "/absolute/path"]

    def test_fallback_to_git_rev_parse(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GITHUB_WORKSPACE", raising=False)
        mock = _make_mock()
        monkeypatch.setattr(subprocess, "run", mock)

        verify.main(["--command", "uv sync --directory relative/path"])

        user_call = mock.call_args_list[1]
        assert user_call[0][0] == ["uv", "sync", "--directory", "/fallback/root/relative/path"]


# --- command execution ---


class TestCommandExecution:
    def test_command_failure_returns_exit_code_1(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_WORKSPACE", "/workspace")
        mock = _make_mock(command_rc=1)
        monkeypatch.setattr(subprocess, "run", mock)

        rc = verify.main(["--command", "uv sync"])

        assert rc == 1

    def test_command_with_platform_flags_unchanged(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GITHUB_WORKSPACE", "/workspace")
        mock = _make_mock()
        monkeypatch.setattr(subprocess, "run", mock)

        cmd = "uv pip compile --python-platform=linux pyproject.toml -o requirements-linux.txt"
        verify.main(["--command", cmd])

        user_call = mock.call_args_list[0]
        assert user_call[0][0] == ["uv", "pip", "compile", "--python-platform=linux", "pyproject.toml", "-o", "requirements-linux.txt"]

    def test_multiple_sequential_invocations(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_WORKSPACE", "/workspace")
        mock = _make_mock()
        monkeypatch.setattr(subprocess, "run", mock)

        rc1 = verify.main(["--command", "uv sync"])
        rc2 = verify.main(["--command", "uv pip compile pyproject.toml -o req.txt"])

        assert rc1 == 0
        assert rc2 == 0


# --- git diff detection ---


class TestGitDiff:
    def test_git_diff_dirty_returns_exit_code_1(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_WORKSPACE", "/workspace")
        mock = _make_mock(diff_rc=1, diff_names="uv.lock\n")
        monkeypatch.setattr(subprocess, "run", mock)

        rc = verify.main(["--command", "uv sync"])

        assert rc == 1

    def test_git_diff_clean_returns_exit_code_0(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_WORKSPACE", "/workspace")
        mock = _make_mock(diff_rc=0)
        monkeypatch.setattr(subprocess, "run", mock)

        rc = verify.main(["--command", "uv sync"])

        assert rc == 0

    def test_dirty_output_lists_changed_files(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setenv("GITHUB_WORKSPACE", "/workspace")
        mock = _make_mock(diff_rc=1, diff_names="uv.lock\nrequirements.txt\n")
        monkeypatch.setattr(subprocess, "run", mock)

        verify.main(["--command", "uv sync"])

        captured = capsys.readouterr().out
        assert "uv.lock" in captured
        assert "requirements.txt" in captured


# --- output messages ---


class TestOutputMessages:
    def test_success_message_printed(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setenv("GITHUB_WORKSPACE", "/workspace")
        mock = _make_mock()
        monkeypatch.setattr(subprocess, "run", mock)

        verify.main(["--command", "uv sync"])

        captured = capsys.readouterr().out
        assert "All files are in sync" in captured

    def test_failure_message_printed(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setenv("GITHUB_WORKSPACE", "/workspace")
        mock = _make_mock(diff_rc=1, diff_names="uv.lock\n")
        monkeypatch.setattr(subprocess, "run", mock)

        verify.main(["--command", "uv sync"])

        captured = capsys.readouterr().out
        assert "Existing files have been modified by sync" in captured
        assert "run the sync command and commit the changes" in captured

    def test_resolved_command_printed(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setenv("GITHUB_WORKSPACE", "/workspace")
        mock = _make_mock()
        monkeypatch.setattr(subprocess, "run", mock)

        verify.main(["--command", "uv sync"])

        captured = capsys.readouterr().out
        assert "Resolved COMMAND: uv sync" in captured
        assert "Running command: uv sync" in captured
