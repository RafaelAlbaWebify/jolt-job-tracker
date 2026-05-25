from fastapi.testclient import TestClient

from app.main import app
from app.services.experimental_linkedin_capture.diagnostics import (
    EXP_BROWSER_URL_CAPTURED,
    EXP_BROWSER_URL_CAPTURE_STARTED,
    EXP_CARD_CLICK_ATTEMPTED,
    EXP_CARD_CLICK_COMPLETED,
    EXP_CARD_CLICK_SEQUENCE_STARTED,
    EXP_CARD_DETECTION_COMPLETED,
    EXP_CARD_DETECTION_STARTED,
    EXP_CARD_DETECTION_ZERO_CARDS,
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
    EXP_LEGACY_BATCH_DEPENDENCIES_MISSING,
    EXP_LEGACY_BATCH_DEPENDENCIES_OK,
    EXP_LEGACY_BATCH_CAPTURE_COMPLETED,
    EXP_LEGACY_BATCH_CAPTURE_STARTED,
    EXP_MOUSE_CONTROL_DEPENDENCIES_OK,
    EXP_MOUSE_CONTROL_TEST_STARTED,
    EXP_MOUSE_MOVEMENT_COMPLETED,
    EXP_MOUSE_POSITION_CAPTURED,
    EXP_NON_LINKEDIN_URL_CAPTURED,
    EXP_PAGE_LIMIT_REACHED,
    EXP_SCREENSHOT_CAPTURED,
    EXP_SCREENSHOT_CAPTURE_STARTED,
    EXP_SCREEN_SIZE_CAPTURED,
    EXP_SELECTED_JOB_ADAPTER_DEPENDENCY_MISSING,
    EXP_SELECTED_JOB_CAPTURE_STARTED,
    EXP_VISIBLE_TEXT_CAPTURED,
    EXP_VISIBLE_TEXT_TOO_SHORT,
    EXP_URL_CURRENT_JOB_ID_MATCHED,
    diagnostic_event,
)
from app.services.experimental_linkedin_capture import runner
from app.services.experimental_linkedin_capture import windows_selected_job_adapter
from app.services.experimental_linkedin_capture.legacy_batch_adapter import LegacyBatchCaptureAdapter
from app.services.experimental_linkedin_capture.legacy_card_detection import LegacyScreenContext
from app.services.experimental_linkedin_capture.models import (
    ExperimentalCapturedJobRecord,
    ExperimentalCaptureRunPackage,
)
from app.services.experimental_linkedin_capture.diagnostics import utc_now_iso
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


