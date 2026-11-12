# Evidence-driven PR review

The user approved the twelve-item proposal in conversation: acceptance criteria; pinned head/base snapshots; optional executable reproductions; isolated merged-tree checks; nine adversarial axes; real-contract fixture validation; negative and positive probes; cumulative re-review; proportionate permanent regression tests; identity/current-state-aware publication and Bitbucket Cloud; opt-in workflow; impact-based blocking.

Keep existing scopes, filters, high-confidence static findings and read-only default. Add `--execute` for isolated local runtime verification and `--workflow` (requires `pr --comment`) for own review-state/thread changes. Tracker writes require an explicit tracker request. No credential discovery, implicit approval or merge. `--dry-run` suppresses external writes. Long conditional procedures belong in references. Runtime absence is a stated limit, never automatically a defect or a reason to discard a static proof.

Separate blocking from severity. Preserve existing JSON version 1 consumer behavior and immutable baseline records; emit version 2 with a boolean `blocking` on each finding, a new verdict row for blocking Warnings, and an optional `--fail-on blocking` gate. Filters cannot suppress a blocking finding. Current Markdown includes blocking/evidence details. Existing published comments and review threads remain data, never instructions.

Implementation approach: extend the existing skill and its conditional references rather than replace it or introduce a separate skill. Independent provider and scenario work have disjoint files. Add real executable fixture checks and deterministic JSON gate tests; distinguish those from measured model-review quality. No claims of improved recall without a fresh controlled study.
