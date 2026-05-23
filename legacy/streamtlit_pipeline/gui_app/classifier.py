from __future__ import annotations

import csv
import datetime as dt
import re
import shutil
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional


def norm(value: Any) -> str:
    return str(value or "").strip()


def low(value: Any) -> str:
    return norm(value).lower()


def has_any(text: str, terms: List[str]) -> bool:
    t = text.lower()
    return any(term.lower() in t for term in terms)


def compact_ws(text: str) -> str:
    return re.sub(r"\s+", " ", norm(text))


def all_text(row: Dict[str, str]) -> str:
    return " ".join([
        low(row.get("job_title")), low(row.get("company")), low(row.get("location")),
        low(row.get("workplace_type")), low(row.get("employment_type")), low(row.get("raw_about_job")),
        low(row.get("parser_notes")), low(row.get("job_title_source")),
    ])


def normalize_key(text: Any) -> str:
    """Normalize text for duplicate/previous-tracker matching."""
    t = low(text)
    t = t.replace("&", " and ")
    t = re.sub(r"[^a-z0-9áéíóúüñ]+", " ", t, flags=re.IGNORECASE)
    t = re.sub(r"\b(ltd|limited|sl|s l|sa|s a|gmbh|inc|corp|corporation|company|group|españa|spain|latam|iberica|ibérica)\b", " ", t)
    return compact_ws(t)


def normalize_title_key(text: Any) -> str:
    t = normalize_key(text)
    t = re.sub(r"\b(100 remote spain|100 remote|remote spain|remote|m f d|all genders|f m d|english speaking|spanish|junior|senior)\b", " ", t)
    t = t.replace("n0 n1", "n0n1")
    return compact_ws(t)


def token_set(text: Any) -> set[str]:
    return set(normalize_title_key(text).split())


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)



# User language policy for this workflow. Default allowed professional languages are
# Spanish and English, but this is configurable from Streamlit preferences.
LANGUAGE_TERM_GROUPS = {
    "english": ["english", "inglés", "ingles"],
    "spanish": ["spanish", "español", "espanol", "castellano"],
    "german": ["german", "deutsch", "alemán", "aleman"],
    "french": ["french", "français", "francais", "francés", "frances"],
    "chinese": ["chinese", "mandarin", "cantonese", "chino"],
    "danish": ["danish", "danés", "danes"],
    "dutch": ["dutch", "nederlands"],
    "italian": ["italian", "italiano"],
    "portuguese": ["portuguese", "português", "portugues"],
    "polish": ["polish", "polaco"],
    "swedish": ["swedish", "sueco"],
    "norwegian": ["norwegian", "noruego"],
    "finnish": ["finnish", "finlandés", "finlandes"],
}

def allowed_language_keys(prefs: Optional[Dict[str, Any]] = None) -> set[str]:
    raw = (prefs or {}).get("allowed_languages", ["english", "spanish"])
    if not isinstance(raw, list):
        raw = ["english", "spanish"]
    allowed = {low(x) for x in raw if low(x) in LANGUAGE_TERM_GROUPS}
    return allowed or {"english", "spanish"}

def disallowed_language_terms(prefs: Optional[Dict[str, Any]] = None) -> List[str]:
    allowed = allowed_language_keys(prefs)
    terms: List[str] = []
    for key, values in LANGUAGE_TERM_GROUPS.items():
        if key not in allowed:
            terms.extend(values)
    return terms

# Backward-compatible default list used by older helper calls.
OTHER_LANGUAGE_TERMS = disallowed_language_terms({"allowed_languages": ["english", "spanish"]})

LANGUAGE_REQUIRED_TERMS = [
    "mandatory", "required", "must", "must-have", "native", "fluent", "speaker", "speaking",
    "bilingual", "c1", "c2", "b2", "advanced", "proficiency", "proficient", "excellent",
    "very good", "good level", "level of", "at least", "minimum", "nivel", "nativo",
]

LANGUAGE_PLUS_TERMS = [
    "plus", "nice to have", "bonus", "preferred", "advantage", "desirable", "valorable",
    "is a plus", "are a plus", "would be a plus", "additional languages", "other european languages",
]


def forbidden_language_mandatory(row: Dict[str, str], prefs: Optional[Dict[str, Any]] = None) -> bool:
    """Return True when a language outside the allowed list appears mandatory.

    Do not reject when another language is only a plus/nice-to-have.
    """
    title = low(row.get("job_title"))
    company = low(row.get("company"))
    about = low(row.get("raw_about_job"))
    text = f"{title}\n{company}\n{about}"

    disallowed_terms = disallowed_language_terms(prefs)
    allowed = allowed_language_keys(prefs)

    # Language-specific titles are normally hard requirements.
    title_hard_patterns = list(disallowed_terms)
    if "german" not in allowed:
        title_hard_patterns.extend(["m/w/d", "all genders"])
    for lang_key, terms in LANGUAGE_TERM_GROUPS.items():
        if lang_key in allowed:
            continue
        for term in terms:
            title_hard_patterns.extend([f"{term} speaker", f"{term} speaking", f"english + {term}", f"english/{term}", f"english & {term}"])
    title_hard_patterns.extend(["ingénieur support", "ingenieur support"])
    if has_any(title, title_hard_patterns):
        return True

    # Split by lines/sentences to avoid rejecting "German is a plus".
    chunks = re.split(r"[\n\r.;•]+", text)
    for chunk in chunks:
        c = compact_ws(chunk).lower()
        if not c:
            continue
        if not any(lang in c for lang in disallowed_terms):
            continue

        # Safe examples: "German is a plus", "French/Dutch/German is a plus", "additional languages are a plus".
        plus_only = any(term in c for term in LANGUAGE_PLUS_TERMS) and not any(term in c for term in [
            "mandatory", "required", "must", "native", "fluent", "bilingual", "speaker", "speaking", "c1", "c2", "b2", "at least"
        ])
        if plus_only:
            continue

        # Hard patterns where another language is a real requirement.
        if any(term in c for term in LANGUAGE_REQUIRED_TERMS):
            return True
        disallowed_re = "|".join(re.escape(x) for x in disallowed_terms)
        if disallowed_re and re.search(rf"english\s*(\+|/|&|and)\s*({disallowed_re})", c):
            return True
        if disallowed_re and re.search(rf"({disallowed_re})\s*(\+|/|&|and)\s*english", c):
            return True

    return False


def is_spain_compatible(row: Dict[str, str]) -> bool:
    text = all_text(row)
    loc = low(row.get("location"))
    return has_any(text, [
        "remote from spain", "remote within spain", "100% remote within spain", "100% remoto", "teletrabajo",
        "modalidad:remoto", "modalidad**: remoto", "spain", "madrid", "barcelona", "valencia", "zaragoza",
        "pamplona", "andalusia", "galicia", "vigo", "remote anywhere in europe", "remotely in europe",
        "remote from europe", "remote within europe", "remote - europe", "european union",
    ]) or "spain" in loc


def clear_remote_from_spain_or_eu(row: Dict[str, str]) -> bool:
    text = all_text(row)
    loc = low(row.get("location"))
    return has_any(text, [
        "remote from spain", "remote within spain", "100% remote within spain", "100% remote position is open to candidates located in spain",
        "100% remoto", "teletrabajo", "modalidad:remoto", "modalidad**: remoto", "remote based in spain",
        "remote anywhere in europe", "remotely in europe", "remote from europe", "remote within europe", "remote - europe",
        "located in spain", "based in spain", "from wherever you want in spain",
    ])


def location_is_spain(row: Dict[str, str]) -> bool:
    loc = low(row.get("location"))
    return has_any(loc, ["spain", "madrid", "barcelona", "valencia", "zaragoza", "pamplona", "galicia", "vigo", "andalusia", "murcia"])


def outside_spain_location(row: Dict[str, str]) -> bool:
    loc = low(row.get("location"))
    if not loc or location_is_spain(row):
        return False
    return True


def outside_spain_non_remote(row: Dict[str, str]) -> bool:
    loc = low(row.get("location"))
    workplace = low(row.get("workplace_type"))
    text = all_text(row)
    spain_markers = ["spain", "madrid", "barcelona", "valencia", "zaragoza", "pamplona", "galicia", "vigo", "andalusia"]
    if any(x in loc for x in spain_markers):
        return False
    if workplace in {"on-site", "onsite", "hybrid"}:
        return True
    if has_any(text, ["based at our office in lisbon", "based at our office in dublin", "based at our office in paris", "work from our paris office", "within 50 km of our dublin office", "fully onsite position"]):
        return True
    return False


# v21 location policy: Rafael is based in Vigo, Spain.
# Remote roles are not affected by distance. Hybrid/onsite roles must be within ~30 km of Vigo.
VIGO_COMMUTABLE_TERMS = [
    "vigo", "pontevedra", "porriño", "o porriño", "porrino", "redondela", "mos",
    "nigrán", "nigran", "baiona", "cangas", "moaña", "moana", "tui",
    "salceda", "gondomar", "soutomaior", "arcade", "chapela"
]

