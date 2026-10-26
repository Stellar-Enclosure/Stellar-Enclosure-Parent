> S01 design review snapshot. Original DRAFT/pre-creation statements below are historical; current migration hashes and execution status are in execution-status.json. This is not executed PostgreSQL validation. Final migrations are immutable.

# S01 META 完整数据库结构草案

状态：**DESIGN FROZEN，root 已确认结构与共同限额；临时 SQL 仍不是最终 migration。**

范围：`/Users/mario/SelfProject/Stellar-Enclosure/tianshu-service` 后端。当前仅创建本目录两个临时草案；未改源代码、managed manifest、sharding YAML 或任何现存 migration，未运行数据库/服务/容器/浏览器，未提交。

实施权威：已接受的 `2026-10-23-17-39-jwt-permission-as-code-i18n-design.md` 与 `2026-10-23-20-14-jwt-permission-as-code-i18n-implementation.md`，含后补的 PostgreSQL source_import_grant 及 B0/B1 两段冷启动。文件头尚未更新授权状态不覆盖用户最新批准。

## 1. 冻结输入与现状

- META HEAD `a7d04077c6cffd6aa611e071214470dc1b66df61`，开始时工作树干净。
- 当前 managed DDL 最后版本 `20261022_001`，freshBaselineVersion 为 `20261018_001`；旧 SQL 不修改。
- 拟最终迁移：`stellar-enclosure-tianshu-admin/src/main/resources/db/egon-mp/V20261023_001__tianshu_permission_metadata.sql`；创建前再次确认无版本碰撞。最终文件一旦创建即不可修改。
- 根代理已冻结：catalogScopeId/resourceId/permissionId、producerVersion、activationVersion 均为正 long；JSON 传十进制字符串，DB 为 bigint。expectedRevision 允许零。producerVersion 是中心分配序号，不是 artifact.version。
- sourceVersion 严格等于 manifestDigest，64 位小写十六进制 SHA-256。
- source-import 提供完整 typed Manifest 与 RBAC 分配的 resource/permission ID map；META 独立重算 policyDigest/metadataDigest/manifestDigest。最终 artifactDigest 不属于源导入，由部署资格处理。
- 使用任务局部 JDK 25：`/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home`。不修改系统默认 Java。

## 2. 最小复用设计

新增 **9 张逻辑表**；扩展现有 `ddc_i18n_page`，将其明确收敛为人工草稿和当前人工发布页，不另建平行的 draft/head 表。

所有新逻辑表路由为 `STANDARD_TENANT_ID`，当前单库物理表后缀 `_t0`。保留项目 EgonModel 基础字段：id、tenant_id、create/update actor/time、deleted_at、version。

| 逻辑表 | 责任与主键 | 核心业务唯一性 / 关系 | 可变性 |
| --- | --- | --- | --- |
| `ddc_metadata_scope` | META 本地 ID；RBAC catalogScopeId 的可信目标映射 | tenant+catalogScopeId；tenant+business+namespace+env+app；FK 现有 namespace/app/binding | insert-only；既有 scope 启用状态仍由原实体决定 |
| `ddc_source_import_grant` | 机器导入授权 | tenant+catalogScopeId+producer+principalBindingDigest；精确 issuer/client/resource 另存并逐次比较 | 身份绑定不可变；仅 enabled 与 version/审计字段可变 |
| `ddc_i18n_source_version` | 不可变来源内容 | tenant+scope+producer+sourceVersion；三摘要、canonical Manifest、中心 ID maps、projectionDigest、统计 | insert-only |
| `ddc_resource_metadata_projection` | 七种资源与权限定义的展示索引 | source+metadataKind+definitionKey；RESOURCE 与 PERMISSION 分型；同 source case-only 冲突拒绝 | insert-only，按 sourceVersion 查询 |
| `ddc_i18n_source_message` | 来源默认文本/占位符 | source+pageCode+messageKey；defaults、defaultLocale、sourceHash、placeholders | insert-only |
| `ddc_i18n_import_receipt` | API-009/010 的原始成功结果 | scope+producer+operationId；精确 producerVersion、source、三摘要、requestDigest、grantVersion、原响应 | insert-only；失败不产生成功回执 |
| `ddc_catalog_activation_projection` | 可信 API-006 不可变描述符 | tenant+scope+activationVersion；完整 descriptor、digest、producerCount | insert-only；没有 active/latest 字段 |
| `ddc_catalog_activation_producer` | 描述符的精确成员 | descriptor+producer；FK 同 scope 的 sourceVersion/三摘要；producerVersion 独立记录 | insert-only |
| `ddc_i18n_published_override` | 人工发布的不可变历史 | scope+page+publicationRevision；scope+page+publishOperationId；源审核版本/摘要与原 draftRevision | insert-only |
| **复用** `ddc_i18n_page` | 人工草稿、当前人工发布头 | 新 scope+page 唯一约束，保留旧物理 scope 约束；复合 FK 绑定 publishedOverride ID/revision | 人工 CAS；source import 永不写入 |

