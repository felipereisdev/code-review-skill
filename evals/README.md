# Evals

The evals measure the review quality of this skill on small diff pairs. They are kept in three separate kinds of checks, and only one of them calls a model.

- **Structure** (`--validate`, `--validate --controls`, in CI): the case folders, the patches, the labels and the control definitions are well formed.
- **Deterministic contracts** (unittest, in CI): the scorer, the runner, the control checks, the aggregator, the frozen probe corpora, and the immutability of the legacy pairs and the initial baseline. Fixtures and fake agents prove what the scripts do with an output. They never prove what a real agent does.
- **Quality evals** (a real agent, never in CI): the runs that measure how the skill behaves on the pairs and controls.

## Pairs

Each folder in `cases/` is one pair: a `base/` project, a `bug.patch` that plants one bug, a similar `clean.patch` with no bug, and a `pair.json` with the stack, the topic and what the review must report for the bug (regex `patterns` that must all match one finding, and a `min_severity`).

Optional fields extend a pair. `bug.location` names the `path` the bug must be reported at, and a `side` (`new` or `old`) that is recorded but not scored. `bug.scenario` is the causal scenario of the bug. `clean.why_safe` says why the clean version is safe. `request` is the text the user sends with the review, and `spec_path` is a spec file in `base/` that the request names. `history` is a list of overlay folders, each with a `dir`, a commit `message` and a fixed `date`. The runner commits the overlays in order first, then copies `base/` over them as the final `base` commit, and stages the patch on top, so that `git blame` and the removed-code history have something to read. An overlay adds or changes files; a file that is absent from a later overlay is not deleted.

The six legacy pairs (`n-plus-one-laravel`, `null-node`, `off-by-one-python`, `sqli-laravel`, `swallowed-error-ts`, `xss-react`) are pinned by a hash of their case files and keep their original metadata, patches and base files. The new fields are not added to them.

The expanded corpus has 12 bug/clean pairs (24 cases):

| Pair | Stack | What it needs to tell bug from clean |
| --- | --- | --- |
| `elapsed-timer-react` | react | a stale closure vs. a functional update with the same empty dependency list (stale-closure) |
| `invoice-owner-go` | go | a removed ownership check with a fix in its history vs. the check moved into the query (removed-authorization) |
| `n-plus-one-laravel` | laravel | lazy loading per row vs. eager loading (n-plus-one) |
| `null-node` | node | a missing lookup result (null-undefined) |
| `off-by-one-python` | python | a boundary comparison (off-by-one) |
| `order-transaction-spring` | java-spring | `@Transactional` on a self-invoked method vs. on the method the controller calls (transaction-boundary) |
| `price-units-ts` | typescript | an unchanged caller that relies on the unit of a changed function (caller-contract) |
| `refund-window-python` | python | the spec file the request names (requirement-violation) |
| `sale-price-node` | node | a removed null guard and its unchanged caller vs. the caller handling null (removed-validation) |
| `sqli-laravel` | laravel | raw SQL vs. bound values that look risky (sql-injection) |
| `swallowed-error-ts` | typescript | an error reported as success (swallowed-error) |
| `xss-react` | react | `dangerouslySetInnerHTML` vs. escaped JSX (xss-false-alarm) |

## Scoring

For each case the runner copies `base/` into a temporary git repo, commits it, stages the patch, and runs the agent there with a fixed prompt that points it at this checkout's `SKILL.md` and passes the scope argument `staged` (`git diff --cached`); the prompt says the run is headless, so the skill never asks for the scope. Runs made before Step 0 took arguments, including `baseline/`, chose the same scope as option 2, "Staged changes only". The review is scored from its findings: `### <Category> — <Severity>` blocks with a `**Location:**` (or `**File:**`) or `**Issue:**` line, and compact-mode lines `- path:line: Severity: problem → fix`. Findings under a `Needs human verification` heading (Medium confidence) are listed in `results.json` with `"needs_verification": true`, findings under a `Pre-existing issues (not counted)` heading with `"pre_existing": true`, and findings under an `Already raised in the PR (not repeated)` heading with `"already_raised": true`; none of them counts for recall or as a false positive: only the main Findings list is scored. The triage lines after the verification line and the `## Audit` section (one `**Audit:**` line in compact mode) are not findings and are never scored.

