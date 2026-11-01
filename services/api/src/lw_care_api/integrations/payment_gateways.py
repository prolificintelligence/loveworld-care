"""
Unified PaymentGatewayPort with Concrete Adapters for:
1. Paystack (Primary NGN collections & clinician transfer payouts, HMAC-SHA512 webhook verification)
2. Flutterwave (NGN & USD diaspora collections, secret hash webhook verification)
3. Espees Wallet (`ESP` LoveWorld currency ecosystem checkout & HMAC-SHA256 webhook verification)

All monetary amounts use integral minor units (`amount_minor: int`). Floating-point money is forbidden (§10.2).
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Literal, Protocol

PaymentProviderName = Literal["PAYSTACK", "FLUTTERWAVE", "ESPEES_WALLET"]
CurrencyCode = Literal["NGN", "ESP", "USD"]


@dataclass(frozen=True)
class PaymentInitiationSession:
    provider: PaymentProviderName
    reference: str
    episode_id: str
    amount_minor: int
    currency: CurrencyCode
    checkout_url: str
    idempotency_key: str


@dataclass(frozen=True)
class VerifiedWebhookPaymentEvent:
    provider: PaymentProviderName
    provider_event_id: str
    reference: str
    episode_id: str
    amount_minor: int
    currency: CurrencyCode
    status: Literal["SETTLED", "FAILED", "REFUNDED"]


class PaymentGatewayPort(Protocol):
    provider_name: PaymentProviderName

    def initiate_checkout(
        self,
        *,
        reference: str,
        episode_id: str,
        patient_email: str,
        amount_minor: int,
        currency: CurrencyCode,
        idempotency_key: str,
    ) -> PaymentInitiationSession: ...

    def verify_webhook(
        self, *, raw_body: bytes, signature_header: str
    ) -> VerifiedWebhookPaymentEvent: ...


class PaystackGatewayAdapter:
    provider_name: PaymentProviderName = "PAYSTACK"

    def __init__(self, secret_key: str, webhook_secret: str) -> None:
        self._secret_key = secret_key
        self._webhook_secret = webhook_secret

    def initiate_checkout(
        self,
        *,
        reference: str,
        episode_id: str,
        patient_email: str,
        amount_minor: int,
        currency: CurrencyCode,
        idempotency_key: str,
    ) -> PaymentInitiationSession:
        if not isinstance(amount_minor, int) or isinstance(amount_minor, bool) or amount_minor <= 0:
            raise ValueError("Paystack amount_minor must be a positive integer (kobo).")
        if currency != "NGN":
            raise ValueError("Paystack primary adapter requires NGN currency in kobo.")
        return PaymentInitiationSession(
            provider="PAYSTACK",
            reference=reference,
            episode_id=episode_id,
            amount_minor=amount_minor,
            currency="NGN",
            checkout_url=f"https://checkout.paystack.com/{reference}",
            idempotency_key=idempotency_key,
        )

    def verify_webhook(
        self, *, raw_body: bytes, signature_header: str
    ) -> VerifiedWebhookPaymentEvent:
        expected = hmac.new(
            self._webhook_secret.encode("utf-8"), raw_body, hashlib.sha512
        ).hexdigest()
        if not hmac.compare_digest(expected, signature_header):
            raise ValueError("Invalid Paystack x-paystack-signature HMAC-SHA512")

        payload = json.loads(raw_body.decode("utf-8"))
        event_name = payload.get("event", "")
        data = payload.get("data", {})
        status: Literal["SETTLED", "FAILED", "REFUNDED"] = (
            "SETTLED"
            if event_name == "charge.success"
            else "REFUNDED"
            if event_name.startswith("refund.")
            else "FAILED"
        )
        return VerifiedWebhookPaymentEvent(
            provider="PAYSTACK",
            provider_event_id=str(data.get("id", reference := data.get("reference", ""))),
            reference=str(reference),
            episode_id=str(data.get("metadata", {}).get("episode_id", "")),
            amount_minor=int(data.get("amount", 0)),
            currency="NGN",
            status=status,
        )


class FlutterwaveGatewayAdapter:
    provider_name: PaymentProviderName = "FLUTTERWAVE"

    def __init__(self, secret_key: str, webhook_hash: str) -> None:
        self._secret_key = secret_key
        self._webhook_hash = webhook_hash

    def initiate_checkout(
        self,
        *,
        reference: str,
        episode_id: str,
        patient_email: str,
        amount_minor: int,
        currency: CurrencyCode,
        idempotency_key: str,
    ) -> PaymentInitiationSession:
        if not isinstance(amount_minor, int) or isinstance(amount_minor, bool) or amount_minor <= 0:
            raise ValueError("Flutterwave amount_minor must be a positive integer.")
        if currency not in ("NGN", "USD"):
            raise ValueError("Flutterwave adapter supports NGN and USD.")
        return PaymentInitiationSession(
            provider="FLUTTERWAVE",
            reference=reference,
            episode_id=episode_id,
            amount_minor=amount_minor,
            currency=currency,
            checkout_url=f"https://checkout.flutterwave.com/v3/hosted/pay/{reference}",
            idempotency_key=idempotency_key,
        )

    def verify_webhook(
        self, *, raw_body: bytes, signature_header: str
    ) -> VerifiedWebhookPaymentEvent:
        if not hmac.compare_digest(self._webhook_hash, signature_header):
            raise ValueError("Invalid Flutterwave verif-hash header")

        payload = json.loads(raw_body.decode("utf-8"))
        data = payload.get("data", {})
        raw_status = str(data.get("status", "")).lower()
        status: Literal["SETTLED", "FAILED", "REFUNDED"] = (
            "SETTLED"
            if raw_status == "successful"
            else "REFUNDED"
            if raw_status == "refunded"
            else "FAILED"
        )
        return VerifiedWebhookPaymentEvent(
            provider="FLUTTERWAVE",
            provider_event_id=str(data.get("id", "")),
            reference=str(data.get("tx_ref", "")),
            episode_id=str(data.get("meta", {}).get("episode_id", "")),
            amount_minor=int(data.get("amount_minor", int(float(data.get("amount", 0)) * 100))),
            currency=data.get("currency", "NGN"),
            status=status,
        )


class EspeesWalletGatewayAdapter:
    """
    Espees (`ESP`) LoveWorld Digital Currency & Wallet Adapter.
    Supports self-pay and sponsor pool funding in integral minor ESP units (1 ESP = 100 minor units).
    """

    provider_name: PaymentProviderName = "ESPEES_WALLET"

    def __init__(
        self, merchant_code: str, api_key: str, webhook_secret: str, base_url: str
    ) -> None:
        self._merchant_code = merchant_code
        self._api_key = api_key
        self._webhook_secret = webhook_secret
        self._base_url = base_url.rstrip("/")

    def initiate_checkout(
        self,
        *,
        reference: str,
        episode_id: str,
        patient_email: str,
        amount_minor: int,
        currency: CurrencyCode,
        idempotency_key: str,
    ) -> PaymentInitiationSession:
        if not isinstance(amount_minor, int) or isinstance(amount_minor, bool) or amount_minor <= 0:
            raise ValueError("Espees amount_minor must be a positive integer.")
        if currency != "ESP":
            raise ValueError("EspeesWalletGatewayAdapter requires currency='ESP'.")
        return PaymentInitiationSession(
            provider="ESPEES_WALLET",
            reference=reference,
            episode_id=episode_id,
            amount_minor=amount_minor,
            currency="ESP",
            checkout_url=f"https://payment.espees.org/pay/{self._merchant_code}/{reference}",
            idempotency_key=idempotency_key,
        )

    def verify_webhook(
        self, *, raw_body: bytes, signature_header: str
    ) -> VerifiedWebhookPaymentEvent:
        expected = hmac.new(
            self._webhook_secret.encode("utf-8"), raw_body, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, signature_header):
            raise ValueError("Invalid Espees Wallet x-espees-signature HMAC-SHA256")

        payload = json.loads(raw_body.decode("utf-8"))
        raw_status = str(payload.get("status", "")).upper()
        status: Literal["SETTLED", "FAILED", "REFUNDED"] = (
            "SETTLED"
            if raw_status in ("SUCCESS", "APPROVED", "SETTLED")
            else "REFUNDED"
            if raw_status == "REFUNDED"
            else "FAILED"
        )
        return VerifiedWebhookPaymentEvent(
            provider="ESPEES_WALLET",
            provider_event_id=str(payload.get("transaction_id", payload.get("reference", ""))),
            reference=str(payload.get("reference", "")),
            episode_id=str(payload.get("episode_id", "")),
            amount_minor=int(payload.get("amount_minor", 0)),
            currency="ESP",
            status=status,
        )
