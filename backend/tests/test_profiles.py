from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_profiles_list_loads() -> None:
    response = client.get("/api/profiles")

    assert response.status_code == 200
    profiles = response.json()
    assert isinstance(profiles, list)
    assert len(profiles) >= 4


def test_rafael_default_exists() -> None:
    response = client.get("/api/profiles")

    profile_ids = {profile["profile_id"] for profile in response.json()}
    assert "rafael_default" in profile_ids


def test_profile_detail_returns_required_fields() -> None:
    response = client.get("/api/profiles/rafael_default")

    assert response.status_code == 200
    profile = response.json()
    required_fields = {
        "profile_id",
        "display_name",
        "description",
        "accepted_languages",
        "mandatory_language_mode",
        "base_location",
        "max_distance_km_for_hybrid_onsite",
        "remote_ignores_distance",
        "preferred_work_modes",
        "acceptable_work_modes",
        "positive_keywords",
        "risk_keywords",
        "discard_keywords",
        "stretch_skills",
        "risk_severity_settings",
        "portfolio_safe",
    }

    assert required_fields.issubset(profile.keys())
    assert profile["accepted_languages"] == ["English", "Spanish"]
    assert profile["base_location"] == "Vigo, Spain"
    assert profile["max_distance_km_for_hybrid_onsite"] == 30
    assert profile["remote_ignores_distance"] is True


def test_unknown_profile_returns_controlled_404() -> None:
    response = client.get("/api/profiles/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {"detail": "Profile not found"}
