from __future__ import annotations

import csv
import datetime as dt
import re
from pathlib import Path
from typing import Any

import streamlit as st

from gui_app.paths import (
    ROOT, CAPTURE_SCRIPT, PARSER_RUNNER, CONFIG_DIR, GSHEET_DIR, REPORTS_DIR, LOGS_DIR, HISTORY_MASTER,
    ensure_dirs, latest_raw_jsonl, latest_parsed_csv, latest_analysis_pages, parsed_csv_files, latest_file,
)
from gui_app.preferences import load_preferences, save_preferences
from gui_app.runner import run_capture, run_parser
from gui_app.classifier import classify_csv

ensure_dirs()
PREFS_PATH = CONFIG_DIR / "job_preferences.json"
MANUAL_INPUTS_DIR = ROOT / "manual_inputs"
MANUAL_INPUTS_DIR.mkdir(parents=True, exist_ok=True)

st.set_page_config(page_title="LinkedIn Job Capture Assistant", layout="wide")
st.title("LinkedIn Job Capture Assistant")
st.caption("Local workflow helper v24: collection-aware capture fallback + diagnostics → strict panel sync → classify → export Tracker_v2-ready CSV.")

prefs = load_preferences(PREFS_PATH)

APP_CAPTURE_VERSION = "v35.10/v24"
APP_PARSER_VERSION = "v34"
APP_CLASSIFIER_VERSION = "v23 rules + configurable languages"

LANGUAGE_OPTIONS = {
    "english": "English",
    "spanish": "Spanish",
    "portuguese": "Portuguese",
    "french": "French",
    "german": "German",
    "dutch": "Dutch",
    "italian": "Italian",
    "chinese": "Chinese/Mandarin",
    "danish": "Danish",
    "polish": "Polish",
    "swedish": "Swedish",
    "norwegian": "Norwegian",
    "finnish": "Finnish",
}

def safe_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", name or "uploaded.csv").strip("._")
    return cleaned or "uploaded.csv"


def save_uploaded_csv(uploaded_file: Any, prefix: str) -> Path | None:
    if uploaded_file is None:
        return None
    stamp = dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    dest = MANUAL_INPUTS_DIR / f"{prefix}_{stamp}_{safe_name(uploaded_file.name)}"
    dest.write_bytes(uploaded_file.getvalue())
    return dest


def count_data_rows(path: Path | None) -> int | None:
    if not path or not path.exists():
        return None
    try:
        if path.suffix.lower() == ".jsonl":
            with path.open("r", encoding="utf-8", errors="replace") as f:
                return sum(1 for line in f if line.strip())
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            return sum(1 for _ in csv.DictReader(f))
    except Exception:
        return None


