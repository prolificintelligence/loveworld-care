# Clinical implementation contracts

The archived suite's IDs and meanings are retained. Native typed routes are under `/v1/clinical/{facility_id}`; the scope and permissions are resolved by the authoritative API, not by the browser's selected role. This register records implementation extensions without renumbering the suite's capture forms or command contracts.

| Extension | Meaning |
|---|---|
| LWH-EXT-CLINICAL-001 | Attributed native clinical capture, including drafts, identity, coded facts, consent and continuity metadata; the record kind distinguishes its typed schema |
| LWH-EXT-CLINICAL-002 | Reasoned demographic correction retaining the previous version |
| LWH-EXT-CLINICAL-003 | Unsigned document draft revision; not a signature |
| LWH-EXT-CLINICAL-004 | Programme review and continuing follow-up |
| LWH-EXT-CLINICAL-005 | Appointment request/acceptance/attendance lifecycle |
| LWH-EXT-CLINICAL-006 | Independently reviewed, reversible identity crosswalk |
| LWH-EXT-CLINICAL-007 | Released-result acknowledgement, clinical response and actual communication; not another result release |
| LWH-EXT-CLINICAL-008 | Task assignment, ownership, acceptance, progress, handover and completion; not a scheduler's due notification |
| LWH-EXT-CLINICAL-009 | Procedure preparation, safety phase, recovery and handover; actual performance emits LWH-EVT-027 |
| LWH-EXT-CLINICAL-010 | Actual transfusion witness/monitoring/closure/reaction event |
| LWH-EXT-CLINICAL-011 | Diagnostic order department/state update after release; actual release emits LWH-EVT-018 |

Canonical clinical events retain the SPEC-011 meanings: encounter changed (015), document signed/amended (016/017), order released (018), specimen changed (019), report released/amended (020/021), medicine order changed (022), actual dispensing (023), actual administration/omission (024), inpatient stay changed (026), actual procedure performed (027), referral state changed (028), sharing grant revoked (029), service-linked charge (031) and actual receipt (032). No due-event scheduling or remote acceptance is inferred from capture.

Each encrypted event carries schema version 2.0.0, resource and patient context, expected resulting version, actor, applicable policy/privilege evidence, actual and recorded times, authority node/epoch, previous hash and server attestation signature. Exact clinical input schemas are defined by `platform/clinical/contracts.py`. The `/care` forms call these contracts directly; no generated JSON editor or demo responder supplies the workflow.
