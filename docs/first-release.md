# First 0.0.1 release

Source validation and package publication are separate. Push workflows never deploy to Central or npm.

## Maven

1. Use Java 21. Configure your Central/GPG credentials outside Git.
2. Run scripts/bootstrap-workspace.sh with explicit workspace/local-repository arguments. It orders actual module dependencies; publishing entire repositories in a simple sequence is insufficient.
3. In COLA run scripts/generate_archetypes.sh generate and check. Validate all seven generated families.
4. Run scripts/maven-deploy.sh --workspace ABS --local-repository ABS --dry-run. It prepares the public artifact graph and release profiles with runtime tests and signing disabled.
5. Review release/maven-release-order.json, all GAVs/POM metadata and release-shape results. Use --publish only when you intentionally want Central publication. Namespace remains top.egon; initial versions are 0.0.1.

The common parent and standalone Components BOM precede the platform parent. Base components precede Shoubing core/starter, Tianshu base starter, the Components RPC Tianshu adapter, upper-level starters and applications. Native/Open facade artifacts use the existing publish-resolved-facade profile so unpublished source-project parents do not leak into public POMs. Internal source projects and modules marked for skipped publication are excluded.

Do not overwrite published GAVs. After partial publication inspect the actual registry before retrying. Published changed content requires a new version.

## npm

Public packages:
- @stellar-enclosure/stellar-enclosure-web-shared@0.0.1
- @stellar-enclosure/stellar-enclosure-tianquan-jianshen-react-sdk@0.0.1

Run web-sdk/scripts/verify-consumers.mjs with workspace/cache/output arguments. Publish the exact verified tarballs with npm publish TARFILE --access public. Actual integrity values are in web-sdk/release/npm-manifest.json. The workspace root and all applications remain private.

After publication validate ordinary npm ci and Maven builds without prewarmed first-party caches. Set STELLAR_USE_SOURCE_BOOTSTRAP=false to use the published-artifact CI path.

## Validation boundary

Compilation, unit tests, deterministic generation, local artifact installation and release-shape checks do not prove live PostgreSQL/Redis/MQ/OAuth behavior or browser flows. Runtime verification remains operator initiated. SQL versions, filenames, content and historical checksums stay immutable.

## Release documentation sources

The release profile uses the existing Maven AntRun 3.2.0 and Lombok 1.18.46 to delombok compiled Java sources before Javadoc generation. Javadoc includes generated MapStruct and Protobuf sources; production Java is unchanged. The empty Yuheng test-suite jar and the existing benchmark/internal source projects are excluded from public release. Compilation and test availability are preserved. Signing and actual registry publication remain user initiated.