def report_metric(report_path: Path | None, label: str) -> str:
    if not report_path or not report_path.exists():
        return ""
    try:
        text = report_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""
    match = re.search(rf"^- {re.escape(label)}: (.+)$", text, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def render_latest_batch_summary() -> None:
    latest_raw = latest_raw_jsonl()
    latest_parsed = latest_parsed_csv()
    latest_report = latest_file(REPORTS_DIR / "classification_report_*.md")
    latest_import = latest_file(GSHEET_DIR / "tracker_v2_import_*.csv")

    st.markdown("#### Latest batch status")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Raw rows", count_data_rows(latest_raw) if latest_raw else "—")
    m2.metric("Parsed rows", count_data_rows(latest_parsed) if latest_parsed else "—")
    m3.metric("Report source rows", report_metric(latest_report, "Source rows") or "—")
    m4.metric("Tracker import rows", count_data_rows(latest_import) if latest_import else "—")

    if latest_import:
        st.success(f"Recommended import file: {latest_import}")
    elif latest_report:
        st.info(f"Latest report: {latest_report}")
    else:
        st.info("No classification report/import file found yet.")


def render_process_output(label: str, output: str) -> None:
    lines = output.splitlines()
    if not lines:
        st.info(f"No {label.lower()} output captured.")
        return
    shown = "\n".join(lines[-80:])
    st.text_area(
        f"{label} output preview — last {min(len(lines), 80)} of {len(lines)} lines",
        value=shown,
        height=260,
        disabled=True,
    )
    if len(lines) > 80:
        with st.expander(f"Show full {label.lower()} output ({len(lines)} lines)", expanded=False):
            st.text_area(
                f"Full {label.lower()} output",
                value=output,
                height=420,
                disabled=True,
                label_visibility="collapsed",
            )


def render_recommended_next_action(result: dict[str, Any], out_csv: Path) -> None:
    import_counts = result.get("import_decision_counts", {})
    total = result.get("total", 0)
    simple_csv = result.get("simple_output_csv", "")
    st.markdown("#### Recommended next action")
    st.success(f"Import this CSV into the tracker staging/paste sheet: {out_csv}")
    if simple_csv:
        st.info(f"Simplified tracker import also generated: {simple_csv}")
    st.write(
        f"Exported rows: **{total}** · "
        f"A: **{import_counts.get('A', 0)}** · "
        f"B: **{import_counts.get('B', 0)}** · "
        f"C: **{import_counts.get('C', 0)}**"
    )
    st.caption("Apply A first, review B next, keep C as backup/low-effort. Ignore D except in the audit archives.")


def render_false_positive_warnings(result: dict[str, Any]) -> None:
    warnings = result.get("false_positive_warnings") or []
    if not warnings:
        st.success("No obvious false-positive warning patterns detected in the exported rows.")
        return
    st.warning(f"Possible false positives to manually check before applying: {len(warnings)}")
    st.dataframe(warnings[:40], width="stretch", hide_index=True)


with st.sidebar:
    st.header("Status")
    st.write(f"Root: `{ROOT}`")
    st.write(f"Capture {APP_CAPTURE_VERSION}:", "✅" if CAPTURE_SCRIPT.exists() else "❌")
    st.write(f"Parser {APP_PARSER_VERSION} runner:", "✅" if PARSER_RUNNER.exists() else "❌")
    st.write("Classifier:", APP_CLASSIFIER_VERSION)
    raw = latest_raw_jsonl()
    parsed = latest_parsed_csv()
    st.write("Latest raw:", raw.name if raw else "None")
    st.write("Latest parsed:", parsed.name if parsed else "None")
    pages = latest_analysis_pages()
    st.write("Analysis pages:", len(pages))
    latest_launcher = latest_file(LOGS_DIR / "capture_launcher_v35_*.log")
    latest_diag = latest_file(LOGS_DIR / "capture_diagnostic_v35_*.log")
    st.write("Latest launcher log:", latest_launcher.name if latest_launcher else "None")
    st.write("Latest diagnostic log:", latest_diag.name if latest_diag else "None")
    st.write("History master:", "✅" if HISTORY_MASTER.exists() else "None yet")

st.info(
    "This is a local assistant. It does not apply to jobs, send LinkedIn messages, log in, or upload captures. "
    "Use A/B/C/D as recommendations only."
)

with st.expander("Latest batch summary", expanded=False):
    render_latest_batch_summary()

tab_prefs, tab_capture, tab_classify, tab_files = st.tabs([
    "1. Preferences", "2. Capture & Parse", "3. Classify & Export", "4. Files"
])

with tab_prefs:
    st.subheader("Job preferences")
    st.write("These settings control classification. LinkedIn filters should still be set manually in the browser for now.")

    c1, c2, c3 = st.columns(3)
    with c1:
        prefs["prefer_remote"] = st.checkbox("Prefer remote", value=bool(prefs["prefer_remote"]))
        prefs["prefer_spain"] = st.checkbox("Prefer Spain-compatible roles", value=bool(prefs["prefer_spain"]))
        prefs["eu_uk_remote_ok"] = st.checkbox("EU/UK remote acceptable", value=bool(prefs["eu_uk_remote_ok"]))
        prefs["b2b_contract_ok"] = st.checkbox("B2B/contractor acceptable", value=bool(prefs["b2b_contract_ok"]))
    with c2:
        prefs["avoid_on_call"] = st.checkbox("Avoid on-call / 24x7", value=bool(prefs["avoid_on_call"]))
        prefs["avoid_weekends"] = st.checkbox("Avoid weekends", value=bool(prefs["avoid_weekends"]))
        prefs["avoid_night_shift"] = st.checkbox("Avoid night shift", value=bool(prefs["avoid_night_shift"]))
        prefs["avoid_call_center"] = st.checkbox("Avoid call-centre / phone-heavy roles", value=bool(prefs["avoid_call_center"]))
        prefs["avoid_us_only"] = st.checkbox("Avoid US-only / US-location roles", value=bool(prefs["avoid_us_only"]))
        prefs["avoid_german_french_required"] = st.checkbox("Avoid mandatory languages outside allowed list", value=bool(prefs["avoid_german_french_required"]))
        prefs["avoid_onsite_outside_spain"] = st.checkbox("Avoid onsite/hybrid outside Spain", value=bool(prefs["avoid_onsite_outside_spain"]))
        allowed_default = [x for x in prefs.get("allowed_languages", ["english", "spanish"]) if x in LANGUAGE_OPTIONS]
        prefs["allowed_languages"] = st.multiselect(
            "Allowed professional languages",
            options=list(LANGUAGE_OPTIONS.keys()),
            default=allowed_default or ["english", "spanish"],
            format_func=lambda key: LANGUAGE_OPTIONS.get(key, key),
            help="Mandatory languages not selected here are hard-discarded. 'Plus/nice-to-have' languages are not hard-discarded.",
        )
    with c3:
        prefs["prefer_it_support"] = st.checkbox("Prefer IT Support / Service Desk", value=bool(prefs["prefer_it_support"]))
        prefs["prefer_saas_support"] = st.checkbox("Prefer Application / SaaS Support", value=bool(prefs["prefer_saas_support"]))
        prefs["prefer_it_ops"] = st.checkbox("Prefer IT Ops / Infrastructure", value=bool(prefs["prefer_it_ops"]))
        prefs["prefer_cloud_ops"] = st.checkbox("Prefer Cloud Operations", value=bool(prefs["prefer_cloud_ops"]))
        prefs["prefer_m365_identity"] = st.checkbox("Prefer M365 / Identity", value=bool(prefs["prefer_m365_identity"]))
        prefs["prefer_erp_industrial"] = st.checkbox("Prefer ERP / Industrial App Support", value=bool(prefs["prefer_erp_industrial"]))

    if st.button("Save preferences", type="primary"):
        save_preferences(PREFS_PATH, prefs)
        st.success(f"Saved: {PREFS_PATH}")

with tab_capture:
    st.subheader("Capture")
    st.warning(
        "Before clicking Run Capture: open LinkedIn Jobs, set filters manually, keep the left list/right panel visible. "
        "After clicking the button, use the countdown to move the mouse over the RIGHT side of the FIRST visible job card."
    )
    pages_to_capture = st.number_input("Pages to capture", min_value=1, max_value=10, value=2, step=1)
    run_phase2 = st.checkbox("Run Phase 2 raw text capture", value=True)

    if st.button("Run Capture v35.10/v24", type="primary"):
        with st.spinner("Running capture. Use the countdown to move the mouse to LinkedIn, then do not touch mouse/keyboard."):
            code, output = run_capture(CAPTURE_SCRIPT, int(pages_to_capture), bool(run_phase2))
        render_process_output("Capture", output)
        if code == 0:
            st.success("Capture completed.")
        else:
            st.error(f"Capture exited with code {code}.")

    st.divider()
    st.subheader("Parse latest raw capture")
    st.write("This uses the current parser runner: `scripts/run_after_capture_v34.py`.")
    if st.button("Parse latest capture"):
        with st.spinner("Running parser and splitter..."):
            code, output = run_parser(PARSER_RUNNER)
        render_process_output("Parser", output)
        if code == 0:
            st.success("Parsing completed.")
        else:
            st.error(f"Parser exited with code {code}.")

with tab_classify:
    st.subheader("Classify, dedupe and export reviewable jobs for Tracker_v2")
    parsed_files = parsed_csv_files()
    parsed_options = [str(p) for p in parsed_files]
    default_idx = 0
    if parsed_options:
        selected_path = st.selectbox("Parsed CSV to classify", parsed_options, index=default_idx)
    else:
        selected_path = ""
        st.warning("No parsed CSV found yet.")

    uploaded_parsed = st.file_uploader(
        "Or browse/select a parsed CSV manually",
        type=["csv"],
        help="Useful when the parsed CSV is outside the default project folders. The selected file is copied into manual_inputs/.",
        key="parsed_csv_upload",
    )
    uploaded_parsed_path = save_uploaded_csv(uploaded_parsed, "parsed") if uploaded_parsed else None
    if uploaded_parsed_path:
        st.info(f"Manual parsed CSV copied to: {uploaded_parsed_path}")
    input_path = st.text_input("Or paste parsed CSV path", value=str(uploaded_parsed_path or selected_path))

    st.markdown("#### Optional: existing tracker duplicate/status check")
    previous_tracker_path = st.text_input(
        "Existing Tracker_v2 CSV export path (optional)",
        value="",
        help="Use this to detect jobs already applied/discarded/tracked. Leave blank for first import or test runs.",
    )
    uploaded_previous = st.file_uploader(
        "Or browse/select existing tracker CSV manually",
        type=["csv"],
        help="Optional. The selected file is copied into manual_inputs/ and used for duplicate/status checks.",
        key="previous_tracker_upload",
    )
    uploaded_previous_path = save_uploaded_csv(uploaded_previous, "previous_tracker") if uploaded_previous else None
    if uploaded_previous_path:
        st.info(f"Manual previous tracker CSV copied to: {uploaded_previous_path}")
        previous_tracker_path = str(uploaded_previous_path)

    exclude_previous_matches = st.checkbox(
        "Exclude rows already actioned in existing tracker",
        value=True,
        help="If the previous tracker has Status other than Not started/New/Pending review, the row is kept in audit but excluded from the main import.",
    )

    st.markdown("#### Local persistent history")
    use_history = st.checkbox(
        "Use/update local job history master",
        value=True,
        help="Stores every captured job across batches, including discards, duplicates and imported rows.",
    )
    exclude_history_actioned = st.checkbox(
        "Exclude jobs already actioned in local history",
        value=True,
        help="Keeps jobs previously marked as applied/discarded/actioned out of the active import.",
    )
    exclude_seen_before = st.checkbox(
        "Exclude jobs already seen before even if not actioned",
        value=False,
        help="Use this later if you want only completely new reviewable jobs in each batch.",
    )
    dry_run = st.checkbox(
        "Dry run / do not update history master",
        value=False,
        help="Use this when testing classifier changes. It still reads history for matching, but does not write/update job_history_master.csv.",
    )
    backup_history = st.checkbox(
        "Back up history master before updating",
        value=True,
        help="Creates outputs/state/backups/job_history_master_<timestamp>.csv before writing history.",
    )
    st.caption(f"History master path: {HISTORY_MASTER}")

    st.markdown("#### Export options")
    batch_label = st.text_input(
        "Batch label",
        value="",
        placeholder="Example: LinkedIn Remote Spain - 2026-05-18",
        help="Optional label written to Review Batch so you can identify where this group came from.",
    )
    create_simple_export = st.checkbox(
        "Create simplified tracker import CSV",
        value=True,
        help="Also writes tracker_simple_import_<timestamp>.csv with only the practical columns for the simplified tracker.",
    )

    latest_parsed_now = latest_parsed_csv()
    if input_path and latest_parsed_now and Path(input_path) != latest_parsed_now:
        st.warning(f"Selected parsed CSV is not the latest parsed file. Latest is: {latest_parsed_now.name}")
    st.caption("Tip: the latest parsed file may contain a different capture batch. Check row count before importing into Tracker_v2.")

    if st.button("Classify selected parsed CSV", type="primary"):
        if not input_path:
            st.error("No parsed CSV selected.")
        else:
            in_csv = Path(input_path)
            if not in_csv.exists():
                st.error(f"File not found: {in_csv}")
            else:
                save_preferences(PREFS_PATH, prefs)
                stamp = dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                out_csv = GSHEET_DIR / f"tracker_v2_import_{stamp}.csv"
                simple_csv = GSHEET_DIR / f"tracker_simple_import_{stamp}.csv" if create_simple_export else None
                report_md = REPORTS_DIR / f"classification_report_{stamp}.md"
                prev_path = Path(previous_tracker_path) if previous_tracker_path.strip() else None
                result = classify_csv(
                    in_csv,
                    out_csv,
                    report_md,
                    prefs,
                    previous_tracker_csv=prev_path,
                    exclude_previous_matches=bool(exclude_previous_matches),
                    history_master_csv=HISTORY_MASTER if use_history else None,
                    exclude_seen_before=bool(exclude_seen_before),
                    exclude_history_actioned=bool(exclude_history_actioned),
                    update_history=bool(use_history and not dry_run),
                    history_backup=bool(backup_history),
                    review_batch_label=batch_label.strip(),
                    simple_output_csv=simple_csv,
                )
                st.success("Classification complete.")
                st.write("Tracker_v2 import CSV:", str(out_csv))
                st.write("Simple tracker import CSV:", result.get("simple_output_csv", ""))
                st.write("Full audit CSV:", result.get("full_output_csv", ""))
                st.write("Discard archive CSV:", result.get("discard_archive_csv", ""))
                st.write("Duplicate archive CSV:", result.get("duplicate_archive_csv", ""))
                st.write("Previous matches archive CSV:", result.get("previous_archive_csv", ""))
                st.write("LinkedIn applied archive CSV:", result.get("linkedin_applied_archive_csv", ""))
                st.write("History master CSV:", result.get("history_master_csv", ""))
                st.write("History backup CSV:", result.get("history_backup_csv", ""))
                st.write("History update mode:", result.get("history_update_mode", ""))
                st.write("Review batch:", result.get("review_batch", ""))
                st.write("Report:", str(report_md))
                render_recommended_next_action(result, out_csv)
                render_false_positive_warnings(result)

                counts = result["decision_counts"]
                import_counts = result.get("import_decision_counts", {})
                c1, c2, c3, c4, c5, c6, c7, c8, c9, c10 = st.columns(10)
                c1.metric("Import rows", result["total"])
                c2.metric("A", import_counts.get("A", 0))
                c3.metric("B", import_counts.get("B", 0))
                c4.metric("C", import_counts.get("C", 0))
                c5.metric("Excluded D", result.get("excluded_auto_discard", 0))
                c6.metric("Manual review", result["manual_review"])
                c7.metric("Duplicate rows", result.get("duplicate_rows", 0))
                c8.metric("Previous matches", result.get("previous_matches", 0))
                c9.metric("History matches", result.get("history_matches", 0))
                c10.metric("LinkedIn applied", result.get("linkedin_applied_rows", 0))
                st.caption(
                    f"Source rows: {result.get('source_total', result['total'])} | "
                    f"Classified unique rows: {result.get('classified_total', result['total'])} | "
                    f"Tracker_v2 exported rows: {result['total']} | "
                    f"All D rows in full batch: {counts.get('D', 0)} | "
                    f"Duplicate groups: {result.get('duplicate_groups', 0)} | "
                    f"Previous actioned excluded: {result.get('previous_actioned_excluded', 0)} | "
                    f"History matches: {result.get('history_matches', 0)} | "
                    f"History rows: {result.get('history_total', 0)} | "
                    f"LinkedIn applied excluded: {result.get('linkedin_applied_rows', 0)}"
                )

                if result["total"] > 100:
                    st.warning("Large review batch detected. Import into a staging tab first, then merge to the main tracker.")
                if result.get("excluded_auto_discard", 0):
                    st.info("Deterministic auto-discard rows are excluded from the Tracker_v2 import. They are kept in the full audit and discard archive CSVs only.")
                if result.get("duplicate_rows", 0):
                    st.info("Duplicate/near-duplicate rows were excluded from the main import. Check the duplicate archive if needed.")
                if result.get("previous_actioned_excluded", 0):
                    st.info("Rows already actioned in the existing tracker were excluded from the main import and kept in the previous matches archive.")
                if result.get("history_matches", 0):
                    st.info("Some rows were already present in the local history master. Use the history exclusion options depending on whether you want only brand-new jobs.")
                if result.get("linkedin_applied_rows", 0):
                    st.info("Rows detected as already applied on LinkedIn were excluded from the main import and kept in the LinkedIn applied archive.")

                preview_cols = ["decision", "fit_score", "company", "job_title", "location", "resume_version", "red_flags", "duplicate_status", "duplicate_group", "history_seen_before", "history_match_type", "linkedin_card_state", "recommended_action", "manual_review", "url"]
                priority = {"A": 0, "B": 1, "C": 2, "D": 3}
                sorted_preview_rows = sorted(result["rows"], key=lambda r: (priority.get(r.get("decision", "D"), 9), -int(r.get("fit_score", "0") or 0)))
                preview = [{k: r.get(k, "") for k in preview_cols} for r in sorted_preview_rows]
                st.dataframe(preview, width="stretch", hide_index=True)

                with out_csv.open("rb") as f:
                    st.download_button("Download Tracker_v2 review import CSV", f, file_name=out_csv.name, mime="text/csv")
                simple_path_text = result.get("simple_output_csv") or ""
                if simple_path_text and Path(simple_path_text).exists():
                    with Path(simple_path_text).open("rb") as f:
                        st.download_button("Download simplified tracker import CSV", f, file_name=Path(simple_path_text).name, mime="text/csv")
                with report_md.open("rb") as f:
                    st.download_button("Download classification report", f, file_name=report_md.name, mime="text/markdown")

with tab_files:
    st.subheader("Local files")
    render_latest_batch_summary()
    st.divider()
    st.write("Latest raw JSONL:", str(latest_raw_jsonl() or ""))
    st.write("Latest parsed CSV:", str(latest_parsed_csv() or ""))
    st.write("Analysis pages:")
    for p in latest_analysis_pages():
        st.write("-", str(p))
    st.write("Latest simple tracker import:", str(latest_file(GSHEET_DIR / "tracker_simple_import_*.csv") or ""))
    st.write("Tracker_v2 imports folder:", str(GSHEET_DIR))
    st.write("Manual inputs folder:", str(MANUAL_INPUTS_DIR))
    st.write("Reports folder:", str(REPORTS_DIR))
    st.write("History master:", str(HISTORY_MASTER))
