from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.services import history_store

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
    assert "manual_raw_jobs" in data["capture_mode"]
    assert "page_text" in data["capture_mode"]
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
    assert data["capture_diagnostics"]["capture_mode_used"] == "manual_raw_jobs"
    assert data["capture_diagnostics"]["candidate_cards_found"] == 1


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


def test_page_text_with_one_job_produces_one_result() -> None:
    response = client.post(
        "/api/capture/run",
        json={
            "profile_id": "rafael_default",
            "capture_mode": "page_text",
            "source": "page_text",
            "source_url": "https://example.test/page",
            "max_results": 5,
            "dry_run": True,
            "page_text": support_job(),
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_captured"] == 1
    assert data["classified_count"] == 1
    assert data["results"][0]["raw_job"]["source"] == "page_text"
    assert data["results"][0]["raw_job"]["source_url"] == "https://example.test/page"
    assert any("Page text" in warning for warning in data["warnings"])


def test_page_text_with_multiple_synthetic_job_blocks_produces_multiple_results() -> None:
    page_text = f"""
Job 1
{support_job()}

Job 2
Title: IT Support Engineer
Company: Example Desk
Location: Remote, Spain
Work mode: Remote
English required. Support Microsoft 365 and endpoint tickets.
"""

    response = client.post(
        "/api/capture/run",
        json={
            "profile_id": "rafael_default",
            "capture_mode": "page_text",
            "source": "page_text",
            "max_results": 5,
            "dry_run": True,
            "page_text": page_text,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_captured"] == 2
    assert [result["parsed_job"]["title"] for result in data["results"]] == [
        "Technical Support Specialist",
        "IT Support Engineer",
    ]
    assert data["capture_diagnostics"]["candidate_cards_found"] == 2
    assert data["capture_diagnostics"]["cards_accepted"] == 2


def test_page_text_with_labelled_blocks_separated_by_dashes() -> None:
    page_text = """
Title: Microsoft 365 Support Specialist
Company: Example SaaS
Location: Remote, Spain
Work mode: Remote
URL: https://example.test/jobs/m365-support
English required. Microsoft 365 support.
---
Title: Infrastructure Support Engineer
Company: Example Infra
Location: Vigo, Spain
Work mode: Onsite
English required. Endpoint and networking support.
"""

    response = client.post(
        "/api/capture/run",
        json={
            "profile_id": "rafael_default",
            "capture_mode": "page_text",
            "source": "page_text",
            "max_results": 5,
            "dry_run": True,
            "page_text": page_text,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_captured"] == 2
    assert data["results"][0]["raw_job"]["source_url"] == "https://example.test/jobs/m365-support"
    assert any("labelled job block" in note for note in data["results"][0]["raw_job"]["capture_notes"])


def test_page_text_with_job_card_separators_produces_multiple_results() -> None:
    page_text = """
Job Card
Title: SaaS Support Analyst
Employer: Example Cloud
Location: Remote, Spain
Work mode: Remote
English required. SaaS and API support.
Easy Apply
Job Card
Role: Service Desk Technician
Company: Example Desk
Location: Vigo, Spain
Work mode: Onsite
English required. Microsoft 365 and endpoint support.
"""

    response = client.post(
        "/api/capture/run",
        json={
            "profile_id": "rafael_default",
            "capture_mode": "page_text",
            "source": "page_text",
            "max_results": 5,
            "dry_run": True,
            "page_text": page_text,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_captured"] == 2
    assert data["results"][0]["parsed_job"]["company"] == "Example Cloud"
    assert data["results"][1]["parsed_job"]["title"] == "Service Desk Technician"


def test_compact_job_board_like_blocks_are_split_conservatively() -> None:
    page_text = """
Microsoft 365 Support Specialist
Northstar SaaS
Remote, Spain
English required. Microsoft 365 and endpoint support.
View job
Infrastructure Support Engineer
Metro Systems
Vigo, Spain
English required. Networking and endpoint troubleshooting.
"""

    response = client.post(
        "/api/capture/run",
        json={
            "profile_id": "rafael_default",
            "capture_mode": "page_text",
            "source": "page_text",
            "max_results": 5,
            "dry_run": True,
            "page_text": page_text,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_captured"] == 2
    assert data["results"][0]["parsed_job"]["title"] == "Microsoft 365 Support Specialist"
    assert data["results"][0]["parsed_job"]["company"] == "Northstar SaaS"
    assert any("compact job-board-like" in note for note in data["results"][0]["raw_job"]["capture_notes"])


def test_html_with_two_article_blocks_extracts_two_jobs_and_strips_noise() -> None:
    html_content = """
<html>
  <body>
    <nav>Navigation should not become a job</nav>
    <article>
      <h2>Title: Microsoft 365 Support Specialist</h2>
      <p>Company: Example SaaS</p>
      <p>Location: Remote, Spain</p>
      <p>Work mode: Remote</p>
      <a href="https://example.test/jobs/123">View job</a>
      <p>English required. Microsoft 365 support.</p>
    </article>
    <article>
      <h2>Title: IT Support Engineer</h2>
      <p>Company: Example Desk</p>
      <p>Location: Vigo, Spain</p>
      <p>Work mode: Onsite</p>
      <a href="https://example.test/careers/456">Apply</a>
      <p>English required. Endpoint support.</p>
    </article>
  </body>
</html>
"""

    response = client.post(
        "/api/capture/run",
        json={
            "profile_id": "rafael_default",
            "capture_mode": "page_text",
            "source": "page_html",
            "max_results": 5,
            "dry_run": True,
            "html_content": html_content,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_captured"] == 2
    assert data["results"][0]["raw_job"]["source_url"] == "https://example.test/jobs/123"
    assert data["results"][1]["raw_job"]["source_url"] == "https://example.test/careers/456"
    assert "Navigation should not become a job" not in data["results"][0]["raw_job"]["raw_text"]
    assert any("HTML block" in note for note in data["results"][0]["raw_job"]["capture_notes"])
    assert data["capture_diagnostics"]["source_url_extraction_notes"]


def test_html_fragment_capture_mode_extracts_anchor_href() -> None:
    html_content = """
<article>
  <a href="https://example.test/jobs/html-fragment-1">Title: Microsoft 365 Support Specialist</a>
  <p>Company: Example SaaS</p>
  <p>Location: Remote, Spain</p>
  <p>Work mode: Remote</p>
  <p>English required. Microsoft 365 support.</p>
</article>
"""

    response = client.post(
        "/api/capture/run",
        json={
            "profile_id": "rafael_default",
            "capture_mode": "html_fragment",
            "source": "html_fragment",
            "max_results": 5,
            "dry_run": True,
            "html_content": html_content,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_captured"] == 1
    assert data["capture_diagnostics"]["capture_mode_used"] == "html_fragment"
    assert data["results"][0]["raw_job"]["source_url"] == "https://example.test/jobs/html-fragment-1"


def test_uploaded_html_content_capture_mode_extracts_job() -> None:
    response = client.post(
        "/api/capture/run",
        json={
            "profile_id": "rafael_default",
            "capture_mode": "uploaded_html_content",
            "source": "uploaded_html_content",
            "max_results": 5,
            "dry_run": True,
            "uploaded_html_content": """
<section>
  <h2>Title: Infrastructure Support Technician</h2>
  <p>Company: Example Infra</p>
  <p>Location: Vigo, Spain</p>
  <p>Work mode: Onsite</p>
  <p>English required. Endpoint and networking support.</p>
</section>
""",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_captured"] == 1
    assert data["capture_diagnostics"]["capture_mode_used"] == "uploaded_html_content"
    assert data["results"][0]["parsed_job"]["title"] == "Infrastructure Support Technician"


def test_global_source_url_fallback_is_used_when_block_has_no_link() -> None:
    response = client.post(
        "/api/capture/run",
        json={
            "profile_id": "rafael_default",
            "capture_mode": "page_text",
            "source": "page_text",
            "source_url": "https://example.test/search-results",
            "max_results": 5,
            "dry_run": True,
            "page_text": support_job(),
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["results"][0]["raw_job"]["source_url"] == "https://example.test/search-results"
    assert any("fallback" in note.lower() for note in data["results"][0]["raw_job"]["capture_notes"])


def test_unclear_page_text_returns_one_result_with_capture_note() -> None:
    response = client.post(
        "/api/capture/run",
        json={
            "profile_id": "rafael_default",
            "capture_mode": "page_text",
            "source": "page_text",
            "max_results": 5,
            "dry_run": True,
            "page_text": "Support role. Tickets. Help users. Remote maybe.",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_captured"] == 1
    assert any("unclear" in note.lower() for note in data["results"][0]["raw_job"]["capture_notes"])
    assert data["capture_diagnostics"]["capture_confidence"] == "low"


def test_full_page_without_clear_cards_warns_about_fallback() -> None:
    response = client.post(
        "/api/capture/run",
        json={
            "profile_id": "rafael_default",
            "capture_mode": "page_text",
            "source": "page_text",
            "max_results": 5,
            "dry_run": True,
            "page_text": "\n".join(
                [
                    "Navigation",
                    "Search jobs",
                    "Filters",
                    "Promoted",
                    "Easy Apply",
                    "Actively recruiting",
                    "Support role maybe remote",
                    "Saved jobs",
                    "Footer",
                ]
            ),
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_captured"] == 1
    assert any("full page" in warning.lower() for warning in data["warnings"])


def test_page_text_avoids_over_splitting_tiny_fragments() -> None:
    page_text = """
Promoted
Easy Apply
View job
Actively recruiting
Support role. Tickets. Remote maybe.
Apply
"""

    response = client.post(
        "/api/capture/run",
        json={
            "profile_id": "rafael_default",
            "capture_mode": "page_text",
            "source": "page_text",
            "max_results": 5,
            "dry_run": True,
            "page_text": page_text,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_captured"] == 1
    assert len(data["results"][0]["raw_job"]["raw_text"].splitlines()) <= 2


def test_tiny_noisy_cards_are_rejected_and_reported() -> None:
    page_text = """
Job Card
Promoted
Easy Apply
---
Job Card
Title: Microsoft 365 Support Specialist
Company: Example SaaS
Location: Remote, Spain
Work mode: Remote
English required. Microsoft 365 support.
---
Job Card
View job
Apply
"""

    response = client.post(
        "/api/capture/run",
        json={
            "profile_id": "rafael_default",
            "capture_mode": "page_text",
            "source": "page_text",
            "max_results": 5,
            "dry_run": True,
            "page_text": page_text,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_captured"] == 1
    assert data["capture_diagnostics"]["cards_rejected"] >= 1
    assert data["capture_diagnostics"]["rejection_reasons"]


def test_page_text_max_results_is_enforced() -> None:
    page_text = "\n".join(
        [
            f"""
Job {index}
Title: Technical Support Specialist {index}
Company: Example SaaS
Location: Vigo, Spain
Work mode: Remote
English required. Microsoft 365 support.
"""
            for index in range(1, 4)
        ]
    )

    response = client.post(
        "/api/capture/run",
        json={
            "profile_id": "rafael_default",
            "capture_mode": "page_text",
            "source": "page_text",
            "max_results": 2,
            "dry_run": True,
            "page_text": page_text,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_captured"] == 2
    assert any("only the first 2" in warning for warning in data["warnings"])
    assert any("max_results applied" in note for note in data["results"][0]["raw_job"]["capture_notes"])


def test_unsupported_capture_mode_returns_controlled_error() -> None:
    response = client.post(
        "/api/capture/run",
        json={
            "profile_id": "rafael_default",
            "capture_mode": "crawler",
            "source": "page_text",
            "dry_run": True,
        },
    )

    assert response.status_code == 422


def test_browser_assisted_does_not_attempt_automation_by_default() -> None:
    response = client.post(
        "/api/capture/run",
        json={
            "profile_id": "rafael_default",
            "capture_mode": "browser_assisted",
            "source": "browser_assisted",
            "max_results": 5,
            "dry_run": True,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_captured"] == 0
    assert any("not enabled" in warning for warning in data["warnings"])
    assert data["capture_diagnostics"]["capture_mode_used"] == "browser_assisted"


def test_capture_marks_likely_duplicate_before_save(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(history_store, "HISTORY_ROOT", tmp_path / "backend" / "data" / "history")
    monkeypatch.setattr(history_store, "HISTORY_FILE", tmp_path / "backend" / "data" / "history" / "jobs.jsonl")

    first = run_capture([raw_job(support_job(), "https://example.test/duplicate-preview")])
    save_response = client.post(
        "/api/history/save-capture-result",
        json={
            "capture_result": first,
            "include_raw_text": False,
            "default_application_status": "Not started",
        },
    )
    assert save_response.status_code == 200

    second = run_capture([raw_job(support_job(), "https://example.test/duplicate-preview")])

    assert second["results"][0]["duplicate_preview"] is True
    assert "source_url" in second["results"][0]["duplicate_reason"]
    assert second["results"][0]["duplicate_history_id"]
