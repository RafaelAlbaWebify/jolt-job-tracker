from __future__ import annotations

import csv
import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional, Tuple

CAPTURE_OUTPUT_DIR = Path("captures_id")
DEFAULT_INPUT_GLOB = "linkedin_job_text_v35_*.jsonl"

ROLE_TERMS = [
    "engineer", "support", "analyst", "developer", "administrator", "manager",
    "specialist", "consultant", "technician", "architect", "operator",
    "coordinator", "assistant", "lead", "director", "representative",
    "customer", "cloud", "systems", "security", "data", "software",
    "application", "technical", "service desk", "product", "operations",
    "qa", "test", "endpoint", "infrastructure", "helpdesk", "servicedesk",
    "virtualization", "collaboration", "automation", "response analyst",
    "field hardware", "service engineer", "business analyst",
]

BAD_TITLE_PATTERNS = [
    r"^share$",
    r"logo$",
    r"profile photo$",
    r"is verified$",
    r"is hiring$",
    r"school alum",
    r"company alum",
    r"alum works here",
    r"be an early applicant",
    r"company review time",
    r"viewed",
    r"promoted",
    r"applicants?",
    r"clicked apply",
    r"retry premium",
    r"premium",
    r"about the company",
    r"about the job",
    r"about the role",
    r"people you can reach out to",
    r"meet the hiring team",
    r"show all",
    r"connect$",
    r"message$",
    r"job search faster",
    r"see curated ai tools",
    r"your profile matches",
    r"skills associated",
    r"assessment",
    r"benefits found",
    r"similar jobs",
    r"more searches",
    r"sign in",
    r"^description$",
    r"^job description$",
    r"^responsibilities$",
    r"^requirements$",
    r"^key responsibilities$",
    r"^what you will do$",
    r"^what you'll do$",
    r"^the work you.?ll do$",
    r"^how you will contribute$",
    r"^what we offer$",
    r"^what you bring$",
    r"^about you$",
    r"^your profile$",
    r"^exceptional leadership$",
    r"^technical expertise$",
    r"^qué encontrarás",
    r"^que encontrarás",
]

BAD_TITLE_STARTS = [
    "take ",
    "serve ",
    "learn ",
    "minimum ",
    "be a ",
    "be an ",
    "participate ",
    "front line ",
    "realizar ",
    "realiza ",
    "manage our ",
    "manage the ",
    "manage system ",
    "support and ",
    "support our ",
    "provide ",
    "you will ",
    "you'll ",
    "responsible for ",
    "work with ",
    "work closely ",
    "collaborate ",
    "own ",
    "drive ",
    "ensure ",
    "maintain ",
    "troubleshoot ",
    "assist ",
    "monitor ",
    "resolve ",
    "respond ",
    "improve ",
    "write ",
    "optimize ",
    "develop ",
    "implement ",
    "coordinate ",
    "coordinating ",
    "facilitate ",
    "help ",
    "give ",
    "perform ",
    "performing ",
    "key responsibilities",
    "lead incident management",
    "lead post-incident",
    "user´s support",
    "user's support",
]

BAD_TITLE_CONTAINS = [
    "years of professional experience",
    "years of experience",
    "professional experience as",
    "experience in ",
    "experience with ",
    "about datacamp",
    "alphanumeric systems",
    "experience as an",
    "experience as a",
    "proven experience",
    "technical inquiries",
    "resolve incidents",
    "with customers",
    "on-call rotations",
    "google systems and licences",
    "customer accounts",
    "internal documentation",
    "support processes",
    "incident management and post-incident reviews",
    "payments integrations",
    "complex sql queries",
    "data-related issues",
    "spare parts management",
    "backup/recovery",
    "disaster recovery",
    "stakeholders",
    "smooth execution",
    "offices around the world",
    "addition and removal of modules",
    "what you'll be doing",
    "what you will be doing",
]

BAD_TITLE_EXACT = {
    "active directory",
    "operations",
    "digital security",
    "key responsibilities user support",
    "1. data foundation & validation",
}


BAD_COMPANY_OR_LOCATION_VALUES = {
    "are these results helpful?",
    "your feedback helps us improve job recommendations.",
    "next",
    "previous",
    "share",
    "show more options",
    "message",
    "save",
    "3",
    "1",
    "2",
    "…",
}

KNOWN_COMPANY_AS_LOCATION_VALUES = {
    "acronis", "laravel", "ninjaone", "ust", "board", "corus consulting",
    "jobgether", "h&k | smart tech. human touch", "h&k smart tech human touch",
}


def is_suspicious_company_or_location(company: str, location: str) -> bool:
    c = (company or "").strip().lower()
    l = (location or "").strip().lower()
    if c in BAD_COMPANY_OR_LOCATION_VALUES or l in BAD_COMPANY_OR_LOCATION_VALUES:
        return True
    if l in KNOWN_COMPANY_AS_LOCATION_VALUES:
        return True
    # A location normally looks like a geography or contains a workplace marker.
    # If it is just a company-ish token, the right-panel anchor likely drifted into UI/left-list text.
    if location and not is_location_line(location) and not re.search(r"\((remote|hybrid|on-site|onsite)\)", location, flags=re.I):
        # Allow rare broad regions; reject short clean proper names that are not places.
        if len(location.split()) <= 5 and not re.search(r"\b(spain|madrid|barcelona|lisbon|portugal|france|germany|ireland|netherlands|hungary|europe|remote|metropolitan|area|county|community|province|region|city|dublin|paris|berlin|budapest|amsterdam|malaga|málaga|valencia|sevilla|zaragoza)\b", l):
            return True
    return False


def selected_detail_source_is_trusted(title_source: str) -> bool:
    src = (title_source or "").lower()
    return src.startswith("right_panel_save_anchor") or src == "right_panel_anchor_before_about"


@dataclass
class ParsedJob:
    sequence: int
    source_sequence: int
    page_number: int
    page_start: int
    viewport_index: int
    card_index: int
    current_job_id: str
    url: str
    raw_status: str

    job_title: str
    job_title_source: str
    company: str
    location: str
    workplace_type: str
    employment_type: str
    applicant_count: str
    easy_apply: str
    promoted: str
    linkedin_card_state: str
    linkedin_applied: str
    linkedin_viewed: str
    linkedin_easy_apply: str
    linkedin_promoted: str
    linkedin_actively_reviewing: str

    hiring_team_names: str
    hiring_team_degrees: str
    hiring_team_profile_urls: str

    about_job_chars: int
    raw_about_job: str
    parser_notes: str


def normalize_lines(raw_text: str) -> List[str]:
    lines = []
    for line in (raw_text or "").splitlines():
        clean = re.sub(r"\s+", " ", line).strip()
        if clean:
            lines.append(clean)
    return lines