SPAIN_FAR_FROM_VIGO_TERMS = [
    "madrid", "barcelona", "valencia", "zaragoza", "sevilla", "seville", "bilbao",
    "pamplona", "murcia", "alicante", "malaga", "málaga", "granada", "cordoba",
    "córdoba", "valladolid", "salamanca", "a coruña", "coruña", "la coruña",
    "santiago", "santiago de compostela", "ourense", "orense", "lugo", "asturias",
    "oviedo", "gijón", "gijon", "santander", "toledo", "palma", "mallorca",
    "canary", "canarias", "tenerife", "las palmas", "andalusia", "andalucía", "andalucia"
]


def is_remote_role(row: Dict[str, str]) -> bool:
    workplace = low(row.get("workplace_type"))
    text = all_text(row)
    title = low(row.get("job_title"))
    if workplace == "remote":
        return True
    return has_any(text + " " + title, [
        "100% remote", "100% remoto", "fully remote", "full remote", "remote from spain",
        "remote within spain", "remote position", "remote role", "work remotely", "teletrabajo",
        "modalidad:remoto", "modalidad remoto", "remote anywhere", "remotely in europe",
        "remote from europe", "remote within europe", "remote-based", "remote based"
    ]) and not has_any(text, [
        "hybrid", "híbrido", "hibrido", "on-site", "onsite", "on site", "presencial",
        "2 days at the office", "3 days onsite", "3 days on-site"
    ])


def hybrid_or_onsite_role(row: Dict[str, str]) -> bool:
    workplace = low(row.get("workplace_type"))
    text = all_text(row)
    if workplace in {"on-site", "onsite", "hybrid"}:
        return True
    return has_any(text, [
        "hybrid", "híbrido", "hibrido", "on-site", "onsite", "on site", "presencial",
        "office-based", "based at our office", "work from our office", "3 days onsite",
        "2 days onsite", "2 days at the office", "3 days at the office", "visits per week",
        "asistencia", "días presencial", "dias presencial", "presencial /"
    ])





# v23 classifier cleanup helpers. These keep realistic remote IT support work visible,
# but prevent weak/stretch/specialist roles from being promoted as B candidates.
def workplace_missing(row: Dict[str, str]) -> bool:
    return not bool(low(row.get("workplace_type")))


def customer_success_or_happiness(row: Dict[str, str]) -> bool:
    title = low(row.get("job_title"))
    text = all_text(row)
    return has_any(title, [
        "happiness engineer", "customer success", "customer support & success",
        "product success", "customer experience", "customer engagement", "onboarding specialist"
    ]) or (has_any(title, ["customer support"]) and has_any(text, ["customer success", "product adoption", "retention", "customer journey"]))


def qa_or_test_role(row: Dict[str, str]) -> bool:
    title = low(row.get("job_title"))
    text = all_text(row)
    return has_any(title, [
        "quality assurance", "qa engineer", "qa analyst", "test automation", "testing engineer",
        "software tester", "qa support engineer"
    ]) or (has_any(title, ["support engineer"]) and has_any(text, ["manual and automated testing", "execution of test requirements", "qa roles", "testing plans"]))


def cloud_stretch_role(row: Dict[str, str]) -> bool:
    title = low(row.get("job_title"))
    text = all_text(row)
    return has_any(title, [
        "cloud engineer", "cloud operations engineer", "sre", "site reliability",
        "api platform engineer", "kubernetes", "openshift", "observability",
        "power platform engineer", "devops", "sysops"
    ]) or has_any(text, [
        "kubernetes", "openshift", "terraform", "helm", "ansible", "ci/cd",
        "api gateway", "kong", "konnect", "sre", "site reliability",
        "devsecops", "landing zones", "enterprise-scale", "cloud contact centre",
        "genesys cloud cx", "dynatrace", "observability", "red hat"
    ])


def industrial_or_hardware_product_support(row: Dict[str, str]) -> bool:
    title = low(row.get("job_title"))
    company = low(row.get("company"))
    text = all_text(row)
    if company in {"sineng electric"}:
        return True
    return has_any(text, [
        "electrical engineering", "power electronics", "energy storage", "battery energy storage",
        "bess", "power conversion system", "technical proposals", "bids and tenders",
        "solar", "inverter", "construction materials", "onsite construction", "hvac", "field service engineer"
    ]) and not has_any(text, ["microsoft 365", "active directory", "servicenow", "itil", "windows", "application support", "erp", "saas"])


def niche_security_compatibility_role(row: Dict[str, str]) -> bool:
    title = low(row.get("job_title"))
    text = all_text(row)
    return has_any(title, ["av whitelisting", "endpoint security compatibility"]) or has_any(text, [
        "av vendor submissions", "whitelisting processes", "false positives",
        "antivirus and edr detections", "windows smartscreen reputation", "code signing",
        "software trust and reputation"
    ])


def remote_location_soft_cap(row: Dict[str, str]) -> bool:
    # Remote is allowed by the Vigo rule, but broad remote roles attached to a non-Spain
    # location or a far-Spain metro location should not be promoted as B without human review.
    if not is_remote_role(row):
        return False
    loc_text = f"{low(row.get('location'))} {all_text(row)}"
    if outside_spain_location(row) and not clear_remote_from_spain_or_eu(row):
        return True
    if has_location_phrase(loc_text, SPAIN_FAR_FROM_VIGO_TERMS) and not has_location_phrase(loc_text, VIGO_COMMUTABLE_TERMS) and not clear_remote_from_spain_or_eu(row):
        return True
    return False



def has_location_phrase(text: str, terms: List[str]) -> bool:
    text_l = text.lower()
    for term in terms:
        pattern = r"(?<![a-záéíóúüñ])" + re.escape(term.lower()) + r"(?![a-záéíóúüñ])"
        if re.search(pattern, text_l):
            return True
    return False

def hybrid_onsite_over_30km_from_vigo(row: Dict[str, str]) -> bool:
    """Hard discard for hybrid/onsite roles not realistically commutable from Vigo."""
    if is_remote_role(row):
        return False
    if not hybrid_or_onsite_role(row):
        return False
    loc = low(row.get("location"))
    text = all_text(row)
    combined = f"{loc} {text}"
    if has_location_phrase(combined, VIGO_COMMUTABLE_TERMS):
        return False
    # Any confirmed hybrid/onsite outside Spain is out.
    if outside_spain_location(row):
        return True
    # Confirmed Spanish locations outside the Vigo/Pontevedra commute area are out.
    if has_location_phrase(combined, SPAIN_FAR_FROM_VIGO_TERMS):
        return True
    # Generic Spain + hybrid/onsite with no Vigo/Pontevedra marker is not safely commutable.
    if "spain" in loc or "españa" in loc or location_is_spain(row):
        return True
    return False


def residence_or_visa_restriction(row: Dict[str, str]) -> bool:
    text = all_text(row)
    return has_any(text, [
        "must permanently reside in ireland", "must reside in ireland", "qualified candidates must permanently reside",
        "must be based in ireland", "must be located in ireland", "must live in ireland",
        "must be based in the uk", "must be based in united kingdom", "uk only",
        "must be based in the united states", "us only", "u.s. only", "remote in us",
        "visa support: not provided", "not able to offer visa support", "not eligible for immigration sponsorship"
    ]) and not location_is_spain(row)


def role_family(row: Dict[str, str]) -> str:
    title = low(row.get("job_title"))
    about = low(row.get("raw_about_job"))
    combined = f"{title} {about}"

    if has_any(combined, ["microsoft 365", "m365", "entra", "azure ad", "active directory", "intune", "identity", "okta", "jamf", "digital workplace"]):
        return "Microsoft 365 / Identity"
    if has_any(combined, ["compute infrastructure", "infrastructure", "windows server", "system administrator", "systems administrator", "sysadmin", "enterprise it services", "vmware", "endpoint", "mdm", "data center", "datacenter"]):
        return "IT Ops / Infrastructure"
    if has_any(combined, ["application support", "technical support", "product support", "saas", "api", "integration", "erp", "functional analyst", "support analyst", "customer support engineer", "n2 support", "software support", "premium support"]):
        return "Application / SaaS Support"
    if has_any(combined, ["service desk", "it support", "support technician", "n0", "n1", "helpdesk", "desktop support", "end user", "desk side"]):
        return "IT Support / Service Desk"
    if has_any(combined, ["cloud operations", "cloud ops", "azure", "aws", "monitoring", "site reliability", "sre"]):
        return "Cloud Operations"
    return "Other"


def recommended_resume(family: str, row: Dict[str, str]) -> str:
    text = all_text(row)
    if has_any(text, ["erp", "sap", "industrial", "manufacturing", "mes", "it/ot", "ot engineer"]):
        return "Application Support / IT Ops Industrial"
    if family in {"IT Ops / Infrastructure", "Cloud Operations", "Microsoft 365 / Identity"}:
        return "IT Operations / Infrastructure"
    if family == "Application / SaaS Support":
        return "Application Support / SaaS Support"
    if family == "IT Support / Service Desk":
        return "IT Support / Service Desk"
    return "Review manually"


