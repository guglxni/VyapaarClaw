"""Tests for CFO Intelligence Layer modules."""

from __future__ import annotations

import datetime as dt
import pytest

# ================================================================
# Calendar Tests
# ================================================================


class TestCalendar:
    """Tests for Indian financial calendar module."""

    def test_weekend_not_business_day(self) -> None:
        from vyapaar_mcp.cfo.calendar import is_business_day

        saturday = dt.date(2025, 3, 15)  # Saturday
        sunday = dt.date(2025, 3, 16)  # Sunday
        assert not is_business_day(saturday)
        assert not is_business_day(sunday)

    def test_weekday_is_business_day(self) -> None:
        from vyapaar_mcp.cfo.calendar import is_business_day

        # Assuming a random weekday that's not a holiday
        monday = dt.date(2025, 3, 10)
        assert is_business_day(monday)

    def test_next_business_day_from_weekend(self) -> None:
        from vyapaar_mcp.cfo.calendar import next_business_day

        saturday = dt.date(2025, 3, 15)
        nbd = next_business_day(saturday)
        assert nbd.weekday() < 5  # Must be a weekday

    def test_settlement_date_t_plus_1(self) -> None:
        from vyapaar_mcp.cfo.calendar import settlement_date

        monday = dt.date(2025, 3, 10)
        settled = settlement_date(monday, t_plus=1)
        assert settled > monday

    def test_business_days_between(self) -> None:
        from vyapaar_mcp.cfo.calendar import business_days_between

        monday = dt.date(2025, 3, 10)
        friday = dt.date(2025, 3, 14)
        # Mon-Fri: Tue, Wed, Thu = 3 business days between (exclusive)
        count = business_days_between(monday, friday)
        assert count == 3

    def test_upcoming_holidays_returns_results(self) -> None:
        from vyapaar_mcp.cfo.calendar import upcoming_holidays

        holidays = upcoming_holidays(dt.date(2025, 1, 1), count=3)
        assert len(holidays) <= 3
        if holidays:
            assert "date" in holidays[0]
            assert "name" in holidays[0]


# ================================================================
# Tax Tests
# ================================================================


class TestTax:
    """Tests for GST & India tax compliance."""

    def test_valid_gstin_format(self) -> None:
        from vyapaar_mcp.cfo.tax import validate_gstin

        # Well-known format valid GSTIN
        result = validate_gstin("27AAPFU0939F1ZV")
        assert "gstin" in result
        assert result["state_code"] == "27"

    def test_invalid_gstin_format(self) -> None:
        from vyapaar_mcp.cfo.tax import validate_gstin

        result = validate_gstin("INVALID")
        assert result["valid"] is False

    def test_gstin_extracts_pan(self) -> None:
        from vyapaar_mcp.cfo.tax import validate_gstin

        result = validate_gstin("29ABCDE1234F1ZQ")
        if result["valid"]:
            assert result["pan"] == "ABCDE1234F"

    def test_calculate_gst_cgst_sgst(self) -> None:
        from vyapaar_mcp.cfo.tax import calculate_gst

        result = calculate_gst(100000, 18.0, is_igst=False)
        assert result["type"] == "CGST+SGST"
        assert result["cgst_paise"] + result["sgst_paise"] == 18000
        assert result["igst_paise"] == 0
        assert result["total_paise"] == 118000

    def test_calculate_gst_igst(self) -> None:
        from vyapaar_mcp.cfo.tax import calculate_gst

        result = calculate_gst(100000, 18.0, is_igst=True)
        assert result["type"] == "IGST"
        assert result["igst_paise"] == 18000

    def test_tds_below_threshold(self) -> None:
        from vyapaar_mcp.cfo.tax import check_tds_applicability

        result = check_tds_applicability(100000, "194C")  # ₹1000
        assert result["applicable"] is False
        assert result["tds_amount_paise"] == 0

    def test_tds_above_threshold(self) -> None:
        from vyapaar_mcp.cfo.tax import check_tds_applicability

        result = check_tds_applicability(5000000, "194C")  # ₹50,000
        assert result["applicable"] is True
        assert result["tds_amount_paise"] > 0


# ================================================================
# Bank Validation Tests
# ================================================================


