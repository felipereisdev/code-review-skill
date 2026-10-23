# Evals

Measures the review quality of this skill on small diff pairs. Each folder in `cases/` is one pair: a `base/` project, a `bug.patch` that plants one bug, a similar `clean.patch` with no bug, and a `pair.json` with the stack, the topic and what the review must report for the bug (regex `patterns` that must all match one finding, and a `min_severity`).

For each case the runner copies `base/` into a temporary git repo, commits it, stages the patch, and runs the agent there with a fixed prompt that points it at this checkout's `SKILL.md` and fixes the scope to "Staged changes only". The review is scored from its findings (`### <Category> — <Severity>` blocks with a `**File:**`/`**Issue:**` line).

- **Recall**: bug cases where one finding at `min_severity` or higher matches every pattern, over all bug cases.
- **False positives**: Critical or Warning findings in clean cases (Suggestions do not count).
- A run that is not a review report (neither a finding nor the line `Code review passed — no issues found.`; for example the agent asked the Step 0 question) is an error, never a pass.

## Run

```bash
python3 evals/run.py --validate                    # offline: case structure and patches (CI runs this)
python3 -m unittest discover -s evals/tests -v     # offline: scorer and runner tests (CI runs this)
python3 evals/run.py --jobs 2                      # all 12 cases with `claude -p` (default model: sonnet)
python3 evals/run.py --cases 'sqli-laravel/*'      # one pair
```

The LLM run needs Claude Code logged in (or `ANTHROPIC_API_KEY`) and is never run in CI. Results go to `evals/results/<timestamp>/` (ignored by git): `results.json`, `summary.md` and one report per case. The default agent runs with `--safe-mode` and no MCP servers, so user settings, hooks and plugins do not affect the score and the skill's Context7 API-validation step is skipped.

Use another agent CLI with `--agent-cmd` (or `EVAL_AGENT_CMD`) and `--agent-name`. The command runs with `bash -c` in the case repo, gets the prompt on stdin and in the file `$EVAL_PROMPT_FILE`, and must print the report on stdout. `$EVAL_SKILL_DIR` is this checkout and `$EVAL_MODEL` the `--model` value.

## Baseline

`baseline.json` and `baseline/` hold the run of the skill as it was before any review-behavior change. After changing `SKILL.md`, `stacks/` or `patterns/`, run the suite and compare recall and false positives with `baseline.json`. Refresh the baseline only on purpose:

```bash
python3 evals/run.py --jobs 2 --out-dir evals/baseline --json evals/baseline.json
```

## Add a pair

1. Create `cases/<pair>/base/` and `cases/<pair>/pair.json`.
2. Write the changed files of each version under `evals/results/work/<pair>/bug/` and `.../clean/`, at their paths relative to `base/`.
3. `bash evals/make-patch.sh evals/cases/<pair> evals/results/work/<pair>/bug evals/cases/<pair>/bug.patch` (same for `clean`).
4. `python3 evals/run.py --validate`.
