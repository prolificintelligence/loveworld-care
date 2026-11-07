"""Frozen cohorts and independently released, disclosure-controlled snapshots."""

import csv
import io
import json
from decimal import ROUND_HALF_EVEN, Decimal

from sqlalchemy import func, select

from .. import db
from ..domain import require
from . import store as s
from . import tables as t
from .service import GLOBAL, ReportingService, catalogue, current, decimal, measured


def inside(child, parent):
    if parent["scope_type"] == "GLOBAL":
        return True
    if (child["scope_type"], child["scope_id"]) == (parent["scope_type"], parent["scope_id"]):
        return True
    return (parent["scope_type"] == "REGION" and child.get("region_id") == parent["scope_id"]) or (
        parent["scope_type"] == "ZONE" and child.get("zone_id") == parent["scope_id"]
    )


def csv_safe(value):
    text = "" if value is None else str(value)
    return (
        "'" + text
        if text.lstrip(" \t\r\n\x00\ufeff").startswith(("=", "+", "-", "@"))
        or text.startswith(("\t", "\r", "\n", "\x00"))
        else text
    )


class AnalyticsService(ReportingService):
    async def policy(self, body):
        self.governor()
        registered = {metric["metric_id"] for metric in catalogue()}
        require(
            set(body["allowed_metric_ids"]).issubset(registered)
            and body["valid_from"] < body["valid_until"],
            "VALIDATION_FAILED",
            "Use registered metrics and ordered disclosure-policy validity",
            422,
        )
        row = {
            "id": db.uid(),
            "name": body["name"],
            "policy_version": body["policy_version"],
            "payload": body,
            "adopted_by": self.actor["id"],
            "created_at": db.now(),
        }
        await self.session.execute(t.policies.insert().values(**row))
        await self.log("DISCLOSURE_POLICY", row, "analytics.disclosure_policy_adopted", GLOBAL)
        return row

    async def revoke_policy(self, identifier, body):
        self.governor()
        await s.load(self.session, t.policies, identifier)
        row = {
            "id": db.uid(),
            "policy_id": identifier,
            "reason": body["evidence"],
            "actor_id": self.actor["id"],
            "created_at": db.now(),
        }
        await self.session.execute(t.policy_revocations.insert().values(**row))
        await self.log("POLICY_REVOCATION", row, "analytics.disclosure_policy_revoked", GLOBAL)
        return row

    async def active_policy(self, identifier):
        row = await s.load(self.session, t.policies, identifier)
        revoked = await self.session.scalar(
            select(t.policy_revocations.c.id).where(t.policy_revocations.c.policy_id == identifier)
        )
        require(
            current(row["payload"]) and not revoked,
            "DISCLOSURE_POLICY_UNAVAILABLE",
            "An adopted, current, unrevoked disclosure policy is required",
            403,
        )
        return row

    async def cohort_for(
        self, identifier, roles=s.ANALYSTS | s.REVIEWERS | s.GOVERNORS | s.LEADERS | s.PROGRAMMES
    ):
        row = await s.load(self.session, t.cohorts, identifier)
        s.require_role(self.actor, roles, row)
        return row

    async def cohort(self, body):
        scope = await self.scope(body, s.ANALYSTS)
        policy = await self.active_policy(body["policy_id"])
        require(
            len(set(body["obligation_ids"])) == len(body["obligation_ids"]),
            "DUPLICATE_UNIT",
            "Select each expected unit-period once",
            422,
        )
        reference = None
        for identifier in body["obligation_ids"]:
            obligation = await self.obligation(identifier, s.ANALYSTS)
            require(
                inside(obligation, scope),
                "COHORT_SCOPE_MISMATCH",
                "Every obligation must belong to the named frozen cohort scope",
                422,
            )
            signature = (
                obligation["stream"],
                obligation["period_start"],
                obligation["period_end"],
                obligation["timezone"],
                tuple(obligation["definition_ids"]),
            )
            if reference is None:
                reference = signature
            require(
                reference == signature,
                "COHORT_NOT_COMPARABLE",
                "A cohort requires aligned periods, streams, time zones and exact definition versions",
                422,
            )
            for definition in (await self.adopted_definitions(obligation)).values():
                require(
                    definition["metric_id"] in policy["payload"]["allowed_metric_ids"],
                    "METRIC_NOT_APPROVED_FOR_DISCLOSURE",
                    "The disclosure policy does not authorise every selected indicator",
                    422,
                )
        row = {
            "id": db.uid(),
            **scope,
            "name": body["name"],
            "obligation_ids": body["obligation_ids"],
            "policy_id": body["policy_id"],
            "created_by": self.actor["id"],
            "created_at": db.now(),
        }
        await self.session.execute(t.cohorts.insert().values(**row))
        await self.log("COHORT", row, "analytics.cohort_frozen", scope)
        return row

    async def sealed_return(self, row):
        version = (
            (
                await self.session.execute(
                    select(t.versions).where(
                        t.versions.c.return_id == row["id"], t.versions.c.version == row["version"]
                    )
                )
            )
            .mappings()
            .first()
        )
        newest = await self.session.scalar(
            select(func.max(t.versions.c.version)).where(t.versions.c.return_id == row["id"])
        )
        require(
            version and newest == row["version"],
            "SOURCE_INTEGRITY_FAILURE",
            "The current source version does not match retained reporting history",
            503,
        )
        source = self.data(version)
        for key in ("state", "source_hash", "version", "submitted_by", "verified_by"):
            require(
                source["return"][key] == row[key],
                "SOURCE_INTEGRITY_FAILURE",
                "Current reporting state differs from its retained version",
                503,
            )
        require(
            row["state"] != "VERIFIED"
            or (
                row["verified_by"]
                and row["verified_by"] not in {row["submitted_by"], row["created_by"]}
            ),
            "SOURCE_INTEGRITY_FAILURE",
            "Verified sources require independent retained review",
            503,
        )
        return source["data"]

    async def build_snapshot(self, cohort_id):
        cohort = await self.cohort_for(cohort_id, s.ANALYSTS)
        await self.active_policy(cohort["policy_id"])
        obligations = [
            await self.obligation(identifier, s.ANALYSTS) for identifier in cohort["obligation_ids"]
        ]
        definitions = await self.adopted_definitions(obligations[0])
        inputs, statuses, values = [], [], {identifier: [] for identifier in definitions}
        for obligation in obligations:
            row = (
                (
                    await self.session.execute(
                        select(t.returns).where(t.returns.c.obligation_id == obligation["id"])
                    )
                )
                .mappings()
                .first()
            )
            item = {
                "obligation_id": obligation["id"],
                "return_id": row["id"] if row else None,
                "return_version": row["version"] if row else None,
                "state": row["state"] if row else "MISSING",
                "late": bool(
                    row and row["received_at"] and row["received_at"] > obligation["due_at"]
                ),
            }
            if row and row["state"] == "VERIFIED":
                data = await self.sealed_return(row)
                item["source_hash"] = row["source_hash"]
                inputs.append(item)
                classifications = {value["completeness"] for value in data["values"]}
                item["completeness"] = (
                    "COMPLETE" if classifications.issubset({"VALUE", "NIL"}) else "PARTIAL"
                )
                for value in data["values"]:
                    values[value["definition_id"]].append(value)
            statuses.append(item)
        cells = []
        for identifier, definition in definitions.items():
            rule = definition["payload"]
            source_values = values[identifier]
            usable = [
                (value, measured(value, rule))
                for value in source_values
                if value["completeness"] in {"VALUE", "NIL", "PARTIAL"}
            ]
            usable = [(value, number) for value, number in usable if number is not None]
            coverage = {
                "expected": len(obligations),
                "known": len(usable),
                "nil": sum(v["completeness"] == "NIL" for v in source_values),
                "partial": sum(v["completeness"] == "PARTIAL" for v in source_values),
                "unknown": sum(v["completeness"] == "UNKNOWN" for v in source_values),
                "missing": len(obligations)
                - len(source_values)
                + sum(v["completeness"] == "MISSING" for v in source_values),
                "not_applicable": sum(v["completeness"] == "NOT_APPLICABLE" for v in source_values),
            }
            number, numerator, denominator, absent = None, None, None, None
            if not usable:
                absent = "NO_VERIFIED_USABLE_VALUES"
            elif rule["aggregation"] == "NONE" and len(usable) > 1:
                absent = "NON_ADDITIVE_RECONCILIATION_REQUIRED"
            elif rule["aggregation"] == "RATIO_OF_SUMS":
                numerator = sum((decimal(v["numerator"]) for v, _ in usable), Decimal(0))
                denominator = sum((decimal(v["denominator"]) for v, _ in usable), Decimal(0))
                if denominator:
                    number = (numerator / denominator * decimal(rule["scale"])).quantize(
                        Decimal("0.00000001"), rounding=ROUND_HALF_EVEN
                    )
                else:
                    absent = "DENOMINATOR_UNAVAILABLE"
            elif rule["formula"] == "RATIO":
                numerator, denominator = (
                    decimal(usable[0][0]["numerator"]),
                    decimal(usable[0][0]["denominator"]),
                )
                number = usable[0][1]
            else:
                number = sum((number for _, number in usable), Decimal(0))
            cells.append(
                {
                    "definition_id": identifier,
                    "metric_id": definition["metric_id"],
                    "definition_version": definition["definition_version"],
                    "name": definition["name"],
                    "unit": rule["unit"],
                    "formula": rule["formula"],
                    "aggregation": rule["aggregation"],
                    "population_definition": rule["population_definition"],
                    "inclusion_exclusion": rule["inclusion_exclusion"],
                    "less_or_equal_metric": rule.get("less_or_equal_metric"),
                    "coverage": coverage,
                    "value": str(number) if number is not None else None,
                    "numerator": str(numerator) if numerator is not None else None,
                    "denominator": str(denominator) if denominator is not None else None,
                    "absent_reason": absent,
                }
            )
        previous_version = (
            await self.session.scalar(
                select(func.max(t.snapshots.c.version)).where(t.snapshots.c.cohort_id == cohort_id)
            )
            or 0
        )
        payload = {
            "schema_version": "LWH-ANALYTICS-1",
            "cohort_id": cohort_id,
            "cohort_name": cohort["name"],
            "period_start": obligations[0]["period_start"],
            "period_end": obligations[0]["period_end"],
            "timezone": obligations[0]["timezone"],
            "stream": obligations[0]["stream"],
            "policy_id": cohort["policy_id"],
            "obligation_ids": cohort["obligation_ids"],
            "coverage": {
                "expected": len(obligations),
                "verified": len(inputs),
                "complete": sum(item.get("completeness") == "COMPLETE" for item in statuses),
                "partial": sum(item.get("completeness") == "PARTIAL" for item in statuses),
                "late": sum(item["late"] for item in statuses),
                "missing": sum(item["state"] == "MISSING" for item in statuses),
                "unverified": sum(
                    item["state"] not in {"MISSING", "VERIFIED"} for item in statuses
                ),
            },
            "sources": statuses,
            "cells": cells,
            "prepared_at": db.now(),
            "rule_version": "LWH-DISCLOSURE-1",
        }
        row = {
            "id": db.uid(),
            "cohort_id": cohort_id,
            "version": previous_version + 1,
            "payload_ciphertext": self.box.encrypt(s.canonical(payload)),
            "source_hash": s.digest(statuses),
            "created_by": self.actor["id"],
            "created_at": db.now(),
        }
        await self.session.execute(t.snapshots.insert().values(**row))
        for item in inputs:
            await self.session.execute(
                t.snapshot_inputs.insert().values(
                    id=db.uid(),
                    snapshot_id=row["id"],
                    return_id=item["return_id"],
                    return_version=item["return_version"],
                )
            )
        await self.log("SNAPSHOT", row, "analytics.snapshot_prepared", cohort)
        return {key: value for key, value in row.items() if key != "payload_ciphertext"} | {
            "coverage": payload["coverage"]
        }

    async def disclosure(self, row, payload, policy):
        cells = [dict(cell) for cell in payload["cells"]]
        for cell in cells:
            coverage, reason = cell["coverage"], cell["absent_reason"]
            if coverage["known"] < policy["minimum_units"]:
                reason = "SUPPRESSED_MINIMUM_REPORTING_UNITS"
            elif not policy["allow_partial"] and (
                coverage["known"] < coverage["expected"] or coverage["partial"]
            ):
                reason = "INCOMPLETE_COHORT_WITHHELD"
            elif cell["value"] is not None:
                sensitive = (
                    [decimal(cell["numerator"]), decimal(cell["denominator"])]
                    if cell["formula"] == "RATIO"
                    else [decimal(cell["value"])]
                )
                if any(
                    number is not None and 0 < number < policy["minimum_cell"]
                    for number in sensitive
                ):
                    reason = "SUPPRESSED_SMALL_CELL"
            cell["disclosure_status"] = reason or "VISIBLE"
        previous = (
            await self.session.execute(
                select(t.snapshot_reviews).where(t.snapshot_reviews.c.decision == "RELEASE")
            )
        ).mappings()
        for release in previous:
            old = json.loads(self.box.decrypt(release["published_ciphertext"]))
            if (old["period_start"], old["period_end"], old["stream"]) != (
                payload["period_start"],
                payload["period_end"],
                payload["stream"],
            ):
                continue
            other = await s.load(self.session, t.snapshots, release["snapshot_id"])
            other_cohort = await s.load(self.session, t.cohorts, other["cohort_id"])
            new_units, old_units = (
                set(payload["obligation_ids"]),
                set(other_cohort["obligation_ids"]),
            )
            if not new_units & old_units:
                continue
            old_cells = {cell["metric_id"]: cell for cell in old["cells"]}
            for cell in cells:
                before = old_cells.get(cell["metric_id"])
                if (
                    cell["disclosure_status"] != "VISIBLE"
                    or not before
                    or before["disclosure_status"] != "VISIBLE"
                ):
                    continue
                if before["definition_version"] != cell["definition_version"] or not (
                    new_units.issubset(old_units) or old_units.issubset(new_units)
                ):
                    cell["disclosure_status"] = "SUPPRESSED_OVERLAPPING_COHORT"
                    continue
                remaining = len(new_units ^ old_units)
                parts = ("numerator", "denominator") if cell["formula"] == "RATIO" else ("value",)
                differences = [
                    abs(decimal(cell[part]) - decimal(before[part]))
                    for part in parts
                    if cell[part] is not None and before[part] is not None
                ]
                if (remaining and remaining < policy["minimum_units"]) or any(
                    0 < difference < policy["minimum_change"] for difference in differences
                ):
                    cell["disclosure_status"] = "SUPPRESSED_DIFFERENCING"
        # A related total/subtotal component is withheld together, so subtraction
        # cannot reconstruct a hidden child through this API or its exports.
        changed = True
        while changed:
            changed = False
            by_metric = {cell["metric_id"]: cell for cell in cells}
            for cell in cells:
                parent = by_metric.get(cell.get("less_or_equal_metric"))
                if parent and (
                    (cell["disclosure_status"] == "VISIBLE")
                    != (parent["disclosure_status"] == "VISIBLE")
                ):
                    target = cell if cell["disclosure_status"] == "VISIBLE" else parent
                    target["disclosure_status"] = "SUPPRESSED_COMPLEMENTARY"
                    changed = True
        for cell in cells:
            if cell["disclosure_status"] != "VISIBLE":
                for key in ("value", "numerator", "denominator"):
                    cell[key] = None
            cell.pop("less_or_equal_metric", None)
        return {
            key: value
            for key, value in payload.items()
            if key not in {"cells", "sources", "obligation_ids"}
        } | {
            "cells": cells,
            "snapshot_id": row["id"],
            "snapshot_version": row["version"],
            "source_hash": row["source_hash"],
            "disclosure_policy_version": policy["policy_version"],
            "released_at": db.now(),
            "interpretation": "Verified reporting sources only. Contacts are not unique people or population incidence. Coverage and suppressed values remain explicit; no causal or anonymity guarantee is inferred.",
        }

    async def snapshot_review(self, identifier, body):
        row = await s.load(self.session, t.snapshots, identifier)
        cohort = await self.cohort_for(row["cohort_id"], s.REVIEWERS)
        require(
            row["created_by"] != self.actor["id"],
            "INDEPENDENT_REVIEW_REQUIRED",
            "Another reviewer must release this snapshot",
            403,
        )
        policy = await self.active_policy(cohort["policy_id"])
        require(
            not await self.session.scalar(
                select(t.snapshot_reviews.c.id).where(
                    t.snapshot_reviews.c.snapshot_id == identifier
                )
            ),
            "ALREADY_REVIEWED",
            "Prepare a new snapshot version after a final release/rejection",
            409,
        )
        payload = self.data(row)
        for source in payload["sources"]:
            current_return = (
                (
                    await self.session.execute(
                        select(t.returns).where(
                            t.returns.c.obligation_id == source["obligation_id"]
                        )
                    )
                )
                .mappings()
                .first()
            )
            require(
                (current_return["version"] if current_return else None) == source["return_version"]
                and (current_return["state"] if current_return else "MISSING") == source["state"],
                "SNAPSHOT_SOURCE_CHANGED",
                "A source changed; prepare a new reconciled snapshot",
                409,
            )
            if current_return and current_return["state"] == "VERIFIED":
                await self.sealed_return(current_return)
        public = (
            await self.disclosure(row, payload, policy["payload"])
            if body["decision"] == "RELEASE"
            else None
        )
        review = {
            "id": db.uid(),
            "snapshot_id": identifier,
            "reviewer_id": self.actor["id"],
            "decision": body["decision"],
            "reason": body["reason"],
            "published_ciphertext": self.box.encrypt(s.canonical(public)) if public else None,
            "published_hash": s.digest(public) if public else None,
            "created_at": db.now(),
        }
        await self.session.execute(t.snapshot_reviews.insert().values(**review))
        await self.log(
            "SNAPSHOT_REVIEW",
            review,
            "analytics.snapshot_released" if public else "analytics.snapshot_rejected",
            cohort,
            "LWH-EVT-011" if public else None,
        )
        return {
            "id": identifier,
            "decision": body["decision"],
            "published_hash": review["published_hash"],
            "cohort_id": cohort["id"],
        }

    async def snapshot_public(self, identifier):
        row = await s.load(self.session, t.snapshots, identifier)
        cohort = await self.cohort_for(row["cohort_id"])
        await self.active_policy(cohort["policy_id"])
        review = (
            (
                await self.session.execute(
                    select(t.snapshot_reviews).where(
                        t.snapshot_reviews.c.snapshot_id == identifier,
                        t.snapshot_reviews.c.decision == "RELEASE",
                    )
                )
            )
            .mappings()
            .first()
        )
        require(review, "NOT_RELEASED", "A snapshot is visible only after independent release", 404)
        payload = json.loads(self.box.decrypt(review["published_ciphertext"]))
        require(
            s.digest(payload) == review["published_hash"],
            "SNAPSHOT_INTEGRITY_FAILURE",
            "Released snapshot integrity check failed",
            503,
        )
        invalidated = await self.session.scalar(
            select(func.count())
            .select_from(t.invalidations)
            .where(t.invalidations.c.snapshot_id == identifier)
        )
        payload["freshness"] = (
            "STALE_SOURCE_CORRECTION" if invalidated else "RELEASED_AS_OF_RECORDED_TIME"
        )
        payload["current_eligible"] = not bool(invalidated)
        await s.audit(
            self.session,
            self.actor,
            "analytics.released_snapshot_read",
            cohort,
            identifier,
            self.correlation,
            purpose="LEADERSHIP_AGGREGATE_OVERSIGHT",
        )
        return payload

    async def export_snapshot(self, identifier):
        payload = await self.snapshot_public(identifier)
        stream = io.StringIO(newline="")
        writer = csv.writer(stream)
        writer.writerow(
            [
                "snapshot_id",
                "metric_id",
                "definition_version",
                "period_start",
                "period_end",
                "unit",
                "value",
                "numerator",
                "denominator",
                "disclosure_status",
                "expected_units",
                "known_units",
                "freshness",
            ]
        )
        for cell in payload["cells"]:
            writer.writerow(
                [
                    csv_safe(value)
                    for value in [
                        identifier,
                        cell["metric_id"],
                        cell["definition_version"],
                        payload["period_start"],
                        payload["period_end"],
                        cell["unit"],
                        cell["value"],
                        cell["numerator"],
                        cell["denominator"],
                        cell["disclosure_status"],
                        cell["coverage"]["expected"],
                        cell["coverage"]["known"],
                        payload["freshness"],
                    ]
                ]
            )
        return stream.getvalue()
