# S01 RBAC schema and shared protocol freeze

Owner: tianquan-jianshen-service. This is the complete schema catalogue before creation of the single V16 migration. It is not executable SQL and does not claim database validation. Current B14__create_current_rbac3_schema.sql and V15__encapsulate_skip_locked_worker_claims.sql remain byte-identical. Existing role/user/assignment/hierarchy/SoD/management/org/directory facts and PostgreSQL Outbox are reused. Existing resource-grant/resource-binding/field-rule tables are retained as retired historical storage; no new runtime reader/writer uses them. No destructive cleanup or compatibility grant conversion occurs.

## Shared identity, versions and payload

- catalogScopeId/resourceId/permissionId/planId/deploymentQualificationId: server-generated positive signed-long values, JSON canonical decimal strings, DB bigint. producerVersion is a monotonically increasing revision within scope+producer; activationVersion is monotonically increasing within scope. Revisions are JSON strings, expected revision permits "0".
- operationId: caller-generated UUID string, scope+producer-bound; not a login credential. No naked operation lookup.
- sourceVersion = manifestDigest = lower-case 64-character SHA-256.
- CatalogScope: catalogScopeId, tenantId, businessCode, applicationCode, namespaceCode, environment; stable target tuple unique. Scope links the existing local application ID and exact trusted DDC mapping. No environment/tenant/URL/ID is encoded into registrationKey.
- Manifest v1 retains the approved Spec's top-level schemaVersion/application/producer/artifact/permissionDefinitions/permissionReferences/resources/resourceReferences/messages. It contains no centre IDs or deployment artifactDigest. Definitions have explicit owner, stable semantics, i18n and classification; DTO adapters normalise a singular requirement or multiple AND groups into a single internal expression.
- Access classifications PUBLIC/INTERNAL/PROTECTED are explicit; omitted classification in the approved example normalises to PROTECTED only when a non-empty requirement is supplied. Missing requirement is never inferred PUBLIC.
- resource types APP/MENU/PAGE/COMPONENT/BUTTON/API/FIELD only. Definition lifecycle ACTIVE/DEPRECATED; current centre governance ACTIVE/DISABLED/RETIRED is a separate overriding state and never changed by CI.
- Canonical UTF-8 JSON: ASCII property/identifier keys, lexicographically sorted object keys, stable sorted/de-duplicated set fields, no insignificant whitespace, finite integral numeric schema values, no unpaired Unicode surrogates. Identity/revision numbers are strings. Full commit/build provenance participates in manifestDigest; only enforcement semantics participate in policyDigest; source defaults and i18n references participate in metadataDigest. Shared fixture vectors ship in the contract JAR.
- Size ceilings: manifest/activation descriptor 16 MiB UTF-8; source-import bounded by manifest plus 2 MiB ID maps each and finite wrapper overhead; 10,000 resources/permission definitions/references per producer, 20,000 messages, 32 locales/message, 32 AND groups with 1..64 unique codes each, nesting depth <=16. Per-resource policy <=256 KiB; target/i18n maps <=64 KiB. Code <=128, resourceKey<=200, producer<=128, pageCode/messageKey<=128, environment<=32, clientId<=200, URI<=2048. ASCII case-only identifier collisions rejected.
- Source-import contains operationId, full scope, producerId, producerVersion, canonical typed Manifest, resourceIds and permissionIds maps, three digests. META recomputes all three, sourceVersion and projectionDigest; response immutable receipt includes the same target/version/digests and original counts. Identical content may be reused by multiple trusted registration operations; same content with different ID maps conflicts.
- ActivationDescriptor contains scope, activationVersion, activation operationId, policyVersion, createdAt and sorted complete producer members. Each member pins producerId/producerVersion/sourceVersion, all three digests and trusted artifact qualification refs. An instance compares its own producer entry, never its digest with a whole-scope aggregate.

## Complete table catalogue

Conventions: all tables have explicit PK/UK/FK/CHECK constraints; timestamps are timestamptz. Mutable governance rows use version bigint>=0, created_at/created_by, updated_at/updated_by. Append-only facts use created_at/created_by and cannot be rewritten. No cascading deletion. All IDs are positive. JSON values have explicit object/array and storage octet-length checks (twice the canonical byte ceiling to allow PostgreSQL JSONB spacing); application contract validation enforces the canonical limits. Unique identifier indexes additionally reject lower-case collisions. Foreign keys always include catalog_scope_id where cross-scope confusion is possible. Existing local application and role tenant/application FKs remain enforced.

### 1. rbac3_catalog_scope

