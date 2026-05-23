# LinkedIn Job Pipeline Clean v4 Restored

This package restores the known-working capture baseline from the previous project and adds the improved conservative parser.

## Included

- `linkedin_capture_v20_two_phase_slow.py`
  - Restored byte-for-byte from the uploaded previous project ZIP.
  - Keeps the original two-phase capture behaviour.
  - Keeps the scrollbar drag behaviour used when no more full cards are visible in the current viewport.

- `scripts/linkedin_parse_v27_conservative_pages.py`
  - Based on parser v26.
  - Preserves `page_number`, `page_start`, `viewport_index`, and `card_index` from v20 raw JSONL.

- `scripts/linkedin_split_parsed_by_page.py`
  - Splits the parsed CSV by real `page_number` when available.
  - Falls back to fixed-size chunks only if no page metadata exists.

- `scripts/run_after_capture.py`
  - Finds the latest v20 JSONL.
  - Runs parser v27.
  - Splits the parsed CSV into upload-friendly files.

## Typical flow

1. Open LinkedIn Jobs in the browser.
2. Run `linkedin_capture_v20_two_phase_slow.py`.
3. Run `scripts/run_after_capture.py`.
4. Upload the generated files from `captures_id/analysis_pages/` one by one in the analysis chat.