class TestBankValidation:
    """Tests for IFSC and bank account validation."""

    def test_valid_ifsc(self) -> None:
        from vyapaar_mcp.cfo.bank import validate_ifsc

        result = validate_ifsc("SBIN0001234")
        assert result["valid"] is True
        assert result["bank_name"] == "State Bank of India"

    def test_invalid_ifsc_format(self) -> None:
        from vyapaar_mcp.cfo.bank import validate_ifsc

        result = validate_ifsc("INVALID")
        assert result["valid"] is False

    def test_ifsc_with_zero_5th_char(self) -> None:
        from vyapaar_mcp.cfo.bank import validate_ifsc

        result = validate_ifsc("HDFC0123456")
        assert result["valid"] is True

    def test_valid_account_number(self) -> None:
        from vyapaar_mcp.cfo.bank import validate_account_number

        result = validate_account_number("1234567890")
        assert result["valid"] is True

    def test_short_account_number(self) -> None:
        from vyapaar_mcp.cfo.bank import validate_account_number

        result = validate_account_number("12345")
        assert result["valid"] is False

    def test_fund_account_validation(self) -> None:
        from vyapaar_mcp.cfo.bank import validate_fund_account

        result = validate_fund_account("SBIN0001234", "1234567890", "Test User")
        assert result["valid"] is True
        assert len(result["errors"]) == 0


# ================================================================
# Categorizer Tests
# ================================================================


class TestCategorizer:
    """Tests for transaction categorization."""

    def test_categorize_saas(self) -> None:
        from vyapaar_mcp.cfo.categorizer import categorize_transaction

        result = categorize_transaction("Monthly AWS subscription payment")
        assert result["category"] == "saas_software"

    def test_categorize_salary(self) -> None:
        from vyapaar_mcp.cfo.categorizer import categorize_transaction

        result = categorize_transaction("Employee salary payment March")
        assert result["category"] == "salaries_wages"

    def test_categorize_unknown(self) -> None:
        from vyapaar_mcp.cfo.categorizer import categorize_transaction

        result = categorize_transaction("XYZ random transaction 123")
        assert "category" in result  # Should return miscellaneous


# ================================================================
# Forecaster Tests
# ================================================================


class TestForecaster:
    """Tests for cash flow forecasting."""

    def test_forecast_with_data(self) -> None:
        from vyapaar_mcp.cfo.forecaster import forecast_burn_rate

        daily_spends = [100000, 120000, 110000, 130000, 115000, 125000, 140000]
        result = forecast_burn_rate(daily_spends, 1000000, 7)

        assert "runway_days" in result
        assert "severity" in result
        assert "trend_direction" in result
        assert result["data_points"] == 7

    def test_forecast_empty_data(self) -> None:
        from vyapaar_mcp.cfo.forecaster import forecast_burn_rate

        result = forecast_burn_rate([], 1000000)
        assert result.get("error") is not None

    def test_anomaly_detection(self) -> None:
        from vyapaar_mcp.cfo.forecaster import detect_spending_anomaly

        normal_spends = [100000, 102000, 98000, 101000, 99000]
        result = detect_spending_anomaly(normal_spends, 500000)
        assert result["anomalous"] is True  # 5x above mean


# ================================================================
# Ledger Tests
# ================================================================


class TestLedger:
    """Tests for double-entry bookkeeping."""

    def test_balanced_entry(self) -> None:
        from vyapaar_mcp.cfo.ledger import Ledger

        ledger = Ledger()
        entry = ledger.record_entry(
            "Test entry",
            [
                {"account": "5000", "type": "debit", "amount_paise": 10000},
                {"account": "1100", "type": "credit", "amount_paise": 10000},
            ],
        )
        assert entry["total_debit_paise"] == entry["total_credit_paise"]

    def test_unbalanced_entry_raises(self) -> None:
        from vyapaar_mcp.cfo.ledger import Ledger

        ledger = Ledger()
        with pytest.raises(ValueError, match="does not balance"):
            ledger.record_entry(
                "Bad entry",
                [
                    {"account": "5000", "type": "debit", "amount_paise": 10000},
                    {"account": "1100", "type": "credit", "amount_paise": 5000},
                ],
            )

    def test_payout_recording(self) -> None:
        from vyapaar_mcp.cfo.ledger import Ledger

        ledger = Ledger()
        entry = ledger.record_payout(50000, "Vendor payment", "Acme Corp")
        assert entry["total_debit_paise"] == entry["total_credit_paise"]

    def test_trial_balance(self) -> None:
        from vyapaar_mcp.cfo.ledger import Ledger

        ledger = Ledger()
        ledger.record_payout(50000, "Test payout")
        tb = ledger.get_trial_balance()
        assert tb["balanced"] is True

    def test_income_statement(self) -> None:
        from vyapaar_mcp.cfo.ledger import Ledger

        ledger = Ledger()
        ledger.record_payout(50000, "Office supplies", category="vendor_supplies")
        income = ledger.get_income_statement()
        assert income["total_expenses_paise"] > 0


# ================================================================
# Fraud Detection Tests
# ================================================================


