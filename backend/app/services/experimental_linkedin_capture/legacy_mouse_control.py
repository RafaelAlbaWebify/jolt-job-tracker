import importlib
import time


class LegacyMouseControl:
    def dependency_error(self) -> str:
        try:
            importlib.import_module("pyautogui")
        except Exception:
            return "Install experimental dependencies from backend/requirements-experimental.txt."
        return ""

    def click_card(self, x: int, y: int) -> None:
        py_auto = importlib.import_module("pyautogui")
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
