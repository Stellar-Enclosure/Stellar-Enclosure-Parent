# Stellar-Enclosure-Parent

Stellar Enclosure Java modules. All first-party modules start at **0.0.1**.

Migrated from [52e407ee3be8](https://github.com/AllenDEricDAlexander/Egon-COLA/tree/52e407ee3be892200aafadb19ad912189f5ada1c). Maven namespace: `top.egon`; npm organization: `@stellar-enclosure`.

## Build

Requires Java 21 and the included Maven Wrapper. Once the 0.0.1 dependencies are published:

```bash
./mvnw -B -ntp test-compile
```

Before the first Central publication, clone the eight Java repositories next to one another and bootstrap their artifact graph explicitly:

```bash
bash ../Stellar-Enclosure-Parent/scripts/bootstrap-migration.sh \
  --workspace "$(cd .. && pwd)" \
  --local-repository "$(cd .. && pwd)/.migration/maven"
```

The bootstrap installs parent/BOM models before building components and business starters in Maven reactor order. It compiles test sources and installs packages with runtime tests disabled. It never runs applications, databases, containers, browsers, or deploy.

## Repository boundaries and first publication

The root POM publishes `top.egon:stellar-enclosure-parent:0.0.1`. `platform-parent/pom.xml` publishes the shared platform parent. Neither aggregates sibling repositories during normal builds. Components owns its standalone BOM; COLA owns its archetype parent.

See [accepted migration design](docs/migration-spec.md), [release guide](docs/first-release.md), [repository manifest](migration/repositories.json), and [source ownership inventory](migration/source-inventory.json). Historical design and runbooks are archived under `docs/history` with the source commit as their reference context.

## Compatibility and publication

Java packages/classes, Bean names, configuration keys, OAuth/RPC identities, APIs, and database ownership are retained. Existing SQL and DDL history are copied byte for byte. Artifact/build versions and necessary build paths change. A successful build does not imply application startup or live infrastructure acceptance.

Git pushes run validation only. Central and npm publication are separate user actions. CI defaults to initial source bootstrap; after publication set `STELLAR_USE_SOURCE_BOOTSTRAP=false` to consume published artifacts directly. Private organizations may supply the Actions secret `STELLAR_ENCLOSURE_READ_TOKEN` with repository read access.

Original MIT/LGPL licenses and author attribution are preserved.