def extract_red_flags(row: Dict[str, str], prefs: Dict[str, Any]) -> Tuple[List[str], List[str], List[str]]:
    title = low(row.get("job_title"))
    company = low(row.get("company"))
    location = low(row.get("location"))
    workplace = low(row.get("workplace_type"))
    employment = low(row.get("employment_type"))
    about = low(row.get("raw_about_job"))
    notes = low(row.get("parser_notes"))
    source = low(row.get("job_title_source"))
    text = all_text(row)

    # major = deterministic discard
    # minor = risk but analyzable
    # review = needs manual validation, not necessarily a bad fit
    major: List[str] = []
    minor: List[str] = []
    review: List[str] = []

    if "bad_panel_capture" in notes or not norm(row.get("job_title")) or not norm(row.get("company")):
        major.append("bad parser/capture")
        review.append("bad parser/capture")
    if any(x in notes for x in ["bad_panel_mismatch", "panel_sync_unverified", "suspicious_parsed_company_location"]):
        major.append("bad parser/capture mismatch")
        review.append("manual parser review")

    # Location / authorization hard guards.
    if has_any(text, [
        "mainland-usa", "mainland usa", "united states only", "u.s. only", "us only", "remote in us",
        "remote - us", "remote within the us", "remote, us", "this role is located in washington", "washington, d.c.",
        "washington d.c.", "e-verify", "based in the united states", "remote in usa", "remote within usa"
    ]):
        major.append("US-only / legal eligibility risk")
    if re.search(r"\b(indianapolis|cincinnati|oh| in,|tx|ca|ny|wa|fl|united states)\b", location) and not has_any(location, ["spain", "madrid", "barcelona"]):
        major.append("non-EU/US location risk")
    if residence_or_visa_restriction(row):
        major.append("residence / visa restriction")
    if hybrid_onsite_over_30km_from_vigo(row):
        major.append("hybrid/onsite >30 km from Vigo")
    elif outside_spain_non_remote(row):
        major.append("onsite/hybrid outside Spain")

    # v23: if the workplace type is missing, do not assume it is remote.
    # Far Spain / non-Spain jobs with no explicit remote wording should not enter the tracker.
    if not is_remote_role(row):
        combined_location_text = f"{location} {text}"
        if outside_spain_location(row):
            major.append("non-Spain location without confirmed remote")
        elif location_is_spain(row) and has_location_phrase(combined_location_text, SPAIN_FAR_FROM_VIGO_TERMS) and not has_location_phrase(combined_location_text, VIGO_COMMUTABLE_TERMS):
            major.append("Spain location >30 km from Vigo without confirmed remote")

    # Schedule guards. These are NOT deterministic hard discards.
    # A night shift in another timezone can be compatible with Spanish daytime,
    # and during an urgent search Rafael may accept a worse schedule temporarily.
    # Keep these rows reviewable, lower the score, and flag them clearly.
    if has_any(text, ["night shift", "overnight", "10:00 pm", "10 pm", "late shift", "ends at 2 am"]):
        minor.append("night shift / timezone check")
        review.append("schedule compatibility check")
    if has_any(text, ["one weekend day", "tuesday–saturday", "tuesday-saturday", "sunday–thursday", "sunday-thursday", "weekend support", "evenings/weekends", "including evenings/weekends"]):
        minor.append("weekend work / schedule risk")
        review.append("schedule compatibility check")
    elif has_any(text, ["weekend", "saturday", "sunday"]):
        minor.append("weekend check")
        review.append("schedule compatibility check")
    if has_any(text, ["on-call", "on call", "24/7", "24x7", "24 x 7", "rotational support", "out of hours", "guardias", "guardia", "after hours coverage", "on-call duty", "24x7x365"]):
        minor.append("on-call / 24x7 risk")
        review.append("schedule compatibility check")

    # Language hard guard. By default Rafael applies/interviews only in Spanish or English,
    # but the allowed language list can be changed in Streamlit preferences.
    if prefs.get("avoid_german_french_required", True) and forbidden_language_mandatory(row, prefs):
        allowed_label = "/".join(sorted(allowed_language_keys(prefs)))
        major.append(f"language outside allowed list mandatory ({allowed_label})")

    # v23 specialist/false-positive guards.
    if qa_or_test_role(row):
        major.append("QA/testing role outside current target")
    if industrial_or_hardware_product_support(row):
        major.append("industrial/electrical product support, not IT/software support")
    if customer_success_or_happiness(row):
        minor.append("customer-success / product support risk")
        review.append("role-fit check")
    if cloud_stretch_role(row):
        minor.append("cloud/platform specialist stretch")
        review.append("technical-depth check")
    if niche_security_compatibility_role(row):
        minor.append("niche endpoint security compatibility role")
        review.append("technical-depth check")
    if workplace_missing(row) and location_is_spain(row) and not clear_remote_from_spain_or_eu(row):
        review.append("remote status check")

    # Role mismatch hard guards for the current urgent job search.
    # v23: be stricter with titles that superficially contain business/automation/support words
    # but are not defendable from Rafael's current CV or are outside IT Support / IT Ops.
    unrelated_title_hard = [
        "compensación y beneficios", "compensacion y beneficios", "compensation and benefits",
        "producto fresco", "alimentación", "alimentacion", "food", "retail team manager",
        "team manager producto", "technical support engineer – construction", "technical support engineer - construction",
        "construction", "jefe de proyectos", "project manager", "technical project manager",
        "ai automation engineer", "automation engineer", "automation & control engineer",
        "analista funcional de producto", "product analyst", "product owner", "product manager",
        "qa engineer", "test automation engineer", "quality assurance engineer", "quality assurance",
        "data science engineer", "ai systems engineer", "ai specialist", "ai trainer",
        "salesforce developer", "desarrollador", "developer", "coding specialist",
        "operations associate", "payroll consultant", "sap spanish-payroll consultant", "senior sap",
        "principal customer success"
    ]
    if has_any(title, unrelated_title_hard):
        # Exceptions: keep explicitly support/operations infrastructure roles unless the hard phrase is clearly unrelated.
        non_exception_terms = [
            "compensación y beneficios", "compensacion y beneficios", "compensation and benefits",
            "producto fresco", "alimentación", "alimentacion", "construction",
            "ai automation engineer", "automation & control engineer", "analista funcional de producto",
            "test automation engineer", "qa engineer", "quality assurance", "salesforce developer", "payroll consultant"
        ]
        if has_any(title, non_exception_terms) or not has_any(title, ["support", "soporte", "administrator", "administrador", "sysops", "systems operations"]):
            major.append("role too far from current CV")
    if has_any(title, ["power automate", "copilot", "ai engineer", "data science", "salesforce developer"]):
        major.append("role too far from current CV")

    # Call centre / customer support guards.
    if has_any(text, ["call centre", "call center", "inbound calls", "high-volume customer service", "high volume customer service", "bpo", "contact center", "7.5 hours of talk/chat", "contact center telephony"]):
        minor.append("call-centre / phone-heavy role")
    elif has_any(text, ["phone support", "phone, email", "calls, chats", "calls/chats", "phone and email"]):
        minor.append("phone-heavy check")
    if has_any(title, ["customer support specialist", "customer service", "customer engagement", "commercial specialist", "onboarding specialist"]):
        minor.append("customer-success / non-IT support risk")

    # Extra hard guards for roles that were incorrectly promoted in v4.
    if has_any(title, [
        "qa engineer", "principal game designer", "game designer", "ai systems engineer", "ai specialist",
        "customer support from greece", "business analyst (technical regulatory reporting)", "technical business analyst",
        "salesforce developer", "power automate", "desarrollador/a power automate", "coding specialist",
        "data science engineer", "junior data science", "operations associate - data", "senior sap spanish-payroll",
        "sap spanish-payroll", "sap payroll", "principal customer success", "field service engineer"
    ]):
        major.append("role too far from current CV")

    if company in {"quantivos", "rec_mrc", "alphanumeric systems"}:
        major.append("customer-support / language-risk role")

    # Known false-positive companies/roles from the 250-job audit.
    if company in {"serveo"} and has_any(title, ["compensación", "compensacion", "beneficios", "benefits"]):
        major.append("non-IT business/HR role")
    if company in {"leadtech group"} and has_any(title, ["ai automation engineer", "automation engineer"]):
        major.append("role too far from current CV")
    if company == "ashby" and has_any(title, ["product support specialist"]):
        minor.append("weekend work / schedule risk")
        review.append("schedule compatibility check")

    if has_any(title, ["expression of interest", "talent network", "join us at", "open application"]):
        minor.append("non-specific talent pool role")
        review.append("role specificity check")

    # Outside-Spain roles must be explicitly remote-from-Spain/EU to survive as A/B.
    if outside_spain_location(row) and not clear_remote_from_spain_or_eu(row):
        minor.append("non-Spain location check")

    # Stability/stress checks. Avoid false positives such as "outsourcing contracts" in the description.
    employment_text = employment
    about_for_contract = about
    if has_any(employment_text, ["temporary", "freelance", "fixed term", "contract", "contractor", "internship"]):
        minor.append("contract/stability check")
    elif has_any(about_for_contract, ["temporary replacement", "fixed-term", "fixed term", "freelance", "gig project"]):
        minor.append("contract/stability check")
    if has_any(text, ["startup", "fast-paced", "wear many hats", "high-volume", "high volume", "ambiguity", "no 9 to 5 mentality", "hyper-growth"]):
        minor.append("pace/stress risk")

    # Parser/metadata checks. These only require manual review if row otherwise survives.
    if "weak_or_suspicious_title" in notes or "fallback" in source or "panel_sync_unverified" in notes:
        review.append("manual parser review")
    if "workplace_type_not_found" in notes:
        review.append("remote status check")
    if "employment_type_not_found" in notes:
        review.append("employment type check")
    if "|" in norm(row.get("location")) or company in {"save", "next", "message", "3", "are these results helpful?"}:
        review.append("suspicious parsed company/location")
        major.append("bad parser/capture mismatch")
    if low(row.get("location")) in {"acronis", "laravel", "ninjaone", "ust", "board", "jobgether"}:
        review.append("suspicious parsed company/location")
        major.append("bad parser/capture mismatch")
    # Commerce is a real company name in this batch; do not auto-flag as suspicious.

    major = list(dict.fromkeys(major))
    minor = list(dict.fromkeys(minor))
    review = list(dict.fromkeys(review))
    return major, minor, review


