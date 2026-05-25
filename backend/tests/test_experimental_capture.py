from fastapi.testclient import TestClient

from app.main import app
from app.services.experimental_linkedin_capture.diagnostics import (
    EXP_BROWSER_URL_CAPTURED,
    EXP_CARD_CLICK_ATTEMPTED,
    EXP_CURRENT_JOB_ID_EXTRACTED,
    EXP_CURRENT_JOB_ID_MISSING,
    EXP_CAPTURE_DISABLED,
    EXP_CAPTURE_STARTED,
    EXP_DETAIL_TEXT_READY,
    EXP_DETAIL_TEXT_NOT_READY,
    EXP_DUPLICATE_JOB_ID,
    EXP_FOCUS_HANDOFF_COMPLETED,
    EXP_FOCUS_HANDOFF_STARTED,
    EXP_FOCUS_HANDOFF_WAITING,
    EXP_JOB_LIMIT_REACHED,
    EXP_NON_LINKEDIN_URL_CAPTURED,
    EXP_SELECTED_JOB_ADAPTER_DEPENDENCY_MISSING,
    EXP_SELECTED_JOB_CAPTURE_STARTED,
    EXP_VISIBLE_TEXT_CAPTURED,
    EXP_VISIBLE_TEXT_TOO_SHORT,
    EXP_URL_CURRENT_JOB_ID_MATCHED,
    diagnostic_event,
)
from app.services.experimental_linkedin_capture import runner
from app.services.experimental_linkedin_capture import windows_selected_job_adapter
from app.services.experimental_linkedin_capture.windows_selected_job_adapter import (
    SelectedJobSnapshot,
    WindowsSelectedJobCaptureAdapter,
)
from app.services.experimental_linkedin_capture.url_utils import (
    extract_current_job_id,
    extract_linkedin_job_id,
    is_duplicate_job_reference,
    normalize_linkedin_job_url,
    same_linkedin_job,
)