id PK, tenant_id bigint, business_code varchar(128), application_id bigint, application_code varchar(128), namespace_code varchar(128), environment varchar(32), ddc_business_id varchar(64), ddc_application_id varchar(64), status ACTIVE/DISABLED, version, audit columns. UK full target tuple and (id,tenant_id,application_id). FK application_id to existing rbac3_application; service additionally verifies code and trusted DDC identity before B0. Scope identity is immutable. Status/version changes do not alter identity. New deployment slots are not namespaces.

### 2. rbac3_catalog_producer

(catalog_scope_id,producer_id varchar(128)) PK; kind JAVA/REACT_TYPESCRIPT, owned_key_prefixes jsonb array, owned_permission_prefixes jsonb array, owned_message_prefixes jsonb array, expected_modules jsonb nonempty array, current_revision bigint>=0, enabled boolean default false, version and audit. Prefixes are owner policy, not trusted from manifest. Empty prefix sets mean no ownership, never wildcard. FK scope. Governance changes are audited and versioned. A producer revision increments only when a new immutable content version is registered.

### 3. rbac3_catalog_service_grant

id PK; scope+producer FK; issuer varchar(2048), client_id varchar(200), resource_uri varchar(2048), principal_binding_digest char(64), capabilities jsonb array restricted to REGISTER/ACTIVATE/READ_DESCRIPTOR/QUALIFY_DEPLOYMENT/CLEAR_PRODUCER, allowed_source_refs jsonb array, allow_permission_expansion boolean false, enabled boolean false, version/audit. UK(scope,producer,principal_binding_digest); exact issuer/client/resource must also match after digest lookup. Coarse OAuth Scope and this database grant are both required. No grant authorises USER role administration. Binding immutable; disable and create replacement to change principal/target. Authentication status still comes from IDP database authority.

### 4. rbac3_catalog_resource

id PK; scope FK, registration_key varchar(200), resource_type enum seven, owner_producer_id, governance_state ACTIVE/DISABLED/RETIRED, version/audit. UK(scope,key), UK(scope,id), FK(scope,owner)->producer. Key/type/semantic identity cannot be silently reused; ownership transfer is explicit and preserves id. Case-only key collisions rejected. Runtime membership comes from exact active resource versions, not presence of this identity row.

### 5. rbac3_catalog_permission

id PK; scope FK, permission_code varchar(128), meaning varchar(1024) immutable, owner_producer_id, governance_state ACTIVE/DISABLED/RETIRED, version/audit. UK(scope,code), UK(scope,id), FK(scope,owner)->producer. Meaning and code are immutable; i18n labels can change through versions. A retired code is never reused. New permission identity does not create any role grant.

### 6. rbac3_catalog_manifest

(scope,producer,producer_version bigint>0) PK; manifest_digest/policy_digest/metadata_digest char(64), canonical_manifest jsonb, state REGISTERED/METADATA_PENDING/READY/FAILED, source_operation_id varchar(36), repository/commit/build_id/artifact_version text bounded, resource_count/permission_count/message_count nonnegative, diff_json jsonb, metadata_receipt_id varchar(128) nullable, failure_code varchar(128) nullable, version, created_at/created_by, updated_at. UK(scope,producer,manifest_digest). Immutable content/provenance; only state/receipt/failure/version transitions. Same digest under a new operation reuses existing version/IDs, does not rewind producer head. producer_version FK for all version rows. CHECK state READY iff matched receipt reference exists; actual reference matching is in the local transaction.

### 7. rbac3_catalog_resource_version

(scope,producer,producer_version,resource_id) PK; registration_key/type, definition_lifecycle ACTIVE/DEPRECATED, classification PUBLIC/INTERNAL/PROTECTED, definition_json jsonb, definition_digest char(64), target_json jsonb, i18n_json jsonb. FK exact manifest and resource(scope,id). UK(scope,producer,version,key). Append-only; service verifies resource owner/type/key and statement coverage. Query indexes by resource/type/Key. Requirements and independent field operations are normalised to the next table in the same transaction.

### 8. rbac3_catalog_resource_requirement

(scope,producer,producer_version,resource_id,operation,group_index,permission_code) PK; operation ACCESS/PLAIN_READ/MASKED_READ/WRITE, group_mode ALL/ANY, permission_id nullable only for a reference not yet registered in a candidate set, group_index 0..31, code_index 0..63. FK exact resource_version; FK(scope,permission_id) when present. Non-empty groups are validated from complete definitions before persistence; active-set closure requires every code resolve to the same scope and trusted owner. Group mode must be consistent within a group; registration service enforces and tests this. Append-only definition content; do not later fill nullable references in immutable rows, resolve unresolved candidate references during activation by code.

### 9. rbac3_catalog_permission_version

