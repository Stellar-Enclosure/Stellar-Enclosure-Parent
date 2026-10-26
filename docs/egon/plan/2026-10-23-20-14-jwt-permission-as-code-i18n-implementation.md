# JWT 无 Session 身份与 Permission as Code 实施 Plan

| Field | Value |
| --- | --- |
| Document | 2026-10-23-20-14-jwt-permission-as-code-i18n-implementation.md |
| Template Version | 4；沿用仓库 Plan 结构与逐步验收格式 |
| Revision | 1 |
| Status | In progress；2026-10-25 按用户要求恢复并发实施，三个阶段尚未完成 |
| Created | 2026-10-23 20:14 Asia/Shanghai |
| Updated | 2026-10-24 06:25 Asia/Shanghai |
| Owner | mario |
| Repository | Stellar-Enclosure-Parent；各实现步骤归属独立子仓库 |
| Scope | Boot 4/JDK 25、JWT/OAuth2/SSO、数据库权威状态、Java + React/TS 权限声明、RBAC、Tianshu 多语言元数据、CI/CD 与本地测试环境注册 |
| Source Requirement | 用户“Plan 确认，按计划开始实施，三个阶段按依赖顺序推进，做好验证，不要自动启动项目。并发多subagent开发。” |
| Implements Spec | [JWT / Permission as Code / i18n Spec](../spec/2026-10-23-17-39-jwt-permission-as-code-i18n-design.md) |
| Spec Status | Accepted；Spec 与 Plan 均已获用户确认 |
| Spec Revision | 2；2026-10-23 19:54 的技术正文，后续仅更新批准状态与 Plan 关联 |
| Effective Specs | 仅上述 Spec 的 REQ-001–036、AC-001–036、TEST-001–054 |
| Depends On Plans | None；历史 Plan 不作为本次实施前置授权 |
| Supersedes | None；[旧身份 Spec](../spec/2026-10-23-16-17-jianshen-oauth2-idp-sso-convergence.md) 已由新版 Spec 整体替代 |

## 1. Summary

按三个阶段、33 个步骤实施：P1 建立 JWT/OAuth2/SSO 与数据库状态基础；P2 建立权限声明、注册、角色权限及 Tianshu 三层内容模型；P3 完成实际应用接入、后端强制鉴权、制品绑定和流水线交付。每步定义责任仓库、入口文件、依赖、执行顺序、验证和安全中间状态。

用户已批准按本 Plan 实施并要求并发 subagent 开发。按依赖推进源码、编译和定向验证；不自动启动项目、服务、数据库、容器、浏览器或 GUI。实际进度与证据记录在 §10，未执行步骤及环境验证不能视为完成。编写 Plan 阶段的文档检查记录保留为历史证据。

核心顺序是“冻结合同和完整数据库结构 → 建立数据库事实与认证链 → 静态声明/候选注册 → 元数据回执 → 版本激活 → 运行鉴权与实际部署验收”。源码开发可按依赖并行；任何不满足完整前置条件的构建不得承接业务流量。

## 2. Effective Design and Repository Baseline

### 2.1 范围与不变量

- 使用当前已升级的 Boot 4.1.2 / Java 25；实施时以 resolved dependencies 和实际 API 为准。不引入 Vue、LDAP、AIoT、外部身份联邦、Token Exchange 或远期扩展。
- Authorization Code + S256/OIDC、Client Credentials 是两条主线；保留受约束 Refresh。IdP 的认证 JWT、业务 Access JWT、ID Token、CSRF Proof 各有独立用途，不能互换。
- 不使用 HttpSession、WebSession、Spring Session、SessionRegistry；不建立 opaque 登录 Cookie → 长期数据库 SecurityContext/Token 仓库。短期 OAuth 事务不是身份凭据。
- 本范围的认证、撤销、授权、注册、幂等、租约、回执、审计和发布事实均以 PostgreSQL 为权威；无 Redis/JVM/磁盘 spool 权威回退。无关业务缓存、服务发现及 MCP 协议会话不在本次重写范围。
- 资源包含 APP/MENU/PAGE/COMPONENT/BUTTON/API/FIELD；角色直接授予 permissionCode。删除资源关联 API 并集授予、suggestedPermissionCode 人工映射和旧分裂注册协议。
- catalogScope = tenant + business + application + namespace + environment；稳定 Key 不带环境/数据库 ID。所有权按 producer 约束；跨环境 ID 不可移植。
- ALL/ANY 组非空，组外 AND；多个角色的合法权限集合先合并。FIELD 的 plainRead/maskedRead/write 独立；前端只控制体验，后端承担实际边界。
- RBAC 是资源/权限/激活权威；Tianshu 是来源文本、人工草稿和已发布覆盖权威。RBAC 只有一个激活指针；Tianshu 不另设 latest。
- 允许破坏式更新，采用清洁环境部署；现存迁移不可修改，不自动删除用户本地数据，不自动提交/推送/发布。

### 2.2 目录别名与责任

用户产品名 Jianshen=IdP、Shoubing=RBAC；当前物理目录相反。以下使用职责别名避免改错仓库，不安排整体目录改名。`W` 为 `/Users/mario/SelfProject/Stellar-Enclosure`；表内为相对 W 的真实目录。

| Alias | 目录 / 当前基线 | 责任 |
| --- | --- | --- |
| DOC | Stellar-Enclosure-Parent；c2a3bff | Spec/Plan、必要的构建顺序元数据 |
| I | tianquan-shoubing-service；49122f8 | Servlet IdP/SAS、身份权威及客户端 Starter |
| R | tianquan-jianshen-service；b2e80d3 | RBAC 合同、目录、角色授权、Runtime、字段执行器 |
| M | tianshu-service；a7d0407 | 多语言来源、翻译、资源元数据投影 |
| Y | yuheng-service；7380a48 | EDGE、既有 Gateway 安全接入 |
| E | Y/stellar-enclosure-yuheng-edge-gateway | 无 Session OAuth Client 与转发 |
| SDK | web-sdk；d407317 | 两个既有 npm 工作区、TS 扫描器与统一 CLI |
| RW | tianquan-jianshen-web；763b54b | RBAC React 管理台 |
| MW | tianshu-web；bf5ca46 | Tianshu React 管理台 |
| IW | tianquan-shoubing-web | IdP React 管理台 |
| PW | portal；f82568a | 门户 |
| YW / AW | yuheng-web / yaoguang-web | 当前网关管理应用 |
| A | yaoguang-service | 既有后端 API/字段权限接入 |

子模块缩写：`IA/IS` = I 下 `stellar-enclosure-tianquan-shoubing-admin/starter`；`RC/RK/RS/RA` = R 下 `stellar-enclosure-tianquan-jianshen-contract/core/starter/admin`；`MA` = M 下 `stellar-enclosure-tianshu-admin`；`SH/RE` = SDK 下 `packages/stellar-enclosure-web-shared`、`packages/stellar-enclosure-tianquan-jianshen-react-sdk`。

Java 文件以模块 `J` 为 `src/main/java` 包根：IA/IS 分别为 `top/egon/cola/platform/tianquan/shoubing/admin|starter`；RC/RK/RS/RA 分别为 `top/egon/cola/platform/tianquan/jianshen/contract|core|starter|admin`；MA 为 `top/egon/cola/component/tianshu/admin`；E 为 `top/egon/cola/component/yuheng/edge`。`T` 为相同包的 `src/test/java`，`RES` 为 `src/main/resources`。所有别名均可机械展开；`M:` 修改已有文件/类，`N:` 拟新增，`D:` 删除旧实现。未标已存在的拟新增名称是目标设计，不是当前事实。

当前 DOC 工作树已有本轮未跟踪 `docs/egon/` 文档且 main ahead 2。实施前逐仓库重验 HEAD、dirty/untracked、迁移版本和依赖；保留无关改动及未推送祖先。不把本 Plan 的历史 SHA 当成将来可覆盖工作树的依据。

### 2.3 复用与设计模式

沿用现有 Controller/Service/Repository、PO/BO/Mapper/Converter、Outbox 与安全 Starter 分层。通过 Adapter 接入 SAS/Servlet/Reactive 扩展点，避免重写 OAuth 协议；用现有领域服务承载目录注册与授权规则；用显式状态及数据库 CAS 实现 OAuth/注册生命周期；跨中心复用 Transactional Outbox。ALL/ANY 使用共享纯函数，扫描器使用编译器/AST API。没有必要新增通用策略注册器、工作流平台、分布式事务或第三个 npm 包。

## 3. Frozen Contracts Before Implementation

### 3.1 AUTH-01–07 的落地 URI 与 DTO

以下为 Plan 拟冻结的目标 URI。S01 用同一合同更新服务端/SDK 测试基线，再开始各端实现。IdP issuer 继续使用已验证的 `/tenants/{tenantId}`；appAlias 来自 EDGE 服务端固定映射，不能由请求选择任意 issuer/Client/audience/上游。

| Contract | 目标入口 | 输入与结果 |
| --- | --- | --- |
| AUTH-01 | GET `/apps/{appAlias}/auth/login`；GET `/apps/{appAlias}/auth/callback` | 受控相对 returnTo；服务端保存 state/nonce/PKCE/绑定摘要/精确回调；回调单次交换 Code 后写凭据 Cookie |
| AUTH-02 | GET/POST `/tenants/{tenantId}/login`；GET `/tenants/{tenantId}/consent`；Consent POST 到该 issuer 的 `/oauth2/authorize` | 已验证的短期 interaction、专用 CSRF、真实认证 JWT；登录只建立 IdP 认证，不直接签业务 Access |
| AUTH-02 | POST `/tenants/{tenantId}/credentials/password` | 受限改密事务或已认证上下文、CSRF；按现有改密规则撤销，不把密码复验升级成 MFA |
| AUTH-03 | issuer 下标准 `/oauth2/authorize`、`/oauth2/token`、`/oauth2/revoke`、`/userinfo`、Discovery/JWKS | 标准协议请求/错误；Code/CC/Refresh Provider 受新的数据库状态约束 |
| AUTH-04 | GET `/apps/{appAlias}/auth/csrf`；POST `/apps/{appAlias}/auth/refresh`；GET `/apps/{appAlias}/auth/refresh-operations/{operationId}` | Proof 绑定浏览器/Client/目的；刷新输入 operationId，结果仅状态/到期信息，凭据只通过 Cookie；查询不能取回凭据或重放兑换 |
| AUTH-05 | GET `/apps/{appAlias}/auth/identity`；API-008 | `IdentityBootstrap` 返回最小主体/tenant/app/认证期限与版本；权限视图返回 codes、完整 scope、auth/policy/catalog/activeRoleContext、expiresAt；无 Token 或 Secret |
| AUTH-06 | POST `/apps/{appAlias}/auth/logout`；GET/POST `/tenants/{tenantId}/logout` | 前者撤销当前应用族；后者 GET 只确认、POST 撤销当前认证 jti 关联族。账号全部撤销继续由受权管理命令推进安全版本 |
| AUTH-07 | POST `/internal/v1/identity/security-state:resolve`；POST `/internal/v1/authorization/runtime:resolve`；POST `/internal/v1/identity/audit-events` | 服务身份绑定 Resource/Scope；用户证明独立验证，禁止 browser 自报 subject/roles。状态/审计接收在 owner 本地验证并查库终止，不递归调用自身 |

Cookie 模式只进入 `/apps/{appAlias}/...`；上游代理入口为 `/apps/{appAlias}/api/**`。Access Cookie 限于该 app 前缀，Refresh/浏览器绑定 Cookie 限于该 app 的 auth 前缀；不同 app 使用不同名称和服务端绑定。IdP 认证 Cookie 限 issuer 域/路径。均使用 Secure、HttpOnly、host-only 和明确 SameSite；CSRF Proof 按专用返回值/双提交合同传递，不把认证 Cookie 暴露给 JS。直连 Bearer 路由单独配置，不能在失败后切换凭据来源。

`IdentityBootstrap` 只返回身份事实；不伪造空权限视图作为成功。P1 的身份组件可独立验证，正式权限 bootstrap 依赖 S20。认证 JWT/Refresh 固定绝对期默认 8 小时；Access 默认 5 分钟、上限 10 分钟；Code 默认 60 秒、上限 120 秒；交互默认 5 分钟。认证 JWT 不由 Refresh 延长。

### 3.2 注册与版本合同

完整保留主 Spec 的 API-001–012 路径、错误码、权限分离与数据语义。唯一 Manifest schema 放 RC 的 `RES/permission-manifest/schema-v1.json`，需要跨语言分发的共享真值/规范化 fixture 放 RC 的 `RES/permission-contract/`，随普通合同 JAR 提供给 TS 测试；不依赖默认不会打包的 test resources，不新增第二份人工 schema。

三个摘要分别是 policyDigest、metadataDigest、manifestDigest；生产者构建内嵌前三者及 producerVersion。最终 JAR/前端包的 artifactDigest 在打包之后计算，记录在受信部署证明中，不把完整制品摘要写回同一个制品制造循环哈希。Header、前端传值或未认证 readiness 不能替代部署证明。

ProducerVersion 的 READY 表示候选完整；ActivationSet 单独标识 ACTIVE/SUPERSEDED 并引用完整 producer 版本集合。未变的旧 producerVersion 可以复用。所有 plan、operation、receipt、CAS、角色命令和缓存键都绑定完整 catalogScope；不能只用 application 或 operationId 裸查。