def test_experimental_capture_feature_flag_defaults_disabled(monkeypatch) -> None:
    monkeypatch.delenv("JOLT_ENABLE_EXPERIMENTAL_LINKEDIN_CAPTURE", raising=False)
    client = TestClient(app)

    response = client.get("/api/experimental-capture/linkedin/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["enabled"] is False
    assert payload["status"] == "disabled"
    assert payload["diagnostics"][0]["code"] == EXP_CAPTURE_DISABLED


def test_experimental_capture_start_disabled_response(monkeypatch) -> None:
    monkeypatch.delenv("JOLT_ENABLE_EXPERIMENTAL_LINKEDIN_CAPTURE", raising=False)
    client = TestClient(app)

    response = client.post(
        "/api/experimental-capture/linkedin/start",
        json={"max_pages": 2, "max_jobs": 10, "dry_run": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["enabled"] is False
    assert payload["status"] == "disabled"
    assert "disabled" in payload["message"].lower()


def test_experimental_capture_stop_disabled_noop(monkeypatch) -> None:
    monkeypatch.delenv("JOLT_ENABLE_EXPERIMENTAL_LINKEDIN_CAPTURE", raising=False)
    client = TestClient(app)

    response = client.post("/api/experimental-capture/linkedin/stop")

    assert response.status_code == 200
    payload = response.json()
    assert payload["enabled"] is False
    assert payload["status"] == "disabled"
    assert "no-op" in payload["message"]


def test_experimental_capture_status_disabled(monkeypatch) -> None:
    monkeypatch.delenv("JOLT_ENABLE_EXPERIMENTAL_LINKEDIN_CAPTURE", raising=False)
    client = TestClient(app)

    response = client.get("/api/experimental-capture/linkedin/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["enabled"] is False
    assert payload["status"] == "disabled"


def test_selected_job_capture_disabled_when_feature_flag_off(monkeypatch) -> None:
    monkeypatch.delenv("JOLT_ENABLE_EXPERIMENTAL_LINKEDIN_CAPTURE", raising=False)
    client = TestClient(app)

    response = client.post(
        "/api/experimental-capture/linkedin/start",
        json={"mode": "selected_job_only", "selected_job_only": True, "dry_run": False},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["enabled"] is False
    assert payload["status"] == "disabled"


def test_selected_job_capture_requires_explicit_selected_job_flag(monkeypatch) -> None:
    monkeypatch.setenv("JOLT_ENABLE_EXPERIMENTAL_LINKEDIN_CAPTURE", "true")
    client = TestClient(app)

    response = client.post(
        "/api/experimental-capture/linkedin/start",
        json={"mode": "selected_job_only", "selected_job_only": False, "dry_run": False},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "failed"
    assert "selected_job_only=true" in payload["message"]


def test_selected_job_focus_delay_validation(monkeypatch) -> None:
    monkeypatch.setenv("JOLT_ENABLE_EXPERIMENTAL_LINKEDIN_CAPTURE", "true")
    client = TestClient(app)

    response = client.post(
        "/api/experimental-capture/linkedin/start",
        json={
            "mode": "selected_job_only",
            "selected_job_only": True,
            "dry_run": False,
            "focus_delay_seconds": 1,
        },
    )

    assert response.status_code == 422


def test_experimental_capture_enabled_start_is_dry_run(monkeypatch) -> None:
    monkeypatch.setenv("JOLT_ENABLE_EXPERIMENTAL_LINKEDIN_CAPTURE", "true")
    client = TestClient(app)

    response = client.post(
        "/api/experimental-capture/linkedin/start",
        json={"max_pages": 2, "max_jobs": 5, "dry_run": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["enabled"] is True
    assert payload["status"] == "completed"
    assert len(payload["run"]["captured_jobs"]) == 4
    assert payload["captured_count"] == 4
    assert payload["can_review"] is True
    assert payload["run"]["diagnostics"][0]["code"] == EXP_CAPTURE_STARTED
    assert "no browser automation" in payload["message"].lower()


def test_enabled_dry_run_returns_mock_diagnostics(monkeypatch) -> None:
    monkeypatch.setenv("JOLT_ENABLE_EXPERIMENTAL_LINKEDIN_CAPTURE", "true")
    client = TestClient(app)

    response = client.post(
        "/api/experimental-capture/linkedin/start",
        json={"max_pages": 2, "max_jobs": 4, "dry_run": True},
    )

    assert response.status_code == 200
    payload = response.json()
    codes = {event["code"] for event in payload["run"]["diagnostics"]}
    assert EXP_CARD_CLICK_ATTEMPTED in codes
    assert EXP_URL_CURRENT_JOB_ID_MATCHED in codes
    assert EXP_DETAIL_TEXT_READY in codes
    assert EXP_DUPLICATE_JOB_ID in codes
    assert payload["run"]["captured_jobs"][2]["duplicate_of"] == 1


def test_enabled_dry_run_respects_max_jobs(monkeypatch) -> None:
    monkeypatch.setenv("JOLT_ENABLE_EXPERIMENTAL_LINKEDIN_CAPTURE", "true")
    client = TestClient(app)

    response = client.post(
        "/api/experimental-capture/linkedin/start",
        json={"max_pages": 2, "max_jobs": 2, "dry_run": True},
    )

    assert response.status_code == 200
    payload = response.json()
    codes = {event["code"] for event in payload["run"]["diagnostics"]}
    assert len(payload["run"]["captured_jobs"]) == 2
    assert EXP_JOB_LIMIT_REACHED in codes


def test_latest_dry_run_can_be_converted_to_capture_review(monkeypatch) -> None:
    monkeypatch.setenv("JOLT_ENABLE_EXPERIMENTAL_LINKEDIN_CAPTURE", "true")
    client = TestClient(app)
    client.post(
        "/api/experimental-capture/linkedin/start",
        json={"max_pages": 1, "max_jobs": 3, "dry_run": True},
    )

    response = client.post(
        "/api/experimental-capture/linkedin/review-latest",
        json={"profile_id": "rafael_default"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["profile_id"] == "rafael_default"
    assert payload["total_captured"] == 3
    assert payload["results"][0]["raw_job"]["source"] == "experimental_linkedin_mock"
    assert "mock experimental LinkedIn capture dry-run" in payload["results"][0]["raw_job"]["capture_notes"]
    assert any("latest experimental package" in warning for warning in payload["warnings"])


def test_selected_job_adapter_missing_dependency_returns_clear_error(monkeypatch) -> None:
    def raise_import_error(name: str):
        if name == "pyautogui":
            raise ImportError("missing pyautogui for test")
        return __import__(name)

    monkeypatch.setattr(windows_selected_job_adapter.importlib, "import_module", raise_import_error)

    run = WindowsSelectedJobCaptureAdapter().run(run_id="selected_missing", max_pages=1, max_jobs=1)

    assert run.status == "failed"
    assert "requirements-experimental.txt" in run.errors[0]
    assert run.diagnostics[-1].code == EXP_SELECTED_JOB_ADAPTER_DEPENDENCY_MISSING


class FakeSelectedJobAdapter(WindowsSelectedJobCaptureAdapter):
    def __init__(self, raw_text: str, source_url: str = "https://www.linkedin.com/jobs/search/?currentJobId=777") -> None:
        self.raw_text = raw_text
        self.source_url = source_url

    def _dependency_error(self) -> str:
        return ""

    def capture_snapshot(self) -> SelectedJobSnapshot:
        return SelectedJobSnapshot(
            source_url=self.source_url,
            raw_text=self.raw_text,
            diagnostics=[
                diagnostic_event(EXP_BROWSER_URL_CAPTURED, "Fake URL captured."),
                diagnostic_event(EXP_VISIBLE_TEXT_CAPTURED, "Fake visible text captured.", details={"text_length": len(self.raw_text)}),
            ],
            warnings=[],
            errors=[],
        )


def test_selected_job_runner_with_fake_adapter_returns_one_job(monkeypatch) -> None:
    monkeypatch.setenv("JOLT_ENABLE_EXPERIMENTAL_LINKEDIN_CAPTURE", "true")
    delays: list[int] = []
    monkeypatch.setattr(windows_selected_job_adapter.time, "sleep", lambda seconds: delays.append(seconds))
    ready_text = (
        "About the job\n"
        "Mock selected IT Support Engineer\n"
        "Company: Demo Selected Company\n"
        "Location: Remote, Spain\n"
        "Easy Apply Save applicants remote hybrid company job "
        + ("support troubleshooting endpoint Microsoft 365 " * 30)
    )
    monkeypatch.setattr(runner, "SELECTED_JOB_ADAPTER_FACTORY", lambda: FakeSelectedJobAdapter(ready_text))
    client = TestClient(app)

    response = client.post(
        "/api/experimental-capture/linkedin/start",
        json={"mode": "selected_job_only", "selected_job_only": True, "dry_run": False, "focus_delay_seconds": 2},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["captured_count"] == 1
    assert payload["can_review"] is True
    assert payload["run"]["captured_jobs"][0]["current_job_id"] == "777"
    codes = {event["code"] for event in payload["run"]["diagnostics"]}
    assert EXP_SELECTED_JOB_CAPTURE_STARTED in codes
    assert EXP_FOCUS_HANDOFF_STARTED in codes
    assert EXP_FOCUS_HANDOFF_WAITING in codes
    assert EXP_FOCUS_HANDOFF_COMPLETED in codes
    assert EXP_CURRENT_JOB_ID_EXTRACTED in codes
    assert EXP_DETAIL_TEXT_READY in codes
    assert delays == [1, 1]


def test_selected_job_too_short_text_produces_warning(monkeypatch) -> None:
    monkeypatch.setenv("JOLT_ENABLE_EXPERIMENTAL_LINKEDIN_CAPTURE", "true")
    monkeypatch.setattr(windows_selected_job_adapter.time, "sleep", lambda seconds: None)
    short_text = "About the job Save"
    monkeypatch.setattr(runner, "SELECTED_JOB_ADAPTER_FACTORY", lambda: FakeSelectedJobAdapter(short_text, "https://example.test/not-linkedin"))
    client = TestClient(app)

    response = client.post(
        "/api/experimental-capture/linkedin/start",
        json={"mode": "selected_job_only", "selected_job_only": True, "dry_run": False, "focus_delay_seconds": 2},
    )

    assert response.status_code == 200
    payload = response.json()
    codes = {event["code"] for event in payload["run"]["diagnostics"]}
    assert EXP_NON_LINKEDIN_URL_CAPTURED in codes
    assert EXP_CURRENT_JOB_ID_MISSING in codes
    assert EXP_VISIBLE_TEXT_TOO_SHORT in codes
    assert EXP_DETAIL_TEXT_NOT_READY in codes
    assert payload["run"]["captured_jobs"][0]["capture_state"] == "selected_job_only_unverified"


def test_selected_job_review_latest_uses_existing_capture_pipeline(monkeypatch) -> None:
    monkeypatch.setenv("JOLT_ENABLE_EXPERIMENTAL_LINKEDIN_CAPTURE", "true")
    monkeypatch.setattr(windows_selected_job_adapter.time, "sleep", lambda seconds: None)
    ready_text = (
        "Title: Selected Job Support Analyst\n"
        "Company: Demo Selected Company\n"
        "Location: Remote, Spain\n"
        "Work mode: Remote\n"
        "About the job Easy Apply Save applicants remote company job "
        + ("English support endpoint troubleshooting " * 30)
    )
    monkeypatch.setattr(runner, "SELECTED_JOB_ADAPTER_FACTORY", lambda: FakeSelectedJobAdapter(ready_text))
    client = TestClient(app)
    client.post(
        "/api/experimental-capture/linkedin/start",
        json={"mode": "selected_job_only", "selected_job_only": True, "dry_run": False, "focus_delay_seconds": 2},
    )

    response = client.post(
        "/api/experimental-capture/linkedin/review-latest",
        json={"profile_id": "rafael_default"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_captured"] == 1
    assert payload["results"][0]["raw_job"]["source"] == "experimental_linkedin_selected_job"
    assert "selected-job experimental capture" in payload["results"][0]["raw_job"]["capture_notes"]


def test_extract_current_job_id_from_query_variants() -> None:
    assert (
        extract_current_job_id("https://www.linkedin.com/jobs/search/?currentJobId=4123456789&start=25")
        == "4123456789"
    )
    assert (
        extract_current_job_id("https://www.linkedin.com/jobs/collections/recommended/?currentJobId=123")
        == "123"
    )
    assert extract_current_job_id("https://www.linkedin.com/jobs/search/?currentJobId=abc") is None
    assert extract_current_job_id("") is None


def test_extract_linkedin_job_id_from_common_url_variants() -> None:
    assert extract_linkedin_job_id("https://www.linkedin.com/jobs/view/4123456789/") == "4123456789"
    assert (
        extract_linkedin_job_id("https://www.linkedin.com/jobs/view/urn:li:fsd_jobPosting:99887766/")
        == "99887766"
    )
    assert (
        extract_linkedin_job_id("https://www.linkedin.com/jobs/search/?keywords=it&currentJobId=555")
        == "555"
    )
    assert extract_linkedin_job_id("https://example.test/jobs/555") is None


def test_normalize_linkedin_job_url_removes_tracking_noise() -> None:
    assert (
        normalize_linkedin_job_url(
            "https://www.linkedin.com/jobs/search/?keywords=support&currentJobId=4123456789&trackingId=x#main"
        )
        == "https://www.linkedin.com/jobs/view/4123456789/"
    )
    assert (
        normalize_linkedin_job_url("https://www.linkedin.com/jobs/view/4123456789/?refId=abc")
        == "https://www.linkedin.com/jobs/view/4123456789/"
    )
    assert normalize_linkedin_job_url(None) == ""


def test_same_linkedin_job_and_duplicate_reference() -> None:
    seen_urls = {"https://www.linkedin.com/jobs/view/4123456789/"}
    seen_job_ids = {"4123456789"}

    assert same_linkedin_job(
        "https://www.linkedin.com/jobs/search/?currentJobId=4123456789",
        "https://www.linkedin.com/jobs/view/4123456789/",
    )
    assert is_duplicate_job_reference(
        source_url="https://www.linkedin.com/jobs/search/?currentJobId=4123456789",
        seen_urls=seen_urls,
        seen_job_ids=seen_job_ids,
    )
    assert not is_duplicate_job_reference(
        source_url="https://www.linkedin.com/jobs/view/1/",
        seen_urls=seen_urls,
        seen_job_ids=seen_job_ids,
    )


def test_diagnostic_event_creation() -> None:
    event = diagnostic_event(EXP_CAPTURE_DISABLED, "Disabled for test", level="warning", details={"enabled": False})

    assert event.code == EXP_CAPTURE_DISABLED
    assert event.level == "warning"
    assert event.details["enabled"] is False
    assert event.timestamp