def fit_score(row: Dict[str, str], family: str, major: List[str], minor: List[str], review: List[str], prefs: Dict[str, Any]) -> int:
    score = 40
    title = low(row.get("job_title"))
    text = all_text(row)

    if family == "IT Support / Service Desk":
        score += 24
    elif family in ["IT Ops / Infrastructure", "Microsoft 365 / Identity"]:
        score += 22
    elif family == "Application / SaaS Support":
        score += 18
    elif family == "Cloud Operations":
        score += 12

    if has_any(text, ["microsoft 365", "m365", "entra", "azure ad", "active directory", "intune", "servicenow", "service now", "itil", "incident", "sla", "documentation", "knowledge base", "windows server", "vmware", "okta", "jamf", "endpoint", "ticketing", "jira", "confluence"]):
        score += 15
    if has_any(text, ["100% remote within spain", "remote from spain", "remote within spain", "100% remoto", "teletrabajo", "modalidad:remoto", "spain"]):
        score += 12
    elif "remote" in text:
        score += 4
    if has_any(text, ["business hours", "monday to friday", "40 horas", "contrato indefinido", "permanent", "full-time"]):
        score += 4
    if has_any(text, ["junior", "n0", "n1", "service desk", "support technician"]):
        score += 4
    if has_any(text, ["sql", "api", "logs", "root cause", "troubleshoot", "troubleshooting", "sso", "mfa"]):
        score += 4

    # Strong stretch penalties.
    if has_any(text, ["kubernetes", "terraform", "devsecops", "machine learning", "deep learning", "senior devops", "coding specialist", "salesforce developer", "power automate", "copilot studio", "game designer", "qa engineer", "ai systems engineer"]):
        score -= 24
    if outside_spain_location(row) and not clear_remote_from_spain_or_eu(row):
        score -= 12
    if has_any(title, ["customer support specialist", "customer service", "onboarding", "customer success", "operations associate"]):
        score -= 12
    if customer_success_or_happiness(row):
        score -= 18
    if cloud_stretch_role(row):
        score -= 10
    if remote_location_soft_cap(row):
        score -= 6
    if niche_security_compatibility_role(row):
        score -= 12

    score -= 45 * len(major)
    score -= 7 * len(minor)
    # Review items are not a quality penalty by themselves; only a small uncertainty penalty.
    score -= 2 * len(review)
    return max(0, min(100, score))


def decision_from(row: Dict[str, str], family: str, score: int, major: List[str], minor: List[str], review: List[str]) -> Tuple[str, str, str]:
    if major:
        return "D", "Discard", "Major red flag: " + "; ".join(major)

    title = low(row.get("job_title"))
    text = all_text(row)

    # A is intentionally narrow: realistic, aligned, and no major schedule/location/language issue.
    strong_a_markers = has_any(text, [
        "itil", "service now", "servicenow", "microsoft 365", "active directory", "entra", "vmware", "windows server",
        "compute infrastructure", "100% remote within spain", "remote from spain", "modalidad:remoto", "erp", "n2 support",
        "support technician", "it support n0", "administración de sistemas", "microsoft security", "identity engineer"
    ])
    strong_a_title = has_any(title, [
        "it support n0", "support technician", "it service delivery analyst", "compute infrastructure service owner",
        "administración de sistemas", "systems administrator", "system administrator", "microsoft security", "identity engineer",
        "agente de soporte erp", "técnico de sistemas azure"
    ])
    good_family = family in {"IT Support / Service Desk", "IT Ops / Infrastructure", "Microsoft 365 / Identity", "Application / SaaS Support"}

    # v23: remote roles are not distance-discarded. Hybrid/onsite and unknown non-remote distance are handled as major red flags.
    # Non-Spain remote/unclear rows should stay reviewable if technically relevant, not be hidden.
    if outside_spain_location(row) and not clear_remote_from_spain_or_eu(row) and is_remote_role(row):
        if score >= 52 and good_family:
            return "C", "Low", "Remote non-Spain location; review legal/timezone fit before applying."

    if has_any(title, ["expression of interest", "talent network", "join us at", "open application"]):
        return "C", "Low", "Non-specific role/talent pool; keep only as backup."

    # v23 caps: these roles may still be worth a manual look, but should not be B/A.
    if customer_success_or_happiness(row):
        if score >= 35 and good_family:
            return "C", "Low", "Customer-success/product-support leaning; backup only."
        return "D", "Discard", "Customer-success/product-support role too far from current priority."

    if remote_location_soft_cap(row):
        if score >= 42 and good_family:
            return "C", "Low", "Remote location needs manual legal/timezone/Spain eligibility check."
        return "D", "Discard", "Remote/location fit too unclear for current priority."

    if niche_security_compatibility_role(row):
        if score >= 38 and good_family:
            return "C", "Low", "Niche endpoint/security compatibility role; backup only after manual technical check."
        return "D", "Discard", "Niche endpoint/security role too far from current priority."

    if workplace_missing(row) and location_is_spain(row) and not clear_remote_from_spain_or_eu(row):
        if score >= 42 and good_family:
            return "C", "Low", "Spain role but remote status is not explicit; verify before applying."

    if cloud_stretch_role(row):
        if score >= 38 and good_family:
            return "C", "Low", "Cloud/platform/SRE specialist stretch; backup only after manual technical check."
        return "D", "Discard", "Cloud/platform specialist role too far from current evidence."

    schedule_risk = any("schedule" in x or "night shift" in x or "weekend" in x or "on-call" in x or "24x7" in x for x in (minor + review))
    if schedule_risk and not (score >= 90 and strong_a_title and strong_a_markers):
        if score >= 45 and good_family:
            return "C", "Low", "Schedule risk; review only if pipeline is weak or timezone is compatible."
        return "C", "Low", "Schedule risk plus weak fit; keep as manual backup, not hard discard."

    if score >= 82 and good_family and strong_a_markers and strong_a_title and len(minor) <= 1:
        return "A", "High", "Strong realistic fit; apply after checking URL."
    if score >= 72 and good_family and len(minor) <= 2:
        return "B", "Medium", "Good fit if manual check confirms remote/schedule."
    if score >= 50 and good_family:
        return "C", "Low", "Backup only or apply if very low effort."
    if is_remote_role(row) and good_family and score >= 42:
        return "C", "Low", "Remote but weak/stretch fit; keep for manual review instead of hiding."
    return "D", "Discard", "Weak fit for current priority."



def yes_no(value: Any) -> str:
    v = low(value)
    if v in {"yes", "true", "1", "y", "applied", "viewed"}:
        return "yes"
    if v in {"no", "false", "0", "n", "unknown", ""}:
        return "no" if v in {"no", "false", "0", "n"} else ""
    return "yes" if any(x in v for x in ["yes", "true", "applied", "viewed"]) else ""


def detect_linkedin_state(row: Dict[str, str]) -> Dict[str, str]:
    """Best-effort LinkedIn visible state detection.

    v11 supports parser columns if present. Older parser files usually only have
    easy_apply/promoted as unknown, so applied/viewed may be blank until the parser
    is upgraded to preserve card state from the raw LinkedIn text.
    """
    card_state = norm(row.get("linkedin_card_state") or row.get("card_state") or row.get("linkedin_state"))
    text = " ".join([
        low(card_state), low(row.get("linkedin_applied")), low(row.get("linkedin_viewed")),
        low(row.get("easy_apply")), low(row.get("promoted")), low(row.get("linkedin_easy_apply")),
        low(row.get("linkedin_promoted")), low(row.get("linkedin_actively_reviewing")),
    ])
    applied = "yes" if has_any(text, ["applied", "already applied"]) or yes_no(row.get("linkedin_applied")) == "yes" else "no"
    viewed = "yes" if has_any(text, ["viewed"]) or yes_no(row.get("linkedin_viewed")) == "yes" else "no"
    easy_apply_raw = low(row.get("linkedin_easy_apply") or row.get("easy_apply"))
    easy_apply = "yes" if "easy apply" in text or easy_apply_raw in {"yes", "true", "1"} else ("no" if easy_apply_raw in {"no", "false", "0"} else "")
    promoted_raw = low(row.get("linkedin_promoted") or row.get("promoted"))
    promoted = "yes" if "promoted" in text or promoted_raw in {"yes", "true", "1"} else ("no" if promoted_raw in {"no", "false", "0"} else "")
    actively = "yes" if "actively reviewing" in text or yes_no(row.get("linkedin_actively_reviewing")) == "yes" else ""
    states = []
    if applied == "yes": states.append("Applied")
    if viewed == "yes": states.append("Viewed")
    if promoted == "yes": states.append("Promoted")
    if easy_apply == "yes": states.append("Easy Apply")
    if actively == "yes": states.append("Actively reviewing applicants")
    if not states and card_state:
        states.append(card_state)
    return {
        "linkedin_card_state": "; ".join(dict.fromkeys(states)),
        "linkedin_applied": applied,
        "linkedin_viewed": viewed,
        "linkedin_easy_apply": easy_apply,
        "linkedin_promoted": promoted,
        "linkedin_actively_reviewing": actively,
    }

