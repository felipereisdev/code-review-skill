# Review Workflow

Read only for `pr ... --comment --workflow`, after the review and publishing preparation are complete. `--workflow` requires both explicit `pr` scope and `--comment`; reject other combinations before reviewing. It extends comment publication with the review-state and own-thread operations below. Without it, comments do not change review state or resolve threads. Approval and merge require separate explicit user instructions and are outside this flag's operations.

## Preconditions and order

1. Record the authenticated account's stable ID and name. Verify repository identity and the current PR state, source SHA and destination SHA. A changed pair means the report describes an older snapshot: keep it as such and perform no workflow writes until the affected code and original reproductions have been reviewed against the current pair. A closed or merged PR receives no workflow writes.
2. Finish and deliver the report, including its confirmed blocking findings, pending verification and material limits. Publish its inline comments and summary as `references/publishing.md` or `references/bitbucket.md` says. An incomplete publication stops this workflow too.
3. Verify each earlier own finding against the current pair, preserving the original trigger, expected corrected result and valid control. Re-run the original reproduction when `--execute` authorized execution; otherwise trace the current code and state explicitly that execution was not performed. A reply saying “fixed”, a passing unrelated test, a moved line or an already-resolved flag is not verification. A runtime-dependent fix that cannot be established by reading stays pending.
4. Resolve only eligible own threads, then update this account's review state, then update a tracker only when the user explicitly requested tracker changes. Re-read identity, pair, PR state and the affected resource immediately before each operation. Re-read the result immediately afterward. Report a concurrent change and stop further writes.

Keep a re-review table: original finding/thread, reproduction or code trace, tested SHA pair, result (`fixed`, `persists`, `regressed`, `not verified`), and thread action. Include reproductions from every previous round, not only the latest. A successful refusal probe needs its accepted-case control too. Recommend a versioned regression test where the risk warrants one; do not edit the repository during a review without `--fix` and its separate authorization.

An eligible thread has an own root finding and no other user's unresolved actionable finding that resolving the thread would hide. Identify ownership by account ID, not display name or text markers. When a provider can resolve only the whole thread, leave it open if it also carries another user's unresolved work. When it can resolve an individual own note, resolve that note alone and leave the others unchanged. Resolve only after verifying the original issue is fixed; never resolve merely to make the board look green.

## Review-state decision

- **Confirmed blocker remains:** request changes, identifying the blocking findings and the published review URL. Critical findings block; a Warning blocks only when the report's `Blocking` decision demonstrates broken required behavior, a public contract or an integration regression. Suggestions and Medium-confidence candidates never become confirmed blockers by this flag.
- **Only a material limit or unverified candidate remains:** preserve the existing review state and state what still needs verification. Missing access is not proof that the author must change code.
- **Every earlier blocker is verified fixed, no pending blocker or material verification gap remains, and the current pair was fully reviewed:** withdraw only this account's own request for changes, without approving. A nonblocking note can stay open; identify it as nonblocking.
- **Withdrawal with no relevant own request, or desired state already current:** no state write. This no-op applies to withdrawing an absent request, not to creating an initial request-changes review when confirmed blockers remain. Never alter another reviewer's request or approval.

Use idempotency by reading the current state first. Do not post a fresh request-changes review on every run when the same account already requests the same changes on the reviewed snapshot. When the platform cannot express the desired operation, report that limitation and keep the evidence in the summary. A comment saying “changes requested” is never described as a platform state transition.

## Provider operations

Prefer a connected tool when it exposes the required operation and resource identity. Otherwise use the already authenticated provider client with structured or temporary-file JSON payloads. No new login, token discovery, package installation, permission change, or branch-protection change is part of this workflow. On failure, stop all further writes and list the partial result; do not improvise another endpoint or retry a write whose result is uncertain.

**GitHub.** Obtain the account with `gh api --hostname <host> user`; list all reviews with `gh api --hostname <host> --paginate repos/<owner>/<repo>/pulls/<n>/reviews`. The existing PR/thread reads provide current ownership, head/base and thread IDs.

