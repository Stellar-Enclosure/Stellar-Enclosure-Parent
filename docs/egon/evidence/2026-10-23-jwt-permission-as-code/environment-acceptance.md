# S10 / S25 / S32 environment acceptance handoff

Status on 2026-10-26: **NOT_RUN**. Source compilation, unit/HTTP/transaction fixtures, static SQL parsing, package installation and artifact verification are separate from real database, browser, listener and delivery acceptance. The user explicitly prohibited automatic project startup, commits and pushes; no authorized existing target/session fixture was supplied. Nothing in this handoff starts a project, database, container or preview server.

## Controlled clean-environment initialization

Provision the approved schemas and existing ACTIVE IdP realms first. Retain all 144 historical and four new migration hashes; do not edit/repair an existing migration. Then use these one-shot commands with reviewed owner-only files:

1. IdP `bootstrap-permission-identities --command-file FILE --receipt-file FILE`: finite client/resource/grant provisioning and original SQL audit receipt. See [IdP B0](../../../../../tianquan-shoubing-service/docs/permission-identity-bootstrap.md).
2. META `bootstrap-permission-metadata --command-file FILE --receipt-file FILE`: exact business/environment/application/namespace/binding/catalog-scope and RBAC-publisher source-import grants. Its public business/application IDs and six-part target must match R. See [META B0](../../../../../tianshu-service/docs/permission-metadata-bootstrap.md).
3. RBAC `bootstrap-permission-catalog --command-file FILE --receipt-file FILE`: explicit scope/producer ownership and finite CI/deployer capabilities. This creates no permission/resource/role definitions. See [RBAC B0/B1](../../../../../tianquan-jianshen-service/docs/permission-catalog-bootstrap.md).
4. Register the actual packaged FULL manifests, await the original matching source-import receipts and READY state, deploy the exact artifact, obtain server-issued deployment qualifications and activate the complete explicit producer set.
5. RBAC `bootstrap-permission-admin --command-file FILE --receipt-file FILE`: one-time explicit administrator codes from the activated catalog, with the reviewed active revision and role-selection intent. It cannot grant wildcard/unactivated codes or replay after a lost SQL original receipt.

These commands branch before normal application startup and reject ordinary CI. Actual JDBC writes and cross-center B0 → READY → activation → B1 were not executed in this task. Preserve the same operationId after an unknown outcome and recover the SQL original receipt; do not switch operations to force a grant through.

## Real PostgreSQL profiles

Use an already running dedicated target and protected credential files. Set only non-secret URLs, usernames, opt-in flags and file paths in the shell; credentials stay in private files. Check every required variable before invoking Maven, and require nonzero executed tests with no relevant skips. A skipped or missing fixture is not acceptance.

| Owner | Maven module / profile | Explicit target contract |
| --- | --- | --- |
| IdP | `:stellar-enclosure-tianquan-shoubing-admin`, `-Pidp-stateless-postgresql-it` | `IDP_STATELESS_POSTGRES_IT=true`, `IDP_STATELESS_JDBC_URL`, `IDP_STATELESS_CREDENTIAL_FILE`; private Properties contains only user/password. Dedicated database name must end `_idp_stateless_it`; operator prepares the empty `tianquan_oauth` schema. Tests apply the immutable scripts there. |
| Edge | `:stellar-enclosure-yuheng-edge-gateway`, `-Pedge-oauth-postgresql-it` | `EGON_EDGE_TEST_PG_ALLOW_DDL=true`, `EGON_EDGE_TEST_PG_URL`, `EGON_EDGE_TEST_PG_EXPECTED_DATABASE`, `EGON_EDGE_TEST_PG_CREDENTIAL_FILE`; private user/password Properties. Tests check database identity, create/migrate/drop only their UUID schema. No password environment variable is used. |
| RBAC | `:stellar-enclosure-tianquan-jianshen-admin`, `-Ptianquan-jianshen-permission-catalog-it` | `TIANQUAN_JIANSHEN_IT_POSTGRES_URL`, `TIANQUAN_JIANSHEN_IT_POSTGRES_USER`, `TIANQUAN_JIANSHEN_IT_POSTGRES_PASSWORD_FILE`; catalog/grant/runtime fixtures create an owned isolated schema and exercise actual migration/locking behavior. |
| META | `:stellar-enclosure-tianshu-admin`, `-Ptianshu-permission-metadata-it` | `TIANSHU_PERMISSION_METADATA_IT_ENABLED=true`, `TIANSHU_PERMISSION_METADATA_IT_CONFIG`; private YAML names the approved already migrated database, credentials and `allowTransactionalWrites: true`. Fixtures roll back their writes. |

For the chosen owner, run from its repository, with JDK 25 selected:

```bash
./mvnw -B -ntp -pl :<exact-module-from-table> -P<exact-profile-from-table> verify
```

This is an execution template, not a recorded pass. Do not copy one owner's profile to another repository. The accidentally copied Tianshu integration profiles were removed from the RBAC POM; each remaining selector belongs to real tests in its owner module.

## Existing browser and protocol environment

The [external Playwright harness](../../../../../tianquan-jianshen-web/docs/permission-external-acceptance.md) has no `webServer` or localhost default. Eight scenarios were collected and typechecked; the disabled runtime gate was tested. No browser ran. It requires an explicit enable flag, an owner-only fixture, two disposable tenants/apps/namespaces/environments, existing private browser states and a known retained refresh operation. It neither fills passwords nor records trace/HAR/video/screenshots.

The [Yuheng handoff](../../../../../yuheng-service/docs/yuheng-permission-producers.md) lists 14 real-listener test classes excluded from the offline run. Their HTTP/gRPC/WebSocket/upstream behavior, real Redis and real SQL authority calls require a separate authorized runtime run. The four in-memory MCP transport cases were executed separately; they are not listener acceptance.

Complete the remaining live cases with the prepared dataset: native login/Consent/Code/PKCE and refresh response loss, cross-node/restart replay, fresh authentication and account switch, two-app SSO/CSRF/Cookie/logout, direct API and nested/multipart FIELD bypass attempts, database failure denial, concurrent authorization changes, old-build mismatch denial, translation draft versus publication, frontend-only activation retaining an old backend, rollback by a new explicit activation, and trusted pipeline deployment qualification. Do not replace these cases with a successful readiness response or mock fixture.

## CI and distribution gate

All SDK/tool locks remain explicitly `LOCAL_UNCOMMITTED`; the user requested no commits. Local tarballs and contract resources were verified. Production distribution and every online operation require a real clean fixed SDK commit, the digest-pinned RC artifact, provisioned exact targets and scoped credentials. No floating main/latest or registry fallback supplies the new APIs.

GitHub delivery requires a successful current protected-branch build and a separate trusted successful deployment workflow/artifact for activation. GitLab additionally verifies the configured exact deployment job, completed pipeline and its actual archived `permission-deployment.json` through the same-origin read-only API. Local readiness JSON alone is insufficient. Missing pin/proof/credentials fails before delivery; LOCAL register/activate adapters reject before any credential or HTTP access. See each repository's `docs/permission-ci.md` and SDK tool README.

Remote CI, service credentials/grants, protected branch/environment settings, real registration, metadata READY, deployment/readiness, qualification and activation remain **NOT_RUN / NOT_CONFIGURED**. Do not mark S10, S25, S32 or overall delivery complete until their dated, redacted target-specific evidence exists.
