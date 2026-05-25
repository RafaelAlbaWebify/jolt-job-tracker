from pathlib import Path
import json

from fastapi.testclient import TestClient

from app.main import app
from app.services import history_store

client = TestClient(app)


def raw_job(
    raw_text: str,
    source_url: str = "https://example.test/history-job",
    external_id: str = "history-1",
) -> dict[str, object]:
    return {
        "source": "manual_raw_jobs",
        "source_url": source_url,
        "raw_text": raw_text,
        "external_id": external_id,
        "capture_notes": ["history test fixture"],
    }


def support_job(title: str = "Technical Support Specialist", company: str = "Example SaaS") -> str:
    return f"""
Title: {title}
Company: {company}
Location: Vigo, Spain
Work mode: Remote
English required.
Support Microsoft 365, endpoint troubleshooting, and SaaS support workflows.
"""


def sample_capture_result(raw_jobs: list[dict[str, object]] | None = None) -> dict[str, object]:
    response = client.post(
        "/api/capture/run",
        json={
            "profile_id": "rafael_default",
            "source": "manual_raw_jobs",
            "max_results": 10,
            "dry_run": True,
            "raw_jobs": raw_jobs or [raw_job(support_job())],
        },
    )
    assert response.status_code == 200
    return response.json()


def save_capture_result(
    capture_result: dict[str, object] | None = None,
    include_duplicates: bool = False,
    default_application_status: str = "New",
) -> dict[str, object]:
    response = client.post(
        "/api/history/save-capture-result",
        json={
            "capture_result": capture_result or sample_capture_result(),
            "include_raw_text": False,
            "default_application_status": default_application_status,
            "include_duplicates": include_duplicates,
        },
    )
    assert response.status_code == 200
    return response.json()


def test_history_uses_ignored_backend_data_history_folder() -> None:
    assert history_store.HISTORY_ROOT == history_store.BACKEND_ROOT / "data" / "history"
    gitignore = (history_store.BACKEND_ROOT.parent / ".gitignore").read_text(encoding="utf-8")
    assert "backend/data/" in gitignore


