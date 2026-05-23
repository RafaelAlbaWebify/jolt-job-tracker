from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def base_job(**overrides: object) -> dict[str, object]:
    job: dict[str, object] = {
        "job_id": "job-1",
        "title": "Technical Support Specialist",
        "company": "Example SaaS",
        "location": "Vigo, Spain",
        "work_mode": "remote",
        "source_url": "https://example.test/job-1",
        "description": "Technical Support role with Microsoft 365 and endpoint troubleshooting.",
        "languages_detected": ["English"],
        "mandatory_languages": ["English"],
        "employment_type": "full-time",
        "shift_indicators": [],
        "on_call_indicators": [],
        "positive_keywords": [],
        "risk_keywords": [],
        "parser_confidence": "high",
        "parser_notes": [],
        "already_reviewed": False,
        "duplicate_of": None,
        "distance_km": None,
    }
    job.update(overrides)
    return job


def classify(job: dict[str, object], profile_id: str = "rafael_default") -> dict[str, object]:
    response = client.post("/api/classify/job", json={"profile_id": profile_id, "job": job})
    assert response.status_code == 200
    return response.json()


def test_mandatory_german_with_rafael_default_discards() -> None:
    result = classify(base_job(mandatory_languages=["German"]))

    assert result["decision"] == "Discard"
    assert "language.unsupported_mandatory" in result["triggered_rules"]


def test_mandatory_french_with_rafael_default_discards() -> None:
    result = classify(base_job(mandatory_languages=["French"]))

    assert result["decision"] == "Discard"
    assert "language.unsupported_mandatory" in result["triggered_rules"]


def test_mandatory_english_is_not_discarded_by_language() -> None:
    result = classify(base_job(mandatory_languages=["English"]))

    assert result["decision"] != "Discard"
    assert "language.unsupported_mandatory" not in result["triggered_rules"]


def test_remote_madrid_role_is_not_discarded_by_distance() -> None:
    result = classify(base_job(location="Madrid, Spain", work_mode="remote", distance_km=600))

    assert result["decision"] != "Discard"
    assert "location.remote_distance_exempt" in result["triggered_rules"]


def test_hybrid_madrid_role_discards_by_distance() -> None:
    result = classify(base_job(location="Madrid, Spain", work_mode="hybrid", distance_km=600))

    assert result["decision"] == "Discard"
    assert "location.outside_distance_limit" in result["triggered_rules"]


def test_onsite_vigo_role_is_not_discarded_by_distance() -> None:
    result = classify(base_job(location="Vigo, Spain", work_mode="onsite", distance_km=5))

    assert result["decision"] != "Discard"
    assert "location.outside_distance_limit" not in result["triggered_rules"]


def test_positive_keywords_do_not_override_hard_discard() -> None:
    result = classify(
        base_job(
            mandatory_languages=["German"],
            description="Microsoft 365 Entra ID automation endpoint networking Technical Support.",
        )
    )

    assert result["decision"] == "Discard"
    assert result["matched_positive_keywords"]


def test_heavy_on_call_creates_discard_from_profile_severity() -> None:
    result = classify(base_job(on_call_indicators=["heavy on-call"], risk_keywords=["24/7"]))

    assert result["decision"] == "Discard"
    assert any("discard" in warning for warning in result["warnings"])


def test_missing_work_mode_and_location_create_missing_information() -> None:
    result = classify(base_job(work_mode="unknown", location=""))

    assert "work_mode" in result["missing_information"]
    assert "location" in result["missing_information"]
    assert result["decision"] in {"Manual Review", "Maybe"}


def test_low_parser_confidence_pushes_manual_review_or_maybe() -> None:
    result = classify(base_job(parser_confidence="low"))

    assert result["decision"] in {"Manual Review", "Maybe"}
    assert "parser.low_confidence" in result["triggered_rules"]


def test_duplicate_of_returns_duplicate() -> None:
    result = classify(base_job(duplicate_of="job-previous"))

    assert result["decision"] == "Duplicate"
    assert "dedupe.duplicate_of" in result["triggered_rules"]
