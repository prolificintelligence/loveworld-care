"""Versioned obligations, retained imports, clinical extracts and independent verification."""

import csv
import io
import json
from decimal import ROUND_HALF_EVEN, Decimal
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import select, update

from .. import db
from ..clinical import tables as clinical
from ..domain import RuleError, require
from . import contracts as c
from . import store as s
from . import tables as t

RULE_VERSION = "LWH-REPORTING-VALIDATION-1"
GLOBAL = {"scope_type": "GLOBAL", "scope_id": "GLOBAL"}


def catalogue():
    return json.loads(Path(__file__).with_name("metric_catalog.json").read_text(encoding="utf-8"))


def current(payload):
    return payload["valid_from"] <= db.now() < payload["valid_until"]


def decimal(value):
    return Decimal(str(value)) if value is not None else None


def measured(value, definition):
    if value["completeness"] in {"UNKNOWN", "MISSING", "NOT_APPLICABLE"}:
        return None
    if definition["formula"] == "RATIO":
        numerator, denominator = decimal(value.get("numerator")), decimal(value.get("denominator"))
        if numerator is None or denominator is None or denominator <= 0:
            return None
        return (numerator / denominator * decimal(definition["scale"])).quantize(
            Decimal("0.00000001"), rounding=ROUND_HALF_EVEN
        )
    return decimal(value.get("value"))