`metadataKind=RESOURCE/PERMISSION` 不增加第八种 resource enum；RESOURCE 的 type 仅 APP/MENU/PAGE/COMPONENT/BUTTON/API/FIELD，PERMISSION 只持 permissionId/code/display metadata。

定义版本生命周期是历史投影。RBAC 当前人工 DISABLED/RETIRED 状态不通过篡改旧 sourceVersion 表达；授权 Runtime 始终以 RBAC 当前治理状态为准。

### 2.1 现有人工页扩展与替换边界

保留现有 draft_translations/version、published_translations/published_version，新增：catalog_scope_id、draft_activation_version、draft_source_hashes、current_override_id、published_source_hashes、published_draft_revision、published_operation_id、published_at。

人工发布在一个事务中锁页/CAS、插入不可变历史、更新当前 publication ID/revision 和对应快照。现有版号 version 仅因人工保存/发布推进；sourceVersion、producerVersion、activationVersion、publishedVersion 各有独立含义。人工 publish 不修改任何源表。

旧 default_locale/published_default_locale 保留为编辑/审核上下文；运行 fallback 使用指定来源版本的 defaultLocale，不以人工页的旧默认语言替代。清除覆盖通过发布空 map，不能删除历史或清空指针。源移除 key 后，人工数据保留，但运行输出 key 域仍由选定源快照决定。

本次只支持清洁目标，不导入旧混合页数据。ALTER 新的 NOT NULL 字段在存在旧数据时拒绝执行；不会自动填造映射、删除本地数据或回写旧历史。旧页面代码在 S21 切换，旧 `/admin/initialize` 不可继续特殊发布代码源。

### 2.2 来源去重与 producerVersion

不可变源内容按 scope+producer+manifestDigest 唯一。producerVersion 是 RBAC 注册序号，记录于回执与激活成员，不强行当作内容哈希。一个精确内容源可被多个已验证的注册/激活成员引用。相同 sourceVersion 但中心 ID map/projectionDigest 不同必须冲突，不能用新导入覆盖旧 ID。

资源/词条的单所有者规则由 RBAC 完整 ActivationSet 及 Manifest 合同校验；META 再验证选定集合内的唯一所有者、引用闭包和页面默认语言一致性。历史所有者变更和候选版本可以同时存在，不能用候选导入切换独立 META owner/latest 指针。

## 3. 授权、事务与并发冻结

### 3.1 精确机器 grant

principalBindingDigest 使用共享规范序列化已验证 issuer/clientId/resourceUri 后计算 SHA-256，避免将两个最长 2048 字符的 URI 放入同一个超宽 btree 唯一键。摘要命中后必须再逐字段精确比较，不能用摘要代替主体绑定。Grant 默认 enabled=false，由 B0 显式启用。

API-009/010 每次依次执行：SERVICE JWT typ/audience/Scope/身份数据库状态 → 可信目标 scope → 本地 grant 的精确主体、producer、enabled/version → 既有 scope/binding 启用状态。重复结果读取也重新鉴权。

导入事务对 grant 与 scope/binding 行取得共享锁，授权禁用/更新必须取得冲突行锁并推进 version；顺序以 PostgreSQL 提交为准，后续请求不使用旧缓存。授权绑定更换用新 grant，旧 grant 只禁用，不改 issuer/client/resource/scope/producer，不删除被历史回执引用的行。

### 3.2 Source-import / receipt

同一个本地事务插入源内容、全部资源/词条与成功回执；不调用 RBAC 网络接口，不写人工页或发布指针。收到相同 operationId 时比较完整 requestDigest；同内容返回原 response_json，不重新造 ID、计数或时间；异内容返回 409。

导入 requestDigest 包含完整 target、producerVersion、typed Manifest 和 ID maps，排除可变传输头。未确认提交的调用方只能查询原 operationId；成功回执缺失不等于允许换 operationId 覆盖。

三摘要与 sourceVersion 的一致性除服务校验外，回执/激活成员还用复合 FK 绑定到同一个 source row 的 policyDigest/metadataDigest。Grant FK 同时绑定 tenant/scope/producer，防止记录别的目标授权。

### 3.3 Descriptor / bundle

通过已认证 API-006 读取精确 activationVersion；校验完整 scope、digest、全部成员、来源三摘要与单所有者/引用闭包后，一次事务保存 descriptor+members。成员外键要求源已存在；失败不保存半个 descriptor。META 不生成当前激活指针，浏览器不能自传成员集合。

