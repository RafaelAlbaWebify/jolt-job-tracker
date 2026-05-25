import importlib
import time

from app.services.experimental_linkedin_capture.legacy_card_detection import (
    LegacyScreenContext,
    screen_context_from_pyautogui,
)


class LegacyMouseControl:
    def dependency_error(self) -> str:
        try:
            importlib.import_module("pyautogui")
        except Exception:
            return "Install experimental dependencies from backend/requirements-experimental.txt."
        return ""

    def screen_context(self) -> LegacyScreenContext:
        py_auto = importlib.import_module("pyautogui")
        return screen_context_from_pyautogui(py_auto)

    def click_card(self, x: int, y: int) -> None:
        py_auto = importlib.import_module("pyautogui")
        py_auto.moveTo(x, y, duration=0.12)
        py_auto.click(x=x, y=y)

    def scroll_left_panel(self, amount: int = -5) -> None:
        py_auto = importlib.import_module("pyautogui")
        py_auto.scroll(amount)
        time.sleep(0.75)

    def navigate_to_url(self, url: str) -> None:
        py_auto = importlib.import_module("pyautogui")
        py_auto.hotkey("ctrl", "l")
        time.sleep(0.15)
        py_auto.write(url, interval=0.001)
        py_auto.press("enter")
        time.sleep(2.0)

    def mouse_position(self) -> tuple[int, int]:
        py_auto = importlib.import_module("pyautogui")
        position = py_auto.position()
        return int(position.x), int(position.y)

    def screen_size(self) -> tuple[int, int]:
        py_auto = importlib.import_module("pyautogui")
        size = py_auto.size()
        return int(size.width), int(size.height)

    def test_small_movement(self) -> None:
        py_auto = importlib.import_module("pyautogui")
        position = py_auto.position()
        x = int(position.x)
        y = int(position.y)
        py_auto.moveTo(x + 20, y, duration=0.15)
        py_auto.moveTo(x, y, duration=0.15)