### 3.3 数据库一次定稿规则

S01 冻结所有 owner 的完整表/列/索引/FK/唯一性/CAS/保留期清单，包含后续步骤才启用的字段。先在非迁移目录的临时草案中完成结构审查；最终迁移一经创建即不可编辑。各 owner 仅一个本次必要新版本，不允许后续步骤追加修改该文件。若发现必须更正已存在迁移，停止该迁移任务并重新评审，不能修改旧文件或擅自添加本任务第二版本。

| Owner / Step | 当前基线与拟定新文件 | 必须一次包含的状态 |
| --- | --- | --- |
| IDP / S02 | IA/RES/db/egon-mp 当前至 V20261009_001；N `V20261023_001__stateless_oauth_state.sql` | 认证事实/安全版本、interaction、授权族、Code/Refresh 摘要与代际、Consent、撤销、审计 inbox/receipt/dead-letter/claim、Outbox 与恢复期限 |
| EDGE / S07 | 当前没有本模块 SQL owner；N E/RES/db/migration/`V1__edge_oauth_state.sql` | 一次性客户端事务、加密 verifier、刷新操作/租约/终态、撤销意图及交付回执；没有长期 SecurityContext/token vault |
| RBAC / S14 | RA/RES/db/migration 基线 B14、最新 V15；N `V16__permission_catalog_and_runtime.sql` | scope/owner、资源/权限版本、角色字符授权、计划/注册/原回执/Diff、激活集合/指针/发布资格、快照/head/fence/rebuild task、Outbox 关系 |
| META / S17 | MA/RES/db/egon-mp 当前至 V20261022_001；N `V20261023_001__tianshu_permission_metadata.sql` | sourceVersion/resourceProjection/sourceMessage、人工 draft/published override、导入回执、ActivationDescriptor 只读投影、sourceImportGrant 及所需索引 |

上述版本号实施前检查冲突再选择；检查不等于允许重命名已存在文件。IDP/META 沿用各自 managed DDL/manifest 流程，RBAC 沿用当前 Flyway 及独立 Outbox history；EDGE 建立自己的数据库 owner/最小访问权限。四个 owner 的不同逻辑存储变化不合并进一个跨库脚本。历史 SQL、baseline、checksum 保持不变；不执行 repair，不自动清库。数据库验证只连接用户提供的隔离环境，DDL rollback 不作为业务回滚手段。

META 的机器导入授权明确属于 META PostgreSQL：新增 `source_import_grant` 表族和 `SourceImportGrant` 模型，纳入 S01 完整清单及 S17 同一个新迁移。每条授权精确绑定已验证 issuer/clientId、目标 Resource、完整 target scope、producerId、enabled 和 version；默认仅授予 RBAC Outbox publisher，普通 CI 不直接调用 Tianshu source-import。API-009/010 在校验 SERVICE Token 的目的/audience/Scope/身份数据库状态之后，本地读取该 grant 和现有 scope/binding，按事务内有效版本决策。禁用/修改提交后，后续鉴权不使用旧缓存；重复操作查回执也重新鉴权。不能只检查宽泛 Scope 后信任请求体 target，不能用 YAML 白名单作权威。

清洁环境初始化分两段：B0 在首次注册前显式建立 IdP Client/Resource Grant、RBAC catalogScope/producer owner、META biz/env/app/namespace/binding/source_import_grant；B1 在首次注册→来源回执→READY→激活之后，由受控一次性管理员流程授予明确 permissionCode，再验证管理 UI。B0/B1 都是获准环境中的受控初始化，不是普通 CI 或服务启动副作用。各 owner 在 S02/S14/S17 提供与测试一致的初始化接口/fixture，S27 汇总交付命令，S32 执行；不存在必须先通过尚未激活的管理权限才能完成 B0 的循环。

## 4. Strategy, Dependencies and Gates

| 阶段 | 步骤 | 交付边界 |
| --- | --- | --- |
| P1 身份与数据库状态 | S01–S10 | 新合同、IdP/EDGE 原生认证链、数据库状态、JWT Cookie transport、实际验证门禁 |
| P2 权限与元数据治理 | S11–S25 | Java/TS 静态导出、目录/角色模型、Tianshu 来源层、激活合同、管理 API/UI |
| P3 执行与交付 | S26–S33 | API/字段强制、当前生产者与六前端、真实包接入、统一 CLI、CI 与验收 |

~~~mermaid
flowchart TD
  S01 --> S02 --> S03 --> S04 --> S05 --> S06
  S01 --> S07
  S05 --> S08
  S06 --> S08
  S07 --> S08 --> S09 --> S10
  S01 --> S11
  S11 --> S12
  S11 --> S13
  S11 --> S14 --> S15 --> S16
  S06 --> S15
  S01 --> S17
  S11 --> S17
  S06 --> S18
  S17 --> S18
  S15 --> S19
  S18 --> S19
  S06 --> S20
  S16 --> S20
  S19 --> S20
  S18 --> S21
  S19 --> S21
  S20 --> S21
  S09 --> S22
  S13 --> S22
  S20 --> S22
  S21 --> S22
  S22 --> S23
  S16 --> S23
  S19 --> S23
  S21 --> S24
  S22 --> S24
  S10 --> S25
  S12 --> S25
  S23 --> S25
  S24 --> S25
  S20 --> S26
  S12 --> S26
  S26 --> S27
  S22 --> S28
  S24 --> S28
  S27 --> S29
  S28 --> S29
  S19 --> S30
  S13 --> S30
  S29 --> S31
  S30 --> S31
  S25 --> S32
  S31 --> S32 --> S33
~~~

每个步骤标题下的 Depends 为精确依赖，图仅概览。S11–S18 的纯合同/扫描/候选存储可与 P1 开发并行；不能绕过 S10 对实际身份链的验收。S20 提前建立 Runtime，是为了让 Tianshu 管理授权与 SDK 使用同一权威，不把它留到 UI 后面造成循环依赖。S26 的执行器可在 P2 UI 开发时并行，但整体 P3 验收仍等 S25。

阶段状态区分 `SOURCE_READY`、`DB_VERIFIED`、`ENV_VERIFIED`。源码和 mock 测试通过不能填后两项；缺实际环境时继续不依赖环境的开发，受保护业务不发布。S10/S25/S32 记录尚缺证据，不用通配权限、公开接口或旧 Session 回退绕过门禁。

## 5. Execution and Validation Conventions

每步按“合同/负向场景 → 最小实现 → 对应验证 → diff 复核”执行，遵守附近代码风格。新增测试只覆盖状态、安全、并发和实际风险；文档/简单映射不机械增加镜像实现测试。每步的 Test 名是计划新增/改造的明确选择器，只有实际执行及报告证明后才可标通过。

验证分层：L0=结构/schema/源码/依赖与制品检查；L1=纯函数、AST/JavaCompiler、单元测试；L2=实际 Servlet/Reactive/SAS/序列化链的进程内测试，无外部长驻服务；L3=已准备的真实 PostgreSQL 事务/并发；L4=已获授权的现有 HTTPS 应用、浏览器、远端 CI/测试环境。模拟 HTTP 响应或 Mock Repository 不能替代 L3/L4。禁止 Testcontainers/Playwright webServer/测试脚本隐式拉起环境。

共同安全中间状态：新增表和候选不自动激活；未完成依赖的接口不暴露业务流量。共同回退：未部署时仅回退本步骤拥有的代码且保留他人改动；新数据库结构保留，不倒改迁移；已激活回退必须新建激活版本并重验 readiness，不能恢复已撤销凭据、人工禁用或旧角色授权。不得为回滚重新启用 Session/Redis 权威。

提交边界：当前没有提交任务。后续若工作流包含提交，每个独立仓库的逻辑任务最多一个聚焦提交；S27/S28/S31 按列出的仓库子任务分别审查。不开全工作区暂存，不把文档、无关 dirty 文件或未推送祖先顺带发布。

## 6. Ordered Implementation Steps

### S01 — 基线、接口与四个数据库 owner 结构冻结

**Owner:** DOC；**Depends:** 无；**Stage:** P1；**Requirements:** REQ-001、REQ-002、REQ-034、REQ-035。

**文件/顺序：** 只读逐仓库 POM/package.json、所有现存迁移、managed manifest 与安全装配；M 本 Plan 的执行基线/合同附录；N 本任务证据目录中的版本/表约束清单。先确认实际 Boot/Security/SAS/Jakarta/Jackson/JDK 版本，再冻结 §3 URI/DTO、错误/TTL、Manifest 字段、服务 Scope、表约束和全范围审计交付状态。IDP、EDGE、RBAC、META 各自列清表所有者、唯一键、索引、事务边界、并发 claim、保留与加密字段。S11 对纯合同的细化不能漏出此清单。

~~~text
inspect(worktree, resolvedDependencies, migrations)
freeze(authContracts, manifestContract, completeOwnerSchemas, testFixtures)
assert noSessionStore && noCrossOwnerTransaction && allStateHasDatabaseOwner
~~~

**验证：** L0，TEST-001、TEST-002、TEST-053；记录旧迁移 SHA-256，核对每个未来写入/恢复路径都在结构清单。仅 dependency tree/effective POM 不能宣称完成编译或测试。

**完成/中间态/回退：** 四个 owner 的设计可供一次性生成最终迁移，真实环境仍未变；新增表草案不能作为已迁移证明。回退限合同文档。若设计需要扩大已接受范围，回到该变更的审核，不自行纳入远期功能。

### S02 — IdP 完整数据库模型与协议事实 Repository

**Owner:** I；**Depends:** S01；**Stage:** P1；**Requirements:** REQ-004、REQ-006、REQ-008、REQ-032、REQ-034。

**文件/顺序：** N IA/RES/db/egon-mp/`V20261023_001__stateless_oauth_state.sql`；M 同目录 `repository-manifest.json` 和现有迁移/readiness 装配；M IA/J/oauth、token、audit 的现有 PO/Mapper/Repository；N 对应 `OAuthInteraction`、`RefreshOperation`、`AuditReceipt` 等领域模型。按 S01 清单一次创建所有必要结构，复用现有身份/授权表，不建立并行用户库。随后实现摘要、加密载荷、一次性消费、乐观版本、claim 和终态查询；本步骤即在 IA/pom.xml 加入无自动启动的 `idp-stateless-postgresql-it` profile，后续 IT 逐步加入。

~~~sql
UPDATE oauth_interaction SET state = 'CONSUMED', version = version + 1
 WHERE id = :id AND realm = :trustedRealm AND version = :expected
   AND state = 'PENDING' AND expires_at > :now;
-- affectedRows 必须为 1；令牌事实、消费与 Outbox 在同一业务事务完成。
~~~

**验证：** N `IdpStatelessSchemaContractTest`、`IdpOAuthStatePostgresqlIT`；L0/L1 验 SQL/manifest/映射；L3 验真实唯一性、回滚、双连接消费、租约恢复和历史 SQL checksum（TEST-005、008、011、012、053）。

**完成/中间态/回退：** Repository 可验证，尚不替换运行入口；L3 缺环境标待验。代码回退不删除表、不改新旧迁移，不导入旧本地登录数据。

### S03 — IdP 数据库安全状态与持久审计终止接口

**Owner:** I；**Depends:** S02；**Stage:** P1；**Requirements:** REQ-004、REQ-007、REQ-009、REQ-032。

**文件/顺序：** M IA/J/token/service/impl/`TokenRevocationServiceImpl`、`OAuthSecurityProjectionComponent`；M audit/service/impl/`OAuthAuditConsumer`、audit/support/outbox/`OAuthAuditOutboxDeliveryHandler` 及 ResourceServer 状态服务；N AUTH-07 状态/审计 Controller、SQL inbox/receipt Repository。先实现同库撤销/版本原子更新，再实现审计事件去重、payload 摘要冲突、worker claim/失败终态和 durable receipt；最后接收内部调用。

~~~java
verifiedService = verifyServiceLocally(jwt, requiredAudience, requiredScope);
transaction(() -> { checkTargetBinding(verifiedService, request); persistOrMatch(event); });
return receiptFromCommittedDatabase(); // 禁止 Redis 已接受或内存已排队就确认
~~~

**验证：** N `IdentitySecurityStateEndpointTest`、`IdentityAuditReceiptPostgresqlIT`；适配 `TokenRevocationServiceTest`、`OAuthAuditOutboxDeliveryHandlerTest`。验证禁止冒充 USER、重入不递归、重复事件幂等、回滚无回执、跨 scope 拒绝、双 worker 单次落库、DB 故障拒绝（TEST-005、010、014、039）。

**完成/中间态/回退：** 数据库提交是撤销/审计事实成立点；不能继续依赖投影到 Redis 后标 APPLIED。内部端点只对明确服务身份开放，尚未切换全部调用端；回退时禁用未完成入口。

### S04 — IdP 无 Session 登录、认证 JWT 与 OAuth 交互

**Owner:** I；**Depends:** S03；**Stage:** P1；**Requirements:** REQ-003、REQ-005、REQ-006、REQ-009。

**文件/顺序：** M IA/J/oauth/config/`AuthorizationServerConfiguration`、support/security/`IdpSecurityConfig`、oauth/controller/`TenantLoginController`、`OAuthConsentController`、oauth/controller/filter/`TenantLoginAuthenticationFilter`；N 同层 SQL 交互适配、Authn JWT 验证/签发、无 Session CSRF 组件。移除 Session RequestCache/SecurityContext/CSRF/认证成功策略，先验证可信 issuer/Client/回调再创建短期交互；登录成功写 Authn JWT 后恢复单次 authorize，Consent 按交互+已验证身份处理。

