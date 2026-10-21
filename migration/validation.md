# Migration validation

The 15 repositories were migrated from source commit 52e407ee3be892200aafadb19ad912189f5ada1c. Initial self-owned versions are 0.0.1; Maven namespace is top.egon and npm organization is @stellar-enclosure.

- 9,542 original tracked files are accounted for in the source ownership inventory, including explicit archive/replacement/exclusion decisions.
- 121 original SQL files and 10 DDL manifests remain byte-identical.
- The 128-project Java/source-archetype build completed using an isolated first-party artifact cache. No old top.egon artifacts were used as fallback.
- 237 focused Java tests passed; 17 existing environment-dependent tests were skipped.
- All six frontend applications built and passed 495 tests. Both SDK workspaces passed 47 tests; the Jianshen resource report passed 4 tests and its browser-bundle guard passed.
- Three skill validator suites passed 114 tests, and all available skill-resource integrity validators passed.
- Seven real archetype families generated, packaged and installed; a second complete generation matched deterministically. Seven generated consumer projects, intentionally versioned 1.0.0-SNAPSHOT, test-compiled against the fixed 0.0.1 library release.
- Release verification checked 80 publishable artifacts: 15 POMs and 65 main/source/Javadoc JAR sets. GPG signing and all actual publication were disabled.
- All 15 validation workflow YAML files parsed successfully. Push workflows do not publish packages.

Necessary migration corrections include project/consumer version separation in the archetype generator, module-local generator test fixtures, new launcher paths, a standalone knowledge application, scoped document-action test queries, repository-specific URL/SCM inheritance, release-only delombok/Javadoc inputs, and explicit exclusion of the empty internal Yuheng test-suite from public deployment.

The old source repository is retained. Java package/class identities, protocol/permission/configuration keys and persistence ownership are preserved. No services, databases, Redis, MQ, containers or browser were started for acceptance. Runtime verification and actual Central/npm publication remain user initiated.

Per-repository commits and the verified remote refs are recorded in the workspace .migration/github-push-results.json receipt after the initial pushes; this report does not claim remote CI or registry publication from local build evidence. See validation.json for machine-readable evidence and docs/first-release.md for operator steps.