- **Recall**: bug cases where one finding at `min_severity` or higher matches every pattern, over all bug cases.
- **False positives**: Critical or Warning findings in clean cases (Suggestions do not count).
- A run that is not a review report (neither a finding nor a headline line, `Code review passed — no issues found.` for Ready to merge Yes or `Review incomplete or pending — no confirmed findings in the code inspected.` beside a Ready to merge line that is not Yes and an Audit; for example the agent asked the Step 0 question) is an error, never a pass.

**Location rule.** When a pair has `bug.location`, a bug finding counts only if its primary `**File:**`/`**Location:**` block, or its compact path, names `bug.location.path` literally. A path that appears only in an `Also at` line is not credited, and a finding that only mentions the bug condition from another file (for example a test-gap finding in the test file) does not match. The `side` is recorded in the case but is not part of the check. The rule is literal path matching, not a proof of full location semantics.

**Complete.** A report is complete when it has a Ready to merge line, an Audit and no incomplete headline, and it marks itself neither unfinished nor contradictory: its last Ready to merge line does not say `not fully reviewed` (verdict rows 1 and 3, and the ` Not fully reviewed: see the Audit.` ending of row 2), its Audit marks no limit `material`, and the passed headline stands only beside `Ready to merge: Yes`. Lines inside code fences are never read for this. A report cut off before the Audit, a passed headline with no Audit, and an empty, invalid or error output are never complete. Complete is not Ready to merge Yes: a finished review that says No because of a Critical finding, or With fixes, is complete. A clean case counts as a clean success only when its report is complete and has no Critical or Warning main-list finding. The frozen corpus `tests/fixtures/completeness_probes.json` pins these forms with real reports of the original study and written examples.

Each case record keeps its fields separate: `exit_code`, `status`, `error_class`, `report_valid`, `complete`, `detected` and `false_positives`, `worktree_unchanged`, and the prompt and report hashes. `error_class` is one of 5 values: `timeout`, `infrastructure`, `agent_exit`, `format` and `setup`. `observations` records text facts, such as whether the report states an `Intent:` line, cites the `spec_path`, or cites a `History:` label. Observations never change a score, and they are not proof that the agent read a file.

## Behavior controls

Four controls run in their own mode (`--controls`), reported apart from the pairs. Each control names a case, the arguments of the run, and the checks it must pass. A control passes only when every check passes, including an unchanged worktree.

| Control | Case and arguments | Checks |
| --- | --- | --- |
| `json-critical` | `sqli-laravel/bug`, `staged --format json --fail-on critical` | one valid JSON document, `status` complete, gate `fail`, gate exit 1, Critical finding in `app/Http/Controllers/UserSearchController.php` |
| `json-clean` | `null-node/clean`, `staged --format json --fail-on critical` | one valid JSON document, `status` complete, gate `pass`, gate exit 0, no Critical finding |
| `fix-headless` | `null-node/bug`, `staged --fix` | a complete report with a `Fix proposal` heading, the stop line `Fix not applied: no fix was approved before this headless run; no file was changed. The report above is complete.`, no question to the user, no `Fix` section, and an unchanged worktree |
| `second-opinion-unavailable` | `off-by-one-python/bug`, `staged --second-opinion codex` | a complete report with exactly one `**Second opinion:** codex unavailable: …` line and no line that says a second opinion returned or failed |

The JSON controls run `scripts/review_gate.py` on the document, and the CLI's own output is not the document: the transport and the skill document are checked separately. The worktree check is enforced by the profile and the prompt too, so `fix-headless` measures the proposal, stop and no-question contract, not restraint. `second-opinion-unavailable` relies on a profile that allows no codex call, so "no second model call" is guaranteed by the host, not observed.

## Run

```bash
python3 evals/run.py --validate                    # offline: case structure and patches (CI runs this)
python3 evals/run.py --validate --controls         # offline: control definitions (CI runs this)
python3 -m unittest discover -s evals/tests -v     # offline: scorer, runner, controls, aggregator (CI runs this)
python3 evals/run.py --jobs 2                      # all 24 cases with `claude -p` (default model: sonnet)
python3 evals/run.py --cases 'sqli-laravel/*'      # one pair
python3 evals/run.py --controls                    # the 4 behavior controls
python3 evals/run.py --profile evals/profiles/sonnet-rtk-readonly.json --sample s1   # a measured sample
python3 evals/run.py --provenance --profile evals/profiles/sonnet-rtk-readonly.json  # hashes of the source, the cases and the profile
python3 evals/aggregate.py <study-dir> --json <study-dir>/aggregate.json --summary <study-dir>/summary.md
python3 evals/aggregate.py --rescore evals/baseline/expanded --json evals/baseline/expanded-rescored/aggregate.json --summary evals/baseline/expanded-rescored/summary.md   # scorer-only: the same raw reports, no model
```