~~~java
interaction = requirePendingInteraction(trustedRealm, browserBinding, csrfProof);
authentication = authenticateLocalCredentials(request); // 不签业务 Access
authnJwt = issueAuthenticationJwt(authentication, fixedAuthTime, absoluteExpiry);
continueAuthorizationOnce(interaction, authnJwt);
~~~

**验证：** N `StatelessIdpSecurityChainTest`、`AuthenticationJwtPurposeTest`、`OAuthInteractionBindingTest`；保留并适配 `OAuthConsentRoundTripTest`。使用实际过滤器/Converter/Provider，验证无 Session Cookie/创建、login CSRF、JWT 交叉用途、错误 issuer/aud、过期/重放/篡改事务（TEST-003、004、006、007、008）。

**完成/中间态/回退：** 登录与 Consent 不以 `STATELESS` 一行配置代替完整链验证；未完成 Token/EDGE 切换前不开放业务流量。回退不恢复旧 Session 作为可选模式。

### S05 — Code、CC、Refresh、Consent 与退出的原子生命周期

**Owner:** I；**Depends:** S04；**Stage:** P1；**Requirements:** REQ-006、REQ-007、REQ-008、REQ-009、REQ-032。

**文件/顺序：** M IA/J/oauth 的现有 SAS service/Converter/Provider、token/repository 与撤销服务；N 当前 SSO 退出/受限改密事务适配。先使 Code 消费、令牌签名/落库和 Outbox 不产生半签发，再实现 Refresh 代际原子切换、固定绝对期限、重放关闭、Consent 缩减与身份新鲜度；接入 CC 独立 SERVICE 以及当前应用/当前 SSO/全部账号三种撤销范围。

~~~java
transaction(() -> {
  requireActiveGrantAndGeneration(expectedGeneration);
  tokens = signWithinApprovedScopeAndPurpose();
  consumeCredentialAndSaveNextGeneration(tokens); appendOutbox();
}); // 只有提交成功才返回 Token 响应
~~~

**验证：** N `OAuthNativeGrantFlowTest`、`OAuthCodeRefreshConcurrencyIT`、`SsoRevocationScopeIT`；实际 SAS 链验证 CC 无 USER/ID/Refresh、Scope 不扩张、PASSWORD 不伪装 STRONG、复制旧 JWT 被撤销、签名/保存失败回滚（TEST-008–015）。

**完成/中间态/回退：** 原生 Code/CC/Refresh 可独立验收，HTTP 返回成功必须对应已提交事实；网络结果未知按拒绝/重新认证处理。授权被关闭后不可由代码回退复活。

### S06 — Starter 与网关读取改用数据库权威端口

**Owner:** I；**Depends:** S03、S05；**Stage:** P1；**Requirements:** REQ-003、REQ-004、REQ-007、REQ-009、REQ-032、REQ-033。

**文件/顺序：** M IS/J/autoconfigure/`IdpStarterAutoConfiguration`、`IdpSecurityObservationAutoConfiguration`、对应 Readiness/Properties；M audit/`TokenUsageAuditComponent`、client/`IdpServiceOAuth2Client`；替换 security/impl/`RedisOAuthRevocationReader` 与 state/`RedisIdentityOAuthClientStateReader`、`RedisIdentityResourceServerStateReader`。先接 AUTH-07 的有界服务客户端与本地 owner 适配，再切 Servlet/Reactive 装配，最后移除磁盘 spool、Redis Stream/receipt bucket/状态投影配置与旧测试契约。

~~~java
proof = verifyAccessJwt(request);
state = authoritativeStateClient.resolve(serviceCredential, proof, fixedResource);
requireActiveVersions(state, proof); requireDurableAuditReceipt(decisionEvent);
continueProtectedRequest();
~~~

**验证：** 改造 `IdpStarterAutoConfigurationTest`、`TokenUsageAuditComponentTest`、`IdpSecurityObservationAutoConfigurationTest`；N `DatabaseSecurityStateClientTest`、`ReactiveIdentityStateAdapterTest`。验证 401/403/503、超时/错误回执不放行、终止接口不递归审计、Redis/文件缺失不触发旧回退（TEST-003、005、010、014、039）。

**完成/中间态/回退：** 写端和读端同时以 SQL 为权威；指标/JWKS 非权威缓存可保留。`RedisRefreshTokenStore` 必须先查 Bean/调用链确认无用再删除。已有 spool 文件不自动清理。未接入新端口的 host 视为未完成，不回退旧 Redis 安全态。

### S07 — EDGE 的短期 SQL 事务与恢复基础

**Owner:** Y（E 模块）；**Depends:** S01；**Stage:** P1；**Requirements:** REQ-003、REQ-004、REQ-006、REQ-008、REQ-034。

**文件/顺序：** N E/RES/db/migration/`V1__edge_oauth_state.sql`、E/J/service/repository 的 SQL Transaction/Refresh/LogoutIntent Repository；M E/pom.xml、config/`EdgeOAuthProperties`、application 配置；N SQL owner/readiness 装配及 `edge-oauth-postgresql-it` profile。按冻结结构一次建表，复用工作区已有 JDBC/Flyway 能力，仅添加本模块实际必要依赖；不引入新的 R2DBC 栈。阻塞 JDBC 必须隔离到有界调度器，不阻塞 Netty event loop。

~~~java
Mono.fromCallable(() -> sqlStore.claim(operation, expectedGeneration, deadline))
    .subscribeOn(databaseScheduler); // 独立有界执行，事务完整留在同步调用内
~~~

**验证：** N `EdgeOAuthSchemaContractTest`、`EdgeOAuthStatePostgresqlIT`、`EdgeDatabaseSchedulingTest`；验证短 TTL、加密 verifier、并发 claim、租约终止、故障恢复和无长期 Token 提取表（TEST-004、005、008、012、053）。

**完成/中间态/回退：** E 只拥有协议事务/协调事实，不共享写入 IdP 内部表；新增结构未接业务。缺数据库时 readiness 失败；不启用 Redis 作为兼容存储。

### S08 — EDGE 无 Session OAuth Client、Cookie、刷新和退出

**Owner:** Y（E 模块）；**Depends:** S05、S06、S07；**Stage:** P1；**Requirements:** REQ-003、REQ-005、REQ-006、REQ-008、REQ-009、REQ-033。

**文件/顺序：** M E/J/config/`EdgeSecurityConfiguration`、filter/`TrustedIdentityHeaderFilter`、`EdgeResourceAuthorizationGatewayFilterFactory`；替换 service/impl/`EdgeAuthorizedClientRepository`、`EdgeSingleFlightAuthorizedClientManager`、`EdgeSessionBindingComponent`、`RedissonEdgeLogoutIntentStore` 与 controller/`EdgeSessionController`；N `EdgeIdentityController`、`EdgeOAuthTransactionRepository`、`EdgeRefreshOperationService`。移除 `EdgeSessionRedisConfiguration`/Serializer、Session BO/DTO 和 spring-session 依赖；接入 §3 路由及 Cookie 模式，剥离代理 Cookie/伪造身份 Header。

~~~text
claim generation → IN_PROGRESS → 至多一次提交旧 Refresh
成功并确认数据库有效 → SUCCEEDED → 仅获胜响应写新 Cookie
竞争/重复查询 → 只返回操作状态；不重放、不返回凭据、不清理赢家 Cookie
未知/租约过期 → CLOSED + 持久撤销意图 → 要求重新认证
~~~

**验证：** 改造 `EdgeLoginContractTest`；N `StatelessEdgeSecurityChainTest`、`EdgeRefreshRaceIT`、`EdgeCookieTransportTest`。覆盖多 Resource、Cookie/Bearer 隔离、Access 过期仍能获取刷新 CSRF、请求/响应丢失、乱序 Set-Cookie、退出/刷新/账号切换竞争（TEST-003–009、012、014、015）。

**完成/中间态/回退：** 删除旧 `/bff/session` 语义；旧身份关闭后迟到 Cookie 不能恢复旧授权。不能把数据库 AuthorizedClient token vault 改名后继续使用；部署切换失败关闭入口并重登录，不恢复旧 Session。

### S09 — Shared SDK 的新身份 transport

**Owner:** SDK；**Depends:** S08；**Stage:** P1；**Requirements:** REQ-005、REQ-006、REQ-009、REQ-031、REQ-033。

**文件/顺序：** M SH/src/auth/`gatewayAuthClient.ts` 及测试、src/api/`httpClient.ts`、公开 exports；M RE/src/client/`Rbac3ApiClient.ts`；N 必要的 `authRequestContext.ts` 与 DTO。先生成/对齐 §3 合同，再实现 bootstrap、显式 refresh、当前应用/SSO 退出；所有凭据通过 Cookie，JS 只持最小身份/版本和短期 CSRF Proof。请求取消与代际切换使用身份/授权事实版本，不继续用服务器 Session 代际语义。

~~~typescript
const generation = identityEpoch.current;
const result = await loadIdentity({ credentials: 'include', signal });
if (generation !== identityEpoch.current) return; // 丢弃切换前响应
applyIdentity(result); // 无 Token 持久化；无写操作自动重放
~~~

**验证：** `gatewayAuthClient.test`、`httpClient.test` 与 N `authRequestContext.test`；验证 URI、CSRF、401/403/503 分流、账号切换/退出的迟到响应和显式重试。权限视图此时只能消费 S20 的冻结合同，不能用空集合或本地 resourceId 兜底（TEST-007、015、045）。

**完成/中间态/回退：** SDK transport 源码可打包，六应用尚未全部接入；旧新 API 不双轨自动探测。回退只回退未发布源码，实际应用继续受阶段门禁限制。

### S10 — P1 身份基础出阶段核验

**Owner:** I / Y / SDK 各自证据；**Depends:** S02–S09；**Stage:** P1；**Requirements:** REQ-002–009、REQ-032、REQ-035。

**文件/顺序：** M 各 owner 测试 profile/验证说明，仅在当前测试无法显式连接外部环境时增加对应独立 profile；N 本任务 P1 证据索引。先跑定向 L0/L1，再原生安全链 L2，最后在已提供环境跑 L3；双应用 SSO/真实 Cookie 的 L4 可与 S32 合并执行，P1 的 ENV_VERIFIED 在此之前保持待验。

~~~text
SOURCE_READY = 实际编译 + 有效测试数>0 + 无 Session 生效链
DB_VERIFIED = 真实 Code/Refresh/审计/撤销并发和故障测试成功
ENV_VERIFIED = 两应用 SSO + CSRF/Cookie/退出/乱序行为实证
~~~

**验证：** TEST-002–015、TEST-054；报告每个 owner 的实际命令、HEAD、测试数/跳过数、环境和失败归因。检索 Session/Redis 词只是检查辅助，不能误删 MCP 协议会话或以“没有关键词”代替行为验证。

**完成/中间态/回退：** 未满足实际门禁不得宣称 P1 全部完成；可继续纯合同/P2 开发。没有环境时列明缺证据，不自动启动任何进程；该步骤不触发发布。

### S11 — 统一权限合同、Manifest schema 与表达式语义

**Owner:** R；**Depends:** S01；**Stage:** P2；**Requirements:** REQ-010–013、REQ-016、REQ-023、REQ-036。

**文件/顺序：** N RC/J/permission 下 `PermissionRequirement`、`PermissionManifest`、`CatalogScope`、`ActivationDescriptor`、`SourceImportReceipt` 及纯 JDK 注解；N RC/RES/permission-manifest/schema-v1.json 和共享 fixture；M RK/J/decision/`PermissionSetMerger`、`UserAuthorizationSnapshotBuilder`、`FieldPolicyMerger`。先定 ASCII/大小写混淆/长度/数量/引用约束与七类资源，再实现组外 AND、显式 PUBLIC/INTERNAL、独立字段规则与 canonical digest。Java/TS 使用同一正常/负向样例，不各自解释 JSON。

~~~java
boolean allowed(Set<String> effectiveCodes, List<Requirement> groups) {
  requireNonEmptyValidGroups(groups);
  return groups.stream().allMatch(g -> evaluateAllOrAny(g, effectiveCodes));
} // PUBLIC 是显式分类，不能用空 groups 表示；不跳过身份/scope/数据边界
~~~

**验证：** N `PermissionRequirementContractTest`、`PermissionManifestSchemaTest`、`PermissionCanonicalizationTest`；TEST-016、020–022、027、028、040。覆盖合法多角色合并、类型/方法组累加、排序/重复/Unicode/空组、字段 masker 输出类型与源词条引用；实际检查 RC JAR 包含 schema 与共享 fixture，TS 只能从该确定制品提取，不能静默回退到其他仓库源码。

**完成/中间态/回退：** 合同不依赖 Spring、数据库或 React；没有运行授权效果。新增注解是同一合同的一部分，禁止再建一套 Starter 独有语义。

### S12 — Java 编译期权限处理器

**Owner:** R；**Depends:** S11；**Stage:** P2；**Requirements:** REQ-012、REQ-014、REQ-016。

