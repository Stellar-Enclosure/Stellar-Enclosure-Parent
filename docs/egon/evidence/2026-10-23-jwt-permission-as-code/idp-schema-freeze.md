> S01 design review snapshot. Original DRAFT/pre-creation statements below are historical; current migration hashes and execution status are in execution-status.json. This is not executed PostgreSQL validation. Final migrations are immutable.

# IDP S01 schema freeze proposal

Status: DRAFT_FOR_MAIN_AGENT_FREEZE. No final migration exists. No database has been touched.
Owner: /Users/mario/SelfProject/Stellar-Enclosure/tianquan-shoubing-service only.
Draft SQL: /tmp/stellar-pac-20261023-implementation/idp-schema.sql.
Target single migration after approval: admin/src/main/resources/db/egon-mp/V20261023_001__stateless_oauth_state.sql.

## Verified baseline

- Git HEAD baseline 49122f8, repository clean when work started.
- Managed family `tianquan-oauth`, schema `tianquan_oauth`; existing scripts 20261008_001 and 20261009_001 are immutable.
- `OAuthManagedDdlComponent` applies the complete repository manifest against the owned single primary through `EgonColaPostgreDdlRunner`; this is not the legacy Flyway public schema.
- `oauth-sharding-native.yml` lists every physical table explicitly. All five new tables must be included before topology/readiness validation. No new datasource, replica or store owner is introduced.
- Existing per-table records follow EgonModel: id, tenant_id, version, create/update time and actor, deleted_at. New tables follow this exact convention.
- tenant_id is the TrustedRealm storagePartitionId; it is not taken from browser/body headers. Existing subject/member facts may use the identity authority partition, so no false cross-partition subject FK is added.
- JDK25 found locally: /opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home (25.0.3). Build commands set JAVA_HOME/PATH only for the task process; no download/global profile changes.

## Frozen authority model

Reuse oauth_authorization.id as the authorization-family ID; do not create a parallel family table. Reuse oauth_token for authorization-code and refresh consumption and consumed-history lookup. Refresh generation is stored on the family and each REFRESH token, atomically advanced with old-token consumption/new-token insertion. The EDGE owns cross-instance HTTP refresh-operation/unknown-outcome coordination; the IDP must not add a competing EDGE operation coordinator or return previously issued credentials from a receipt.

Reuse oauth_security_state for REALM/CLIENT/SUBJECT generations and oauth_revocation for JTI/AUTHORIZATION/KID revocation facts. Database commit defines revocation; remove projection_status and Redis APPLIED transitions. All issuer/client/resource/grant/membership reads used by authorization come from the owner DB/verified owner service, with no Redis or disk-spool authority fallback.

New oauth_authentication stores minimal revocable authentication facts keyed by the SHA-256 of Authentication JWT jti: subject, browser binding digest, REALM/SUBJECT generations, auth_time, PASSWORD acr, immutable 8-hour maximum expiry and revocation. It stores neither the JWT nor a SecurityContext. Every browser request still proves identity with the signed JWT; a transaction ID never becomes authentication. Authentication expiry ends SSO reuse, not an unrelated re-authentication or every existing family; retain facts until all linked families' safe retention bounds have elapsed.

## Existing-table changes (all included in the single draft)

| Table | Changes and invariants |
| --- | --- |
| oauth_client | browser_bound flag for explicitly enrolled EDGE clients; exact post_logout_redirect_uris; same-tenant ID unique key for FKs. Ordinary direct OAuth clients do not gain REFRESH_CONTEXT capability. |
| oauth_authorization | immutable requested_scopes/resource_uri/authentication_jti_digest/interaction_id/client_browser_binding_digest; mutable approved-scope narrowing and refresh_generation; retain_until; lifecycle PENDING_CONSENT/ACTIVE/REVOKED/EXPIRED/CANCELLED; one intended audience; scope subset; same-tenant client/authentication/interaction FKs. |
| oauth_token | refresh_generation and retain_until; uniqueness per family/generation; at most one nonconsumed/nonrevoked REFRESH; same-tenant family FK; CONSENT_STATE exits the type list because consent is now an interaction fact. Encrypted token material remains internal SAS persistence and is never exposed by status/receipt APIs. |
| oauth_consent | resource_uri in uniqueness; consent for one client/resource cannot grant another resource's scopes. Client FK. |
| oauth_security_state | permanent unique (tenant_id,target_type,target_key); deleting/recreating state must not reset a generation. |
| oauth_revocation | remove Redis projection_status; permanent target identity and retain_until. KID tombstones may remain unbounded; finite targets retain past every valid credential's last acceptance time. |
| oauth_audit | event_fingerprint, source issuer/client facts and retain_until; stable unique event ID already exists; same payload replays succeed, different payload conflicts. |

