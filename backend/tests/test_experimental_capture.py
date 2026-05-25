from fastapi.testclient import TestClient

from app.main import app
from app.services.experimental_linkedin_capture.diagnostics import (
    EXP_CAPTURE_DISABLED,
    EXP_CAPTURE_STARTED,
    diagnostic_event,
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


def test_experimental_capture_enabled_start_is_dry_run(monkeypatch) -> None:
    monkeypatch.setenv("JOLT_ENABLE_EXPERIMENTAL_LINKEDIN_CAPTURE", "true")
    client = TestClient(app)

    response = client.post(
        "/api/experimental-capture/linkedin/start",
        json={"max_pages": 1, "max_jobs": 5, "dry_run": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["enabled"] is True
    assert payload["status"] == "completed"
    assert payload["run"]["captured_jobs"] == []
    assert payload["run"]["diagnostics"][0]["code"] == EXP_CAPTURE_STARTED
    assert "no browser automation" in payload["message"].lower()


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