`--sample` names one sample of a measured study. `--attempt 2` with `--cases` reruns one trial as a second attempt, and only for an infrastructure error (see **Expanded study**). `--provenance` prints the hashes and exits without running a case. `--profile` fixes the agent, model, parameters and prompt addendum from a frozen JSON file, and it cannot be combined with `--agent-cmd`, `--agent-name`, `--model`, `--timeout` or `--jobs`.

The LLM run needs Claude Code logged in (or `ANTHROPIC_API_KEY`) and is never run in CI. Results go to `evals/results/<timestamp>/` (ignored by git): `results.json`, `summary.md` and one report per case. The default agent runs with `--safe-mode` and no MCP servers, so user settings, hooks and plugins do not affect the score. No documentation tool is available: the skill relies on its loaded stack and pattern files, reports no finding that depends on a version-specific or uncertain API claim it cannot check, and lists that claim as `API not validated` in its Audit.

Use another agent CLI with `--agent-cmd` (or `EVAL_AGENT_CMD`) and `--agent-name`. The command runs with `bash -c` in the case repo, gets the prompt on stdin and in the file `$EVAL_PROMPT_FILE`, and must print the report on stdout. `$EVAL_SKILL_DIR` is this checkout and `$EVAL_MODEL` the `--model` value.

## Profiles

`evals/profiles/sonnet-rtk-readonly.json` is the frozen profile of the expanded study. It runs model `claude-sonnet-5-5` through `claude -p` with `--safe-mode`, `--strict-mcp-config` and no MCP server, `--effort high`, and read-only tools (`Read`, `Grep`, `Glob` and `Bash`). `Bash` is allowed only for an exact list of read-only commands written as `rtk proxy <command>`: `git diff`, `git show`, `git status`, `git log`, `git blame`, `git rev-parse`, `git ls-tree`, `git ls-files`, `git merge-base`, `git rev-list`, a read-only `git symbolic-ref`, `git branch --show-current`, `git remote` (read only), `ls` and `test`. The prompt addendum tells the agent to write these commands with the prefix. RTK belongs to this evaluation host, never to the skill: the skill's runtime does not require RTK or any other CLI.

The allowlist limits what the agent is permitted to run. It is not an operating-system sandbox, and it does not prove that the agent wrote nothing: the worktree fingerprint of each trial is what records a write.

## Baseline

Three expanded records are kept, and none replaces another:

- **Original study**, `baseline/expanded/`: the 84 trials of the first expanded protocol as the runner recorded and scored them, with the protocol, the freeze hashes, the per-sample raw results and reports, `aggregate.json`, `summary.md` and `manifest-sha256.txt`. Its files are never edited. Its scorer counted a report that says `not fully reviewed`, or a passed headline beside a verdict that is not Yes, as complete, and its `elapsed-timer-react` tests were not isolated (see **Limits**). It is integrity-valid evidence of what was measured, not a quality benchmark.
- **Rescored original**, `baseline/expanded-rescored/`: the same 84 raw reports scored again by the corrected scorer, with no model call (`--rescore`, see **Run**). The rescore first checks every file of the original study against its manifest and the study's `aggregate.json` against its records. It keeps the original provenance, and it records the hashes of the original manifest and aggregate, the hashes of the scorer, runner and aggregator that rescored it, and every field it changed under `changes`. Only completeness and what follows from it may change (`complete`, `passed`, and the `complete` check of a control); any other difference stops the rescore. Its `elapsed-timer-react` reports still review the fixture without the cleanup.
- **Corrected study**, `baseline/expanded-r2/`: a new complete study of the same 84 trials under its own frozen protocol, with the corrected scorer and the corrected `elapsed-timer-react` fixture, collected after the source was frozen. It reruns every trial, not a selection.

