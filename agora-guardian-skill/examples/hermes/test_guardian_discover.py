#!/usr/bin/env python3
"""Regression tests for the shipped Hermes Guardian discovery tick."""

import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


sys.dont_write_bytecode = True
SCRIPT_PATH = Path(__file__).with_name("guardian-discover.py")
SPEC = importlib.util.spec_from_file_location("guardian_discover", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"could not load {SCRIPT_PATH}")
GUARDIAN_DISCOVER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GUARDIAN_DISCOVER)


class GuardianDiscoverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.kanban_path = Path(self.temp_dir.name) / "guardian-kanban.json"

    def test_default_kanban_uses_dedicated_state_directory(self) -> None:
        self.assertEqual(
            Path(GUARDIAN_DISCOVER.KANBAN),
            Path.home()
            / ".hermes"
            / "agora-guardian-state"
            / "guardian-kanban.json",
        )

    def run_tick(self, board: dict, ready: dict[str, int], now: int) -> tuple[dict, dict]:
        self.kanban_path.write_text(json.dumps(board), encoding="utf-8")
        output = io.StringIO()
        with (
            mock.patch.object(GUARDIAN_DISCOVER, "KANBAN", str(self.kanban_path)),
            mock.patch.object(GUARDIAN_DISCOVER, "now_ts", return_value=now),
            mock.patch.object(GUARDIAN_DISCOVER, "discover", return_value=ready),
            contextlib.redirect_stdout(output),
        ):
            GUARDIAN_DISCOVER.main()

        saved = json.loads(self.kanban_path.read_text(encoding="utf-8"))
        emitted = json.loads(output.getvalue())
        return saved, emitted

    def test_done_bounty_stays_done_while_still_judgeable(self) -> None:
        timeout_at = 1_000
        board = {
            "33": {
                "status": "done",
                "settlement_timeout_at": timeout_at,
                "started_at": None,
            }
        }

        saved, emitted = self.run_tick(
            board,
            ready={"33": timeout_at},
            now=timeout_at + GUARDIAN_DISCOVER.PRUNE_AFTER_SECS + 1,
        )

        self.assertEqual(saved["33"]["status"], "done")
        self.assertEqual(
            emitted,
            {"wakeAgent": False, "guardian_action": "NO_WORK"},
        )

    def test_old_terminal_bounty_is_pruned_after_it_leaves_discovery(self) -> None:
        timeout_at = 1_000
        board = {
            "33": {
                "status": "done",
                "settlement_timeout_at": timeout_at,
                "started_at": None,
            }
        }

        saved, emitted = self.run_tick(
            board,
            ready={},
            now=timeout_at + GUARDIAN_DISCOVER.PRUNE_AFTER_SECS + 1,
        )

        self.assertEqual(saved, {})
        self.assertEqual(
            emitted,
            {"wakeAgent": False, "guardian_action": "NO_WORK"},
        )


if __name__ == "__main__":
    unittest.main()
