# Stellar-Enclosure-Parent

Shared Maven build and release foundations for Stellar Enclosure. All first-party modules start at **0.0.1**.

## Responsibilities

| Entry | Function |
|---|---|
| [Common parent](pom.xml) | Publishes `stellar-enclosure-parent`; manages the Spring Boot dependency baseline, shared database dependencies and release plugin configuration. |
| [Platform parent](platform-parent/pom.xml) | Publishes `stellar-enclosure-platform-parent`; sets the Java 25 baseline, imports the Components BOM, manages platform libraries, and configures compiler, test, Protobuf and packaging plugins. |
| [Workspace bootstrap](scripts/bootstrap-workspace.sh) | Installs prerequisite POMs and builds the eight sibling Java repositories in dependency order before their first public release. Supports explicit workspace/cache paths, offline mode and reactor resume. |
| [Release inventory](release/maven-release-order.json) and [inventory generator](scripts/maven-release-order.py) | Records artifact ownership, publication exclusions and dependency order for the first Maven Central release. |
| [Release guide](docs/first-release.md) | Documents credentials, local checks, publication order and recovery after a partial publication. |

This is a build infrastructure repository: it contains two parent POMs and supporting scripts, with no business application or API. Parent inheritance and dependency management do not start services or aggregate sibling repositories in a normal Maven invocation. Components owns the reusable libraries/BOM; [COLA](https://github.com/Stellar-Enclosure/Stellar-Enclosure-COLA) owns the application archetypes and coding skills. The release guide is the entry point for working across repositories.

## Build

Requires Java 25 and the included Maven Wrapper. The shared parent manages Spring Boot 4.1.2. Once the 0.0.1 dependencies are published:

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

## Java 25 and Spring Boot 4

The common parent sets Java 25 and Spring Boot 4.1.2 for every Java repository and generated application. Platform and archetype parents use Spring Cloud 2025.1.4; the archetype parent also uses Spring Cloud Alibaba 2025.1.0.0. Components uses MyBatis-Plus's Boot 4 starter at 3.5.17, Redisson 4.8.0 and Spring AI 2.0.2. Springdoc is 3.1.1, JaCoCo 0.8.14 supports Java 25 bytecode, and the test-only WireMock baseline is 3.13.2. The platform and Components parents import the gRPC 1.75.0 BOM to keep core, API, stubs and transports on the existing protocol baseline. GitHub Actions, GitLab CI and container templates use Java 25.

Existing business JSON types and serializers continue to use Jackson 2 through Boot's `spring-boot-jackson2` compatibility module. The identity and Tianshu RPC SDK auto-configurations retain the qualified `jacksonObjectMapper` name as an alias when Boot supplies `jackson2ObjectMapper`; an explicitly supplied host mapper keeps its name. Application configurations select `jackson2` with `spring.http.converters.preferred-json-mapper` and `spring.http.codecs.preferred-json-mapper`. Move external Jackson 2 settings from `spring.jackson.*` to `spring.jackson2.*`, matching the checked-in configurations. Jackson 3 remains available to Spring AI and Springdoc. See the [Spring Boot migration guide](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide) and [Jackson 2 configuration](https://docs.spring.io/spring-boot/4.1/reference/features/json.html).

The archetype async configuration exposes `AsyncConfigurer` through an adapter bean so Boot can decorate it without replacing the configuration object that owns the bean factories. The existing `asyncConfiguration` and executor bean names are retained. Identity authorization providers are decorated through the security post-processing hook so Security 7 can still discover their request validators.

Use a JDK 25 `JAVA_HOME` for Maven and generator subprocesses. Compilation and offline unit tests do not establish database, Redis, OAuth, RPC or application startup acceptance; run those checks in your deployment environment before rollout.

## Repository boundaries and first publication

The root POM publishes `top.egon:stellar-enclosure-parent:0.0.1`. `platform-parent/pom.xml` publishes the shared platform parent. Neither aggregates sibling repositories during normal builds. Components owns its standalone BOM; COLA owns its archetype parent.

See the [release guide](docs/first-release.md) and [Maven release order](release/maven-release-order.json). Historical architecture designs and runbooks are archived under `docs/history`.

## Publish to Maven Central

This repository publishes two independent POMs. Run from this directory with Java 25, a Central Portal token configured as Maven server `central`, and a local GPG signing key. See [credentials and initial release order](https://github.com/Stellar-Enclosure/Stellar-Enclosure-Parent/blob/main/docs/first-release.md).

```bash
# Common parent: local release check, then publication.
./mvnw -B -ntp -N -Prelease -Dgpg.skip=true clean verify
./mvnw -B -ntp -N -Prelease clean deploy

# Platform parent: the Components BOM at the referenced version must already be published.
./mvnw -B -ntp -N -f platform-parent/pom.xml -Prelease -Dgpg.skip=true clean verify
./mvnw -B -ntp -N -f platform-parent/pom.xml -Prelease clean deploy
```

The root does not aggregate `platform-parent` or any sibling repository. Initial order is common parent → Components BOM → platform parent → library parents and modules in dependency order. Each GAV may be published once; choose new versions for changed content. Normal builds and Git pushes do not publish.

## Compatibility and publication

Java packages/classes, Bean names, configuration keys, OAuth/RPC identities, APIs, and database ownership are retained. Existing SQL and DDL history are copied byte for byte. Artifact/build versions and necessary build paths change. A successful build does not imply application startup or live infrastructure acceptance.

Git pushes run validation only. Central and npm publication are separate user actions. CI defaults to initial source bootstrap; after publication set `STELLAR_USE_SOURCE_BOOTSTRAP=false` to consume published artifacts directly. Private organizations may supply the Actions secret `STELLAR_ENCLOSURE_READ_TOKEN` with repository read access.

Original MIT/LGPL licenses and author attribution are preserved.