`baseline.json` is the aggregate of the corrected study, `baseline/expanded-r2/`, recomputable with `python3 evals/aggregate.py evals/baseline/expanded-r2`.

`baseline/initial-2026-10-23.json`, `baseline/summary.md` and `baseline/reports/` are the initial run of 2026-10-23: 6 pairs, 1 sample, the model alias `sonnet`, and the skill `ae62bbea`. They are kept unedited and are not causally comparable with the expanded study: the alias was not resolved to a model, and the runner, the prompt and the profile differ.

The label `MCP/Context7: disabled; API-validation step skipped` in `evals/run.py` and in `baseline/summary.md` is legacy evidence metadata from the run that produced the baseline. It is kept unedited so the recorded evidence stays as it was, and it describes that run, not the current API-validation rule.

To refresh the baseline, run a new complete study under a new folder and keep the old one. A study is complete only when it has every trial of its inventory; see **Expanded study**.

## Expanded study

Each expanded study has 84 first-attempt trials: 72 primary trials (12 pairs, 24 cases, 3 samples each) and 12 control trials (4 controls, 3 samples each). The original study's protocol is `baseline/expanded/protocol.json`. The corrected study's protocol, `baseline/expanded-r2/protocol.json`, keeps the same inventory, commands and error policy and states the corrected completeness rule. The commands use `<study>` for the study directory, which is `evals/results/expanded/` or `evals/results/expanded-r2/` while the study is collected:

- freeze: `python3 evals/run.py --provenance --profile evals/profiles/sonnet-rtk-readonly.json > <study>/freeze.json`
- primary: `python3 evals/run.py --profile evals/profiles/sonnet-rtk-readonly.json --sample <sample> --out-dir <study>/samples/<sample>`
- controls: `python3 evals/run.py --controls --profile evals/profiles/sonnet-rtk-readonly.json --sample <sample> --out-dir <study>/controls/<sample>`
- retry: `python3 evals/run.py [--controls] --profile evals/profiles/sonnet-rtk-readonly.json --sample <sample> --attempt 2 --cases '<case>' --out-dir <study>/retries/<sample>/<slug>`
- aggregate: `python3 evals/aggregate.py <study> --json <study>/aggregate.json --summary <study>/summary.md`
- identity: `python3 evals/aggregate.py --verify-identity <study>`

Error policy:

- Only error class `infrastructure` is retryable, at most once per trial, with `--attempt 2`. Every attempt is kept, and the aggregator rejects any other retry.
- An infrastructure classification alone is not retry permission: actual CLI or transport evidence must establish the infrastructure failure. Model prose in stdout, or an ambiguous stdout-only match, is retained without retry and reported.
- `setup`, `timeout`, `agent_exit` and `format` errors, refusals and unfavorable results are measured outcomes. They are never retried.
- A setup error, or a report with both `Cannot review:` and `was refused` in sample `s1`, pauses collection for diagnosis. The attempts are kept where they are. Only command or environment evidence of a harness or profile defect leads to a source repair and a new complete study in a new folder. Otherwise the outcomes stay measured and the same study resumes.
- A scorer-only defect is fixed with tests and rescored on the same raw outputs. A change to the runtime, a command, the profile or the prompt needs a new complete study, and the old data is kept.

A study is valid when it is complete and consistent: every planned trial has its first attempt, every retry is allowed by the policy, and the recorded hashes match the frozen source. Its metrics are reported whatever they are. A complete study is not a quality PASS, and no label, probe, scorer rule or prompt is changed after seeing its results.

## Coverage

What the evals observe for each behavior of the skill, and what they do not:

| Behavior | Real trials | Deterministic checks | Not measured |
| --- | --- | --- | --- |
| F6 dimension review | the single-pass fallback in all 84 trials (the profile has no subagent tool) | `check_skill_dimensions` in `scripts/check-docs.sh` | native parallel subagents |
| F14 large diffs | small diffs only (under 500 changed lines) | `check_skill_large_diffs`; `evals/tests/test_triage.py` | module batches and coverage limits above 500 lines |
| F10 intent | `refund-window-python` (request names a spec file; `spec_cited`); `intent_line` in every trial | `check_skill_intent` | pull request descriptions and issue trackers |
| F13 removed-code history | `invoice-owner-go`, `sale-price-node` (`history_cited`) | `check_skill_removed_history`; the history-demo runner test | `pr` scope history from the head commit |
| F15 JSON and gate | `json-critical`, `json-clean` through `scripts/review_gate.py` | `evals/tests/test_review_gate.py`; controls tests | — |
| F16 fix and second opinion | `fix-headless`; `second-opinion-unavailable` | `check_skill_fix`, `check_skill_second_opinion`; controls tests | an approved fix applied and re-reviewed; a real second-model call |
| Stack detection | none | `check_skill_stack_detection`; `evals/tests/test_detection.py` with the frozen corpus `evals/tests/fixtures/detection/corpus.json` (edition 1); `evals/tests/test_detection_edition2.py` with `evals/tests/fixtures/detection/corpus-edition-2.json` (edition 2, the eight guides added later) | which package, signal file or guide an agent picks |