class ReportingService:
    def __init__(self, session, cfg, box, actor, correlation):
        self.session, self.cfg, self.box, self.actor, self.correlation = (
            session,
            cfg,
            box,
            actor,
            correlation,
        )

    def governor(self):
        s.require_role(self.actor, s.GOVERNORS, GLOBAL)

    async def scope(self, body, roles):
        scope = await s.scope_for(self.session, body["scope_type"], body.get("scope_id"))
        s.require_role(self.actor, roles, scope)
        return scope

    async def obligation(self, identifier, roles=s.SOURCE_READERS):
        row = await s.load(self.session, t.obligations, identifier)
        s.require_role(self.actor, roles, row)
        return row

    async def return_for(self, identifier, roles=s.SOURCE_READERS):
        row = await s.load(self.session, t.returns, identifier, lock=True)
        return row, await self.obligation(row["obligation_id"], roles)

    async def adopted_definitions(self, obligation):
        rows = [
            await s.load(self.session, t.definitions, identifier)
            for identifier in obligation["definition_ids"]
        ]
        return {row["id"]: row for row in rows}

    def data(self, row):
        return json.loads(self.box.decrypt(row["payload_ciphertext"]))

    async def log(self, kind, row, action, scope, contract=None, content=None):
        await s.journal(
            self.session,
            self.cfg,
            self.box,
            self.actor,
            kind,
            row,
            action,
            scope,
            self.correlation,
            contract,
            content,
        )

    async def definition(self, body):
        self.governor()
        require(
            body["metric_id"] in {metric["metric_id"] for metric in catalogue()},
            "UNKNOWN_METRIC",
            "Use a registered suite metric identifier",
            422,
        )
        row = {
            "id": db.uid(),
            "metric_id": body["metric_id"],
            "definition_version": body["definition_version"],
            "name": body["name"],
            "stream": body["stream"],
            "payload": body,
            "adopted_by": self.actor["id"],
            "created_at": db.now(),
        }
        await self.session.execute(t.definitions.insert().values(**row))
        await self.log("DEFINITION", row, "reporting.definition_adopted", GLOBAL)
        return row

    async def create_obligation(self, body):
        self.governor()
        scope = await s.scope_for(
            self.session, body["scope_type"], body["scope_id"], at=body["period_start"]
        )
        binding = None
        if body.get("template_id"):
            from .templates import TemplateService

            binding = await TemplateService(self).bind(body, scope)
        expected_scope = {
            "FACILITY_ACTIVITY": "FACILITY",
            "ZONE_COMMUNITY": "ZONE",
            "REGIONAL_COORDINATION": "REGION",
        }[body["stream"]]
        require(
            body["scope_type"] == expected_scope,
            "STREAM_SCOPE_MISMATCH",
            "Keep facility, community and regional reporting streams distinct",
            422,
        )
        require(
            len(set(body["definition_ids"])) == len(body["definition_ids"]),
            "DUPLICATE_DEFINITION",
            "Select each indicator definition once",
            422,
        )
        metrics = set()
        for identifier in body["definition_ids"]:
            definition = await s.load(self.session, t.definitions, identifier)
            payload = definition["payload"]
            require(
                definition["stream"] == body["stream"]
                and payload["valid_from"] <= body["period_start"]
                and payload["valid_until"] >= body["period_end"],
                "DEFINITION_NOT_APPLICABLE",
                "Definitions must cover the actual reporting stream and period",
                422,
            )
            require(
                definition["metric_id"] not in metrics,
                "DUPLICATE_METRIC",
                "One authoritative definition per indicator and obligation is required",
                422,
            )
            metrics.add(definition["metric_id"])
        for identifier in body["definition_ids"]:
            definition = await s.load(self.session, t.definitions, identifier)
            parent = definition["payload"].get("less_or_equal_metric")
            require(
                not parent or parent in metrics,
                "RELATED_TOTAL_REQUIRED",
                "Include the adopted comparison total in this obligation",
                422,
            )
            if parent:
                comparisons = [
                    await s.load(self.session, t.definitions, item)
                    for item in body["definition_ids"]
                ]
                parent_rule = next(
                    item["payload"] for item in comparisons if item["metric_id"] == parent
                )
                rule = definition["payload"]
                require(
                    rule["unit"] == parent_rule["unit"]
                    and rule["formula"] == parent_rule["formula"] == "COUNT",
                    "RELATED_TOTAL_UNIT_MISMATCH",
                    "Subtotal comparisons require count measures in the same unit",
                    422,
                )
        overlap = await self.session.scalar(
            select(t.obligations.c.id)
            .where(
                t.obligations.c.scope_type == scope["scope_type"],
                t.obligations.c.scope_id == scope["scope_id"],
                t.obligations.c.stream == body["stream"],
                t.obligations.c.period_start < body["period_end"],
                t.obligations.c.period_end > body["period_start"],
            )
            .limit(1)
        )
        require(
            not overlap,
            "OVERLAPPING_OBLIGATION",
            "An overlapping unit/stream obligation already exists; retain one authority for each reporting period",
            409,
        )
        values = {
            key: body[key]
            for key in (
                "stream",
                "period_start",
                "period_end",
                "due_at",
                "timezone",
                "definition_ids",
                "adoption_reference",
            )
        }
        row = {
            "id": db.uid(),
            **scope,
            **values,
            "created_by": self.actor["id"],
            "created_at": db.now(),
        }
        await self.session.execute(t.obligations.insert().values(**row))
        if binding:
            await self.log(
                "OBLIGATION_TEMPLATE",
                {"id": row["id"], "version": 1, "template": binding},
                "reporting.obligation_template_bound",
                scope,
            )
        await self.log("OBLIGATION", row, "reporting.obligation_opened", scope)
        return row

    async def findings(self, body, obligation, definitions):
        findings = []
        values = body["values"]
        supplied = [v["definition_id"] for v in values]
        require(
            set(supplied) == set(definitions) and len(supplied) == len(definitions),
            "INDICATOR_SET_MISMATCH",
            "Declare every expected indicator exactly once, using explicit missingness where needed",
            422,
        )
        metric_values = {}
        for value in values:
            definition = definitions[value["definition_id"]]
            rule = definition["payload"]
            number = measured(value, rule)
            metric_values[definition["metric_id"]] = (number, value, rule)

            def finding(
                code,
                severity,
                message,
                definition_id=value["definition_id"],
                metric_id=definition["metric_id"],
            ):
                findings.append(
                    {
                        "id": f"{definition_id}:{code}",
                        "definition_id": definition_id,
                        "metric_id": metric_id,
                        "severity": severity,
                        "code": code,
                        "message": message,
                    }
                )

            status = value["completeness"]
            if status in {"VALUE", "NIL"} and number is None:
                finding(
                    "VALUE_REQUIRED",
                    "BLOCKING",
                    "Supply the declared value or a usable numerator and denominator",
                )
            if status == "NIL" and rule["formula"] != "COUNT":
                finding(
                    "NIL_COUNT_ONLY",
                    "BLOCKING",
                    "Nil means an attested absence of qualifying count events; undefined rates are unavailable",
                )
            if (
                rule["formula"] == "COUNT"
                and number is not None
                and number != number.to_integral_value()
            ):
                finding(
                    "COUNT_NOT_INTEGER", "BLOCKING", "Count indicators require whole event counts"
                )
            if rule["formula"] != "RATIO" and (
                value.get("numerator") is not None or value.get("denominator") is not None
            ):
                finding(
                    "UNEXPECTED_RATIO_PARTS",
                    "BLOCKING",
                    "Do not mix count/decimal and ratio input contracts",
                )
            if rule["formula"] == "RATIO" and number is not None:
                supplied_number = decimal(value.get("value"))
                if supplied_number is not None and supplied_number != number:
                    finding(
                        "ARITHMETIC_MISMATCH",
                        "BLOCKING",
                        "The declared rate must equal its governed numerator/denominator formula",
                    )
                if rule.get("numerator_is_subset") and decimal(value["numerator"]) > decimal(
                    value["denominator"]
                ):
                    finding(
                        "NUMERATOR_EXCEEDS_TOTAL",
                        "BLOCKING",
                        "The adopted subset numerator cannot exceed its total",
                    )
            if (
                number is not None
                and rule.get("maximum_value") is not None
                and number > decimal(rule["maximum_value"])
            ):
                finding(
                    "ADOPTED_LIMIT_EXCEEDED",
                    "BLOCKING",
                    "The value exceeds the adopted indicator limit",
                )
            if (
                number is not None
                and not value.get("source_reference")
                and not value.get("extract_id")
            ):
                finding(
                    "SOURCE_REQUIRED",
                    "BLOCKING",
                    "Record the actual source or governed extract reference",
                )
            if status in {"UNKNOWN", "MISSING", "PARTIAL", "NOT_APPLICABLE"}:
                finding(
                    "LIMITED_COVERAGE",
                    "INFORMATIONAL",
                    "Coverage is limited and will remain visible in every downstream view",
                )
            if value.get("extract_id"):
                extract = await s.load(self.session, t.extracts, value["extract_id"])
                require(
                    extract["obligation_id"] == obligation["id"],
                    "EXTRACT_SCOPE_MISMATCH",
                    "Use an extract for this exact obligation",
                    422,
                )
                extract_value = self.data(extract)["values"].get(value["definition_id"])
                require(
                    extract_value is not None,
                    "EXTRACT_INDICATOR_MISMATCH",
                    "The extract does not support this indicator",
                    422,
                )
                if number is not None and number != decimal(extract_value["value"]):
                    finding(
                        "EXTRACT_DISCREPANCY",
                        "WARNING",
                        "Declared and extracted values differ; independent reconciliation evidence is required",
                    )
            if number is not None and rule.get("warning_change_fraction") is not None:
                earlier = (
                    (
                        await self.session.execute(
                            select(t.returns, t.obligations.c.period_end)
                            .join(t.obligations)
                            .where(
                                t.obligations.c.scope_type == obligation["scope_type"],
                                t.obligations.c.scope_id == obligation["scope_id"],
                                t.obligations.c.stream == obligation["stream"],
                                t.obligations.c.period_end <= obligation["period_start"],
                                t.returns.c.state == "VERIFIED",
                            )
                            .order_by(t.obligations.c.period_end.desc())
                            .limit(1)
                        )
                    )
                    .mappings()
                    .first()
                )
                if earlier:
                    previous = next(
                        (
                            v
                            for v in self.data(earlier)["values"]
                            if v["definition_id"] == value["definition_id"]
                        ),
                        None,
                    )
                    old = measured(previous, rule) if previous else None
                    if old is not None and (
                        (old == 0 and number != 0)
                        or (
                            old > 0
                            and abs(number - old) / old > decimal(rule["warning_change_fraction"])
                        )
                    ):
                        finding(
                            "HISTORICAL_CHANGE",
                            "WARNING",
                            "Change exceeds the adopted review threshold; this is a review flag, not an outbreak classification",
                        )
        for metric, (number, value, rule) in metric_values.items():
            parent = rule.get("less_or_equal_metric")
            parent_number = metric_values[parent][0] if parent in metric_values else None
            if number is not None and parent_number is not None and number > parent_number:
                findings.append(
                    {
                        "id": f"{value['definition_id']}:SUBTOTAL_EXCEEDS_TOTAL",
                        "definition_id": value["definition_id"],
                        "metric_id": metric,
                        "severity": "BLOCKING",
                        "code": "SUBTOTAL_EXCEEDS_TOTAL",
                        "message": "The adopted subtotal exceeds its corresponding total",
                    }
                )
        return findings

    async def save_version(self, row, obligation, data, action, contract=None):
        await self.invalidate_obligation(row, obligation, action)
        await self.session.execute(
            t.versions.insert().values(
                id=db.uid(),
                return_id=row["id"],
                version=row["version"],
                payload_ciphertext=self.box.encrypt(
                    s.canonical({"return": row, "data": data, "obligation": obligation})
                ),
                source_hash=row["source_hash"],
                actor_id=self.actor["id"],
                created_at=db.now(),
            )
        )
        await self.log("RETURN", row, action, obligation, contract, data)

    async def invalidate_obligation(self, row, obligation, reason):
        # Coverage is evidence too: a late first receipt changes an earlier
        # snapshot even when that snapshot had no verified input for this unit.
        identifiers = []
        cohorts = (await self.session.execute(select(t.cohorts))).mappings()
        for cohort in cohorts:
            if obligation["id"] not in cohort["obligation_ids"]:
                continue
            for snapshot_id in (
                await self.session.execute(
                    select(t.snapshots.c.id).where(t.snapshots.c.cohort_id == cohort["id"])
                )
            ).scalars():
                identifiers.append(snapshot_id)
                existing = await self.session.scalar(
                    select(t.invalidations.c.id).where(
                        t.invalidations.c.snapshot_id == snapshot_id,
                        t.invalidations.c.return_id == row["id"],
                        t.invalidations.c.return_version == row["version"],
                    )
                )
                if not existing:
                    await self.session.execute(
                        t.invalidations.insert().values(
                            id=db.uid(),
                            snapshot_id=snapshot_id,
                            return_id=row["id"],
                            return_version=row["version"],
                            reason=reason,
                            created_at=db.now(),
                        )
                    )
        return identifiers

    async def validate(self, row, obligation, data):
        definitions = await self.adopted_definitions(obligation)
        findings = await self.findings(data, obligation, definitions)
        run = {
            "id": db.uid(),
            "return_id": row["id"],
            "return_version": row["version"],
            "rule_version": RULE_VERSION,
            "source_hash": row["source_hash"],
            "findings": findings,
            "created_at": db.now(),
        }
        await self.session.execute(t.validation_runs.insert().values(**run))
        await self.session.execute(
            update(t.returns).where(t.returns.c.id == row["id"]).values(validation_id=run["id"])
        )
        row["validation_id"] = run["id"]
        return run

    async def draft(self, obligation_id, body):
        obligation = await self.obligation(obligation_id, s.REPORTERS)
        require(
            obligation["period_end"] <= db.now(),
            "PERIOD_NOT_ENDED",
            "An attested reporting period must have ended before its return is prepared",
            409,
        )
        existing = (
            (
                await self.session.execute(
                    select(t.returns)
                    .where(t.returns.c.obligation_id == obligation_id)
                    .with_for_update()
                )
            )
            .mappings()
            .first()
        )
        definitions = await self.adopted_definitions(obligation)
        await self.findings(body, obligation, definitions)
        if existing:
            require(
                existing["state"] in {"DRAFT", "RETURNED_FOR_CORRECTION"},
                "INVALID_STATE",
                "Open a reasoned correction before editing submitted or verified information",
                409,
            )
            row = await s.amend(
                self.session,
                t.returns,
                dict(existing),
                {
                    "state": "DRAFT",
                    "payload_ciphertext": self.box.encrypt(s.canonical(body)),
                    "source_hash": s.digest(
                        {"values": body["values"], "definitions": obligation["definition_ids"]}
                    ),
                    "updated_at": db.now(),
                    "verified_by": None,
                    "verified_at": None,
                },
                body["expected_version"],
            )
        else:
            require(
                body["expected_version"] == 0,
                "VERSION_CONFLICT",
                "The return does not yet exist; reload before creating it",
                412,
            )
            row = {
                "id": db.uid(),
                "obligation_id": obligation_id,
                "version": 1,
                "state": "DRAFT",
                "payload_ciphertext": self.box.encrypt(s.canonical(body)),
                "source_hash": s.digest(
                    {"values": body["values"], "definitions": obligation["definition_ids"]}
                ),
                "created_by": self.actor["id"],
                "submitted_by": None,
                "received_at": None,
                "verified_by": None,
                "verified_at": None,
                "validation_id": None,
                "updated_at": db.now(),
            }
            await self.session.execute(t.returns.insert().values(**row))
        run = await self.validate(row, obligation, body)
        await self.save_version(row, obligation, body, "reporting.return_drafted")
        return {**s.opened(self.box, row), "validation": run}

    async def submit(self, identifier, body):
        row, obligation = await self.return_for(identifier, s.REPORTERS)
        require(
            row["state"] == "DRAFT",
            "INVALID_STATE",
            "Only a current draft can be attested and submitted",
            409,
        )
        data = self.data(row)
        definitions = await self.adopted_definitions(obligation)
        findings = await self.findings(data, obligation, definitions)
        require(
            not any(f["severity"] == "BLOCKING" for f in findings),
            "VALIDATION_BLOCKED",
            "Resolve blocking validation findings before submission",
            409,
        )
        row = await s.amend(
            self.session,
            t.returns,
            row,
            {
                "state": "SUBMITTED",
                "submitted_by": self.actor["id"],
                "received_at": db.now(),
                "updated_at": db.now(),
            },
            body["expected_version"],
        )
        data["attestation"] = {**body, "actor_id": self.actor["id"], "at": db.now()}
        row["payload_ciphertext"] = self.box.encrypt(s.canonical(data))
        await self.session.execute(
            update(t.returns)
            .where(t.returns.c.id == identifier)
            .values(payload_ciphertext=row["payload_ciphertext"])
        )
        run = await self.validate(row, obligation, data)
        await self.save_version(row, obligation, data, "reporting.return_submitted", "LWH-EVT-007")
        return {
            **s.opened(self.box, row),
            "validation": run,
            "late": row["received_at"] > obligation["due_at"],
        }

    async def review(self, identifier, body):
        row, obligation = await self.return_for(identifier, s.REVIEWERS)
        require(
            row["state"] == "SUBMITTED",
            "INVALID_STATE",
            "A submitted current version is required for review",
            409,
        )
        require(
            self.actor["id"] not in {row["created_by"], row["submitted_by"]},
            "INDEPENDENT_REVIEW_REQUIRED",
            "The preparer/submitter cannot verify their own return",
            403,
        )
        data = self.data(row)
        findings = await self.findings(data, obligation, await self.adopted_definitions(obligation))
        if body["decision"] == "VERIFY":
            require(
                not any(f["severity"] == "BLOCKING" for f in findings),
                "VALIDATION_BLOCKED",
                "Blocking findings cannot be overridden",
                409,
            )
            warnings = {f["id"] for f in findings if f["severity"] == "WARNING"}
            require(
                warnings.issubset(body["warning_overrides"]),
                "WARNING_REVIEW_REQUIRED",
                "Record an attributed reason for every warning override",
                422,
            )
        state = "VERIFIED" if body["decision"] == "VERIFY" else "RETURNED_FOR_CORRECTION"
        data["review"] = {**body, "reviewer_id": self.actor["id"], "at": db.now()}
        row = await s.amend(
            self.session,
            t.returns,
            row,
            {
                "state": state,
                "verified_by": self.actor["id"] if state == "VERIFIED" else None,
                "verified_at": db.now() if state == "VERIFIED" else None,
                "payload_ciphertext": self.box.encrypt(s.canonical(data)),
                "updated_at": db.now(),
            },
            body["expected_version"],
        )
        run = await self.validate(row, obligation, data)
        await self.save_version(
            row,
            obligation,
            data,
            "reporting.return_verified"
            if state == "VERIFIED"
            else "reporting.correction_requested",
            "LWH-EVT-008" if state == "VERIFIED" else None,
        )
        return {**s.opened(self.box, row), "validation": run}

    async def correction(self, identifier, body):
        row, obligation = await self.return_for(identifier, s.REPORTERS)
        require(
            row["state"] in {"SUBMITTED", "VERIFIED", "RETURNED_FOR_CORRECTION"},
            "INVALID_STATE",
            "A submitted/verified version is required for a correction",
            409,
        )
        data = self.data(row)
        data["correction"] = {
            "reason": body["reason"],
            "source_version": row["version"],
            "opened_by": self.actor["id"],
            "at": db.now(),
        }
        row = await s.amend(
            self.session,
            t.returns,
            row,
            {
                "state": "DRAFT",
                "verified_by": None,
                "verified_at": None,
                "payload_ciphertext": self.box.encrypt(s.canonical(data)),
                "updated_at": db.now(),
            },
            body["expected_version"],
        )
        snapshot_ids = await self.invalidate_obligation(row, obligation, body["reason"])
        await self.validate(row, obligation, data)
        await self.save_version(row, obligation, data, "reporting.return_corrected", "LWH-EVT-009")
        return {**s.opened(self.box, row), "invalidated_snapshot_ids": snapshot_ids}

    async def import_csv(self, obligation_id, body):
        obligation = await self.obligation(obligation_id, s.REPORTERS)
        definitions = await self.adopted_definitions(obligation)
        by_code = {row["metric_id"]: row for row in definitions.values()}
        reader = csv.DictReader(io.StringIO(body["csv_text"], newline=""), strict=True)
        expected = {
            "metric_id",
            "definition_version",
            "completeness",
            "value",
            "numerator",
            "denominator",
            "source_reference",
            "explanation",
        }
        require(
            reader.fieldnames
            and set(reader.fieldnames) == expected
            and len(reader.fieldnames) == len(expected),
            "IMPORT_HEADER_INVALID",
            "Use the exact controlled CSV headers supplied by the reporting editor",
            422,
        )
        try:
            rows = list(reader)
        except csv.Error as exc:
            raise RuleError(
                "IMPORT_CSV_INVALID",
                "The CSV syntax is malformed; repair the source file before retrying",
                422,
            ) from exc
        outcomes, accepted, seen = [], {}, set()
        for number, raw in enumerate(rows, start=2):
            require(
                number <= 1001, "IMPORT_TOO_LARGE", "A reporting batch is limited to 1000 rows", 422
            )
            outcome = {
                "row_number": number,
                "input_hash": s.digest({str(key): value for key, value in raw.items()}),
                "metric_id": raw.get("metric_id"),
                "outcome": "BLOCKED",
                "code": None,
            }
            definition = by_code.get(raw.get("metric_id"))
            if None in raw or any(value is None for value in raw.values()):
                outcome["code"] = "ROW_COLUMN_COUNT_MISMATCH"
            elif (
                definition is None
                or raw.get("definition_version") != definition["definition_version"]
            ):
                outcome["code"] = "UNMAPPED_DEFINITION"
            elif definition["id"] in seen:
                outcome.update(outcome="DUPLICATE", code="DUPLICATE_INDICATOR_ROW")
            else:
                seen.add(definition["id"])
                try:
                    value = c.MetricValue(
                        definition_id=definition["id"],
                        **{
                            key: raw.get(key) or None
                            for key in (
                                "completeness",
                                "value",
                                "numerator",
                                "denominator",
                                "source_reference",
                                "explanation",
                            )
                        },
                    )
                except ValidationError:
                    outcome["code"] = "ROW_VALIDATION_FAILED"
                else:
                    accepted[definition["id"]] = value.model_dump(mode="json")
                    outcome.update(outcome="ACCEPTED", code="TYPED_CAPTURE_ACCEPTED_NOT_VERIFIED")
            outcomes.append(outcome)
        require(outcomes, "IMPORT_EMPTY", "The batch contains no data rows", 422)
        batch = {
            "id": db.uid(),
            "obligation_id": obligation_id,
            "actor_id": self.actor["id"],
            "input_hash": s.digest(body["csv_text"]),
            "raw_ciphertext": self.box.encrypt(body["csv_text"]),
            "outcomes": outcomes,
            "counts": {
                "input": len(outcomes),
                **{
                    label.lower(): sum(o["outcome"] == label for o in outcomes)
                    for label in ("ACCEPTED", "BLOCKED", "DUPLICATE")
                },
            },
            "created_at": db.now(),
        }
        await self.session.execute(t.imports.insert().values(**batch))
        values = [
            accepted.get(identifier)
            or {
                "definition_id": identifier,
                "completeness": "MISSING",
                "value": None,
                "numerator": None,
                "denominator": None,
                "source_reference": None,
                "explanation": "No accepted input row for this expected indicator",
                "extract_id": None,
            }
            for identifier in obligation["definition_ids"]
        ]
        draft = await self.draft(
            obligation_id,
            {
                "expected_version": body["expected_version"],
                "values": values,
                "source_method": body["source_method"],
                "reconciliation": body["reconciliation"],
                "reason": "Controlled import batch " + batch["id"],
            },
        )
        await s.audit(
            self.session,
            self.actor,
            "reporting.batch_imported",
            obligation,
            batch["id"],
            self.correlation,
        )
        return {"id": batch["id"], "counts": batch["counts"], "outcomes": outcomes, "return": draft}

    async def extract(self, obligation_id):
        obligation = await self.obligation(obligation_id, s.REPORTERS)
        require(
            obligation["scope_type"] == "FACILITY",
            "EXTRACT_NOT_APPLICABLE",
            "Clinical extraction applies only to facility activity obligations",
            422,
        )
        definitions = await self.adopted_definitions(obligation)
        eligible = [
            d
            for d in definitions.values()
            if d["payload"]["source_selector"] == "EMR_COMPLETED_ENCOUNTERS"
        ]
        require(
            eligible,
            "EXTRACT_NOT_CONFIGURED",
            "No adopted clinical extractor is configured for this obligation",
            409,
        )
        records = list(
            (
                await self.session.execute(
                    select(clinical.records).where(
                        clinical.records.c.facility_id == obligation["facility_id"],
                        clinical.records.c.kind.in_(["encounter", "record_error"]),
                    )
                )
            ).mappings()
        )
        restricted = set()
        for row in records:
            if row["kind"] == "record_error":
                restricted.add(
                    json.loads(self.box.decrypt(row["content_ciphertext"]))["content"]["target_id"]
                )
        source_ids, excluded = [], 0
        for row in records:
            if row["kind"] != "encounter" or row["status"] != "COMPLETED":
                continue
            content = json.loads(self.box.decrypt(row["content_ciphertext"]))["content"]
            disposition = content.get("disposition", {})
            occurred_at = disposition.get("occurred_at")
            if occurred_at is None or not (
                obligation["period_start"] <= occurred_at < obligation["period_end"]
            ):
                continue
            if row["id"] in restricted:
                excluded += 1
                continue
            source_ids.append({"id": row["id"], "version": row["version"]})
        payload = {
            "rule_version": "LWH-EMR-CONTACT-EXTRACT-1",
            "as_of": db.now(),
            "period_start": obligation["period_start"],
            "period_end": obligation["period_end"],
            "excluded_entered_in_error": excluded,
            "source_count": len(source_ids),
            "values": {
                d["id"]: {"value": str(len(source_ids)), "metric_id": d["metric_id"]}
                for d in eligible
            },
            "limitations": "Facility completed encounter IDs, by actual disposition time. Not unique people or population incidence. Other source streams are not added.",
        }
        row = {
            "id": db.uid(),
            "obligation_id": obligation_id,
            "source_hash": s.digest(source_ids),
            "payload_ciphertext": self.box.encrypt(s.canonical(payload)),
            "actor_id": self.actor["id"],
            "created_at": db.now(),
        }
        await self.session.execute(t.extracts.insert().values(**row))
        await s.audit(
            self.session,
            self.actor,
            "reporting.clinical_extract_prepared",
            obligation,
            row["id"],
            self.correlation,
            purpose="AGGREGATE_INSTITUTIONAL_REPORTING",
        )
        return s.opened(self.box, row)
