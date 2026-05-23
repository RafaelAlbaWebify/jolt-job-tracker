import re

from app.models import NormalizedJob, ParserConfidence

LANGUAGES = ["English", "Spanish", "German", "French"]
LANGUAGE_PATTERN = "|".join(LANGUAGES)
MANDATORY_LANGUAGE_PATTERNS = [
    re.compile(rf"\b({LANGUAGE_PATTERN})\s+(?:is\s+)?(?:required|mandatory)\b", re.IGNORECASE),
    re.compile(rf"\b(?:required|mandatory)\s+(?:language\s*[:\-]\s*)?({LANGUAGE_PATTERN})\b", re.IGNORECASE),
    re.compile(rf"\b(?:fluent|native)\s+({LANGUAGE_PATTERN})\b", re.IGNORECASE),
]
OPTIONAL_LANGUAGE_PATTERN = re.compile(
    rf"\b({LANGUAGE_PATTERN})\b[^.\n]*(?:nice to have|is a plus|preferred|bonus)", re.IGNORECASE
)

FIELD_PATTERNS = {
    "title": [
        re.compile(r"^(?:job\s+title|title|role)\s*[:\-]\s*(.+)$", re.IGNORECASE | re.MULTILINE),
    ],
    "company": [
        re.compile(r"^(?:company|employer|organization|organisation)\s*[:\-]\s*(.+)$", re.IGNORECASE | re.MULTILINE),
    ],
    "location": [
        re.compile(r"^(?:location|office|based in)\s*[:\-]\s*(.+)$", re.IGNORECASE | re.MULTILINE),
    ],
}

EMPLOYMENT_PATTERNS = [
    ("full-time", re.compile(r"\bfull[ -]?time\b", re.IGNORECASE)),
    ("part-time", re.compile(r"\bpart[ -]?time\b", re.IGNORECASE)),
    ("contract", re.compile(r"\bcontract(?:or)?\b", re.IGNORECASE)),
    ("internship", re.compile(r"\binternship\b", re.IGNORECASE)),
]

# Parser signals are neutral extraction hints. Profile-specific preference weighting stays in rule profiles.
TECHNICAL_SIGNAL_PATTERNS = [
    ("Microsoft 365", re.compile(r"\bMicrosoft\s+365\b", re.IGNORECASE)),
    ("Entra ID", re.compile(r"\bEntra\s+ID\b", re.IGNORECASE)),
    ("SaaS", re.compile(r"\bSaaS\b", re.IGNORECASE)),
    ("API", re.compile(r"\bAPIs?\b", re.IGNORECASE)),
    ("SQL", re.compile(r"\bSQL\b", re.IGNORECASE)),
    ("PowerShell", re.compile(r"\bPowerShell\b", re.IGNORECASE)),
    ("Azure", re.compile(r"\bAzure\b", re.IGNORECASE)),
]

RISK_SIGNAL_PATTERNS = [
    ("24/7", re.compile(r"\b24\s*/\s*7\b", re.IGNORECASE)),
    ("rotating shifts", re.compile(r"\brotating\s+shifts?\b", re.IGNORECASE)),
    ("night shifts", re.compile(r"\bnight\s+shifts?\b", re.IGNORECASE)),
    ("weekends", re.compile(r"\bweekends?\b", re.IGNORECASE)),
    ("call-center", re.compile(r"\bcall[- ]cent(?:er|re)\b", re.IGNORECASE)),
    ("high pressure", re.compile(r"\bhigh[- ]pressure\b", re.IGNORECASE)),
    ("chaotic startup", re.compile(r"\bchaotic\s+startup\b", re.IGNORECASE)),
]

ON_CALL_PATTERNS = [
    ("heavy on-call", re.compile(r"\bheavy\s+on[- ]call\b", re.IGNORECASE)),
    ("on-call", re.compile(r"\bon[- ]call\b", re.IGNORECASE)),
]

SHIFT_PATTERNS = [
    ("24/7", re.compile(r"\b24\s*/\s*7\b", re.IGNORECASE)),
    ("rotating shifts", re.compile(r"\brotating\s+shifts?\b", re.IGNORECASE)),
    ("night shifts", re.compile(r"\bnight\s+shifts?\b", re.IGNORECASE)),
    ("weekends", re.compile(r"\bweekends?\b", re.IGNORECASE)),
]


