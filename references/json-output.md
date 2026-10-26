# JSON Output

Read this file only when the arguments include `--format json`, as **Arguments** in SKILL.md Step 0 says. It changes how the result is delivered, never what the review checks, how it counts or what the verdict says: the JSON document is another form of the same report, built from the facts that **Reconcile before you deliver** in SKILL.md Step 3 settles. It never runs a second review and never publishes anything.

## Delivery

- Your whole reply is one JSON document: no code fence, no heading, no line before or after it, and never the Markdown report as well. The run is headless, as Step 0 says, so it never asks a question.
- Write valid JSON in UTF-8: keys and strings in double quotes, every `"` and `\` inside a string escaped, every line break inside a string written as `\n`, no comments, no trailing commas, no `NaN` or `Infinity`, and no key twice in one object.
- Text values keep the Markdown of the report as it is, backticks included. A **Fix:** that ends with a code block keeps its fence inside the string.
- When the run stops with a `Cannot review` or `Nothing to review` line, that line is the `message` of the document, as **Status** below says, and nothing else is written.
- Never write a partial document, and never write a complete one with fewer findings than the review has. A run that ends any other way, for example because your agent stops or its reply is cut off, has produced no document. An empty, cut-off or wrapped reply is not a document, and a consumer must never read it as zero findings.

## Document

Every document has these seven keys, in this order:

| Key | Value |
| --- | --- |
| `schema` | always `"code-review-skill/review"` |
| `version` | always `1`, the version of this contract |
| `status` | `"complete"`, `"nothing_to_review"` or `"error"` (see **Status**) |
| `message` | the `Nothing to review` or `Cannot review` line as written, or `null` for a complete review |
| `scope` | the text after `**Scope:** ` of the Scope line, such as `"staged (git diff --cached)"`, or `null` when the run stopped before the scope and its command were known |
| `gate` | the gate object (see **Gate**) |
| `review` | the review object for a complete review (see **Review**), otherwise `null` |

**Status.**

- `"complete"`: the review finished and the report is settled.
- `"nothing_to_review"`: the run stopped with a `Nothing to review` line, such as `Nothing to review: git diff --cached shows no changes.` or `Nothing to review: every changed file matches ignore_paths.`
- `"error"`: the run stopped with a `Cannot review` line, the argument checks of Step 0 included.

## Review

The review object has these keys, in this order:

| Key | Value |
| --- | --- |
| `context_lines` | the lines that SKILL.md puts right after the Scope line, each as written: the line that says code outside the diff was not read, the `**Configuration:**` line and the `**Excluded by configuration:**` line; `[]` when there is none |
| `intent` | the lines of the `## Intent` section, each as written, without its heading |
| `findings` | one finding object for each finding under `## Findings`, in report order, the findings omitted by the configuration included |
| `needs_verification` | one finding object for each finding under `## Needs human verification`, in report order, the omitted ones included |
| `pre_existing` | each line under `## Pre-existing issues (not counted)` without its leading `- `; `[]` when there is none |
| `already_raised` | each line under `## Already raised in the PR (not repeated)` without its leading `- `; `[]` when there is none |
| `verification` | `{"checked": <checked>, "refuted": <refuted>}`, the counts of the verification line |
| `omitted_by_configuration` | the text after `**Omitted by configuration:** ` of that line, or `null` when the report has none |
| `triage` | an object with `review_effort`, `relevant_tests`, `look_first` and `ready_to_merge`: the text after the label of each triage line |
| `verdict` | `{"ready_to_merge": <value>, "row": <row>}`: the row of the verdict table of SKILL.md Step 3 that gives the **Ready to merge:** line, and its value, `"Yes"`, `"No"` or `"With fixes"` |
| `audit` | the audit object (see **Audit**) |

The document leaves out What Was Done Well and the Summary table: the findings carry every count that the table shows, which counts the findings whose `omitted_by` is `null`.

**Finding object.** Each finding has these keys, in this order:

| Key | Value |
| --- | --- |
| `category` | the category of its heading, a row of the Summary table |
| `severity` | `"Critical"`, `"Warning"` or `"Suggestion"` |
| `confidence` | `"High"` under `findings`, `"Medium"` under `needs_verification` |
| `location` | the **Location:** as written, without backticks: `path:line` or `path:start-end` |
| `path` | the path of the Location |
| `side` | `"new"` for lines that the change adds or modifies, `"old"` for removed lines under the deletion-only exception |
| `start_line` | the first line of the Location |
| `end_line` | the last line of the Location; the same as `start_line` for one line |
| `rule` | the citation of its **Rule:** line without backticks, such as `"src/AGENTS.md:L4-L5"`, or `null` |
| `also_at` | the places of its **Also at:** line, each as `path:line` or `path:start-end` without backticks, or `[]` |
| `issue`, `evidence`, `fix` | the text of its **Issue:**, **Evidence:** and **Fix:** lines |
| `omitted_by` | `null` when the report shows the finding; otherwise the filter of `./references/configuration.md` that omitted it: `"min_severity"`, `"disabled_categories"` or `"max_findings_per_file"` |

- A grouped finding is one object: its other places are in `also_at`, never in objects of their own, and no place is listed twice.
- A Critical finding always has `omitted_by` `null`: no filter omits it, as `./references/configuration.md` says.
- A finding that a filter omits keeps every other key as Step 2 left it. The filters decide only what the Markdown report would show; the document keeps every fact that the verdict and the gate count.

**Audit.** The audit object has these keys, in this order:

| Key | Value |
| --- | --- |
| `files_reviewed` | `{"reviewed": <n>, "changed": <m>, "paths": [...]}`, from the **Files reviewed** line |
| `read_for_context` | the identities of the **Read for context** line, in its order, or `[]` |
| `checked_with_no_findings` | the categories of that line, in its order, or `[]` |
| `already_raised_not_verified` | `null` outside a `pr` review; in a `pr` review, one `{"location": "<path>:<line>", "category": "<category>"}` for each entry of that line, or `[]` |
| `not_verified` | one `{"what": ..., "tag": ..., "material": true or false, "detail": ...}` for each item of **Not verified**, or `[]` |

This file is listed on **Read for context** as `skill:references/json-output.md`, like any other file of this skill that you read.

**File accounting.** The document keeps the facts that the Audit of SKILL.md Step 3 uses to account for every changed file: `changed` is `<m>`; the reviewed files are the `paths` of `files_reviewed`; the files excluded by configuration are counted and listed on the `**Excluded by configuration:**` line of `context_lines`; a binary file is a `binary` item whose `what` is `` `<path>` ``; and a file not read at all is a `not read` item whose `what` is `` `<path>` (whole file) ``. The reviewed, excluded, binary and whole-file unread files add up to `changed`, and no file is counted twice. A file read only in part stays a reviewed file, and its unread lines are one `not read` item whose `what` is `` `<path>` lines <a>-<b> ``. A changed file is never in `read_for_context`.

## Gate

The gate object has three keys:

- `fail_on`: `"critical"` when the arguments include `--fail-on critical`, otherwise `null`.
- `status`: the first of these that applies:
  1. `"error"` when the document's status is `"error"`.
  2. `"not_requested"` when `fail_on` is `null`.
  3. `"pass"` when the document's status is `"nothing_to_review"`.
  4. `"fail"` when the verdict row is 2: a Critical finding is under `## Findings`.
  5. `"incomplete"` when the verdict row is 1 or 3: no changed file was reviewed, or the Audit lists a `material` limit.
  6. `"pass"` otherwise.
- `reason`: for `"error"`, the `message`; for `"not_requested"`, `no gate was requested`; for `"pass"` on a document with nothing to review, `nothing to review`; for `"fail"`, `1 verified Critical finding` or `<c> verified Critical findings`; for `"incomplete"`, the text after `No — ` of the **Ready to merge:** line; for any other `"pass"`, `complete review with no verified Critical finding`.

The gate counts only the findings under `## Findings`, before the filters: they have High confidence and went through Step 2. A Critical finding under `## Needs human verification` is not verified: it never fails the gate, and verdict row 5 already asks a person to check it. When what a person must check depends on code that you could not inspect, SKILL.md also lists a `context not read` limit, and a `material` one makes the gate `"incomplete"`. A review that is not complete never passes the gate, and a run that stopped with `Cannot review` is an error, never a pass.

The gate is text in the document, like the verdict. It never changes the exit status of your agent, and it never approves, blocks or changes the status of a pull request. Only a program that reads the document, such as the optional `scripts/review_gate.py` of this skill's repository, can turn it into an exit status. Such a program can check the structure of the document and the facts it states, such as the gate, the verdict row and the file accounting; it cannot check that the review read what the document says, or that its evidence and judgments are right.

## Examples