def classify_row(row: Dict[str, str], prefs: Dict[str, Any]) -> Dict[str, str]:
    family = role_family(row)
    linkedin_state = detect_linkedin_state(row)
    major, minor, review = extract_red_flags(row, prefs)
    score = fit_score(row, family, major, minor, review, prefs)
    decision, priority, reason = decision_from(row, family, score, major, minor, review)
    resume = recommended_resume(family, row)
    # Manual review means "review before applying", not "discard". Do not count deterministic D rows as manual workload.
    manual_review = "yes" if decision in {"A", "B", "C"} and bool(review) else "no"

    red_flags = "; ".join(major + minor + review)
    if decision == "A":
        action = "Apply after checking URL"
    elif decision == "B":
        action = "Apply if Quick Apply / low effort"
    elif decision == "C":
        action = "Keep as backup only"
    else:
        action = "Discard"

    out = dict(row)
    out.update(linkedin_state)
    parser_review = "yes" if any("parser" in x or "parsed" in x or "capture" in x for x in review + major) else "no"
    remote_review = "yes" if any("remote" in x or "location" in x or "spain" in x for x in review + minor + major) else "no"
    schedule_review = "yes" if any("schedule" in x or "night" in x or "weekend" in x or "on-call" in x or "24x7" in x for x in review + minor) else "no"
    contract_review = "yes" if any("contract" in x or "employment type" in x or "stability" in x for x in review + minor) else "no"

    out.update({
        "capture_date": dt.datetime.now().strftime("%Y-%m-%d"),
        "source": "LinkedIn Jobs",
        "decision": decision,
        "human_decision": "Pending review" if decision in {"A", "B", "C"} else "Auto-discarded",
        "priority": priority,
        "fit_score": str(score),
        "role_family": family,
        "resume_version": resume,
        "red_flags": red_flags,
        "fit_reason": reason,
        "recommended_action": action,
        "manual_review": manual_review,
        "parser_review": parser_review,
        "remote_review": remote_review,
        "schedule_review": schedule_review,
        "contract_review": contract_review,
        "application_status": "Applied on LinkedIn" if linkedin_state.get("linkedin_applied") == "yes" else "Not started",
        "applied_date": "",
        "follow_up_date": "",
        "notes": "",
    })
    return out


# Tracker_v2 import columns. These are intentionally aligned with the recommended
# Google Sheets tracker so the export can be pasted/imported with minimal friction.
TRACKER_V2_COLUMNS = [
    "ID", "Company", "Role", "Role Family", "Decision", "Human Decision", "Priority", "Fit Score",
    "Remote Type", "Region", "Source", "URL", "Status", "Previous Status", "Previous Decision",
    "Previous Match Type", "History Seen Before", "History Status", "History Match Type", "LinkedIn State", "LinkedIn Applied", "LinkedIn Viewed", "LinkedIn Easy Apply", "Duplicate Status", "Duplicate Group", "Duplicate Action", "Date Applied",
    "Next Action", "Follow-up Date", "Due?", "Contact", "Contact Degree",
    "Resume Version", "Red Flags", "Fit Reason", "Recommended Action",
    "Manual Review", "Parser Review", "Remote Review", "Schedule Review", "Contract Review",
    "Parser Notes", "Notes", "Capture Date", "Raw Status", "Page", "Job Title Source", "Review Batch",
]

# Minimal copy/paste export for the simplified tracker.
# This does not replace the full audit or Tracker_v2 export; it is an extra low-friction output.
SIMPLE_TRACKER_COLUMNS = [
    "Status", "Priority", "Decision", "Score", "Company", "Role", "Remote", "Location",
    "Next Action", "URL", "Date Applied", "Follow-up", "Contact", "Notes", "Review Batch",
]

# Full technical export kept for audit/debug. This is not meant to be pasted into
# the main tracker.
FULL_CLASSIFIED_COLUMNS = [
    "capture_date", "source", "page_number", "current_job_id", "url", "company", "job_title", "location",
    "workplace_type", "employment_type", "easy_apply", "promoted", "applicant_count",
    "hiring_team_names", "hiring_team_degrees", "hiring_team_profile_urls",
    "decision", "priority", "fit_score", "role_family", "resume_version", "red_flags", "fit_reason",
    "recommended_action", "application_status", "applied_date", "follow_up_date", "notes",
    "manual_review", "parser_review", "remote_review", "schedule_review", "contract_review",
    "previous_status", "previous_decision", "previous_match_type",
    "history_seen_before", "history_status", "history_match_type", "first_seen_date", "last_seen_date", "times_seen",
    "linkedin_card_state", "linkedin_applied", "linkedin_viewed", "linkedin_easy_apply", "linkedin_promoted", "linkedin_actively_reviewing",
    "duplicate_status", "duplicate_group", "duplicate_action", "review_batch",
    "parser_notes", "raw_status", "job_title_source",
]


def to_tracker_v2_row(row: Dict[str, str]) -> Dict[str, str]:
    return {
        "ID": norm(row.get("current_job_id")),
        "Company": norm(row.get("company")),
        "Role": norm(row.get("job_title")),
        "Role Family": norm(row.get("role_family")),
        "Decision": norm(row.get("decision")),
        "Human Decision": norm(row.get("human_decision")),
        "Priority": norm(row.get("priority")),
        "Fit Score": norm(row.get("fit_score")),
        "Remote Type": norm(row.get("workplace_type")),
        "Region": norm(row.get("location")),
        "Source": norm(row.get("source")) or "LinkedIn Jobs",
        "URL": norm(row.get("url")),
        "Status": norm(row.get("application_status")) or "Not started",
        "Previous Status": norm(row.get("previous_status")),
        "Previous Decision": norm(row.get("previous_decision")),
        "Previous Match Type": norm(row.get("previous_match_type")),
        "History Seen Before": norm(row.get("history_seen_before")),
        "History Status": norm(row.get("history_status")),
        "History Match Type": norm(row.get("history_match_type")),
        "LinkedIn State": norm(row.get("linkedin_card_state")),
        "LinkedIn Applied": norm(row.get("linkedin_applied")),
        "LinkedIn Viewed": norm(row.get("linkedin_viewed")),
        "LinkedIn Easy Apply": norm(row.get("linkedin_easy_apply")),
        "Duplicate Status": norm(row.get("duplicate_status")),
        "Duplicate Group": norm(row.get("duplicate_group")),
        "Duplicate Action": norm(row.get("duplicate_action")),
        "Date Applied": norm(row.get("applied_date")),
        "Next Action": norm(row.get("recommended_action")),
        "Follow-up Date": norm(row.get("follow_up_date")),
        "Due?": "",
        "Contact": norm(row.get("hiring_team_names")),
        "Contact Degree": norm(row.get("hiring_team_degrees")),
        "Resume Version": norm(row.get("resume_version")),
        "Red Flags": norm(row.get("red_flags")),
        "Fit Reason": norm(row.get("fit_reason")),
        "Recommended Action": norm(row.get("recommended_action")),
        "Manual Review": norm(row.get("manual_review")),
        "Parser Review": norm(row.get("parser_review")),
        "Remote Review": norm(row.get("remote_review")),
        "Schedule Review": norm(row.get("schedule_review")),
        "Contract Review": norm(row.get("contract_review")),
        "Parser Notes": norm(row.get("parser_notes")),
        "Notes": norm(row.get("notes")),
        "Capture Date": norm(row.get("capture_date")),
        "Raw Status": norm(row.get("raw_status")),
        "Page": norm(row.get("page_number")),
        "Job Title Source": norm(row.get("job_title_source")),
        "Review Batch": norm(row.get("review_batch")),
    }



def to_simple_tracker_row(row: Dict[str, str]) -> Dict[str, str]:
    return {
        "Status": norm(row.get("application_status")) or "Not started",
        "Priority": norm(row.get("priority")),
        "Decision": norm(row.get("decision")),
        "Score": norm(row.get("fit_score")),
        "Company": norm(row.get("company")),
        "Role": norm(row.get("job_title")),
        "Remote": norm(row.get("workplace_type")),
        "Location": norm(row.get("location")),
        "Next Action": norm(row.get("recommended_action")),
        "URL": norm(row.get("url")),
        "Date Applied": norm(row.get("applied_date")),
        "Follow-up": norm(row.get("follow_up_date")),
        "Contact": norm(row.get("hiring_team_names")),
        "Notes": norm(row.get("notes")),
        "Review Batch": norm(row.get("review_batch")),
    }


