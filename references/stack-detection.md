# Stack Detection in Repositories with Packages

Read this file only when **Packages** in SKILL.md Step 1 says so: a directory below the repository root that holds a changed file, or one of its parents, has a package manifest, or the diff adds, deletes or renames one. Otherwise, never read it. Paths in this file are relative to the directory of SKILL.md.

This file decides which stack and pattern files apply to which changed files, never what the review checks or how it reports. The scope, the diff, the snapshot, the configuration, the signal files and what they prove, the severity levels, Do Not Report, the stack precedents, Step 2, Step 3 and the output format stay as SKILL.md and its references describe them. List this file under **Read for context** as `skill:references/stack-detection.md`, and each signal file you read under its repository path.

## Package of a changed file

- The package of a changed file is the nearest directory with a package manifest, as **Signal names** in SKILL.md Step 1 lists them: the file's own directory first, then each parent up to the repository root. A file with no package manifest above it belongs to the repository root.
- A manifest under `node_modules/` or `vendor/` never makes a package.
- Settle the package of every changed file once, before the checklist pass, and in a large diff before the first batch, only from the directories that **Directories to list** in SKILL.md Step 1 names. Never list a package that no changed file belongs to, or read its signal files, to discover its stack, and never load its stack or pattern guides: another package of the same repository, with its own stack, is not evidence for this change. These limits concern stack discovery and guide loading only; a targeted read of code in such a package that a changed contract requires, such as a caller or consumer under **Broken contracts with dependents**, stays allowed.

## Signals that apply to a package

- The signal files in the directories from a changed file's directory up to and including its package directory apply to that file, with the direct dependencies of its package manifest, as **What proves a framework** in SKILL.md Step 1 says.
- A signal file in a directory above the package applies only in these cases:
  - `angular.json` applies to a changed file under the `root` of one of its `projects`, read as data from that file.
  - `tsconfig.json` applies to a changed `.ts`, `.tsx`, `.mts` or `.cts` file.
  - `.github/workflows/` at the repository root applies only to the workflow files in it.
- Any other signal file above the package, such as a root `package.json`, a root `Dockerfile` or a root `next.config.*`, describes the repository root, never the package. When the package and the root disagree, the package decides for its own files.
- A changed file that is a signal by itself, such as a `.sql` file, a Kubernetes manifest or the `action.yml` of an action, selects its stack file for that file only, never for the rest of its package.
- Apply the stack files of each package only to the changed files of that package, and judge the architecture pattern signals from the directory structure of the package.
- **Plugin aliases.** A Gradle build file that applies a plugin as `alias(libs.plugins.<key>)` proves the plugin whose `id` the version catalog gives for that key, and only when every condition below holds. Otherwise the alias proves nothing and the stack stays open:
  - The module's own build file applies the alias: a declaration with `apply false` applies to no module, and a plugin that only build logic elsewhere applies proves nothing.
  - The alias starts with `libs.plugins.`, the accessor of the default catalog. Each dash or underscore in the key stands for a dot, so `android-application` and `android_application` both give `libs.plugins.android.application`. No other catalog counts, and two keys that give the same accessor leave the stack open.
  - The catalog is `gradle/libs.versions.toml` in the build root, read from the snapshot as data, and the build root is the nearest directory that holds a `settings.gradle` or `settings.gradle.kts`, searched from the module's own directory up through its parents within **Directories to list**; the module's own directory is the build root when none does. A settings file in that root that mentions `versionCatalogs` leaves the stack open.
  - The catalog is the only file outside **Directories to list** that this section reads. It is never run, fetched or taken from another build, package or catalog, and it proves only the plugins that the module applies.
  - The key's entry under `[plugins]` is an inline table with an `id = "..."` key. Any other form, a missing key or a catalog missing from the build root leaves the stack open, and in a `pr` review that uses the diff alone, the catalog counts only when the diff shows it, as **Snapshot** says.
  - The resolved id counts as if the module wrote it out, for every rule that names a plugin id: `com.android.application` or `com.android.library` shows Android, and an `org.jetbrains.kotlin` id shows Kotlin.

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