(scope,producer,producer_version,permission_id) PK; permission_code, definition_json jsonb, definition_digest char(64), i18n_json jsonb, lifecycle ACTIVE/DEPRECATED. FK exact manifest and permission(scope,id). Append-only. Definition ownership and immutable meaning checked on registration.

### 10. rbac3_catalog_message_owner

(scope,page_code varchar(128),message_key varchar(128)) PK; owner_producer_id, lifecycle ACTIVE/DISABLED/RETIRED, version/audit. FK(scope,owner)->producer. Case-only key pairs rejected. Does not own translations. Explicit ownership transfer preserves stable page/key and cannot mutate already registered source versions.

### 11. rbac3_catalog_registration_plan

id PK; scope+producer FK, expected_producer_revision>=0, expected_active_revision>=0, owner_version>=0, service_grant_id/version, manifest_digest/policy_digest/metadata_digest, request_digest, canonical_manifest jsonb, diff_json jsonb, authorization_expansion boolean, expires_at, created_at/created_by. UK(scope,producer,id). Immutable planned facts; grant/owner/current pointer rechecked at apply, not trusted from stale plan. Plan expiry is fixed. No runtime directory effects.

### 12. rbac3_catalog_registration_operation

(scope,producer,operation_id varchar(36)) PK; plan_id, request_digest, manifest_digest, producer_version, original_receipt_json jsonb, created_at/created_by. Composite FK plan and manifest. Append-only original receipt including original IDs/counts/revisions. GET returns that receipt plus separately derived current manifest status; response status is not rewritten into the original receipt. Same operation differing body/target/plan fails.

### 13. rbac3_catalog_source_receipt

(scope,producer,producer_version) PK; source_operation_id varchar(36), receipt_id varchar(128), source_version char(64), manifest/policy/metadata/projection digests, receipt_json jsonb, received_at. Composite FK manifest; UK(scope,producer,source_operation_id). Append-only. Outbox retry uses stable original operation; mismatch cannot advance READY. Remote delivery is never inside the candidate transaction.

### 14. rbac3_catalog_deployment_qualification

id PK; scope+producer+version FK; artifact_digest char(64), manifest/policy digests, pipeline_id/build_id/source_ref/commit, deployment_id, readiness_digest, trusted_issuer/client_id/resource, verified_at, expires_at, original_receipt_json jsonb. UK(scope,producer,id). Append-only; server verifies caller's QUALIFY_DEPLOYMENT capability and allowed source refs, immutable build/manifest matches and non-business readiness. A browser or arbitrary request Header cannot supply authority. Expiry only limits using the qualification for a new activation, not the immutable historical activation proof.

### 15. rbac3_catalog_activation

(scope,activation_version bigint>0) PK; operation_id varchar(36), expected_active_revision>=0, request_digest, descriptor_json jsonb, descriptor_digest char(64), producer_count>0, policy_version bigint>=0, created_at/created_by. UK(scope,operation_id). Append-only. ACTIVE/SUPERSEDED is derived from the single pointer, not another mutable current flag. Unknown commit outcome queries original operation; committed rollback creates a new version.

### 16. rbac3_catalog_activation_producer

(scope,activation_version,producer_id) PK; producer_version, manifest/policy/metadata digests, source_version char(64), qualification_id. FK exact activation, manifest and scope/producer qualification. Append-only. The complete set must be closed over all code/resource/message references, all source receipts matched. Unchanged versions may be reused. New set does not union policies from old/new instances.

### 17. rbac3_catalog_active_pointer

scope PK; activation_version bigint nullable only before first activation, revision bigint>=0, policy_version bigint>=0, version, updated_at/updated_by. Composite FK activation. Initial revision 0, activation null; subsequent revision equals activation version and advances exactly once under row lock/CAS. Same local activation transaction increments existing tenant authorization policy_version, so existing role/constraint mutation and new catalogue changes share a revocation barrier.

### 18. rbac3_catalog_role_binding

(scope,role_id) PK; tenant_id, application_id, permission_version bigint>=0, enabled boolean true, version/audit. Composite FK(scope,tenant,application) to scope and (tenant,application,role) to existing role. Same role can be explicitly bound to multiple scopes but each permission assignment is isolated; a role in another tenant/application cannot be bound. Existing role hierarchy/SoD/cardinality rules remain facts and cannot bypass this mapping.

### 19. rbac3_catalog_role_permission

(scope,role_id,permission_id) PK; status ACTIVE/DISABLED, valid_from, valid_to nullable, version/audit. Composite FKs to role_binding and permission(scope,id); valid_to>valid_from. Replacement of a role's full target set is one transaction with binding permission_version CAS, existing tenant policy_version increment, audit and rebuild Outbox. Existing user assignments/active roots are preserved; this table is the only permission-code grant source, never legacy resource grants or resource_api_binding.