def count_history_rows(path: Optional[Path]) -> int:
    if not path or not path.exists():
        return 0
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            return sum(1 for _ in csv.DictReader(f))
    except Exception:
        return 0


def backup_history_master(path: Optional[Path]) -> str:
    if not path or not path.exists():
        return ""
    backup_dir = path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_path = backup_dir / f"{path.stem}_{stamp}{path.suffix}"
    shutil.copy2(path, backup_path)
    return str(backup_path)


def detect_false_positive_warnings(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    warnings: List[Dict[str, str]] = []
    title_patterns = [
        ("Data/BI analyst", r"\b(data analyst|bi analyst|business intelligence|qlik|power bi|data governance)\b"),
        ("AI/revenue/sales-adjacent", r"\b(ai revenue|revenue engineer|sales engineer|growth|commercial specialist)\b"),
        ("Generic/template title", r"\bplantilla base|template|open application\b"),
        ("Developer-heavy", r"\bdeveloper|desarrollador|software engineer|chatbot developer|frontend|backend\b"),
        ("QA/testing-heavy", r"\bqa|quality assurance|test automation|tester\b"),
        ("Customer-success/product-success leaning", r"\bcustomer success|product success|onboarding specialist|happiness engineer\b"),
    ]
    body_patterns = [
        ("Remote non-Spain location", r"remote", "non_spain_location"),
        ("Mandatory extra language risk", r"\b(german|french|dutch|danish|italian|portuguese|chinese|mandarin)\b", "language"),
        ("Cloud/SRE stretch", r"\b(kubernetes|aks|terraform|sre|devops|api gateway|kong|openshift)\b", "stretch"),
    ]
    for row in rows:
        title = low(row.get("job_title"))
        body = low(" ".join([row.get("raw_about_job", ""), row.get("red_flags", ""), row.get("fit_reason", "")]))
        loc = low(row.get("location"))
        reasons: List[str] = []
        for label, pattern in title_patterns:
            if re.search(pattern, title):
                reasons.append(label)
        for label, pattern, kind in body_patterns:
            if kind == "non_spain_location":
                if "remote" in low(row.get("workplace_type")) and loc and "spain" not in loc and "españa" not in loc:
                    reasons.append(label)
            elif re.search(pattern, body):
                reasons.append(label)
        if reasons:
            warnings.append({
                "decision": norm(row.get("decision")),
                "score": norm(row.get("fit_score")),
                "company": norm(row.get("company")),
                "job_title": norm(row.get("job_title")),
                "location": norm(row.get("location")),
                "reasons": "; ".join(dict.fromkeys(reasons)),
                "url": norm(row.get("url")),
            })
    return warnings


def _dedupe_rows(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Keep one row per LinkedIn job ID, preferring non-bad parser rows with longer descriptions."""
    best: Dict[str, Dict[str, str]] = {}
    order: List[str] = []
    for row in rows:
        jid = norm(row.get("current_job_id")) or f"row-{len(order)+1}"
        if jid not in best:
            best[jid] = row
            order.append(jid)
            continue
        old = best[jid]
        def quality(r: Dict[str, str]) -> tuple:
            bad = 1 if "bad_panel_capture" in low(r.get("parser_notes")) or not norm(r.get("job_title")) else 0
            about_len = len(norm(r.get("raw_about_job")))
            return (-bad, about_len)
        if quality(row) > quality(old):
            best[jid] = row
    return [best[jid] for jid in order]


def should_export_to_tracker(row: Dict[str, str]) -> bool:
    """Rows for the working tracker.

    The main Tracker_v2 import should contain jobs worth reviewing/applying.
    Deterministic auto-discard rows stay in the full audit CSV only. This keeps
    Google Sheets fast and avoids spending review time on roles that violate
    hard constraints such as mandatory non-Spanish/English languages.
    """
    return norm(row.get("decision")) in {"A", "B", "C"} or norm(row.get("manual_review")) == "yes"




def _duplicate_group_key(row: Dict[str, str]) -> str:
    """Group near-duplicate posts that should not clutter the working tracker."""
    company = normalize_key(row.get("company"))
    title = normalize_title_key(row.get("job_title"))
    about = normalize_key(row.get("raw_about_job"))[:450]

    # Same company + highly similar description catches duplicate reposts with slightly different titles.
    if company and about:
        return f"about::{company}::{about[:280]}"
    if company and title:
        return f"company_title::{company}::{title}"
    return f"job::{norm(row.get('current_job_id')) or norm(row.get('url'))}"


def _is_near_duplicate(a: Dict[str, str], b: Dict[str, str]) -> bool:
    ca, cb = normalize_key(a.get("company")), normalize_key(b.get("company"))
    ta, tb = normalize_title_key(a.get("job_title")), normalize_title_key(b.get("job_title"))
    if not ta or not tb:
        return False
    # Exact/similar title and company.
    if ca and cb and (ca == cb or ca in cb or cb in ca) and jaccard(token_set(ta), token_set(tb)) >= 0.45:
        return True
    # Same title with related UST naming variants or duplicated posts across company aliases.
    if ta == tb and (ca and cb) and (ca in cb or cb in ca or ("ust" in ca and "ust" in cb)):
        return True
    # Same long support title in same country/region.
    if jaccard(token_set(ta), token_set(tb)) >= 0.85 and normalize_key(a.get("location")) == normalize_key(b.get("location")):
        return True
    return False


def _row_quality_for_duplicate(row: Dict[str, str]) -> tuple:
    decision_rank = {"A": 3, "B": 2, "C": 1, "D": 0}.get(norm(row.get("decision")), 0)
    score = int(norm(row.get("fit_score")) or 0)
    manual_penalty = 1 if norm(row.get("manual_review")) == "yes" else 0
    company_len = len(norm(row.get("company")))
    # Prefer real company names over generic aliases like UST when score is equal.
    location_spain_bonus = 1 if normalize_key(row.get("location")) == "spain" else 0
    about_len = min(len(norm(row.get("raw_about_job"))), 8000)
    return (decision_rank, score, location_spain_bonus, company_len, about_len, -manual_penalty)


def mark_and_filter_duplicates(rows: List[Dict[str, str]]) -> Tuple[List[Dict[str, str]], List[Dict[str, str]], Dict[str, int]]:
    """Mark duplicates and return rows to keep plus duplicate rows excluded from tracker import."""
    # Start with each row in its own group, then greedily merge near duplicates among exportable rows.
    candidates = [r for r in rows if should_export_to_tracker(r)]
    groups: List[List[Dict[str, str]]] = []
    for row in candidates:
        placed = False
        for group in groups:
            if any(_is_near_duplicate(row, existing) for existing in group):
                group.append(row)
                placed = True
                break
        if not placed:
            groups.append([row])

    keep_ids = set()
    duplicate_rows: List[Dict[str, str]] = []
    duplicate_groups = 0
    for idx, group in enumerate(groups, 1):
        group_id = f"DUP-{idx:04d}" if len(group) > 1 else ""
        if len(group) == 1:
            r = group[0]
            r["duplicate_status"] = "Unique"
            r["duplicate_group"] = ""
            r["duplicate_action"] = "Keep"
            keep_ids.add(id(r))
            continue
        duplicate_groups += 1
        primary = sorted(group, key=_row_quality_for_duplicate, reverse=True)[0]
        for r in group:
            r["duplicate_group"] = group_id
            if r is primary:
                r["duplicate_status"] = "Primary"
                r["duplicate_action"] = "Keep best duplicate"
                keep_ids.add(id(r))
            else:
                r["duplicate_status"] = "Duplicate"
                r["duplicate_action"] = f"Skip duplicate of {norm(primary.get('company'))} | {norm(primary.get('job_title'))}"
                duplicate_rows.append(r)

    kept_rows = [r for r in rows if (not should_export_to_tracker(r)) or id(r) in keep_ids]
    return kept_rows, duplicate_rows, {"duplicate_groups": duplicate_groups, "duplicate_rows": len(duplicate_rows)}



HISTORY_COLUMNS = [
    "current_job_id", "url", "company", "job_title", "location", "decision", "human_decision",
    "application_status", "fit_score", "role_family", "resume_version", "red_flags", "recommended_action",
    "first_seen_date", "last_seen_date", "times_seen", "last_batch_id", "last_imported_to_tracker",
    "linkedin_card_state", "linkedin_applied", "linkedin_viewed", "linkedin_easy_apply", "linkedin_promoted", "linkedin_actively_reviewing",
    "parser_notes", "raw_status", "job_title_source",
]


def _empty_history_index() -> Dict[str, Dict[str, Dict[str, str]]]:
    return {"by_id": {}, "by_url": {}, "by_company_role": {}}


def load_history_master(path: Optional[Path]) -> Dict[str, Dict[str, Dict[str, str]]]:
    if not path or not path.exists():
        return _empty_history_index()
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    idx = _empty_history_index()
    for r in rows:
        jid = norm(r.get("current_job_id") or r.get("ID"))
        url = norm(r.get("url") or r.get("URL"))
        company = norm(r.get("company") or r.get("Company"))
        role = norm(r.get("job_title") or r.get("Role"))
        key = f"{normalize_key(company)}::{normalize_title_key(role)}"
        if jid: idx["by_id"][jid] = r
        if url: idx["by_url"][url] = r
        if company and role: idx["by_company_role"][key] = r
    return idx


def apply_history_matches(rows: List[Dict[str, str]], history_index: Dict[str, Dict[str, Dict[str, str]]]) -> int:
    matches = 0
    for row in rows:
        match = None
        match_type = ""
        jid = norm(row.get("current_job_id"))
        url = norm(row.get("url"))
        key = f"{normalize_key(row.get('company'))}::{normalize_title_key(row.get('job_title'))}"
        if jid and jid in history_index.get("by_id", {}):
            match = history_index["by_id"][jid]
            match_type = "ID"
        elif url and url in history_index.get("by_url", {}):
            match = history_index["by_url"][url]
            match_type = "URL"
        elif key in history_index.get("by_company_role", {}):
            match = history_index["by_company_role"][key]
            match_type = "Company+Role"
        if match:
            matches += 1
            row["history_seen_before"] = "yes"
            row["history_status"] = norm(match.get("application_status") or match.get("Status") or match.get("decision"))
            row["history_match_type"] = match_type
            row["first_seen_date"] = norm(match.get("first_seen_date"))
            row["times_seen"] = str(int(norm(match.get("times_seen")) or "1") + 1)
        else:
            row["history_seen_before"] = "no"
            row["history_status"] = ""
            row["history_match_type"] = ""
            row["first_seen_date"] = ""
            row["times_seen"] = "1"
    return matches


def is_history_actioned(row: Dict[str, str]) -> bool:
    status = low(row.get("history_status"))
    return bool(status and status not in {"not started", "new", "pending review", "a", "b", "c", "d", "auto-discarded", ""})


def update_history_master(path: Optional[Path], rows: List[Dict[str, str]], batch_id: str, imported_ids: set[str]) -> int:
    if not path:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: Dict[str, Dict[str, str]] = {}
    if path.exists():
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                key = norm(r.get("current_job_id")) or norm(r.get("url")) or f"{normalize_key(r.get('company'))}::{normalize_title_key(r.get('job_title'))}"
                if key:
                    existing[key] = r
    today = dt.datetime.now().strftime("%Y-%m-%d")
    for row in rows:
        key = norm(row.get("current_job_id")) or norm(row.get("url")) or f"{normalize_key(row.get('company'))}::{normalize_title_key(row.get('job_title'))}"
        if not key:
            continue
        old = existing.get(key, {})
        first_seen = norm(old.get("first_seen_date")) or today
        times_seen = int(norm(old.get("times_seen")) or "0") + 1
        record = {
            "current_job_id": norm(row.get("current_job_id")),
            "url": norm(row.get("url")),
            "company": norm(row.get("company")),
            "job_title": norm(row.get("job_title")),
            "location": norm(row.get("location")),
            "decision": norm(row.get("decision")),
            "human_decision": norm(old.get("human_decision")) or norm(row.get("human_decision")),
            "application_status": norm(old.get("application_status")) or norm(row.get("application_status")),
            "fit_score": norm(row.get("fit_score")),
            "role_family": norm(row.get("role_family")),
            "resume_version": norm(row.get("resume_version")),
            "red_flags": norm(row.get("red_flags")),
            "recommended_action": norm(row.get("recommended_action")),
            "first_seen_date": first_seen,
            "last_seen_date": today,
            "times_seen": str(times_seen),
            "last_batch_id": batch_id,
            "last_imported_to_tracker": "yes" if norm(row.get("current_job_id")) in imported_ids else norm(old.get("last_imported_to_tracker")),
            "linkedin_card_state": norm(row.get("linkedin_card_state")),
            "linkedin_applied": norm(row.get("linkedin_applied")),
            "linkedin_viewed": norm(row.get("linkedin_viewed")),
            "linkedin_easy_apply": norm(row.get("linkedin_easy_apply")),
            "linkedin_promoted": norm(row.get("linkedin_promoted")),
            "linkedin_actively_reviewing": norm(row.get("linkedin_actively_reviewing")),
            "parser_notes": norm(row.get("parser_notes")),
            "raw_status": norm(row.get("raw_status")),
            "job_title_source": norm(row.get("job_title_source")),
        }
        existing[key] = record
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HISTORY_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(existing.values())
    return len(existing)

def _load_previous_tracker(path: Optional[Path]) -> Dict[str, Dict[str, str]]:
    if not path or not path.exists():
        return {"by_id": {}, "by_url": {}, "by_company_role": {}}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    by_id: Dict[str, Dict[str, str]] = {}
    by_url: Dict[str, Dict[str, str]] = {}
    by_company_role: Dict[str, Dict[str, str]] = {}
    for r in rows:
        jid = norm(r.get("ID") or r.get("current_job_id") or r.get("Job ID"))
        url = norm(r.get("URL") or r.get("url"))
        company = norm(r.get("Company") or r.get("company"))
        role = norm(r.get("Role") or r.get("job_title"))
        key = f"{normalize_key(company)}::{normalize_title_key(role)}"
        if jid:
            by_id[jid] = r
        if url:
            by_url[url] = r
        if company and role:
            by_company_role[key] = r
    return {"by_id": by_id, "by_url": by_url, "by_company_role": by_company_role}


def apply_previous_tracker_matches(rows: List[Dict[str, str]], previous_index: Dict[str, Dict[str, Dict[str, str]]]) -> int:
    matches = 0
    for row in rows:
        match = None
        match_type = ""
        jid = norm(row.get("current_job_id"))
        url = norm(row.get("url"))
        key = f"{normalize_key(row.get('company'))}::{normalize_title_key(row.get('job_title'))}"
        if jid and jid in previous_index.get("by_id", {}):
            match = previous_index["by_id"][jid]
            match_type = "ID"
        elif url and url in previous_index.get("by_url", {}):
            match = previous_index["by_url"][url]
            match_type = "URL"
        elif key in previous_index.get("by_company_role", {}):
            match = previous_index["by_company_role"][key]
            match_type = "Company+Role"
        if match:
            matches += 1
            prev_status = norm(match.get("Status") or match.get("application_status"))
            prev_decision = norm(match.get("Decision") or match.get("Auto Decision") or match.get("decision"))
            row["previous_status"] = prev_status
            row["previous_decision"] = prev_decision
            row["previous_match_type"] = match_type
            # Do not import jobs already actioned in the tracker by default.
            if prev_status and prev_status.lower() not in {"not started", "new", "pending review", ""}:
                row["duplicate_status"] = row.get("duplicate_status") or "Previously tracked"
                row["duplicate_action"] = f"Skip - previous status: {prev_status}"
        else:
            row["previous_status"] = ""
            row["previous_decision"] = ""
            row["previous_match_type"] = ""
    return matches


def is_previous_actioned(row: Dict[str, str]) -> bool:
    prev = low(row.get("previous_status"))
    return bool(prev and prev not in {"not started", "new", "pending review", ""})


def classify_csv(
    input_csv: Path,
    output_csv: Path,
    report_md: Path,
    prefs: Dict[str, Any],
    previous_tracker_csv: Optional[Path] = None,
    exclude_previous_matches: bool = True,
    history_master_csv: Optional[Path] = None,
    exclude_seen_before: bool = False,
    exclude_history_actioned: bool = True,
    update_history: bool = True,
    history_backup: bool = True,
    review_batch_label: str = "",
    simple_output_csv: Optional[Path] = None,
) -> Dict[str, Any]:
    with input_csv.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        raw_rows = list(reader)

    source_total = len(raw_rows)
    deduped_rows = _dedupe_rows(raw_rows)
    timestamp_batch = dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    review_batch = norm(review_batch_label) or timestamp_batch
    rows = [classify_row(row, prefs) for row in deduped_rows]
    for row in rows:
        row["review_batch"] = review_batch
        row.setdefault("duplicate_status", "")
        row.setdefault("duplicate_group", "")
        row.setdefault("duplicate_action", "")

    previous_index = _load_previous_tracker(previous_tracker_csv)
    previous_matches = apply_previous_tracker_matches(rows, previous_index)

    history_index = load_history_master(history_master_csv)
    history_matches = apply_history_matches(rows, history_index)

    rows_with_duplicate_marks, duplicate_rows, duplicate_stats = mark_and_filter_duplicates(rows)

    # Main tracker import excludes deterministic D rows, duplicate rows, and optionally rows already actioned in an existing tracker.
    # The full audit CSV below still contains everything for traceability.
    import_rows = []
    for row in rows_with_duplicate_marks:
        if not should_export_to_tracker(row):
            continue
        if norm(row.get("linkedin_applied")) == "yes":
            continue
        if exclude_previous_matches and is_previous_actioned(row):
            continue
        if exclude_history_actioned and is_history_actioned(row):
            continue
        if exclude_seen_before and norm(row.get("history_seen_before")) == "yes":
            continue
        if row.get("duplicate_status") == "Duplicate":
            continue
        import_rows.append(row)
    tracker_rows = [to_tracker_v2_row(row) for row in import_rows]

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=TRACKER_V2_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(tracker_rows)

    if simple_output_csv is None:
        simple_output_csv = output_csv.with_name(output_csv.stem.replace("tracker_v2_import", "tracker_simple_import") + output_csv.suffix)
    simple_output_csv.parent.mkdir(parents=True, exist_ok=True)
    with simple_output_csv.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SIMPLE_TRACKER_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows([to_simple_tracker_row(row) for row in import_rows])

    full_output_csv = output_csv.with_name(output_csv.stem.replace("tracker_v2_import", "full_classified_export") + output_csv.suffix)
    with full_output_csv.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FULL_CLASSIFIED_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    discard_archive_csv = output_csv.with_name(output_csv.stem.replace("tracker_v2_import", "discard_archive") + output_csv.suffix)
    discard_rows = [row for row in rows if not should_export_to_tracker(row)]
    with discard_archive_csv.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=TRACKER_V2_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows([to_tracker_v2_row(row) for row in discard_rows])

    duplicate_archive_csv = output_csv.with_name(output_csv.stem.replace("tracker_v2_import", "duplicate_archive") + output_csv.suffix)
    with duplicate_archive_csv.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=TRACKER_V2_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows([to_tracker_v2_row(row) for row in duplicate_rows])

    previous_archive_csv = output_csv.with_name(output_csv.stem.replace("tracker_v2_import", "previous_matches_archive") + output_csv.suffix)
    previous_actioned_rows = [row for row in rows if is_previous_actioned(row)]
    with previous_archive_csv.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=TRACKER_V2_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows([to_tracker_v2_row(row) for row in previous_actioned_rows])

    linkedin_applied_archive_csv = output_csv.with_name(output_csv.stem.replace("tracker_v2_import", "linkedin_applied_archive") + output_csv.suffix)
    linkedin_applied_rows = [row for row in rows if norm(row.get("linkedin_applied")) == "yes"]
    with linkedin_applied_archive_csv.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=TRACKER_V2_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows([to_tracker_v2_row(row) for row in linkedin_applied_rows])

    history_ids = {norm(row.get("current_job_id")) for row in import_rows if norm(row.get("current_job_id"))}
    history_backup_csv = ""
    if update_history and history_backup and history_master_csv and history_master_csv.exists():
        history_backup_csv = backup_history_master(history_master_csv)
    history_total = update_history_master(history_master_csv, rows, review_batch, history_ids) if update_history else count_history_rows(history_master_csv)
    false_positive_warnings = detect_false_positive_warnings(import_rows)

    decision_counts = Counter(r["decision"] for r in rows)
    import_decision_counts = Counter(r["decision"] for r in import_rows)
    manual_count = sum(1 for r in rows if r.get("manual_review") == "yes")
    import_manual_count = sum(1 for r in import_rows if r.get("manual_review") == "yes")
    excluded_count = len(discard_rows)
    priority_rank = {"A": 0, "B": 1, "C": 2, "D": 3}
    sorted_rows = sorted(import_rows, key=lambda r: (priority_rank.get(r.get("decision", "D"), 9), -int(r.get("fit_score", "0") or 0)))
    top_rows = [r for r in sorted_rows if r.get("decision") in {"A", "B"}][:30]

    report_lines = [
        "# LinkedIn Job Classification Report", "",
        f"Input CSV: `{input_csv}`",
        f"Tracker_v2 import CSV: `{output_csv}`",
        f"Simple tracker import CSV: `{simple_output_csv}`",
        f"Full classified audit CSV: `{full_output_csv}`",
        f"Discard archive CSV: `{discard_archive_csv}`",
        f"Duplicate archive CSV: `{duplicate_archive_csv}`",
        f"Previous matches archive CSV: `{previous_archive_csv}`",
        f"LinkedIn applied archive CSV: `{linkedin_applied_archive_csv}`",
        f"History master CSV: `{history_master_csv}`",
        f"History backup CSV: `{history_backup_csv}`",
        f"Review batch: `{review_batch}`",
        f"History update mode: `{'updated' if update_history else 'dry-run / not updated'}`", "",
        "## Summary", "",
        f"- Source rows: {source_total}",
        f"- Unique rows classified: {len(rows)}",
        f"- Tracker_v2 rows exported: {len(import_rows)}",
        f"- Auto-discard rows excluded from Tracker_v2 import: {excluded_count}",
        f"- Duplicate rows excluded from Tracker_v2 import: {duplicate_stats.get('duplicate_rows', 0)}",
        f"- Duplicate groups detected: {duplicate_stats.get('duplicate_groups', 0)}",
        f"- Previous tracker matches found: {previous_matches}",
        f"- Previous actioned rows excluded: {len(previous_actioned_rows) if exclude_previous_matches else 0}",
        f"- History matches found: {history_matches}",
        f"- History master rows after update: {history_total}",
        f"- LinkedIn applied rows excluded: {len(linkedin_applied_rows)}",
        f"- A: {decision_counts.get('A', 0)}",
        f"- B: {decision_counts.get('B', 0)}",
        f"- C: {decision_counts.get('C', 0)}",
        f"- D: {decision_counts.get('D', 0)}",
        f"- Manual review total: {manual_count}",
        f"- Manual review exported: {import_manual_count}",
        f"- Possible false-positive warnings: {len(false_positive_warnings)}", "",
        "## Export policy", "",
        f"The Tracker_v2 import excludes deterministic auto-discard rows. Hard-discarded roles include mandatory languages outside the allowed list ({', '.join(sorted(allowed_language_keys(prefs)))}), bad parser/capture mismatches, and any hybrid/onsite role more than ~30 km from Vigo. Remote roles are not discarded by distance. Schedule risks such as night shift, weekend work, or on-call are kept as reviewable rows instead of being excluded. Duplicate/near-duplicate posts are grouped and only the best row is kept in the Tracker_v2 import. All captured rows are stored in the persistent local history file so future batches can skip already-seen/actioned jobs if configured.", "",
        "## Top exported candidates", "",
        "| Decision | Score | Company | Title | Location | Action | Red flags |",
        "|---|---:|---|---|---|---|---|",
    ]

    def esc(s: str) -> str:
        return norm(s).replace("|", "\\|")[:220]

    for r in top_rows:
        cells = [
            esc(r.get("decision", "")),
            esc(r.get("fit_score", "")),
            esc(r.get("company", "")),
            esc(r.get("job_title", "")),
            esc(r.get("location", "")),
            esc(r.get("recommended_action", "")),
            esc(r.get("red_flags", "")),
        ]
        report_lines.append(f"| {cells[0]} | {cells[1]} | {cells[2]} | {cells[3]} | {cells[4]} | {cells[5]} | {cells[6]} |")

    report_lines.extend(["", "## Possible false positives to manually check", "", "| Decision | Score | Company | Title | Location | Reasons |", "|---|---:|---|---|---|---|"])
    for r in false_positive_warnings[:40]:
        report_lines.append(
            f"| {esc(r.get('decision', ''))} | {esc(r.get('score', ''))} | {esc(r.get('company', ''))} | "
            f"{esc(r.get('job_title', ''))} | {esc(r.get('location', ''))} | {esc(r.get('reasons', ''))} |"
        )

    report_md.parent.mkdir(parents=True, exist_ok=True)
    report_md.write_text("\n".join(report_lines), encoding="utf-8")

    return {
        "rows": import_rows,
        "all_rows": rows,
        "total": len(import_rows),
        "classified_total": len(rows),
        "source_total": source_total,
        "excluded_auto_discard": excluded_count,
        "decision_counts": dict(decision_counts),
        "import_decision_counts": dict(import_decision_counts),
        "manual_review": import_manual_count,
        "manual_review_total": manual_count,
        "output_csv": str(output_csv),
        "simple_output_csv": str(simple_output_csv),
        "full_output_csv": str(full_output_csv),
        "discard_archive_csv": str(discard_archive_csv),
        "duplicate_archive_csv": str(duplicate_archive_csv),
        "previous_archive_csv": str(previous_archive_csv),
        "linkedin_applied_archive_csv": str(linkedin_applied_archive_csv),
        "history_master_csv": str(history_master_csv) if history_master_csv else "",
        "history_backup_csv": history_backup_csv,
        "history_update_mode": "updated" if update_history else "dry-run / not updated",
        "review_batch": review_batch,
        "false_positive_warnings": false_positive_warnings,
        "duplicate_rows": duplicate_stats.get("duplicate_rows", 0),
        "duplicate_groups": duplicate_stats.get("duplicate_groups", 0),
        "previous_matches": previous_matches,
        "previous_actioned_excluded": len(previous_actioned_rows) if exclude_previous_matches else 0,
        "history_matches": history_matches,
        "history_total": history_total,
        "linkedin_applied_rows": len(linkedin_applied_rows),
        "report_md": str(report_md),
    }
