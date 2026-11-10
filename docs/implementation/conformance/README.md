# Canonical conformance register

This register covers every baseline form, field, screen, state family and interface. It is an engineering crosswalk with explicit exceptions. It does not accept the suite, adopt an extension or approve operation.

Run `python scripts/build_conformance_register.py` in the existing workspace environment to regenerate the JSON and five CSV views. Run with `--check` to reject stale output. CI verifies the complete register against the immutable 78-document baseline, typed request models and the effective institutional API routes. Legacy/demo applications never supply mappings.

`canonical-register.json` retains original field identity, requiredness, type, rule and source. Candidate bindings include actual typed properties, requiredness differences and source hashes. The form rows link handlers, permission/validation/persistence source candidates and existing engineering test candidates. These references are starting points for review, not assertions that every field has passed those tests. Schema definitions are retained so references and enum/range constraints can be inspected. Generic canonical capture envelopes and split native commands remain distinct.

Screen links associate the current platform page with its domain. They do not establish 75 individual screen implementations. State rows retain the entire canonical state/guard/effect text and source candidates. Each transition still needs its own wrong-role, wrong-subject, expired-authority, wrong-version, replay, missing-evidence, reversed-order and outage proof. Interfaces retain all 52 capture routes, 15 commands and 15 query families; path matching alone never establishes semantics.

Current results: 47 forms have candidate typed-route mappings and four retain explicit mapping gaps; 48 fields have name/alias candidates and 307 retain explicit field gaps. Every field still needs field-specific purpose permissions, validation, canonical missingness, persistence and failure proof. All 75 screens and 30 state families remain semantically unqualified. The four form mapping gaps include rights requests, programme funding, downtime/sync and optional ERP; a mapping gap is not proof that every related capability is absent.

Director-first review starts with forms 001–018 and screens 001–030: registry → affiliation → returns → independent verification → permitted intelligence → accepted intervention/outcome. Resolve the field-specific exceptions before advancing claims. Record explicit typed extensions for owner review; preserve baseline meanings and actual adoption dependencies. The existing clinical extension register remains applicable.

Formal acceptance remains **200 requirements /111 cases NOT_RUN**. Operating adoption and independent actual-role/device/accessibility/low-bandwidth UAT remain separate gates.
