from app.models import DecisionResult, NormalizedJob, RuleProfile


def _lower_values(values: list[str]) -> list[str]:
    return [value.strip().lower() for value in values if value.strip()]


def _contains_any(text: str, keywords: list[str]) -> list[str]:
    lowered_text = text.lower()
    return [keyword for keyword in keywords if keyword.lower() in lowered_text]


def _priority(score: int) -> str:
    if score >= 75:
        return "High"
    if score >= 45:
        return "Medium"
    return "Low"


def _risk_key(value: str) -> str:
    normalized = value.lower().replace("/", "_").replace("-", "_").replace(" ", "_")
    if normalized in {"24_7", "heavy_on_call"}:
        return "heavy_on_call"
    if "rotating" in normalized:
        return "rotating_shifts"
    if "night" in normalized:
        return "night_shifts"
    if "call_center" in normalized or "call_centre" in normalized:
        return "call_center"
    if "weekend" in normalized:
        return "weekends"
    if "on_call" in normalized:
        return "on_call"
    return normalized


def _outside_base_location(job: NormalizedJob, profile: RuleProfile) -> bool:
    if job.distance_km is not None:
        return job.distance_km > profile.max_distance_km_for_hybrid_onsite

    base_city = profile.base_location.split(",", maxsplit=1)[0].strip().lower()
    location = job.location.lower()
    if not base_city or base_city in {"remote", "remote or local region"} or not location:
        return False

    return base_city not in location and profile.max_distance_km_for_hybrid_onsite <= 50


def classify_job(job: NormalizedJob, profile: RuleProfile) -> DecisionResult:
    score = 50
    reasons: list[str] = []
    triggered_rules: list[str] = []
    warnings: list[str] = []
    missing_information: list[str] = []
    hard_discard = False
    manual_review = False

    if job.duplicate_of:
        return DecisionResult(
            decision="Duplicate",
            score=0,
            priority="Low",
            reasons=[f"Job duplicates {job.duplicate_of}."],
            triggered_rules=["dedupe.duplicate_of"],
            warnings=[],
            missing_information=[],
            matched_positive_keywords=[],
            matched_risk_keywords=[],
            parser_confidence=job.parser_confidence,
            profile_id=profile.profile_id,
        )

    # Already-reviewed jobs are surfaced as Duplicate for now so they do not re-enter Apply/Maybe queues.
    if job.already_reviewed:
        return DecisionResult(
            decision="Duplicate",
            score=0,
            priority="Low",
            reasons=["Job was already reviewed previously."],
            triggered_rules=["dedupe.already_reviewed"],
            warnings=[],
            missing_information=[],
            matched_positive_keywords=[],
            matched_risk_keywords=[],
            parser_confidence=job.parser_confidence,
            profile_id=profile.profile_id,
        )

    if not job.title:
        missing_information.append("title")
    if not job.company:
        missing_information.append("company")
    if not job.location:
        missing_information.append("location")
    if not job.work_mode or job.work_mode == "unknown":
        missing_information.append("work_mode")
    if not job.mandatory_languages:
        missing_information.append("mandatory_language_clarity")

    accepted_languages = set(_lower_values(profile.accepted_languages))
    unsupported_languages = [
        language for language in job.mandatory_languages if language.lower() not in accepted_languages
    ]
    if unsupported_languages:
        hard_discard = True
        reasons.append(f"Unsupported mandatory language(s): {', '.join(unsupported_languages)}.")
        triggered_rules.append("language.unsupported_mandatory")

    work_mode = job.work_mode.lower()
    if work_mode in {"hybrid", "onsite"} and _outside_base_location(job, profile):
        hard_discard = True
        reasons.append("Hybrid/onsite role is outside the configured distance limit.")
        triggered_rules.append("location.outside_distance_limit")
    elif work_mode == "remote" and profile.remote_ignores_distance:
        reasons.append("Remote role ignores distance for this profile.")
        triggered_rules.append("location.remote_distance_exempt")

    searchable_text = " ".join(
        [job.title, job.company, job.location, job.description, " ".join(job.risk_keywords), " ".join(job.positive_keywords)]
    )
    matched_discard_keywords = _contains_any(searchable_text, profile.discard_keywords)
    if matched_discard_keywords:
        hard_discard = True
        reasons.append(f"Matched discard keyword(s): {', '.join(matched_discard_keywords)}.")
        triggered_rules.append("keywords.discard")

    matched_positive_keywords = sorted(
        set(_contains_any(searchable_text, profile.positive_keywords) + job.positive_keywords)
    )
    if matched_positive_keywords:
        score += min(len(matched_positive_keywords) * 10, 30)
        reasons.append(f"Matched positive keyword(s): {', '.join(matched_positive_keywords)}.")
        triggered_rules.append("keywords.positive")

    matched_risk_keywords = sorted(
        set(
            _contains_any(searchable_text, profile.risk_keywords)
            + job.risk_keywords
            + job.shift_indicators
            + job.on_call_indicators
        )
    )
    for risk in matched_risk_keywords:
        severity = profile.risk_severity_settings.get(_risk_key(risk), "warning")
        warnings.append(f"{risk}: {severity}")
        triggered_rules.append(f"risk.{_risk_key(risk)}")
        if severity == "discard":
            hard_discard = True
        elif severity == "manual_review":
            manual_review = True
        score -= 10

    if work_mode in _lower_values(profile.preferred_work_modes):
        score += 10
        reasons.append("Work mode is preferred by the selected profile.")
        triggered_rules.append("work_mode.preferred")
    elif work_mode and work_mode in _lower_values(profile.acceptable_work_modes):
        score += 5
        reasons.append("Work mode is acceptable for the selected profile.")
        triggered_rules.append("work_mode.acceptable")
    elif work_mode and work_mode != "unknown":
        warnings.append("Work mode is not configured as acceptable for this profile.")
        score -= 10

    matched_stretch_skills = _contains_any(searchable_text, profile.stretch_skills)
    if matched_stretch_skills:
        warnings.append(f"Stretch skill(s) need review: {', '.join(matched_stretch_skills)}.")
        triggered_rules.append("skills.stretch")
        manual_review = True
        score -= 5

    if missing_information:
        score -= len(missing_information) * 5
        triggered_rules.append("parser.missing_information")
        if {"work_mode", "location"}.intersection(missing_information):
            manual_review = True

    if job.parser_confidence == "low":
        warnings.append("Parser confidence is low.")
        triggered_rules.append("parser.low_confidence")
        manual_review = True
        score -= 20
    elif job.parser_confidence == "medium":
        score -= 5

    score = max(0, min(score, 100))

    if hard_discard:
        decision = "Discard"
        score = min(score, 30)
    elif manual_review:
        decision = "Manual Review"
    elif score >= 75:
        decision = "Apply"
    elif score >= 45:
        decision = "Maybe"
    else:
        decision = "Manual Review"

    if not reasons and decision == "Maybe":
        reasons.append("Job has no hard discard rules but lacks enough positive signal for Apply.")

    return DecisionResult(
        decision=decision,
        score=score,
        priority=_priority(score),
        reasons=reasons,
        triggered_rules=sorted(set(triggered_rules)),
        warnings=warnings,
        missing_information=missing_information,
        matched_positive_keywords=matched_positive_keywords,
        matched_risk_keywords=matched_risk_keywords,
        parser_confidence=job.parser_confidence,
        profile_id=profile.profile_id,
    )
