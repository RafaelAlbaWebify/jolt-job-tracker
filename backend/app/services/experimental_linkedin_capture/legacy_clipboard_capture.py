import importlib
import time


DETAIL_READY_MARKERS = (
    "about the job",
    "easy apply",
    "save",
    "applicants",
    "remote",
    "hybrid",
    "on-site",
    "company",
    "job details",
)


class LegacyClipboardCapture:
    def dependency_error(self) -> str:
        try:
            importlib.import_module("pyautogui")
        except Exception:
            return "Install experimental dependencies from backend/requirements-experimental.txt."
        try:
            import tkinter  # noqa: F401
        except Exception:
            return "Python tkinter clipboard support is unavailable."
        return ""

    def copy_current_url(self) -> str:
        py_auto = importlib.import_module("pyautogui")
        py_auto.hotkey("ctrl", "l")
        time.sleep(0.15)
        py_auto.hotkey("ctrl", "c")
        time.sleep(0.2)
        return _clipboard_text().strip()

    def copy_visible_text(self) -> str:
        py_auto = importlib.import_module("pyautogui")
        py_auto.press("esc")
        time.sleep(0.1)
        py_auto.hotkey("ctrl", "a")
        time.sleep(0.15)
        py_auto.hotkey("ctrl", "c")
        time.sleep(0.35)
        py_auto.press("esc")
        return _clipboard_text().strip()


def raw_text_has_job_panel(raw_text: str, *, min_chars: int = 600) -> bool:
    lowered = raw_text.lower()
    marker_hits = sum(1 for marker in DETAIL_READY_MARKERS if marker in lowered)
    return len(raw_text) >= min_chars and marker_hits >= 2


def _clipboard_text() -> str:
    import tkinter

    root = tkinter.Tk()
    root.withdraw()
    try:
        return root.clipboard_get()
    except Exception:
        return ""
    finally:
        root.destroy()
