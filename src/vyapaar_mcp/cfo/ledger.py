"""Double-Entry Bookkeeping Engine.

A minimal but correct double-entry ledger. Every VyapaarClaw payout
generates a journal entry that keeps the books balanced.

Accounting equation:  Assets = Liabilities + Equity
Every transaction has equal debits and credits.
"""

from __future__ import annotations

import datetime as _dt
import uuid
from enum import Enum
from typing import Any


class AccountType(str, Enum):
    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    REVENUE = "revenue"
    EXPENSE = "expense"


class DebitCredit(str, Enum):
    DEBIT = "debit"
    CREDIT = "credit"


# ---------------------------------------------------------------------------
# Chart of Accounts (India-typical)
# ---------------------------------------------------------------------------

_DEFAULT_CHART: dict[str, dict[str, Any]] = {
    "1000": {"name": "Cash & Bank", "type": AccountType.ASSET},
    "1100": {"name": "Razorpay Balance", "type": AccountType.ASSET},
    "1200": {"name": "Accounts Receivable", "type": AccountType.ASSET},
    "2000": {"name": "Accounts Payable", "type": AccountType.LIABILITY},
    "2100": {"name": "GST Payable", "type": AccountType.LIABILITY},
    "2200": {"name": "TDS Payable", "type": AccountType.LIABILITY},
    "3000": {"name": "Owner's Equity", "type": AccountType.EQUITY},
    "3100": {"name": "Retained Earnings", "type": AccountType.EQUITY},
    "4000": {"name": "Revenue", "type": AccountType.REVENUE},
    "5000": {"name": "Vendor Payments", "type": AccountType.EXPENSE},
    "5100": {"name": "SaaS & Software", "type": AccountType.EXPENSE},
    "5200": {"name": "Professional Services", "type": AccountType.EXPENSE},
    "5300": {"name": "Salaries & Wages", "type": AccountType.EXPENSE},
    "5400": {"name": "Marketing & Advertising", "type": AccountType.EXPENSE},
    "5500": {"name": "Utilities & Rent", "type": AccountType.EXPENSE},
    "5600": {"name": "Travel & Transport", "type": AccountType.EXPENSE},
    "5900": {"name": "Miscellaneous Expenses", "type": AccountType.EXPENSE},
}