def find_latest_input_file() -> Optional[Path]:
    candidates = sorted(
        CAPTURE_OUTPUT_DIR.glob(DEFAULT_INPUT_GLOB),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def yesno(v: bool) -> str:
    return "yes" if v else "no"


def is_bad_title(line: str) -> bool:
    raw = (line or "").strip()
    low = raw.lower()

    if low in BAD_TITLE_EXACT or is_too_generic_title(raw):
        return True

    if re.match(r"^\d+[.)]\s+", low):
        return True

    if not low:
        return True

    # LinkedIn/chrome noise or unusable length.
    if len(low) < 4 or len(low) > 120:
        return True

    # Very long candidates are usually responsibilities, not titles.
    if len(raw.split()) > 14:
        return True

    for pat in BAD_TITLE_PATTERNS:
        if re.search(pat, low, flags=re.I):
            return True

    if any(low.startswith(prefix) for prefix in BAD_TITLE_STARTS):
        return True

    if any(fragment in low for fragment in BAD_TITLE_CONTAINS):
        return True

    # Reject sentence-like candidates.
    if raw.endswith("."):
        return True

    if "," in raw and len(raw.split()) > 8:
        return True

    # Reject obvious questions/headings.
    if "?" in raw or "¿" in raw:
        return True

    return False


def has_role_term(text: str) -> bool:
    low = (text or "").lower()
    return any(term in low for term in ROLE_TERMS)




def is_too_generic_title(text: str) -> bool:
    """Reject short skill/category headings that are often copied from LinkedIn/body sections."""
    low = (text or "").strip().lower()
    generic_exact = {
        "digital security",
        "active directory",
        "operations",
        "user support",
        "systems administration",
        "technical expertise",
        "exceptional leadership",
    }
    if low in generic_exact:
        return True
    # Two-word category labels ending in a broad domain are usually not job titles.
    broad_domains = {"security", "operations", "administration", "support"}
    parts = low.replace("&", " ").split()
    if len(parts) == 2 and parts[-1] in broad_domains and not any(
        role in low for role in ["engineer", "analyst", "specialist", "technician", "manager", "consultant"]
    ):
        return True
    return False


def clean_title(title: str) -> str:
    title = re.sub(r"\s+", " ", title or "").strip(" .:-–—!|")
    title = re.sub(r"\s+with verification$", "", title, flags=re.I)
    title = re.sub(r"\s*\|\s*LinkedIn.*$", "", title, flags=re.I)

    # Fix duplicated pasted titles:
    # "Service EngineerService Engineer" -> "Service Engineer"
    # "Desk Side Support EngineerDesk Side Support Engineer" -> "Desk Side Support Engineer"
    if len(title) % 2 == 0:
        half = len(title) // 2
        if title[:half].strip().lower() == title[half:].strip().lower():
            title = title[:half].strip()

    # Common LinkedIn/body pattern cleanup.
    title = re.sub(r"^We are looking for (?:an?|the)?\s+", "", title, flags=re.I)
    title = re.sub(r"^We're looking for (?:an?|the)?\s+", "", title, flags=re.I)
    title = re.sub(r"^We are seeking (?:an?|the)?\s+", "", title, flags=re.I)
    title = re.sub(r"^We are currently seeking (?:an?|the)?\s+", "", title, flags=re.I)
    title = re.sub(r"^Posici[oó]n\s*:\s*", "", title, flags=re.I)
    title = re.sub(r"^Position\s*:\s*", "", title, flags=re.I)
    title = re.sub(r"^Title\s*:\s*", "", title, flags=re.I)

    return title.strip(" .:-–—!|")


def extract_about_job(raw_text: str) -> str:
    text = raw_text or ""

    start_patterns = [
        r"\nAbout the job\s*\n",
        r"\nAbout The Job\s*\n",
        r"\nAbout the role\s*\n",
        r"\nJob Description\s*\n",
        r"\nDescription\s*\n",
    ]

    start = None
    for pat in start_patterns:
        m = re.search(pat, text, flags=re.I)
        if m:
            start = m.end()
            break

    if start is None:
        # Last resort: the whole text may already be mostly the job body.
        # But avoid dumping the entire page if it is clearly LinkedIn chrome.
        lines = normalize_lines(text)
        if len(lines) > 20:
            start = 0
        else:
            return ""

    tail = text[start:].strip()

    stop_patterns = [
        r"\n\s*Benefits found in job post\s*\n",
        r"\n\s*Job search faster with Premium\s*\n",
        r"\n\s*About the company\s*\n",
        r"\n\s*Seniority level\s*\n",
        r"\n\s*Employment type\s*\n",
        r"\n\s*Job function\s*\n",
        r"\n\s*Industries\s*\n",
        r"\n\s*Referrals increase your chances\s*\n",
        r"\n\s*People also viewed\s*\n",
        r"\n\s*Similar jobs\s*\n",
        r"\n\s*More searches\s*\n",
        r"\n\s*Sign in to create job alert\s*\n",
        r"\n\s*See curated AI tools for your job search\s*\n",
    ]

    stop = len(tail)
    for pat in stop_patterns:
        m = re.search(pat, tail, flags=re.I)
        if m and m.start() < stop:
            stop = m.start()

    about = tail[:stop].strip()
    about = re.sub(r"\n{3,}", "\n\n", about)
    return about


def is_bad_panel_capture(raw_text: str, about: str, lines: List[str]) -> bool:
    low = (raw_text or "").lower()

    overlay_signals = [
        "loading job details",
        "rafael albastatus",
        "messaging",
        "you are on the messaging overlay",
    ]

    if "loading job details" in low and "messaging" in low:
        return True

    if any(sig in low for sig in overlay_signals) and len(about or "") < 700:
        return True

    # If there is no real job body and the copied text looks like LinkedIn chrome.
    if len(lines) < 25 and not about:
        return True

    return False



HEADER_NOISE_EXACT = {
    "top job picks for you", "based on your profile, preferences, and activity like applies, searches, and saves",
    "viewed", "promoted", "easy apply", "be an early applicant", "actively reviewing applicants",
    "company review time is typically 1 week", "jobs no longer available were omitted from results",
    "about", "accessibility", "help center", "privacy & terms", "ad choices", "advertising",
    "business services", "get the linkedin app", "more", "linkedin corporation © 2026",
    "thanks for your feedback. tell us more", "previous", "next", "1", "2",
}


def is_header_noise(line: str) -> bool:
    low = (line or "").strip().lower()
    if not low:
        return True
    if low in HEADER_NOISE_EXACT:
        return True
    if low.endswith(" logo"):
        return True
    if "university" in low and "alum" in low:
        return True
    if "school alum" in low or "school alumni" in low:
        return True
    if "connection works here" in low or "connections work here" in low:
        return True
    if "with verification" == low:
        return True
    if re.fullmatch(r"\d+ results?", low):
        return True
    if re.fullmatch(r"\d+ applicants?", low):
        return True
    return False


def clean_header_candidate(line: str) -> str:
    c = clean_title(line)
    # Some copied LinkedIn card text is "TitleTitle with verification".
    c = re.sub(r"\s+with verification$", "", c, flags=re.I).strip()
    if len(c) % 2 == 0:
        half = len(c) // 2
        if c[:half].strip().lower() == c[half:].strip().lower():
            c = c[:half].strip()
    return c.strip(" .:-–—!|")


def is_plausible_company_line(line: str) -> bool:
    raw = (line or "").strip()
    low = raw.lower()
    if not raw or len(raw) > 90:
        return False
    if is_header_noise(raw):
        return False
    if is_location_line(raw):
        return False
    if has_role_term(raw):
        return False
    bad_fragments = [
        "pay range", "remote", "hybrid", "on-site", "onsite", "based in", "permanent work at home",
        "full-time", "part-time", "contract", "internship", "activos", "applicants", "followers",
        "reposted", "published", "viewed", "promoted", "easy apply",
    ]
    if any(f in low for f in bad_fragments):
        return False
    return True


def extract_header_fields(lines: List[str]) -> Tuple[str, str, str, str]:
    """Return title, company, location, source from the copied LinkedIn header/card area.

    The parser v27 preferred the first body line, which can be marketing copy. This header-first
    extractor looks before About the job for a title-like line, then takes the next plausible
    non-noise line as company and the next explicit place/remote/hybrid line as location.
    """
    limit = min(len(lines), 180)
    for i, line in enumerate(lines):
        if re.search(r"^(About the job|About The Job|About the role|Job Description|Description)$", line, flags=re.I):
            limit = i
            break
    header = lines[:limit]

    for i, raw in enumerate(header[:120]):
        cand = clean_header_candidate(raw)
        if not cand or is_header_noise(cand):
            continue
        if not has_role_term(cand) or is_bad_title(cand):
            continue
        # Avoid selecting body/responsibility sentences that leaked into the header.
        if len(cand.split()) > 12:
            continue
        company = ""
        location = ""
        for nxt in header[i + 1:i + 10]:
            n = nxt.strip()
            if not n or is_header_noise(n):
                continue
            if not company and is_plausible_company_line(n):
                company = n
                continue
            if is_location_line(n) and len(n) <= 140:
                location = clean_location(n)
                break
        return cand, company, location, "header_first_card"
    return "", "", "", ""



def find_about_index(lines: List[str]) -> int:
    for i, line in enumerate(lines):
        if re.fullmatch(r"About the job|About The Job|About the role|Job Description|Description", line, flags=re.I):
            return i
    return -1


def is_salary_or_compensation_line(line: str) -> bool:
    low = (line or "").lower().strip()
    return bool(re.search(r"[$€£]\s*\d|\b\d+\s*k\s*/\s*yr\b|\b/hr\b|\bsalary\b|\bpay range\b", low, flags=re.I))


def is_detail_panel_noise(line: str, selected_title: str = "") -> bool:
    raw = (line or "").strip()
    low = raw.lower()
    if not raw:
        return True
    if is_header_noise(raw):
        return True
    if selected_title and low == selected_title.lower():
        return True
    noise_fragments = [
        "matches your job preferences", "workplace type is", "employment type is",
        "responses managed off linkedin", "you'd be a top applicant", "see how you compare",
        "meet the hiring team", "people you can reach out to", "viewed", "promoted",
        "apply", "easy apply", "be an early applicant", "job alert", "similar jobs",
        "save ", "saved ", "share", "show all", "company review time",
    ]
    if any(f in low for f in noise_fragments):
        return True
    if re.search(r"\b\d+\s+people clicked apply\b", low):
        return True
    if re.search(r"\b\d+\s+applicants?\b", low):
        return True
    return False


def split_linkedin_dot_line(line: str) -> List[str]:
    return [p.strip() for p in re.split(r"\s*[·•]\s*", line or "") if p.strip()]


def parse_company_location_meta(line: str) -> Tuple[str, str]:
    """Parse LinkedIn right-panel meta lines like:
    Company · Barcelona, Catalonia, Spain · 2 days ago · Over 100 people clicked apply
    """
    raw = (line or "").strip()
    parts = split_linkedin_dot_line(raw)
    if len(parts) < 2:
        return "", ""

    # Drop time/applicant/repost fragments after the useful company/location pieces.
    useful = []
    for part in parts:
        low = part.lower()
        if re.search(r"\b(days?|hours?|minutes?|weeks?|months?) ago\b", low):
            break
        if "clicked apply" in low or re.search(r"\bapplicants?\b", low):
            break
        if low in {"viewed", "promoted", "easy apply", "be an early applicant"}:
            break
        useful.append(part)
    if len(useful) < 2:
        useful = parts[:2]

    first, second = useful[0], useful[1]

    # Normal case: company first, location second.
    if is_plausible_company_line(first) and (is_location_line(second) or len(second) <= 90):
        loc = clean_location(second)
        return first, loc

    return "", ""


def strip_logo_suffix(line: str) -> str:
    raw = (line or "").strip()
    raw = re.sub(r"\s+logo$", "", raw, flags=re.I).strip()
    return raw


def is_right_panel_company_candidate(line: str) -> bool:
    raw = strip_logo_suffix(line)
    low = raw.lower()
    if not raw:
        return False
    if low in {"share", "show more options", "apply", "save", "remote", "full-time", "easy apply"}:
        return False
    if is_salary_or_compensation_line(raw):
        return False
    if is_location_line(raw):
        return False
    if re.search(r"\b(days?|hours?|weeks?|months?) ago\b", low):
        return False
    if "clicked apply" in low or re.search(r"\bapplicants?\b", low):
        return False
    if "skills match" in low:
        return False
    if "matches your job preferences" in low:
        return False
    if "responses managed off linkedin" in low:
        return False
    if raw.endswith(" logo"):
        return False
    return is_plausible_company_line(raw) or (2 <= len(raw) <= 90 and not has_role_term(raw))


def parse_right_panel_location_meta(line: str) -> str:
    """Parse selected detail-panel metadata lines like:
    Barcelona, Catalonia, Spain · Reposted 9 hours ago · Over 100 people clicked apply
    Spain · 4 days ago · Over 100 applicants
    The company is NOT in this line in the current LinkedIn copied text; it appears before Share.
    """
    raw = (line or "").strip()
    if not raw:
        return ""
    parts = split_linkedin_dot_line(raw)
    if not parts:
        return ""
    first = parts[0].strip()
    low = first.lower()
    if re.search(r"\b(days?|hours?|minutes?|weeks?|months?) ago\b", low):
        return ""
    if "clicked apply" in low or re.search(r"\bapplicants?\b", low):
        return ""
    if is_salary_or_compensation_line(first):
        return ""
    if "skills match" in low or "matches your job preferences" in low:
        return ""
    if first.lower() in {"remote", "hybrid", "on-site", "full-time", "apply", "save"}:
        return ""
    # LinkedIn sometimes has a bare country/region here (Spain, France, Greater Dublin).
    if is_location_line(first) or len(first) <= 100:
        return clean_location(first)
    return ""



def clean_company_name(company: str) -> str:
    raw = strip_logo_suffix(company or "")
    raw = re.sub(r"\s+with verification$", "", raw, flags=re.I).strip()
    raw = raw.strip(" .:-–—")
    return raw


def extract_save_title_company(window: List[str]) -> Tuple[str, str, int]:
    """Extract the selected right-panel title/company from LinkedIn's reliable CTA line:
    "Save TITLE at COMPANY".

    Use the last occurrence before About the job because the left list and right panel may both
    be present in copied text, and the right-panel CTA is closest to the job body.
    """
    for idx in range(len(window) - 1, -1, -1):
        raw = (window[idx] or "").strip()
        if not raw.lower().startswith("save "):
            continue
        if raw.lower() in {"save", "saved"}:
            continue
        # Greedy title so titles that contain " at " are handled:
        # "Save Expression of Interest - Join us at Xata! at Xata.io"
        m = re.match(r"^Save\s+(.+)\s+at\s+(.+)$", raw, flags=re.I)
        if not m:
            continue
        title = clean_header_candidate(m.group(1))
        company = clean_company_name(m.group(2))
        if not title or not company:
            continue
        # The save line is a right-panel UI string; do not require ROLE_TERMS here.
        if is_bad_title(title):
            # v33: a title coming from LinkedIn's selected right-panel CTA is strong evidence.
            # Some real postings are generic, e.g. "Technical Support" or "IT Support",
            # which our generic-title filter rejects elsewhere to avoid body/header noise.
            low = title.lower()
            allowed_generic_save_titles = {
                "technical support",
                "it support",
                "customer support",
                "business support",
                "application support",
                "product support",
                "systems support",
                "system support",
            }
            if not (
                low in allowed_generic_save_titles
                or "expression of interest" in low
                or "join us" in low
                or low.startswith("technical support ")
                or low.startswith("it support ")
                or low.startswith("customer support ")
            ):
                continue
        if not is_right_panel_company_candidate(company):
            # Some real company names include role-ish words or punctuation; still reject obvious UI noise.
            lowc = company.lower()
            if lowc in {"save", "share", "show more options", "remote", "full-time", "next", "previous"}:
                continue
            if is_salary_or_compensation_line(company) or is_location_line(company):
                continue
        return title, company, idx
    return "", "", -1


def find_location_for_saved_title(window: List[str], title: str, save_idx: int = -1) -> str:
    """Find the selected job location line near the title in the right-panel header."""
    if not title:
        return ""
    title_norm = clean_header_candidate(title).lower()

    # Prefer title occurrences after the last Show more options before the Save line.
    upper = save_idx if save_idx >= 0 else len(window)
    show_indices = [i for i, x in enumerate(window[:upper]) if re.fullmatch(r"show more options", x or "", flags=re.I)]
    starts = [show_indices[-1] + 1] if show_indices else [max(0, upper - 35)]
    starts.append(0)

    seen = set()
    for start in starts:
        for i in range(start, upper):
            if i in seen:
                continue
            seen.add(i)
            cand = clean_header_candidate(window[i])
            if cand.lower() != title_norm:
                continue
            for j in range(i + 1, min(len(window), i + 12)):
                raw = (window[j] or "").strip()
                low = raw.lower()
                if not raw:
                    continue
                if low in {"remote", "hybrid", "on-site", "onsite", "full-time", "part-time", "contract", "apply", "save"}:
                    continue
                if is_salary_or_compensation_line(raw):
                    continue
                if "promoted by hirer" in low or "responses managed off linkedin" in low:
                    continue
                if "matches your job preferences" in low or "skills match" in low:
                    continue
                loc = parse_right_panel_location_meta(raw)
                if loc:
                    return loc

    # Last resort: scan between Show more options and Save for the first location/date metadata line.
    if show_indices:
        for raw in window[show_indices[-1] + 1:upper]:
            loc = parse_right_panel_location_meta(raw)
            if loc:
                return loc
    return ""


def extract_right_panel_fields(lines: List[str]) -> Tuple[str, str, str, str]:
    """Extract selected job title/company/location from the right detail panel.

    v33 primarily uses the selected detail-panel "Save TITLE at COMPANY" line before "About the job":
      Company
      Share
      Show more options
      Title
      Location · date · applicants
      ...
    This avoids reading the first visible card in the left results list as the selected job.
    """
    about_idx = find_about_index(lines)
    if about_idx < 0:
        return "", "", "", ""

    start = max(0, about_idx - 220)
    window = lines[start:about_idx]

    # Primary v33: LinkedIn's selected right-panel CTA is the most reliable source:
    # "Save TITLE at COMPANY". It sits immediately before About the job and avoids
    # reading the first visible result from the left list.
    save_title, save_company, save_idx = extract_save_title_company(window)
    if save_title and save_company:
        save_location = find_location_for_saved_title(window, save_title, save_idx)
        return save_title, save_company, save_location, "right_panel_save_anchor_relaxed_before_about"

    # Secondary: use the last Show more options before About the job.
    show_indices = [i for i, x in enumerate(window) if re.fullmatch(r"show more options", x or "", flags=re.I)]
    share_indices = [i for i, x in enumerate(window) if re.fullmatch(r"share", x or "", flags=re.I)]

    anchor = show_indices[-1] if show_indices else -1
    if anchor >= 0:
        company = ""
        # Usually: company, Share, Show more options. Search backwards a little.
        for j in range(anchor - 1, max(-1, anchor - 8), -1):
            cand = strip_logo_suffix(window[j])
            if re.fullmatch(r"share", cand or "", flags=re.I):
                continue
            if re.fullmatch(r"show more options", cand or "", flags=re.I):
                continue
            if is_right_panel_company_candidate(cand):
                company = cand
                break

        title = ""
        title_idx = -1
        # Usually the first valid title after Show more options.
        for j in range(anchor + 1, min(len(window), anchor + 8)):
            cand = clean_header_candidate(window[j])
            if not cand or is_header_noise(cand) or is_bad_title(cand):
                continue
            if has_role_term(cand) and len(cand.split()) <= 18:
                title = cand
                title_idx = j
                break

        location = ""
        if title_idx >= 0:
            # The location/date/applicant meta line normally follows the title directly.
            for j in range(title_idx + 1, min(len(window), title_idx + 10)):
                cand = window[j].strip()
                low = cand.lower()
                if not cand:
                    continue
                if low in {"remote", "hybrid", "on-site", "full-time", "part-time", "contract"}:
                    continue
                if is_salary_or_compensation_line(cand):
                    continue
                if "promoted by hirer" in low or "responses managed off linkedin" in low:
                    continue
                if "matches your job preferences" in low:
                    continue
                if "skills match" in low:
                    continue
                loc = parse_right_panel_location_meta(cand)
                if loc:
                    location = loc
                    break

        if title and (company or location):
            return title, company, location, "right_panel_anchor_before_about"

    # Secondary: last Share before About, with title after Show/Share and company before Share.
    if share_indices:
        share = share_indices[-1]
        company = ""
        for j in range(share - 1, max(-1, share - 6), -1):
            cand = strip_logo_suffix(window[j])
            if is_right_panel_company_candidate(cand):
                company = cand
                break
        title = ""
        title_idx = -1
        for j in range(share + 1, min(len(window), share + 10)):
            cand = clean_header_candidate(window[j])
            if not cand or is_header_noise(cand) or is_bad_title(cand):
                continue
            if has_role_term(cand) and len(cand.split()) <= 18:
                title = cand
                title_idx = j
                break
        location = ""
        if title_idx >= 0:
            for j in range(title_idx + 1, min(len(window), title_idx + 10)):
                loc = parse_right_panel_location_meta(window[j])
                if loc:
                    location = loc
                    break
        if title and (company or location):
            return title, company, location, "right_panel_share_anchor_before_about"

    # Fallback: v30 candidate scan, but don't let location/date/salary become company.
    candidates = []
    for i, raw in enumerate(window):
        title = clean_header_candidate(raw)
        if not title or is_header_noise(title) or is_bad_title(title):
            continue
        if not has_role_term(title) or len(title.split()) > 14:
            continue

        company = ""
        location = ""
        score = 0
        for nxt in window[i + 1:i + 18]:
            n = (nxt or "").strip()
            if not n:
                continue
            low = n.lower()
            if low == "about the job" or low.startswith("about the company"):
                break
            if is_detail_panel_noise(n, title) or is_salary_or_compensation_line(n):
                continue
            loc = parse_right_panel_location_meta(n)
            if loc and not location:
                location = loc
                score += 3
                continue
            if not company and is_right_panel_company_candidate(n):
                company = strip_logo_suffix(n)
                score += 4
                continue
        if company or location:
            proximity = i / max(1, len(window))
            candidates.append((score + proximity, title, company, location))

    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        _, title, company, location = candidates[0]
        # v33: avoid hiring-team blocks being mistaken for the selected job header.
        bad_fallback_bits = {"message", "job poster", "follow", "connect", "show all"}
        if (title or "").strip().lower() in {"talent acquisition specialist", "job poster"}:
            return "", "", "", ""
        if (company or "").strip().lower() in bad_fallback_bits:
            return "", "", "", ""
        if (location or "").strip().lower() in bad_fallback_bits:
            return "", "", "", ""
        return title, company, location, "right_panel_fallback_anchor_relaxed"

    return "", "", "", ""

def extract_company_from_about_company(lines: List[str]) -> str:
    for i, line in enumerate(lines):
        if re.fullmatch(r"About the company", line, flags=re.I):
            window = lines[i + 1:i + 20]
            for candidate in window:
                low = candidate.lower()
                if "company logo" in low:
                    continue
                if "followers" in low or "employees" in low or " on linkedin" in low:
                    continue
                if candidate.lower() in {"follow", "show more", "interested in working with us in the future?"}:
                    continue
                if len(candidate) <= 100:
                    return candidate
    return ""


def infer_company_from_about(about: str) -> str:
    lines = normalize_lines(about)
    if not lines:
        return ""

    # Pattern: "At Company,"
    for line in lines[:20]:
        m = re.search(r"\bAt\s+([A-Z][A-Za-z0-9&.\- ]{2,60}),", line)
        if m:
            return m.group(1).strip()

    # Pattern: "Company is..."
    for line in lines[:15]:
        m = re.match(r"([A-Z][A-Za-z0-9&.\- ]{2,60})\s+(is|are|somos|es)\b", line)
        if m:
            val = m.group(1).strip()
            if len(val.split()) <= 5:
                return val

    return ""


def extract_company(lines: List[str], about: str) -> str:
    return extract_company_from_about_company(lines) or infer_company_from_about(about)


def is_location_line(line: str) -> bool:
    low = (line or "").lower()
    location_terms = [
        "spain", "madrid", "barcelona", "valencia", "pontevedra", "granada",
        "alcobendas", "illescas", "guadalajara", "azuq", "andalusia",
        "galicia", "castile", "community of madrid", "remote", "hybrid",
        "on-site", "onsite", "on site",
    ]
    return any(t in low for t in location_terms)


def clean_location(line: str) -> str:
    if not line:
        return ""
    loc = line.split("·")[0].strip()
    loc = re.sub(r"\s*\((Remote|Hybrid|On-site|Onsite|On site)\)\s*", "", loc, flags=re.I).strip()
    # Avoid title-like locations.
    if has_role_term(loc) and not any(t in loc.lower() for t in ["spain", "madrid", "barcelona", "remote", "hybrid"]):
        return ""
    return loc


def extract_location(lines: List[str], about: str) -> str:
    # Do NOT trust generic "Remote" from LinkedIn chrome/header.
    # Only extract location from explicit patterns.

    body_lines = normalize_lines(about)

    explicit_patterns = [
        r"\bLocation\s*[:：]\s*(.+)",
        r"\bUbicaci[oó]n\s*[:：]\s*(.+)",
        r"\bLocalizaci[oó]n\s*[:：]\s*(.+)",
        r"\bLugar\s*[:：]\s*(.+)",
        r"\bBased in\s+(.+)",
        r"\boffice-based role in\s+(.+)",
    ]

    for line in body_lines[:120]:
        for pat in explicit_patterns:
            m = re.search(pat, line, flags=re.I)
            if m:
                loc = clean_location(m.group(1))
                if loc and len(loc) <= 100:
                    return loc

    # Conservative city/country fallback from body only.
    known_places = [
        "Madrid", "Barcelona", "Valencia", "Vigo", "Pontevedra", "Granada",
        "Guadalajara", "Azuqueca de Henares", "Alcobendas", "Illescas",
        "Spain", "España",
    ]

    for line in body_lines[:120]:
        if any(place.lower() in line.lower() for place in known_places):
            # Avoid returning a whole paragraph.
            if len(line) <= 120 and not has_role_term(line):
                return clean_location(line)

    return ""


def title_from_about_patterns(about: str) -> Tuple[str, str]:
    lines = normalize_lines(about)
    joined = "\n".join(lines[:80])

    # Direct first-line title.
    if lines:
        first = clean_title(lines[0])
        if has_role_term(first) and not is_bad_title(first):
            return first, "about_first_line"

    patterns = [
        # English
        (r"\bWe are looking for (?:an?|the)?\s*([A-Z][A-Za-z0-9/\-+&,. ]{4,100}?)(?:\s+to\b|\.|\n|$)", "about_pattern_we_are_looking_for"),
        (r"\bWe're looking for (?:an?|the)?\s*([A-Z][A-Za-z0-9/\-+&,. ]{4,100}?)(?:\s+to\b|\.|\n|$)", "about_pattern_were_looking_for"),
        (r"\bWe are currently seeking (?:an?|the)?\s*(?:experienced\s+)?([A-Z][A-Za-z0-9/\-+&,. ]{4,100}?)(?:\s+to\b|\.|\n|$)", "about_pattern_currently_seeking"),
        (r"\bAs (?:a|an) ([A-Z][A-Za-z0-9/\-+&,. ]{4,100}?), you will\b", "about_pattern_as_a"),
        (r"^The ([A-Z][A-Za-z0-9/\-+&,. ]{4,100}?) is\b", "about_pattern_the_x_is"),
        (r"\bPosition\s*[:：]\s*([A-Z][A-Za-z0-9/\-+&,. ]{4,100})", "about_pattern_position"),
        # Spanish
        (r"\bEn\s+[A-ZÁÉÍÓÚÑa-záéíóúñ0-9&,. ]+\s+buscamos\s+(?:un/a|un|una|a un/a|a un|a una)\s+([A-ZÁÉÍÓÚÑa-záéíóúñ0-9/\-+&,. ]{4,100}?)(?:\s+para\b|\.|\n|$)", "about_pattern_en_buscam"),
        (r"\bBuscamos\s+(?:un/a|un|una|a un/a|a un|a una)\s+([A-ZÁÉÍÓÚÑa-záéíóúñ0-9/\-+&,. ]{4,100}?)(?:\s+para\b|\.|\n|$)", "about_pattern_buscamos"),
        (r"\bEstamos buscando\s+(?:un/a|un|una|a un/a|a un|a una)\s+([A-ZÁÉÍÓÚÑa-záéíóúñ0-9/\-+&,. ]{4,100}?)(?:\s+para\b|\.|\n|$)", "about_pattern_estamos_buscando"),
        (r"\bActualmente buscamos incorporar\s+(?:un/a|un|una|a un/a|a un|a una)?\s*([A-ZÁÉÍÓÚÑa-záéíóúñ0-9/\-+&,. ]{4,100}?)(?:\s+para\b|\.|\n|$)", "about_pattern_actualmente_buscamos"),
        (r"\bEn la actualidad buscamos\s+(?:un/a|un|una|a un/a|a un|a una)?\s*([A-ZÁÉÍÓÚÑa-záéíóúñ0-9/\-+&,. ]{4,100}?)(?:\s+en\b|\.|\n|$)", "about_pattern_actualidad_buscamos"),
    ]

    for pat, source in patterns:
        m = re.search(pat, joined, flags=re.I | re.M)
        if not m:
            continue
        candidate = clean_title(m.group(1))
        # Trim common trailing clauses
        candidate = re.split(r"\s+(?:working|based|with|who|that|for cliente|prestando)\b", candidate, maxsplit=1, flags=re.I)[0].strip()
        if has_role_term(candidate) and not is_bad_title(candidate):
            return candidate, source

    # Section title fallback: search first 30 lines for a role-like heading.
    # v25 is intentionally stricter here because v24 picked responsibilities as titles.
    title_role_words = [
        "engineer", "analyst", "administrator", "specialist", "consultant",
        "technician", "architect", "operator", "lead", "manager",
        "service desk", "helpdesk", "servicedesk", "support engineer",
        "technical support", "system engineer", "systems engineer",
    ]
    for line in lines[:30]:
        candidate = clean_title(line)
        low_candidate = candidate.lower()
        if has_role_term(candidate) and not is_bad_title(candidate):
            if 2 <= len(candidate.split()) <= 10 and any(w in low_candidate for w in title_role_words):
                return candidate, "about_early_role_line_strict"

    return "", ""


def title_from_header(lines: List[str], company: str) -> Tuple[str, str]:
    # Limit to header area before the job body.
    limit = min(len(lines), 180)
    for i, line in enumerate(lines):
        if re.search(r"^(About the job|About The Job|Job Description|Description)$", line, flags=re.I):
            limit = i
            break

    header = lines[:limit]

    # If company appears in header, title is usually nearby.
    if company:
        for i, line in enumerate(header):
            if line.strip().lower() == company.strip().lower():
                # Check 8 lines before and after; LinkedIn order varies in copied text.
                nearby = header[max(0, i - 8):min(len(header), i + 10)]
                candidates = []
                for c in nearby:
                    c = clean_title(c)
                    if has_role_term(c) and not is_bad_title(c) and c.lower() != company.lower():
                        candidates.append(c)
                if candidates:
                    # Prefer the nearest one after company, otherwise nearest before.
                    after = [c for c in header[i + 1:i + 10] if has_role_term(c) and not is_bad_title(c)]
                    if after:
                        return clean_title(after[0]), "header_near_company_after"
                    return clean_title(candidates[-1]), "header_near_company"

    # General header fallback.
    for line in header[:120]:
        candidate = clean_title(line)
        if has_role_term(candidate) and not is_bad_title(candidate):
            return candidate, "header_role_line"

    return "", ""


def extract_title(lines: List[str], about: str, company: str) -> Tuple[str, str]:
    # Prefer about-based title because copied header contains lots of LinkedIn noise.
    title, src = title_from_about_patterns(about)
    if title:
        return title, src

    title, src = title_from_header(lines, company)
    if title:
        return title, src

    return "", ""


def infer_workplace_type(lines: List[str], about: str) -> str:
    low = (about or "").lower()

    onsite_terms = [
        "fully on-site",
        "fully onsite",
        "fully on site",
        "100% presencial",
        "presencial",
        "office-based",
        "office based",
        "office first",
        "office-first",
        "on-site support",
        "onsite support",
    ]

    hybrid_terms = [
        "hybrid",
        "híbrido",
        "hibrido",
        "modelo híbrido",
        "modelo hibrido",
        "remote and on-site",
        "remote and onsite",
        "days in the office",
        "días en oficina",
        "dias en oficina",
        "1 día en oficina",
        "2 días en oficina",
        "3 días en oficina",
        "teletrabajo /",
    ]

    remote_terms = [
        "100% remoto",
        "100% teletrabajo",
        "fully remote",
        "full remote",
        "remote-first",
        "remote first",
        "remote role",
        "remote working",
        "work-from-home",
        "work from home",
        "home office friendly",
    ]

    if any(t in low for t in onsite_terms):
        return "On-site"

    if any(t in low for t in hybrid_terms):
        return "Hybrid"

    if any(t in low for t in remote_terms):
        return "Remote"

    # Do not trust generic header "Remote".
    return ""


def infer_employment_type(lines: List[str], about: str) -> str:
    low = (about or "").lower()

    found = []

    checks = [
        ("Full-time", [
            "full-time",
            "full time",
            "jornada completa",
            "contrato indefinido",
            "permanent contract",
            "permanent position",
        ]),
        ("Part-time", [
            "part-time",
            "part time",
            "media jornada",
        ]),
        ("Contract", [
            "contractor",
            "freelance",
            "b2b",
            "contract type: subcontracting",
            "subcontracting",
            "contrato mercantil",
        ]),
        ("Temporary", [
            "temporary",
            "temporal",
            "fixed-term",
            "fixed term",
            "duration: 12 months",
            "duration: 6 months",
            "6 meses",
            "12 meses",
        ]),
        ("Internship", [
            "internship",
            "prácticas",
            "practicas",
        ]),
    ]

    for label, terms in checks:
        if any(t in low for t in terms):
            found.append(label)

    return ", ".join(dict.fromkeys(found))


def extract_applicant_count(lines: List[str]) -> str:
    for line in lines[:180]:
        m = re.search(r"(over\s+)?(\d[\d,.]*)\s+(people clicked apply|applicants?)", line, flags=re.I)
        if m:
            return ((m.group(1) or "") + m.group(2)).strip()
    return ""



LEFT_PANEL_STOP_MARKERS = {
    "are these results helpful?",
    "your feedback helps us improve job recommendations.",
    "next",
    "about",
    "accessibility",
    "help center",
}
LEFT_PANEL_STATE_MARKERS = {
    "actively reviewing applicants",
    "viewed",
    "promoted",
    "easy apply",
    "be an early applicant",
    "applied",
    "company review time is typically 1 week",
}


def _is_left_panel_location(line: str) -> bool:
    l = (line or "").lower()
    return bool(re.search(r"\((remote|hybrid|on-site|onsite)\)", l)) or any(x in l for x in [
        "spain", "madrid", "barcelona", "lisbon", "portugal", "budapest", "hungary", "dublin", "ireland",
        "netherlands", "france", "amsterdam", "paris", "cork", "community of madrid", "greater madrid",
    ])


def _clean_card_key(value: str) -> str:
    value = (value or "").lower().replace("&", " and ")
    value = re.sub(r"[^a-z0-9áéíóúüñ]+", " ", value, flags=re.I)
    return re.sub(r"\s+", " ", value).strip()


def _card_signature(title: str, company: str, location: str = "") -> str:
    return _clean_card_key(f"{company}|{title}|{location}")


def parse_left_panel_cards(lines: List[str]) -> List[dict]:
    start = 0
    for i, line in enumerate(lines):
        if re.search(r"\b\d+\s+results\b", line.lower()):
            start = i + 1
            break
    cards = []
    i = start
    while i < len(lines) - 3:
        line = lines[i]
        lc = line.lower()
        if lc in LEFT_PANEL_STOP_MARKERS or lc.startswith("are you finding what"):
            break
        if line.endswith(" logo") and i + 3 < len(lines):
            title = lines[i + 1]
            company = lines[i + 2]
            location = lines[i + 3]
            if _is_left_panel_location(location):
                state_lines = []
                j = i + 4
                while j < len(lines):
                    nxt = lines[j]
                    nl = nxt.lower()
                    if nxt.endswith(" logo") or nl in LEFT_PANEL_STOP_MARKERS or nl.startswith("are you finding what"):
                        break
                    if nl in LEFT_PANEL_STATE_MARKERS or "applicants" in nl or "review time" in nl or "school alumni" in nl:
                        state_lines.append(nxt)
                    elif len(state_lines) >= 1 and len(nxt) <= 45:
                        state_lines.append(nxt)
                    j += 1
                workplace = ""
                m = re.search(r"\((Remote|Hybrid|On-site|Onsite)\)", location, flags=re.I)
                if m:
                    workplace = m.group(1).replace("Onsite", "On-site")
                cards.append({
                    "title": title,
                    "company": company,
                    "location": location,
                    "workplace_type": workplace,
                    "state_text": "; ".join(dict.fromkeys(state_lines)),
                    "signature": _card_signature(title, company, location),
                })
                i = max(j, i + 4)
                continue
        i += 1
    # dedupe while preserving order
    seen = set(); out = []
    for c in cards:
        sig = c.get("signature", "")
        if sig and sig not in seen:
            seen.add(sig); out.append(c)
    return out


def match_left_panel_card(lines: List[str], title: str, company: str, location: str) -> dict:
    cards = parse_left_panel_cards(lines)
    if not cards:
        return {}
    title_key = _clean_card_key(title)
    company_key = _clean_card_key(company)
    location_key = _clean_card_key(location)
    best = {}
    best_score = 0
    for c in cards:
        ct = _clean_card_key(c.get("title", ""))
        cc = _clean_card_key(c.get("company", ""))
        cl = _clean_card_key(c.get("location", ""))
        score = 0
        if title_key and (title_key == ct or title_key in ct or ct in title_key):
            score += 4
        if company_key and (company_key == cc or company_key in cc or cc in company_key):
            score += 4
        if location_key and (location_key == cl or location_key in cl or cl in location_key):
            score += 1
        if score > best_score:
            best = c; best_score = score
    return best if best_score >= 4 else {}


def left_panel_state_columns(card: dict) -> dict:
    state = card.get("state_text", "") if card else ""
    low_state = state.lower()
    return {
        "linkedin_card_state": state,
        "linkedin_applied": "yes" if "applied" in low_state and "easy apply" not in low_state else "no",
        "linkedin_viewed": "yes" if "viewed" in low_state else "no",
        "linkedin_easy_apply": "yes" if "easy apply" in low_state else "",
        "linkedin_promoted": "yes" if "promoted" in low_state else "",
        "linkedin_actively_reviewing": "yes" if "actively reviewing applicants" in low_state else "",
    }


def extract_easy_apply(lines: List[str]) -> str:
    # Raw Ctrl+A/C often includes LinkedIn chrome. Do not trust this field.
    return "unknown"


def extract_promoted(lines: List[str]) -> str:
    # Raw Ctrl+A/C often includes LinkedIn chrome. Do not trust this field.
    return "unknown"


def clean_hiring_name(name: str) -> str:
    name = re.sub(r"\s+profile photo$", "", name or "", flags=re.I)
    name = re.sub(r"\s+is verified$", "", name, flags=re.I)
    name = re.sub(r"\s+is hiring$", "", name, flags=re.I)
    name = re.sub(r"\b(1st|2nd|3rd)\b.*$", "", name, flags=re.I)
    name = re.sub(r"\s+", " ", name).strip(" ·-:;")
    return name


def looks_like_person_name(name: str) -> bool:
    if not name:
        return False
    low = name.lower()
    if any(x in low for x in [
        "about the job", "the team", "the work", "company alumni", "your network",
        "meet the hiring team", "people you can reach out to", "message", "connect",
        "show all", "hiring team", "job description", "responsibilities", "requirements",
        "profile photo",
    ]):
        return False
    parts = name.split()
    if not (1 <= len(parts) <= 5):
        return False
    # Initials like "Nicolás P." are acceptable.
    return bool(re.search(r"[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+", name))


def extract_hiring_team(lines: List[str]) -> Tuple[str, str, str, str]:
    section_starts = []
    for i, line in enumerate(lines):
        if re.fullmatch(r"(Meet the hiring team|People you can reach out to)", line, flags=re.I):
            section_starts.append(i)

    names = []
    degrees = []
    notes = []

    for start in section_starts:
        block = []
        for line in lines[start + 1:start + 45]:
            if re.search(r"^(About the job|About The Job|Job Description|Description|About the company)$", line, flags=re.I):
                break
            block.append(line)

        for idx, line in enumerate(block):
            degree = ""
            m = re.search(r"\b(1st|2nd|3rd)\b", line)
            if m:
                degree = m.group(1)

            raw_name = clean_hiring_name(line)

            if not degree:
                for nxt in block[idx + 1:idx + 4]:
                    m2 = re.search(r"\b(1st|2nd|3rd)\b", nxt)
                    if m2:
                        degree = m2.group(1)
                        break

            if degree == "1st":
                continue
            if degree not in {"2nd", "3rd"}:
                continue
            if not looks_like_person_name(raw_name):
                continue

            norm = raw_name.lower().replace(".", "").strip()
            existing_norms = [n.lower().replace(".", "").strip() for n in names]

            if norm in existing_norms:
                continue

            # Avoid keeping both "Nicolás" and "Nicolás P." / "Ignacio J." and full name.
            skip = False
            for existing in existing_norms:
                if norm.startswith(existing + " ") or existing.startswith(norm + " "):
                    # Prefer the longer/more complete name.
                    if len(norm) > len(existing):
                        idx_existing = existing_norms.index(existing)
                        names[idx_existing] = raw_name
                        degrees[idx_existing] = degree
                    skip = True
                    break

            if skip:
                continue

            names.append(raw_name)
            degrees.append(degree)

    if names:
        notes.append("hiring_team_url_not_available_from_raw_text")

    return "; ".join(names), "; ".join(degrees), "", "; ".join(notes)


def parse_one(record: dict) -> ParsedJob:
    raw_text = record.get("raw_text", "") or ""
    about = extract_about_job(raw_text)
    lines = normalize_lines(raw_text)

    notes = []

    if is_bad_panel_capture(raw_text, about, lines):
        notes.append("bad_panel_capture")
        return ParsedJob(
            sequence=int(record.get("sequence", 0) or 0),
            source_sequence=int(record.get("source_sequence", 0) or 0),
            page_number=int(record.get("page_number", 0) or 0),
            page_start=int(record.get("page_start", 0) or 0),
            viewport_index=int(record.get("viewport_index", 0) or 0),
            card_index=int(record.get("card_index", 0) or 0),
            current_job_id=str(record.get("current_job_id", "") or ""),
            url=str(record.get("url", "") or ""),
            raw_status=str(record.get("status", "") or ""),

            job_title="",
            job_title_source="",
            company="",
            location="",
            workplace_type="",
            employment_type="",
            applicant_count="",
            easy_apply="unknown",
            promoted="unknown",
            linkedin_card_state="",
            linkedin_applied="no",
            linkedin_viewed="no",
            linkedin_easy_apply="",
            linkedin_promoted="",
            linkedin_actively_reviewing="",

            hiring_team_names="",
            hiring_team_degrees="",
            hiring_team_profile_urls="",

            about_job_chars=len(about),
            raw_about_job=about,
            parser_notes=", ".join(dict.fromkeys(notes)),
        )

    # Prefer the selected job detail panel immediately before About the job.
    # The copied text often contains the left results list first; header-first parsing can
    # otherwise repeat the first visible card across multiple records.
    panel_title, panel_company, panel_location, panel_source = extract_right_panel_fields(lines)
    header_title, header_company, header_location, header_source = extract_header_fields(lines)

    company = panel_company or header_company or extract_company(lines, about)

    if panel_title:
        title, title_source = panel_title, panel_source
    elif header_title:
        title, title_source = header_title, header_source
    else:
        title, title_source = extract_title(lines, about, company)

    location = panel_location or header_location or extract_location(lines, about)
    workplace = infer_workplace_type(lines, about)
    employment = infer_employment_type(lines, about)
    applicants = extract_applicant_count(lines)
    h_names, h_degrees, h_urls, h_note = extract_hiring_team(lines)
    matched_card = match_left_panel_card(lines, title, company, location)
    card_state = left_panel_state_columns(matched_card)
    if matched_card:
        # Use the left-panel card as a safe fallback for workplace state when the right panel is missing it.
        if not workplace and matched_card.get("workplace_type"):
            workplace = matched_card.get("workplace_type", "")

    if not title:
        notes.append("title_not_found")
    elif is_bad_title(title):
        notes.append("weak_or_suspicious_title")

    if not company:
        notes.append("company_not_found")
    if not location:
        notes.append("location_not_found")
    if not workplace:
        notes.append("workplace_type_not_found")
    if not employment:
        notes.append("employment_type_not_found")
    if h_note:
        notes.append(h_note)

    # v13 safety: rows where selected detail metadata cannot be trusted must not reach Tracker_v2.
    # These are the rows that caused card/detail mixtures such as:
    #   left card: h&k IT Support, right-panel body: UST 3rd Line Support
    #   company: 3, location: Acronis
    #   company: Are these results helpful?, location: Laravel
    if title_source in {"header_first_card", "right_panel_fallback_anchor_relaxed"} or "fallback" in (title_source or "").lower():
        notes.append("panel_sync_unverified")
    if is_suspicious_company_or_location(company, location):
        notes.append("suspicious_parsed_company_location")
    if title and about:
        # If neither the selected title nor selected company appears anywhere in the job body,
        # treat it as unsafe unless it came from LinkedIn's reliable Save-title anchor.
        body_low = about.lower()
        title_core = re.sub(r"[^a-z0-9áéíóúüñ]+", " ", title.lower()).strip()
        company_core = re.sub(r"[^a-z0-9áéíóúüñ]+", " ", company.lower()).strip()
        title_tokens = [t for t in title_core.split() if len(t) >= 4][:4]
        title_hits = sum(1 for t in title_tokens if t in body_low)
        company_hit = company_core and len(company_core) >= 3 and company_core in re.sub(r"[^a-z0-9áéíóúüñ]+", " ", body_low)
        if not selected_detail_source_is_trusted(title_source) and title_hits == 0 and not company_hit:
            notes.append("bad_panel_mismatch")

    return ParsedJob(
        sequence=int(record.get("sequence", 0) or 0),
        source_sequence=int(record.get("source_sequence", 0) or 0),
        page_number=int(record.get("page_number", 0) or 0),
        page_start=int(record.get("page_start", 0) or 0),
        viewport_index=int(record.get("viewport_index", 0) or 0),
        card_index=int(record.get("card_index", 0) or 0),
        current_job_id=str(record.get("current_job_id", "") or ""),
        url=str(record.get("url", "") or ""),
        raw_status=str(record.get("status", "") or ""),

        job_title=title,
        job_title_source=title_source,
        company=company,
        location=location,
        workplace_type=workplace,
        employment_type=employment,
        applicant_count=applicants,
        easy_apply=card_state.get("linkedin_easy_apply") or extract_easy_apply(lines),
        promoted=card_state.get("linkedin_promoted") or extract_promoted(lines),
        linkedin_card_state=card_state.get("linkedin_card_state", ""),
        linkedin_applied=card_state.get("linkedin_applied", "no"),
        linkedin_viewed=card_state.get("linkedin_viewed", "no"),
        linkedin_easy_apply=card_state.get("linkedin_easy_apply", ""),
        linkedin_promoted=card_state.get("linkedin_promoted", ""),
        linkedin_actively_reviewing=card_state.get("linkedin_actively_reviewing", ""),

        hiring_team_names=h_names,
        hiring_team_degrees=h_degrees,
        hiring_team_profile_urls=h_urls,

        about_job_chars=len(about),
        raw_about_job=about,
        parser_notes=", ".join(dict.fromkeys(notes)),
    )


def read_jsonl(path: Path) -> List[dict]:
    records = []
    with path.open("r", encoding="utf-8") as f:
        for n, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"WARNING: line {n} JSON error: {e}")
    return records