Bundle 事务读取指定 descriptor、精确源集合、page/common 的当前人工发布快照；输出 key 域仅来自该源集合。默认查询不以 MAX(version) 代替 RBAC 版本。ETag 必须覆盖源集合和人工发布 revision，draftVersion 不参与。

### 3.4 人工发布

draft API 限 USER 管理权限；SERVICE grant 不授权人工写入。每次编辑保存明确的 activationVersion/sourceHashes 审核上下文，并按现有 page version CAS。publish 使用稳定 operationId、expectedDraftRevision 与请求摘要；重复发布查询精确历史结果，不重新推进 publishedVersion。

发布只能复制当前已保存 draft，不能借 publish 同时带入尚未保存的编辑。数据库 publication guard 检查历史快照与页当前发布字段完全一致、publishedVersion 恰增一、snapshot.draftRevision 等于发布前 page.version。空 map 是合法的清除覆盖，不恢复旧缓存中的 key。

## 4. 数据库防护与完整字段清单

`meta-schema.sql` 是展开后的完整草稿，包含全部列、类型、NOT NULL、CHECK、业务唯一键、FK、查询索引与触发器。新 immutable 表禁止 UPDATE/DELETE；grant 只允许 enabled+CAS；人工页限制身份不变、版本推进与原子发布快照。

使用现有 PostgreSQL managed runner，它支持 dollar-quoted function 分句；新触发器不修改旧表历史脚本。函数/触发器必须纳入 readiness 与数据库集成测试，不仅检查表存在。首版不增加历史版本物理清理任务；保留可回滚/审计内容，不自动删旧版本。

数据库硬上限草案：canonical Manifest/descriptor 16 MiB；各 ID map、完整页翻译/源审核 hash map 2 MiB；单资源 policy 256 KiB、target/i18n refs 64 KiB。服务与共享 schema 还必须限制 key/locale/资源数/深度；最终上限需在 S11 同步确认，SQL 不能晚于最终文件创建再修正。

所有 API ID/revision 编解码必须严格十进制 long 字符串；数据库 bigint 已约束正值或允许零的 expected/draft/grant revision。禁止 JavaScript number 透传 ID。

## 5. Managed DDL、路由与 readiness 修改清单

现有文件的完整路径前缀：
`/Users/mario/SelfProject/Stellar-Enclosure/tianshu-service/stellar-enclosure-tianshu-admin/`

1. `src/main/resources/db/egon-mp/repository-manifest.json`：只追加本次最终 SQL 的一个版本及 SHA-256，保留所有旧条目与 `freshBaselineVersion=20261018_001`。
2. `src/main/resources/egon-tianshu-persistence.yml`：新增下列 9 个 STANDARD_TENANT_ID logical table；保留现有 ddc_i18n_page 路由、PRIMARY/LOCAL、Outbox 同数据源/事务。
3. `src/main/java/top/egon/cola/component/tianshu/admin/config/DdcDatabaseReadyValidator.java`：表清单、完整列集合、PK/UK/FK/CHECK、case-insensitive/GiN 索引及 3 函数/10 触发器均需覆盖；旧页面列集合必须加入本次扩展。现有 validator 检查完整列集合，因此不能只补表名。
4. `src/main/java/top/egon/cola/component/tianshu/admin/migration/DdcPersistenceMigrationCli.java` 与 `DdcI18nTopologyUpgrade.java`：新版路径为清洁目标 initialize→validate；旧 upgrade-i18n 仍只认识截至 20261022_001 的精确历史。显式保留历史入口或拒绝当前新 manifest，不放宽 fingerprint。历史测试固定旧 fixture 或断言新版拒绝，不能把新表塞入旧指纹转换。
5. `src/test/java/.../migration/DdcTianshuDdlContractTest.java`：更新预期拓扑、精确列/约束、清洁初始化后的完整链；旧 migration SHA 与旧基线保持不变。
6. `pom.xml`：S17 建立 PostgreSQL-only `tianshu-permission-metadata-it`，默认不执行外部数据库测试、不启动 Testcontainers；后续 S18/S21 将各自 IT 加入。

路由指纹由完整新 topology 重新推导；Tianshu 的 public.ddl_history 与 egon_outbox.ddl_history 均按完整新 topology 验证。B0 只在已初始化并通过 validate 的新目标执行；无在线拓扑升级或旧数据迁移。

## 6. B0/B1 初始化顺序

B0（首次 source-import 前，显式受控工具/fixture，绝非服务启动）：

1. IdP 建限定 Resource/Scope 的 RBAC publisher SERVICE Client 与 Resource Grant。
2. RBAC 建完整 catalogScope 与 producer owner，返回正式 catalogScopeId。
3. META 建/核验现有 biz/env/app/namespace/binding，再校验精确本地实体 ID 与名称映射并创建 immutable metadata_scope。
4. META 建默认仅 RBAC publisher 的 exact source_import_grant；激活 enabled/version 后才允许导入。
5. 标准登记→Tianshu receipt→READY→RBAC activate→读取可信 descriptor。

