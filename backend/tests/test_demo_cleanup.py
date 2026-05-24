from fastapi.testclient import TestClient

from app.main import app
from app.services import demo_cleanup

client = TestClient(app)


def patch_cleanup_roots(tmp_path, monkeypatch) -> tuple[object, object, object]:
    backend_root = tmp_path / "backend"
    data_root = backend_root / "data"
    exports_root = data_root / "exports"
    history_root = data_root / "history"

    monkeypatch.setattr(demo_cleanup, "BACKEND_ROOT", backend_root)
    monkeypatch.setattr(demo_cleanup, "DATA_ROOT", data_root)
    monkeypatch.setattr(demo_cleanup, "EXPORTS_ROOT", exports_root)
    monkeypatch.setattr(demo_cleanup, "HISTORY_ROOT", history_root)
    return exports_root, history_root, backend_root


def test_demo_cleanup_deletes_files_under_exports_and_history(tmp_path, monkeypatch) -> None:
    exports_root, history_root, _ = patch_cleanup_roots(tmp_path, monkeypatch)
    (exports_root / "export_1").mkdir(parents=True)
    (history_root / "nested").mkdir(parents=True)
    (exports_root / "export_1" / "capture.xlsx").write_text("demo export", encoding="utf-8")
    (history_root / "jobs.jsonl").write_text("{}", encoding="utf-8")
    (history_root / "nested" / "old.json").write_text("{}", encoding="utf-8")

    response = client.post("/api/demo/cleanup")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["exports_files_deleted"] == 1
    assert data["history_files_deleted"] == 2
    assert data["directories_deleted"] >= 2
    assert list(exports_root.rglob("*")) == []
    assert list(history_root.rglob("*")) == []


def test_demo_cleanup_does_not_error_if_folders_are_missing(tmp_path, monkeypatch) -> None:
    patch_cleanup_roots(tmp_path, monkeypatch)

    response = client.post("/api/demo/cleanup")

    assert response.status_code == 200
    data = response.json()
    assert data["exports_files_deleted"] == 0
    assert data["history_files_deleted"] == 0
    assert data["directories_deleted"] == 0


def test_demo_cleanup_does_not_delete_files_outside_allowed_folders(tmp_path, monkeypatch) -> None:
    _, _, backend_root = patch_cleanup_roots(tmp_path, monkeypatch)
    protected_file = backend_root / "app" / "main.py"
    protected_file.parent.mkdir(parents=True)
    protected_file.write_text("protected", encoding="utf-8")

    response = client.post("/api/demo/cleanup")

    assert response.status_code == 200
    assert protected_file.exists()
    assert protected_file.read_text(encoding="utf-8") == "protected"


def test_demo_cleanup_refuses_root_outside_backend_data(tmp_path, monkeypatch) -> None:
    _, history_root, backend_root = patch_cleanup_roots(tmp_path, monkeypatch)
    unsafe_exports = tmp_path / "outside_exports"
    unsafe_exports.mkdir()
    (unsafe_exports / "file.txt").write_text("do not delete", encoding="utf-8")
    monkeypatch.setattr(demo_cleanup, "EXPORTS_ROOT", unsafe_exports)

    try:
        demo_cleanup.cleanup_demo_data()
    except ValueError as exc:
        assert "allowed demo data folder" in str(exc) or "backend/data" in str(exc)
    else:  # pragma: no cover - defensive assertion for safety boundary.
        raise AssertionError("Expected cleanup to reject an unsafe root.")

    assert (unsafe_exports / "file.txt").exists()
    assert history_root.parent == backend_root / "data"