def write_outputs(input_path: Path, parsed: List[ParsedJob]) -> Tuple[Path, Path]:
    stem = input_path.stem
    stem = stem.replace("linkedin_job_text_v20_", "")
    stem = stem.replace("linkedin_job_text_", "")

    csv_path = CAPTURE_OUTPUT_DIR / f"linkedin_jobs_parsed_v34_{stem}.csv"
    json_path = CAPTURE_OUTPUT_DIR / f"linkedin_jobs_parsed_v34_{stem}.json"

    fields = list(asdict(parsed[0]).keys()) if parsed else list(ParsedJob.__dataclass_fields__.keys())

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for job in parsed:
            writer.writerow(asdict(job))

    json_path.write_text(
        json.dumps([asdict(j) for j in parsed], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return csv_path, json_path


def main() -> int:
    print("LinkedIn raw text parser v34 right-panel + left-panel state")
    print("-----------------------------------------")
    print("Reads saved raw JSONL from v20/v34+. Does not open LinkedIn.")
    print("Outputs CSV + JSON only.")
    print("")

    if len(sys.argv) > 1:
        input_path = Path(sys.argv[1])
    else:
        input_path = find_latest_input_file()
        if not input_path:
            print(f"No input file found in {CAPTURE_OUTPUT_DIR} matching {DEFAULT_INPUT_GLOB}")
            return 2

    print(f"Input: {input_path}")
    records = read_jsonl(input_path)
    parsed = [parse_one(r) for r in records]

    bad_or_missing_titles = [j for j in parsed if not j.job_title or is_bad_title(j.job_title)]
    bad_panel_captures = [j for j in parsed if "bad_panel_capture" in j.parser_notes]

    print(f"Raw records read: {len(records)}")
    print(f"Parsed records: {len(parsed)}")
    print(f"Missing/bad title: {len(bad_or_missing_titles)}")
    print(f"Bad panel captures: {len(bad_panel_captures)}")
    print(f"Missing company: {sum(1 for j in parsed if not j.company)}")
    print(f"Missing about_job: {sum(1 for j in parsed if not j.raw_about_job)}")
    print(f"Hiring team visible: {sum(1 for j in parsed if j.hiring_team_names)}")

    csv_path, json_path = write_outputs(input_path, parsed)

    print("")
    print("Output files:")
    print(f"  CSV:  {csv_path.resolve()}")
    print(f"  JSON: {json_path.resolve()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
