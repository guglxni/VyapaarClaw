"""Tests for CFO Intelligence Layer modules."""

from __future__ import annotations

import datetime as dt
from typing import Any

import httpx
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
# Currency Tests
# ================================================================


class TestCurrency:
    """Tests for Frankfurter currency conversion helpers."""

    @pytest.mark.asyncio
    async def test_get_exchange_rate_normalizes_inputs(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from vyapaar_mcp.cfo import currency

        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(
                200,
                json={"date": "2025-01-15", "rates": {"INR": 83.25}},
                request=request,
            )

        transport = httpx.MockTransport(handler)
        real_async_client = httpx.AsyncClient
        monkeypatch.setattr(
            currency.httpx,
            "AsyncClient",
            lambda **kwargs: real_async_client(transport=transport, **kwargs),
        )

        result = await currency.get_exchange_rate("usd", "inr", date="2025-01-15")

        assert result == {
            "base": "USD",
            "target": "INR",
            "rate": 83.25,
            "date": "2025-01-15",
            "source": "Frankfurter (ECB)",
        }
        assert requests[0].url.path == "/2025-01-15"
        assert requests[0].url.params["base"] == "USD"
        assert requests[0].url.params["symbols"] == "INR"

    @pytest.mark.asyncio
    async def test_convert_amount_same_currency_short_circuits(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from vyapaar_mcp.cfo import currency

        async def fail_if_called(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
            raise AssertionError("get_exchange_rate should not be called")

        monkeypatch.setattr(currency, "get_exchange_rate", fail_if_called)

        result = await currency.convert_amount(125.5, "inr", "INR")

        assert result["converted_amount"] == 125.5
        assert result["rate"] == 1.0
        assert result["date"] == "latest"

    @pytest.mark.asyncio
    async def test_convert_amount_raises_when_rate_missing(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from vyapaar_mcp.cfo import currency

        async def no_rate(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
            return {"rate": None, "date": "2025-01-15", "source": "Frankfurter (ECB)"}

        monkeypatch.setattr(currency, "get_exchange_rate", no_rate)

        with pytest.raises(ValueError, match="No rate found"):
            await currency.convert_amount(100, "USD", "INR")

    @pytest.mark.asyncio
    async def test_convert_amount_applies_exchange_rate(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from vyapaar_mcp.cfo import currency

        async def fixed_rate(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
            return {"rate": 83.456, "date": "2025-01-15", "source": "Frankfurter (ECB)"}

        monkeypatch.setattr(currency, "get_exchange_rate", fixed_rate)

        result = await currency.convert_amount(10, "usd", "inr")

        assert result == {
            "original_amount": 10,
            "original_currency": "USD",
            "converted_amount": 834.56,
            "converted_currency": "INR",
            "rate": 83.456,
            "date": "2025-01-15",
            "source": "Frankfurter (ECB)",
        }

    @pytest.mark.asyncio
    async def test_get_supported_currencies(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from vyapaar_mcp.cfo import currency

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/currencies"
            return httpx.Response(
                200,
                json={"USD": "US Dollar", "INR": "Indian Rupee"},
                request=request,
            )

        transport = httpx.MockTransport(handler)
        real_async_client = httpx.AsyncClient
        monkeypatch.setattr(
            currency.httpx,
            "AsyncClient",
            lambda **kwargs: real_async_client(transport=transport, **kwargs),
        )

        assert await currency.get_supported_currencies() == {
            "USD": "US Dollar",
            "INR": "Indian Rupee",
        }


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
            {
                "agent_id": "agent1",
                "vendor_name": "Vendor A",
                "amount_paise": 10000,
                "pan": "ABCDE1234F",
            },
            {
                "agent_id": "agent1",
                "vendor_name": "Vendor B",
                "amount_paise": 20000,
                "pan": "ABCDE1234F",
            },
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

        result = analyze_contract_text(
            "This agreement shall automatically renew for successive 1-year terms."
        )
        assert result["has_auto_renewal"] is True

    def test_clean_contract(self) -> None:
        from vyapaar_mcp.cfo.contracts import analyze_contract_text

        result = analyze_contract_text("Simple service agreement without special clauses.")
        assert result["risk_level"] == "low"


# ================================================================
# Report Generation Tests
# ================================================================


class TestReports:
    """Tests for PDF compliance report generation."""

    def test_generate_governance_report_writes_pdf_with_optional_sections(self, tmp_path) -> None:
        from vyapaar_mcp.cfo.reports import generate_governance_report

        output_path = tmp_path / "governance" / "report.pdf"
        summary = {
            "budget_summary": {
                "total_budget_paise": 1_000_000,
                "utilized_paise": 250_000,
                "remaining_paise": 750_000,
                "utilization_percent": 25,
            },
            "risk_summary": {
                "total_reviewed": 4,
                "anomalies_detected": 1,
                "payouts_held": 1,
                "payouts_rejected": 0,
            },
            "forecast": {"severity": "warning", "runway_days": 14},
            "recent_transactions": [
                {
                    "date": "2025-01-15",
                    "vendor": "Acme Cloud Services",
                    "amount_paise": 123_456,
                    "category": "saas",
                    "status": "approved",
                }
            ],
            "gst_compliance": {
                "validated": 3,
                "invalid": 1,
                "total_gst_paise": 22_222,
            },
            "fraud_detection": {
                "patterns_found": 1,
                "risk_level": "medium",
                "findings": [
                    {
                        "type": "shared_pan",
                        "severity": "medium",
                        "description": "Two vendors share the same PAN",
                    }
                ],
            },
        }

        result = generate_governance_report(summary, str(output_path))

        assert result == str(output_path)
        assert output_path.exists()
        assert output_path.read_bytes().startswith(b"%PDF")
        assert output_path.stat().st_size > 1_000


# ================================================================
# Sanctions Tests
# ================================================================


class TestSanctions:
    """Tests for OpenSanctions screening and vendor scoring."""

    @pytest.mark.asyncio
    async def test_screen_against_sanctions_rate_limited(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from vyapaar_mcp.cfo import sanctions

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(429, request=request)

        transport = httpx.MockTransport(handler)
        real_async_client = httpx.AsyncClient
        monkeypatch.setattr(
            sanctions.httpx,
            "AsyncClient",
            lambda **kwargs: real_async_client(transport=transport, **kwargs),
        )

        result = await sanctions.screen_against_sanctions("Acme Ltd")

        assert result["screened"] is False
        assert result["risk_level"] == "unknown"
        assert "Rate limited" in result["error"]

    @pytest.mark.asyncio
    async def test_screen_against_sanctions_api_error_status(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from vyapaar_mcp.cfo import sanctions

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503, request=request)

        transport = httpx.MockTransport(handler)
        real_async_client = httpx.AsyncClient
        monkeypatch.setattr(
            sanctions.httpx,
            "AsyncClient",
            lambda **kwargs: real_async_client(transport=transport, **kwargs),
        )

        result = await sanctions.screen_against_sanctions("Acme Ltd")

        assert result["screened"] is False
        assert result["error"] == "API returned 503"
        assert result["risk_level"] == "unknown"

    @pytest.mark.asyncio
    async def test_screen_against_sanctions_clear_result(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from vyapaar_mcp.cfo import sanctions

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"results": []}, request=request)

        transport = httpx.MockTransport(handler)
        real_async_client = httpx.AsyncClient
        monkeypatch.setattr(
            sanctions.httpx,
            "AsyncClient",
            lambda **kwargs: real_async_client(transport=transport, **kwargs),
        )

        result = await sanctions.screen_against_sanctions("Acme Ltd")

        assert result == {
            "screened": True,
            "entity": "Acme Ltd",
            "matches": 0,
            "risk_level": "clear",
            "details": [],
        }

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("score", "risk_level", "recommendation"),
        [
            (0.7, "high", "REVIEW"),
            (0.4, "medium", "REVIEW"),
            (0.2, "low", "PASS"),
        ],
    )
    async def test_screen_against_sanctions_risk_bands(
        self,
        monkeypatch: pytest.MonkeyPatch,
        score: float,
        risk_level: str,
        recommendation: str,
    ) -> None:
        from vyapaar_mcp.cfo import sanctions

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={"results": [{"caption": "Possible Match", "score": score}]},
                request=request,
            )

        transport = httpx.MockTransport(handler)
        real_async_client = httpx.AsyncClient
        monkeypatch.setattr(
            sanctions.httpx,
            "AsyncClient",
            lambda **kwargs: real_async_client(transport=transport, **kwargs),
        )

        result = await sanctions.screen_against_sanctions("Possible Match")

        assert result["risk_level"] == risk_level
        assert result["recommendation"].startswith(recommendation)
        assert result["max_match_score"] == score

    @pytest.mark.asyncio
    async def test_screen_against_sanctions_formats_critical_match(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from vyapaar_mcp.cfo import sanctions

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/match/default"
            assert request.url.params["q"] == "Blocked Vendor"
            assert request.url.params["schema"] == "Company"
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "caption": "Blocked Vendor LLC",
                            "score": 0.91,
                            "schema": "Company",
                            "datasets": [{"name": "OFAC SDN"}],
                            "properties": {
                                "country": ["US"],
                                "topics": ["sanction"],
                                "notes": ["not returned"],
                            },
                        }
                    ]
                },
                request=request,
            )

        transport = httpx.MockTransport(handler)
        real_async_client = httpx.AsyncClient
        monkeypatch.setattr(
            sanctions.httpx,
            "AsyncClient",
            lambda **kwargs: real_async_client(transport=transport, **kwargs),
        )

        result = await sanctions.screen_against_sanctions("Blocked Vendor")

        assert result["screened"] is True
        assert result["matches"] == 1
        assert result["max_match_score"] == 0.91
        assert result["risk_level"] == "critical"
        assert result["recommendation"].startswith("BLOCK")
        assert result["details"][0]["datasets"] == ["OFAC SDN"]
        assert result["details"][0]["properties"] == {
            "country": ["US"],
            "topics": ["sanction"],
        }

    @pytest.mark.asyncio
    async def test_screen_against_sanctions_handles_http_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from vyapaar_mcp.cfo import sanctions

        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("network down", request=request)

        transport = httpx.MockTransport(handler)
        real_async_client = httpx.AsyncClient
        monkeypatch.setattr(
            sanctions.httpx,
            "AsyncClient",
            lambda **kwargs: real_async_client(transport=transport, **kwargs),
        )

        result = await sanctions.screen_against_sanctions("Acme Ltd")

        assert result["screened"] is False
        assert result["risk_level"] == "unknown"
        assert result["error"] == "network down"

    @pytest.mark.asyncio
    async def test_comprehensive_vendor_screen_scores_components(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from vyapaar_mcp.cfo import sanctions, tax

        async def sanctions_clear(_vendor_name: str) -> dict[str, Any]:
            return {"screened": True, "max_match_score": 0.25, "risk_level": "low"}

        monkeypatch.setattr(sanctions, "screen_against_sanctions", sanctions_clear)
        monkeypatch.setattr(tax, "validate_gstin", lambda _gstin: {"valid": True})

        result = await sanctions.comprehensive_vendor_screen(
            "Acme Ltd",
            vendor_url="https://acme.test",
            gstin="27AAPFU0939F1ZV",
        )

        assert result["trust_score"] == 0.85
        assert result["trust_level"] == "trusted"
        assert result["component_scores"] == {"sanctions": 0.75, "gstin": 1.0}
        assert result["recommendation"].startswith("✅")

    @pytest.mark.asyncio
    async def test_comprehensive_vendor_screen_unknown_without_gstin_is_review(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from vyapaar_mcp.cfo import sanctions

        async def sanctions_unknown(_vendor_name: str) -> dict[str, Any]:
            return {"screened": False, "risk_level": "unknown"}

        monkeypatch.setattr(sanctions, "screen_against_sanctions", sanctions_unknown)

        result = await sanctions.comprehensive_vendor_screen("Acme Ltd")

        assert result["trust_score"] == 0.5
        assert result["trust_level"] == "review"
        assert result["component_scores"] == {"sanctions": 0.5, "gstin": 0.5}
        assert result["recommendation"].startswith("⚠️")

    @pytest.mark.asyncio
    async def test_comprehensive_vendor_screen_blocks_low_trust_vendor(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from vyapaar_mcp.cfo import sanctions, tax

        async def sanctions_hit(_vendor_name: str) -> dict[str, Any]:
            return {"screened": True, "max_match_score": 0.9, "risk_level": "critical"}

        monkeypatch.setattr(sanctions, "screen_against_sanctions", sanctions_hit)
        monkeypatch.setattr(tax, "validate_gstin", lambda _gstin: {"valid": False})

        result = await sanctions.comprehensive_vendor_screen("Blocked Ltd", gstin="bad")

        assert result["trust_score"] == 0.06
        assert result["trust_level"] == "blocked"
        assert result["component_scores"] == {
            "sanctions": pytest.approx(0.1),
            "gstin": 0.0,
        }
        assert result["recommendation"].startswith("🛑")