- Request changes with `POST repos/<owner>/<repo>/pulls/<n>/reviews`, body `{"commit_id":"<reviewed head SHA>","event":"REQUEST_CHANGES","body":"<blocking findings and review URL>"}`. This is separate from the publishing guide's comment-only review.
- Withdraw an eligible own request with `PUT repos/<owner>/<repo>/pulls/<n>/reviews/<own-review-id>/dismissals`, body `{"message":"<verified fixes and review URL>","event":"DISMISS"}`. Dismiss only this account's active request-changes review; never a review carrying another account's ID. Protected-branch dismissal may require permissions the account lacks; report that outcome without seeking more permission or changing protection.
- Resolve an eligible own thread using the GraphQL mutation `resolveReviewThread(input:{threadId:<id>}) { thread { id isResolved } }`. Pass the ID as a GraphQL variable; use no PR text as query source. Verify the returned ID and `isResolved`, then re-read the thread. Do not dismiss a review merely because its threads were resolved: the state decision above is separate.

**GitLab.** Read identity with `glab api --hostname <host> user` and re-read the MR and discussions as Pull Request Scope describes. For an individual own resolvable note use `PUT projects/<project_id>/merge_requests/<iid>/discussions/<discussion_id>/notes/<own-note-id>` with `{"resolved":true}`; the body contains no `body` field. For an entirely eligible own thread use `PUT projects/<project_id>/merge_requests/<iid>/discussions/<discussion_id>` with `{"resolved":true}`. Re-read that discussion to verify the result. A formal request-changes/withdraw operation depends on the installed instance and available connector; use it only when its supported capability and exact semantics are established. Otherwise report `Review-state update unavailable: this GitLab connection exposes no supported request-changes/withdraw operation.` Do not substitute unapproval, a label, a blocking discussion or a status change.

**Bitbucket Cloud.** Use the account, pair checks, request-changes, withdrawal and resolution operations in `references/bitbucket.md`; each operation is scoped to that account and PR. The comment-resolution operation uses an empty body with no `Content-Type` header.

## Optional tracker update

`--workflow` alone does not authorize tracker writes. When the user explicitly requested them and a tracker is connected, identify the linked card, re-read its status, list the legal transitions, and map the board's actual change-requested status before acting. When confirmed blockers remain, move the card only through a legal, semantically correct transition and add a short comment linking this review. Deduplicate an existing own link comment. If reaching the target would require claiming implementation has begun, completion, validation or merge, leave the card in its truthful current state and report the missing transition. Never select an unrelated intermediate state to manufacture a route.

When fixes are verified, do not move a card to a status meaning “validated after merge” before a merge. State available transitions and leave that move to its actual event. Re-read PR and tracker state immediately before the final summary, including when no transition was possible. Report whose account made each change and link the review/card; never describe a ten-minute-old status as current.

## Dry run and outcome

With `--dry-run`, perform the identity, ownership, pagination and state reads and all applicable review checks, but make no external write: no comment, thread resolution, review-state update or tracker transition. After the report and publishing dry run, list the workflow operations in their intended order, each with provider, method/tool, resource ID, redacted payload or “empty body”, expected result and any unavailable prerequisite. State `Workflow dry run: nothing was changed.` Never print secrets or authentication headers.

On a real run, report the own threads resolved, review-state result, tracker result if requested, and any failed/skipped operation. A failed write does not invalidate the completed review; it does mean the workflow was only partially completed. Verify rather than assume: a timeout after a write is an unknown result until read back, not permission to duplicate it.

## API references

GitHub review creation/dismissal uses its [review REST API](https://docs.github.com/en/rest/pulls/reviews), and thread resolution uses [resolveReviewThread](https://docs.github.com/en/graphql/reference/mutations#resolvereviewthread). GitLab note/thread resolution uses its [discussions API](https://docs.gitlab.com/api/discussions/). Bitbucket operations are linked in `references/bitbucket.md`. This guide intentionally does not equate platform permissions with permission to modify other people's review records.
