"""Constants for the LLMOps Governance Platform.

Contains the complete Banking77 label set, route names, and system constants.
"""

from __future__ import annotations

from typing import Final

# ── Banking77 canonical labels ────────────────────────────────────────────
# 77 intent labels from the PolyAI Banking77 dataset.
BANKING77_LABELS: Final[list[str]] = [
    "activate_my_card",
    "age_limit",
    "apple_pay_or_google_pay",
    "atm_support",
    "automatic_top_up",
    "balance_not_updated_after_bank_transfer",
    "balance_not_updated_after_cheque_or_cash_deposit",
    "beneficiary_not_allowed",
    "cancel_transfer",
    "card_about_to_expire",
    "card_acceptance",
    "card_arrival",
    "card_delivery_estimate",
    "card_linking",
    "card_not_working",
    "card_payment_fee_charged",
    "card_payment_not_recognised",
    "card_payment_wrong_exchange_rate",
    "card_swallowed",
    "cash_withdrawal_charge",
    "cash_withdrawal_not_recognised",
    "change_pin",
    "compromised_card",
    "contactless_not_working",
    "country_support",
    "declined_card_payment",
    "declined_cash_withdrawal",
    "declined_transfer",
    "direct_debit_payment_not_recognised",
    "disposable_card_limits",
    "edit_personal_details",
    "exchange_charge",
    "exchange_rate",
    "exchange_via_app",
    "extra_charge_on_statement",
    "failed_transfer",
    "fiat_currency_support",
    "freeze_card",
    "get_disposable_virtual_card",
    "get_physical_card",
    "getting_spare_card",
    "getting_virtual_card",
    "lost_or_stolen_card",
    "lost_or_stolen_phone",
    "order_physical_card",
    "passcode_forgotten",
    "pending_card_payment",
    "pending_cash_withdrawal",
    "pending_top_up",
    "pending_transfer",
    "pin_blocked",
    "receiving_money",
    "refund_not_showing_up",
    "request_refund",
    "reverted_card_payment",
    "supported_cards_and_currencies",
    "terminate_account",
    "top_up_by_bank_transfer_charge",
    "top_up_by_card_charge",
    "top_up_by_cash_or_cheque",
    "top_up_failed",
    "top_up_limits",
    "top_up_reverted",
    "topping_up_by_card",
    "transaction_charged_twice",
    "transfer_fee_charged",
    "transfer_into_account",
    "transfer_not_received_by_recipient",
    "transfer_timing",
    "unable_to_verify_identity",
    "verify_my_identity",
    "verify_source_of_funds",
    "verify_top_up",
    "virtual_card_not_working",
    "visa_or_mastercard",
    "why_verify_identity",
    "wrong_amount_of_cash_received",
    "wrong_exchange_rate_for_cash_withdrawal",
]

BANKING77_LABEL_SET: Final[frozenset[str]] = frozenset(BANKING77_LABELS)
NUM_CLASSES: Final[int] = len(BANKING77_LABELS)  # 77

# ── Route names ───────────────────────────────────────────────────────────
ROUTE_BASELINE: Final[str] = "baseline"
ROUTE_LOCAL: Final[str] = "local"
ROUTE_SHADOW: Final[str] = "shadow"

# ── Experiment modes ──────────────────────────────────────────────────────
MODE_BASELINE: Final[str] = "baseline"
MODE_WEIGHTED: Final[str] = "weighted"
MODE_SHADOW: Final[str] = "shadow"
MODE_CANARY: Final[str] = "canary"

# ── Model identifiers ────────────────────────────────────────────────────
DEFAULT_BASELINE_MODEL: Final[str] = "gpt-4o-mini"
DEFAULT_LOCAL_MODEL: Final[str] = "qwen2.5-1.5b-instruct-q4_k_m"

# ── Few-shot examples for baseline prompting ─────────────────────────────
FEW_SHOT_EXAMPLES: Final[list[dict[str, str]]] = [
    {"message": "I want to get a new card, how do I do that?", "intent": "get_physical_card"},
    {"message": "My card has been stolen what should I do", "intent": "lost_or_stolen_card"},
    {"message": "Why is my transfer still pending?", "intent": "pending_transfer"},
    {"message": "How do I change my PIN number?", "intent": "change_pin"},
    {"message": "I need to cancel a bank transfer", "intent": "cancel_transfer"},
]

