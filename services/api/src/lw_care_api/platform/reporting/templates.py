"""Institutional template adoption in the existing append-only reporting journal."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator
from sqlalchemy import and_, func, select

from .. import db
from ..contracts import StrictModel
from ..domain import require
from ..paging import page
from . import store as s
from . import tables as t
from .contracts import Short, Stream, Text, Versioned

KIND = "REPORTING_TEMPLATE"
GLOBAL = {"scope_type": "GLOBAL", "scope_id": "GLOBAL"}
READERS = s.SOURCE_READERS | s.PROGRAMMES
EDITORS = s.GOVERNORS | s.REVIEWERS


class TemplateField(StrictModel):
    code: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_.-]{0,79}$")
    label: Short
    required: bool = Field(strict=True)
    disposition: Literal["MEASURE", "CONTEXT", "EXCLUDED", "GAP"]
    definition_id: UUID | None = None
    part: Literal["VALUE", "NUMERATOR", "DENOMINATOR"] | None = None
    context: (
        Literal["FACILITY", "ZONE", "REGION", "PERIOD_START", "PERIOD_END", "OFFICER_ATTESTATION"]
        | None
    ) = None
    rationale: Text

    @model_validator(mode="after")
    def mapping(self):
        if self.disposition == "MEASURE":
            if not self.definition_id or not self.part or self.context:
                raise ValueError("A measure needs its exact definition and component")
        elif self.disposition == "CONTEXT":
            if not self.context or self.definition_id or self.part:
                raise ValueError("Map a context field separately from indicators")
        elif self.definition_id or self.part or self.context:
            raise ValueError("Gaps/exclusions have rationale, not an implied mapping")
        return self


class Template(StrictModel):
    name: Short
    source_version: Short
    source_reference: Text
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    stream: Stream
    jurisdictions: list[Short] = Field(min_length=1, max_length=100)
    adoption_reference: Text
    valid_from: datetime
    valid_until: datetime
    fields: list[TemplateField] = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def inventory(self):
        if self.valid_until <= self.valid_from:
            raise ValueError("Template validity must be ordered")
        codes = [field.code.casefold() for field in self.fields]
        if len(codes) != len(set(codes)):
            raise ValueError("Inventory each source field once")
        if self.stream != "FACILITY_ACTIVITY" and self.jurisdictions != ["GLOBAL"]:
            raise ValueError(
                "Zone/regional templates require explicit central GLOBAL applicability"
            )
        return self


class Edit(Template):
    expected_version: int = Field(ge=1)
    reason: Text


class Transition(Versioned):
    action: Literal["SUBMIT", "REVIEW_ACCEPT", "RETURN_FOR_CORRECTION", "ADOPT", "WITHDRAW"]
    evidence: Text
    intent_confirmed: Literal[True]


class TemplateService:
    def __init__(self, service):
        self.service = service
        self.session, self.actor, self.box = service.session, service.actor, service.box

    def editor(self):
        return s.permits(self.actor, EDITORS, GLOBAL)

    async def get(self, identifier):
        row = (
            (
                await self.session.execute(
                    select(t.history)
                    .where(
                        t.history.c.resource_type == KIND,
                        t.history.c.resource_id == str(identifier),
                    )
                    .order_by(t.history.c.version.desc())
                    .limit(1)
                )
            )
            .mappings()
            .first()
        )
        require(row, "NOT_FOUND_OR_NOT_PERMITTED", "Reporting template unavailable", 404)
        payload = self.service.data(row)
        require(
            s.digest(payload) == row["payload_hash"],
            "INTEGRITY_FAILURE",
            "Template history failed verification",
            503,
        )
        value = payload["resource"]
        require(
            value["id"] == str(identifier) and value["version"] == row["version"],
            "INTEGRITY_FAILURE",
            "Template identity differs",
            503,
        )
        return value

    async def mapping(self, body, *, resolved=False):
        components, definitions = {}, {}
        for field in body["fields"]:
            require(
                not resolved or field["disposition"] != "GAP",
                "TEMPLATE_GAPS_UNRESOLVED",
                "Resolve each source field before adoption; exclusions need explicit rationale",
                409,
            )
            if field["disposition"] != "MEASURE":
                continue
            definition = await s.load(self.session, t.definitions, field["definition_id"])
            rule = definition["payload"]
            require(
                definition["stream"] == body["stream"]
                and rule["valid_from"] <= body["valid_from"]
                and rule["valid_until"] >= body["valid_until"],
                "TEMPLATE_DEFINITION_MISMATCH",
                "Mapped definitions must cover the template stream and validity",
                422,
            )
            expected = {"NUMERATOR", "DENOMINATOR"} if rule["formula"] == "RATIO" else {"VALUE"}
            parts = components.setdefault(definition["id"], set())
            require(
                field["part"] in expected and field["part"] not in parts,
                "TEMPLATE_COMPONENT_MISMATCH",
                "Map each required measure component once; ratios need numerator and denominator",
                422,
            )
            parts.add(field["part"])
            definitions[definition["id"]] = definition
        if resolved:
            require(
                definitions,
                "TEMPLATE_MEASURE_REQUIRED",
                "Map at least one actual adopted indicator",
                422,
            )
            metrics = [value["metric_id"] for value in definitions.values()]
            require(
                len(metrics) == len(set(metrics)),
                "DUPLICATE_METRIC",
                "Use one definition version per indicator",
                422,
            )
            for identifier, definition in definitions.items():
                rule = definition["payload"]
                require(
                    components[identifier]
                    == ({"NUMERATOR", "DENOMINATOR"} if rule["formula"] == "RATIO" else {"VALUE"}),
                    "TEMPLATE_COMPONENT_MISSING",
                    "Map the complete measure, including both ratio components",
                    422,
                )
                parent = rule.get("less_or_equal_metric")
                require(
                    not parent or parent in metrics,
                    "RELATED_TOTAL_REQUIRED",
                    "Include the adopted comparison total",
                    422,
                )
        return sorted(definitions)

    async def save(self, row, action, evidence):
        await self.service.log(KIND, row, action, GLOBAL, content=evidence)
        return row

    async def create(self, body):
        self.service.governor()
        ids = await self.mapping(body)
        row = {
            "id": db.uid(),
            "version": 1,
            "state": "DRAFT",
            "name": body["name"],
            "created_by": self.actor["id"],
            "author_ids": [self.actor["id"]],
            "reviewer_id": None,
            "adopter_id": None,
            "created_at": db.now(),
            "definition_ids": ids,
            "inventory_hash": s.digest(body),
            "payload": body,
        }
        return await self.save(
            row,
            "reporting.template_created",
            {"source_fingerprint": "ATTESTED_NOT_FETCHED_OR_SCANNED"},
        )

    async def edit(self, identifier, body):
        self.service.governor()
        row = await self.get(identifier)
        require(
            row["state"] == "DRAFT",
            "TEMPLATE_FROZEN",
            "Submitted/adopted mappings are frozen; create a new template edition",
            409,
        )
        require(
            row["version"] == body["expected_version"],
            "VERSION_CONFLICT",
            "Refresh the current mapping",
            412,
        )
        payload = {k: v for k, v in body.items() if k not in {"expected_version", "reason"}}
        ids = await self.mapping(payload)
        current = row | {
            "version": row["version"] + 1,
            "payload": payload,
            "name": payload["name"],
            "author_ids": sorted(set(row["author_ids"]) | {self.actor["id"]}),
            "definition_ids": ids,
            "reviewer_id": None,
            "inventory_hash": s.digest(payload),
        }
        return await self.save(current, "reporting.template_edited", {"reason": body["reason"]})

    async def transition(self, identifier, body):
        row = await self.get(identifier)
        require(
            row["version"] == body["expected_version"],
            "VERSION_CONFLICT",
            "Refresh this template before deciding",
            412,
        )
        action, current = body["action"], dict(row)
        if action in {"REVIEW_ACCEPT", "RETURN_FOR_CORRECTION"}:
            s.require_role(self.actor, s.REVIEWERS, GLOBAL)
            require(
                self.actor["id"] not in row["author_ids"],
                "INDEPENDENT_REVIEW_REQUIRED",
                "A reviewer who did not author this mapping must examine the source",
                403,
            )
            require(
                row["state"] == "SUBMITTED",
                "INVALID_TRANSITION",
                "Review a submitted inventory",
                409,
            )
            if action == "REVIEW_ACCEPT":
                await self.mapping(row["payload"], resolved=True)
            current.update(
                state="REVIEWED" if action == "REVIEW_ACCEPT" else "DRAFT",
                reviewer_id=self.actor["id"],
            )
        else:
            self.service.governor()
            if action == "SUBMIT":
                require(
                    row["state"] == "DRAFT", "INVALID_TRANSITION", "Submit a current draft", 409
                )
                current.update(state="SUBMITTED", reviewer_id=None)
            elif action == "ADOPT":
                require(
                    row["state"] == "REVIEWED" and row["reviewer_id"] != self.actor["id"],
                    "INDEPENDENT_REVIEW_REQUIRED",
                    "Adoption requires another person's completed review",
                    403,
                )
                await self.mapping(row["payload"], resolved=True)
                require(
                    row["payload"]["valid_until"] > db.now(),
                    "TEMPLATE_EXPIRED",
                    "Adopt a currently applicable or future template",
                    409,
                )
                current.update(state="ADOPTED", adopter_id=self.actor["id"])
            else:
                require(
                    row["state"] == "ADOPTED",
                    "INVALID_TRANSITION",
                    "Only an adopted template can be withdrawn",
                    409,
                )
                current.update(state="WITHDRAWN")
        current["version"] += 1
        return await self.save(current, "reporting.template_" + action.lower(), body)

    async def listing(self, after):
        require(
            self.editor() or any(g["role"] in READERS for g in self.actor["grants"]),
            "ACCESS_DENIED",
            "Template reporting assignment required",
            403,
        )
        latest = (
            select(t.history.c.resource_id, func.max(t.history.c.version).label("version"))
            .where(t.history.c.resource_type == KIND)
            .group_by(t.history.c.resource_id)
            .subquery()
        )
        query = (
            select(t.history)
            .join(
                latest,
                and_(
                    latest.c.resource_id == t.history.c.resource_id,
                    latest.c.version == t.history.c.version,
                ),
            )
            .where(t.history.c.resource_type == KIND)
        )
        if not self.editor():
            query = query.where(
                t.history.c.action.in_(["reporting.template_adopt", "reporting.template_withdraw"])
            )
        rows, cursor = await page(
            self.session, query, after, t.history.c.created_at, t.history.c.id, size=50
        )
        items = []
        for row in rows:
            payload = self.service.data(row)
            require(
                s.digest(payload) == row["payload_hash"]
                and payload["resource"]["id"] == row["resource_id"]
                and payload["resource"]["version"] == row["version"],
                "INTEGRITY_FAILURE",
                "Template history failed verification",
                503,
            )
            items.append(payload["resource"])
        return {"items": items, "next_cursor": cursor, "as_of": db.now()}

    async def bind(self, body, scope):
        template = await self.get(body["template_id"])
        require(
            template["state"] == "ADOPTED",
            "TEMPLATE_NOT_ADOPTED",
            "Use a currently adopted template",
            409,
        )
        require(
            template["version"] == body["template_version"],
            "VERSION_CONFLICT",
            "Use the exact currently adopted edition",
            412,
        )
        rule = template["payload"]
        require(
            rule["stream"] == body["stream"]
            and rule["valid_from"] <= body["period_start"]
            and rule["valid_until"] >= body["period_end"],
            "TEMPLATE_NOT_APPLICABLE",
            "Template stream/validity does not cover the reporting period",
            422,
        )
        require(
            set(body["definition_ids"]) == set(template["definition_ids"]),
            "TEMPLATE_INDICATOR_SET_MISMATCH",
            "The obligation must retain the template's exact adopted indicator versions",
            422,
        )
        if scope["scope_type"] == "FACILITY":
            facility = await s.load(self.session, db.facilities, scope["facility_id"])
            require(
                "GLOBAL" in rule["jurisdictions"]
                or facility["jurisdiction"] in rule["jurisdictions"],
                "TEMPLATE_JURISDICTION_MISMATCH",
                "The template does not apply to this facility jurisdiction",
                422,
            )
        return {
            "template_id": template["id"],
            "template_version": template["version"],
            "inventory_hash": template["inventory_hash"],
            "payload": rule,
            "reviewer_id": template["reviewer_id"],
            "adopter_id": template["adopter_id"],
        }

    async def binding(self, obligation_id):
        row = (
            (
                await self.session.execute(
                    select(t.history).where(
                        t.history.c.resource_type == "OBLIGATION_TEMPLATE",
                        t.history.c.resource_id == obligation_id,
                    )
                )
            )
            .mappings()
            .first()
        )
        if not row:
            return None
        payload = self.service.data(row)
        require(
            s.digest(payload) == row["payload_hash"]
            and payload["resource"]["id"] == str(obligation_id)
            and payload["resource"]["version"] == row["version"] == 1,
            "INTEGRITY_FAILURE",
            "Frozen template binding failed verification",
            503,
        )
        return payload["resource"]["template"]
