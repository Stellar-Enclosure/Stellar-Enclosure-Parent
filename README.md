# Stellar-Enclosure-Parent

Stellar Enclosure Java modules. All first-party modules start at **0.0.1**.

## Build

Requires Java 21 and the included Maven Wrapper. Once the 0.0.1 dependencies are published:

```bash
./mvnw -B -ntp test-compile
```

Before the first Central publication, clone the eight Java repositories next to one another and bootstrap their artifact graph explicitly:

```bash
bash ../Stellar-Enclosure-Parent/scripts/bootstrap-workspace.sh \
  --workspace "$(cd .. && pwd)" \
  --local-repository "$HOME/.m2/repository"

# Resolve subsequent Maven commands and generator subprocesses from this same cache.
export MAVEN_ARGS="${MAVEN_ARGS:-} -Dmaven.repo.local=$HOME/.m2/repository"
```

The bootstrap installs parent/BOM models before building components and business starters in Maven reactor order. It compiles test sources and installs packages with runtime tests disabled. It never runs applications, databases, containers, browsers, or deploy.

Build dependencies use the standard Maven cache. Temporary Maven reactors use the system temporary directory and are removed after both successful and failed builds.

## Repository boundaries and first publication

The root POM publishes `top.egon:stellar-enclosure-parent:0.0.1`. `platform-parent/pom.xml` publishes the shared platform parent. Neither aggregates sibling repositories during normal builds. Components owns its standalone BOM; COLA owns its archetype parent.

See the [release guide](docs/first-release.md) and [Maven release order](release/maven-release-order.json). Historical architecture designs and runbooks are archived under `docs/history`.

## Publish to Maven Central

This repository publishes two independent POMs. Run from this directory with Java 21, a Central Portal token configured as Maven server `central`, and a local GPG signing key. See [credentials and initial release order](https://github.com/Stellar-Enclosure/Stellar-Enclosure-Parent/blob/main/docs/first-release.md).

```bash
# Common parent: local release check, then publication.
./mvnw -B -ntp -N -Prelease -Dgpg.skip=true clean verify
./mvnw -B -ntp -N -Prelease clean deploy

# Platform parent: the Components BOM at the referenced version must already be published.
./mvnw -B -ntp -N -f platform-parent/pom.xml -Prelease -Dgpg.skip=true clean verify
./mvnw -B -ntp -N -f platform-parent/pom.xml -Prelease clean deploy
```

The root does not aggregate `platform-parent` or any sibling repository. Initial order is common parent → Components BOM → platform parent → library parents and modules in dependency order. Each GAV may be published once; choose new versions for changed content. The old workspace-wide `scripts/maven-deploy.sh --publish` entry is disabled; its dry run remains available for migration checks. Normal builds and Git pushes do not publish.

## Compatibility and publication

Java packages/classes, Bean names, configuration keys, OAuth/RPC identities, APIs, and database ownership are retained. Existing SQL and DDL history are copied byte for byte. Artifact/build versions and necessary build paths change. A successful build does not imply application startup or live infrastructure acceptance.

Git pushes run validation only. Central and npm publication are separate user actions. CI defaults to initial source bootstrap; after publication set `STELLAR_USE_SOURCE_BOOTSTRAP=false` to consume published artifacts directly. Private organizations may supply the Actions secret `STELLAR_ENCLOSURE_READ_TOKEN` with repository read access.

Original MIT/LGPL licenses and author attribution are preserved.