def test_saving_capture_result_creates_history_records(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(history_store, "HISTORY_ROOT", tmp_path / "backend" / "data" / "history")
    monkeypatch.setattr(history_store, "HISTORY_FILE", tmp_path / "backend" / "data" / "history" / "jobs.jsonl")

    data = save_capture_result()

    assert data["saved_count"] == 1
    assert data["saved_new_count"] == 1
    assert data["total_input_count"] == 1
    assert data["duplicate_count"] == 0
    assert data["skipped_duplicate_count"] == 0
    assert data["errors"] == []
    assert history_store.HISTORY_FILE.exists()
    record = json.loads(history_store.HISTORY_FILE.read_text(encoding="utf-8").splitlines()[0])
    assert record["raw_text_included"] is False
    assert record["raw_text"] is None


def test_listing_saved_jobs_returns_records(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(history_store, "HISTORY_ROOT", tmp_path / "backend" / "data" / "history")
    monkeypatch.setattr(history_store, "HISTORY_FILE", tmp_path / "backend" / "data" / "history" / "jobs.jsonl")
    save_capture_result()

    response = client.get("/api/history/jobs")

    assert response.status_code == 200
    jobs = response.json()
    assert len(jobs) == 1
    assert jobs[0]["title"] == "Technical Support Specialist"
    assert jobs[0]["application_status"] == "New"


def test_getting_one_saved_job_works(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(history_store, "HISTORY_ROOT", tmp_path / "backend" / "data" / "history")
    monkeypatch.setattr(history_store, "HISTORY_FILE", tmp_path / "backend" / "data" / "history" / "jobs.jsonl")
    saved = save_capture_result()

    response = client.get(f"/api/history/jobs/{saved['history_ids'][0]}")

    assert response.status_code == 200
    assert response.json()["history_id"] == saved["history_ids"][0]


def test_updating_application_status_works(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(history_store, "HISTORY_ROOT", tmp_path / "backend" / "data" / "history")
    monkeypatch.setattr(history_store, "HISTORY_FILE", tmp_path / "backend" / "data" / "history" / "jobs.jsonl")
    saved = save_capture_result()

    response = client.patch(
        f"/api/history/jobs/{saved['history_ids'][0]}/status",
        json={"application_status": "Applied"},
    )

    assert response.status_code == 200
    assert response.json()["application_status"] == "Applied"

    listed = client.get("/api/history/jobs")
    assert listed.status_code == 200
    assert listed.json()[0]["application_status"] == "Applied"

    loaded = client.get(f"/api/history/jobs/{saved['history_ids'][0]}")
    assert loaded.status_code == 200
    assert loaded.json()["application_status"] == "Applied"


def test_duplicate_source_url_or_external_id_is_detected(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(history_store, "HISTORY_ROOT", tmp_path / "backend" / "data" / "history")
    monkeypatch.setattr(history_store, "HISTORY_FILE", tmp_path / "backend" / "data" / "history" / "jobs.jsonl")
    capture_result = sample_capture_result()
    first = save_capture_result(capture_result)
    second = save_capture_result(capture_result)

    assert first["saved_count"] == 1
    assert second["saved_count"] == 0
    assert second["saved_new_count"] == 0
    assert second["duplicate_count"] == 1
    assert second["skipped_duplicate_count"] == 1
    assert second["already_reviewed_count"] == 0
    jobs = client.get("/api/history/jobs").json()
    assert len(jobs) == 1
    assert jobs[0]["application_status"] == "New"


def test_fallback_duplicate_title_company_location_works(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(history_store, "HISTORY_ROOT", tmp_path / "backend" / "data" / "history")
    monkeypatch.setattr(history_store, "HISTORY_FILE", tmp_path / "backend" / "data" / "history" / "jobs.jsonl")
    first_result = sample_capture_result(
        [raw_job(support_job(), source_url="", external_id="fallback-1")]
    )
    second_result = sample_capture_result(
        [raw_job(support_job(), source_url="", external_id="fallback-2")]
    )

    save_capture_result(first_result)
    second = save_capture_result(second_result)

    assert second["saved_count"] == 0
    assert second["duplicate_count"] == 1
    assert second["skipped_duplicate_count"] == 1


def test_duplicate_include_mode_appends_visible_duplicate_record(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(history_store, "HISTORY_ROOT", tmp_path / "backend" / "data" / "history")
    monkeypatch.setattr(history_store, "HISTORY_FILE", tmp_path / "backend" / "data" / "history" / "jobs.jsonl")
    capture_result = sample_capture_result()
    first = save_capture_result(capture_result)
    second = save_capture_result(capture_result, include_duplicates=True)

    assert first["saved_count"] == 1
    assert second["saved_count"] == 1
    assert second["saved_new_count"] == 0
    assert second["duplicate_count"] == 1
    jobs = client.get("/api/history/jobs").json()
    assert len(jobs) == 2
    assert jobs[-1]["application_status"] == "Duplicate"


def test_skipped_duplicate_preserves_existing_status(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(history_store, "HISTORY_ROOT", tmp_path / "backend" / "data" / "history")
    monkeypatch.setattr(history_store, "HISTORY_FILE", tmp_path / "backend" / "data" / "history" / "jobs.jsonl")
    capture_result = sample_capture_result()
    first = save_capture_result(capture_result)
    response = client.patch(
        f"/api/history/jobs/{first['history_ids'][0]}/status",
        json={"application_status": "Follow Up"},
    )
    assert response.status_code == 200

    second = save_capture_result(capture_result)

    assert second["saved_count"] == 0
    assert second["already_reviewed_count"] == 1
    jobs = client.get("/api/history/jobs").json()
    assert len(jobs) == 1
    assert jobs[0]["application_status"] == "Follow Up"


def test_new_queue_status_update_works(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(history_store, "HISTORY_ROOT", tmp_path / "backend" / "data" / "history")
    monkeypatch.setattr(history_store, "HISTORY_FILE", tmp_path / "backend" / "data" / "history" / "jobs.jsonl")
    saved = save_capture_result()

    response = client.patch(
        f"/api/history/jobs/{saved['history_ids'][0]}/status",
        json={"application_status": "Waiting"},
    )

    assert response.status_code == 200
    assert response.json()["application_status"] == "Waiting"


def test_legacy_statuses_still_validate(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(history_store, "HISTORY_ROOT", tmp_path / "backend" / "data" / "history")
    monkeypatch.setattr(history_store, "HISTORY_FILE", tmp_path / "backend" / "data" / "history" / "jobs.jsonl")
    capture_result = sample_capture_result()

    response = client.post(
        "/api/history/save-capture-result",
        json={
            "capture_result": capture_result,
            "include_raw_text": False,
            "default_application_status": "Not started",
        },
    )

    assert response.status_code == 200
    jobs = client.get("/api/history/jobs").json()
    assert jobs[0]["application_status"] == "New"


def test_legacy_statuses_are_mapped_when_loaded(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(history_store, "HISTORY_ROOT", tmp_path / "backend" / "data" / "history")
    monkeypatch.setattr(history_store, "HISTORY_FILE", tmp_path / "backend" / "data" / "history" / "jobs.jsonl")
    saved = save_capture_result(default_application_status="Watchlist")

    jobs = client.get("/api/history/jobs").json()
    loaded = client.get(f"/api/history/jobs/{saved['history_ids'][0]}").json()

    assert jobs[0]["application_status"] == "Follow Up"
    assert loaded["application_status"] == "Follow Up"


def test_duplicate_against_actioned_history_is_saved_as_already_reviewed(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(history_store, "HISTORY_ROOT", tmp_path / "backend" / "data" / "history")
    monkeypatch.setattr(history_store, "HISTORY_FILE", tmp_path / "backend" / "data" / "history" / "jobs.jsonl")
    first = save_capture_result()
    response = client.patch(
        f"/api/history/jobs/{first['history_ids'][0]}/status",
        json={"application_status": "Applied"},
    )
    assert response.status_code == 200

    second = save_capture_result(sample_capture_result())

    assert second["saved_count"] == 0
    assert second["already_reviewed_count"] == 1
    jobs = client.get("/api/history/jobs").json()
    assert len(jobs) == 1
    assert jobs[-1]["application_status"] == "Applied"


def test_no_browser_automation_or_scraping_dependencies_added() -> None:
    backend_root = history_store.BACKEND_ROOT
    requirements = (backend_root / "requirements.txt").read_text(encoding="utf-8").lower()
    source_files = "\n".join(
        path.read_text(encoding="utf-8").lower()
        for path in (backend_root / "app").rglob("*.py")
        if "__pycache__" not in str(path)
    )

    assert "selenium" not in requirements
    assert "playwright" not in requirements
    assert "pyautogui" not in requirements
    assert "pywin32" not in requirements
    assert "import selenium" not in source_files
    assert "from selenium" not in source_files
    assert "import playwright" not in source_files
    assert "from playwright" not in source_files
    assert "import pyautogui" not in source_files
    assert "import win32" not in source_files