def _clean_value(value: str) -> str:
    return value.strip().strip(" -|\t")


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = value.lower()
        if key not in seen:
            seen.add(key)
            result.append(value)
    return result


def _extract_labeled_field(raw_text: str, field: str) -> str:
    for pattern in FIELD_PATTERNS[field]:
        match = pattern.search(raw_text)
        if match:
            return _clean_value(match.group(1))
    return ""


def _detect_work_mode(raw_text: str, parser_notes: list[str]) -> str:
    remote = bool(re.search(r"\bremote\b", raw_text, re.IGNORECASE))
    hybrid = bool(re.search(r"\bhybrid\b", raw_text, re.IGNORECASE))
    onsite = bool(re.search(r"\b(?:onsite|on-site|on site|in-office|in office)\b", raw_text, re.IGNORECASE))

    detected = [mode for mode, present in [("remote", remote), ("hybrid", hybrid), ("onsite", onsite)] if present]
    if len(detected) > 1:
        parser_notes.append(f"Conflicting work mode signals found: {', '.join(detected)}.")
        return "unknown"
    if detected:
        return detected[0]

    parser_notes.append("Work mode is unclear.")
    return "unknown"


def _detect_languages(raw_text: str) -> tuple[list[str], list[str]]:
    detected = [language for language in LANGUAGES if re.search(rf"\b{language}\b", raw_text, re.IGNORECASE)]
    optional = {match.group(1).lower() for match in OPTIONAL_LANGUAGE_PATTERN.finditer(raw_text)}

    mandatory: list[str] = []
    for pattern in MANDATORY_LANGUAGE_PATTERNS:
        for match in pattern.finditer(raw_text):
            language = match.group(1)
            if language.lower() not in optional:
                mandatory.append(language.capitalize())

    return _dedupe(detected), _dedupe(mandatory)


def _detect_employment_type(raw_text: str) -> str:
    for employment_type, pattern in EMPLOYMENT_PATTERNS:
        if pattern.search(raw_text):
            return employment_type
    return ""


def _detect_pattern_matches(raw_text: str, patterns: list[tuple[str, re.Pattern[str]]]) -> list[str]:
    return [label for label, pattern in patterns if pattern.search(raw_text)]


def _confidence(raw_text: str, job: NormalizedJob, parser_notes: list[str]) -> ParserConfidence:
    word_count = len(re.findall(r"\w+", raw_text))
    missing_critical = sum(
        1
        for value in [job.title, job.company, job.location]
        if not value
    )
    if job.work_mode == "unknown":
        missing_critical += 1

    if word_count < 20 or missing_critical >= 3:
        return "low"
    if missing_critical >= 1 or parser_notes:
        return "medium"
    return "high"


def parse_job(raw_text: str, source_url: str = "") -> NormalizedJob:
    normalized_text = raw_text.strip()
    parser_notes: list[str] = []

    title = _extract_labeled_field(normalized_text, "title")
    company = _extract_labeled_field(normalized_text, "company")
    location = _extract_labeled_field(normalized_text, "location")

    if not title:
        parser_notes.append("Title was not found using supported labels.")
    if not company:
        parser_notes.append("Company was not found using supported labels.")
    if not location:
        parser_notes.append("Location was not found using supported labels.")

    work_mode = _detect_work_mode(normalized_text, parser_notes)
    languages_detected, mandatory_languages = _detect_languages(normalized_text)
    if languages_detected and not mandatory_languages:
        parser_notes.append("Languages were detected, but mandatory language requirements are unclear.")
    elif not languages_detected:
        parser_notes.append("No language requirements were detected.")

    job = NormalizedJob(
        title=title,
        company=company,
        location=location,
        work_mode=work_mode,
        source_url=source_url or "",
        description=normalized_text,
        languages_detected=languages_detected,
        mandatory_languages=mandatory_languages,
        employment_type=_detect_employment_type(normalized_text),
        shift_indicators=_detect_pattern_matches(normalized_text, SHIFT_PATTERNS),
        on_call_indicators=_detect_pattern_matches(normalized_text, ON_CALL_PATTERNS),
        positive_keywords=_detect_pattern_matches(normalized_text, TECHNICAL_SIGNAL_PATTERNS),
        risk_keywords=_detect_pattern_matches(normalized_text, RISK_SIGNAL_PATTERNS),
        parser_notes=parser_notes,
    )
    job.parser_confidence = _confidence(normalized_text, job, parser_notes)
    return job
