# Independent package releases

Each repository owns its publication commands in its README. Normal builds and Git pushes validate code; they do not publish. Java coordinates retain `top.egon`, the npm scope is `@stellar-enclosure`, and initial versions are `0.0.1`.

## Publication scope

| Repository | Public artifacts | Excluded artifacts |
|---|---|---|
| Stellar-Enclosure-Parent | Common parent and platform parent POMs | No sibling repositories are aggregated |
| Stellar-Enclosure-Components | BOM, parent POMs, reusable components, Starters, code generator, Maven plugin and reusable boundary-test assertions | Executable Admin, sample/integration tests and benchmarks |
| Stellar-Enclosure-COLA | Root archetype parent, seven archetypes and four required peer facade contracts | Generated aggregator and all other source examples |
| tianshu-service | Parent and three Starters | Admin and integration tests |
| yuheng-service | Parent, contract, cores and four Starters | Admin, all executable gateways and the test reactor |
| tianquan-jianshen-service | Parent, contract, core and Starter | Admin and internal gateway adapter |
| tianquan-shoubing-service | Parent, core, RPC contract and Starter | Admin and internal gateway adapter |
| yaoguang-service | None | Entire application repository |
| web-sdk | Shared web package and Jianshen React SDK | Private workspace root |
| portal and the five *-web applications | None | All frontend applications remain private |

## Maven credentials

Use Java 25 and each repository's Maven Wrapper. The existing `release` profile attaches sources, Javadoc and GPG signatures and publishes with `central-publishing-maven-plugin`. The plugin version remains unchanged. It maps each module's `maven.deploy.skip` to `skipPublishing`; explicit exclusions also protect application and test artifacts. See [Sonatype's plugin configuration](https://central.sonatype.org/publish/publish-portal-maven/#skippublishing).

Before running `deploy`, verify ownership of namespace `top.egon` in Central Portal, generate a Portal user token and configure its token username/password under server ID `central` in your local `~/.m2/settings.xml`. These are Portal token credentials, rather than the account login password. For example, merge the following server into your existing settings without replacing other configuration:

```xml
<server>
    <id>central</id>
    <username>${env.CENTRAL_USERNAME}</username>
    <password>${env.CENTRAL_TOKEN}</password>
</server>
```

Provide those environment variables in your local publishing session or use Maven's supported encrypted credentials. Keep the token and GPG private key outside Git. A local GPG signing key must be available and its public key published for Central signature validation; configure `gpg.keyname` in local Maven settings if multiple keys are present, and unlock it with your local GPG agent. Credential creation and public-key distribution are operator setup.

Local rehearsal uses `-Prelease -Dgpg.skip=true ... clean verify`; it neither signs nor uploads. Actual publication uses `-Prelease ... clean deploy`. Unit tests remain enabled in the README commands; infrastructure/invoker tests are explicitly skipped where documented. Fix failing tests before publication.

## First Maven release and dependencies

A fresh release cannot be completed by publishing eight whole repositories in a fixed sequence: the platform parent imports the Components BOM, and the Components RPC Tianshu adapter depends on the Tianshu base Starter.

1. Publish `stellar-enclosure-parent` from Parent's root using `-N`.
2. Publish `stellar-enclosure-components-bom` from Components using its standalone POM and `-N`.
3. Publish `stellar-enclosure-platform-parent` from Parent's `platform-parent/pom.xml` using `-N`.
4. Publish the remaining public parent POMs, base Components and RPC Starter in dependency order.
5. Publish Shoubing core/Starter, Tianshu base Starter, the Components RPC Tianshu adapter, and then the upper-level Starters/contracts/cores in their dependency order.
6. In COLA, generate/check all seven archetypes. Publish its parent once, then the four facade contracts with `publish-resolved-facade`, and finally select the seven archetypes. Its README supplies the exact commands. Apply the flattening profile only to facade builds, so the parent retains its management sections.

The public artifact graph lists the precise per-artifact order. Regenerate it from the sibling checkouts, including generated archetypes, when versions or dependencies change:

```bash
python3 scripts/maven-release-order.py \
  --workspace "$(cd .. && pwd)" \
  --output "$(pwd)/release/maven-release-order.json"
```

This generates metadata only. For an initial partial release, run the owning repository's Maven Wrapper against a single POM in that order; use `-N` for parent POMs, and add `-Ppublish-resolved-facade` only for the four COLA facade contracts. Local bootstrap via `scripts/bootstrap-workspace.sh` can prepare builds, but installed artifacts are not available to remote consumers until actually published. The README bootstrap block exports `MAVEN_ARGS` with the chosen repository so later Maven commands and COLA generator subprocesses resolve the same local artifacts, including when local Maven settings configure a different default cache. Change both cache paths together if needed.

After the prerequisites are public, use each repository's normal README release commands independently. Never overwrite a published GAV. If publication partially succeeds, inspect Central and select only unpublished modules with `-pl`, or version the changed artifacts and update dependent POMs. Do not rerun a full reactor at unchanged versions after publishing some of its modules.

## npm credentials and independent packages

The only public packages are:

- `@stellar-enclosure/stellar-enclosure-web-shared`
- `@stellar-enclosure/stellar-enclosure-tianquan-jianshen-react-sdk`

Use Node 24/npm 11 and an npmjs account with publishing access to the `@stellar-enclosure` organization. Run `npm login --registry https://registry.npmjs.org/` in your own publishing session, or configure a permitted publishing token through your local secret tooling. Each package pins the public registry and access in `publishConfig`; the private workspace and all applications stay private. See [npm publishing documentation](https://docs.npmjs.com/cli/v11/commands/npm-publish/).

From `web-sdk`:

```bash
npm ci
npm run release:check
npm run release:shared -- --dry-run
npm run release:jianshen -- --dry-run

# Publish either package independently when ready.
npm run release:shared
npm run release:jianshen
```

`prepublishOnly` runs package tests and `prepack` rebuilds JavaScript/declarations, including on a direct workspace publication. Version each workspace explicitly for subsequent releases, then update the workspace lock and the consuming applications' dependency versions and locks. Published npm name/version pairs are immutable.

For the initial release, `web-sdk/scripts/verify-consumers.mjs` checks the actual packed bytes against all six applications' locks. When publishable contents change before that release, explicitly run `--phase prepare`, then `--phase verify`. Publish the exact verified tarballs using the commands in the web-sdk README. The verifier's output manifest records the resulting checksums; it never publishes.

After publication, verify ordinary npm/Maven builds without prewarmed first-party caches. Set `STELLAR_USE_SOURCE_BOOTSTRAP=false` to select the published-artifact CI path.

## Validation boundary

Compilation, local installation, unit tests, deterministic generation and release-shape checks do not prove credentials, Central/npm acceptance or live PostgreSQL/Redis/MQ/OAuth/browser behavior. Applications and infrastructure are started only by the operator. Existing SQL migrations remain unchanged.
