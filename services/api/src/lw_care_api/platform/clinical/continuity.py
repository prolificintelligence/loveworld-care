"""Identity review, scheduling, consented disclosure and actual care-finance effects."""

from sqlalchemy import select

from .. import db
from ..domain import require
from . import store as s
from . import tables as t
from .service import ClinicalService


class EMRService(ClinicalService):
    async def sharing_grant(self, body):
        _, _, encounter = await self.context(body, allow_closed=True)
        require(
            body["valid_until"] > db.now(),
            "VALIDATION_FAILED",
            "Sharing requires an explicit future expiry",
            422,
        )
        for identifier in body["record_ids"]:
            row = await self.row(identifier)
            require(
                row["patient_id"] == body["patient_id"] or row["id"] == body["patient_id"],
                "PATIENT_CONTEXT_MISMATCH",
                "Sharing scope must contain only this patient's records",
                409,
            )
            require(
                row["kind"] not in {"invoice", "cash_receipt", "disclosure", "sharing_grant"},
                "INVALID_DISCLOSURE_SCOPE",
                "Select clinical source records for this care disclosure",
                422,
            )
            if row["confidentiality"] == "RESTRICTED":
                await self.guard("SENSITIVE", patient_id=body["patient_id"], service=row["service"])
        return await self.create(
            "sharing_grant",
            body,
            patient_id=body["patient_id"],
            encounter_id=body["encounter_id"],
            service=encounter["service"],
            status="ACTIVE",
        )

    async def valid_share(self, identifier, patient_id, recipient, purpose):
        row = await self.linked(identifier, "sharing_grant", patient_id)
        data = self.content(row)
        require(
            row["status"] == "ACTIVE"
            and data["valid_until"] > db.now()
            and data["recipient"] == recipient
            and data["purpose"] == purpose,
            "SHARING_NOT_AUTHORISED",
            "Recipient, purpose, record scope and current sharing authority must match",
            403,
        )
        return row, data

    async def revoke_sharing(self, identifier, body):
        row = await self.linked(identifier, "sharing_grant", body["patient_id"])
        await self.guard(
            "CARE", patient_id=row["patient_id"], encounter_id=row["encounter_id"], write=True
        )
        data = self.content(row)
        require(
            row["status"] == "ACTIVE", "INVALID_STATE", "This sharing grant is already revoked", 409
        )
        data["revocation"] = {**body, "actor_id": self.actor["id"], "recorded_at": db.now()}
        return await self.change(
            row, data, "REVOKED", body["expected_version"], "records.grant_revoked", "LWH-EVT-029"
        )

    async def disclosure(self, body):
        await self.guard("CARE", patient_id=body["patient_id"], write=True)
        grant, scope = await self.valid_share(
            body["sharing_grant_id"], body["patient_id"], body["recipient"], body["purpose"]
        )
        sources, versions = [], []
        for identifier in scope["record_ids"]:
            row = await self.row(identifier)
            await self.usable(row)
            if row["confidentiality"] == "RESTRICTED":
                await self.guard("SENSITIVE", patient_id=body["patient_id"], service=row["service"])
            if row["kind"] == "note":
                require(
                    row["status"] == "SIGNED",
                    "SIGNED_RECORD_REQUIRED",
                    "Unsigned drafts cannot enter a clinical disclosure",
                    409,
                )
            sources.append(s.opened(self.box, row))
            versions.append({"id": identifier, "version": row["version"]})
        record = await self.create(
            "disclosure",
            {
                **body,
                "source_versions": versions,
                "delivery_state": "PREPARED_FOR_AUTHORISED_DOWNLOAD",
                "receiver_acceptance": "NOT_RECORDED",
            },
            patient_id=body["patient_id"],
            encounter_id=grant["encounter_id"],
            service=grant["service"],
            status="PREPARED",
        )
        # Typed native source package retains original codes and versions. No FHIR conformance claim.
        record["package"] = {
            "schema": "lwh.authorised-clinical-disclosure/1",
            "disclosure_id": record["id"],
            "recipient": body["recipient"],
            "purpose": body["purpose"],
            "sharing_grant_id": grant["id"],
            "sources": sources,
            "prepared_at": db.now(),
        }
        return record

    async def appointment(self, body):
        await self.guard(
            "REGISTER",
            patient_id=body["patient_id"],
            service=body["service"],
            write=True,
            relationship=False,
        )
        await s.privilege_for(
            self.session, body["clinician_id"], self.facility_id, "CARE", body["service"]
        )
        require(
            body["starts_at"] > db.now(), "VALIDATION_FAILED", "Schedule a future appointment", 422
        )
        return await self.create(
            "appointment",
            {**body, "history": []},
            patient_id=body["patient_id"],
            service=body["service"],
            status="REQUESTED",
        )

    async def appointment_action(self, identifier, body):
        row = await self.linked(identifier, "appointment", body["patient_id"])
        data, action = self.content(row), body["action"]
        await self.guard(
            "CARE" if action == "CONFIRM" else "REGISTER",
            patient_id=row["patient_id"],
            service=row["service"],
            write=True,
            relationship=False,
        )
        allowed, status = {
            "CONFIRM": ({"REQUESTED"}, "CONFIRMED"),
            "ARRIVE": ({"CONFIRMED"}, "ARRIVED"),
            "NO_SHOW": ({"CONFIRMED"}, "NO_SHOW"),
            "CANCEL": ({"REQUESTED", "CONFIRMED"}, "CANCELLED"),
        }[action]
        require(
            row["status"] in allowed,
            "INVALID_STATE",
            "This appointment cannot take the selected action",
            409,
        )
        if action == "CONFIRM":
            require(
                data["clinician_id"] == self.actor["id"],
                "ACCESS_DENIED",
                "The scheduled clinician must accept the commitment",
            )
            current = (
                await self.session.execute(
                    select(t.records).where(
                        t.records.c.facility_id == self.facility_id,
                        t.records.c.kind == "appointment",
                        t.records.c.status.in_(["CONFIRMED", "ARRIVED"]),
                        t.records.c.id != identifier,
                    )
                )
            ).mappings()
            for other in current:
                appointment = self.content(other)
                require(
                    not (
                        appointment["clinician_id"] == data["clinician_id"]
                        and appointment["starts_at"] < data["ends_at"]
                        and appointment["ends_at"] > data["starts_at"]
                    ),
                    "SCHEDULE_CONFLICT",
                    "This clinician already has an overlapping accepted commitment",
                    409,
                )
        if action == "NO_SHOW":
            require(
                data["ends_at"] <= db.now(),
                "INVALID_STATE",
                "Do not mark a future appointment as missed",
                409,
            )
        data["history"].append({**body, "actor_id": self.actor["id"], "recorded_at": db.now()})
        return await self.change(
            row,
            data,
            status,
            body["expected_version"],
            "clinical.appointment_changed",
            "LWH-EXT-CLINICAL-005",
        )

    async def identity_link(self, body):
        await self.guard("RECORDS", patient_id=body["patient_id"], write=True)
        require(
            body["other_patient_id"] != body["patient_id"],
            "VALIDATION_FAILED",
            "Identity review requires two separate patient records",
            422,
        )
        await self.row(body["other_patient_id"], "patient")
        return await self.create(
            "identity_link",
            {**body, "history": []},
            patient_id=body["patient_id"],
            status="PROPOSED",
            unique_value=":".join(sorted([body["patient_id"], body["other_patient_id"]])),
        )

    async def identity_link_action(self, identifier, body):
        row = await self.linked(identifier, "identity_link", body["patient_id"])
        await self.guard("RECORDS", patient_id=body["patient_id"], write=True)
        data, action = self.content(row), body["action"]
        if action == "ACCEPT":
            require(
                row["created_by"] != self.actor["id"] and row["status"] == "PROPOSED",
                "INDEPENDENT_REVIEW_REQUIRED",
                "Another records custodian must review and accept the evidence",
                403,
            )
        else:
            require(
                row["status"] in {"PROPOSED", "ACCEPTED", "DISPUTED"},
                "INVALID_STATE",
                "This identity link is already revoked",
                409,
            )
        status = {"ACCEPT": "ACCEPTED", "DISPUTE": "DISPUTED", "REVOKE": "REVOKED"}[action]
        data["history"].append({**body, "reviewer_id": self.actor["id"], "recorded_at": db.now()})
        # Source charts remain distinct. Acceptance creates a reversible, evidenced crosswalk only.
        return await self.change(
            row,
            data,
            status,
            body["expected_version"],
            "records.identity_link_reviewed",
            "LWH-EXT-CLINICAL-006",
        )

    async def tariff(self, body):
        await self.guard("FINANCE", write=True, relationship=False)
        require(
            body["valid_until"] > db.now(),
            "VALIDATION_FAILED",
            "An adopted tariff must have future validity",
            422,
        )
        return await self.create(
            "tariff", body, service="FINANCE", status="ADOPTED", unique_value=body["code"]
        )

    async def post_ledger(self, source, debit, credit, amount, currency):
        await self.session.execute(
            t.ledger.insert(),
            [
                {
                    "id": db.uid(),
                    "facility_id": self.facility_id,
                    "source_id": source["id"],
                    "leg": leg,
                    "account": account,
                    "amount_minor": value,
                    "currency": currency,
                    "recorded_at": db.now(),
                }
                for leg, account, value in [(1, debit, amount), (2, credit, -amount)]
            ],
        )

    async def invoice(self, body):
        await self.guard("FINANCE", patient_id=body["patient_id"], write=True, relationship=False)
        source = await self.row(body["service_record_id"])
        require(
            source["patient_id"] == body["patient_id"],
            "PATIENT_CONTEXT_MISMATCH",
            "Charge the correct patient's actual service",
            409,
        )
        fulfilled = {
            "encounter": {"COMPLETED"},
            "procedure": {"PERFORMED", "RECOVERY", "HANDED_OVER"},
            "order": {"FULFILLED"},
            "dispense": {"DISPENSED"},
            "stay": {"DISCHARGED"},
        }
        require(
            source["status"] in fulfilled.get(source["kind"], set()),
            "SERVICE_NOT_FULFILLED",
            "An actual fulfilled service is required before charging",
            409,
        )
        await self.usable(source)
        tariff = await self.row(body["tariff_id"], "tariff")
        price = self.content(tariff)
        require(
            tariff["status"] == "ADOPTED" and price["valid_until"] > db.now(),
            "TARIFF_EXPIRED",
            "A current approved tariff is required",
            409,
        )
        result = await self.create(
            "invoice",
            {
                **body,
                "tariff_snapshot": price,
                "amount_minor": price["amount_minor"],
                "currency": price["currency"],
                "paid_minor": 0,
            },
            patient_id=body["patient_id"],
            service="FINANCE",
            status="ISSUED",
            unique_value=source["id"] + ":" + tariff["id"],
            contract="LWH-EVT-031",
            action="finance.service_fulfilled",
        )
        await self.post_ledger(
            result, "RECEIVABLE", "CARE_REVENUE", price["amount_minor"], price["currency"]
        )
        return result

    async def cash_receipt(self, body):
        await self.guard("CASHIER", patient_id=body["patient_id"], write=True, relationship=False)
        s.event_time(body["received_at"])
        invoice = await self.linked(body["invoice_id"], "invoice", body["patient_id"])
        data = self.content(invoice)
        require(
            invoice["version"] == body["expected_invoice_version"],
            "VERSION_CONFLICT",
            "The invoice changed",
            412,
        )
        require(
            body["currency"] == data["currency"]
            and body["amount_minor"] <= data["amount_minor"] - data["paid_minor"],
            "RECEIPT_ALLOCATION_INVALID",
            "Currency and amount must match the outstanding invoice",
            422,
        )
        result = await self.create(
            "cash_receipt",
            {**body, "payment_method": "CASH", "settlement": "CASH_RECEIVED_AT_FACILITY"},
            patient_id=body["patient_id"],
            service="FINANCE",
            status="RECEIVED",
            unique_value=body["receipt_reference"],
            contract="LWH-EVT-032",
            action="finance.receipt_confirmed",
        )
        data["paid_minor"] += body["amount_minor"]
        await self.change(
            invoice,
            data,
            "PAID" if data["paid_minor"] == data["amount_minor"] else "PART_PAID",
            invoice["version"],
            "finance.invoice_allocated",
            "LWH-EVT-032",
        )
        await self.post_ledger(result, "CASH", "RECEIVABLE", body["amount_minor"], body["currency"])
        return result