**文件/顺序：** N `R/stellar-enclosure-tianquan-jianshen-processor` 模块、`PermissionManifestProcessor`、processor SPI 注册和 JavaCompiler fixture；M R/pom.xml 模块声明；M RS/J/security/`RBACAPIResource`、`RequiresPermission` 与 field/`RBACFieldResource` 的合同引用。处理器只依赖 RC 和编译器模型，处理编译期常量、继承/组合注解、Spring Mapping 与 DTO 字段；不能反射加载应用类。输出有 producer/build/schema 标识的确定性 fragment，完整模块集合成功后才汇总 FULL。

~~~java
for (Element resource : declaredElements) {
  model = resolveFromCompilerSymbols(resource); // 不 Class.forName，不启动 Spring
  failOnAmbiguousMappingOrDynamicValue(model); collect(model);
}
if (round.processingOver() && !hadError) writeCanonicalFragment();
~~~

**验证：** N `PermissionManifestProcessorTest`、`PermissionProcessorCompletenessTest`；用会在类初始化时抛错/触网的 fixture 证明其未执行；覆盖继承 Mapping、组合注解、重名 Key、分模块缺失、编译失败无 FULL（TEST-023、024、027、028、030）。

**完成/中间态/回退：** 单独模块可构建，实际生产者声明留 S27；annotationProcessorPaths 显式加入并保留 Lombok/MapStruct 等现有处理器，不能用自动发现假装已启用。

### S13 — TS 权限核心、AST 扫描和离线 Manifest CLI

**Owner:** SDK；**Depends:** S11；**Stage:** P2；**Requirements:** REQ-013、REQ-015、REQ-016、REQ-017。

**文件/顺序：** N SH/src/permissions/`definitions.ts`、`evaluateRequirement.ts`、`index.ts` 及测试；M SH 的 exports/package.json/build 配置；N SDK/scripts/`permission-manifest.mjs`、scripts/permissions/`scan-typescript.mjs`、`canonicalize.mjs`、`validate-manifest.mjs`、`prepare-contract.mjs` 与 fixture。本步骤同步实现 §S30 所述固定工具版本/合同摘要的离线准备方式，供 S28 本地 build 使用，不等待在线注册命令。先从固定版本 RC 合同制品提取并校验 schema/fixture，再用已有 TypeScript Compiler API 静态解析 const/import/对象/数组；不 eval、不加载应用模块、不正则猜表达式。

~~~typescript
const declarations = parseRestrictedAst(tsProgram, configuredEntryPoints);
if (hasDynamicExpression || unresolvedImport || missingExpectedModule) fail();
const manifest = canonicalize(validateAgainstPinnedContract(declarations));
write(manifest, { completeness: successfulFullScan ? 'FULL' : 'PARTIAL' });
~~~

**验证：** N `evaluateRequirement.test`、`scan-typescript.test.mjs`、`canonicalize.test.mjs`；Java/TS 共用 fixture 的字节/摘要和真值一致；动态拼接、缺 import、恶意模块执行、空结果、缺模块失败，且不把失败输出当 FULL（TEST-021、025–030）。

**完成/中间态/回退：** `scan/validate` 离线可用；`diff` 的纯比较内核可测试，在线命令尚未开放。生成合同副本为构建产物且有版本/摘要记录，不成为第二手工维护源；纯权限核心不引入 React，扫描器不打进浏览器包。

### S14 — RBAC 完整目录、角色与 Runtime 数据库结构

**Owner:** R；**Depends:** S01、S11；**Stage:** P2；**Requirements:** REQ-004、REQ-010、REQ-011、REQ-017、REQ-018、REQ-020、REQ-029、REQ-034。

**文件/顺序：** N RA/RES/db/migration/`V16__permission_catalog_and_runtime.sql`；M RA/J/config/flyway/`Rbac3FlywayConfiguration` 的必要验证与新实体映射；N registration/catalog、grant/rolepermission、runtime 的 Repository/PO。严格按 S01 冻结清单一次包含 S15/S16/S19/S20 的全部结构；保留已有 Outbox 的独立 history，不挪动 B14/V15。

~~~sql
-- 领域约束示意；实际列名沿用本仓库命名
UNIQUE (tenant_id, business_code, application_code, namespace_code, environment);
UNIQUE (catalog_scope_id, registration_key);
UNIQUE (catalog_scope_id, permission_code);
UNIQUE (catalog_scope_id, producer_id, producer_version);
-- role、receipt、activation 与 resource 引用均有同 scope 约束。
~~~

**验证：** N `PermissionCatalogMigrationIT`、`PermissionCatalogPostgresqlIT`；真实 PostgreSQL 检查 FK/唯一约束、大小写冲突、ID 字符串返回、跨 scope 写入失败、已有脚本不变（TEST-016、017、029–032、053）。当前仅验证注解/校验和的旧 IT 不算真实 DB 证据。

**完成/中间态/回退：** 新表和映射完整，运行授权尚未改读；新增迁移从创建起不可追加字段。无真实 DB 时源码可继续，不能标 DB_VERIFIED。

### S15 — Manifest 计划、注册、差异、所有权与 Outbox

**Owner:** R；**Depends:** S06、S12、S13、S14；**Stage:** P2；**Requirements:** REQ-010、REQ-016–019、REQ-022、REQ-025。

**文件/顺序：** M RA/J/registration/ci/service/`CiResourceRegistrationService`、`JpaCiResourceRegistrationStore`，authorization/resource/service/`GlobalResourceCatalogService`；复用 authorization/runtime/repository/outbox/`TransactionalOutboxAuthorizationEventPublisher`；N `PermissionManifestPlanService`、`PermissionManifestRegistrationService`、API-001–003 Controller/DTO/Repository。先校验机器身份绑定目标/producer，再生成不可变 plan/Diff，再 CAS 注册候选与原回执并同事务写 Outbox。

~~~java
transaction(() -> {
  requireTrustedOwnerAndMatchingPlan(scope, producer, digests, expectedRevisions);
  if (operationExists) return requireSamePayloadAndReturnOriginalReceipt();
  candidate = saveImmutableVersionAndStableIds(); saveReceipt(candidate); appendSourceImportOutbox();
}); // 此处不切 active、不改角色、不发布人工翻译
~~~

**验证：** N `PermissionManifestRegistrationTest`、`PermissionRegistrationPostgresqlIT`、`PermissionManifestDiffTest`；同 operation 同摘要原样返回 ID/计数、异内容 409、双流水线 CAS、FULL 所有权隔离、缺席只影响候选、失败/PARTIAL/空扫描不得推导退役。Diff 必须展示新资源绑定旧权限、ALL→ANY、PUBLIC 化和字段放宽（TEST-016、017、027–033、038、039、043）。

**完成/中间态/回退：** 候选可注册且明确 metadata pending；不能用 200/已保存宣称已生效。旧注册入口在 S27 迁移生产者后删除，过渡构建不允许同时对同 scope 写入两套协议。

### S16 — 角色直接授予权限字符及治理命令

**Owner:** R；**Depends:** S15；**Stage:** P2；**Requirements:** REQ-011、REQ-013、REQ-022、REQ-033、REQ-036。

**文件/顺序：** N RA/J/authorization/grant/rolepermission 的 Service/Repository/Controller；替换 grant/roleresource/`RoleResourceGrantService` 及其 API；M runtime/activation/repository/jpa/`JpaRoleActivationFactRepository`，删除读取 `role_resource_grant + resource_api_binding` 并集的事实来源。实现 API-007/012：同 scope 字符全集、expectedVersion、角色约束、显式停用/退役/所有权转移；角色变化与 authVersion/Outbox 同事务。

~~~java
transaction(() -> {
  requireAdminPermissionAndSameScope(role, requestedCodes);
  validateKnownEnabledCodesAndRoleConstraints(); replaceRolePermissions(expectedVersion);
  advanceAuthorizationVersion(); appendSnapshotRebuildOutbox();
});
~~~

**验证：** N `RolePermissionGrantTest`、`RolePermissionGrantPostgresqlIT`；旧 resourceIds 请求拒绝、CI 不能授予角色、新 permissionCode 默认没有角色获授予、多角色约束与合并、转移不改变同 scope 资源 ID、CI 不恢复人工禁用（TEST-018、019、022、038、039）。新资源引用已授予的旧字符会扩大既有持有者的能力，必须进入 Diff 与激活资格判断；不能误断言所有新资源都无人可访问。

**完成/中间态/回退：** 只有 permissionCode 是角色资源能力授予源；已有用户角色/激活角色/数据范围约束保留并适配，不重新引入手工字段策略与代码声明竞争。Runtime 尚未接好时不放行管理后产生的业务流量。

### S17 — Tianshu 来源/翻译三层模型与完整持久化路由

**Owner:** M；**Depends:** S01、S11；**Stage:** P2；**Requirements:** REQ-004、REQ-023、REQ-024、REQ-034、REQ-036。

**文件/顺序：** N MA/RES/db/egon-mp/`V20261023_001__tianshu_permission_metadata.sql`；M `repository-manifest.json`、MA/RES/`egon-tianshu-persistence.yml`、MA/J/config/`DdcDatabaseReadyValidator`、migration/`DdcPersistenceMigrationCli`；N SourceVersion/ResourceMetadataProjection/SourceMessage/TranslationDraft/PublishedOverride/ImportReceipt/CatalogActivationProjection/SourceImportGrant 的现有风格 PO/BO/Mapper/Repo。逐表配置 STANDARD_TENANT_ID 路由、约束与 readiness；人工层 revision 与代码源版本完全分离。本步骤即在 MA/pom.xml 加入 `tianshu-permission-metadata-it` PostgreSQL-only profile，S18/S21 的 IT 随实现纳入，不等 S32 才建立执行入口。

~~~text
完整新 schema → manifest/table routing → column/index/constraint readiness
sourceVersion 不可变；draft 可 CAS 编辑；publishedOverride 独立发布
activationDescriptorProjection 只缓存确定版本，不拥有 active 指针
~~~

**验证：** M `DdcTianshuDdlContractTest`；N `DdcPermissionMetadataPersistenceIT`。检查 tenant 路由、路由指纹、全表 readiness、源/草稿/发布版本独立、历史 SQL 不变（TEST-040–042、053）。

**完成/中间态/回退：** 新清洁环境走 initialize→validate。当前 `DdcI18nTopologyUpgrade` 硬编码旧版本列表，必须显式保持历史路径或拒绝用于新 manifest；不能沿用 `upgrade-i18n` 跳过新表/指纹验证，也不把旧脚本当线上迁移需求。代码回退保留数据库结构。

### S18 — Tianshu SERVICE 来源导入与不可变回执

**Owner:** M；**Depends:** S06、S17；**Stage:** P2；**Requirements:** REQ-007、REQ-022–025、REQ-032、REQ-036。

**文件/顺序：** N MA/J/controller/i18n/`DdcI18nSourceImportController`、service/i18n/`DdcI18nSourceImportService`；M security/management/`DdcAdminSecurityConfiguration`、security/tenancy/`DdcTenantContextFilter`、service/i18n/`DdcI18nScopeValidator`。为 API-009/010 建 SERVICE 专用受权入口，保留 USER 翻译入口的独立授权；从已验证主体取 tenant/target，禁止伪造 Rbac3UserDetails 或把 source-import 转发到人工 replaceDraft/publish。

~~~java
transaction(() -> {
  requireServiceImportGrantAndExactTarget();
  requireImmutableSourceOrSameDigest(); saveResourceIndexAndMessages();
  return persistImportReceipt(scope, producer, sourceVersion, allDigests);
}); // 不增加人工 draft/published revision
~~~

**验证：** N `DdcI18nSourceImportServiceTest`、`DdcI18nSourceImportSecurityTest`、`DdcI18nImportConcurrencyIT`；重复/乱序、冲突内容、跨 namespace/producer、USER/SERVICE 混淆、人工草稿不变、DB 回滚无回执（TEST-038–043）。

**完成/中间态/回退：** 只保存候选来源，无运行 bundle 激活；服务身份可在 S20 的 USER Runtime 上线前工作，但仍必须通过 S06 的身份/数据库状态验证及 §3.3 的 META 数据库 import grant 校验。测试先按 B0 建立 scope/binding/grant，再导入；不能绕过校验创建任意目标。真实首次执行同样先完成 B0。

### S19 — 回执确认、部署资格、激活集合与唯一描述符

**Owner:** R；**Depends:** S15、S18；**Stage:** P2；**Requirements:** REQ-018、REQ-020、REQ-025、REQ-030、REQ-036。

**文件/顺序：** N RA/J/registration 的 Outbox handler/receipt matcher；N activation 的 `PermissionCatalogActivationService`、`DeploymentQualificationRepository`、API-004–006 Controller。先按完整目标、sourceVersion 和三个摘要匹配 Tianshu 收据推进 metadataReady；再校验完整 producer 集合、引用闭包、受信制品证明和 pre-activation readiness；最后本地 CAS 切换唯一 active pointer、推进 policyVersion/fence 并写审计/Outbox。

~~~java
transaction(() -> {
  requireAllProducersReadyAndMetadataReceiptsMatched();
  requireTrustedArtifactsAndPreActivationReadiness();
  next = insertImmutableActivationSet(completeProducerVersions);
  casActivePointer(expectedActiveRevision, next); advancePolicyVersion();
});
~~~

