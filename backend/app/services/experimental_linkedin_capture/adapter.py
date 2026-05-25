from typing import Protocol

from app.services.experimental_linkedin_capture.diagnostics import (
    EXP_CARD_CLICK_ATTEMPTED,
    EXP_CARD_SELECTED,
    EXP_CAPTURE_COMPLETED,
    EXP_CAPTURE_STARTED,
    EXP_DETAIL_TEXT_READY,
    EXP_DUPLICATE_JOB_ID,
    EXP_JOB_LIMIT_REACHED,
    EXP_PAGE_LIMIT_REACHED,
    EXP_URL_CURRENT_JOB_ID_MATCHED,
    diagnostic_event,
    utc_now_iso,
)
from app.services.experimental_linkedin_capture.models import (
    ExperimentalCapturedJobRecord,
    ExperimentalCaptureRunPackage,
)


class ExperimentalLinkedInCaptureAdapter(Protocol):
    """Future automation boundary.

    Phase 17B provides only a mock implementation. No browser control is performed.
    """

    def run(self, *, run_id: str, max_pages: int, max_jobs: int) -> ExperimentalCaptureRunPackage:
        raise NotImplementedError


class MockExperimentalLinkedInCaptureAdapter:
    """Fake capture adapter that exercises the run-package shape with demo data only."""

    _FAKE_CARDS = [
        {
            "source_url": "https://www.linkedin.com/jobs/view/900100001/",
            "current_job_id": "900100001",
            "title": "Mock Microsoft 365 Support Specialist",
            "company": "Demo Cloud Services",
            "location": "Remote, Spain",
            "raw_text": (
                "Title: Mock Microsoft 365 Support Specialist\n"
                "Company: Demo Cloud Services\n"
                "Location: Remote, Spain\n"
                "Work mode: Remote\n"
                "English required. Support Microsoft 365, endpoint troubleshooting, and ticket triage. "
                "This is fake demo data from the experimental dry-run adapter."
            ),
            "page_index": 1,
            "card_index": 1,
        },
        {
            "source_url": "https://www.linkedin.com/jobs/view/900100002/",
            "current_job_id": "900100002",
            "title": "Mock IT Support Analyst",
            "company": "Demo Desk",
            "location": "Vigo, Spain",
            "raw_text": (
                "Title: Mock IT Support Analyst\n"
                "Company: Demo Desk\n"
                "Location: Vigo, Spain\n"
                "Work mode: Hybrid\n"
                "English and Spanish required. Help desk, Windows endpoint support, networking basics, "
                "and internal user support. Fake demo data only."
            ),
            "page_index": 1,
            "card_index": 2,
        },
        {
            "source_url": "https://www.linkedin.com/jobs/view/900100001/?trackingId=duplicate-demo",
            "current_job_id": "900100001",
            "title": "Mock Microsoft 365 Support Specialist",
            "company": "Demo Cloud Services",
            "location": "Remote, Spain",
            "raw_text": (
                "Title: Mock Microsoft 365 Support Specialist\n"
                "Company: Demo Cloud Services\n"
                "Location: Remote, Spain\n"
                "Work mode: Remote\n"
                "Duplicate dry-run card for the same fake currentJobId. This record exists only to "
                "exercise duplicate diagnostics."
            ),
            "page_index": 1,
            "card_index": 3,
        },
        {
            "source_url": "https://www.linkedin.com/jobs/view/900200001/",
            "current_job_id": "900200001",
            "title": "Mock SaaS Support Engineer",
            "company": "Demo Support Lab",
            "location": "Remote, Europe",
            "raw_text": (
                "Title: Mock SaaS Support Engineer\n"
                "Company: Demo Support Lab\n"
                "Location: Remote, Europe\n"
                "Work mode: Remote\n"
                "Customer-facing SaaS support, troubleshooting APIs, documenting issues, and escalation "
                "coordination. Fake demo data only."
            ),
            "page_index": 2,
            "card_index": 1,
        },
    ]

    def run(self, *, run_id: str, max_pages: int, max_jobs: int) -> ExperimentalCaptureRunPackage:
        started_at = utc_now_iso()
        diagnostics = [
            diagnostic_event(
                EXP_CAPTURE_STARTED,
                "Mock dry-run capture started; no browser automation was executed.",
                details={"max_pages": max_pages, "max_jobs": max_jobs, "mock": True},
            )
        ]
        captured_jobs: list[ExperimentalCapturedJobRecord] = []
        first_sequence_by_job_id: dict[str, int] = {}

        eligible_cards = [card for card in self._FAKE_CARDS if int(card["page_index"]) <= max_pages]
        for card in eligible_cards:
            if len(captured_jobs) >= max_jobs:
                diagnostics.append(
                    diagnostic_event(
                        EXP_JOB_LIMIT_REACHED,
                        "Mock dry-run stopped at the configured job limit.",
                        details={"max_jobs": max_jobs},
                    )
                )
                break

            sequence = len(captured_jobs) + 1
            job_id = str(card["current_job_id"])
            per_job_diagnostics = [
                diagnostic_event(
                    EXP_CARD_CLICK_ATTEMPTED,
                    "Mock card selection attempted. No browser click occurred.",
                    details={"sequence": sequence, "page_index": int(card["page_index"])},
                ),
                diagnostic_event(
                    EXP_CARD_SELECTED,
                    "Mock card selected.",
                    details={"sequence": sequence, "card_index": int(card["card_index"])},
                ),
                diagnostic_event(
                    EXP_URL_CURRENT_JOB_ID_MATCHED,
                    "Mock URL/currentJobId matched.",
                    details={"sequence": sequence, "current_job_id": job_id},
                ),
                diagnostic_event(
                    EXP_DETAIL_TEXT_READY,
                    "Mock detail text ready.",
                    details={"sequence": sequence},
                ),
            ]
            duplicate_of = first_sequence_by_job_id.get(job_id)
            if duplicate_of is not None:
                duplicate_event = diagnostic_event(
                    EXP_DUPLICATE_JOB_ID,
                    "Mock duplicate currentJobId detected.",
                    level="warning",
                    details={"sequence": sequence, "duplicate_of": duplicate_of, "current_job_id": job_id},
                )
                per_job_diagnostics.append(duplicate_event)
                diagnostics.append(duplicate_event)
            else:
                first_sequence_by_job_id[job_id] = sequence

            captured_jobs.append(
                ExperimentalCapturedJobRecord(
                    sequence=sequence,
                    source_url=str(card["source_url"]),
                    current_job_id=job_id,
                    title=str(card["title"]),
                    company=str(card["company"]),
                    location=str(card["location"]),
                    raw_text=str(card["raw_text"]),
                    capture_state="mock_duplicate" if duplicate_of else "mock_captured",
                    page_index=int(card["page_index"]),
                    card_index=int(card["card_index"]),
                    duplicate_of=duplicate_of,
                    diagnostics=per_job_diagnostics,
                )
            )
            diagnostics.extend(per_job_diagnostics)

        if max_pages < 2:
            diagnostics.append(
                diagnostic_event(
                    EXP_PAGE_LIMIT_REACHED,
                    "Mock dry-run stopped at the configured page limit.",
                    details={"max_pages": max_pages},
                )
            )

        diagnostics.append(
            diagnostic_event(
                EXP_CAPTURE_COMPLETED,
                "Mock dry-run completed.",
                details={"captured_jobs": len(captured_jobs)},
            )
        )
        return ExperimentalCaptureRunPackage(
            run_id=run_id,
            status="completed",
            started_at=started_at,
            finished_at=utc_now_iso(),
            max_pages=max_pages,
            max_jobs=max_jobs,
            captured_jobs=captured_jobs,
            diagnostics=diagnostics,
            warnings=[
                "Mock dry-run package uses fake demo data only.",
                "No browser was controlled, no pages were opened, and no LinkedIn session was accessed.",
            ],
        )
