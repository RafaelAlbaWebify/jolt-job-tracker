from pathlib import Path

from app.models import DemoCleanupResponse

BACKEND_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = BACKEND_ROOT / "data"
EXPORTS_ROOT = DATA_ROOT / "exports"
HISTORY_ROOT = DATA_ROOT / "history"


def _ensure_allowed_root(root: Path) -> Path:
    resolved_root = root.resolve()
    resolved_data = DATA_ROOT.resolve()
    if resolved_root not in {EXPORTS_ROOT.resolve(), HISTORY_ROOT.resolve()}:
        raise ValueError("Cleanup root is not an allowed demo data folder.")
    if resolved_data not in resolved_root.parents:
        raise ValueError("Cleanup root escaped backend/data.")
    return resolved_root


def _delete_tree_contents(root: Path) -> tuple[int, int]:
    resolved_root = _ensure_allowed_root(root)
    if not resolved_root.exists():
        return 0, 0

    files_deleted = 0
    directories_deleted = 0

    for path in sorted(resolved_root.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        resolved_path = path.resolve()
        if resolved_root not in resolved_path.parents:
            raise ValueError("Cleanup target escaped the allowed folder.")

        if path.is_file():
            path.unlink()
            files_deleted += 1
        elif path.is_dir():
            try:
                path.rmdir()
                directories_deleted += 1
            except OSError:
                pass

    return files_deleted, directories_deleted


def cleanup_demo_data() -> DemoCleanupResponse:
    exports_files_deleted, export_dirs_deleted = _delete_tree_contents(EXPORTS_ROOT)
    history_files_deleted, history_dirs_deleted = _delete_tree_contents(HISTORY_ROOT)

    return DemoCleanupResponse(
        status="completed",
        exports_files_deleted=exports_files_deleted,
        history_files_deleted=history_files_deleted,
        directories_deleted=export_dirs_deleted + history_dirs_deleted,
        warnings=[
            "Only backend/data/exports and backend/data/history were cleaned.",
            "Source code, specs, profiles, and documentation were not touched.",
        ],
    )
