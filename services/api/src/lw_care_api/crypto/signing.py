"""
Ed25519 Cryptographic Signing & Verification for Clinical Records (§6.3, §8.2, §13.4).

Every signed ClinicalDocument, ClinicalAddendum, Prescription, and Referral is bound to:
1. Canonical SHA-256 content hash over deterministic JSON representation.
2. Ed25519 digital signature over the canonical hash + signer identity + MDCN licence + timestamp.
3. Immutable append-only addendum chain linking any amendment to `original_signed_document_hash`.
"""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


@dataclass(frozen=True)
class SignedClinicalEnvelope:
    document_sha256: str
    signature_ed25519_base64: str
    public_key_pem: str
    signed_at_iso: str
    signer_clinician_id: str
    signer_mdcn_licence: str


class ClinicalDocumentSigner:
    """Deterministic canonical JSON + Ed25519 cryptographic signer for clinical artefacts."""

    def __init__(self, seed_hex: str) -> None:
        seed_bytes = bytes.fromhex(seed_hex)
        if len(seed_bytes) != 32:
            seed_bytes = hashlib.sha256(seed_hex.encode("utf-8")).digest()
        self._private_key = Ed25519PrivateKey.from_private_bytes(seed_bytes)
        self._public_key = self._private_key.public_key()

    @property
    def public_key_pem(self) -> str:
        return self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")

    @staticmethod
    def compute_canonical_sha256(payload: dict[str, Any]) -> str:
        canonical_bytes = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), default=str
        ).encode("utf-8")
        return hashlib.sha256(canonical_bytes).hexdigest()

    def sign_clinical_payload(
        self,
        payload: dict[str, Any],
        signer_clinician_id: str,
        signer_mdcn_licence: str,
        signed_at_iso: str,
    ) -> SignedClinicalEnvelope:
        envelope_payload = {
            **payload,
            "signer_clinician_id": signer_clinician_id,
            "signer_mdcn_licence": signer_mdcn_licence,
            "signed_at_iso": signed_at_iso,
        }
        doc_hash = self.compute_canonical_sha256(envelope_payload)
        signature_bytes = self._private_key.sign(doc_hash.encode("utf-8"))
        signature_b64 = base64.b64encode(signature_bytes).decode("ascii")
        return SignedClinicalEnvelope(
            document_sha256=doc_hash,
            signature_ed25519_base64=signature_b64,
            public_key_pem=self.public_key_pem,
            signed_at_iso=signed_at_iso,
            signer_clinician_id=signer_clinician_id,
            signer_mdcn_licence=signer_mdcn_licence,
        )

    @staticmethod
    def verify_signature(
        document_sha256: str,
        signature_ed25519_base64: str,
        public_key_pem: str,
    ) -> bool:
        try:
            pub_key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
            if not isinstance(pub_key, Ed25519PublicKey):
                return False
            sig_bytes = base64.b64decode(signature_ed25519_base64.encode("ascii"))
            pub_key.verify(sig_bytes, document_sha256.encode("utf-8"))
            return True
        except (InvalidSignature, ValueError, TypeError):
            return False