These examples are fictional. A `branch` review whose configuration sets `min_severity: Critical` and disables `Security`, with `--format json --fail-on critical`. The Critical finding stays, because no filter omits a Critical finding, and the Warning finding is omitted but still in the document:

```json
{
  "schema": "code-review-skill/review",
  "version": 1,
  "status": "complete",
  "message": null,
  "scope": "branch origin/main (git diff origin/main...HEAD)",
  "gate": {"fail_on": "critical", "status": "fail", "reason": "1 verified Critical finding"},
  "review": {
    "context_lines": ["**Configuration:** `.code-review/config.yml`."],
    "intent": [
      "**Intent:** inferred: filter the order report by customer (diff).",
      "**Requirements:** none stated.",
      "**Scope creep:** not judged: no source states a requirement.",
      "**Sources not read:** none."
    ],
    "findings": [
      {
        "category": "Security",
        "severity": "Critical",
        "confidence": "High",
        "location": "src/orders.js:42-44",
        "path": "src/orders.js",
        "side": "new",
        "start_line": 42,
        "end_line": 44,
        "rule": null,
        "also_at": [],
        "issue": "`findOrders` concatenates the customer filter into the SQL query.",
        "evidence": "`/report?customer=1 OR 1=1` reaches `findOrders(\"1 OR 1=1\")` through `src/report.js:9` → the query `WHERE customer_id = 1 OR 1=1` returns the orders of every customer. Verification checked `src/routes.js`; nothing validates `customer`.",
        "fix": "Bind the value: `db.query(\"SELECT * FROM orders WHERE customer_id = $1\", [customerId])`.",
        "omitted_by": null
      },
      {
        "category": "Potential Bugs",
        "severity": "Warning",
        "confidence": "High",
        "location": "src/report.js:17",
        "path": "src/report.js",
        "side": "new",
        "start_line": 17,
        "end_line": 17,
        "rule": null,
        "also_at": [],
        "issue": "The page loop stops one page early.",
        "evidence": "A report with 3 pages runs `for (let p = 1; p < pages; p++)` → page 3 is never read and its orders are missing from the report.",
        "fix": "Loop while `p <= pages`.",
        "omitted_by": "min_severity"
      }
    ],
    "needs_verification": [],
    "pre_existing": [],
    "already_raised": [],
    "verification": {"checked": 3, "refuted": 1},
    "omitted_by_configuration": "min_severity Critical: 1 omitted; disabled categories Security: 0 omitted.",
    "triage": {
      "review_effort": "1/5 — up to 50 changed lines in 2 files; no risk area.",
      "relevant_tests": "existing — `tests/orders.test.js` runs `findOrders` with a numeric id; no test passes a customer filter from the report. Execution: not run.",
      "look_first": "`src/orders.js` (Critical SQL injection in the customer filter), `src/report.js` (Warning: the last page is skipped).",
      "ready_to_merge": "No — 1 Critical finding must be fixed before merging."
    },
    "verdict": {"ready_to_merge": "No", "row": 2},
    "audit": {
      "files_reviewed": {"reviewed": 2, "changed": 2, "paths": ["src/orders.js", "src/report.js"]},
      "read_for_context": [".code-review/config.yml", "skill:references/configuration.md", "skill:references/intent.md", "skill:references/json-output.md", "src/routes.js", "tests/orders.test.js"],
      "checked_with_no_findings": ["Performance", "Tests/Coverage", "Architecture", "Code & File Size"],
      "already_raised_not_verified": null,
      "not_verified": []
    }
  }
}
```

A run with `--format json --fail-on critical --comment` stops before it reviews anything:

```json
{
  "schema": "code-review-skill/review",
  "version": 1,
  "status": "error",
  "message": "Cannot review: --comment cannot be combined with --format json; publish from a Markdown review. Nothing was reviewed.",
  "scope": null,
  "gate": {"fail_on": "critical", "status": "error", "reason": "Cannot review: --comment cannot be combined with --format json; publish from a Markdown review. Nothing was reviewed."},
  "review": null
}
```

A `staged` review with `--format json --fail-on critical` and nothing staged:

```json
{
  "schema": "code-review-skill/review",
  "version": 1,
  "status": "nothing_to_review",
  "message": "Nothing to review: git diff --cached shows no changes.",
  "scope": "staged (git diff --cached)",
  "gate": {"fail_on": "critical", "status": "pass", "reason": "nothing to review"},
  "review": null
}
```