B1：受控一次性管理员流程授予明确 permissionCodes；之后人工页/资源 UI 才使用正式 USER Runtime 权限。机器初始化不授予用户角色，不借暂时公开管理 API 完成冷启动。

## 7. 验证范围（尚未运行）

S17 单元/合同：DDL 文件 checksum/历史不变，table-route parity，完整列/索引/约束，JSON long 边界，函数分句与 immutable trigger 清单。

真实 PostgreSQL IT：清洁初始化、重复初始化、wrong fingerprint/缺表/缺约束拒绝；跨 tenant/scope 复合 FK；source immutable UPDATE/DELETE 拒绝；grant disable/版本竞争；source+receipt 同事务 rollback；重复/乱序/冲突；人工发布原子快照/重复 operation；未保存编辑不得借 publish 带入；空覆盖发布；source import 后人工 revision/文本完全不变；descriptor 成员缺失或错摘要拒绝。

S18/S21 联调等待共享 Manifest/DTO 与 IDP S06、RBAC S19/S20；不能以 mock 用户 principal 或宽泛 SERVICE Scope 提前启用接口。当前未执行任何 Java、数据库或环境测试。

## 8. 仍需 root 最终确认后才能创建 migration

- 接受复用人工页、9 个新表与 immutable source/published 历史结构。
- 接受纯数据库防护 trigger（immutable、grant identity/CAS、publication一致性）；若选择其他实现必须在最终文件创建前确定。
- 与 S11 合并确认 projection 生命周期值、JSON大小上限与 sourceHash/placeholder canonical 规则；SQL 结构已容纳 typed Manifest 与两类中心ID maps。
- sourceContent 同一摘要允许多 producerVersion 引用；receipt/descriptor 保存精确 revision，不能用 sourceVersion 推算 revision。

最终 migration 当前尚不存在。草案可以在冻结前修正；最终迁移创建后不能修改，所有后续接口和测试必须符合冻结结构。

## 9. 静态清点结果

- draft SQL SHA-256：`0f34f24cd01a067024019c94ec764d8280e85b7b74cf84f3d907c5c184203cdf`（仅草案指纹，不是最终 migration checksum）。
- 新表 9；具名约束 85；显式查询/表达式索引 7；函数 3；触发器 10。
- Python 静态清点已检查本文件同类名称无重复、标识符不超过 PostgreSQL 63-byte 上限、无 DROP TABLE/TRUNCATE；这不是 PostgreSQL SQL 执行或迁移成功证明。

### 新 logical table 路由

```yaml
ddc_metadata_scope: { type: STANDARD_TENANT_ID }
ddc_source_import_grant: { type: STANDARD_TENANT_ID }
ddc_i18n_source_version: { type: STANDARD_TENANT_ID }
ddc_resource_metadata_projection: { type: STANDARD_TENANT_ID }
ddc_i18n_source_message: { type: STANDARD_TENANT_ID }
ddc_i18n_import_receipt: { type: STANDARD_TENANT_ID }
ddc_catalog_activation_projection: { type: STANDARD_TENANT_ID }
ddc_catalog_activation_producer: { type: STANDARD_TENANT_ID }
ddc_i18n_published_override: { type: STANDARD_TENANT_ID }
```

### Readiness 触发器与函数

- `ddc_metadata_reject_mutation`
- `ddc_source_import_grant_guard`
- `ddc_i18n_page_publication_guard`
- `tr_ddc_metadata_scope_immutable`
- `tr_ddc_i18n_source_version_immutable`
- `tr_ddc_resource_metadata_projection_immutable`
- `tr_ddc_i18n_source_message_immutable`
- `tr_ddc_i18n_import_receipt_immutable`
- `tr_ddc_catalog_activation_projection_immutable`
- `tr_ddc_catalog_activation_producer_immutable`
- `tr_ddc_i18n_published_override_immutable`
- `tr_source_import_grant_guard`
- `tr_i18n_page_publication_guard`

## 10. 冻结确认补充

- root 已确认9新表+人工页复用，以及immutable/grant CAS/publication数据库guards。
- environment上限32；pageCode/messageKey上限128；registrationKey上限200；clientId上限200。
- code lifecycle仅ACTIVE/DEPRECATED，DISABLED/RETIRED是RBAC独立治理状态。
- sourceHash = SHA256(canonical {pageCode,key,defaultLocale,defaults,sortedPlaceholderNames})；各语言沿既有{{name}}占位符规则验证一致。
- 共用限额：Manifest/descriptor16MiB；ID maps各2MiB；每producer最多10k资源/权限定义/refs、20k messages、每词条32locales、32组x64code、depth16。
