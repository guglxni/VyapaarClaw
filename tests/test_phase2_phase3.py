"""Tests for Phase 2 and Phase 3 enhancements."""

from __future__ import annotations

import pytest

from vyapaar_mcp.cfo.einvoice import validate_einvoice_bundle, validate_irn
from vyapaar_mcp.cfo.gst_providers import (
    FormatGstProvider,
    GstVerificationChain,
    _fuzzy_name_match,
)
from vyapaar_mcp.reputation.adverse_media import screen_adverse_media
from vyapaar_mcp.research.exa_client import ExaClient


class TestGstProviders:
    @pytest.mark.asyncio
    async def test_format_provider_valid_gstin(self) -> None:
        provider = FormatGstProvider()
        result = await provider.verify("27AAPFU0939F1ZV")
        assert result["valid"] is True
        assert result["recommendation"] == "PASS"

    @pytest.mark.asyncio
    async def test_format_provider_invalid_gstin(self) -> None:
        provider = FormatGstProvider()
        result = await provider.verify("BAD")
        assert result["valid"] is False
        assert result["recommendation"] == "REJECT"

    @pytest.mark.asyncio
    async def test_verification_chain(self) -> None:
        chain = GstVerificationChain([FormatGstProvider()])
        result = await chain.verify("27AAPFU0939F1ZV", "Acme Corp")
        assert result["valid"] is True

    def test_fuzzy_name_match(self) -> None:
        assert _fuzzy_name_match("Acme Technologies Pvt Ltd", "ACME TECHNOLOGIES PRIVATE LIMITED")
        assert not _fuzzy_name_match("Totally Different Co", "ACME TECHNOLOGIES")


class TestExaClient:
    def test_unconfigured_client(self) -> None:
        client = ExaClient(api_key="")
        assert not client.configured

    @pytest.mark.asyncio
    async def test_unconfigured_search(self) -> None:
        client = ExaClient(api_key="")
        result = await client.search("test query")
        assert "error" in result
        assert result["results"] == []


class TestAdverseMedia:
    @pytest.mark.asyncio
    async def test_unconfigured_screening(self) -> None:
        result = await screen_adverse_media("Test Vendor", exa_client=None)
        assert result["screened"] is False
        assert result["risk_level"] == "unknown"


class TestEinvoice:
    def test_valid_irn_format(self) -> None:
        irn = "a" * 64
        assert validate_irn(irn)["valid"] is True

    def test_invalid_irn_format(self) -> None:
        assert validate_irn("short")["valid"] is False

    def test_einvoice_bundle_requires_reference(self) -> None:
        result = validate_einvoice_bundle()
        assert result["valid"] is False
        assert any("IRN" in e or "ack" in e for e in result["errors"])


class TestFraudEnhancement:
    def test_structural_anomaly_score(self) -> None:
        from vyapaar_mcp.cfo.fraud import detect_fraud_patterns

        txns = [
            {"agent_id": "a1", "vendor_name": "v1", "amount_paise": 10000, "pan": "AAAAA1111A"},
            {"agent_id": "a2", "vendor_name": "v2", "amount_paise": 20000, "pan": "AAAAA1111A"},
            {"agent_id": "a3", "vendor_name": "v3", "amount_paise": 30000},
        ]
        result = detect_fraud_patterns(txns)
        assert "structural_anomaly_score" in result
        assert result["patterns_found"] >= 1

    def test_ml_fraud_fallback(self) -> None:
        from vyapaar_mcp.cfo.fraud import detect_fraud_with_ml

        result = detect_fraud_with_ml([])
        assert result["ml_engine"] == "networkx"