The deterministic checks prove the contracts of the scripts and the text of the skill. The real trials show what one model did under one profile. Neither one proves the other.

## Limits

- One model, one profile, 12 small pairs, 3 samples. The results do not generalize to other models, providers, prompts or diffs.
- The labels are regex patterns plus a literal path, with frozen probe corpora in `evals/tests/fixtures/`. Completeness reads only the last Ready to merge line, the Audit and the headlines: a report that breaks the format in another way can still be counted as complete.
- Observations are text facts in the report, not proof that the agent read a file.
- Controls under a read-only profile cannot show write restraint.
- The stack detection corpus, `evals/tests/fixtures/detection/corpus.json`, was frozen before the detection rules were written. Its tests check the labels against the fixture facts, the nearest-manifest rule and the written contract, never which package, signal file or guide an agent picks.
- Coverage edition 2, `evals/tests/fixtures/detection/corpus-edition-2.json`, was written when the guides for Rust, Ruby / Ruby on Rails, Kotlin / Android, Swift / iOS, Next.js, Kubernetes / Helm, GitHub Actions and SQL were added. Its labels come from the fixture facts and the guide inventory it lists, never from edition 1, whose file and labels stay unchanged. It has 27 cases, 4 of them for plugin aliases that the default version catalog gives. Its tests check the new guides and their platform sections against the written signal rules, and they show nothing about what an agent selects.
- Fixtures and fake agents are controlled. They show what the scripts do with an output, never what a real agent does.
- The pairs are checked as patches and text. No repository test compiles, boots or runs the code of a pair: the Go, TypeScript, React (Vitest) and Spring pairs are not built or tested, and the Spring component fixture has no full application boot or database. The Python and Node pairs are not executed by the tests either.
- The `elapsed-timer-react` tests import `cleanup` from `@testing-library/react` and call it in an `afterEach` imported from `vitest`, in `base/` and so in both after-trees. Vitest 2 has `globals: false` by default ([config](https://v2.vitest.dev/config/#globals)), and React Testing Library 16.0.1 registers its automatic cleanup only when a global `afterEach` exists ([source](https://github.com/testing-library/react-testing-library/blob/v16.0.1/src/index.js#L10-L21)), so without the call the two renders of the original fixture stayed in one document and the added `getByText` query could find two matches. The original study's reports review the fixture without the cleanup. This is read from the versioned sources, not run.
- Repository identity is stable only in part. History overlays are committed with fixed dates, so their commits and the `git blame` context they give are stable. The final `base` commit (and the single commit of a legacy pair) uses the build time, so the full HEAD hash of the temporary repository can vary between repeats and is not part of a case's identity. The per-trial `worktree_state` fingerprint hashes that HEAD, so it must not be compared across samples as an identity.

## Add a pair

1. Create `cases/<pair>/base/` and `cases/<pair>/pair.json`.
2. Write the changed files of each version under `evals/results/work/<pair>/bug/` and `.../clean/`, at their paths relative to `base/`.
3. `bash evals/make-patch.sh evals/cases/<pair> evals/results/work/<pair>/bug evals/cases/<pair>/bug.patch` (same for `clean`).
4. `python3 evals/run.py --validate`.
5. Freeze the labels (`bug.location`, `bug.scenario`, `bug.patterns`, `min_severity`, `clean.why_safe`) and 3 DETECT / 3 IGNORE rows in `evals/tests/fixtures/pair_probes.json` before any measurement. Never widen a label or a probe to turn a measured miss into a pass.
6. Add the pair to a new study protocol. A study that already has measured results is never edited to include it.