class Ledger:
    """In-memory double-entry ledger.

    In production, entries would be persisted to PostgreSQL.
    This implementation provides the accounting engine that
    can be wired to any storage backend.
    """

    def __init__(self) -> None:
        self.chart = dict(_DEFAULT_CHART)
        self.journal: list[dict[str, Any]] = []
        self.balances: dict[str, int] = {code: 0 for code in self.chart}

    def add_account(self, code: str, name: str, account_type: AccountType) -> None:
        """Add or update an account in the chart."""
        self.chart[code] = {"name": name, "type": account_type}
        if code not in self.balances:
            self.balances[code] = 0

    def record_entry(
        self,
        description: str,
        entries: list[dict[str, Any]],
        reference: str = "",
        date: _dt.date | None = None,
    ) -> dict[str, Any]:
        """Record a journal entry (must balance: total debits == total credits).

        Args:
            description: Human-readable description.
            entries: List of {"account": code, "type": "debit"|"credit", "amount_paise": int}.
            reference: External reference (e.g., Razorpay payout ID).
            date: Entry date (defaults to today).

        Returns:
            The recorded journal entry with ID.
        """
        total_debit = sum(e["amount_paise"] for e in entries if e["type"] == "debit")
        total_credit = sum(e["amount_paise"] for e in entries if e["type"] == "credit")

        if total_debit != total_credit:
            raise ValueError(
                f"Journal entry does not balance: debits={total_debit} ≠ credits={total_credit}"
            )

        entry_id = str(uuid.uuid4())[:8]
        entry_date = date or _dt.date.today()

        journal_entry = {
            "id": entry_id,
            "date": entry_date.isoformat(),
            "description": description,
            "reference": reference,
            "lines": entries,
            "total_debit_paise": total_debit,
            "total_credit_paise": total_credit,
        }

        # Update balances
        for line in entries:
            account_code = line["account"]
            amount = line["amount_paise"]
            account_info = self.chart.get(account_code, {})
            account_type = account_info.get("type", AccountType.EXPENSE)

            # Normal balance: assets/expenses increase with debit
            # Liabilities/equity/revenue increase with credit
            if line["type"] == "debit":
                if account_type in (AccountType.ASSET, AccountType.EXPENSE):
                    self.balances[account_code] = self.balances.get(account_code, 0) + amount
                else:
                    self.balances[account_code] = self.balances.get(account_code, 0) - amount
            else:  # credit
                if account_type in (AccountType.LIABILITY, AccountType.EQUITY, AccountType.REVENUE):
                    self.balances[account_code] = self.balances.get(account_code, 0) + amount
                else:
                    self.balances[account_code] = self.balances.get(account_code, 0) - amount

        self.journal.append(journal_entry)
        return journal_entry

    def record_payout(
        self,
        amount_paise: int,
        description: str,
        vendor_name: str = "",
        category: str = "vendor_payments",
        payout_id: str = "",
        gst_paise: int = 0,
        tds_paise: int = 0,
    ) -> dict[str, Any]:
        """Convenience: record a vendor payout as a journal entry.

        Debit: Expense account (from category)
        Credit: Razorpay Balance
        Plus optional GST/TDS entries.
        """
        # Map category to expense account
        expense_accounts: dict[str, str] = {
            "vendor_payments": "5000",
            "saas_software": "5100",
            "professional_services": "5200",
            "salaries_wages": "5300",
            "marketing_advertising": "5400",
            "utilities_rent": "5500",
            "travel_transport": "5600",
            "miscellaneous": "5900",
        }
        expense_code = expense_accounts.get(category, "5000")

        entries: list[dict[str, Any]] = []
        net_amount = amount_paise

        # GST entries
        if gst_paise > 0:
            entries.append({
                "account": "2100",  # GST Payable
                "type": "debit",
                "amount_paise": gst_paise,
            })
            net_amount -= gst_paise

        # TDS entries
        if tds_paise > 0:
            entries.append({
                "account": "2200",  # TDS Payable
                "type": "credit",
                "amount_paise": tds_paise,
            })
            net_amount += tds_paise  # TDS reduces actual outflow

        # Main expense
        entries.append({
            "account": expense_code,
            "type": "debit",
            "amount_paise": amount_paise,
        })

        # Razorpay outflow
        entries.append({
            "account": "1100",  # Razorpay Balance
            "type": "credit",
            "amount_paise": amount_paise,
        })

        full_desc = f"Payout to {vendor_name}: {description}" if vendor_name else description

        return self.record_entry(
            description=full_desc,
            entries=entries,
            reference=payout_id,
        )

    def get_trial_balance(self) -> dict[str, Any]:
        """Generate a trial balance (all account balances)."""
        trial: list[dict[str, Any]] = []
        total_debit = 0
        total_credit = 0

        for code, balance in sorted(self.balances.items()):
            if balance == 0:
                continue
            account_info = self.chart.get(code, {})
            account_type = account_info.get("type", AccountType.EXPENSE)

            if account_type in (AccountType.ASSET, AccountType.EXPENSE):
                debit = balance if balance > 0 else 0
                credit = abs(balance) if balance < 0 else 0
            else:
                credit = balance if balance > 0 else 0
                debit = abs(balance) if balance < 0 else 0

            total_debit += debit
            total_credit += credit
            trial.append({
                "code": code,
                "name": account_info.get("name", "Unknown"),
                "type": account_type.value if isinstance(account_type, AccountType) else str(account_type),
                "debit_paise": debit,
                "credit_paise": credit,
            })

        return {
            "accounts": trial,
            "total_debit_paise": total_debit,
            "total_credit_paise": total_credit,
            "balanced": total_debit == total_credit,
            "total_entries": len(self.journal),
        }

    def get_income_statement(self) -> dict[str, Any]:
        """Generate a simple Income Statement (P&L)."""
        revenue = sum(
            self.balances.get(code, 0)
            for code, info in self.chart.items()
            if info.get("type") == AccountType.REVENUE
        )
        expenses = sum(
            self.balances.get(code, 0)
            for code, info in self.chart.items()
            if info.get("type") == AccountType.EXPENSE
        )
        net_income = revenue - expenses

        expense_breakdown = {
            info["name"]: self.balances.get(code, 0)
            for code, info in self.chart.items()
            if info.get("type") == AccountType.EXPENSE and self.balances.get(code, 0) != 0
        }

        return {
            "total_revenue_paise": revenue,
            "total_expenses_paise": expenses,
            "net_income_paise": net_income,
            "profitable": net_income > 0,
            "expense_breakdown": expense_breakdown,
        }


# Module-level singleton (will be replaced with PostgreSQL-backed in production)
_ledger = Ledger()


def get_ledger() -> Ledger:
    """Return the module-level ledger instance."""
    return _ledger
