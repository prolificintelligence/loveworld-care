# ADR-0006: Shared design system with per-app themes

- **Status:** Accepted
- **Date:** 2026-11-01
- **Spec refs:** §21.6 (WCAG 2.2 AA, shared-device, low bandwidth)

## Decision

`packages/design-system` provides three things:

1. **Core tokens:** spacing, radius, type scale, motion and semantic colour roles such as `surface`, `ink`, `accent`, `danger`, `emergency` and `focus`. They are exposed as CSS custom properties.
2. **Accessible primitives:** Button, Field, Stepper, Sheet, Toast, Banner, DataTable, StatTile, EmptyState and SessionLock. They have keyboard and screen-reader semantics, 44 px targets and visible focus.
3. **Four themes** that remap semantic roles only:

| Theme | Personality | Notes |
|---|---|---|
| `patient` | Warm, calm, reassuring | Large type, generous spacing, one primary action per screen, bottom tab bar (Home · Care · Messages · Profile) |
| `clinician` | Dense, fast, focused | Compact rhythm, three-pane layout, keyboard shortcuts, high-contrast state chips |
| `command` | Analytical | Dark-capable, data-viz palette safe for colour-blind users, tabular numerals |
| `sponsor` | Trust-led, institutional | Restrained palette, persistent "aggregate-only, no patient data" assurance |

The emergency colour and emergency banner are identical in every theme and cannot be overridden.

## Consequences

- Apps never hard-code hex values. Inline-style pages are replaced as each app is rebuilt.