class TestFraudDetection:
    """Tests for graph-based fraud detection."""

    def test_no_fraud_in_normal_transactions(self) -> None:
        from vyapaar_mcp.cfo.fraud import detect_fraud_patterns

        txns = [
            {"agent_id": "agent1", "vendor_name": "Vendor A", "amount_paise": 10000},
            {"agent_id": "agent2", "vendor_name": "Vendor B", "amount_paise": 20000},
        ]
        result = detect_fraud_patterns(txns)
        assert result["risk_level"] in ("low", "medium")

    def test_shared_pan_detection(self) -> None:
        from vyapaar_mcp.cfo.fraud import detect_fraud_patterns

        txns = [
            {"agent_id": "agent1", "vendor_name": "Vendor A", "amount_paise": 10000, "pan": "ABCDE1234F"},
            {"agent_id": "agent1", "vendor_name": "Vendor B", "amount_paise": 20000, "pan": "ABCDE1234F"},
        ]
        result = detect_fraud_patterns(txns)
        shared_pan_findings = [f for f in result["findings"] if f["type"] == "shared_pan"]
        assert len(shared_pan_findings) > 0

    def test_empty_transactions(self) -> None:
        from vyapaar_mcp.cfo.fraud import detect_fraud_patterns

        result = detect_fraud_patterns([])
        assert result["patterns_found"] == 0


# ================================================================
# Workflow Tests
# ================================================================


class TestWorkflow:
    """Tests for payout approval state machine."""

    def test_create_workflow(self) -> None:
        from vyapaar_mcp.cfo.workflow import PayoutWorkflow

        wf = PayoutWorkflow(payout_id="test1", amount_paise=50000)
        assert wf.state == "queued"  # type: ignore[attr-defined]

    def test_happy_path(self) -> None:
        from vyapaar_mcp.cfo.workflow import PayoutWorkflow

        wf = PayoutWorkflow(payout_id="test2")
        wf.start_review()  # type: ignore[call-arg]
        wf.pass_policy()  # type: ignore[call-arg]
        wf.pass_reputation()  # type: ignore[call-arg]
        wf.pass_anomaly()  # type: ignore[call-arg]
        assert wf.state == "approved"  # type: ignore[attr-defined]

    def test_hold_and_escalation(self) -> None:
        from vyapaar_mcp.cfo.workflow import PayoutWorkflow

        wf = PayoutWorkflow(payout_id="test3")
        wf.start_review()  # type: ignore[call-arg]
        wf.hold()  # type: ignore[call-arg]
        assert wf.state == "held"  # type: ignore[attr-defined]
        wf.escalate_l1()  # type: ignore[call-arg]
        assert wf.state == "pending_l1_approval"  # type: ignore[attr-defined]
        wf.approve_l1()  # type: ignore[call-arg]
        assert wf.state == "approved"  # type: ignore[attr-defined]

    def test_rejection(self) -> None:
        from vyapaar_mcp.cfo.workflow import PayoutWorkflow

        wf = PayoutWorkflow(payout_id="test4")
        wf.start_review()  # type: ignore[call-arg]
        wf.reject()  # type: ignore[call-arg]
        assert wf.state == "rejected"  # type: ignore[attr-defined]

    def test_transition_history(self) -> None:
        from vyapaar_mcp.cfo.workflow import PayoutWorkflow

        wf = PayoutWorkflow(payout_id="test5")
        wf.start_review()  # type: ignore[call-arg]
        wf.pass_policy()  # type: ignore[call-arg]
        assert len(wf.history) == 2


# ================================================================
# Contract Analysis Tests
# ================================================================


class TestContractAnalysis:
    """Tests for contract analysis."""

    def test_extract_payment_terms(self) -> None:
        from vyapaar_mcp.cfo.contracts import analyze_contract_text

        result = analyze_contract_text("Payment terms: Net 30 days from invoice date.")
        assert result["payment_terms_days"] == 30

    def test_detect_penalty_clause(self) -> None:
        from vyapaar_mcp.cfo.contracts import analyze_contract_text

        result = analyze_contract_text("Late payment fee: 2% per month on outstanding amounts.")
        assert result["has_penalty"] is True

    def test_detect_auto_renewal(self) -> None:
        from vyapaar_mcp.cfo.contracts import analyze_contract_text

        result = analyze_contract_text("This agreement shall automatically renew for successive 1-year terms.")
        assert result["has_auto_renewal"] is True

    def test_clean_contract(self) -> None:
        from vyapaar_mcp.cfo.contracts import analyze_contract_text

        result = analyze_contract_text("Simple service agreement without special clauses.")
        assert result["risk_level"] == "low"
