"""Structured actual specialty care and independently witnessed medicine/stock effects."""

from decimal import Decimal

from sqlalchemy import func, select, update

from .. import db
from ..domain import require
from . import flow_index as f
from . import store as s
from . import tables as t
from .advanced import AdvancedService


class Phase5Service(AdvancedService):
    async def labour(self, body):
        result = await self.flow(
            "labour_observation",
            {**body, "automated_clinical_interpretation": "UNAVAILABLE_NOT_INFERRED"},
        )
        encounter = await self.row(body["encounter_id"], "encounter")
        await self.task(
            encounter,
            "Review maternal assessment",
            body["plan"],
            body["review_owner_id"],
            body["review_due_at"],
            result["id"],
        )
        return result

    async def birth(self, body):
        await self.phase5()
        await self.context(body, allow_closed=bool(body.get("amends_id")))
        await self.signed_note(body["signed_note_id"], body["patient_id"], body["encounter_id"])
        infant_ids = [item["patient_id"] for item in body["infants"]]
        orders = [item["birth_order"] for item in body["infants"]]
        require(
            len(set(infant_ids)) == len(infant_ids)
            and body["patient_id"] not in infant_ids
            and len(set(orders)) == len(orders),
            "DISTINCT_INFANT_IDENTITIES_REQUIRED",
            "Each infant needs its own chart and unique birth order",
            409,
        )
        for member in body["actual_team"]:
            await s.privilege_for(
                self.session,
                member,
                self.facility_id,
                "CARE",
                (await self.row(body["encounter_id"], "encounter"))["service"],
            )
        infants = []
        for item in body["infants"]:
            s.event_time(item["occurred_at"])
            _, _, encounter = await self.guard(
                "CARE", patient_id=item["patient_id"], encounter_id=item["encounter_id"], write=True
            )
            require(
                encounter["status"] not in {"COMPLETED", "CANCELLED", "TRANSFERRED"},
                "ENCOUNTER_CLOSED",
                "Use the infant's current care encounter",
                409,
            )
            infants.append((item, encounter))
        result = await self.flow("birth", body)
        for item, encounter in infants:
            link = await self.create(
                "birth_link",
                {
                    **item,
                    "source_id": result["id"],
                    "maternal_patient_id": body["patient_id"],
                    "relationship_authority": "CLINICAL_RELATIONSHIP_ONLY_NO_PROXY_GRANT",
                },
                patient_id=item["patient_id"],
                encounter_id=item["encounter_id"],
                service=encounter["service"],
                status="RECORDED",
                unique_value=item["patient_id"] if not body.get("amends_id") else None,
                contract="LWH-EXT-CLINICAL-035",
            )
            await self.task(
                encounter,
                "Review recorded infant outcome and continuity",
                item["relationship_evidence"],
                item["follow_up_owner_id"],
                item["follow_up_due_at"],
                link["id"],
            )
        await self.task(
            await self.row(body["encounter_id"], "encounter"),
            "Review postnatal maternal care",
            body["maternal_outcome"],
            body["maternal_review_owner_id"],
            body["maternal_review_due_at"],
            result["id"],
        )
        return result

    async def growth(self, body):
        result = await self.flow(
            "child_measurement",
            {**body, "automated_percentiles_or_schedule": "UNAVAILABLE_NOT_INFERRED"},
        )
        await self.task(
            await self.row(body["encounter_id"], "encounter"),
            "Review child measurements",
            body["interpretation_as_assessed"],
            body["review_owner_id"],
            body["review_due_at"],
            result["id"],
        )
        return result

    async def immunisation(self, body):
        await self.context(body, "NURSING", allow_closed=True)
        administration = await self.linked(
            body["administration_id"], "administration", body["patient_id"], body["encounter_id"]
        )
        require(
            administration["status"] == "GIVEN",
            "ACTUAL_ADMINISTRATION_REQUIRED",
            "Link a recorded actual administration, not a plan or omission",
            409,
        )
        data = self.content(administration)
        medicine = await self.linked(data["medication_id"], "medication", body["patient_id"])
        supply = await self.linked(
            body["dispense_id"], "dispense", body["patient_id"], body["encounter_id"]
        )
        supplied = self.content(supply)
        require(
            supply["status"] == "DISPENSED"
            and supplied["medication_id"] == medicine["id"]
            and supplied["occurred_at"] <= data["occurred_at"],
            "TRACEABLE_SUPPLY_REQUIRED",
            "Record the actual vaccine supply and batch before completing this chain",
            409,
        )
        result = await self.flow(
            "immunisation",
            {
                **body,
                "administration_snapshot": data,
                "actual_supply_snapshot": supplied,
                "automated_schedule_generated": False,
            },
            capability="NURSING",
            closed=True,
        )
        await self.task(
            await self.row(body["encounter_id"], "encounter"),
            "Review immunisation continuity",
            body["schedule_reference"],
            body["next_review_owner_id"],
            body["next_review_due_at"],
            result["id"],
        )
        return result

    async def reconciliation(self, body):
        await self.phase5()
        _, _, encounter = await self.context(body, allow_closed=True)
        for item in body["items"]:
            require(
                bool(item.get("medicine_id")) != bool(item.get("external_description")),
                "MEDICINE_SOURCE_REQUIRED",
                "Each item needs one local order or explicitly sourced external medicine",
                422,
            )
            if item.get("medicine_id"):
                row = await self.linked(item["medicine_id"], "medication", body["patient_id"])
                item["source_version"] = row["version"]
                item["source_status"] = row["status"]
        result = await self.flow(
            "medicine_reconciliation", {**body, "order_changes_inferred": False}, closed=True
        )
        unresolved = [
            item for item in body["items"] if item["assessment"] in {"UNKNOWN", "CHANGE", "STOP"}
        ]
        if unresolved:
            await self.task(
                encounter,
                "Resolve reconciled medicine decisions",
                body["instructions"],
                body["unresolved_owner_id"],
                body["review_due_at"],
                result["id"],
            )
        return result

    async def stock_lot(self, identifier):
        row = (
            (
                await self.session.execute(
                    select(t.lots)
                    .where(t.lots.c.id == identifier, t.lots.c.facility_id == self.facility_id)
                    .with_for_update()
                )
            )
            .mappings()
            .first()
        )
        require(row, "NOT_FOUND", "This local stock lot is unavailable", 404)
        return row

    async def held_stock(self, lot_id, exclude=""):
        if not await self.advanced_ready():
            return Decimal(0)
        require(
            await f.ready(self.session),
            "CLINICAL_WORK_INDEX_RECONCILIATION_REQUIRED",
            "Reconcile actual stock reservations before new supply",
            503,
        )
        return await self.session.scalar(
            select(func.coalesce(func.sum(f.index.c.quantity), 0)).where(
                f.index.c.facility_id == self.facility_id,
                f.index.c.kind == "stock_hold",
                f.index.c.source_id == lot_id,
                f.index.c.status == "HELD",
                f.index.c.ends_at > db.now(),
                f.index.c.record_id != exclude,
            )
        )

    async def stock_hold(self, body):
        await self.phase5()
        _, _, encounter = await self.context(body, "PHARMACY", allow_closed=True)
        medicine = await self.linked(
            body["medication_id"], "medication", body["patient_id"], body["encounter_id"]
        )
        require(
            medicine["status"] == "VERIFIED"
            and medicine["version"] == body["expected_medication_version"],
            "ORDER_NOT_CURRENT",
            "Reserve against the current pharmacy-verified medication",
            409,
        )
        lot = await self.stock_lot(body["lot_id"])
        require(
            lot["version"] == body["expected_lot_version"],
            "VERSION_CONFLICT",
            "The stock lot changed",
            412,
        )
        require(
            lot["product_id"] == self.content(medicine)["product_id"]
            and lot["unit"] == body["unit"],
            "PRODUCT_OR_UNIT_MISMATCH",
            "Use the exact ordered product and lot unit",
            409,
        )
        require(
            lot["status"] == "AVAILABLE"
            and lot["expires_at"] > db.now()
            and db.now()
            < body["expires_at"]
            <= min(lot["expires_at"], self.content(medicine)["stops_at"]),
            "STOCK_UNAVAILABLE",
            "The reservation must fall within valid stock/order dates",
            409,
        )
        require(
            lot["quantity"] - await self.held_stock(lot["id"]) >= Decimal(body["quantity"]),
            "INSUFFICIENT_UNRESERVED_STOCK",
            "The remaining stock is already reserved or insufficient",
            409,
        )
        return await self.create(
            "stock_hold",
            {**body, "owner_id": self.actor["id"]},
            patient_id=body["patient_id"],
            encounter_id=body["encounter_id"],
            service=encounter["service"],
            status="HELD",
            contract="LWH-EXT-CLINICAL-036",
        )

    async def cancel_hold(self, identifier, body):
        await self.phase5()
        row = await self.row(identifier)
        require(
            row["kind"] in {"bed_hold", "stock_hold", "admission_order"},
            "INVALID_SOURCE",
            "Choose a bed, stock or admission commitment",
            422,
        )
        require(
            body.get("patient_id") == row["patient_id"],
            "PATIENT_CONTEXT_MISMATCH",
            "Review the selected patient's commitment",
            409,
        )
        capability = {"bed_hold": "NURSING", "stock_hold": "PHARMACY", "admission_order": "CARE"}[
            row["kind"]
        ]
        await self.guard(
            capability, patient_id=row["patient_id"], encounter_id=row["encounter_id"], write=True
        )
        require(
            row["status"] in {"HELD", "ORDERED"} and body["action"] == "CANCEL",
            "INVALID_STATE",
            "Only a pending commitment can be cancelled",
            409,
        )
        return await self.change(
            row,
            {**self.content(row), "cancellation": body},
            "CANCELLED",
            body["expected_version"],
            "clinical.commitment_cancelled",
            "LWH-EXT-CLINICAL-036",
        )

    async def dispense(self, body):
        lot = await self.stock_lot(body["lot_id"])
        hold = None
        if body.get("reservation_id"):
            await self.phase5()
            hold = await self.linked(
                body["reservation_id"], "stock_hold", body["patient_id"], body["encounter_id"]
            )
            data = self.content(hold)
            require(
                hold["status"] == "HELD"
                and data["expires_at"] > db.now()
                and data["lot_id"] == lot["id"]
                and data["medication_id"] == body["medication_id"]
                and Decimal(data["quantity"]) >= Decimal(body["quantity"]),
                "RESERVATION_NOT_CURRENT",
                "Review the current matching stock reservation",
                409,
            )
        require(
            lot["quantity"] - await self.held_stock(lot["id"], hold["id"] if hold else "")
            >= Decimal(body["quantity"]),
            "INSUFFICIENT_UNRESERVED_STOCK",
            "Other patients' active reservations protect this stock",
            409,
        )
        result = await super().dispense(body)
        if hold:
            data = self.content(hold)
            remainder = Decimal(data["quantity"]) - Decimal(body["quantity"])
            data.update(quantity=str(remainder), last_dispense_id=result["id"])
            await self.change(
                hold,
                data,
                "HELD" if remainder else "CONSUMED",
                hold["version"],
                "medicines.reservation_consumed",
                "LWH-EXT-CLINICAL-036",
            )
        return result

    async def stock_adjustment(self, body):
        await self.phase5()
        await self.guard("PHARMACY", write=True)
        lot = await self.stock_lot(body["lot_id"])
        require(
            lot["version"] == body["expected_lot_version"] and lot["unit"] == body["unit"],
            "VERSION_OR_UNIT_CONFLICT",
            "Review the actual lot and its current unit/version",
            412,
        )
        require(
            Decimal(body["quantity"]) != 0,
            "ACTUAL_MOVEMENT_REQUIRED",
            "A physical adjustment cannot have zero quantity",
            422,
        )
        return await self.create(
            "stock_adjustment",
            {**body, "owner_id": self.actor["id"]},
            status="PROPOSED",
            contract="LWH-EXT-CLINICAL-036",
        )

    async def stock_return(self, body):
        await self.phase5()
        await self.guard("PHARMACY", patient_id=body["patient_id"], write=True, relationship=False)
        source = await self.linked(body["dispense_id"], "dispense", body["patient_id"])
        data = self.content(source)
        require(
            body["lot_id"] == data["lot_id"]
            and body["unit"] == data["unit"]
            and 0 < Decimal(body["quantity"]) <= Decimal(data["quantity"])
            and body["disposition"] == "QUARANTINED",
            "RETURN_CHAIN_MISMATCH",
            "Returned physical stock must match the actual supply and enter quarantine",
            409,
        )
        lot = await self.stock_lot(body["lot_id"])
        require(
            lot["version"] == body["expected_lot_version"],
            "VERSION_CONFLICT",
            "The lot changed",
            412,
        )
        return await self.create(
            "stock_return",
            {**body, "source_id": source["id"], "owner_id": self.actor["id"]},
            patient_id=source["patient_id"],
            encounter_id=source["encounter_id"],
            service=source["service"],
            status="PROPOSED",
            contract="LWH-EXT-CLINICAL-036",
        )

    async def witness_stock(self, identifier, body):
        await self.phase5()
        row = await self.row(identifier)
        require(
            row["kind"] in {"stock_adjustment", "stock_return"},
            "INVALID_SOURCE",
            "Choose an actual physical stock proposal",
            422,
        )
        await self.guard("PHARMACY", patient_id=row["patient_id"], write=True, relationship=False)
        data = self.content(row)
        require(
            body.get("patient_id") == row["patient_id"],
            "PATIENT_CONTEXT_MISMATCH",
            "Review the proposal's current subject",
            409,
        )
        require(
            data["owner_id"] != self.actor["id"],
            "INDEPENDENT_WITNESS_REQUIRED",
            "Another currently authorised pharmacist must review the physical evidence",
            409,
        )
        require(
            row["status"] == "PROPOSED" and body["action"] in {"APPROVE", "REJECT"},
            "INVALID_STATE",
            "This proposal is no longer pending",
            409,
        )
        if body["action"] == "APPROVE":
            lot = await self.stock_lot(data["lot_id"])
            require(
                lot["version"] == data["expected_lot_version"] and lot["unit"] == data["unit"],
                "VERSION_CONFLICT",
                "The source lot changed; prepare a new reviewed proposal",
                412,
            )
            delta = Decimal(data["quantity"])
            if row["kind"] == "stock_return":
                returned = await self.session.scalar(
                    select(func.coalesce(func.sum(f.index.c.quantity), 0)).where(
                        f.index.c.facility_id == self.facility_id,
                        f.index.c.kind == "stock_return",
                        f.index.c.source_id == data["dispense_id"],
                        f.index.c.status == "APPLIED",
                    )
                )
                source = await self.row(data["dispense_id"], "dispense")
                require(
                    returned + delta <= Decimal(self.content(source)["quantity"]),
                    "RETURN_EXCEEDS_ACTUAL_SUPPLY",
                    "Previously returned quantities already account for this supply",
                    409,
                )
            require(
                lot["quantity"] + delta >= await self.held_stock(lot["id"]),
                "RESERVED_STOCK_CONFLICT",
                "The witnessed adjustment cannot consume protected reservations",
                409,
            )
            next_status = data["disposition"]
            if lot["status"] in {"RECALLED", "QUARANTINED"}:
                require(
                    next_status == lot["status"] or next_status == "QUARANTINED",
                    "RELEASE_REVIEW_REQUIRED",
                    "An adjustment cannot silently release recalled or quarantined stock",
                    409,
                )
                next_status = lot["status"]
            await self.session.execute(
                update(t.lots)
                .where(t.lots.c.id == lot["id"], t.lots.c.version == lot["version"])
                .values(
                    quantity=lot["quantity"] + delta, status=next_status, version=lot["version"] + 1
                )
            )
            await self.session.execute(
                t.movements.insert().values(
                    id=db.uid(),
                    lot_id=lot["id"],
                    source_id=row["id"],
                    quantity=delta,
                    reason=body["reason"],
                    actor_id=self.actor["id"],
                    recorded_at=db.now(),
                )
            )
        data["witness"] = {**body, "actor_id": self.actor["id"]}
        return await self.change(
            row,
            data,
            "APPLIED" if body["action"] == "APPROVE" else "REJECTED",
            body["expected_version"],
            "medicines.witnessed_stock_movement",
            "LWH-EXT-CLINICAL-036",
        )

    async def substitution(self, body):
        await self.phase5()
        _, _, encounter = await self.context(body, "PHARMACY", allow_closed=True)
        source = await self.linked(
            body["medication_id"], "medication", body["patient_id"], body["encounter_id"]
        )
        require(
            source["version"] == body["expected_medication_version"]
            and source["status"] in {"SIGNED", "VERIFIED", "ON_HOLD"},
            "ORDER_NOT_CURRENT",
            "Use the current live prescribed order",
            409,
        )
        require(
            self.content(source)["substitution"] == "PHARMACIST_APPROVED_EQUIVALENT",
            "SUBSTITUTION_NOT_PERMITTED",
            "This order prohibits substitution; seek a separately reviewed new prescribing decision",
            409,
        )
        product = await self.row(body["replacement_product_id"], "product")
        require(
            product["status"] == "ACTIVE"
            and self.content(product)["valid_until"] > db.now()
            and product["id"] != self.content(source)["product_id"],
            "PRODUCT_NOT_CURRENT",
            "Select another currently adopted exact product",
            409,
        )
        await s.privilege_for(
            self.session, body["prescriber_id"], self.facility_id, "PRESCRIBE", encounter["service"]
        )
        return await self.create(
            "substitution",
            {**body, "owner_id": self.actor["id"], "recipient_id": body["prescriber_id"]},
            patient_id=body["patient_id"],
            encounter_id=body["encounter_id"],
            service=encounter["service"],
            status="PROPOSED",
            contract="LWH-EXT-CLINICAL-037",
        )

    async def substitution_decision(self, identifier, body):
        await self.phase5()
        row = await self.linked(identifier, "substitution", body["patient_id"])
        data = self.content(row)
        await self.guard(
            "PRESCRIBE", patient_id=row["patient_id"], encounter_id=row["encounter_id"], write=True
        )
        require(self.actor["id"] == data["prescriber_id"] and self.actor["id"] != data["owner_id"])
        require(
            row["status"] == "PROPOSED",
            "INVALID_STATE",
            "This substitution is no longer pending",
            409,
        )
        if body["action"] == "APPROVE":
            source = await self.linked(data["medication_id"], "medication", row["patient_id"])
            replacement = await self.linked(
                body.get("replacement_medication_id"),
                "medication",
                row["patient_id"],
                row["encounter_id"],
            )
            require(
                source["version"] == data["expected_medication_version"]
                and source["status"] in {"SIGNED", "VERIFIED", "ON_HOLD"},
                "ORDER_NOT_CURRENT",
                "The original prescription changed",
                409,
            )
            require(
                replacement["status"] in {"SIGNED", "VERIFIED"}
                and self.content(replacement)["product_id"] == data["replacement_product_id"]
                and self.content(replacement).get("prescriber_id") == self.actor["id"],
                "SIGNED_REPLACEMENT_REQUIRED",
                "The named prescriber must intentionally sign the exact replacement order",
                409,
            )
            await self.change(
                source,
                {
                    **self.content(source),
                    "replacement_order_id": replacement["id"],
                    "substitution_id": identifier,
                    "stop_reason": body["reason"],
                },
                "STOPPED",
                source["version"],
                "medicines.order_replaced_by_reviewed_substitution",
                "LWH-EXT-CLINICAL-037",
            )
        data["decision"] = {**body, "actor_id": self.actor["id"]}
        return await self.change(
            row,
            data,
            "APPROVED" if body["action"] == "APPROVE" else "REJECTED",
            body["expected_version"],
            "medicines.substitution_reviewed",
            "LWH-EXT-CLINICAL-037",
        )

    async def anaesthesia(self, body):
        await self.context(body, "PROCEDURE")
        source = await self.linked(
            body["procedure_id"], "procedure", body["patient_id"], body["encounter_id"]
        )
        require(
            source["status"] not in {"CANCELLED", "COMPLETED"},
            "PROCEDURE_NOT_CURRENT",
            "Use the actual current procedural episode",
            409,
        )
        require(
            self.actor["id"] in self.content(source)["team_ids"],
            "PROCEDURE_TEAM_REQUIRED",
            "Record monitoring under the accepted procedural team",
            403,
        )
        if body["phase"] != "PRE_ASSESSMENT":
            require(
                source["status"]
                in {"SIGNED_IN", "TIME_OUT_COMPLETE", "PERFORMED", "RECOVERY", "HANDOVER_PENDING"},
                "PROCEDURE_PREPARATION_REQUIRED",
                "Record the actual safety preparation before anaesthesia monitoring",
                409,
            )
            await self.valid_consent(self.content(source)["consent_id"], body["patient_id"])
        return await self.flow(
            "anaesthesia_observation",
            {**body, "automated_score_or_dose_inferred": False},
            capability="PROCEDURE",
        )

    async def device(self, body):
        await self.context(body, "PROCEDURE")
        source = await self.linked(
            body["procedure_id"], "procedure", body["patient_id"], body["encounter_id"]
        )
        require(
            source["status"]
            in {"PERFORMED", "RECOVERY", "HANDOVER_PENDING", "HANDED_OVER", "COMPLETED"},
            "ACTUAL_PROCEDURE_REQUIRED",
            "A plan is not evidence of actual device use",
            409,
        )
        if body.get("expires_at"):
            require(
                body["occurred_at"] < body["expires_at"],
                "DEVICE_EXPIRED",
                "The actual use cannot be beyond recorded expiry",
                409,
            )
        return await self.flow(
            "device_use", {**body, "source_id": source["id"]}, capability="PROCEDURE", closed=True
        )

    async def recall(self, body):
        await self.phase5()
        _, _, encounter = await self.context(body, "PROCEDURE", allow_closed=True)
        source = await self.linked(body["source_id"], None, body["patient_id"])
        require(
            source["kind"] in {"device_use", "transfusion"},
            "TRACEABLE_SOURCE_REQUIRED",
            "Identify the actual device use or component record",
            409,
        )
        result = await self.create(
            "clinical_recall",
            {**body, "exposure_or_harm_inferred": False},
            patient_id=body["patient_id"],
            encounter_id=encounter["id"],
            service=encounter["service"],
            status="REVIEW_REQUIRED",
            contract="LWH-EXT-CLINICAL-038",
        )
        await self.task(
            encounter,
            "Review clinical device/component recall",
            body["action_plan"],
            body["owner_id"],
            body["due_at"],
            result["id"],
        )
        return result

    async def infusion(self, body):
        await self.context(body, "NURSING")
        source = await self.linked(
            body["medication_id"], "medication", body["patient_id"], body["encounter_id"]
        )
        require(
            source["version"] == body["expected_medication_version"]
            and source["status"] == "VERIFIED",
            "ORDER_NOT_CURRENT",
            "Record infusion events against the current verified order",
            409,
        )
        require(
            self.content(source)["starts_at"]
            <= body["occurred_at"]
            < self.content(source)["stops_at"],
            "ORDER_EXPIRED",
            "Review the order's actual validity",
            409,
        )
        require(
            body["witness_id"] != self.actor["id"],
            "INDEPENDENT_WITNESS_REQUIRED",
            "Name the independently involved qualified nurse",
            409,
        )
        await s.privilege_for(
            self.session, body["witness_id"], self.facility_id, "NURSING", source["service"]
        )
        require(
            body["action"] not in {"START", "RATE_CHANGE"}
            or body.get("actual_rate")
            and body.get("rate_unit"),
            "ACTUAL_RATE_REQUIRED",
            "Record the actual measured rate and unit; no calculation is inferred",
            422,
        )
        require(
            body.get("actual_volume") is None or body.get("volume_unit"),
            "VOLUME_UNIT_REQUIRED",
            "Record the original volume unit",
            422,
        )
        result = await self.flow(
            "infusion_event",
            {
                **body,
                "witness_state": "AWAITING_PERSONAL_ATTESTATION",
                "automated_calculation": "UNAVAILABLE_MANUAL_REVIEW_ONLY",
            },
            capability="NURSING",
        )
        return result

    async def infusion_witness(self, identifier, body):
        await self.phase5()
        source = await self.linked(identifier, "infusion_event", body["patient_id"])
        data = self.content(source)
        await self.guard(
            "NURSING",
            patient_id=source["patient_id"],
            encounter_id=source["encounter_id"],
            write=True,
        )
        require(data["witness_id"] == self.actor["id"] and body["action"] in {"ATTEST", "DISPUTE"})
        return await self.create(
            "infusion_witness",
            {**body, "source_id": identifier, "witness_id": self.actor["id"]},
            patient_id=source["patient_id"],
            encounter_id=source["encounter_id"],
            service=source["service"],
            status="RECORDED",
            unique_value=identifier + ":" + self.actor["id"],
            contract="LWH-EXT-CLINICAL-039",
        )
