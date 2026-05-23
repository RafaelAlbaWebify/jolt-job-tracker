from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def raw_job(raw_text: str, source_url: str = "https://example.test/job") -> dict[str, object]:
    return {
        "source": "manual_raw_jobs",
        "source_url": source_url,
        "raw_text": raw_text,
        "external_id": "example-1",
        "capture_notes": ["test fixture"],
    }


def support_job(extra: str = "") -> str:
    return f"""
Title: Technical Support Specialist
Company: Example SaaS
Location: Vigo, Spain
Employment Type: full-time

Remote role supporting Microsoft 365, endpoint troubleshooting, and SaaS Support workflows.
English required. {extra}
"""


def run_capture(raw_jobs: list[dict[str, object]], max_results: int = 25) -> dict[str, object]:
    response = client.post(
        "/api/capture/run",
        json={
            "profile_id": "rafael_default",
            "source": "manual_raw_jobs",
            "query": "technical support",
            "location": "Vigo, Spain",
            "work_mode_filter": "remote",
            "max_results": max_results,
            "dry_run": True,
            "raw_jobs": raw_jobs,
        },
    )
    assert response.status_code == 200
    return response.json()


def test_capture_health_says_browser_automation_disabled() -> None:
    response = client.get("/api/capture/health")

    assert response.status_code == 200
    data = response.json()
    assert data["capture_mode"] == "manual_raw_jobs"
    assert data["browser_automation_enabled"] is False
    assert any("not implemented" in warning for warning in data["warnings"])


def test_empty_raw_jobs_returns_completed_result_with_warning_and_zero_counts() -> None:
    data = run_capture([])

    assert data["status"] == "completed"
    assert data["total_captured"] == 0
    assert data["parsed_count"] == 0
    assert data["classified_count"] == 0
    assert data["failed_count"] == 0
    assert any("No raw_jobs" in warning for warning in data["warnings"])


def test_one_raw_remote_english_microsoft_365_job_parses_and_classifies() -> None:
    data = run_capture([raw_job(support_job())])

    assert data["status"] == "completed"
    assert data["total_captured"] == 1
    assert data["parsed_count"] == 1
    assert data["classified_count"] == 1
    result = data["results"][0]
    assert result["errors"] == []
    assert result["parsed_job"]["work_mode"] == "remote"
    assert "English" in result["parsed_job"]["mandatory_languages"]
    assert result["decision"]["profile_id"] == "rafael_default"


def test_mandatory_german_job_discards_with_rafael_default() -> None:
    data = run_capture([raw_job(support_job("German required for customer escalations."))])

    decision = data["results"][0]["decision"]
    assert decision["decision"] == "Discard"
    assert "language.unsupported_mandatory" in decision["triggered_rules"]


def test_mixed_run_continues_when_one_raw_job_is_empty() -> None:
    data = run_capture([raw_job(""), raw_job(support_job(), source_url="https://example.test/job-2")])

    assert data["status"] == "completed_with_errors"
    assert data["total_captured"] == 2
    assert data["failed_count"] == 1
    assert data["parsed_count"] == 1
    assert data["classified_count"] == 1
    assert data["results"][0]["errors"] == ["raw_text is required for manual capture boundary processing."]
    assert data["results"][1]["decision"] is not None


def test_max_results_limits_and_warns() -> None:
    data = run_capture(
        [
            raw_job(support_job(), "https://example.test/1"),
            raw_job(support_job(), "https://example.test/2"),
        ],
        max_results=1,
    )

    assert data["total_captured"] == 1
    assert len(data["results"]) == 1
    assert data["results"][0]["raw_job"]["source_url"] == "https://example.test/1"
    assert any("only the first 1" in warning for warning in data["warnings"])


def test_capture_run_does_not_create_persistence_or_history_files(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    data = run_capture([raw_job(support_job())])

    assert data["classified_count"] == 1
    for path in ["runs", "outputs", "exports", "job_history_master.csv"]:
        assert not Path(path).exists()
