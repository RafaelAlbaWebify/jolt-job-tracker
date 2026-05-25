from typing import Protocol

from app.services.experimental_linkedin_capture.models import ExperimentalCaptureRunPackage


class ExperimentalLinkedInCaptureAdapter(Protocol):
    """Future automation boundary. No implementation is provided in Phase 17A."""

    def run(self, *, max_pages: int, max_jobs: int) -> ExperimentalCaptureRunPackage:
        raise NotImplementedError

