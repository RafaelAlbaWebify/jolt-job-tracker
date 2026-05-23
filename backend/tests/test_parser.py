from fastapi.testclient import TestClient

from app.main import app
from app.services.parser import parse_job

client = TestClient(app)


BASE_TEXT = """
Title: Technical Support Specialist
Company: Example SaaS
Location: Vigo, Spain
Employment Type: full-time

We are hiring for a Technical Support role working with Microsoft 365, endpoint troubleshooting,
networking basics, and SaaS Support workflows. English required. The role collaborates with IT
Operations and handles documented customer support cases with clear escalation paths.
"""


def test_remote_work_mode_detection() -> None:
    job = parse_job(BASE_TEXT + "\nWork mode: remote")

    assert job.work_mode == "remote"


def test_hybrid_work_mode_detection() -> None:
    job = parse_job(BASE_TEXT + "\nThis is a hybrid role in Vigo.")

    assert job.work_mode == "hybrid"


def test_onsite_work_mode_detection() -> None:
    job = parse_job(BASE_TEXT + "\nThis is an on-site position.")

    assert job.work_mode == "onsite"


def test_unknown_work_mode_when_unclear() -> None:
    job = parse_job(BASE_TEXT)

    assert job.work_mode == "unknown"
    assert "Work mode is unclear." in job.parser_notes


def test_mandatory_german_detection() -> None:
    job = parse_job(BASE_TEXT + "\nGerman required for customer escalations. Remote role.")

    assert "German" in job.languages_detected
    assert "German" in job.mandatory_languages


def test_optional_german_does_not_become_mandatory() -> None:
    job = parse_job(BASE_TEXT + "\nGerman nice to have. Remote role.")

    assert "German" in job.languages_detected
    assert "German" not in job.mandatory_languages


def test_english_required_detected_as_mandatory_language() -> None:
    job = parse_job(BASE_TEXT + "\nRemote role.")

    assert "English" in job.languages_detected
    assert "English" in job.mandatory_languages


def test_shift_and_on_call_detection() -> None:
    job = parse_job(
        BASE_TEXT
        + "\nRemote role with heavy on-call, 24/7 coverage, rotating shifts, night shifts, and weekends."
    )

    assert "heavy on-call" in job.on_call_indicators
    assert "on-call" in job.on_call_indicators
    assert "24/7" in job.shift_indicators
    assert "rotating shifts" in job.shift_indicators
    assert "night shifts" in job.shift_indicators
    assert "weekends" in job.shift_indicators
    assert "24/7" in job.risk_keywords


def test_low_confidence_for_very_short_text() -> None:
    job = parse_job("Support job")

    assert job.parser_confidence == "low"


def test_parser_notes_include_missing_unclear_fields() -> None:
    job = parse_job("We need support help with tickets and users.")

    assert "Title was not found using supported labels." in job.parser_notes
    assert "Company was not found using supported labels." in job.parser_notes
    assert "Location was not found using supported labels." in job.parser_notes
    assert "Work mode is unclear." in job.parser_notes


def test_parse_api_returns_normalized_job() -> None:
    response = client.post(
        "/api/parse/job",
        json={"raw_text": BASE_TEXT + "\nRemote role.", "source_url": "https://example.test/job"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Technical Support Specialist"
    assert data["company"] == "Example SaaS"
    assert data["location"] == "Vigo, Spain"
    assert data["source_url"] == "https://example.test/job"


def test_parsed_job_can_be_classified_successfully() -> None:
    response = client.post(
        "/api/parse-and-classify/job",
        json={
            "profile_id": "rafael_default",
            "raw_text": BASE_TEXT + "\nRemote role.",
            "source_url": "https://example.test/job",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["job"]["mandatory_languages"] == ["English"]
    assert data["decision"]["profile_id"] == "rafael_default"
    assert data["decision"]["decision"] in {"Apply", "Maybe", "Manual Review", "Discard", "Duplicate"}
