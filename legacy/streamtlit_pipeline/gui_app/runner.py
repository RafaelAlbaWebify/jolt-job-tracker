from __future__ import annotations

import datetime as dt
import subprocess
import sys
import traceback
from pathlib import Path
from typing import Tuple


def _stamp() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def _write_log(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", errors="replace")


def run_capture(capture_script: Path, pages: int, run_phase2: bool, timeout_seconds: int = 7200) -> Tuple[int, str]:
    """Run capture script and always write a launcher-level log.

    This log is created by Streamlit before the subprocess starts, so it exists even if
    the capture script crashes before initializing its own diagnostic logger.
    """
    logs_dir = Path.cwd() / "logs"
    stamp = _stamp()
    launcher_log = logs_dir / f"capture_launcher_v35_{stamp}.log"
    header = [
        "LinkedIn Job Capture Launcher Log v24",
        f"timestamp: {stamp}",
        f"cwd: {Path.cwd()}",
        f"python: {sys.executable}",
        f"capture_script: {capture_script}",
        f"capture_script_exists: {capture_script.exists()}",
        f"pages_requested: {pages}",
        f"run_phase2: {run_phase2}",
        "",
    ]
    _write_log(launcher_log, "\n".join(header) + "\n")
    if not capture_script.exists():
        msg = f"Capture script not found: {capture_script}\nLauncher log: {launcher_log}"
        _write_log(launcher_log, launcher_log.read_text(encoding='utf-8') + msg + "\n")
        return 127, msg
    stdin = f"{pages}\ny\n{'y' if run_phase2 else 'n'}\n"
    try:
        proc = subprocess.run(
            [sys.executable, "-u", str(capture_script)],
            input=stdin,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout_seconds,
            cwd=str(Path.cwd()),
        )
        body = proc.stdout or ""
        footer = f"\n\nreturncode: {proc.returncode}\nlauncher_log: {launcher_log}\n"
        _write_log(launcher_log, "\n".join(header) + "\n--- CAPTURE OUTPUT ---\n" + body + footer)
        return proc.returncode, body + footer
    except subprocess.TimeoutExpired as exc:
        body = (exc.stdout or "") if isinstance(exc.stdout, str) else str(exc.stdout or "")
        msg = body + "\nCAPTURE TIMEOUT.\n" + f"launcher_log: {launcher_log}\n"
        _write_log(launcher_log, "\n".join(header) + "\n--- CAPTURE OUTPUT BEFORE TIMEOUT ---\n" + msg)
        return 124, msg
    except Exception:
        tb = traceback.format_exc()
        msg = f"CAPTURE LAUNCHER EXCEPTION\n{tb}\nlauncher_log: {launcher_log}\n"
        _write_log(launcher_log, "\n".join(header) + "\n" + msg)
        return 1, msg


def run_parser(parser_runner: Path, timeout_seconds: int = 1800) -> Tuple[int, str]:
    logs_dir = Path.cwd() / "logs"
    stamp = _stamp()
    parser_log = logs_dir / f"parser_launcher_v34_{stamp}.log"
    header = [
        "LinkedIn Parser Launcher Log v24",
        f"timestamp: {stamp}",
        f"cwd: {Path.cwd()}",
        f"python: {sys.executable}",
        f"parser_runner: {parser_runner}",
        f"parser_runner_exists: {parser_runner.exists()}",
        "",
    ]
    _write_log(parser_log, "\n".join(header) + "\n")
    if not parser_runner.exists():
        msg = f"Parser runner not found: {parser_runner}\nParser launcher log: {parser_log}"
        _write_log(parser_log, parser_log.read_text(encoding='utf-8') + msg + "\n")
        return 127, msg
    try:
        proc = subprocess.run(
            [sys.executable, "-u", str(parser_runner)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout_seconds,
            cwd=str(Path.cwd()),
        )
        body = proc.stdout or ""
        footer = f"\n\nreturncode: {proc.returncode}\nparser_launcher_log: {parser_log}\n"
        _write_log(parser_log, "\n".join(header) + "\n--- PARSER OUTPUT ---\n" + body + footer)
        return proc.returncode, body + footer
    except subprocess.TimeoutExpired as exc:
        body = (exc.stdout or "") if isinstance(exc.stdout, str) else str(exc.stdout or "")
        msg = body + "\nPARSER TIMEOUT.\n" + f"parser_launcher_log: {parser_log}\n"
        _write_log(parser_log, "\n".join(header) + "\n--- PARSER OUTPUT BEFORE TIMEOUT ---\n" + msg)
        return 124, msg
    except Exception:
        tb = traceback.format_exc()
        msg = f"PARSER LAUNCHER EXCEPTION\n{tb}\nparser_launcher_log: {parser_log}\n"
        _write_log(parser_log, "\n".join(header) + "\n" + msg)
        return 1, msg