## New tables

| Table | Responsibility | Important key/constraints |
| --- | --- | --- |
| oauth_authentication | JWT authentication/revocation fact only | (tenant,jti_digest) permanent; fixed expiry; generation >=0; no serialized user/token/security context; revocation must carry time/reason |
| oauth_interaction | one bounded authorization/forced-password-change/logout transaction | (tenant,interaction_id), purpose, request digest/encrypted parameters, separate IDP and EDGE browser-binding digests, CSRF digest, exact Client/resource/redirect/PKCE, scope ceiling, optional verified authentication/restricted-subject, CAS state, 5-minute expiry, consumed time |
| oauth_audit_inbox | authenticated audit intake and recoverable delivery | (tenant,event_id), fingerprint, source issuer/client/resource, redacted payload <=16KiB, PENDING/PROCESSING/STORED/DEAD/EXPIRED, attempts, next-attempt, owner/token/generation/lease, terminal/processing/retention deadlines |
| oauth_audit_receipt | immutable outcome returned after actual durable outcome | unique (tenant,event_id), receiptId and inbox; fingerprint + source binding; STORED requires final audit row FK; DEAD/EXPIRED never count as successful strict audit handoff |
| oauth_audit_dead_letter | permanent failure evidence, no Redis dead stream | unique inbox FK, safe failure code/attempts/fingerprint/timestamps; original sanitized event remains in inbox until bounded retention |

All relationships are same tenant. No CASCADE delete. Worker claim uses a transaction plus expected-version/lease-generation CAS; database time is authoritative. A worker that lost its lease cannot finalize or acknowledge an event using an old token. Claim is not an in-memory distributed lock. Bounded cleanup transactions can use row locks/CAS without a separate persistent global lock table.

## OAuth and TOKEN response contract

Main agent confirmed the following claims for USER Access JWT:
- authorization_id: existing positive decimal string, family ID.
- authn_jti: Authentication JWT jti string.
- refresh_generation: canonical nonnegative decimal string.
- authorization_expires_at and authn_expires_at: NumericDate integer seconds.
SERVICE tokens retain authorization_id and their existing service claims, but carry no authn_jti/refresh_generation/user authentication expiry fields. Signature typ/purpose/audience remain isolated. ID Token is never an Access Token. Fresh authentication sets auth_time and PASSWORD; password repetition does not produce MFA/STRONG.

The raw authn_jti necessary for token issuance can remain inside existing encrypted authorization attributes; the indexed DB join uses its digest. No raw Authentication JWT is persisted. Signing-key verify_until must cover the longest Authentication JWT issued by that key plus allowed clock skew, even if normal Access JWT lifetime is shorter.

### Browser binding (EDGE owner acknowledged; pending main-agent schema freeze)

IDP browser binding and EDGE browser binding are distinct origins/credentials. Enrolled browser_bound clients send the constrained browser_binding authorization parameter containing SHA-256 of the EDGE browser-binding cookie. IDP freezes it into interaction/family; EDGE verifies the successful callback against its original request transaction. Normal token exchange does not accept a caller-supplied replacement binding. REFRESH_CONTEXT compares the EDGE request digest to family.client_browser_binding_digest. Missing/mismatched binding rejects this special service operation.

AUTH-07 resolve request candidate: purpose ACCESS_VALIDATION|REFRESH_CONTEXT; accessToken (sensitive); expectedResource; expectedClientId; refreshTokenDigest and browserBindingDigest required only for REFRESH_CONTEXT. Service identity is independently authenticated against dedicated scope/audience; issuer/tenant/resource are server-bound. Ordinary ACCESS_VALIDATION strictly validates exp. Only explicitly authorized EDGE callers may use REFRESH_CONTEXT: it validates signature/typ/iss/aud/client, checks the family absolute deadline and current DB generations, and confirms the supplied opaque Refresh digest belongs to that same active family/current generation/browser. A bounded expired Access JWT can establish only refresh-context eligibility, never API Authentication or IdentityBootstrap. Response fields are purpose, eligible, reasonCode, issuer, resource, clientId, subject, authorizationId, authenticationJti, refreshGeneration, authorizationExpiresAt, authenticationExpiresAt and securityVersion. Identifiers/generation are strings and the two expiries are NumericDate integer seconds. On eligible=false only purpose/eligible/reasonCode are populated; callers cannot treat denial facts as authentication. Response contains no Token, Secret or SecurityContext.

### Consumed Refresh standard revocation (confirmed)

