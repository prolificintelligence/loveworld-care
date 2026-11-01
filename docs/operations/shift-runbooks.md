# LoveWorld Care — Operational Shift Runbooks (§19.3)

## 1. Start-of-Shift Checklist
1. Verify active clinician roster and confirm all scheduled practitioners hold `APPROVED_ACTIVE` status and non-expired MDCN credentials in Care Command.
2. Confirm LiveKit WebRTC, Paystack, Flutterwave, and Espees Wallet webhook health.
3. Inspect unclosed clinical incidents and pending `CareContinuity` follow-up tasks from prior shift.

## 2. Clinician Credential Expiry Mid-Shift (`AT-07`)
1. System automatically blocks new case claims or signing for any clinician whose `credential_expires_at <= now()`.
2. Clinical Operations Lead uses `reassign_encounter_by_ops` in Care Command to transfer open encounters to an active verified clinician on duty.

## 3. Video / Connectivity Degradation (`§8.3` & `AT-09`)
1. Clinician switches encounter room to **Low-Bandwidth Audio Fallback (`AUDIO_FALLBACK`)** or approved asynchronous clinical messaging.
2. Document modality limitation in `modality_limitations_noted` prior to signing.
3. Brief or interrupted video connections never auto-complete billing; if consultation cannot be safely completed, decline remote suitability (`remote_suitability_accepted=False`) to release sponsor reservation or issue refund.

## 4. Unsafe AI Output or Model Provider Outage (`§15.6` & `AT-16`)
1. Clinical Governance Lead or SRE toggles **Global AI-Off Kill Switch** (`POST /v1/governance/ai-kill-switch`).
2. Verify that patient intake, deterministic protocol routing, appointment booking, LiveKit consultation, and Ed25519 encounter signing continue uninterrupted.
