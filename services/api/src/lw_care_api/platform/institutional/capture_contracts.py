"""Bounded canonical FRM-010 envelope inside an intentional, versioned native command."""

import re
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, ConfigDict, Field, model_validator

from ..contracts import StrictModel
from .contracts import Versioned


class Absence(StrictModel):
    absent_reason: Literal["unknown", "not_assessed", "not_applicable", "not_available", "declined"]
    explanation: str = Field(default="", max_length=4000)


Text = Annotated[str, Field(min_length=1, max_length=20000)]
Refs = Annotated[list[UUID], Field(max_length=40)]
TIMESTAMP = r"\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[Zz]|[+-]\d{2}:\d{2})"


def canonical_optional_properties(schema):
    # None is the internal default for an omitted slot, never a wire answer.
    for field in schema.get("properties", {}).values():
        if field.get("default", "present") is None:
            field.pop("default")
        if "anyOf" in field:
            field["anyOf"] = [item for item in field["anyOf"] if item.get("type") != "null"]


def canonical_form_schema(schema):
    canonical_optional_properties(schema)
    schema["allOf"] = [
        {
            "if": {"properties": {"stage": {"const": "submitted"}}},
            "then": {
                "properties": {
                    "answers": {
                        "required": ["finding_id", "required_action", "owner_team_id", "due_at"]
                    }
                }
            },
        }
    ]


class CorrectiveAnswers(StrictModel):
    model_config = ConfigDict(json_schema_extra=canonical_optional_properties)
    finding_id: UUID | Absence | None = None
    required_action: Text | Absence | None = None
    owner_team_id: UUID | Absence | None = None
    due_at: AwareDatetime | Absence | None = None
    response: Text | Absence | None = None
    evidence_refs: Refs | Absence | None = None
    review_result: Text | Absence | None = None

    @model_validator(mode="before")
    @classmethod
    def explicit_answers(cls, value):
        if isinstance(value, dict):
            for key, answer in value.items():
                if answer is None:
                    raise ValueError(
                        "Omit an unanswered field or choose an explicit absence reason"
                    )
                if key == "due_at" and not isinstance(answer, (str, dict)):
                    raise ValueError(
                        "A recorded deadline needs an explicit timestamp or absence reason"
                    )
                if (
                    key == "due_at"
                    and isinstance(answer, str)
                    and not re.fullmatch(TIMESTAMP, answer)
                ):
                    raise ValueError("Record an explicit timestamp with seconds and timezone")
        return value


class CorrectiveForm(StrictModel):
    model_config = ConfigDict(json_schema_extra=canonical_form_schema)
    form_id: Literal["LWH-FRM-010"]
    schema_version: Literal["1.0.0"]
    stage: Literal["draft", "submitted"]
    authority_node_id: UUID
    actor_id: UUID
    facility_or_unit_id: UUID
    recorded_at: AwareDatetime | None = None
    source_refs: list[Annotated[str, Field(max_length=2000)]] = Field(
        default_factory=list, max_length=40
    )
    answers: CorrectiveAnswers

    @model_validator(mode="before")
    @classmethod
    def explicit_envelope(cls, value):
        if isinstance(value, dict) and any(item is None for item in value.values()):
            raise ValueError("Canonical envelope properties cannot be null")
        if (
            isinstance(value, dict)
            and "recorded_at" in value
            and not isinstance(value["recorded_at"], str)
        ):
            raise ValueError("An explicit timestamp string is required")
        if (
            isinstance(value, dict)
            and isinstance(value.get("recorded_at"), str)
            and not re.fullmatch(TIMESTAMP, value["recorded_at"])
        ):
            raise ValueError("Record an explicit timestamp with seconds and timezone")
        return value

    @model_validator(mode="after")
    def submitted_slots(self):
        if (
            self.stage == "submitted"
            and not {"finding_id", "required_action", "owner_team_id", "due_at"}
            <= self.answers.model_fields_set
        ):
            raise ValueError(
                "Submitted forms require all four canonical slots, with actual values or explicit absence"
            )
        return self


class CorrectiveCapture(Versioned):
    expected_case_version: int = Field(ge=1)
    form: CorrectiveForm
