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
    diff_content: str = "",
) -> MagicMock:
    """Build a subprocess.run mock that dispatches on the command."""

    def _side_effect(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        cmd: str | list[str] = args[0] if args else kwargs.get("args", "")

        if isinstance(cmd, list) and cmd[:2] == ["git", "diff"]:
            if "--name-only" in cmd:
                return subprocess.CompletedProcess(cmd, 0, stdout=diff_names)
            if "--exit-code" in cmd:
                return subprocess.CompletedProcess(cmd, diff_rc)
            return subprocess.CompletedProcess(cmd, 0, stdout=diff_content)

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


# --- show diff ---


class TestShowDiff:
    def __init__(self):
        pass

    def test_no_diff_output_without_flag(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setenv("GITHUB_WORKSPACE", "/workspace")
        mock = _make_mock(
            diff_rc=1,
            diff_names="uv.lock\n",
            diff_content="diff --git a/uv.lock b/uv.lock\n-old\n+new\n",
        )
        monkeypatch.setattr(subprocess, "run", mock)

        verify.main(["--command", "uv sync"])

        captured = capsys.readouterr().out
        assert "uv.lock" in captured
        assert "diff --git" not in captured

    def test_show_diff_prints_diff_content(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setenv("GITHUB_WORKSPACE", "/workspace")
        mock = _make_mock(
            diff_rc=1,
            diff_names="uv.lock\n",
            diff_content="diff --git a/uv.lock b/uv.lock\n-old\n+new\n",
        )
        monkeypatch.setattr(subprocess, "run", mock)

        verify.main(["--command", "uv sync", "--show-diff"])

        captured = capsys.readouterr().out
        assert "diff --git a/uv.lock" in captured
        assert "-old" in captured
        assert "+new" in captured

    def test_show_diff_default_max_lines_is_200(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setenv("GITHUB_WORKSPACE", "/workspace")
        content = "\n".join(f"line {i}" for i in range(201))
        mock = _make_mock(diff_rc=1, diff_names="uv.lock\n", diff_content=content)
        monkeypatch.setattr(subprocess, "run", mock)

        verify.main(["--command", "uv sync", "--show-diff"])

        captured = capsys.readouterr().out
        assert "line 0" in captured
        assert "line 199" in captured
        assert "line 200" not in captured
        assert "1 more line omitted" in captured
        assert "showing 200/201" in captured

    def test_diff_max_lines_customizes_truncation(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setenv("GITHUB_WORKSPACE", "/workspace")
        content = "\n".join(f"line {i}" for i in range(10))
        mock = _make_mock(diff_rc=1, diff_names="uv.lock\n", diff_content=content)
        monkeypatch.setattr(subprocess, "run", mock)

        verify.main(["--command", "uv sync", "--show-diff", "--diff-max-lines", "5"])

        captured = capsys.readouterr().out
        assert "line 4" in captured
        assert "line 5" not in captured
        assert "5 more lines omitted" in captured
        assert "showing 5/10" in captured

    def test_diff_not_truncated_when_under_limit(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setenv("GITHUB_WORKSPACE", "/workspace")
        content = "\n".join(f"line {i}" for i in range(3))
        mock = _make_mock(diff_rc=1, diff_names="uv.lock\n", diff_content=content)
        monkeypatch.setattr(subprocess, "run", mock)

        verify.main(["--command", "uv sync", "--show-diff", "--diff-max-lines", "10"])

        captured = capsys.readouterr().out
        assert "line 0" in captured
        assert "line 1" in captured
        assert "line 2" in captured
        assert "omitted" not in captured

    def test_diff_at_exact_boundary_not_truncated(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setenv("GITHUB_WORKSPACE", "/workspace")
        content = "\n".join(f"line {i}" for i in range(5))
        mock = _make_mock(diff_rc=1, diff_names="uv.lock\n", diff_content=content)
        monkeypatch.setattr(subprocess, "run", mock)

        verify.main(["--command", "uv sync", "--show-diff", "--diff-max-lines", "5"])

        captured = capsys.readouterr().out
        assert "line 0" in captured
        assert "line 4" in captured
        assert "omitted" not in captured

    def test_show_diff_no_output_on_clean(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setenv("GITHUB_WORKSPACE", "/workspace")
        mock = _make_mock(diff_rc=0)
        monkeypatch.setattr(subprocess, "run", mock)

        rc = verify.main(["--command", "uv sync", "--show-diff"])

        captured = capsys.readouterr().out
        assert rc == 0
        assert "All files are in sync" in captured
        assert "diff --git" not in captured

    def test_truncation_message_shows_omitted_count(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setenv("GITHUB_WORKSPACE", "/workspace")
        content = "\n".join(f"line {i}" for i in range(150))
        mock = _make_mock(diff_rc=1, diff_names="uv.lock\n", diff_content=content)
        monkeypatch.setattr(subprocess, "run", mock)

        verify.main(["--command", "uv sync", "--show-diff", "--diff-max-lines", "50"])

        captured = capsys.readouterr().out
        assert "100 more lines omitted" in captured
        assert "showing 50/150" in captured

    def test_show_diff_fallback_on_git_diff_failure(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setenv("GITHUB_WORKSPACE", "/workspace")

        def _side_effect(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
            cmd: str | list[str] = args[0] if args else kwargs.get("args", "")
            if isinstance(cmd, list) and cmd[:2] == ["git", "diff"]:
                if "--name-only" in cmd:
                    return subprocess.CompletedProcess(cmd, 0, stdout="uv.lock\n")
                if "--exit-code" in cmd:
                    return subprocess.CompletedProcess(cmd, 1)
                raise subprocess.CalledProcessError(1, cmd)
            return subprocess.CompletedProcess(cmd, 0)

        mock = MagicMock(side_effect=_side_effect)
        monkeypatch.setattr(subprocess, "run", mock)

        rc = verify.main(["--command", "uv sync", "--show-diff"])

        assert rc == 1
        captured = capsys.readouterr().out
        assert "(unable to retrieve diff content)" in captured

    def test_diff_max_lines_rejects_non_positive(self) -> None:
        with pytest.raises(SystemExit, match="2"):
            verify.main(["--command", "uv sync", "--diff-max-lines", "0"])

        with pytest.raises(SystemExit, match="2"):
            verify.main(["--command", "uv sync", "--diff-max-lines", "-5"])