**验证：** N `SourceImportReceiptContractTest`、`PermissionCatalogActivationPostgresqlIT`、`ActivationDescriptorSecurityTest`；旧/错目标/错摘要回执无效、旧流水线 CAS 失败、候选不生效、旧 producer 可复用、回滚新序号不复活停用/角色、任意 Header 不能冒充部署证明（TEST-032、034、035、043、044、051）。

**完成/中间态/回退：** descriptor 按 scope/version 不可变可读；Tianshu 只能使用此描述符。pre-activation 只验版本/组件/连接/策略装载，不提前要求新业务请求成功；实际业务验收在激活后执行。提交前失败保留旧 active；提交结果未知先按原 operationId 查询回执及当前指针。确认已提交后若需回退，创建新激活序号并重验部署资格、人工禁用与当前角色事实，不跨库回滚人工翻译。

### S20 — PostgreSQL 授权快照、fence 与统一 Runtime

**Owner:** R；**Depends:** S06、S16、S19；**Stage:** P2 基础 / P3 执行前置；**Requirements:** REQ-004、REQ-011、REQ-013、REQ-027、REQ-029、REQ-030、REQ-032。

**文件/顺序：** 替换 RA/J/authorization/runtime/repository/redis/`RedisAuthorizationRuntimeRepository`、`RedisProjectionCheckpointRepository`；M `SystemAuthorizationSnapshotService`、`RuntimeSnapshotRebuildService`、`AuthorizationPublicationGuardService`、config/runtime/`Rbac3ApplicationConfiguration`；N SQL snapshot/head/fence/claim Repository 和 AUTH-07 Runtime Controller；M RS 的 snapshot loader/fence reader。先从新角色字符事实构建快照，再同事务发布版本/head/fence；读取时校验身份、target、有效角色、策略摘要及到期。

~~~java
snapshot = database.readConsistentAuthorizationState(verifiedIdentity, fixedScope);
require(snapshot.ready && snapshot.authVersion == authority.authVersion);
require(snapshot.catalogVersion == active.version);
entry = trustedDescriptor.requireProducer(localProducerId, localProducerVersion);
require(localPolicyDigest == entry.policyDigest && localManifestDigest == entry.manifestDigest);
requireDeploymentArtifactMatchesTrustedProof();
return boundedPermissionView(snapshot); // 未就绪、过期、错版或 DB 不可用均拒绝
~~~

**验证：** N `AuthorizationRuntimePostgresqlIT`、`AuthorizationFenceTest`、`RuntimeProofBindingTest`；真实并发撤权/重建/发布、坏快照不成为 head、伪造用户 Header、SERVICE 代取权限越界、旧二进制错 digest 拒绝（TEST-005、022、038、044、046、050、051）。

**完成/中间态/回退：** 读写端均迁至数据库；不保留 Redis snapshot/checkpoint 作为故障宽限。仅承诺 Spec 定义的鉴权点一致性；同库业务可在事务中复验 fence，跨库不能声称全局原子撤权。后续 Tianshu 管理和 SDK 直接消费此合同。

### S21 — Tianshu 描述符、Bundle、人工翻译与资源索引 API

**Owner:** M；**Depends:** S18、S19、S20；**Stage:** P2；**Requirements:** REQ-023–025、REQ-031、REQ-032、REQ-036。

**文件/顺序：** N MA/J/service/i18n/`DdcCatalogActivationClient`、`DdcI18nBundleAssembler`、`DdcResourceMetadataService` 和对应 Controller；M `DdcI18nPageService`、`DdcAdminUiI18nService`、现有 Catalog、`DdcI18nBundleResult`、Draft/Publish Command 与安全装配。先经受认证 API-006 获取指定版本 descriptor 并落只读投影，再精确选择 producer/sourceVersion 的 Key 域，最后合成人工已发布覆盖并提供资源索引/人工编辑 API。USER 管理入口使用 S20 Runtime；机器导入继续使用独立 Scope。

~~~text
requested locale: compatible published override → selected source
default locale: compatible published override → selected source → key
每个 key 先 page 再 common；draft 不参与运行；已移除 source key 不复活
cache = full scope + catalogVersion + page + locale + publishedOverrideRevision/ETag
~~~

**验证：** N `DdcI18nBundleAssemblerTest`、`DdcCatalogActivationClientTest`、`DdcI18nDraftPublishIT`、`DdcResourceMetadataServiceTest`。验证 fallback 逐 key、占位符兼容、回滚旧 source、人工作品不被 CI 覆盖、仅发布翻译也能刷新缓存、错误 descriptor 拒绝、安全展示降级不改变权限（TEST-040–045、052）。

**完成/中间态/回退：** 旧 `/admin/initialize` 不再自动发布代码默认文本；内置目录转标准 producer 留 S27。Tianshu 没有“自己选最新”的指针，索引中的表达式只读。回退代码不回滚人工 draft/published 数据。

### S22 — React 权限 Guard、字段体验与版本缓存

**Owner:** SDK；**Depends:** S09、S13、S20、S21；**Stage:** P2 基础 / P3 使用；**Requirements:** REQ-013、REQ-015、REQ-026、REQ-028、REQ-031。

**文件/顺序：** M SH/src/hooks/`usePermission.ts`、src/i18n/`pageI18n.ts`；N SH/src/components/`PermissionGate.tsx`、permissions/`usePermissionSnapshot.ts`；M RE/src/types.ts、provider/`Rbac3Provider.tsx`、`rbac3StateMachine.ts`、hooks/`usePermission.ts`、guards/`PermissionGuard.tsx`、`ActionGuard.tsx`、`FieldGuard.tsx`、registry/`FrontendResourceRegistry.ts`；同时 M RE/package.json、vite.config.ts external、SDK/package-lock.json 和根 build 顺序。先建立 RE→SH 真实依赖并按 SH→RE 构建，再统一纯函数/有版本快照/Guard/字段状态，最后更新语言缓存；不复制求值器。本步骤即产出可安装 tarball，不等 S29 才首次打包。

~~~typescript
if (!snapshot || snapshot.expired || !sameIdentityScopeAndVersions(snapshot, current)) return DENY;
return evaluateRequirement(snapshot.permissionCodes, declaredRequirement);
// field: plainRead > maskedRead > omitted；write 单独决定能否编辑/提交
~~~

**验证：** N `PermissionGate.test`、`PermissionSnapshotCache.test`，改造已有 Guard/provider/i18n 测试；修复当前 `ALL([])=true`、去除 `resourceCodes.includes` 替代授权。覆盖加载/失败默认拒绝、401/403 清理、scope/auth/policy/role/expiry/catalog 切换、翻译单独发布与迟到响应（TEST-021、026、045、047、048）。

**完成/中间态/回退：** Guard 只提供 UX，不成为 API 授权依据；不增加通用表单框架。JS 权限快照永远不能作为后端用户证明；旧 resourceId 授予假设不得作为 fallback。

### S23 — RBAC React 权限字符、Manifest 与治理管理页

**Owner:** RW；**Depends:** S16、S19、S22；**Stage:** P2；**Requirements:** REQ-011、REQ-019、REQ-020、REQ-031、REQ-033。

**文件/顺序：** 替换 src/features/role/`RoleResourceGrantPage.tsx` 为 N `RolePermissionGrantPage.tsx`；M `role.api.ts`、`RolePages.test.tsx`、features/permission/`PermissionCatalogPage.tsx`、features/application/`application.api.ts`、`ResourceCatalogPage.tsx`、`FieldDefinitionPage.tsx`、features/`governance.routes.tsx`、app/navigation.ts/router.tsx；N features/registration/`ManifestVersionsPage.tsx`、`ManifestDiffPage.tsx`、`registration.api.ts`。先对齐新 DTO，再实现字符选择/显式授予，最后增加候选、差异、激活、停用/转移及影响预览。

~~~typescript
await replaceRolePermissions(roleId, {
  catalogScopeId, permissionCodes: selectedCodes, expectedVersion,
}); // 不提交 resourceIds；资源关联仅用于解释影响
~~~

**验证：** 先在隔离验证工作区安装 S22 同批 tarball，再运行改造后的角色/权限目录测试、N `ManifestVersionsPage.test`、`ManifestDiffPage.test`；API mock 验实际 payload 和错误状态，组件测试验只读代码规则、扩权 Diff、冲突后重新加载（TEST-018、019、033、034、052）。最终六仓正式锁文件在 S29 统一收敛，不用 alias 代替实包。

**完成/中间态/回退：** 不出现旧角色资源授予页与新字符页并行可写；UI 注册操作不自动给角色赋权。实际 SDK tarball/锁文件联动在 S29 验证，不能以本地 alias 宣称交付完成。

### S24 — Tianshu React 来源对照与资源元数据管理

**Owner:** MW；**Depends:** S21、S22；**Stage:** P2；**Requirements:** REQ-023、REQ-024、REQ-031、REQ-036。

**文件/顺序：** M src/pages/`I18nPage.tsx`、`I18nPageEditor.tsx`、`I18nDraftForm.tsx`、`I18nBundlePreview.tsx`，api/`i18n.ts`、`adminI18n.ts`、`client.ts`，auth/`AuthContext.tsx`、`RouteGuards.tsx`，i18n/`AdminI18nProvider.tsx`、App.tsx；N api/`resourceMetadata.ts`、pages/`ResourceMetadataPage.tsx`。先展示七类资源及 permissionCode/i18nRef/sourceVersion，再提供源默认/草稿/已发布覆盖对照，最后接 CAS 编辑/发布、源变化待复核和占位符冲突。

~~~typescript
const view = await loadResourceMetadata({ scope, catalogVersion, filters });
renderReadonlyPolicy(view.resourceKey, view.requirements, view.sourceVersion);
saveTranslationDraft({ key, locale, expectedDraftRevision, value });
~~~

**验证：** 在隔离验证工作区安装 S22 同批 tarball，运行 N `ResourceMetadataPage.test` 并改造编辑/预览/provider 测试；验证策略不可编辑、未发布草稿不影响运行预览、语言/身份切换不串缓存、CI 导入后人工修订不丢失（TEST-040–045、052）。正式 lock 在 S29 统一验证。

**完成/中间态/回退：** 页面只编辑翻译层；权限/资源停用继续由 RBAC 治理。现有 Playwright 的自动 preview 配置不能用于默认验证，外部环境验收留 S32。

### S25 — P2 合同、候选注册与治理出阶段核验

**Owner:** R / M / SDK / RW / MW 各自证据；**Depends:** S10、S11–S24；**Stage:** P2；**Requirements:** REQ-010–025、REQ-031、REQ-035、REQ-036。

**文件/顺序：** N 跨语言 fixture 结果与 P2 证据索引；M 必要的只读 conformance 检查。依次验证两端扫描确定性、RBAC 同库事务、Outbox→META→回执→READY、角色字符、descriptor/bundle、管理 UI。S10/S25 的 ENV_VERIFIED 未完成时，不阻止独立源码继续，但整体阶段不标完成。

~~~text
candidate(A) 注册 → metadata pending → 匹配回执 → READY
assert active == old && rolePermissions == before && humanTranslations == before
activate(exact set, trusted proof, expected revision) → 新指针与一致 Runtime
~~~

**验证：** TEST-016–044、052–054；同一 fixture 必须经 Java 和 TS 实现，真实 DB 证据必须来自真实 Repository。验证 partial/失败扫描不会触发 retire，Candidate/READY 不等于已部署。

**完成/中间态/回退：** 报告源码、DB、环境三种状态；尚未部署的 UI 或模拟制品证明不算 P3。候选失败仅保留诊断/终态，不改 active 或人工翻译。

### S26 — 后端 API 与字段读写统一强制执行

**Owner:** R；**Depends:** S12、S20；**Stage:** P3；**Requirements:** REQ-012、REQ-013、REQ-027–030。

**文件/顺序：** M RS/J/security/`Rbac3MethodAuthorizationManager`、field/`Rbac3FieldPropertyWriter`、`Rbac3FieldWriteAuthorizationComponent`、相关本地 registry 和 RPC/导出接入端口；N `SubmittedFieldSet` 边界采集和非 Jackson 输出适配。先把执行器绑定编译期 policyDigest/Key，再统一 API ALL/ANY 和类型/方法组；分别实现读视图和写前校验。字段存在性在反序列化边界采集，与实际绑定目标对照，不能从 DTO 的非 null 值倒推。

~~~java
submitted = captureActualBoundFields(jsonTokens, aliases, nestedPaths, arrays);
requireApiPermissionAndScope(); requireAllSubmittedWrites(submitted);
businessWrite(); // 所有项先验证，禁止批次部分写入
return serializeAuthorizedView(result); // 不修改实体；脱敏失败省略/拒绝
~~~

**验证：** N `ApiRequirementEnforcementTest`、`FieldReadPolicyTest`、`SubmittedFieldAuthorizationTest`、`AlternativeEntryAuthorizationTest`；TEST-022、028、046–050。null/PATCH/嵌套/数组/别名/未知字段、数值 masker JSON 类型、导出/下载/RPC/批处理/直接服务调用均有代表性真实路径测试；不仅测一个 serializer helper。

**完成/中间态/回退：** 失败发生在持久化前，不自动删掉未授权字段后继续写。外部路由、Service 和替代输出需要明确接入，扫描登记本身不证明执行覆盖。

### S27 — 当前 Java 生产者声明、执行器和 bootstrap 接入

**Owner:** 下列独立仓库子任务；**Depends:** S06、S12、S15、S19、S21、S26；**Stage:** P3；**Requirements:** REQ-012、REQ-014、REQ-023、REQ-027、REQ-028、REQ-030、REQ-033。