### 20. rbac3_catalog_effective_snapshot

id PK; scope,tenant_id,user_id,issuer/subject,auth_version,tenant_policy_version,catalog_version,role_context_digest char(64),snapshot_digest char(64),snapshot_json jsonb,expires_at,created_at. Composite scope FK and existing user(tenant,id) FK. Lookup index(scope,user,auth_version,tenant_policy_version,catalog_version,role_context_digest,expires_at), deliberately nonunique so an expired snapshot can be rebuilt without inventing an authority-version change. Immutable snapshot with codes, effective roles, existing data scopes, field requirements and deadlines. No token/plain credentials. Valid only while every authoritative version and expiry matches.

### 21. rbac3_catalog_snapshot_head

(scope,user_id) PK; snapshot_id,auth_version,tenant_policy_version,catalog_version,role_context_digest,fence_version bigint>=0,version,updated_at. Composite snapshot identity FK prevents head pointing to another subject/scope/version. Publish head/fence atomically after rechecking all authority facts in one consistent database transaction. No Redis checkpoint or grace fallback.

### 22. rbac3_catalog_rebuild_task

id PK; scope,user_id nullable (scope rebuild),requested_auth_version,requested_policy_version,requested_catalog_version,command_id varchar(128),state PENDING/RUNNING/SUCCEEDED/FAILED,attempt>=0,next_attempt_at,owner/lease_token nullable,lease_generation>=0,lease_until,deadline,failure_code,version,created_at/updated_at. UK(scope,command_id). State/lease checks, due indexes and bounded claim CAS. Local Outbox schedules work; stale worker cannot publish after lease/authority changes. No in-memory authoritative queue.

### 23. rbac3_catalog_runtime_projection

(projection_kind,projection_key) PK; tenant_id,auth_version,policy_version,payload_json jsonb,checksum char(64),ready boolean,updated_at. Kinds USER/TENANT/CHECKPOINT/GATEWAY preserve existing RuntimeRepository interface payloads while moving shared authoritative storage to SQL. Every write is database CAS; final permission decisions additionally use scope-specific active/snapshot tables. This is a storage adapter for existing ports, not a second permission truth. Expected version and checksum conflicts reject.

## Existing table changes and retirements

- rbac3_data_rule gets catalog_scope_id bigint NOT NULL. Require an empty legacy data-rule table on this clean-only migration rather than deleting rows or guessing mappings. Replace only fk_rbac3_data_rule_permission_global with composite same-scope FK to new catalog_permission; add scope/role_binding FK. Retain existing rule/ref tables and ALL/SELF/DEPT/... semantics, expiry and directory snapshot facts. DAO reads/writes take catalogScopeId. Existing rbac3_field_rule is not read as a competing field-policy source.
- Existing role/user/assignment/hierarchy/SoD and management tables stay; all their authorised mutation flows continue to advance existing user/tenant versions. Catalogue role grants and activation explicitly participate in those versions.
- Existing rbac3_resource/permission/role_resource_grant/resource_api_binding/field_definition remain historical, with their old read/write endpoints and runtime joins retired. No CI seed restores old grants. New runtime is fail closed until new B0/registration/activation/B1 completes.
- New append-only tables may be retained indefinitely in the first release; no physical manifest/translation deletion job is introduced. Only expiring registration plans, terminal tasks and existing approved audit retention are eligible for bounded cleanup once no live reference exists; no deletion revives credentials or retired codes.
- Authentication/audit owner remains IDP. Registration/activation role commands reuse existing PostgreSQL transactional Outbox publisher with payload JSON and owner transaction; no cross-database transaction or new general workflow.

## Freeze checks and B0/B1

The 23 table families above each have a specified writer; audit uses the existing rbac3_audit_log service with full scope and operation in its structured payload, so no parallel audit table is created. Before final V16 creation, verify every column/constraint against these writers; no later step may edit V16. R uses existing EntityManager/native SQL repositories and constructor injection rather than introducing a new ORM or code generator. Proper tests exercise real PostgreSQL FK/CAS/claims when an authorised existing isolated database exists; absent DB does not become PASS.

B0 explicitly establishes current app identity, catalogue scope/producer/exact service grants and role bindings as needed, never on ordinary startup. First registry/publisher receipt activates exact producer set; B1 explicitly grants defined permissionCodes to initial administrators. Old seed rows do not implicitly acquire new namespace/environment rights. No automatic data deletion/repair/publication.
