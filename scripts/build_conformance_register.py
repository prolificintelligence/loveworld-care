"""Reproducible canonical-to-current traceability, with explicit unqualified gaps.

Only platform-web and the institutional API count. Candidate links and matching
names do not establish meaning, transition parity, clinical acceptance or adoption.
"""

import argparse
import ast
import csv
import hashlib
import importlib
import inspect
import io
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/api/src"))
SUITE = (
    ROOT
    / "docs/LW_Health_Intelligence_Platform_Complete_Documentation_Suite_v1.0/LW_Health_Intelligence_Platform_Documentation_Suite_v1.0"
)
OUTPUT = ROOT / "docs/implementation/conformance"

# Deliberate source associations, not equivalence assertions. Absent core modules
# and deferred hosting stay visible rather than borrowing legacy/demo routes.
FORM_MODELS = {
    1: ["contracts.Facility", "contracts.Application"],
    2: ["clinical.contracts.Activation"],
    3: ["reporting.contracts.ReturnDraft", "reporting.contracts.Attest"],
    4: ["reporting.contracts.ReturnDraft", "reporting.contracts.Obligation"],
    5: ["reporting.contracts.SafetyCase"],
    6: ["reporting.contracts.Action"],
    7: ["contracts.Decision"],
    8: ["contracts.Inspection"],
    9: ["institutional.contracts.CaseOpen"],
    10: ["institutional.contracts.Response"],
    11: ["institutional.contracts.Decide"],
    12: ["reporting.contracts.Review"],
    13: ["institutional.contracts.Content"],
    14: ["reporting.contracts.ActionUpdate"],
    15: ["clinical.contracts.Activation"],
    16: ["clinical.contracts.Referral", "clinical.contracts.ReferralAction"],
    17: ["clinical.contracts.SharingGrant"],
    18: ["contracts.Unit", "contracts.Invite"],
    19: [],
    20: [],
    21: ["clinical.contracts.Patient"],
    22: ["personal.contracts.LinkRequest", "personal.contracts.LinkReview"],
    23: ["clinical.contracts.Encounter"],
    24: ["clinical.contracts.Triage"],
    25: ["clinical.contracts.Note", "clinical.contracts.Sign"],
    26: ["clinical.contracts.Problem", "clinical.contracts.Allergy"],
    27: ["clinical.contracts.Order"],
    28: ["clinical.contracts.Specimen"],
    29: ["clinical.contracts.Result"],
    30: ["clinical.contracts.Medication"],
    31: ["clinical.contracts.Dispense"],
    32: ["clinical.contracts.Administration"],
    33: ["clinical.contracts.LotAction"],
    34: ["clinical.contracts.Admission"],
    35: ["clinical.advanced_contracts.Nursing"],
    36: [
        "clinical.contracts.StayAction",
        "clinical.contracts.Disposition",
        "clinical.advanced_contracts.Handover",
    ],
    37: ["clinical.contracts.ProgrammeReview"],
    38: ["clinical.advanced_contracts.Birth"],
    39: ["clinical.contracts.ProgrammeReview"],
    40: ["clinical.advanced_contracts.Growth", "clinical.advanced_contracts.Immunisation"],
    41: ["clinical.contracts.Procedure", "clinical.contracts.ProcedureAction"],
    42: ["clinical.advanced_contracts.Anaesthesia"],
    43: ["clinical.contracts.Transfusion", "clinical.contracts.TransfusionAction"],
    44: ["clinical.contracts.Invoice"],
    45: ["clinical.contracts.CashReceipt"],
    46: [],
    47: ["control.contracts.PolicyPackage"],
    48: [],
    49: ["clinical.contracts.Task", "clinical.contracts.Programme"],
    50: ["control.contracts.Coverage"],
    51: ["clinical.contracts.Consent"],
}
ALIASES = {
    "site_name": "name",
    "operator_org_id": "operator_id",
    "jurisdiction_profile": "jurisdiction",
    "indicator_values": "values",
    "conflict_declaration": "conflict_declared",
}
DOMAINS = {
    "registry": ("main.py", "domain.py", "db.py", "test_platform_readiness.py"),
    "reporting": (
        "reporting/router.py",
        "reporting/service.py",
        "reporting/tables.py",
        "test_platform_reporting.py",
    ),
    "clinical": (
        "clinical/router.py",
        "clinical/service.py",
        "clinical/tables.py",
        "test_platform_clinical.py",
    ),
    "institutional": (
        "institutional/router.py",
        "institutional/affiliation.py",
        "institutional/tables.py",
        "test_platform_institutional.py",
    ),
    "control": (
        "control/router.py",
        "control/service.py",
        "control/tables.py",
        "test_platform_controls.py",
    ),
    "personal": (
        "personal/router.py",
        "personal/service.py",
        "personal/tables.py",
        "test_platform_personal.py",
    ),
}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def source(path):
    path = Path(path)
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "sha256_lf": hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
    }