| 子任务 | 文件范围 / 接入内容 |
| --- | --- |
| S27-I / I | IA Controller/Service/公开 DTO 与 IS 依赖；原生 OAuth 端点登记系统元数据，准入仍由原生协议保证；移除旧 Redis/Session 生效配置 |
| S27-R / R | RA 管理/注册/Runtime Controller/DTO，新权限定义与角色治理 API；删除旧 CI Controller、`Rbac3ApplicationCatalogRegistrationCli`、`ResourcePermissionMappingService` 和资源角色链 |
| S27-M / M | MA 的管理 API/DTO/字段及内置多语言目录；`DdcAdminUiI18nService` 默认词条走标准 Manifest 来源，不再特殊发布 |
| S27-Y / Y | E 及已存在各 Gateway 管理入口/DTO/转发鉴权；保留既有流式协议，不新增 AIoT 或重写 MCP 协议状态 |
| S27-A / A | 已存在 Yaoguang 管理 API/DTO/替代读写入口；只做权限声明及统一安全接入 |

**文件/顺序：** 每个子任务 M 对应 pom.xml/compiler annotationProcessorPaths、Controller/DTO/当前安全配置；N 该 producer 的权限定义、metadata 源词条和受管入口清单。先盘点 route/DTO/导出/RPC，再选择 PROTECTED/PUBLIC/INTERNAL，最后用产物与运行入口覆盖对照。七类中的前端资源由 S28 提供；跨端 FIELD 由 Java 定义，React 引用，同一 code 只能一处定义。

~~~text
inventory(existing managed entrypoints) → explicit declarations → compiler manifest
compare(entrypoint inventory, generated resources, enforcement adapters) → 零未解释缺口
~~~

**验证：** 每仓库 N `PermissionProducerCoverageTest` 及最小直接调用负向测试；TEST-020、023、024、028、040、046–049。现有管理员/机器初始化改为显式清洁环境 bootstrap：预设 scope/producer owner/有限 service grant，登记内置权限后由受控一次性管理员初始化分配明确字符；不放通全部权限、不由普通 CI 授予角色。bootstrap 在已授权环境执行，不能作为源码启动副作用。

**完成/中间态/回退：** 每仓库独立记录扫描覆盖、artifact 与依赖版本；运行未激活构建只提供非业务 readiness。不扩大到其他无关领域重构。

### S28 — 六个 React 应用声明与实际组件接入

**Owner:** PW / IW / RW / MW / YW / AW 独立子任务；**Depends:** S13、S22、S23、S24；**Stage:** P3；**Requirements:** REQ-012、REQ-015、REQ-026、REQ-028、REQ-031、REQ-033。

| 子任务 | 现有接入点 |
| --- | --- |
| S28-PW | src/auth/portalAuth.ts、app/PortalLayout.tsx、pages/PortalHomePage.tsx、ChildRoutePage.tsx |
| S28-IW | src/auth/AuthContext.tsx、app/router.tsx 及现有管理页面/动作/字段 |
| S28-RW | src/features/auth/gatewayAuth.ts、AuthenticationShell.tsx、app/navigation.ts、治理路由/页面 |
| S28-MW | src/auth/AuthContext.tsx、RouteGuards.tsx、api/client.ts、资源与翻译页面 |
| S28-YW | src/auth/AuthContext.tsx、workspaceResource.ts、RouteGuards.tsx、app/capabilities.tsx |
| S28-AW | src/auth/AuthContext.tsx、workspaceResource.ts、RouteGuards.tsx、app/capabilities.tsx |

**文件/顺序：** 各应用 N `src/permissions/permissions.ts`、`resources.ts` 和 `permission-manifest.config.json`，M 路由/导航/有权限含义的组件、按钮、表单。先固定稳定 Key 与 definition/reference 所有者，再接共享 Guard 与当前身份 transport，最后用 AST 扫描覆盖实际使用位置。D RW 的 `resourceDefinitions.json`、旧 `report-rbac-resources.mjs` 及禁止 permissionCode/RolePermission 的旧 conformance 规则，用统一 schema/扫描替代。

~~~typescript
export const EDIT_RESOURCE_KEY = 'order.edit';
export const resources = defineResources([/* 使用 EDIT_RESOURCE_KEY 的显式静态声明 */]);
<PermissionGate resourceKey={EDIT_RESOURCE_KEY}>{/* 业务动作 */}</PermissionGate>
// 不手写第二份权限字符串数组；字段仅引用后端定义并显示对应 UX。
~~~

**验证：** 每应用 typecheck、Vitest 和 build；扫描生成 Manifest，与路由/动作/字段清单逐项对照；TEST-020、025、026、045、052。M 六应用 package.json/既有构建入口，使正式 `npm run build` 固定执行 prepare-contract→scan/validate→Vite build，产物内嵌本次标识；不能只有 CI 先扫描、本地 build 仍用旧标识。纯装饰组件可以明确 INTERNAL，不把所有 React 元素机械注册。

**完成/中间态/回退：** 六应用分别报告状态，不能一个应用通过就宣称前端完成；不在源码中存 Token 或接入新框架。实际 npm 包解析统一由 S29 封口。

### S29 — Maven 依赖顺序、SDK 实包与六消费者锁文件

**Owner:** DOC / R / SDK / 六前端的独立构建接入任务；**Depends:** S27、S28；**Stage:** P3；**Requirements:** REQ-002、REQ-014–016、REQ-030、REQ-035。

**文件/顺序：** 按需 M DOC/release/`maven-release-order.json`、scripts/`maven-release-order.py` 与现有 bootstrap 入口，加入 processor 的真实依赖；M SDK/package.json 工作区构建顺序、scripts/`verify-consumers.mjs`、`release/npm-manifest.json`；M 六前端 package.json/package-lock.json。合同 schema/fixture 由 RC 的有版本资源制品交付，SDK prepare-contract 校验版本和摘要后生成工具所需文件，不从远端 latest 漂移读取。来源明确为 RC 成功构建的固定 CI artifact（pipeline/job 标识和摘要）或经同样校验的本地构建产物；不假定尚未发布的 Maven/npm 版本已存在于公共仓库。

~~~text
RC 合同 → RK/processor/RS/RA → IdP/META/Y/Yaoguang 消费者
SH typecheck/test/build → RE typecheck/test/build → npm pack → 六应用安装同批 tarball
消费者 prepare-contract → scan/validate → typecheck/test → Vite build 内嵌本次标识
最终 artifactDigest 与内部 manifest 标识校验
~~~

**验证：** 实际构建/测试报告和 tarball integrity；检查 RE 真实依赖 SH、浏览器 bundle 不包含 TypeScript Compiler/Node fs/注册客户端。`verify-consumers.mjs --phase prepare` 会更新六个 lock 和 release manifest，只在本步骤明确执行后审查；接着 `--phase verify` 检查同一批包。TEST-002、027、035、054。

**完成/中间态/回退：** 不使用 tsconfig 临时 path alias 掩盖未发布 API；本地 pack 不等于 npm/Maven Central 发布，不执行 publish。锁文件只保留本任务所需依赖变动。

### S30 — 统一在线 CLI：diff/sync/status/activate

**Owner:** SDK；**Depends:** S13、S19、S20、S21；**Stage:** P3；**Requirements:** REQ-018、REQ-020–022、REQ-025、REQ-030、REQ-032。

**文件/顺序：** M SDK/scripts/`permission-manifest.mjs`；N scripts/permissions/`registration-client.mjs` 及 HTTP 合同测试，M CLI 使用说明。接已有离线 scan/validate；diff 调 API-001，sync 消费固定 plan/摘要/expected versions，status 按操作查询，activate 只接受受信部署资格与完整 producer 集合。注册不自动激活；本地写入必须明确 `--target test`，服务端仍独立校验目标与身份。

~~~text
scan → validate → diff(planId) → sync(operationId) → status(metadata READY)
deploy externally → verify trusted artifact/readiness → activate(expectedActiveRevision)
未知结果：status 查询原操作；禁止换 operationId 无条件重提/覆盖
~~~

**验证：** N `registration-client.test.mjs`、`cli-contract.test.mjs`；L1 用严格 HTTP fixture 验请求/错误/超时恢复，L3/L4 在 S32 验真实中心。exit code 约定：0=当前命令成功，2=输入/schema 错，3=CAS/所有权冲突，4=认证授权拒绝，5=目标不可用，6=等待超时/仍 pending（附 operationId）。pending 不能打印 completed。dry-run 不发写请求，日志/argv/artifact 不含 Token/Secret（TEST-031、032、036、038、039）。

**完成/中间态/回退：** 机器凭据从现有受控秘密注入机制读取，输出脱敏；无直接数据库注册后门，不授予角色。真实目标未验证时不得称本地/CI 注册已通过。

CLI 分发冻结为固定 commit 的 SDK 工具 checkout：每个消费者保存非秘密 `permission-toolchain.lock.json`，记录 SDK commit、Node 主版本、RC 合同 artifact 引用/版本/摘要和依赖 lock 摘要；本地与 CI 按相同记录准备工具目录，执行 npm ci 并校验合同制品。不得读取浮动 main/latest，且不依赖 `STELLAR_USE_SOURCE_BOOTSTRAP` 开关。不新增第三个 npm 包，也不把注册客户端放进浏览器 bundle。S13 的离线工具首次交付即采用此方式，S30 只扩展其在线子命令。

### S31 — 各仓库 CI 注册、制品证明与受控激活

**Owner:** I / R / M / Y / A / 六前端各一项流水线任务；SDK/DOC 只提供工具校验与依赖支持；**Depends:** S29、S30；**Stage:** P3；**Requirements:** REQ-017–022、REQ-025、REQ-030、REQ-032。

**文件/顺序：** M 每个生产者现有 `.github/workflows/ci.yml`、`.gitlab-ci.yml`、README 和非秘密 target/producer/toolchain lock 配置。沿用 Java 25 与当前 Node 24 基线；Java 流水线新增独立 Node 工具 job，接收 Java 编译 fragment、固定 RC 合同和最终制品记录，按 S30 固定 commit 准备 CLI。前端无论是否启用 source bootstrap，都独立准备相同固定工具。先编译/test/scan/validate，打包后生成 artifactDigest；PR 仅离线校验/展示 Diff，无写凭据。受保护可信分支才取得绑定 scope+producer 的 CC 身份并注册候选，部署完成且 readiness 通过后由受控交付阶段显式激活。

~~~yaml
# 语义顺序，按各仓库现有 CI 语法实现
validate: [compile, unit_tests, scan, schema_check]
package: [embed_policy_manifest_ids, build_artifact, compute_artifact_digest]
register: [trusted_ref_only, diff, sync, await_matching_metadata_receipt]
activate: [deployment_proof, pre_activation_readiness, active_revision_cas]
verify: [post_activation_protected_flows]
~~~

**验证：** actionlint/YAML 结构、离线流水线 fixture、取消/过期流水线/并发版本/失败扫描/未部署不得激活。所有现有生产者都列清完成状态；SDK 不是业务 producer，不向目录注册自身 npm 包。远端运行与秘密配置在 S32 的已授权目标验证，不在本轮修改账号权限（TEST-030、032、034–039、043、051）。

**完成/中间态/回退：** 不因注册成功就标部署成功；未授权目标不可写。前端 artifact 证明来自受信部署管道，不由浏览器 Header 提供。撤销流水线写权限不回滚已确认的目录/人工授权事实。

### S32 — 已启动环境的数据库、浏览器与交付验收

**Owner:** 各 owner 的验证任务；**Depends:** S10、S25、S26–S31；**Stage:** P3；**Requirements:** REQ-002–032、REQ-034–036。

**文件/顺序：** 使用 S02/S07/S14/S17 已建立的 PostgreSQL 测试 profile，按需 M 汇总选择器；N 前端 `playwright.external.config.ts`、验收 fixture 和证据索引；M README/验收清单。测试数据含两个 tenant、namespace、environment、app，每 app 前后端 producer，两用户、多角色、不同服务 Scope 与七类资源。测试仅连接用户已准备的隔离 PG/HTTPS 环境；浏览器和远端注册有对应授权后才运行。external Playwright 配置无 webServer，不能调用会自动起 preview 的默认 e2e。

~~~text
真实 PG 原子性/并发 → 两应用 SSO/CSRF/Cookie/退出 → 直接 API/字段绕过
本地 --target test 与 CI 同产物注册 → metadata READY → 部署资格
激活 → 实际受保护流程 → 复用旧 producer / 回滚新版本 / 人工翻译独立发布
~~~

**验证：** 补齐 TEST-001–054 的所有适用层次；尤其 Code/Refresh 响应丢失、跨节点重放、账号切换、已授权 code 新增资源的扩权 Diff、人工草稿未发布时 CI 导入、只发布翻译、更新前端复用后端、旧构建 policyDigest 错配拒绝、DB 故障无放行。业务失败后执行已定义的新激活回滚，不能修改历史记录伪造成功。

**完成/中间态/回退：** 每项保存脱敏证据、构建版本/target/test counts。没有环境或授权就记录阻塞的具体测试及理由；不自动起环境，不把手工说明或 Mock 当成功。

### S33 — 旧轨道清理、需求核对与交付关闭

