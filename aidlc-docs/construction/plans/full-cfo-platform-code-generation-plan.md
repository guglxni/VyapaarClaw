# Code Generation Plan — full-cfo-platform (Phase 3)

## Checklist

- [x] `cfo/einvoice.py`
- [x] `cfo/invoice_ocr.py`
- [x] `cfo/forecaster_darts.py` + numpy fallback in forecaster
- [x] `cfo/fraud.py` structural scoring + PyGOD hook
- [x] Postgres migrations: payout_workflows, ledger_entries
- [x] Workflow persistence (set_workflow_store, persist_workflow)
- [x] Ledger persistence (persist_journal_entry)
- [x] MCP tools: validate_einvoice, extract_invoice_data, detect_fraud_network_ml
- [x] Optional cfo-advanced deps
- [x] 350 tests passing
