import type {ClinicalForm} from "./forms";

export const phase5Forms:ClinicalForm[] = [
  {
    "id": "capacity",
    "title": "Record actual service capacity",
    "group": "Team & capacity",
    "path": "workflows/capacity",
    "capability": [
      "GOVERNOR"
    ],
    "fields": [
      {
        "key": "service",
        "label": "Service",
        "required": true,
        "ref": "service"
      },
      {
        "key": "max_open_encounters",
        "label": "Actual concurrent encounter limit",
        "required": true,
        "type": "integer"
      },
      {
        "key": "resources_evidence",
        "label": "Resources evidence",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "policy_reference",
        "label": "Applicable adopted policy and version",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "starts_at",
        "label": "Actual effective start time",
        "required": true,
        "type": "datetime-local"
      },
      {
        "key": "ends_at",
        "label": "Actual end or expiry time",
        "required": true,
        "type": "datetime-local"
      },
      {
        "key": "require_roster",
        "label": "Require roster",
        "required": true,
        "type": "boolean"
      },
      {
        "key": "require_admission_order",
        "label": "Require admission order",
        "required": true,
        "type": "boolean"
      },
      {
        "key": "intent_confirmed",
        "label": "I intend to attest and commit this action under my authenticated authority",
        "required": true,
        "type": "intent"
      }
    ],
    "context": false,
    "patient": false
  },
  {
    "id": "capacity-revision",
    "title": "Revise actual service capacity",
    "group": "Team & capacity",
    "path": "workflows/capacity/{id}/revisions",
    "capability": [
      "GOVERNOR"
    ],
    "fields": [
      {
        "key": "service",
        "label": "Service",
        "required": true,
        "ref": "service"
      },
      {
        "key": "max_open_encounters",
        "label": "Actual concurrent encounter limit",
        "required": true,
        "type": "integer"
      },
      {
        "key": "resources_evidence",
        "label": "Resources evidence",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "policy_reference",
        "label": "Applicable adopted policy and version",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "starts_at",
        "label": "Actual effective start time",
        "required": true,
        "type": "datetime-local"
      },
      {
        "key": "ends_at",
        "label": "Actual end or expiry time",
        "required": true,
        "type": "datetime-local"
      },
      {
        "key": "require_roster",
        "label": "Require roster",
        "required": true,
        "type": "boolean"
      },
      {
        "key": "require_admission_order",
        "label": "Require admission order",
        "required": true,
        "type": "boolean"
      },
      {
        "key": "intent_confirmed",
        "label": "I intend to attest and commit this action under my authenticated authority",
        "required": true,
        "type": "intent"
      },
      {
        "key": "reason",
        "label": "Actual reason and supporting evidence",
        "required": true,
        "type": "textarea"
      }
    ],
    "context": false,
    "patient": false,
    "target": "service_capacity"
  },
  {
    "id": "withdraw-shift",
    "title": "Withdraw an offered or accepted duty shift",
    "group": "Team & capacity",
    "path": "workflows/shifts/{id}/actions",
    "capability": [
      "GOVERNOR"
    ],
    "fields": [
      {
        "key": "reason",
        "label": "Actual reason and supporting evidence",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "action",
        "label": "Action",
        "required": true,
        "options": [
          "WITHDRAW"
        ]
      },
      {
        "key": "occurred_at",
        "label": "Occurred at",
        "required": true,
        "type": "datetime-local"
      },
      {
        "key": "intent_confirmed",
        "label": "I intend to attest and commit this action under my authenticated authority",
        "required": true,
        "type": "intent"
      }
    ],
    "context": false,
    "patient": false,
    "target": "duty_shift"
  },
  {
    "id": "shift",
    "title": "Offer a qualified duty shift",
    "group": "Team & capacity",
    "path": "workflows/shifts",
    "capability": [
      "GOVERNOR"
    ],
    "fields": [
      {
        "key": "service",
        "label": "Service",
        "required": true,
        "ref": "service"
      },
      {
        "key": "account_id",
        "label": "Account id",
        "required": true,
        "ref": "staff"
      },
      {
        "key": "capability",
        "label": "Capability",
        "required": true,
        "options": [
          "CARE",
          "NURSING",
          "DIAGNOSTICS",
          "PHARMACY",
          "PROCEDURE"
        ]
      },
      {
        "key": "capacity",
        "label": "Actual professional workload limit",
        "required": true,
        "type": "integer"
      },
      {
        "key": "starts_at",
        "label": "Actual effective start time",
        "required": true,
        "type": "datetime-local"
      },
      {
        "key": "ends_at",
        "label": "Actual end or expiry time",
        "required": true,
        "type": "datetime-local"
      },
      {
        "key": "policy_reference",
        "label": "Applicable adopted policy and version",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "reason",
        "label": "Actual reason and supporting evidence",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "intent_confirmed",
        "label": "I intend to attest and commit this action under my authenticated authority",
        "required": true,
        "type": "intent"
      }
    ],
    "context": false,
    "patient": false
  },
  {
    "id": "shift-action",
    "title": "Personally accept, decline or end shift",
    "group": "Team & capacity",
    "path": "workflows/shifts/{id}/actions",
    "capability": [
      "CARE",
      "NURSING",
      "DIAGNOSTICS",
      "PHARMACY",
      "PROCEDURE"
    ],
    "fields": [
      {
        "key": "reason",
        "label": "Actual reason and supporting evidence",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "action",
        "label": "Action",
        "required": true,
        "options": [
          "ACCEPT",
          "DECLINE",
          "END"
        ]
      },
      {
        "key": "occurred_at",
        "label": "Occurred at",
        "required": true,
        "type": "datetime-local"
      },
      {
        "key": "intent_confirmed",
        "label": "I intend to attest and commit this action under my authenticated authority",
        "required": true,
        "type": "intent"
      }
    ],
    "context": false,
    "patient": false,
    "target": "duty_shift",
    "explanation": "Ending or expiring a shift does not transfer or close existing care. Use accepted handover for unresolved work."
  },
  {
    "id": "handover",
    "title": "Offer current encounter and owned-task handover",
    "group": "Team & capacity",
    "path": "workflows/handovers",
    "capability": [
      "CARE",
      "NURSING"
    ],
    "fields": [
      {
        "key": "occurred_at",
        "label": "Occurred at",
        "required": true,
        "type": "datetime-local"
      },
      {
        "key": "recipient_id",
        "label": "Recipient id",
        "required": true,
        "ref": "staff"
      },
      {
        "key": "capability",
        "label": "Capability",
        "required": true,
        "options": [
          "CARE",
          "NURSING"
        ]
      },
      {
        "key": "summary",
        "label": "Summary",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "due_at",
        "label": "Due at",
        "required": true,
        "type": "datetime-local"
      },
      {
        "key": "reason",
        "label": "Actual reason and supporting evidence",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "intent_confirmed",
        "label": "I intend to attest and commit this action under my authenticated authority",
        "required": true,
        "type": "intent"
      }
    ],
    "context": true,
    "patient": false,
    "explanation": "The sender remains responsible until personal acceptance. Changed work requires a new current offer."
  },
  {
    "id": "handover-action",
    "title": "Respond to a named handover",
    "group": "Team & capacity",
    "path": "workflows/handovers/{id}/actions",
    "capability": [
      "CARE",
      "NURSING"
    ],
    "fields": [
      {
        "key": "reason",
        "label": "Actual reason and supporting evidence",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "action",
        "label": "Action",
        "required": true,
        "options": [
          "ACCEPT",
          "DECLINE",
          "CANCEL"
        ]
      },
      {
        "key": "occurred_at",
        "label": "Occurred at",
        "required": true,
        "type": "datetime-local"
      },
      {
        "key": "intent_confirmed",
        "label": "I intend to attest and commit this action under my authenticated authority",
        "required": true,
        "type": "intent"
      }
    ],
    "context": false,
    "patient": true,
    "target": "team_handover"
  },
  {
    "id": "admission-order",
    "title": "Order inpatient admission",
    "group": "Inpatient",
    "path": "workflows/admission-orders",
    "capability": [
      "CARE"
    ],
    "fields": [
      {
        "key": "occurred_at",
        "label": "Occurred at",
        "required": true,
        "type": "datetime-local"
      },
      {
        "key": "signed_note_id",
        "label": "Signed note id",
        "required": true,
        "ref": "signed_note"
      },
      {
        "key": "intended_ward",
        "label": "Intended ward",
        "required": true
      },
      {
        "key": "reason",
        "label": "Actual reason and supporting evidence",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "policy_reference",
        "label": "Applicable adopted policy and version",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "intent_confirmed",
        "label": "I intend to attest and commit this action under my authenticated authority",
        "required": true,
        "type": "intent"
      }
    ],
    "context": true,
    "patient": false
  },
  {
    "id": "bed-hold",
    "title": "Reserve an actual local bed",
    "group": "Inpatient",
    "path": "workflows/bed-holds",
    "capability": [
      "NURSING"
    ],
    "fields": [
      {
        "key": "occurred_at",
        "label": "Occurred at",
        "required": true,
        "type": "datetime-local"
      },
      {
        "key": "admission_order_id",
        "label": "Admission order id",
        "required": true,
        "ref": "admission_order"
      },
      {
        "key": "bed_id",
        "label": "Bed id",
        "required": true,
        "ref": "bed"
      },
      {
        "key": "expires_at",
        "label": "Expires at",
        "required": true,
        "type": "datetime-local"
      },
      {
        "key": "reason",
        "label": "Actual reason and supporting evidence",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "intent_confirmed",
        "label": "I intend to attest and commit this action under my authenticated authority",
        "required": true,
        "type": "intent"
      }
    ],
    "context": true,
    "patient": false
  },
  {
    "id": "cancel-commitment",
    "title": "Cancel pending admission, bed or stock commitment",
    "group": "Inpatient",
    "path": "workflows/commitments/{id}/cancel",
    "capability": [
      "CARE",
      "NURSING",
      "PHARMACY"
    ],
    "fields": [
      {
        "key": "reason",
        "label": "Actual reason and supporting evidence",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "action",
        "label": "Action",
        "required": true,
        "options": [
          "CANCEL"
        ]
      },
      {
        "key": "occurred_at",
        "label": "Occurred at",
        "required": true,
        "type": "datetime-local"
      },
      {
        "key": "intent_confirmed",
        "label": "I intend to attest and commit this action under my authenticated authority",
        "required": true,
        "type": "intent"
      }
    ],
    "context": false,
    "patient": true,
    "target": "commitment"
  },
  {
    "id": "ward-event",
    "title": "Record leave, return, special disposition or bed release",
    "group": "Inpatient",
    "path": "workflows/stays/{id}/events",
    "capability": [
      "CARE",
      "NURSING"
    ],
    "fields": [
      {
        "key": "reason",
        "label": "Actual reason and supporting evidence",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "action",
        "label": "Action",
        "required": true,
        "options": [
          "LEAVE",
          "RETURN",
          "SELF_DISCHARGE",
          "DEATH",
          "RELEASE_BED",
          "DECLINE_TRANSFER",
          "ACCEPT_NURSING"
        ]
      },
      {
        "key": "occurred_at",
        "label": "Occurred at",
        "required": true,
        "type": "datetime-local"
      },
      {
        "key": "signed_summary_id",
        "label": "Signed summary id",
        "required": false,
        "ref": "signed_note"
      },
      {
        "key": "policy_reference",
        "label": "Applicable adopted policy and version",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "instructions",
        "label": "Instructions",
        "required": false,
        "type": "textarea"
      },
      {
        "key": "medication_reconciliation",
        "label": "Medication reconciliation",
        "required": false,
        "type": "textarea"
      },
      {
        "key": "follow_up_owner_id",
        "label": "Follow up owner id",
        "required": false,
        "ref": "staff"
      },
      {
        "key": "actual_evidence",
        "label": "Actual observation or fulfilment evidence",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "intent_confirmed",
        "label": "I intend to attest and commit this action under my authenticated authority",
        "required": true,
        "type": "intent"
      }
    ],
    "context": false,
    "patient": true,
    "target": "stay",
    "explanation": "Clinical disposition, physical bed release, statutory documentation and settlement remain separate actual events."
  },
  {
    "id": "nursing",
    "title": "Record actual bedside assessment",
    "group": "Nursing",
    "path": "workflows/nursing-assessments",
    "capability": [
      "NURSING"
    ],
    "fields": [
      {
        "key": "occurred_at",
        "label": "Occurred at",
        "required": true,
        "type": "datetime-local"
      },
      {
        "key": "assessment",
        "label": "Assessment",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "plan",
        "label": "Plan",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "escalation",
        "label": "Escalation",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "source",
        "label": "Actual source and provenance",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "amends_id",
        "label": "Original actual record being corrected, if applicable",
        "required": false
      },
      {
        "key": "amendment_reason",
        "label": "Amendment reason",
        "required": false,
        "type": "textarea"
      },
      {
        "key": "intent_confirmed",
        "label": "I intend to attest and commit this action under my authenticated authority",
        "required": true,
        "type": "intent"
      }
    ],
    "context": true,
    "patient": false
  },
  {
    "id": "fluid",
    "title": "Record measured intake or output",
    "group": "Nursing",
    "path": "workflows/fluids",
    "capability": [
      "NURSING"
    ],
    "fields": [
      {
        "key": "occurred_at",
        "label": "Occurred at",
        "required": true,
        "type": "datetime-local"
      },
      {
        "key": "direction",
        "label": "Direction",
        "required": true,
        "options": [
          "INTAKE",
          "OUTPUT"
        ]
      },
      {
        "key": "route_or_source",
        "label": "Route or source",
        "required": true
      },
      {
        "key": "quantity",
        "label": "Actual physical quantity (signed change for adjustment)",
        "required": true,
        "type": "decimal"
      },
      {
        "key": "unit",
        "label": "Unit",
        "required": true
      },
      {
        "key": "method",
        "label": "Method",
        "required": true
      },
      {
        "key": "source",
        "label": "Actual source and provenance",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "amends_id",
        "label": "Original actual record being corrected, if applicable",
        "required": false
      },
      {
        "key": "amendment_reason",
        "label": "Amendment reason",
        "required": false,
        "type": "textarea"
      },
      {
        "key": "intent_confirmed",
        "label": "I intend to attest and commit this action under my authenticated authority",
        "required": true,
        "type": "intent"
      }
    ],
    "context": true,
    "patient": false
  },
  {
    "id": "labour",
    "title": "Record structured maternal and labour review",
    "group": "Maternal & child",
    "path": "workflows/labour",
    "capability": [
      "CARE"
    ],
    "fields": [
      {
        "key": "occurred_at",
        "label": "Occurred at",
        "required": true,
        "type": "datetime-local"
      },
      {
        "key": "programme_id",
        "label": "Programme id",
        "required": false,
        "ref": "programme"
      },
      {
        "key": "source",
        "label": "Actual source and provenance",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "policy_reference",
        "label": "Applicable adopted policy and version",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "amends_id",
        "label": "Original actual record being corrected, if applicable",
        "required": false
      },
      {
        "key": "amendment_reason",
        "label": "Amendment reason",
        "required": false,
        "type": "textarea"
      },
      {
        "key": "intent_confirmed",
        "label": "I intend to attest and commit this action under my authenticated authority",
        "required": true,
        "type": "intent"
      },
      {
        "key": "dating_source",
        "label": "Dating source",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "dating_uncertainty",
        "label": "Dating or history uncertainty",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "gestation_days",
        "label": "Gestation days",
        "required": false,
        "type": "integer"
      },
      {
        "key": "labour_stage_as_assessed",
        "label": "Labour stage as assessed",
        "required": true
      },
      {
        "key": "assessment",
        "label": "Assessment",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "plan",
        "label": "Plan",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "review_owner_id",
        "label": "Review owner id",
        "required": true,
        "ref": "staff"
      },
      {
        "key": "review_due_at",
        "label": "Actual accountable review due time",
        "required": true,
        "type": "datetime-local"
      }
    ],
    "context": true,
    "patient": false,
    "repeat": {
      "key": "observations",
      "label": "Actual observations",
      "fields": [
        {
          "key": "code.system",
          "label": "System",
          "required": true
        },
        {
          "key": "code.code",
          "label": "Code",
          "required": true
        },
        {
          "key": "code.display",
          "label": "Display",
          "required": true
        },
        {
          "key": "code.version",
          "label": "Version",
          "required": true
        },
        {
          "key": "value",
          "label": "Value",
          "required": false,
          "type": "decimal"
        },
        {
          "key": "unit",
          "label": "Unit",
          "required": false
        },
        {
          "key": "absent_reason",
          "label": "Explicit reason no measurement is recorded",
          "required": false
        },
        {
          "key": "source",
          "label": "Actual source and provenance",
          "required": true,
          "type": "textarea"
        }
      ],
      "max": 30
    }
  },
  {
    "id": "birth",
    "title": "Record birth and separate infant chart links",
    "group": "Maternal & child",
    "path": "workflows/births",
    "capability": [
      "CARE"
    ],
    "fields": [
      {
        "key": "occurred_at",
        "label": "Occurred at",
        "required": true,
        "type": "datetime-local"
      },
      {
        "key": "programme_id",
        "label": "Programme id",
        "required": false,
        "ref": "programme"
      },
      {
        "key": "source",
        "label": "Actual source and provenance",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "policy_reference",
        "label": "Applicable adopted policy and version",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "amends_id",
        "label": "Original actual record being corrected, if applicable",
        "required": false
      },
      {
        "key": "amendment_reason",
        "label": "Amendment reason",
        "required": false,
        "type": "textarea"
      },
      {
        "key": "intent_confirmed",
        "label": "I intend to attest and commit this action under my authenticated authority",
        "required": true,
        "type": "intent"
      },
      {
        "key": "signed_note_id",
        "label": "Signed note id",
        "required": true,
        "ref": "signed_note"
      },
      {
        "key": "mode_as_recorded",
        "label": "Mode as recorded",
        "required": true
      },
      {
        "key": "maternal_outcome",
        "label": "Maternal outcome",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "actual_team",
        "label": "Actually involved qualified clinicians",
        "required": true,
        "ref": "staff",
        "type": "multi"
      },
      {
        "key": "maternal_review_owner_id",
        "label": "Maternal review owner id",
        "required": true,
        "ref": "staff"
      },
      {
        "key": "maternal_review_due_at",
        "label": "Maternal review due at",
        "required": true,
        "type": "datetime-local"
      }
    ],
    "context": true,
    "patient": false,
    "repeat": {
      "key": "infants",
      "label": "Actual infants",
      "fields": [
        {
          "key": "patient_id",
          "label": "Actual independent infant chart identifier",
          "required": true
        },
        {
          "key": "encounter_id",
          "label": "Actual infant encounter identifier",
          "required": true
        },
        {
          "key": "birth_order",
          "label": "Birth order",
          "required": true,
          "type": "integer"
        },
        {
          "key": "outcome",
          "label": "Outcome",
          "required": true,
          "options": [
            "LIVE_BIRTH",
            "STILLBIRTH",
            "UNKNOWN"
          ]
        },
        {
          "key": "occurred_at",
          "label": "Occurred at",
          "required": true,
          "type": "datetime-local"
        },
        {
          "key": "relationship_evidence",
          "label": "Relationship evidence",
          "required": true,
          "type": "textarea"
        },
        {
          "key": "observations.0.code.system",
          "label": "System",
          "required": true
        },
        {
          "key": "observations.0.code.code",
          "label": "Code",
          "required": true
        },
        {
          "key": "observations.0.code.display",
          "label": "Display",
          "required": true
        },
        {
          "key": "observations.0.code.version",
          "label": "Version",
          "required": true
        },
        {
          "key": "observations.0.value",
          "label": "Value",
          "required": false,
          "type": "decimal"
        },
        {
          "key": "observations.0.unit",
          "label": "Unit",
          "required": false
        },
        {
          "key": "observations.0.absent_reason",
          "label": "Explicit reason no measurement is recorded",
          "required": false
        },
        {
          "key": "observations.0.source",
          "label": "Actual source and provenance",
          "required": true,
          "type": "textarea"
        },
        {
          "key": "follow_up_owner_id",
          "label": "Follow up owner id",
          "required": true,
          "ref": "staff"
        },
        {
          "key": "follow_up_due_at",
          "label": "Follow up due at",
          "required": true,
          "type": "datetime-local"
        }
      ],
      "max": 10
    },
    "explanation": "Register and accept care on each infant chart separately first. Relationship evidence grants no caregiver or infant-chart access."
  },
  {
    "id": "growth",
    "title": "Record child measurements and sourced review",
    "group": "Maternal & child",
    "path": "workflows/growth",
    "capability": [
      "CARE"
    ],
    "fields": [
      {
        "key": "occurred_at",
        "label": "Occurred at",
        "required": true,
        "type": "datetime-local"
      },
      {
        "key": "programme_id",
        "label": "Programme id",
        "required": false,
        "ref": "programme"
      },
      {
        "key": "source",
        "label": "Actual source and provenance",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "policy_reference",
        "label": "Applicable adopted policy and version",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "amends_id",
        "label": "Original actual record being corrected, if applicable",
        "required": false
      },
      {
        "key": "amendment_reason",
        "label": "Amendment reason",
        "required": false,
        "type": "textarea"
      },
      {
        "key": "intent_confirmed",
        "label": "I intend to attest and commit this action under my authenticated authority",
        "required": true,
        "type": "intent"
      },
      {
        "key": "age_context",
        "label": "Age context",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "interpretation_as_assessed",
        "label": "Interpretation as assessed",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "review_owner_id",
        "label": "Review owner id",
        "required": true,
        "ref": "staff"
      },
      {
        "key": "review_due_at",
        "label": "Actual accountable review due time",
        "required": true,
        "type": "datetime-local"
      }
    ],
    "context": true,
    "patient": false,
    "repeat": {
      "key": "measurements",
      "label": "Actual measurements",
      "fields": [
        {
          "key": "code.system",
          "label": "System",
          "required": true
        },
        {
          "key": "code.code",
          "label": "Code",
          "required": true
        },
        {
          "key": "code.display",
          "label": "Display",
          "required": true
        },
        {
          "key": "code.version",
          "label": "Version",
          "required": true
        },
        {
          "key": "value",
          "label": "Value",
          "required": false,
          "type": "decimal"
        },
        {
          "key": "unit",
          "label": "Unit",
          "required": false
        },
        {
          "key": "absent_reason",
          "label": "Explicit reason no measurement is recorded",
          "required": false
        },
        {
          "key": "source",
          "label": "Actual source and provenance",
          "required": true,
          "type": "textarea"
        }
      ],
      "max": 20
    }
  },
  {
    "id": "immunisation",
    "title": "Record traceable actual immunisation",
    "group": "Maternal & child",
    "path": "workflows/immunisations",
    "capability": [
      "NURSING"
    ],
    "fields": [
      {
        "key": "occurred_at",
        "label": "Occurred at",
        "required": true,
        "type": "datetime-local"
      },
      {
        "key": "programme_id",
        "label": "Programme id",
        "required": false,
        "ref": "programme"
      },
      {
        "key": "source",
        "label": "Actual source and provenance",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "policy_reference",
        "label": "Applicable adopted policy and version",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "amends_id",
        "label": "Original actual record being corrected, if applicable",
        "required": false
      },
      {
        "key": "amendment_reason",
        "label": "Amendment reason",
        "required": false,
        "type": "textarea"
      },
      {
        "key": "intent_confirmed",
        "label": "I intend to attest and commit this action under my authenticated authority",
        "required": true,
        "type": "intent"
      },
      {
        "key": "administration_id",
        "label": "Actual given administration",
        "required": true,
        "ref": "administration"
      },
      {
        "key": "dispense_id",
        "label": "Dispense id",
        "required": true,
        "ref": "dispense"
      },
      {
        "key": "schedule_reference",
        "label": "Schedule reference",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "next_review_owner_id",
        "label": "Next review owner id",
        "required": true,
        "ref": "staff"
      },
      {
        "key": "next_review_due_at",
        "label": "Next review due at",
        "required": true,
        "type": "datetime-local"
      }
    ],
    "context": true,
    "patient": false,
    "explanation": "Requires an actual given administration and traceable supply. No dose schedule is calculated."
  },
  {
    "id": "medicine-reconciliation",
    "title": "Attest medicine reconciliation",
    "group": "Medicine stewardship",
    "path": "workflows/reconciliations",
    "capability": [
      "CARE"
    ],
    "fields": [
      {
        "key": "occurred_at",
        "label": "Occurred at",
        "required": true,
        "type": "datetime-local"
      },
      {
        "key": "transition",
        "label": "Transition",
        "required": true,
        "options": [
          "ADMISSION",
          "TRANSFER",
          "REVIEW",
          "DISCHARGE"
        ]
      },
      {
        "key": "allergy_review",
        "label": "Allergy review",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "unresolved_owner_id",
        "label": "Unresolved owner id",
        "required": true,
        "ref": "staff"
      },
      {
        "key": "review_due_at",
        "label": "Actual accountable review due time",
        "required": true,
        "type": "datetime-local"
      },
      {
        "key": "instructions",
        "label": "Instructions",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "policy_reference",
        "label": "Applicable adopted policy and version",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "intent_confirmed",
        "label": "I intend to attest and commit this action under my authenticated authority",
        "required": true,
        "type": "intent"
      }
    ],
    "context": true,
    "patient": false,
    "repeat": {
      "key": "items",
      "label": "Actual items",
      "fields": [
        {
          "key": "medicine_id",
          "label": "Medicine id",
          "required": false,
          "ref": "medication"
        },
        {
          "key": "external_description",
          "label": "External description",
          "required": false,
          "type": "textarea"
        },
        {
          "key": "source",
          "label": "Actual source and provenance",
          "required": true,
          "type": "textarea"
        },
        {
          "key": "assessment",
          "label": "Assessment",
          "required": true,
          "options": [
            "CONTINUE",
            "STOP",
            "CHANGE",
            "UNKNOWN",
            "NOT_TAKEN"
          ]
        },
        {
          "key": "reason",
          "label": "Actual reason and supporting evidence",
          "required": true,
          "type": "textarea"
        }
      ],
      "max": 100
    },
    "explanation": "This attestation does not silently change prescriptions. Intentionally stop or replace the actual order separately."
  },
  {
    "id": "stock-hold",
    "title": "Reserve actual stock for a current order",
    "group": "Medicine stewardship",
    "path": "workflows/stock-holds",
    "capability": [
      "PHARMACY"
    ],
    "fields": [
      {
        "key": "occurred_at",
        "label": "Occurred at",
        "required": true,
        "type": "datetime-local"
      },
      {
        "key": "medication_id",
        "label": "Medication id",
        "required": true,
        "ref": "medication"
      },
      {
        "key": "lot_id",
        "label": "Lot id",
        "required": true,
        "ref": "lot"
      },
      {
        "key": "quantity",
        "label": "Actual physical quantity (signed change for adjustment)",
        "required": true,
        "type": "decimal"
      },
      {
        "key": "unit",
        "label": "Unit",
        "required": true
      },
      {
        "key": "expires_at",
        "label": "Expires at",
        "required": true,
        "type": "datetime-local"
      },
      {
        "key": "reason",
        "label": "Actual reason and supporting evidence",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "intent_confirmed",
        "label": "I intend to attest and commit this action under my authenticated authority",
        "required": true,
        "type": "intent"
      }
    ],
    "context": true,
    "patient": false
  },
  {
    "id": "adjustment",
    "title": "Propose witnessed physical stock adjustment",
    "group": "Medicine stewardship",
    "path": "workflows/stock-adjustments",
    "capability": [
      "PHARMACY"
    ],
    "fields": [
      {
        "key": "lot_id",
        "label": "Lot id",
        "required": true,
        "ref": "lot"
      },
      {
        "key": "quantity",
        "label": "Actual physical quantity (signed change for adjustment)",
        "required": true,
        "type": "decimal"
      },
      {
        "key": "unit",
        "label": "Unit",
        "required": true
      },
      {
        "key": "disposition",
        "label": "Disposition",
        "required": true,
        "options": [
          "AVAILABLE",
          "QUARANTINED"
        ]
      },
      {
        "key": "physical_evidence",
        "label": "Physical evidence",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "policy_reference",
        "label": "Applicable adopted policy and version",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "reason",
        "label": "Actual reason and supporting evidence",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "intent_confirmed",
        "label": "I intend to attest and commit this action under my authenticated authority",
        "required": true,
        "type": "intent"
      }
    ],
    "context": false,
    "patient": false
  },
  {
    "id": "stock-return",
    "title": "Propose actual returned stock for quarantine",
    "group": "Medicine stewardship",
    "path": "workflows/stock-returns",
    "capability": [
      "PHARMACY"
    ],
    "fields": [
      {
        "key": "lot_id",
        "label": "Lot id",
        "required": true,
        "ref": "lot"
      },
      {
        "key": "quantity",
        "label": "Actual physical quantity (signed change for adjustment)",
        "required": true,
        "type": "decimal"
      },
      {
        "key": "unit",
        "label": "Unit",
        "required": true
      },
      {
        "key": "disposition",
        "label": "Disposition",
        "required": true,
        "options": [
          "AVAILABLE",
          "QUARANTINED"
        ]
      },
      {
        "key": "physical_evidence",
        "label": "Physical evidence",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "policy_reference",
        "label": "Applicable adopted policy and version",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "reason",
        "label": "Actual reason and supporting evidence",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "intent_confirmed",
        "label": "I intend to attest and commit this action under my authenticated authority",
        "required": true,
        "type": "intent"
      },
      {
        "key": "dispense_id",
        "label": "Dispense id",
        "required": true,
        "ref": "dispense"
      }
    ],
    "context": false,
    "patient": true
  },
  {
    "id": "stock-witness",
    "title": "Independently review actual physical stock evidence",
    "group": "Medicine stewardship",
    "path": "workflows/stock-movements/{id}/witness",
    "capability": [
      "PHARMACY"
    ],
    "fields": [
      {
        "key": "reason",
        "label": "Actual reason and supporting evidence",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "action",
        "label": "Action",
        "required": true,
        "options": [
          "APPROVE",
          "REJECT"
        ]
      },
      {
        "key": "occurred_at",
        "label": "Occurred at",
        "required": true,
        "type": "datetime-local"
      },
      {
        "key": "intent_confirmed",
        "label": "I intend to attest and commit this action under my authenticated authority",
        "required": true,
        "type": "intent"
      }
    ],
    "context": false,
    "patient": false,
    "target": "stock_movement",
    "explanation": "An independent qualified pharmacist reviews current physical evidence before the one stock effect."
  },
  {
    "id": "substitution",
    "title": "Request exact product substitution",
    "group": "Medicine stewardship",
    "path": "workflows/substitutions",
    "capability": [
      "PHARMACY"
    ],
    "fields": [
      {
        "key": "occurred_at",
        "label": "Occurred at",
        "required": true,
        "type": "datetime-local"
      },
      {
        "key": "medication_id",
        "label": "Medication id",
        "required": true,
        "ref": "medication"
      },
      {
        "key": "replacement_product_id",
        "label": "Replacement product id",
        "required": true,
        "ref": "product"
      },
      {
        "key": "prescriber_id",
        "label": "Prescriber id",
        "required": true,
        "ref": "staff"
      },
      {
        "key": "reason",
        "label": "Actual reason and supporting evidence",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "policy_reference",
        "label": "Applicable adopted policy and version",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "intent_confirmed",
        "label": "I intend to attest and commit this action under my authenticated authority",
        "required": true,
        "type": "intent"
      }
    ],
    "context": true,
    "patient": false
  },
  {
    "id": "substitution-decision",
    "title": "Review exact signed replacement order",
    "group": "Medicine stewardship",
    "path": "workflows/substitutions/{id}/decision",
    "capability": [
      "PRESCRIBE"
    ],
    "fields": [
      {
        "key": "reason",
        "label": "Actual reason and supporting evidence",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "action",
        "label": "Action",
        "required": true,
        "options": [
          "APPROVE",
          "REJECT"
        ]
      },
      {
        "key": "occurred_at",
        "label": "Occurred at",
        "required": true,
        "type": "datetime-local"
      },
      {
        "key": "intent_confirmed",
        "label": "I intend to attest and commit this action under my authenticated authority",
        "required": true,
        "type": "intent"
      },
      {
        "key": "replacement_medication_id",
        "label": "Replacement medication id",
        "required": false,
        "ref": "medication"
      }
    ],
    "context": false,
    "patient": true,
    "target": "substitution"
  },
  {
    "id": "anaesthesia",
    "title": "Record actual anaesthesia and recovery monitoring",
    "group": "Procedural monitoring",
    "path": "workflows/anaesthesia",
    "capability": [
      "PROCEDURE"
    ],
    "fields": [
      {
        "key": "occurred_at",
        "label": "Occurred at",
        "required": true,
        "type": "datetime-local"
      },
      {
        "key": "programme_id",
        "label": "Programme id",
        "required": false,
        "ref": "programme"
      },
      {
        "key": "source",
        "label": "Actual source and provenance",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "policy_reference",
        "label": "Applicable adopted policy and version",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "amends_id",
        "label": "Original actual record being corrected, if applicable",
        "required": false
      },
      {
        "key": "amendment_reason",
        "label": "Amendment reason",
        "required": false,
        "type": "textarea"
      },
      {
        "key": "intent_confirmed",
        "label": "I intend to attest and commit this action under my authenticated authority",
        "required": true,
        "type": "intent"
      },
      {
        "key": "procedure_id",
        "label": "Procedure id",
        "required": true,
        "ref": "procedure"
      },
      {
        "key": "phase",
        "label": "Phase",
        "required": true,
        "options": [
          "PRE_ASSESSMENT",
          "INDUCTION",
          "MAINTENANCE",
          "EMERGENCE",
          "RECOVERY"
        ]
      },
      {
        "key": "technique",
        "label": "Technique",
        "required": true
      },
      {
        "key": "medication_evidence",
        "label": "Medication evidence",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "airway_and_monitoring",
        "label": "Airway and monitoring",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "complications",
        "label": "Complications",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "plan",
        "label": "Plan",
        "required": true,
        "type": "textarea"
      }
    ],
    "context": true,
    "patient": false,
    "repeat": {
      "key": "observations",
      "label": "Actual observations",
      "fields": [
        {
          "key": "code.system",
          "label": "System",
          "required": true
        },
        {
          "key": "code.code",
          "label": "Code",
          "required": true
        },
        {
          "key": "code.display",
          "label": "Display",
          "required": true
        },
        {
          "key": "code.version",
          "label": "Version",
          "required": true
        },
        {
          "key": "value",
          "label": "Value",
          "required": false,
          "type": "decimal"
        },
        {
          "key": "unit",
          "label": "Unit",
          "required": false
        },
        {
          "key": "absent_reason",
          "label": "Explicit reason no measurement is recorded",
          "required": false
        },
        {
          "key": "source",
          "label": "Actual source and provenance",
          "required": true,
          "type": "textarea"
        }
      ],
      "max": 30
    }
  },
  {
    "id": "device",
    "title": "Record actual implant or device traceability",
    "group": "Procedural monitoring",
    "path": "workflows/devices",
    "capability": [
      "PROCEDURE"
    ],
    "fields": [
      {
        "key": "occurred_at",
        "label": "Occurred at",
        "required": true,
        "type": "datetime-local"
      },
      {
        "key": "programme_id",
        "label": "Programme id",
        "required": false,
        "ref": "programme"
      },
      {
        "key": "source",
        "label": "Actual source and provenance",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "policy_reference",
        "label": "Applicable adopted policy and version",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "amends_id",
        "label": "Original actual record being corrected, if applicable",
        "required": false
      },
      {
        "key": "amendment_reason",
        "label": "Amendment reason",
        "required": false,
        "type": "textarea"
      },
      {
        "key": "intent_confirmed",
        "label": "I intend to attest and commit this action under my authenticated authority",
        "required": true,
        "type": "intent"
      },
      {
        "key": "procedure_id",
        "label": "Procedure id",
        "required": true,
        "ref": "procedure"
      },
      {
        "key": "device_identifier",
        "label": "Device identifier",
        "required": true
      },
      {
        "key": "manufacturer",
        "label": "Manufacturer",
        "required": true
      },
      {
        "key": "model",
        "label": "Model",
        "required": true
      },
      {
        "key": "serial_or_lot",
        "label": "Serial or lot",
        "required": true
      },
      {
        "key": "expires_at",
        "label": "Expires at",
        "required": false,
        "type": "datetime-local"
      },
      {
        "key": "actual_disposition",
        "label": "Actual disposition",
        "required": true,
        "options": [
          "IMPLANTED",
          "USED",
          "REMOVED"
        ]
      },
      {
        "key": "actual_evidence",
        "label": "Actual observation or fulfilment evidence",
        "required": true,
        "type": "textarea"
      }
    ],
    "context": true,
    "patient": false
  },
  {
    "id": "recall",
    "title": "Assign review of an actual device or component recall",
    "group": "Procedural monitoring",
    "path": "workflows/recalls",
    "capability": [
      "PROCEDURE"
    ],
    "fields": [
      {
        "key": "occurred_at",
        "label": "Occurred at",
        "required": true,
        "type": "datetime-local"
      },
      {
        "key": "source_id",
        "label": "Source id",
        "required": true,
        "ref": "recall_source"
      },
      {
        "key": "issuer_reference",
        "label": "Issuer reference",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "action_plan",
        "label": "Action plan",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "owner_id",
        "label": "Owner id",
        "required": true,
        "ref": "staff"
      },
      {
        "key": "due_at",
        "label": "Due at",
        "required": true,
        "type": "datetime-local"
      },
      {
        "key": "intent_confirmed",
        "label": "I intend to attest and commit this action under my authenticated authority",
        "required": true,
        "type": "intent"
      }
    ],
    "context": true,
    "patient": false
  },
  {
    "id": "infusion",
    "title": "Record an actual manual infusion event",
    "group": "Nursing",
    "path": "workflows/infusions",
    "capability": [
      "NURSING"
    ],
    "fields": [
      {
        "key": "occurred_at",
        "label": "Occurred at",
        "required": true,
        "type": "datetime-local"
      },
      {
        "key": "programme_id",
        "label": "Programme id",
        "required": false,
        "ref": "programme"
      },
      {
        "key": "source",
        "label": "Actual source and provenance",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "policy_reference",
        "label": "Applicable adopted policy and version",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "amends_id",
        "label": "Original actual record being corrected, if applicable",
        "required": false
      },
      {
        "key": "amendment_reason",
        "label": "Amendment reason",
        "required": false,
        "type": "textarea"
      },
      {
        "key": "intent_confirmed",
        "label": "I intend to attest and commit this action under my authenticated authority",
        "required": true,
        "type": "intent"
      },
      {
        "key": "medication_id",
        "label": "Medication id",
        "required": true,
        "ref": "medication"
      },
      {
        "key": "action",
        "label": "Action",
        "required": true,
        "options": [
          "START",
          "RATE_CHANGE",
          "MONITOR",
          "STOP"
        ]
      },
      {
        "key": "actual_rate",
        "label": "Actual rate",
        "required": false,
        "type": "decimal"
      },
      {
        "key": "rate_unit",
        "label": "Rate unit",
        "required": false
      },
      {
        "key": "actual_volume",
        "label": "Actual volume",
        "required": false,
        "type": "decimal"
      },
      {
        "key": "volume_unit",
        "label": "Volume unit",
        "required": false
      },
      {
        "key": "manual_check_reference",
        "label": "Actual manual review or adopted formula reference",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "witness_id",
        "label": "Witness id",
        "required": true,
        "ref": "staff"
      }
    ],
    "context": true,
    "patient": false,
    "explanation": "No rate or dose is calculated. Naming a witness is distinct from their separate personal attestation."
  },
  {
    "id": "infusion-witness",
    "title": "Personally attest or dispute infusion evidence",
    "group": "Nursing",
    "path": "workflows/infusions/{id}/witness",
    "capability": [
      "NURSING"
    ],
    "fields": [
      {
        "key": "reason",
        "label": "Actual reason and supporting evidence",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "action",
        "label": "Action",
        "required": true,
        "options": [
          "ATTEST",
          "DISPUTE"
        ]
      },
      {
        "key": "occurred_at",
        "label": "Occurred at",
        "required": true,
        "type": "datetime-local"
      },
      {
        "key": "intent_confirmed",
        "label": "I intend to attest and commit this action under my authenticated authority",
        "required": true,
        "type": "intent"
      }
    ],
    "context": false,
    "patient": true,
    "target": "infusion_event"
  },
  {
    "id": "care-instructions",
    "title": "Record individual care instructions and communication",
    "group": "Continuity plan",
    "path": "workflows/instructions",
    "capability": [
      "CARE"
    ],
    "fields": [
      {
        "key": "occurred_at",
        "label": "Occurred at",
        "required": true,
        "type": "datetime-local"
      },
      {
        "key": "signed_summary_id",
        "label": "Signed summary id",
        "required": true,
        "ref": "signed_note"
      },
      {
        "key": "language",
        "label": "Language",
        "required": true
      },
      {
        "key": "instructions",
        "label": "Instructions",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "warning_and_contact_plan",
        "label": "Warning and contact plan",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "pending_work_explained",
        "label": "Pending work explained",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "medicine_plan",
        "label": "Medicine plan",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "review_owner_id",
        "label": "Review owner id",
        "required": true,
        "ref": "staff"
      },
      {
        "key": "review_due_at",
        "label": "Actual accountable review due time",
        "required": true,
        "type": "datetime-local"
      },
      {
        "key": "communication",
        "label": "Communication",
        "required": true,
        "options": [
          "PREPARED",
          "GIVEN_IN_PERSON",
          "ACTUAL_AUTHORISED_COMMUNICATION"
        ]
      },
      {
        "key": "communication_evidence",
        "label": "Communication evidence",
        "required": true,
        "type": "textarea"
      },
      {
        "key": "intent_confirmed",
        "label": "I intend to attest and commit this action under my authenticated authority",
        "required": true,
        "type": "intent"
      }
    ],
    "context": true,
    "patient": false,
    "explanation": "Prepared instructions and actual communication remain separate. Pending clinical work keeps its named owner."
  }
];
