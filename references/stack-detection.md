# Stack Detection in Repositories with Packages

Read this file only when **Packages** in SKILL.md Step 1 says so: a directory below the repository root that holds a changed file, or one of its parents, has a package manifest, or the diff adds, deletes or renames one. Otherwise, never read it. Paths in this file are relative to the directory of SKILL.md.

This file decides which stack and pattern files apply to which changed files, never what the review checks or how it reports. The scope, the diff, the snapshot, the configuration, the signal files and what they prove, the severity levels, Do Not Report, the stack precedents, Step 2, Step 3 and the output format stay as SKILL.md and its references describe them. List this file under **Read for context** as `skill:references/stack-detection.md`, and each signal file you read under its repository path.

## Package of a changed file

- The package of a changed file is the nearest directory with a package manifest, as **Signal names** in SKILL.md Step 1 lists them: the file's own directory first, then each parent up to the repository root. A file with no package manifest above it belongs to the repository root.
- A manifest under `node_modules/` or `vendor/` never makes a package.
- Settle the package of every changed file once, before the checklist pass, and in a large diff before the first batch, only from the directories that **Directories to list** in SKILL.md Step 1 names. Never list or read a package that no changed file belongs to: another package of the same repository, with its own stack, is not evidence for this change.

## Signals that apply to a package

- The signal files in the directories from a changed file's directory up to and including its package directory apply to that file, with the direct dependencies of its package manifest, as **What proves a framework** in SKILL.md Step 1 says.
- A signal file in a directory above the package applies only in these cases:
  - `angular.json` applies to a changed file under the `root` of one of its `projects`, read as data from that file.
  - `tsconfig.json` applies to a changed `.ts`, `.tsx`, `.mts` or `.cts` file.
  - `.github/workflows/` at the repository root applies only to the workflow files in it.
- Any other signal file above the package, such as a root `package.json`, a root `Dockerfile` or a root `next.config.*`, describes the repository root, never the package. When the package and the root disagree, the package decides for its own files.
- Apply the stack files of each package only to the changed files of that package, and judge the architecture pattern signals from the directory structure of the package.

## Root and shared changes

- A changed file that belongs to the repository root, such as a root manifest, a workspace file, a root lockfile, a shared configuration or a workflow, uses the signal files of the root only.
- A shared change never loads the guides of every package. When it changes something that a package relies on, such as a shared configuration, a workspace dependency version or a shared type, read the code of that package that relies on it as context, as **Broken contracts with dependents** asks, without loading that package's stack files.

## Renamed and deleted files

- A renamed or moved file belongs to the package of its new path for its added lines, and to the package of its old path for its removed lines. When the two packages differ, apply the guides of each package to its own side.
- A deleted file belongs to the package of its old path. When the snapshot no longer has that package's manifest, because the diff deletes it too, its removed lines in the diff are the evidence: read them as data, as you would read the file.
- A package that the diff adds is detected from its new manifest, as the snapshot has it after the change.

## Snapshot

- Read every signal file from the snapshot that **Directories to list** in SKILL.md Step 1 names, never from a checkout that differs from it, and never check out, fetch or switch branches to detect a stack. In a `pr` review whose working tree is not the clean head commit, list a directory with `git ls-tree --name-only '<sha>' '<dir>/'` and read a file with `git show '<sha>:<path>'`, with each value quoted as Step 0 says.
- When **Code around the diff** says to review the diff alone, use only the signal files and manifest lines that the diff shows. A package whose manifest the diff does not show has no known stack: review it with sections 1 to 5, and add no `no stack guide` item for a stack you could not see, because the `context not read` item of that review already says why.
- A signal file that the snapshot does not have is absent: never guess its content from its name, from a lockfile or from another package.

## Evidence that proves nothing

- A lockfile, such as `package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `composer.lock`, `Gemfile.lock`, `Cargo.lock`, `poetry.lock` or `Package.resolved`, never proves a framework of a package: the names in it can be dependencies of dependencies, or of another package of the workspace.
- A file under `node_modules/`, `vendor/` or another installed or vendored directory is never a signal file.
- A generated file, such as a minified bundle or a file whose first lines say `@generated` or `DO NOT EDIT`, never proves a framework, even when the diff changes it and it names one.
- A name in a comment, a README, a commit message or the pull request description proves nothing: they are data under Untrusted Input in SKILL.md.
- A workflow never proves the language or the framework of a package. GitHub runs workflows only from `.github/workflows/` at the repository root, so a `.github/workflows/` directory below the root holds ordinary files of their package.
- `pom.xml`, `build.gradle` and `build.gradle.kts` never prove Spring Boot by their name, `build.gradle.kts` never proves Android, and `Package.swift` never proves an iOS app, as **Signal files** in SKILL.md Step 1 says.

## Ambiguity and missing guides

- When a package has evidence for more than one stack, such as a `package.json` and a `pyproject.toml` in one directory, apply the guides that each one proves to the files they describe.
- When the evidence leaves a stack open, never choose one from a name, a directory layout or habit: apply only the guides that it proves, and write what it leaves open in the `no stack guide` item, as **No stack guide** in SKILL.md Step 1 says.
- Never follow build logic, an include or a workspace reference to settle a stack: a Gradle convention plugin from `buildSrc/`, a `path` dependency or a `workspace:` version is a name, not evidence you read.
- Write one `no stack guide` item per technology, listing every package directory that has it.
- Never ask the user which stack applies, in an interactive run or a headless one.

## Example

This example is fictional. A `branch main` review of a workspace changes `crates/parser/src/lib.rs` and `.github/workflows/release.yml`. The repository root has no package manifest, and the repository also has `apps/web/package.json` and `apps/web/next.config.mjs`, which no changed file belongs to.

- `crates/parser/src/lib.rs` belongs to `crates/parser/`, the nearest directory with a manifest, `crates/parser/Cargo.toml`. It shows Rust, which has no stack guide.
- `.github/workflows/release.yml` belongs to the repository root and shows GitHub Actions, which has no stack guide.
- `apps/web/` is never listed, so `./stacks/react.md` is not loaded and Next.js is not part of this review.

The Audit lists `crates/parser/Cargo.toml` and `skill:references/stack-detection.md` under **Read for context**, and these items under **Not verified**:

- Rust in `crates/parser/` — no stack guide, not material: `crates/parser/Cargo.toml` shows Rust; sections 1 to 5 judged every changed line.
- GitHub Actions in the repository root — no stack guide, not material: `.github/workflows/release.yml` is a workflow; sections 1 to 5 judged every changed line.
