# Evidence-driven Review Implementation Plan

> Implement inline in this session; independent provider/scenario work and a final review supplement implementation.

**Goal:** Incorporate the approved evidence-driven review improvements into the generic code-review skill.
**Architecture:** Extend routing in SKILL.md, add conditional evidence/execution/provider/workflow references, and evolve the JSON gate compatibly.
**Tech Stack:** Markdown, Python standard library, existing unittest and shell checks.
**Spec:** docs/superpowers/specs/2026-11-12-evidence-driven-review-design.md

## Global Constraints

Read-only by default; execution/workflow opt-in. No approval/merge or credential discovery. Preserve frozen studies and version-1 JSON. No textual check presented as behavioral proof. Do not push or publish this change without a concrete reviewed result.

## Review Focus

- Blocking Warning hidden by configuration must still block.
- New commits during review must not receive stale review-state writes.
- Runtime unavailable must retain statically proven findings.
- Mocks that match reality must not become automatic findings.
- Re-review must exercise valid controls and prior regressions, not just reject more inputs.

## Tasks

1. [x] Record baseline checks and independent pressure-scenario observations; add failing JSON v2 tests (blockers, omissions, Medium confidence, malformed flags, v1 compatibility).
2. [x] Implement compatible JSON gate v2; document same facts in JSON and Markdown, filters and publishing.
3. [x] Add execution/evidence references and route them; reinforce intent and cumulative re-review. Add Bitbucket/workflow references and route them through all scope/publishing paths.
4. [x] Add executable scenarios without changing frozen baselines; update docs/version/project structure and structural checks.
5. [x] Run unittest suite, eval validation, docs positive/negative checks, skill validator; final independent whole-change review and fix material findings. Record results and leave local branch reviewable.

## Validation result

- 509 Python tests passed; 12 eval pairs / 24 cases and four controls validate; skill/frontmatter/reference checks passed.
- Documentation mutation/control checks ran in isolated snapshots with the existing mutations and assertions, queued through a temporary parallel harness. The completed run satisfied 625 of 626; the remaining old mutation depended on JSON comma whitespace removed by reformatting. Its mutation was corrected and the affected case retested successfully. An earlier old flag-text mutation was also corrected and passed in that completed run. All 626 expectations are covered; the serial shell command was not rerun end-to-end after those test-fixture corrections.
- Independent whole-change review exposed gate precedence; three regression tests failed before the corrections and now pass. Review also checked three scenarios qualitatively, without a repeated efficacy study.
- Live provider writes and tracker transitions were not exercised. Measured reports, trial records and scores remain unchanged; the subsequent user-requested privacy cleanup redacts environment metadata and refreshes dependent manifest identities.