**Owner:** 各责任仓库最后的范围审查；**Depends:** S32；**Stage:** P3；**Requirements:** REQ-001、REQ-003、REQ-004、REQ-031–036。

**文件/顺序：** 清理本次已被替代的 Session API/依赖/配置、Redis 安全/审计投影、磁盘 spool 装配、旧角色资源/人工映射、旧前端注册脚本/校验规则及无用 fixture；更新各仓库 README 的新命令、阶段与已验证边界。无关 Session 同名协议类、业务 Redis、既有数据文件不动。旧测试只删除已失效合同，必要安全回归迁移到新链后再移除。

~~~text
Spec 36 REQ/AC ↔ Plan steps ↔ executed test evidence
diff scope / migration checksums / package locks / no secrets / no old authority path
all required evidence complete → delivery complete；否则列明确剩余项
~~~

**验证：** L0 最终 diff/迁移哈希/依赖/旧调用者审查；仅新增清理引起变化的模块补跑相关验证，不无理由重复全量测试。TEST-001、003、005、018、019、039、053、054。

**完成/中间态/回退：** 最终交付只报告已执行证据；不自动启动项目或发布。若 S32 尚缺必要实证，本步骤只能完成源码清理，不能标整个任务完成。

## 7. Validation Commands and Evidence

### 7.1 命令执行前提

本节是实施后的命令合同，**本轮未运行**。新增类、profile、CLI 参数和 external Playwright 配置必须先在相应步骤实现；不能对当前代码直接执行后把“找不到测试/跳过”当通过。Maven 先按真实依赖 DAG 安装本地所需模块，继承当前版本，不临时升级依赖；npm 先准备同批 SDK 包。不得启用服务/容器自启动脚本。

每个 Maven 命令在对应仓库根执行。`-Dsurefire.failIfNoSpecifiedTests=false` 仅让 `-am` 的无匹配上游模块通过；目标模块必须存在所选测试、报告有效用例数 > 0，关键测试不得全部 skipped。只有 test-compile、BUILD SUCCESS 或测试类文件存在均不够。Failsafe 同样检查实际报告与失败/跳过数。

### 7.2 定向 L0–L2 验证

| 责任仓库 | 代表命令 / 对应步骤 |
| --- | --- |
| I | `./mvnw -B -ntp -pl :stellar-enclosure-tianquan-shoubing-admin -am -Dtest='StatelessIdpSecurityChainTest,AuthenticationJwtPurposeTest,OAuthInteractionBindingTest,OAuthNativeGrantFlowTest,IdentitySecurityStateEndpointTest' -Dsurefire.failIfNoSpecifiedTests=false test`（S03–S05） |
| I | `./mvnw -B -ntp -pl :stellar-enclosure-tianquan-shoubing-starter -am -Dtest='IdpStarterAutoConfigurationTest,TokenUsageAuditComponentTest,IdpSecurityObservationAutoConfigurationTest,DatabaseSecurityStateClientTest,ReactiveIdentityStateAdapterTest' -Dsurefire.failIfNoSpecifiedTests=false test`（S06） |
| Y | `./mvnw -B -ntp -pl :stellar-enclosure-yuheng-edge-gateway -am -Dtest='StatelessEdgeSecurityChainTest,EdgeCookieTransportTest,EdgeDatabaseSchedulingTest' -Dsurefire.failIfNoSpecifiedTests=false test`（S07–S08） |
| R | `./mvnw -B -ntp -pl :stellar-enclosure-tianquan-jianshen-core,:stellar-enclosure-tianquan-jianshen-processor -am -Dtest='PermissionRequirementContractTest,PermissionManifestSchemaTest,PermissionCanonicalizationTest,PermissionManifestProcessorTest,PermissionProcessorCompletenessTest' -Dsurefire.failIfNoSpecifiedTests=false test`（S11–S12） |
| R | `./mvnw -B -ntp -pl :stellar-enclosure-tianquan-jianshen-admin,:stellar-enclosure-tianquan-jianshen-starter -am -Dtest='PermissionManifestRegistrationTest,PermissionManifestDiffTest,RolePermissionGrantTest,SourceImportReceiptContractTest,ActivationDescriptorSecurityTest,AuthorizationFenceTest,RuntimeProofBindingTest,ApiRequirementEnforcementTest,FieldReadPolicyTest,SubmittedFieldAuthorizationTest,AlternativeEntryAuthorizationTest' -Dsurefire.failIfNoSpecifiedTests=false test`（S15–S20、S26） |
| M | `./mvnw -B -ntp -pl :stellar-enclosure-tianshu-admin -am -Dtest='DdcTianshuDdlContractTest,DdcI18nSourceImportServiceTest,DdcI18nSourceImportSecurityTest,DdcI18nBundleAssemblerTest,DdcCatalogActivationClientTest,DdcResourceMetadataServiceTest' -Dsurefire.failIfNoSpecifiedTests=false test`（S17–S21） |
| SDK | `node --test scripts/permissions/*.test.mjs`（S13/S30；Node 测试不得访问真实注册目标） |
| 各 Java 生产者 | 在其 owner module 选择 `PermissionProducerCoverageTest` 及对应 Controller/DTO/Service 测试，不运行无关外部 IT（S27） |
| 各 React 应用 | `npm run typecheck`、`npm test`、`npm run build`；另运行已替换的资源覆盖/conformance 检查（S23/S24/S28） |
| 各 CI owner | `actionlint .github/workflows/ci.yml`；使用项目已有 YAML 校验工具检查 `.gitlab-ci.yml`，再对可信 ref/取消/失败条件做离线合同检查（S31） |

SDK 显式顺序如下，不依赖 workspace 字典序或旧 dist：

~~~sh
npm run typecheck --workspace @stellar-enclosure/stellar-enclosure-web-shared
npm run test --workspace @stellar-enclosure/stellar-enclosure-web-shared
npm run build --workspace @stellar-enclosure/stellar-enclosure-web-shared
npm run typecheck --workspace @stellar-enclosure/stellar-enclosure-tianquan-jianshen-react-sdk
npm run test --workspace @stellar-enclosure/stellar-enclosure-tianquan-jianshen-react-sdk
npm run build --workspace @stellar-enclosure/stellar-enclosure-tianquan-jianshen-react-sdk
~~~

S29 使用现有脚本的真实参数；`PAC_CACHE`、`PAC_OUTPUT` 是执行者选择的绝对任务目录，不指向工作区根，不含凭据：

~~~sh
node scripts/verify-consumers.mjs \
  --workspace /Users/mario/SelfProject/Stellar-Enclosure \
  --cache "$PAC_CACHE" --output "$PAC_OUTPUT" --phase prepare
node scripts/verify-consumers.mjs \
  --workspace /Users/mario/SelfProject/Stellar-Enclosure \
  --cache "$PAC_CACHE" --output "$PAC_OUTPUT" --phase verify
~~~

prepare 影响六消费者 lock 与 SDK release manifest，必须检查每仓库 diff。现有脚本默认 offline，缓存缺依赖属于环境准备问题；需要联网时使用其明确的 `--online true` 并记录，不能悄悄改到另一批包。脚本需在 S29 补齐新合同文件、SH→RE 顺序与新增依赖处理后再执行。

### 7.3 L3：真实 PostgreSQL

数据库 URL/用户名/凭据从现有安全配置渠道传入，不写到示例命令、日志或证据。本次新 profile 均为 PostgreSQL-only，显式启用且无容器/Redis/应用启动行为。没有已准备的匹配 schema 和隔离库时不运行。

| Owner | profile / 定向测试命令 |
| --- | --- |
| I | N `idp-stateless-postgresql-it`：`./mvnw -B -ntp -pl :stellar-enclosure-tianquan-shoubing-admin -am -Pidp-stateless-postgresql-it -Dit.test='IdpOAuthStatePostgresqlIT,IdentityAuditReceiptPostgresqlIT,OAuthCodeRefreshConcurrencyIT,SsoRevocationScopeIT' -Dfailsafe.failIfNoSpecifiedTests=false verify` |
| Y/E | N `edge-oauth-postgresql-it`：`./mvnw -B -ntp -pl :stellar-enclosure-yuheng-edge-gateway -am -Pedge-oauth-postgresql-it -Dit.test='EdgeOAuthStatePostgresqlIT,EdgeRefreshRaceIT' -Dfailsafe.failIfNoSpecifiedTests=false verify` |
| R | 现有 `tianquan-jianshen-local-it`，先确认不隐式启动环境：`./mvnw -B -ntp -pl :stellar-enclosure-tianquan-jianshen-admin -am -Ptianquan-jianshen-local-it -Dit.test='PermissionCatalogMigrationIT,PermissionCatalogPostgresqlIT,PermissionRegistrationPostgresqlIT,RolePermissionGrantPostgresqlIT,PermissionCatalogActivationPostgresqlIT,AuthorizationRuntimePostgresqlIT' -Dfailsafe.failIfNoSpecifiedTests=false verify` |
| M | N `tianshu-permission-metadata-it`：`./mvnw -B -ntp -pl :stellar-enclosure-tianshu-admin -am -Ptianshu-permission-metadata-it -Dit.test='DdcPermissionMetadataPersistenceIT,DdcI18nImportConcurrencyIT,DdcI18nDraftPublishIT' -Dfailsafe.failIfNoSpecifiedTests=false verify` |

不借用 Tianshu 含其他 AI/Redis 场景的 `tianshu-ai-persistence-it` 来证明本任务。S02/S07/S14/S17 各 owner 单次完整新迁移分别验证，任何一次失败都记录当前数据库状态；不能用 repair、删库重跑或修改已存在迁移来掩盖失败。

### 7.4 L4：外部环境与注册验收

下面的 CLI 是 S13/S30/S31 需实现并在 README 固定的参数合同；在对应前端/生产者目录运行，CLI 路径通过已固定版本工具配置提供。`${PAC_CLI}`、`${PAC_MANIFEST}`、`${PAC_REPORT}`、`${PAC_PLAN_ID}`、`${PAC_OPERATION_ID}`、`${PAC_ACTIVATION_REQUEST}` 都是非秘密、已验证的任务参数。

~~~sh
node "$PAC_CLI" scan --config permission-manifest.config.json --output "$PAC_MANIFEST"
node "$PAC_CLI" validate --manifest "$PAC_MANIFEST"
node "$PAC_CLI" diff --manifest "$PAC_MANIFEST" --target test --output "$PAC_REPORT"
node "$PAC_CLI" sync --manifest "$PAC_MANIFEST" --target test --plan-id "$PAC_PLAN_ID" --operation-id "$PAC_OPERATION_ID"
node "$PAC_CLI" status --target test --operation-id "$PAC_OPERATION_ID"
node "$PAC_CLI" activate --target test --request "$PAC_ACTIVATION_REQUEST"
~~~

在线 diff 只创建计划/差异、不改运行目录；`--dry-run` 必须完全无写请求，不能包装成已经远端创建 plan 的操作。activate 的 request 包含完整集合、expectedActiveRevision 和可信部署记录引用；不能在 sync 后无条件执行。授权身份/目标由配置与服务端 grant 双重约束，本地禁止默认生产目标。

浏览器仅在用户明确授权、目标已启动且配置无 webServer 后执行：`npx playwright test --config playwright.external.config.ts`。禁止直接使用现有可能自动起 preview 的 `npm run e2e`。测试失败不自动起后端、数据库、Redis 或浏览器调试 GUI。

### 7.5 必须保留的证据

每条证据记录仓库/HEAD、实际命令、工具/依赖版本、时间、测试名称和总数/失败数/跳过数、目标 scope 的非敏感标识、schema/manifest/producer/catalog/artifact 版本、结论和限制。敏感 Cookie、Token、Secret、密码、verifier、用户业务字段不得进入日志、报告或制品。

单元/源码通过、真实数据库通过、浏览器通过、CI 通过和远端注册/激活通过分别记录。未执行标 `NOT_RUN`，环境缺失标 `BLOCKED_ENV`，不能把它们合并为 PASS。实际执行失败先判断是本次变更还是既有环境/依赖问题，报告证据后处理。

## 8. Requirement and Test Traceability

下表 REQ/AC/TEST 均来自唯一有效 Spec。测试编号不表示本轮执行；每个 TEST 在实际证据索引中还须记录所需层次。