def test_legacy_batch_capture_disabled_when_feature_flag_off(monkeypatch) -> None:
    monkeypatch.delenv("JOLT_ENABLE_EXPERIMENTAL_LINKEDIN_CAPTURE", raising=False)
    client = TestClient(app)

    response = client.post(
        "/api/experimental-capture/linkedin/start",
        json={"mode": "legacy_batch_capture", "max_pages": 1, "max_jobs": 3, "dry_run": False},
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


def test_legacy_batch_parameter_validation(monkeypatch) -> None:
    monkeypatch.setenv("JOLT_ENABLE_EXPERIMENTAL_LINKEDIN_CAPTURE", "true")
    client = TestClient(app)

    response = client.post(
        "/api/experimental-capture/linkedin/start",
        json={
            "mode": "legacy_batch_capture",
            "max_pages": 1,
            "max_jobs": 3,
            "delay_between_cards_seconds": 0.1,
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


class FakeLegacyBatchAdapter(LegacyBatchCaptureAdapter):
    def run(
        self,
        *,
        run_id: str,
        max_pages: int,
        max_jobs: int,
        focus_delay_seconds: int,
        delay_between_cards_seconds: float,
        include_pagination: bool,
        capture_detail_phase: bool,
        debug_screenshots: bool,
        timeout_seconds: int,
        stop_requested,
    ) -> ExperimentalCaptureRunPackage:
        started_at = utc_now_iso()
        diagnostics = [
            diagnostic_event(EXP_LEGACY_BATCH_CAPTURE_STARTED, "Fake legacy batch started."),
        ]
        if stop_requested():
            return ExperimentalCaptureRunPackage(
                run_id=run_id,
                status="stopped",
                started_at=started_at,
                finished_at=utc_now_iso(),
                max_pages=max_pages,
                max_jobs=max_jobs,
                diagnostics=diagnostics,
            )
        jobs: list[ExperimentalCapturedJobRecord] = []
        fake_ids = ["9001", "9002", "9001", "9003", "9004"]
        seen: dict[str, int] = {}
        for sequence, job_id in enumerate(fake_ids[:max_jobs], start=1):
            page_index = 1 if sequence <= 3 else 2
            if page_index > max_pages:
                diagnostics.append(diagnostic_event(EXP_PAGE_LIMIT_REACHED, "Fake max_pages reached."))
                break
            duplicate_of = seen.get(job_id)
            if duplicate_of is not None:
                diagnostics.append(
                    diagnostic_event(EXP_DUPLICATE_JOB_ID, "Fake duplicate detected.", details={"current_job_id": job_id})
                )
                capture_state = "legacy_batch_duplicate"
            else:
                seen[job_id] = sequence
                capture_state = "legacy_batch_captured"
            diagnostics.append(diagnostic_event(EXP_CARD_CLICK_ATTEMPTED, "Fake card click."))
            jobs.append(
                ExperimentalCapturedJobRecord(
                    sequence=sequence,
                    source_url=f"https://www.linkedin.com/jobs/search/?currentJobId={job_id}",
                    current_job_id=job_id,
                    title=f"Legacy Batch Job {sequence}",
                    company="Demo Legacy Company",
                    location="Remote",
                    raw_text=(
                        f"Title: Legacy Batch Job {sequence}\n"
                        "Company: Demo Legacy Company\n"
                        "Location: Remote\n"
                        "About the job Easy Apply Save applicants remote company job "
                        + ("support endpoint troubleshooting " * 30)
                    ),
                    capture_state=capture_state,
                    page_index=page_index,
                    card_index=sequence - 1,
                    duplicate_of=duplicate_of,
                )
            )
        diagnostics.append(diagnostic_event(EXP_LEGACY_BATCH_CAPTURE_COMPLETED, "Fake legacy batch completed."))
        return ExperimentalCaptureRunPackage(
            run_id=run_id,
            status="completed",
            started_at=started_at,
            finished_at=utc_now_iso(),
            max_pages=max_pages,
            max_jobs=max_jobs,
            captured_jobs=jobs,
            diagnostics=diagnostics,
        )


def test_legacy_batch_capture_with_fake_adapter_captures_multiple_jobs(monkeypatch) -> None:
    monkeypatch.setenv("JOLT_ENABLE_EXPERIMENTAL_LINKEDIN_CAPTURE", "true")
    monkeypatch.setattr(runner, "LEGACY_BATCH_ADAPTER_FACTORY", FakeLegacyBatchAdapter)
    client = TestClient(app)

    response = client.post(
        "/api/experimental-capture/linkedin/start",
        json={"mode": "legacy_batch_capture", "max_pages": 2, "max_jobs": 4, "dry_run": False},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["captured_count"] == 4
    codes = {event["code"] for event in payload["run"]["diagnostics"]}
    assert EXP_LEGACY_BATCH_CAPTURE_STARTED in codes
    assert EXP_LEGACY_BATCH_CAPTURE_COMPLETED in codes
    assert EXP_CARD_CLICK_ATTEMPTED in codes
    assert EXP_DUPLICATE_JOB_ID in codes
    assert payload["run"]["captured_jobs"][2]["duplicate_of"] == 1


def test_legacy_batch_respects_max_jobs_and_pages(monkeypatch) -> None:
    monkeypatch.setenv("JOLT_ENABLE_EXPERIMENTAL_LINKEDIN_CAPTURE", "true")
    monkeypatch.setattr(runner, "LEGACY_BATCH_ADAPTER_FACTORY", FakeLegacyBatchAdapter)
    client = TestClient(app)

    max_jobs_response = client.post(
        "/api/experimental-capture/linkedin/start",
        json={"mode": "legacy_batch_capture", "max_pages": 2, "max_jobs": 2, "dry_run": False},
    )
    assert max_jobs_response.status_code == 200
    assert max_jobs_response.json()["captured_count"] == 2

    max_pages_response = client.post(
        "/api/experimental-capture/linkedin/start",
        json={"mode": "legacy_batch_capture", "max_pages": 1, "max_jobs": 5, "dry_run": False},
    )
    assert max_pages_response.status_code == 200
    page_payload = max_pages_response.json()
    assert page_payload["captured_count"] == 3
    codes = {event["code"] for event in page_payload["run"]["diagnostics"]}
    assert EXP_PAGE_LIMIT_REACHED in codes


def test_legacy_batch_missing_dependencies_return_clear_error(monkeypatch) -> None:
    monkeypatch.setenv("JOLT_ENABLE_EXPERIMENTAL_LINKEDIN_CAPTURE", "true")

    class MissingDependencyAdapter(LegacyBatchCaptureAdapter):
        def __init__(self) -> None:
            super().__init__()

        def run(self, **kwargs) -> ExperimentalCaptureRunPackage:  # type: ignore[no-untyped-def]
            now = utc_now_iso()
            return ExperimentalCaptureRunPackage(
                run_id=kwargs["run_id"],
                status="failed",
                started_at=now,
                finished_at=now,
                max_pages=kwargs["max_pages"],
                max_jobs=kwargs["max_jobs"],
                diagnostics=[
                    diagnostic_event(EXP_SELECTED_JOB_ADAPTER_DEPENDENCY_MISSING, "Install experimental dependencies.")
                ],
                errors=["Install experimental dependencies from backend/requirements-experimental.txt."],
            )

    monkeypatch.setattr(runner, "LEGACY_BATCH_ADAPTER_FACTORY", MissingDependencyAdapter)
    client = TestClient(app)

    response = client.post(
        "/api/experimental-capture/linkedin/start",
        json={"mode": "legacy_batch_capture", "max_pages": 1, "max_jobs": 3, "dry_run": False},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "failed"
    assert "requirements-experimental.txt" in payload["run"]["errors"][0]


def test_legacy_batch_dependency_missing_code_is_explicit() -> None:
    class MissingClipboard:
        def dependency_error(self) -> str:
            return "Install experimental dependencies from backend/requirements-experimental.txt."

    class UnusedMouse:
        def dependency_error(self) -> str:
            return ""

    run = LegacyBatchCaptureAdapter(clipboard=MissingClipboard(), mouse=UnusedMouse()).run(
        run_id="legacy_missing_deps",
        max_pages=1,
        max_jobs=1,
        focus_delay_seconds=2,
        delay_between_cards_seconds=0.25,
        include_pagination=False,
        capture_detail_phase=True,
        debug_screenshots=False,
        timeout_seconds=30,
        stop_requested=lambda: False,
    )

    codes = {event.code for event in run.diagnostics}
    assert run.status == "failed"
    assert EXP_LEGACY_BATCH_DEPENDENCIES_MISSING in codes
    assert EXP_SELECTED_JOB_ADAPTER_DEPENDENCY_MISSING in codes


def test_legacy_batch_real_adapter_detects_before_ctrl_a_and_then_clicks(monkeypatch) -> None:
    monkeypatch.setattr(windows_selected_job_adapter.time, "sleep", lambda seconds: None)
    call_order: list[str] = []

    class FakeClipboard:
        def dependency_error(self) -> str:
            return ""

        def copy_current_url(self) -> str:
            call_order.append("copy_url")
            return "https://www.linkedin.com/jobs/search/?currentJobId=9010"

        def copy_visible_text(self) -> str:
            call_order.append("copy_visible_text")
            return (
                "Title: Runtime Diagnostics Support Engineer\n"
                "Company: Demo Runtime Co\n"
                "Location: Remote\n"
                "About the job Easy Apply Save applicants remote company job "
                + ("support endpoint troubleshooting " * 30)
            )

    class FakeMouse:
        def dependency_error(self) -> str:
            return ""

        def screen_context(self) -> LegacyScreenContext:
            call_order.append("screen_context")
            return LegacyScreenContext(
                screenshot_width=1600,
                screenshot_height=900,
                active_window_title="LinkedIn Jobs - Chrome",
                active_window_width=1600,
                active_window_height=900,
            )

        def click_card(self, x: int, y: int) -> None:
            call_order.append(f"click:{x}:{y}")

        def scroll_left_panel(self, amount: int = -5) -> None:
            call_order.append("scroll")

    adapter = LegacyBatchCaptureAdapter(clipboard=FakeClipboard(), mouse=FakeMouse())

    run = adapter.run(
        run_id="legacy_real_fake",
        max_pages=1,
        max_jobs=1,
        focus_delay_seconds=2,
        delay_between_cards_seconds=0.25,
        include_pagination=False,
        capture_detail_phase=True,
        debug_screenshots=False,
        timeout_seconds=30,
        stop_requested=lambda: False,
    )

    assert run.status == "completed"
    assert len(run.captured_jobs) == 1
    assert call_order[0] == "screen_context"
    assert call_order[1].startswith("click:")
    assert call_order.index("copy_visible_text") > call_order.index("copy_url")
    codes = {event.code for event in run.diagnostics}
    assert EXP_LEGACY_BATCH_DEPENDENCIES_OK in codes
    assert EXP_SCREENSHOT_CAPTURE_STARTED in codes
    assert EXP_SCREENSHOT_CAPTURED in codes
    assert EXP_CARD_DETECTION_STARTED in codes
    assert EXP_CARD_DETECTION_COMPLETED in codes
    assert EXP_CARD_CLICK_SEQUENCE_STARTED in codes
    assert EXP_CARD_CLICK_ATTEMPTED in codes
    assert EXP_CARD_CLICK_COMPLETED in codes
    assert EXP_BROWSER_URL_CAPTURE_STARTED in codes


def test_legacy_batch_zero_cards_has_explicit_diagnostic(monkeypatch) -> None:
    monkeypatch.setattr(windows_selected_job_adapter.time, "sleep", lambda seconds: None)

    class FakeClipboard:
        def dependency_error(self) -> str:
            return ""

    class FakeMouse:
        def dependency_error(self) -> str:
            return ""

        def screen_context(self) -> LegacyScreenContext:
            return LegacyScreenContext(screenshot_width=300, screenshot_height=200, active_window_title="Tiny")

    adapter = LegacyBatchCaptureAdapter(clipboard=FakeClipboard(), mouse=FakeMouse())

    run = adapter.run(
        run_id="legacy_zero_cards",
        max_pages=1,
        max_jobs=3,
        focus_delay_seconds=2,
        delay_between_cards_seconds=0.25,
        include_pagination=False,
        capture_detail_phase=True,
        debug_screenshots=False,
        timeout_seconds=30,
        stop_requested=lambda: False,
    )

    codes = {event.code for event in run.diagnostics}
    assert run.status == "failed"
    assert EXP_CARD_DETECTION_ZERO_CARDS in codes
    zero_event = next(event for event in run.diagnostics if event.code == EXP_CARD_DETECTION_ZERO_CARDS)
    assert zero_event.details["screenshot_width"] == 300
    assert zero_event.details["active_window_title"] == "Tiny"


def test_legacy_batch_stop_condition_is_respected(monkeypatch) -> None:
    monkeypatch.setenv("JOLT_ENABLE_EXPERIMENTAL_LINKEDIN_CAPTURE", "true")

    class StopAwareAdapter(FakeLegacyBatchAdapter):
        def run(self, **kwargs) -> ExperimentalCaptureRunPackage:  # type: ignore[no-untyped-def]
            runner._STOP_REQUESTED = True
            return super().run(**kwargs)

    monkeypatch.setattr(runner, "LEGACY_BATCH_ADAPTER_FACTORY", StopAwareAdapter)
    client = TestClient(app)

    response = client.post(
        "/api/experimental-capture/linkedin/start",
        json={"mode": "legacy_batch_capture", "max_pages": 2, "max_jobs": 4, "dry_run": False},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "stopped"
    assert payload["captured_count"] == 0


def test_legacy_batch_review_latest_uses_existing_capture_pipeline(monkeypatch) -> None:
    monkeypatch.setenv("JOLT_ENABLE_EXPERIMENTAL_LINKEDIN_CAPTURE", "true")
    monkeypatch.setattr(runner, "LEGACY_BATCH_ADAPTER_FACTORY", FakeLegacyBatchAdapter)
    client = TestClient(app)
    client.post(
        "/api/experimental-capture/linkedin/start",
        json={"mode": "legacy_batch_capture", "max_pages": 1, "max_jobs": 2, "dry_run": False},
    )

    response = client.post(
        "/api/experimental-capture/linkedin/review-latest",
        json={"profile_id": "rafael_default"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_captured"] == 2
    assert payload["results"][0]["raw_job"]["source"] == "experimental_linkedin_legacy_batch"
    assert "legacy batch experimental capture" in payload["results"][0]["raw_job"]["capture_notes"]


def test_mouse_control_test_feature_flag_disabled(monkeypatch) -> None:
    monkeypatch.delenv("JOLT_ENABLE_EXPERIMENTAL_LINKEDIN_CAPTURE", raising=False)
    client = TestClient(app)

    response = client.post("/api/experimental-capture/linkedin/test-mouse-control")

    assert response.status_code == 200
    payload = response.json()
    assert payload["enabled"] is False
    assert payload["status"] == "disabled"


def test_mouse_control_test_with_fake_mouse(monkeypatch) -> None:
    monkeypatch.setenv("JOLT_ENABLE_EXPERIMENTAL_LINKEDIN_CAPTURE", "true")
    monkeypatch.setattr(windows_selected_job_adapter.time, "sleep", lambda seconds: None)
    movements: list[str] = []

    class FakeMouseControl:
        def dependency_error(self) -> str:
            return ""

        def screen_size(self) -> tuple[int, int]:
            return 1920, 1080

        def mouse_position(self) -> tuple[int, int]:
            return 400, 300

        def test_small_movement(self) -> None:
            movements.append("moved")

    monkeypatch.setattr(runner, "MOUSE_CONTROL_FACTORY", FakeMouseControl)
    client = TestClient(app)

    response = client.post("/api/experimental-capture/linkedin/test-mouse-control")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert movements == ["moved"]
    codes = {event["code"] for event in payload["diagnostics"]}
    assert EXP_MOUSE_CONTROL_TEST_STARTED in codes
    assert EXP_MOUSE_CONTROL_DEPENDENCIES_OK in codes
    assert EXP_SCREEN_SIZE_CAPTURED in codes
    assert EXP_MOUSE_POSITION_CAPTURED in codes
    assert EXP_MOUSE_MOVEMENT_COMPLETED in codes


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