Keep POST issuer/oauth2/revoke. Authenticate the confidential client first. A dedicated historical digest lookup may find a consumed Refresh token and its original family; strict realm/client ownership is mandatory. It then calls the existing family-revocation domain service. Unknown/nonmatching tokens have the normal non-disclosing RFC7009 response. Do not relax general OAuth2AuthorizationService.findByToken, Refresh Provider eligibility, or any API JWT expiry check. Do not add a generic family-revoke endpoint.

Current code gap: TransactionalOAuthRevocationAuthenticationProvider first calls TenantAuthorizationServiceImpl.findByToken, whose isCurrentToken rejects spent Refresh; authorization==null currently skips durable revoke. TokenRevocationServiceImpl.revoke already resolves by digest and closes REFRESH families, so that extension point can be reused safely.

## Transaction, receipt and failure boundaries

- Consent state transition, approved scopes and one-use Code persist in one local transaction. Identity binding is immutable, protocol state is not blanket-immutable.
- Refresh validates and locks family + old token, consumes old generation, advances generation, signs/inserts new token facts and enqueues audit in the same transaction. Failed signature/persistence leaves no successful response. Replayed generation closes the family according to policy; no credential replay receipt exists.
- Owner-originated identity/token events use the existing PostgreSQL transactional Outbox in egon_outbox with its existing independent history. No new outbox table or cross-owner transaction is added.
- Remote audit intake may process inbox + final audit + receipt synchronously in one transaction. If processing is deferred, only PENDING is exposed; strict audit callers require a committed STORED receipt before continuation. Background claim/recovery produces terminal receipts atomically with final audit/dead-letter. A durable inbox alone must not be reported as final STORED.
- An HTTP timeout after committed audit/registration is resolved by the same event ID + fingerprint; no new event ID retry. A DB failure has no Redis/spool or in-memory success fallback.
- AUTH-07 owner termination authenticates the SERVICE locally and reads DB state without recursively invoking itself or triggering recursive remote auditing.

## TTL and retention decisions

- Authn JWT absolute validity: default/max 8h in this first implementation; no refresh extension.
- Access: default 300s / max 600s. Code default60s/max120s. Interaction max300s.
- Refresh: family absolute lifetime bounded by registered client policy and configured first-release 8h default. Family expires independently of ongoing browser requests.
- Retain all family tokens including spent Refresh until >= family.absolute_expires_at + 24h, reusing existing TOKEN_FAMILY_GRACE. authn and interaction records extend retain_until monotonically to the maximum of their own bounds and all linked family bounds; this does not extend authentication/interaction eligibility.
- Retain finite revocation tombstones until expiry +24h (never before max token/family acceptance plus skew); compromised KID records are not automatically deleted.
- Reuse existing 180-day final-audit retention. Inbox/receipt/dead-letter share matching retention to preserve idempotency and provenance. Worker processing deadline is finite, configured independently of evidence retention; no lease can survive that terminal deadline.
- Cleanup order is receipt/dead-letter -> final audit/inbox where eligible, token -> family -> no-longer-referenced interaction/authentication. Reject cleanup with live references. Cleanup cannot erase a spent Refresh digest merely because consumed_at is non-null.

## Freeze and validation gate

The draft deliberately rejects non-empty legacy authorization/token/consent/revocation/audit state instead of performing implicit migration or deleting data. Full clean initialization runs both immutable older managed scripts then this one. Existing identity/client/key facts are not copied into a new identity store.

Before final file creation: confirm EDGE binding/DTO, inspect complete schema and all intended S02-S06 writes, verify names/unique keys/retention, verify old SQL hashes, then main agent acknowledges freeze. Once the final migration is created it is immutable; later steps cannot add columns to it. Discovery of missing schema after creation is a plan-review blocker, not permission to edit history.

S01 validation performed: source/PO/Mapper/XML/manifest/routing/retention and framework-extension inspection; local JDK25 version query; cross-review by EDGE owner and explicit SQL NULL/lease-bound correction. No SQL syntax engine, real migration, database, service or browser has run.

Targeted baseline command attempted on unmodified sources:
JAVA_HOME=/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home PATH=<jdk25>/bin:$PATH ./mvnw -B -ntp -pl :stellar-enclosure-tianquan-shoubing-admin -am -Dtest=OAuthConsentRoundTripTest,TokenRevocationServiceTest,OAuthAuditOutboxDeliveryHandlerTest -Dsurefire.failIfNoSpecifiedTests=false test
Result: exit 1 before compilation/tests. The resolved parent BOM does not manage 12 Boot4 split-module dependencies; actual tests executed = 0. Log: /tmp/stellar-pac-20261023-implementation/idp-baseline-test.log. Root notified to coordinate Parent/BOM local bootstrap; no POM workaround was made. Actual SQL execution and concurrent PostgreSQL proof remain explicitly unverified.