def domain_evidence(domain):
    permission, validation, persistence, test = DOMAINS[domain]
    base = ROOT / "services/api/src/lw_care_api/platform"
    return {
        "permission_candidate": source(base / permission),
        "validation_candidate": source(base / validation),
        "persistence_candidate": source(base / persistence),
        "engineering_test_candidate": source(ROOT / "tests/integration" / test),
    }


def screen_domain(prd):
    number = int(prd.rsplit("-", 1)[1])
    if number in {4, 5, 6, 7, 8}:
        return "reporting", "/directorate"
    if number in {2, 3}:
        return "registry", "/"
    if number == 10:
        return "institutional", "/learn"
    if number in {11, 23}:
        return "personal", "/my-health"
    if number in {9, 12, 15, 16, 17, 18, 19, 20, 21, 22}:
        return "clinical", "/care"
    return "control", "/operations"


def canonical_table(document, prefix):
    rows = []
    for line in document.splitlines():
        if line.startswith("| " + prefix):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            identifier = re.match(re.escape(prefix) + r"\d{3}", cells[0]).group()
            rows.append({"id": identifier, "cells": cells})
    return rows


def proof_references(proof):
    require_refs = proof.get("tests", [])
    if not require_refs:
        raise ValueError("Field proof needs a concrete regression reference")
    references = []
    for item in require_refs:
        path = ROOT / item["path"]
        tree = ast.parse(path.read_text(encoding="utf-8"))
        symbols = {
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        scenarios = next(
            ast.literal_eval(node.value)
            for node in tree.body
            if isinstance(node, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "SCENARIOS" for t in node.targets)
        )
        if item["symbol"] not in symbols or not set(item["scenarios"]) <= set(scenarios):
            raise ValueError("Dangling field proof test/scenario")
        references.append(
            item | {"source": source(path), "class": "ENGINEERING_REGRESSION_NOT_FORMAL_ACCEPTANCE"}
        )
    return references


def build():
    manifest = load(SUITE / "manifest.json")
    documents = {row["document_id"]: row for row in manifest["documents"]}
    for row in documents.values():
        if hashlib.sha256((SUITE / row["path"]).read_bytes()).hexdigest() != row["sha256"]:
            raise ValueError("Controlled document integrity mismatch: " + row["document_id"])
    # Pinned FastAPI has lazy included routers; cross-check effective paths with OpenAPI.
    from fastapi.routing import _iter_routes_with_context
    from lw_care_api.platform.config import PlatformSettings
    from lw_care_api.platform.main import create_platform_app

    app = create_platform_app(
        PlatformSettings(
            environment="test",
            database_url="sqlite+aiosqlite://",
            data_key_hex="01" * 32,
            authority_node_id="conformance-inspection",
            web_origin="http://localhost:3004",
        )
    )
    routes, models = [], {}
    for original, context in _iter_routes_with_context(app.routes):
        route = context or original
        body = getattr(route, "body_field", None)
        model = body.field_info.annotation if body else None
        if not hasattr(model, "model_json_schema"):
            model = None
        name = (
            model.__module__.removeprefix("lw_care_api.platform.") + "." + model.__name__
            if model
            else None
        )
        for method in sorted(getattr(route, "methods", set())):
            if route.path.startswith("/v1/") and route.path != "/v1/docs":
                routes.append(
                    {
                        "method": method,
                        "path": route.path,
                        "request_model": name,
                        "handler": source(inspect.getsourcefile(route.endpoint)),
                        "handler_line": inspect.getsourcelines(route.endpoint)[1],
                    }
                )
    expected = {
        (method.upper(), path)
        for path, ops in app.openapi()["paths"].items()
        for method in ops
        if method in {"get", "post", "put", "delete", "patch"}
        if path.startswith("/v1/")
    }
    if {(r["method"], r["path"]) for r in routes} != expected:
        raise ValueError("Effective route inventory differs from published API schema")
    forms, fields = [], []
    baseline_fields = load(SUITE / "contracts/form_field_manifest.json")
    for number in range(1, 52):
        identifier = f"LWH-FRM-{number:03}"
        schema_path = SUITE / f"contracts/forms/{identifier}.schema.json"
        schema = load(schema_path)
        links = FORM_MODELS[number]
        for name in links:
            module, symbol = name.rsplit(".", 1)
            model = getattr(importlib.import_module("lw_care_api.platform." + module), symbol)
            models[name] = {
                "schema": model.model_json_schema(),
                "source": source(inspect.getsourcefile(model)),
                "line": inspect.getsourcelines(model)[1],
            }
        associated = [r for r in routes if r["request_model"] in links]
        domain = links[0].split(".")[0] if links else "control"
        domain = "registry" if domain == "contracts" else domain
        forms.append(
            {
                "id": identifier,
                "name": schema["title"],
                "canonical_schema": source(schema_path),
                "candidate_models": links,
                "candidate_routes": associated,
                "candidate_evidence": domain_evidence(domain) if links else {},
                "status": "PARTIAL_CANDIDATE_MAPPING"
                if associated
                else "OPEN_EXPLICIT_MAPPING_GAP",
                "exception": "Split typed commands replace the generic capture envelope; field/state equivalence and independent adoption remain unqualified.",
            }
        )
        for field in [f for f in baseline_fields if f["form_id"] == identifier]:
            candidates = []
            for name in links:
                implementation = models[name]["schema"]
                actual = (
                    field["name"]
                    if field["name"] in implementation["properties"]
                    else ALIASES.get(field["name"])
                )
                if actual in implementation["properties"]:
                    candidates.append(
                        {
                            "model": name,
                            "field": actual,
                            "required": actual in implementation.get("required", []),
                            "requiredness_matches": field["required_on_capture_submission"]
                            == (actual in implementation.get("required", [])),
                            "schema": implementation["properties"][actual],
                            "match": "NAME_ONLY"
                            if actual == field["name"]
                            else "REVIEWED_ALIAS_CANDIDATE",
                        }
                    )
            fields.append(
                field
                | {
                    "candidate_bindings": candidates,
                    "status": "PARTIAL_NAME_OR_ALIAS_CANDIDATE"
                    if candidates
                    else "OPEN_EXPLICIT_FIELD_MAPPING_GAP",
                    "permission": "UNQUALIFIED_AT_FIELD_LEVEL_SEE_FORM_ROUTE_HANDLERS",
                    "validation": "TYPED_SCHEMA_CANDIDATE_RULE_EQUIVALENCE_NOT_PROVEN"
                    if candidates
                    else "UNQUALIFIED",
                    "missingness": "UNQUALIFIED_CANONICAL_UNKNOWN_NIL_NOT_APPLICABLE_SEMANTICS",
                    "persistence": "UNQUALIFIED_AT_FIELD_LEVEL",
                    "test_evidence": [],
                    "formal_acceptance": "NOT_RUN",
                    "exception": "No equivalence inferred from name/type. Requiredness, purpose/field scope, persistence, missingness and failure cases require a field-specific proof.",
                }
            )
    screens = canonical_table(
        (SUITE / documents["LWH-SPEC-001"]["path"]).read_text(encoding="utf-8"), "LWH-SCR-"
    )
    states = canonical_table(
        (SUITE / documents["LWH-SPEC-009"]["path"]).read_text(encoding="utf-8"), "LWH-STM-"
    )
    for row in screens + states:
        row.update(
            status="OPEN_SEMANTIC_CONFORMANCE_GAP",
            formal_acceptance="NOT_RUN",
            candidate_sources=[],
            test_evidence=[],
            exception="No one-to-one identity/transition equivalence asserted. Require actor, permission, guards, missingness, persistence, failure/recovery and actual-role evidence.",
        )
    for row in screens:
        domain, page = screen_domain(row["cells"][2])
        row["candidate_sources"] = domain_evidence(domain)
        row["candidate_page"] = source(
            ROOT / "apps/platform-web/src/app" / page.strip("/") / "page.tsx"
        )
        row["page_route"] = page
        row["exception"] += (
            " Page association is domain-level, not one of 75 individually qualified screens."
        )
    state_domains = {
        1: "registry",
        2: "registry",
        3: "institutional",
        4: "registry",
        5: "clinical",
        6: "reporting",
        7: "reporting",
        8: "reporting",
        9: "institutional",
        24: "clinical",
        25: "clinical",
        26: "clinical",
        27: "clinical",
        28: "control",
        29: "control",
        30: "control",
    }
    for row in states:
        number = int(row["id"].rsplit("-", 1)[1])
        row["candidate_sources"] = domain_evidence(state_domains.get(number, "clinical"))
        if number in {25, 27, 28, 30}:
            row["exception"] += (
                " Complete sponsorship/payer/sync/ERP family is not delivered by these candidate modules."
            )
    proof_path = OUTPUT / "director-proofs.json"
    proofs = load(proof_path)
    by_field = {f["id"]: f for f in fields}
    seen = set()
    for proof in proofs["fields"]:
        if (
            proof["id"] in seen
            or proof["id"] not in by_field
            or proof["formal_acceptance"] != "NOT_RUN"
        ):
            raise ValueError("Invalid/duplicate field proof identity or acceptance claim")
        seen.add(proof["id"])
        field = by_field[proof["id"]]
        field.update(
            engineering_proof=proof,
            status=proof["status"],
            test_evidence=proof_references(proof),
            permission=proof["permission"],
            persistence=proof["persistence"],
        )
    by_state = {r["id"]: r for r in states}
    for proof in proofs["states"]:
        by_state[proof["id"]].update(
            status="PARTIAL_ENGINEERING_TRANSITION_PROOF_EXCEPTION_OPEN", engineering_proof=proof
        )
    captures = load(SUITE / "contracts/openapi.capture.json")["paths"]
    interfaces = []
    for path, operations in captures.items():
        for method, operation in operations.items():
            if method in {"get", "post", "put", "patch", "delete"}:
                interfaces.append(
                    {
                        "id": operation.get("operationId", method + " " + path),
                        "kind": "CAPTURE",
                        "canonical": {"method": method.upper(), "path": path},
                        "status": "OPEN_TYPED_EXTENSION_RECONCILIATION",
                        "formal_acceptance": "NOT_RUN",
                    }
                )
    for row in load(SUITE / "contracts/query_catalogue.json"):
        exact = [r for r in routes if r["method"] == row["method"] and r["path"] == row["path"]]
        interfaces.append(
            {
                "id": row["id"],
                "kind": "QUERY",
                "canonical": row,
                "candidate_routes": exact,
                "status": "PARTIAL_PATH_MATCH_SEMANTICS_UNQUALIFIED"
                if exact
                else "OPEN_ROUTE_MAPPING_GAP",
                "formal_acceptance": "NOT_RUN",
            }
        )
    for row in load(SUITE / "contracts/command_schemas.json"):
        interfaces.append(
            {
                "id": row["$id"],
                "kind": "COMMAND",
                "canonical": row,
                "status": "OPEN_TYPED_EXTENSION_RECONCILIATION",
                "formal_acceptance": "NOT_RUN",
            }
        )
    return {
        "format": 1,
        "scope": "INSTITUTIONAL_API_AND_PLATFORM_WEB_ONLY",
        "meaning": "Complete canonical inventory with explicit exceptions; candidate links are not parity or acceptance.",
        "controlled_documents_verified": len(documents),
        "forms": forms,
        "fields": fields,
        "screens": screens,
        "state_families": states,
        "interfaces": interfaces,
        "implementation_models": models,
        "reviewed_proof_input": source(proof_path),
        "actual_routes": routes,
        "baseline_inputs": [
            source(SUITE / p)
            for p in [
                "manifest.json",
                "contracts/form_field_manifest.json",
                "contracts/openapi.capture.json",
                "contracts/query_catalogue.json",
                "contracts/command_schemas.json",
            ]
        ],
        "acceptance": {"requirements": 200, "specified_cases": 111, "status": "NOT_RUN"},
    }


def validate(register):
    for key, count in (
        ("forms", 51),
        ("fields", 355),
        ("screens", 75),
        ("state_families", 30),
        ("interfaces", 82),
    ):
        rows = register[key]
        if len(rows) != count or len({r["id"] for r in rows}) != count:
            raise ValueError("Incomplete/duplicate canonical inventory: " + key)
    forms = {r["id"] for r in register["forms"]}
    actual_routes = {
        (r["method"], r["path"], r["request_model"]) for r in register["actual_routes"]
    }
    for form in register["forms"]:
        for route in form["candidate_routes"]:
            if (route["method"], route["path"], route["request_model"]) not in actual_routes:
                raise ValueError("Dangling implementation route")
    for field in register["fields"]:
        if field["form_id"] not in forms or field["formal_acceptance"] != "NOT_RUN":
            raise ValueError("Invalid field ownership or unexecuted acceptance claim")
        if "engineering_proof" in field and field["engineering_proof"]["id"] != field["id"]:
            raise ValueError("Field-specific proof was attached to a different canonical field")
        for binding in field["candidate_bindings"]:
            schema = register["implementation_models"][binding["model"]]["schema"]
            if binding["field"] not in schema["properties"]:
                raise ValueError("Dangling implementation field")
    for key in ("forms", "fields", "screens", "state_families", "interfaces"):
        if any(r["status"].startswith(("ACCEPTED", "CONFORMANT", "PASSED")) for r in register[key]):
            raise ValueError("This inventory cannot establish conformance or operating acceptance")
        if any(row.get("formal_acceptance", "NOT_RUN") != "NOT_RUN" for row in register[key]):
            raise ValueError("Formal suite acceptance remains unexecuted")


def rendered(register):
    outputs = {"canonical-register.json": json.dumps(register, indent=2, ensure_ascii=False) + "\n"}
    for key in ("forms", "fields", "screens", "state_families", "interfaces"):
        output = io.StringIO(newline="")
        columns = list(dict.fromkeys(k for row in register[key] for k in row))
        writer = csv.DictWriter(output, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in register[key]:
            writer.writerow(
                {
                    k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v
                    for k, v in row.items()
                }
            )
        outputs[key + ".csv"] = output.getvalue()
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    register = build()
    validate(register)
    path = OUTPUT / "canonical-register.json"
    for filename, content in rendered(register).items():
        target = OUTPUT / filename
        if args.check:
            if not target.exists() or target.read_bytes() != content.encode("utf-8"):
                raise SystemExit("Conformance register is stale: " + filename)
        else:
            OUTPUT.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content.encode("utf-8"))
    print(
        json.dumps(
            {
                "register": path.relative_to(ROOT).as_posix(),
                "checked": args.check,
                "counts": {
                    k: dict(Counter(r["status"] for r in register[k]))
                    for k in ("forms", "fields", "screens", "state_families", "interfaces")
                },
            }
        )
    )


if __name__ == "__main__":
    main()