| Requirement | Acceptance | Steps | Tests |
| --- | --- | --- | --- |
| REQ-001 | AC-001 | S01、S33 | TEST-001 |
| REQ-002 | AC-002 | S01、S10、S12、S29 | TEST-002 |
| REQ-003 | AC-003 | S04、S06、S08、S10、S33 | TEST-003、TEST-004 |
| REQ-004 | AC-004 | S02、S03、S06、S07、S14、S17、S20 | TEST-005 |
| REQ-005 | AC-005 | S04、S08、S09、S32 | TEST-006、TEST-007 |
| REQ-006 | AC-006 | S02、S04、S05、S07、S08、S32 | TEST-008、TEST-009 |
| REQ-007 | AC-007 | S03、S05、S06、S18、S30 | TEST-010 |
| REQ-008 | AC-008 | S02、S05、S07、S08、S32 | TEST-011、TEST-012、TEST-013 |
| REQ-009 | AC-009 | S03、S05、S06、S08、S09、S32 | TEST-009、TEST-014、TEST-015 |
| REQ-010 | AC-010 | S11、S14、S15、S16 | TEST-016、TEST-017 |
| REQ-011 | AC-011 | S16、S20、S23、S33 | TEST-018、TEST-019 |
| REQ-012 | AC-012 | S11、S12、S26、S27、S28 | TEST-020 |
| REQ-013 | AC-013 | S11、S13、S16、S20、S22、S26 | TEST-021、TEST-022 |
| REQ-014 | AC-014 | S12、S27、S29 | TEST-023、TEST-024 |
| REQ-015 | AC-015 | S13、S22、S28、S29 | TEST-025、TEST-026 |
| REQ-016 | AC-016 | S11、S12、S13、S15、S29 | TEST-027、TEST-028 |
| REQ-017 | AC-017 | S13、S14、S15、S31 | TEST-029、TEST-030 |
| REQ-018 | AC-018 | S14、S15、S19、S30、S31 | TEST-031、TEST-032 |
| REQ-019 | AC-019 | S15、S23、S31 | TEST-033 |
| REQ-020 | AC-020 | S19、S23、S30、S31、S32 | TEST-034、TEST-035 |
| REQ-021 | AC-021 | S30、S31、S32 | TEST-036、TEST-037 |
| REQ-022 | AC-022 | S15、S16、S18、S30、S31 | TEST-038、TEST-039 |
| REQ-023 | AC-023 | S11、S17、S18、S21、S24、S27 | TEST-040 |
| REQ-024 | AC-024 | S17、S18、S21、S24 | TEST-041、TEST-042 |
| REQ-025 | AC-025 | S15、S18、S19、S21、S30、S31 | TEST-043、TEST-044 |
| REQ-026 | AC-026 | S22、S28、S32 | TEST-045 |
| REQ-027 | AC-027 | S20、S26、S27、S32 | TEST-046 |
| REQ-028 | AC-028 | S22、S26、S27、S28、S32 | TEST-047、TEST-048、TEST-049 |
| REQ-029 | AC-029 | S14、S20、S26、S32 | TEST-050 |
| REQ-030 | AC-030 | S19、S20、S26、S27、S29、S31 | TEST-034、TEST-035、TEST-051 |
| REQ-031 | AC-031 | S09、S21、S22、S23、S24、S28 | TEST-045、TEST-052 |
| REQ-032 | AC-032 | S03、S06、S18、S20、S21、S30、S31 | TEST-005、TEST-039、TEST-044 |
| REQ-033 | AC-033 | S06、S08、S16、S23、S27、S28、S33 | TEST-018、TEST-019 |
| REQ-034 | AC-034 | S01、S02、S07、S14、S17、S33 | TEST-053 |
| REQ-035 | AC-035 | S01、S10、S25、S29、S32、S33 | TEST-054 |
| REQ-036 | AC-036 | S11、S16、S18、S19、S21、S24 | TEST-043、TEST-044 |

## 9. Review and Delivery Boundaries

本 Plan 的实施范围与主 Spec 相同。计划允许源码并行和分层验证，不允许以进度为由跳过完整 scope、数据库权威、后端强制、元数据回执或制品匹配。迁移一次定稿、注册候选与激活分离、React 权限体验与后端执行分离，是整个执行顺序的约束。

Plan 已获用户确认，按步骤推进，不重复请求已有授权范围内的普通编辑/测试许可。真实数据库、浏览器、目标部署、凭据配置、注册及发布按已有授权和明确环境执行；不自动启动任何项目或外部服务。

本轮文档验收范围：检查 33 个步骤的依赖无环、36 项 REQ/AC 与 54 个 TEST 的追踪覆盖、现有入口和拟新增文件标识、命令与实际脚本参数一致、文档链接和 Markdown 结构；不是代码构建、数据库迁移或运行验收。

Plan 编写阶段已执行上述结构检查：33 个步骤均具备 owner/依赖/文件顺序/验证/安全中间态；94 条显式依赖均指向前置步骤，无环；36 项 REQ/AC 和 54 个 TEST 无遗漏；Plan 与主 Spec 合计 25 个本地链接有效、46 对围栏闭合，表格列数和 Git 空白检查通过。对照源码完成身份/权限、Tianshu、React/CLI/CI 三组交叉审查，并修正合同 fixture 打包、producer 摘要匹配、提交结果未知、机器导入 grant、冷启动、SDK 实包前置及工具分发顺序。16 个子仓库状态检查只有 DOC 的本轮文档目录未跟踪，其他仓库无工作树改动。

该记录只证明 Plan 编写阶段的文档完整性和源码入口核对；当时未运行 Maven/npm 业务构建测试、SQL、浏览器或远端 CI/注册，没有执行 Git 提交。当前实施验证记录见下节。未使用当前工作区不存在的历史 `validate_plan.py`，不声称通过该工具的 strict 校验。

## 10. Execution Ledger

用户已批准实施；2026-10-25 再次要求继续，三个 subagent 已确认恢复工作。上次额度中断记录保留为历史。**三个阶段均未整体完成，不具备整套运行验收结论。** 后续继续沿既有授权与依赖推进，不需要重新审核已经批准的 Spec/Plan。

[结构化执行记录](../evidence/2026-10-23-jwt-permission-as-code/execution-status.json)保存阶段测试、校验值与剩余工作；[初始基线](../evidence/2026-10-23-jwt-permission-as-code/baseline.json)记录16仓库状态与144个既有SQL校验值；[结构冻结清单](../evidence/2026-10-23-jwt-permission-as-code/schema-freeze.json)记录四个数据库owner设计。

| 步骤 | 当前状态 | 已取得证据与边界 |
| --- | --- | --- |
| S01 | 结构/基线冻结，校验通过 | 16仓库HEAD保持基线；144历史+4新迁移共148个SHA无变化。真实DB未执行 |
| S02–S06 | 源码及离线验证完成 | IdP最终完整Admin488、Core29、RPC1、Starter152通过；祖先安全新增后13项bootstrap定向通过并重验最终JAR。SQL权威/持久审计与原生协议已接入，真实PG/浏览器仍待验收 |
| S07–S08 | 源码及离线验证完成 | Edge39测试通过；SQL/Cookie/CSRF/refresh/revocation/native metadata与最终制品核验通过。PG/多节点/浏览器NOT_RUN |
| S09 | SDK传输完成 | 最终SH78+RE37+Node140共255测试通过；身份代际取消、401/403/503、显式refresh/logout和真实npm实包已验证 |
| S10 | 真实整体门禁未通过 | 已有离线证据；实际PG、两应用SSO、跨节点/响应丢失及重启尚未执行，不能以mock替代 |
| S11 | 共享合同完成 | 纯RC/schema/注解及当前视图/版本/descriptor/qualification合同已用于实际生产者；最新合同模块55测试通过，固定RC JAR五资源摘要复核一致 |
| S12 | 编译与完整制品汇总完成 | processor33与纯build CLI8测试通过；新增SOURCE native dispatcher准确描述动态方法，不执行业务类；9个Java最终JAR均与FULL/三摘要绑定 |
| S13 | AST/离线CLI完成 | 固定RC资源、严格扫描/源码词条/借用FIELD引用/三个摘要/失败清理已验证；正式commit pin受no-commit要求阻断 |
| S14 | 迁移落盘且静态校验通过 | 唯一V16冻结，23表/92语句/15函数及SQL语法/引用静态检查通过；实际PG迁移/事务NOT_RUN |
| S15 | 注册/来源投递源码完成 | 所有权/稳定ID/Diff/CAS/原回执/Outbox与严格SERVICE边界已实现并离线验证，不自动激活或授予角色 |
| S16 | 字符授权与数据范围接入完成 | RolePermission直接code、完整target DataRule、未来grant/禁用约束与治理已实现；RW实际表单对应新合同；真实SQL锁/原子性待验 |
| S17–S18 | META结构及严格来源完成 | 唯一迁移冻结；scope/grant绑定、不可变source/projection/message/receipt及幂等查询实现；已有完整与定向回归，真实PG未运行 |
| S19 | 资格/激活/descriptor源码完成 | 完整producer集合、READY回执、受信qualification、活动revision CAS、禁用/退役/转移与原始操作恢复均实现并测试 |
| S20 | SQL Runtime及实例围栏完成 | 新snapshot/head/fence/rebuild路径、固定artifact/scope绑定已替换旧授权Redis来源；RS112测试通过，普通SERVICE也必须有verified HTTP/RPC proof |
| S21 | 来源与人工翻译独立发布完成 | descriptor/bundle/source-page、人工CAS/不可变publication及有界读取实现；真实SQL guard兼容查询修复。META完整845基线（1Docker skip）+最终24定向/产物复验通过，计数不相加 |
| S22 | SDK授权/字段消费完成 | scope/version/角色代际、请求取消和后端字段投影接入；PUBLIC字段只读，inputBinding与写表达式独立；24-key批次须保持同scope/catalogVersion |
| S23 | RBAC管理前端完成 | 目录/候选/Diff/原操作/激活/治理及角色字符授权、完整target数据范围已接；RW80测试、build/typecheck与170个真实可写FIELD引用对照通过 |
| S24 | META管理前端完成 | 资源/来源页/人工草稿和发布、版本边界接入；MW189测试及构建通过，95个FIELD引用对照通过 |
| S25 | 真实P2门禁未通过 | 跨中心实际DB/注册READY/资格/激活/人工翻译发布与角色授权验收NOT_RUN；源码完成不等于门禁通过 |
| S26 | API/FIELD执行及宿主接入完成 | 真实HTTP与RPC边界、字段/null/unknown/readonly/嵌套/multipart检查完成；真实Boot MVC验证R/M/A/Y实际JSON reader，保留String/byte/stream和内部mapper行为 |
| S27 | 全部Java生产者及显式B0/B1完成 | I/R/M/A与Y五独立宿主共9个FULL，2734 API/FIELD资源；Y非Edge621+4内存transport通过，14真实listener类明确NOT_RUN；初始化无普通启动/CI授予副作用 |
| S28 | 六React生产者及消费接入完成 | PW34/IW62/RW80/MW189/YW169/AW69共603测试通过，全部typecheck/build/最终artifact通过；560个FIELD引用均存在且有write规则 |
| S29 | 本地构建/实包/锁验证完成，生产pin待外部步骤 | Maven70制品依赖顺序、纯processor/CLI、同批npm pack/六锁/offline安装及bundle验证完成；所有工具为LOCAL_UNCOMMITTED，无伪造commit或发布 |
| S30 | 统一在线CLI源码及严格HTTP fixture完成 | diff/sync/status/activate与CI helper、退出码/原operationId/超时恢复/secret-file已实现并纳入Node140；真实中心写入NOT_RUN，LOCAL在凭据/HTTP前拒绝 |
| S31 | 流水线源码/离线验证完成 | 23份GitHub actionlint、12份GitLab YAML、Parent16与六FE54 CI测试通过；受保护人工交付、独立部署proof/原artifact/来源校验完整，远端未执行/未配置 |
| S32 | 安全执行入口已准备，环境验收NOT_RUN | 新增无webServer外部Playwright8场景，类型/收集/禁用gate通过；明确PG profiles、B0/B1、listener和交付命令。未连接真实PG或运行浏览器 |
| S33 | 源码清理与交付记录完成，整体交付未关闭 | 旧Session/授权Redis/资源角色与手工FIELD写主链退场；SQL/HEAD/dirty范围/锁/产物审查完成。S10/S25/S32缺实证，不能标整个任务完成 |

以上为2026-10-26最新源码与离线证据；历史整仓基线和之后的定向复验有重叠，不能将各日志计数相加。最终9个Java制品的字节/SHA、内嵌FULL、无processor/CLI运行依赖与Node合同验证见[Java最终制品记录](../evidence/2026-10-23-jwt-permission-as-code/java-final-artifacts.json)；六前端/SDK见[前端最终记录](../evidence/2026-10-23-jwt-permission-as-code/frontend-final-evidence.json)。

新增初始化修复涵盖私有输入的原路径/real路径祖先控制、既有本地回执与SQL原回执一致性、SERVICE真实proof和真实Boot JSON转换器。所有本次新增迁移创建后均未修改；[148个迁移校验](../evidence/2026-10-23-jwt-permission-as-code/migration-checksums-final.json)与[16仓库HEAD/范围审查](../evidence/2026-10-23-jwt-permission-as-code/repository-scope-final.json)已保存。没有提交、推送、发布或自动启动项目。

后续只在已获准的隔离环境执行[外部验收交接](../evidence/2026-10-23-jwt-permission-as-code/environment-acceptance.md)。用户本轮禁止提交/推送，因此实际SDK固定commit分发门禁保留为未配置；所有LOCAL锁只支持离线验证。真实PostgreSQL、浏览器/SSO、Redis/listeners、远端CI、部署/readiness、注册/READY/qualification/激活均未作为已通过证据。

以下保留早期历史检查点，不代表最新状态：

- 2026-10-25 续接：16仓库HEAD及dirty范围与上次检查点一致；144个历史SQL和3个本次新增迁移SHA均未变化。I续接S03–S06，E续接S08，M续接S18；主agent续接S11注解/S12处理器。未启动项目或外部环境。

- 2026-10-25 续接验证：RC新增注册envelope与共享descriptor canonical方法后53测试通过；Java处理器18测试、Diff7测试、RBAC注册/跨中心投递45测试分别通过。148个历史及本次新增SQL摘要复核无变化。S19来源精确回执推进READY已实现；激活/qualification/S20 Runtime与后续UI/CI尚未完成。