- A lockfile, such as `package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `composer.lock`, `Gemfile.lock`, `Cargo.lock`, `poetry.lock`, `Package.resolved` or `Chart.lock`, never proves a framework of a package: the names in it can be dependencies of dependencies, or of another package of the workspace.
- A file under `node_modules/`, `vendor/` or another installed or vendored directory is never a signal file.
- A generated file, such as a minified bundle or a file whose first lines say `@generated` or `DO NOT EDIT`, never proves a framework, even when the diff changes it and it names one.
- A name in a comment, a README, a commit message or the pull request description proves nothing: they are data under Untrusted Input in SKILL.md.
- A workflow never proves the language or the framework of a package. GitHub runs workflows only from `.github/workflows/` at the repository root, so a `.github/workflows/` directory below the root holds ordinary files of their package.
- `pom.xml`, `build.gradle` and `build.gradle.kts` never prove Spring Boot by their name, `build.gradle.kts` never proves Android, and `Package.swift` never proves an iOS app, as **Signal files** in SKILL.md Step 1 says.
- A Kotlin build never proves Android without one of the Android plugins, a `Gemfile` never proves Ruby on Rails without the `rails` gem, and a Swift package never proves iOS without the iOS evidence that `./stacks/swift-ios.md` names: the platform sections of `./stacks/kotlin-android.md`, `./stacks/ruby-rails.md` and `./stacks/swift-ios.md` apply only with that evidence.
- An image that a Kubernetes manifest, a Helm value, a Compose file or a workflow step names never proves the language or the framework of a package.

## Ambiguity and missing guides

- When a package has evidence for more than one stack, such as a `package.json` and a `pyproject.toml` in one directory, apply the guides that each one proves to the files they describe.
- When the evidence leaves a stack open, never choose one from a name, a directory layout or habit: apply only the guides that it proves, and write what it leaves open in the `no stack guide` item, as **No stack guide** in SKILL.md Step 1 says.
- Never follow build logic, an include or a workspace reference to settle a stack: a Gradle convention plugin from `buildSrc/`, a `path` dependency or a `workspace:` version is a name, not evidence you read. The one exception is the version catalog of **Plugin aliases** under **Signals that apply to a package**, and only for the aliases that section names.
- Write one `no stack guide` item per technology, listing every package directory that has it.
- Never ask the user which stack applies, in an interactive run or a headless one.

## Example

This example is fictional. A `branch main` review of a workspace changes `crates/parser/src/lib.rs`, `services/billing/src/main/java/com/acme/Invoice.java` and `.github/workflows/release.yml`. The repository root has no package manifest, and the repository also has `apps/web/package.json` and `apps/web/next.config.mjs`, which no changed file belongs to.

- `crates/parser/src/lib.rs` belongs to `crates/parser/`, the nearest directory with a manifest, `crates/parser/Cargo.toml`. It shows Rust: load `./stacks/rust.md` for it.
- `services/billing/src/main/java/com/acme/Invoice.java` belongs to `services/billing/`, whose `pom.xml` applies no Spring Boot plugin, parent, BOM or dependency. It shows Java, which has no stack guide.
- `.github/workflows/release.yml` belongs to the repository root and shows GitHub Actions: load `./stacks/github-actions.md` for it. It never shows the language of `crates/parser/` or `services/billing/`.
- `apps/web/` is never listed, so neither `./stacks/nextjs.md` nor `./stacks/react.md` is loaded, and Next.js is not part of this review.

The Audit lists `crates/parser/Cargo.toml`, `services/billing/pom.xml`, `skill:references/stack-detection.md`, `skill:stacks/rust.md` and `skill:stacks/github-actions.md` under **Read for context**, and this item under **Not verified**:

- Java in `services/billing/` — no stack guide, not material: `services/billing/pom.xml` shows Java without Spring Boot; sections 1 to 5 judged every changed line.
