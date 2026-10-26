# Jianshen OAuth2、IdP 与 SSO 三阶段优化规格

> 本文已被[JWT 无 Session 与 Permission as Code 新版规格](2026-10-23-17-39-jwt-permission-as-code-i18n-design.md)整体替代。本文中的 Session/BFF Session、Redis 安全状态、旧接口兼容和旧资源授权模型保留方案均不再作为实施依据；请审核新版。

| Field | Value |
| --- | --- |
| Document | 2026-10-23-16-17-jianshen-oauth2-idp-sso-convergence.md |
| Template Version | 7；沿用仓库现存 RFC 章节与追踪格式 |
| Status | Superseded；不再作为实施依据 |
| Superseded By | [2026-10-23-17-39-jwt-permission-as-code-i18n-design.md](2026-10-23-17-39-jwt-permission-as-code-i18n-design.md) |
| Type | Architecture / Bugfix / Refactoring |
| Complexity | Complex |
| Complexity Drivers | 多仓库身份边界、SAS 生命周期与真实持久层一致性、Servlet/Reactive 安全链、分布式会话与并发续期、兼容的浏览器登出 |
| Created | 2026-10-23 16:17 Asia/Shanghai |
| Updated | 2026-10-23 16:50 Asia/Shanghai |
| Owner | mario |
| Repository | Stellar-Enclosure-Parent；跨仓库规格的文档归属 |
| Scope | 第一阶段协议与业务契约修正；第二阶段实现结构整理；第三阶段当前应用 SSO 与会话验收 |
| Change Surface | 当前 IdP Admin/Core/Starter、RBAC3 认证强度消费边界、Yuheng Edge、共享认证 SDK 及当前第一方调用方；必要的客户端登出元数据 |
| Affected Chapters | §7–§16 |
| Source Requirement | 用户批准上一轮三阶段优化方案，并要求“按照这三个阶段写 Spec……不包含 AIoT、LDAP 和远期扩展。先不要改代码，Spec 写好后我再审核” |
| Baseline Revision | 2026-10-23 16:50 Asia/Shanghai 交付前只读复核；精确仓库基线见 §2.1 |
| Amends | 审核通过后，仅修订[OAuth/OIDC 主规格](../../history/egon/spec/2026-09-22-17-14-tianquan-multitenant-oauth-oidc-design.md)与[当前代码对齐规格](../../history/egon/spec/2026-10-08-10-18-oauth-current-code-alignment.md)中本文件明确列出的授权生命周期、密码复验强度、标准组件装配和当前门户登出合同 |
| Supersedes | None；不整体替换历史规格，不复活历史实施计划中的扩展范围 |
| Depends On | 现有租户 issuer / Resource Grant / 安全版本 / 撤销 / Outbox / RBAC3 合同；[自身安全规格](../../history/egon/spec/2026-10-10-12-36-tianquan-security-self-hardening.md)未被本文件点名修改的约束 |
| Related Plans | None；本轮不编写实施 Plan，不执行代码、迁移或运行环境操作 |

## 1. Summary

本规格将已获方向批准的方案转成可审核、可测试的合同。只收敛现有 OAuth2、IdP、SSO 的职责与实现，主要授权流程固定为 Authorization Code 与 Client Credentials。用户授权已有的 Refresh Token 是续期机制；不是新增第三条业务授权入口。

顺序固定为：本 Spec 审核 → 另行编写/确认实施 Plan → 按三阶段实施与验证。方案已获批准不等于本 Spec 已获批准。本轮交付只包含本文件，不修改业务代码、历史文档、配置、数据库脚本或依赖文件。

本规格区分“协议框架处理”“领域规则判断”“存储一致性保障”和“客户端会话管理”，复用现有 Spring Authorization Server（SAS）、Spring Security、Spring Session、共享 SDK 与 RBAC3。不得借本次优化重建认证框架。

## 2. Background and Current State

### 2.1 命名、路径和工作树基线

**产品命名以用户本轮确认为准：Jianshen = IdP / 账号 / OAuth2 / SSO，Shoubing = RBAC3。** 本地物理路径仍存在相反的历史命名。为避免实施落错模块，本文件使用以下职责别名；这些别名不是重命名指令。

| 别名 | 当前物理仓库 / 模块 | 基线 HEAD | 本轮读取时状态 |
| --- | --- | --- | --- |
| DOC | Stellar-Enclosure-Parent | c2a3bff | 仅本 Spec 未跟踪 |
| IDP-A | tianquan-shoubing-service / stellar-enclosure-tianquan-shoubing-admin | 49122f8 | 干净 |
| IDP-C | 同仓库 / stellar-enclosure-tianquan-shoubing-core | 同上 | 同上 |
| IDP-S | 同仓库 / stellar-enclosure-tianquan-shoubing-starter | 同上 | 同上 |
| AUTHZ | tianquan-jianshen-service | b2e80d3 | 干净 |
| EDGE | yuheng-service / stellar-enclosure-yuheng-edge-gateway | 7380a48 | 干净 |
| SDK | web-sdk / packages/stellar-enclosure-web-shared | d407317 | 干净 |
| PORTAL | portal | f82568a | 干净 |
| IDP-W | tianquan-shoubing-web | ebb7244 | 干净 |
| AUTHZ-W | tianquan-jianshen-web | 763b54b | 干净 |

目录根为各独立仓库，不把整个 workspace 当成一个 Git 仓库。初读时上述四个仓库存在已有修改；撰写期间这些修改由其他工作提交，本轮未创建提交。交付前已重新确认关键授权生命周期与认证强度证据仍存在，并更新表中 HEAD。实施前必须再次固定源码和依赖基线，保留无关改动。

IDP-A Java 根为 src/main/java/top/egon/cola/platform/tianquan/shoubing/admin；IDP-C/IDP-S 根分别为同一平台前缀下的 core/starter。EDGE Java 根为 src/main/java/top/egon/cola/component/yuheng/edge。下文“模块别名 + Java 相对路径 + 符号”是精确定位，不依据产品名猜测文件路径。

### 2.2 现状证据

| Evidence ID | 当前源码 / 证据 | 已观察事实 | 设计影响 |
| --- | --- | --- | --- |
| EVD-001 | IDP-A oauth/config/AuthorizationServerConfiguration | 已装配 SAS；同一类包含链、参数校验、JWT Claim、事务包装、错误与观测 | 按职责提取，保留标准 SPI 与业务约束 |
| EVD-002 | IDP-A oauth/controller/filter/TenantLoginAuthenticationFilter | 直接调用 IdentityFacade，手工构建认证及保存 Session；密码复验写 STRONG | 改用标准认证机制，纠正强度语义 |
| EVD-003 | IDP-A oauth/service/impl/TenantAuthorizationServiceImpl#save | Consent 确认时更新已选 Scope | 定义合法状态转换 |
| EVD-004 | IDP-A oauth/domain/converter/SasAuthorizationConverter#toSource | 授权码产生后清除 PendingConsent | attributes 不能整体永久不可变 |
| EVD-005 | IDP-A oauth/repository/impl/OAuthAuthorizationRepositoryImpl#save/#requireImmutableIdentity | 同时禁止 Scope 与 attributes 变化 | 按身份绑定与过程状态分别约束 |
| EVD-006 | IDP-A 测试 OAuthConsentRoundTripTest#Fixture.configurePorts | Repository.save 使用 Map 替身，没有执行实际 Repository 校验 | 必须补真实 Repository 类及真实数据库层验证 |
| EVD-007 | IDP-A oauth/domain/converter/SasRegisteredClientConverter | USER/SERVICE 与 PUBLIC/CONFIDENTIAL 分离；S256；CONFIDENTIAL USER 轮换 Refresh；PUBLIC USER 无 Refresh | 保持当前分类和生命周期 |
| EVD-008 | IDP-S security/IdpBearerAuthenticationFilter；TenantIssuerAuthenticationManagerComponent | 自定义 Bearer/Context 处理，同时已有 Spring JWT/issuer resolver 基础 | 标准 Filter 接入现有可信验证，一次认证 |
| EVD-009 | EDGE config/EdgeSecurityConfiguration；service/impl/EdgeAuthorizedClientRepository、EdgeSingleFlightAuthorizedClientManager | 原生 Reactive OAuth2 Login/Client 外围已有加密存储、会话绑定与并发控制 | 保留这些必要增强，精简装配 |
| EVD-010 | EDGE controller/EdgeSessionController#logout；SDK src/auth/gatewayAuthClient.ts | POST /bff/logout 固定返回 204 或带远端状态的 503；SDK 明确识别该契约 | 保留原接口，浏览器登出采用独立入口 |
| EVD-011 | IDP-C identity/IdentityFacade#changePassword；IDP-A identity/controller | 已有改密领域方法；所查生产调用方未接通该方法，临时密码登录被拒绝 | 必须提供受限的初始/强制改密通路 |
| EVD-012 | AUTHZ core/delegation/ManagementPolicySpecification | PASSWORD < MFA < STRONG | 密码复验不能满足更高强度策略 |
| EVD-013 | IDP-A OAuthManagedDdlComponent；db/egon-mp/repository-manifest.json | OAuth schema 使用独立 managed DDL；另有旧 Flyway 链 | 不修改旧版本、不混用迁移归属 |
| EVD-014 | IDP-A TenantAuthorizationServiceImpl#findByToken/#isCurrentToken | 普通读取拒绝过期/撤销 Token 与无效授权 | 不能直接兼作所有 OIDC 登出提示的读取语义 |
| EVD-015 | 本地 spring-security-samples main@2e3f349b；官方文档与原生 OIDC Logout Provider | 标准链和 SPI 可复用；登出提示校验与普通 Bearer Token 校验目的不同 | 登出适配必须目的受限，不放宽 API 鉴权 |
| EVD-016 | IDP-A OAuthTokenIssueServiceImpl#authorizeClientCredentials；IDP-C OAuthClient | 旧 core OAuthClient 仍在 SERVICE 资源策略使用 | 不把其旧 PKCE 规则误用于新的 USER 注册，也不全量删除该类型 |

上述均为静态证据。没有将历史测试结果计作本次测试通过，也没有读取生产数据或执行登录。

### 2.3 官方示例的采用范围

| 参考 | 本规格采用 | 明确不照搬 |
| --- | --- | --- |
| servlet/spring-boot/java/oauth2/authorization-server | SAS 协议链及注册/授权/Consent/Token 扩展点 | 静态演示用户、内存存储、演示密钥与客户端混用 |
| servlet/spring-boot/java/oauth2/login | 标准 OAuth/OIDC Client 登录分工 | 将登录 Client 当成 IdP |
| servlet/spring-boot/java/oauth2/resource-server | Bearer、JWT、AuthenticationManagerResolver 的标准接入 | 仅验签和 Scope 即代替平台授权 |
| servlet/spring-boot/java/oauth2/webclient、restclient | AuthorizedClientManager 与 HTTP 客户端分工 | 为全部请求默认携带同一个 Token |
| reactive/webflux/java/oauth2/login、webclient、resource-server | EDGE 的标准 Reactive 客户端与安全链 | 把 Servlet IdP 或所有 RBAC3 调用改成 Reactive |
| servlet/spring-boot/java/ldap | 仅记录为排除项 | 不增加 LDAP 依赖或配置 |

## 3. Goals and Non-goals

### 3.1 Goals

G-01：完成两条主要授权流程的正确性与持久化合同。G-02：让安全链、认证 Provider、领域服务与 Repository 分工明确。G-03：完成当前第一方应用登录、续期、退出和安全撤销。G-04：保留现有租户、资源、RBAC3、审计与兼容边界。G-05：提供可追踪且不夸大证据的阶段验收。

### 3.2 Non-goals

- NG-001：AIoT、设备身份、设备授权、MQTT 与设备所有权。
- NG-002：LDAP/AD、SAML、外部 IdP 联邦、通用身份源插件。
- NG-003：AI 委托、Token Exchange、代理任务身份。
- NG-004：新增 Password Grant、Implicit Grant、Device Grant、动态客户端注册或其他授权类型。
- NG-005：新增 private_key_jwt、mTLS 客户端认证、DPoP、JWE 或 opaque Token 路线。
- NG-006：新增 MFA、Passkey、手机/邮箱验证码登录、自助注册或新账号恢复产品。
- NG-007：新建移动端长期登录方案、为 PUBLIC Client 新增 Refresh。
- NG-008：任意外部 RP 的 Back-Channel/Front-Channel Logout 平台或全局联邦登出。
- NG-009：重命名仓库/包/配置前缀、改写 issuer、替换 RBAC3 或通用重构。
- NG-010：修改旧迁移、运行数据库修复/迁移、发布制品、启动服务或浏览器。
- NG-011：改变 Tianshu/Yuheng 其他引擎、业务数据库、角色模型、数据/字段规则。
- NG-012：本轮编写实施 Plan 或业务代码。

### 3.3 三阶段边界

| 阶段 | 唯一范围 | 出阶段条件 |
| --- | --- | --- |
| P1 协议与业务契约修正 | Consent/授权/Scope/Token 生命周期、强度/新鲜度、现有改密通路、客户端参数与元数据合同 | 合法流程可持久化；跨身份、超范围和重放被拒绝；实际 Repository 参与验证 |
| P2 实现结构整理 | 安全链、Provider、配置与 Filter 分工、Bearer 标准接入、共享客户端边界 | 原有接口和安全约束兼容；认证不重复执行；各职责有单一实现归属 |
| P3 当前 SSO 与会话验收 | 已接入门户和第一方应用、续期、兼容本地退出、对应 IdP 浏览器会话退出、账号撤销 | 正常、并发和依赖故障场景可验证；局部/SSO/账号安全撤销语义明确 |

P1/P2 的测试可驱动后续必要的同范围适配；不得把 NG 项包装成“完善第三阶段”。每阶段的真实运行验收状态单独记录。

## 4. Requirements and Acceptance Criteria

下表是规范性要求；MUST 表示必须，MUST NOT 表示禁止。每条 AC 在 §14 和 §19 有对应验证。

| Requirement ID | Stage | 规范性要求 | Acceptance ID / 判定 |
| --- | --- | --- | --- |
| REQ-001 | ALL | 严格限制三阶段范围与审核顺序 | AC-001：仅本 Spec 被新增；排除项无实施内容 |
| REQ-002 | ALL | 产品职责与真实路径明确，保留现有外部身份和兼容边界 | AC-002：模块映射、API/issuer/Bean/配置兼容清单完整 |
| REQ-003 | P1 | 授权身份绑定与过程状态分离校验 | AC-003：合法 Consent 转换成功，身份篡改拒绝 |
| REQ-004 | P1 | 请求、获批与实际 Token Scope 分别校验 | AC-004：部分同意、取消、Refresh 限权与 UserInfo 无越界 |
| REQ-005 | P1 | 授权码单次消费与 Refresh 轮换保持原子性 | AC-005：并发最多一次成功，失败不留下半成品 |
| REQ-006 | P1 | USER Client 沿用现有 PKCE/OIDC/回调/资源规则并明确平台约束 | AC-006：标准 Client 经明确配置可接入，非法参数在持久化前被拒绝 |
| REQ-007 | P1 | SERVICE Client 仅按 Client/Resource/Tenant/Scope 获准 | AC-007：CC 不产生 USER 会话、ID/Refresh Token 或 USER 权限 |
| REQ-008 | P1 | 密码复验只更新认证新鲜度，不提升因素强度 | AC-008：密码流程不会满足 MFA/STRONG 门槛 |
| REQ-009 | P1 | prompt/max_age 基于真实认证时间；Refresh 不伪造新认证 | AC-009：新鲜度边界和同一主体复验正确 |
| REQ-010 | P1 | 当前临时密码/强制改密可在未取得业务 Token 前完成 | AC-010：受限改密完成后重新认证；不能绕过账号/成员限制 |
| REQ-011 | P2 | 协议、浏览器、API 与兜底安全链边界确定 | AC-011：每种路径只进入预定链；浏览器 POST 保留 CSRF |
| REQ-012 | P2 | 登录使用标准 AuthenticationManager/Provider/会话机制 | AC-012：账号策略保留，无手工多处安装 Context |
| REQ-013 | P2 | 标准 Bearer 认证接入既有完整验证结果 | AC-013：单次验签与身份构建，所有现有拒绝条件仍生效 |
| REQ-014 | P2 | 协议错误、API 错误、CORS、审计执行点统一 | AC-014：401/403/503 不混淆，审计不重复、不泄密 |
| REQ-015 | P2 | 原生 AuthorizedClientManager 是授权/续期协议主执行者 | AC-015：SDK/BFF 不另写 Token 协议，不重复持有不同事实 |
| REQ-016 | P2 | 对现有配置按职责整理，保留必要 Adapter/Decorator | AC-016：配置主要装配；无新增通用框架或无意义转发层 |
| REQ-017 | P3 | BFF 会话绑定唯一 issuer/subject/tenant，按 Resource 保存 Client | AC-017：第二应用复用登录，各资源 Token 不串用 |
| REQ-018 | P3 | 并发续期、失败未知与绝对到期遵守现有关闭/补偿规则 | AC-018：注销与刷新竞态不能复活旧会话 |
| REQ-019 | P3 | POST /bff/logout 及现有 SDK logout 契约不变 | AC-019：旧调用仍只得到既定 204/503 语义 |
| REQ-020 | P3 | 新增当前门户浏览器登出衔接，对应 IdP 会话通过标准 OIDC 退出 | AC-020：本地立即关闭，合法回跳受控，不能假报远端完成 |
| REQ-021 | P3 | 登出提示的读取只用于退出，不放宽 Bearer/Token 读取 | AC-021：过期/已撤销授权的历史登录事实不恢复任何 API/续期权限 |
| REQ-022 | P3 | 登出回调地址作为 Client 元数据准确登记与校验 | AC-022：未登记、跨 Client/issuer、篡改回跳均拒绝 |
| REQ-023 | P3 | 账号禁用、改密、既有全部撤销继续沿用安全版本/Outbox | AC-023：所有依赖消费者失效；其他账号和 SERVICE 不被误伤 |
| REQ-024 | ALL | 所有新增持久化仅采用一个必要的新迁移版本 | AC-024：旧 SQL/manifest 历史项字节不变；本次无迁移执行 |
| REQ-025 | ALL | 当前应用只做必要认证入口与 SDK 消费适配 | AC-025：业务页面、RBAC3 逻辑和远期功能未被改动 |
| REQ-026 | ALL | 验证覆盖实际框架、Repository 与运行边界并追踪到要求 | AC-026：各层结果分别记录，未运行项不标成功 |

### 4.1 场景清单

SC-01：已有账号首次登录并同意授权。SC-02：只同意部分业务 Scope。SC-03：取消/过期 Consent。SC-04：另一个当前应用复用 IdP Session。SC-05：CC 的 Tenant 与 Platform 分别取得 Token。SC-06：当前用户密码复验。SC-07：临时密码/管理员重置后必须改密。SC-08：并发 Refresh。SC-09：本地退出及远端撤销失败。SC-10：门户退出对应 IdP Session。SC-11：账号禁用与全部撤销。SC-12：跨 issuer、Client、Resource、主体或会话的攻击输入。SC-13：Redis/SQL/审计依赖故障。SC-14：升级前存量授权与旧 SDK 兼容。

## 5. Constraints, Assumptions, and Decisions

### 5.1 已确认约束

- 不改已发布的 issuer、subject 规则、USER/SERVICE 语义、原路由与配置前缀。
- 保留 POST /bff/logout 的无请求体/无 query、CSRF、204 与 503 合同；不通过内容协商悄悄改成重定向。
- 不把 RBAC3 的角色或数据权限编码成长期 JWT 权限全集。
- 保留原本的资源精确绑定、安全版本、撤销、审计、Tenant/Platform 隔离与失败拒绝。
- 不修改已有 Flyway/managed DDL；不借机迁移整个持久化体系。
- 不自动运行任何服务、数据库、容器、浏览器；代码实施需要本 Spec 后续审核。

### 5.2 本 Spec 的具体化决定

| Decision ID | 选择 | 理由与边界 |
| --- | --- | --- |
| DEC-001 | 三阶段保持用户批准的范围 | 不新增技术路线或产品模块 |
| DEC-002 | 身份服务保持 Servlet/SAS；EDGE 保持 Reactive | 与当前工程和官方扩展点一致 |
| DEC-003 | 保留现有 purpose + clientType 分类，不新增 ClientProfile 数据模型 | 已能表达本次两类主要用途 |
| DEC-004 | 现有 USER 参数边界先保留并公开为平台接入规则 | 不以“标准化”为由放宽安全校验或破坏调用方 |
| DEC-005 | Pending/Approved 为领域生命周期视图，不新增数据库状态枚举 | 复用 existing status、PendingConsent 与 Token 记录 |
| DEC-006 | 强度与新鲜度独立；不新增 MFA | 无可信增强因素时不发更高 acr |
| DEC-007 | 增加受限初始/强制改密浏览器通路 | 复用现有 changePassword，修复当前账号流程缺口 |
| DEC-008 | 原 /bff/logout 保留；新增 POST /bff/logout/browser 与 GET /bff/logout/callback | 满足当前门户 IdP 退出且不破坏旧 JSON Client |
| DEC-009 | 登出采用原生 OIDC Provider/Client 机制；只有登出使用只读提示适配 | 避免撤销先发生导致普通有效 Token 查询无法完成 IdP 登出 |
| DEC-010 | Client 增加可选 postLogoutRedirectUris 元数据 | 标准登记和精确匹配需要稳定持久化事实，不从请求 Host 猜测 |
| DEC-011 | 浏览器登出短事务使用现有 Redis 基础设施，生命周期 120 秒 | 关闭 BFF Session 后仍能关联回跳；不建 SQL 会话平台 |
| DEC-012 | 不更改 core OAuthClient 的全部旧用途 | 该类型仍参与 SERVICE 策略；USER 由已有 SAS 注册转换治理 |
| DEC-013 | 新增字段迁移只规划一个 managed DDL 版本 | 本 Spec 不创建脚本；实施前复核版本未被其他工作占用 |

DEC-007/008/009/010 是已批准方向的具体接口和兼容设计，属于本 Spec 的审核内容；尚未实施。若审核修改这些决定，先修订 Spec，不由实施阶段擅自改接口。

### 5.3 审核与依赖边界

当前不存在要求启动环境才能编写本 Spec 的前置条件。真实依赖版本解析、部署 origin/注册 ID、现网会话与数据规模在实施 Plan/运行验收时复核。不能使用未知现网事实填造验收成功。

## 6. Project Technology Context

保持当前 Java 25、父 POM 配置的 Spring Boot 4.1.2、现有 SAS/Spring Security、MyBatis-Plus/managed DDL、PostgreSQL、Redis/Redisson、Spring Session、现有 React SDK 结构。实际传递依赖必须在实施开始时用 reactor 解析结果锁定；本轮未运行 Maven。

本地 Spring samples 指向 Security 7.1.0-SNAPSHOT，不能复制其依赖版本。官方 Security 7.1.2 文档/源码只用于核对 SPI 与协议行为，不能代替项目的实际 resolved dependency 证明。

生产新增类遵守现有业务分包、Lombok/MapStruct/Bean 命名、异常、日志、校验及注释风格。core 保持不依赖 Web/持久化框架。平台 HTTP/持久化 BO 不进入公共 core 以迫使下游依赖 Admin。

## 7. Architecture Design

### 7.1 System Architecture Design

~~~mermaid
flowchart LR
    U[浏览器] --> E[EDGE / 当前门户 BFF]
    E -->|Authorization Code + PKCE + OIDC| I[IdP Servlet / SAS]
    S[后台服务] -->|Client Credentials| I
    E -->|资源绑定 USER Token| R[当前 API / Resource Server]
    S -->|资源绑定 SERVICE Token| R
    R -->|USER 授权| A[RBAC3]
    I --> D[(现有 PostgreSQL)]
    I --> X[(安全状态 / Session / Outbox)]
    E --> B[(现有 BFF Redis)]
~~~

IdP 决定身份和 Token 的可签发性；RBAC3 决定 USER 的具体业务权限。SERVICE 继续按照精确 Client Resource Grant/Scope 处理，不伪装 USER。

### 7.2 High-Level Design：安全链

| Chain | 覆盖范围 | 会话 / CSRF | 主执行者 |
| --- | --- | --- | --- |
| C1 SAS 协议 | 可信 issuer 下 SAS 已启用端点、UserInfo、OIDC 登出和元数据 | 授权浏览器操作 IF_REQUIRED；Consent POST 保护；Token/Revoke 按协议豁免 | SAS |
| C2 浏览器身份 | 当前租户 login/consent 页面及新增受限改密页 | IF_REQUIRED，登录/改密 POST 必须 CSRF | Spring AuthenticationManager + 现有身份业务 |
| C3 API | /api/** 与当前已登记内部路径 | STATELESS；只接受该路径允许的 USER/SERVICE Bearer | 原生 Bearer Filter + 既有完整验证 |
| C4 Fallback | 明确公开健康端点；其他未匹配路径 | 无隐式登录兜底 | 显式放行列表，其余拒绝 |

C1/C2 的 exact issuer 上下文必须在使用依赖之前建立；realm 来自配置与可信注册，不由 Host、任意 Header 或参数决定。共享 filter 实例不得被容器和 Security 双重注册。

C1 的 Consent 提交不是关闭 CSRF 的理由；C2 的页面 Session 不能使 C3 的 Bearer 缺失请求获得身份。EDGE API 链中委托路由过滤器执行的授权，必须有完整路由覆盖测试；不能只看到 permitAll 就认定整个请求已获准。

### 7.3 Detailed Design：认证与授权生命周期

登录调用路径：薄认证 Filter → AuthenticationManager → IdentityPasswordAuthenticationProvider → IdentityFacade → 成功/失败处理与原生 SessionAuthenticationStrategy。账号禁用、失败计数、哈希策略与审计保留。认证凭据不得进入 Session、JWT、日志或错误响应。

认证结果包含稳定 subject、auth_time、真实 acr 及受控认证事务信息。密码复验要求当前主体相同，更新 auth_time，acr 保持 PASSWORD。max_age/prompt=login 不能只刷新 Token 或 Session 时间。

~~~mermaid
stateDiagram-v2
    [*] --> PendingConsent: 可信授权请求与已认证用户
    PendingConsent --> Approved: 有效确认及 Scope 子集
    PendingConsent --> Cancelled: 用户取消
    PendingConsent --> Expired: 事务超时
    Approved --> CodeConsumed: 授权码单次消费
    CodeConsumed --> ActiveFamily: 原子签发成功
    ActiveFamily --> ActiveFamily: 合法 Refresh 轮换
    ActiveFamily --> Revoked: 撤销或安全事实失效
    ActiveFamily --> Expired: 绝对期限到达
~~~

图中状态是业务含义，不要求新增全部 PO 状态值。以下转换在同一权威事务及 expectedVersion 下完成：

- Pending → Approved：校验 state、Client、issuer、subject、Session 绑定、CSRF、当前资源授权；将选中 Scope 固定为获批范围，清除 PendingConsent，创建 Code 并使旧待确认事实不可再次使用。
- Code 消费 → Token 签发：校验回调与 PKCE；消费标记、授权/Token 保存与必要 Outbox 共同成功或共同回滚。
- Refresh：校验当前有效授权与安全事实；新 Token 先满足所有规则，再原子使旧 Refresh 不可再次消费；不得把存储失败当作签发成功。
- 取消：保留无关的历史 Consent，不签发 Code；已取消事务不可恢复成批准状态。

Scope 使用规则：请求范围是请求快照；获批范围是本次用户授权上界；Access Token 的实际范围必须来自该 Token 已验证的签名内容。缩减的 Access Scope 不能因重新加载授权父记录而恢复。Refresh 的任何请求/默认范围都不能超过获批范围与当前 Client/Resource Grant；本规格不新增超出当前合同的独立“永久收窄”产品策略。

### 7.4 初始/强制改密

密码验证成功但 mustChangePassword=true 时，不保存一个拥有 ROLE_USER 的完整认证，也不签发授权码。只生成同 Session、同 issuer、同 subject、同保存授权事务的受限挑战，TTL 5 分钟、一次性、绑定凭据版本。

用户通过受限表单重新提供旧密码、新密码和确认值；服务端复用现有 changePassword 与密码策略，重新校验账号状态、凭据版本和挑战。成功后完成已有撤销/审计，销毁挑战，返回同一可信登录流程重新认证；不把改密直接当成 MFA/STRONG。失败不扩大权限，不暴露账号存在性。挑战不能访问 API、Token Endpoint 或切换主体。

### 7.5 当前门户登出

正常浏览器退出有三个独立结果：BFF 本地关闭、授权族远端撤销、对应 IdP 浏览器会话结束。任何一项未知都不能合并为“全部退出完成”。

~~~mermaid
sequenceDiagram
    participant UI as 当前门户
    participant B as BFF
    participant AS as IdP / SAS
    participant RS as Redis / 撤销补偿
    UI->>B: CSRF 后 POST /bff/logout/browser
    B->>RS: 保存短时登出关联与撤销意图
    B->>B: 关闭本地会话及全部关联 AuthorizedClient
    B-->>UI: 原生 OIDC RP-Initiated Logout 跳转
    UI->>AS: end_session_endpoint + 已绑定提示与 state
    AS->>AS: 验证提示 / Client / 当前浏览器 Session，执行登出
    AS-->>UI: 精确已登记 callback + state
    UI->>B: GET /bff/logout/callback
    B->>RS: 原子消费关联，读取撤销结果
    B-->>UI: 受控退出结果页，显式登录入口
    RS->>AS: 既有撤销补偿重试
~~~

原 POST /bff/logout 不参与重定向，语义不变。新浏览器入口复用本地关闭和撤销意图，不等待 IdP 可达才关闭本地会话。回调不能重新创建已认证 BFF Session，也不自动发起 login。

OIDC 提示适配只提供给原生登出 Provider：只读取服务器已保存、与请求摘要精确一致的 ID Token 认证事实，绑定 issuer、Client/aud、subject 与当前浏览器会话。过期或已撤销的授权不能恢复为有效授权；普通 OAuth2AuthorizationService、Bearer、UserInfo、Code/Refresh 查询保持原拒绝规则。详细目的边界见 §9.4。

## 8. Package Structure and Code File Tree

### 8.1 现有边界

IDP-A 继续使用 identity / oauth / token / support；IDP-S 继续使用 security / client / audit；EDGE 继续使用 config / filter / service / controller；AUTHZ 保留现有 core/starter/admin 分工。不得新增独立认证模块或调整业务包总体布局。

### 8.2 责任与文件范围

标为“拟新增”的符号只有 Spec 获批并进入实施后才创建。名称可在实施 Plan 中按附近命名核对，职责和合同不得漂移。

| 模块 / 文件或符号 | 保留 / 收敛后的责任 |
| --- | --- |
| IDP-A oauth/config/AuthorizationServerConfiguration、support/security/IdpSecurityConfig | Bean 与链装配；声明 matcher、顺序和标准 SPI |
| IDP-A oauth/config/OAuthBrowserSecurityConfiguration（拟新增） | 浏览器身份链；必要独立配置，不复制 SAS 协议配置 |
| IDP-A TenantLoginAuthenticationFilter / TenantLoginController | 请求转换与页面；原 URI 保持；不在 Filter 中承载密码领域规则 |
| IDP-A identity/service/impl/IdentityPasswordAuthenticationProvider（拟新增） | AuthenticationProvider Adapter；调用现有身份事务边界 |
| IDP-A oauth/service/impl 下请求校验、JWT Customizer、协议失败处理组件（按职责拟提取） | 迁移原配置中对应逻辑；禁止一个方法一个转发类 |
| IDP-A TenantAuthorizationServiceImpl / SasAuthorizationConverter / OAuthAuthorizationRepositoryImpl | 生命周期映射、合法变更校验、CAS/事务保存 |
| IDP-A TransactionalOAuthAuthenticationProvider / TransactionalOAuthRevocationAuthenticationProvider | 保留必要的事务 Decorator，不重写原生 grant 算法 |
| IDP-A oauth/service/impl/TenantLogoutAuthorizationService（拟新增） | 只读、只供 OIDC Logout 的认证事实视图；不用于签发或 API 验证 |
| IDP-A OAuthClientBO/PO/DTO/VO/Converter/DAO / SasRegisteredClientConverter | 增加登出回调元数据，保留原字段合同 |
| IDP-C IdentityFacade / AuthenticationContext | 复用既有密码规则和认证合同；不引入 Spring Web |
| IDP-S IdpBearerAuthenticationFilter / TenantIssuerAuthenticationManagerComponent / 各 AccessTokenVerifier | 标准 Bearer 接入现有验证；兼容适配器保留已发布类型与必要调用 |
| IDP-S IdpServiceOAuth2Client / ServiceTokenWebClientConfiguration | 继续原生授权管理、缓存和安全重试 |
| AUTHZ ManagementPolicySpecification 与对应认证强度调用测试 | 保留因素等级；验证 PASSWORD 复验不可满足更高要求 |
| EDGE EdgeSecurityConfiguration / EdgeSessionRedisConfiguration | 安全链与会话装配，各自职责清晰 |
| EDGE config/EdgeOAuthClientConfiguration（拟新增） | 原生 Client Manager 与现有存储/并发组件装配 |
| EDGE EdgeSessionBindingComponent / EdgeAuthorizedClientRepository / EdgeSingleFlightAuthorizedClientManager | 可信绑定、原子生命周期与并发续期 |
| EDGE EdgeLogoutService / EdgeSessionController / 撤销 Worker | 原退出接口和补偿兼容 |
| EDGE service/impl/EdgeBrowserLogoutHandler、EdgeLogoutTransactionRepository（拟新增） | 原生浏览器登出衔接、120 秒关联；复用现有 Redis/加密能力 |
| SDK src/auth/gatewayAuthClient.ts | 保留 logout；增加浏览器登出入口调用 |
| PORTAL / 当前六个控制台认证包装与 SDK 锁定信息 | 仅改调用方式、状态提示和必要依赖一致性；无页面重设计 |

### 8.3 单一执行与依赖规则

- 不同时注册旧、新两个 Bearer 执行链；旧公开类型可保留为兼容 Adapter，但一次请求只执行一个主认证路径。
- 不把认证成功后的 JWT 再交给另一个层重复解析来生成第二套主体。
- 保留现有临时可信 token carrier、MDC、RPC/gateway adapter 等必要契约；明确建立和 finally 清理的位置。
- 新增客户端登出字段仅进入需要它的管理/注册 DTO/BO/PO；不改动 core OAuthClient record 的已发布构造器来强迫所有消费者升级。
- 公共 Bean 名、配置键、接口或序列化类型确需变化时，必须在实施 Plan 列出已知调用方与兼容办法；无必要时保持不变。

## 9. Interface Definitions

### 9.1 Interface Inventory

URI 中 tenantId 为已登记的正数租户标识；realm 只允许当前可信的 tenants/{tenantId} 或 platform。下面的“保持”指原 wire contract 保持，不是忽略本规格的合法状态修复。

| API ID | 方法 / 路径 | 变化 | 认证与职责 |
| --- | --- | --- | --- |
| API-001 | GET /tenants/{tenantId}/oauth2/authorize | 保持并修复内部状态处理 | SAS 用户授权请求 |
| API-002 | POST /tenants/{tenantId}/oauth2/authorize | 保持，CSRF 不可豁免 | 已认证主体的 Consent 提交 |
| API-003 | GET /tenants/{tenantId}/login | 保持 | 仅显示有合法已保存授权请求的登录页 |
| API-004 | POST /tenants/{tenantId}/login | 保持输入；must-change 分支增加受限跳转 | 标准认证 Filter/Provider |
| API-005 | GET /tenants/{tenantId}/consent | 保持 | 当前用户与待确认事务匹配 |
| API-006 | POST /tenants/{tenantId}/oauth2/token | 保持 | Code、既有 Refresh、Tenant CC |
| API-007 | POST /platform/oauth2/token | 保持 | 仅既有 PLATFORM SERVICE CC |
| API-008 | POST /{realm}/oauth2/revoke | 保持 | SAS Client 认证与持久撤销 |
| API-009 | GET /tenants/{tenantId}/userinfo | 保持 | 仅正确用户 Token 和实际 Scope |
| API-010 | GET /{realm}/.well-known/jwks.json 及当前配置的发现/元数据路径 | 保持 | 公开可信元数据；不从 Host 派生 issuer |
| API-011 | GET /oauth2/authorization/{registrationId} | 保持 | EDGE 原生授权入口及既有 resource alias 映射 |
| API-012 | GET /login/oauth2/code/{registrationId} | 保持 | EDGE 原生授权回调 |
| API-013 | GET /bff/session | 保持 | 当前 BFF 可信身份，原响应字段 |
| API-014 | GET /bff/csrf | 保持 | 原 CSRF 响应；不暴露 OAuth Token |
| API-015 | POST /bff/logout | 完全保留原 HTTP/SDK 语义 | 本地关闭与远端撤销状态 |
| API-016 | POST /bff/logout/browser | 新增，P3 | 当前第一方门户浏览器退出 |
| API-017 | GET /bff/logout/callback | 新增，P3 | 单次有界登出回调；无需已认证 Session |
| API-018 | GET /tenants/{tenantId}/connect/logout | 使当前已启用原生 OIDC 端点完成集成 | 只退出匹配当前浏览器的 IdP Session |
| API-019 | GET /tenants/{tenantId}/password/change | 新增，P1 | 受限改密挑战页面 |
| API-020 | POST /tenants/{tenantId}/password/change | 新增，P1 | 挑战 + CSRF + 原密码 + 新密码校验 |
| API-021 | POST /api/v1/tianquan-shoubing/clients | 保持路由，增加可选字段 | 原管理权限，新字段受同等校验 |
| API-022 | PATCH /api/v1/tianquan-shoubing/clients/{clientId} | 保持路由，增加可选字段 | 原 expectedVersion 与管理权限 |
| API-023 | GET /api/v1/tianquan-shoubing/clients | 保持路由，响应增加字段 | 原列表/权限/分页行为不变 |

API-010 不是新增任意通配路由。现有发现地址形式，包括 RFC 8414 的 issuer-path 表达，必须从已登记 AuthorizationServerSettings 与现有 ExactIssuerContextFilter 验证并逐条测试。Platform 不新增用户登录、用户授权或门户退出功能。其他现有客户端管理、密钥、账号、内省和资源管理接口保持原合同，仅做回归，不扩展功能。

### 9.2 请求与响应合同

**API-001/002/005：授权与确认。** 保留当前参数白名单、单值/重复检测和长度限制。当前平台配置要求 state、nonce 为 32–512 字符，S256 challenge 为 43 个 Base64URL 字符，resource 为单个已登记绝对 URI，Scope 最多 64 个且每个符合现有 ASCII 规则。这些是已选平台规则，不声称全部来自 OAuth 核心规范。OIDC 请求的 nonce 原样绑定到该授权事务；非 OIDC 的既有接入也不得因本次重构被静默放宽或拒绝新增组合。

redirect_uri 必须精确登记，resource 必须属于可信 Client 的当前允许集合。授权端点只有在 Client/回调已经验证后才能重定向错误，并带回原 state；其余返回受控错误页面/协议错误。不得把任意 returnTo、Host 或 Forwarded Header 当成受信回调。

Consent 表单仅接受现有 client_id、state、scope、_csrf、consent_action。显式取消或空选择按现有拒绝规则处理；不得使用历史 Consent 把本次未勾选的业务 Scope 自动加回来。成功使用 303 跳转已验证的 Client 回调，Code 不记录到日志。

**API-003/004：本地登录。** POST 继续只接受 username、password、_csrf，保持当前 16 KiB 请求上限、用户名/口令边界以及不接受 query 的规则。正常成功更新 Session ID/CSRF 并恢复原授权请求。凭据错误/锁定/禁用返回泛化失败，不暴露差异；依赖不可用按既有服务不可用处理。must-change 分支在受限挑战建立后 303 到 API-019，而非签发认证令牌。

**API-006/007：Token。**

| grant_type | 允许 Client / 上下文 | 关键输入 | 结果限制 |
| --- | --- | --- | --- |
| authorization_code | 当前 USER PUBLIC/CONFIDENTIAL；tenant issuer | code、redirect_uri、code_verifier；CONFIDENTIAL 还须 Basic Client 认证 | Access；有 openid 时 ID；仅原允许的 CONFIDENTIAL USER 可有 Refresh |
| refresh_token | 当前 CONFIDENTIAL USER 已获授权族 | refresh_token、按规范处理的 scope、Client 认证 | 当前安全事实重验、Refresh 轮换、绝对期限不延长 |
| client_credentials | CONFIDENTIAL SERVICE；精确 Tenant/Platform | Client Basic 认证、scope、resource | SERVICE Access；不含 ID/Refresh，不创建人员 Session |

Token 响应沿用 OAuth JSON，禁止混入业务 Result 包装。invalid_request / invalid_grant / invalid_scope / invalid_target 按原生协议返回；invalid_client 使用相应认证错误及 HTTP 状态；基础设施不可用明确映射为既有 temporarily_unavailable/503，不假报凭据无效。错误优先级与 Token 使用审计拒绝仍保持当前已确认合同。

**API-008/009/010：撤销、UserInfo 与元数据。** 撤销未知 Token 的信息泄露防护与幂等语义沿用 SAS。UserInfo 使用实际 Access Token 的 Scope，不以授权父记录补回权限。元数据只宣告实际开放的 grant/authentication method/endpoint；新增登出元数据不能把 NG-004/005/008 能力一并宣告可用。JWKS 和签名生命周期不改名、不换算法、不发布私钥。

**API-011/012：EDGE 原生入口/回调。** 当前 registration/resource alias 的服务端映射、PKCE、nonce、state、回调 iss、returnTo 白名单和 canonical session 绑定全部保留。调用者不能覆盖目标 resource、issuer、tenant、subject、Client。调用重构后仍通过原生 Login/AuthorizedClientManager 完成，不手工重写授权码交换。

**API-013/014/015：兼容接口。**

- /bff/session 保持 authenticated、tenantId、subject、displayName 合同；不得加入原始 Token、完整认证对象或角色快照。
- /bff/csrf 保持 headerName=X-CSRF-TOKEN 与 token；不得使获取 CSRF 等于用户已认证。
- POST /bff/logout 仍拒绝任何 query/body；要求当前认证与 CSRF Header。204 仅表示本地关闭且远端撤销确认；503 的既有 code=REMOTE_REVOCATION_PENDING、localLoggedOut=true、remoteState=PENDING|UNKNOWN 不改名、不改义。
- 503 不能使前端继续显示用户在线；网络结果未知不能宣称服务器已经完成退出。当前 SDK 的 logout(): Promise<GatewayLogoutResult> 保持不变。

**API-016/017/018：当前门户浏览器退出。**

| 项目 | 明确合同 |
| --- | --- |
| 浏览器发起 | SDK 先取 /bff/csrf，再以顶层表单 POST /bff/logout/browser；仅 _csrf，无 returnTo、issuer、Client 或 Token 输入 |
| 浏览器校验 | Session + CSRF + 现有同源策略；拒绝重复/未知字段、Bearer 与 Cookie 混用或无可信 OIDC 登录事实 |
| 关联状态 | 服务端产生至少 256 bit 随机 state；Redis 保存摘要和可信关联，TTL 120 秒；以 Secure/HttpOnly/SameSite=Lax 的短时 __Host-egon_logout Cookie 绑定浏览器 |
| 本地关闭 | 原子进入 CLOSING/CLOSED，保存可保存的撤销意图，清除 BFF Cookie 和全部关联 Client；不等待 IdP 可达 |
| OIDC 跳转 | 使用原生 OIDC Client-Initiated Logout handler 与受控 redirect strategy；end_session_endpoint 必须来自当前可信 registration/issuer；默认顶层 GET 保持 IdP Lax Cookie 可用 |
| 提示数据 | id_token_hint 仅用于标准登出跳转；不进入 SDK JSON、localStorage 或日志。全链查询日志必须脱敏，响应 no-store 与 no-referrer |
| 回调地址 | 精确登记的 HTTPS /bff/logout/callback；禁止请求提供任意回跳 |
| 回调校验 | 仅单值 state，必须同时匹配短时 Cookie、未消费 Redis 记录与固定 callback；原子消费，删除 Cookie；不恢复认证 |
| 回调结果 | 展示“本地已退出”及独立的远端撤销/IdP 流程结果；有效回跳不能被解释成任意其他 RP 或其他设备均已退出 |
| 部分失败 | 记录可安全输出的阶段/错误码；无法确认 IdP 时明确提示，不自动 login，不伪造成功；既有撤销 Worker 继续补偿 |
| 已无 IdP Session | 在可信提示/Client/回跳已验证的前提下幂等完成；不能据此关闭另一个用户的会话 |
| 未完成/超时 | Redis 关联过期后仍保持本地 CLOSED；回调拒绝且无自动再认证；不能使用过期关联发起新授权 |

API-018 继续由 SAS OIDC Logout Provider 与原生 LogoutHandler 执行。必须建立与 Spring Session 存储一致的 SessionRegistry/会话登记，保留 SID/主体匹配；不得注册一个与实际会话无关的独立内存“权威”。有会话时只允许匹配当前浏览器的 issuer/subject/SID，禁止跨用户清除。存量登录缺少必要 SID/关联时采用明确的兼容失败/重新登录路径，不伪造 SID。

API-017 不接收、转发或签发 Access/Refresh Token。浏览器自行中断或伪造未验证的回调不能使系统宣告服务端撤销完成；实际“下次进入需登录”必须通过运行验收验证。

**API-019/020：受限改密。** GET 只在有效挑战存在时展示表单；不存在、过期、跨 Session/issuer 返回通用拒绝。POST 仅允许 challenge、old_password、new_password、confirm_password、_csrf，最大 16 KiB；密码值遵守现有最大长度与 IdentityFacade 的最小复杂度/禁止同密码规则。挑战最多 5 次提交失败，届满必须重新走密码认证，不允许任意获取挑战。expected credential version 变化、账号禁用或重置使挑战失效。

成功只更新既有密码凭据、身份安全状态及其审计/撤销，销毁挑战后 303 回到同一受控登录入口重新认证。未取得业务 Token 的用户只能执行这一受限动作，不能调用 /me、管理 API、授权确认或 Token Endpoint。不新增匿名重置、找回或注册能力。

**API-021/022/023：Client 登出元数据。** 在现有管理 DTO/VO 增加可选 postLogoutRedirectUris，最多 16 项、每项最多 2048 字符、去重、精确 HTTPS URI、无 userinfo/query/fragment。本期使用当前第一方 BFF 的固定 callback；与部署的可信 publicOrigin 对齐。保留当前 local-only 回调规则时必须同时满足现有本地 profile 与精确 loopback，不允许通配域名。

创建省略时保存 []；更新省略或 null 表示保留旧值，显式 [] 表示清空；更新仍要求 expectedVersion，并遵循已有 Client 状态、安全版本与审计规则。SERVICE Client 必须为空。列表响应返回该字段，旧消费者可以忽略。删除回跳登记后，未完成登出不得继续使用旧地址。已有 redirectUris、resourceUris、allowedScopes 的含义不变。

### 9.3 非 HTTP 合同

| Contract ID | 边界 | 约束 |
| --- | --- | --- |
| CTR-001 | IdentityPasswordAuthenticationProvider → IdentityFacade | 复用密码/锁定/审计；清除凭据；失败计数按已有身份合同持久化 |
| CTR-002 | SAS → TenantAuthorizationServiceImpl → Repository | 合法转换校验、同源事务、expectedVersion、无半签发 |
| CTR-003 | Bearer 主认证 → VerifiedPrincipal / RBAC3 | 单一已验证事实，完整资源/租户/撤销/审计检查 |
| CTR-004 | 原生 AuthorizedClientManager → 缓存/并发 Decorator | 缓存键保持 issuer/Client/凭据版本/resource/context/tenant/scopes；错误失效规则保持 |
| CTR-005 | 原生 OIDC Logout Provider → TenantLogoutAuthorizationService | 只读、仅 ID Token 历史登录事实、不支持 save/remove 或其他 Token 类型 |
| CTR-006 | SDK logoutBrowser() → 浏览器表单导航 | 新增能力；原 logout 签名和结果不变；可注入表单提交以测试，不复制 SDK 到各应用 |
| CTR-007 | 现有安全状态 Outbox → 消费者 | 提交前不发布有效新事实；消费者异常继续 fail closed |

### 9.4 登出只读提示适配的安全边界

原生登出 Provider 与普通 Access/Refresh 校验对“过期/撤销”的目的不同。为了同时满足“立即关闭/撤销”与“对应 IdP 会话退出”，必须提供独立、最小的只读适配；不能修改普通 findByToken 让任何过期或撤销 Token 通用生效。

该适配必须满足：

1. 仅按完整提示的安全摘要读取当前可信 issuer 分区内服务器曾签发的 ID Token，并验证精确值、原 Client/aud、subject、签发时间与认证来源；查询继续使用既有加密/摘要存储。
2. 只构建给 OIDC Logout Provider 的“历史登录事实视图”；不把数据库 REVOKED/EXPIRED 改成 ACTIVE，不清除持久化 revoked_at/consumed_at，不重新发布安全版本。
3. 授权族已撤销或 ID Token 的登录有效期已过去，不会恢复 API/刷新权限；匹配当前浏览器 Session 后，该事实最多用于结束该 Session。提示来自未知签发、错 Client/issuer/subject、无法验证的时间/SID、被删除/无法读取的事实时拒绝。
4. 适配产生的 ID Token 元数据仅说明其作为登出提示的可信性，不能作为“授权仍有效”的证据。不得携带 Access/Refresh/Code，save/remove 和非 ID Token 查询明确拒绝。
5. 适配 Bean 只能注入对应 OIDC Logout Provider，不得标为默认/Primary AuthorizationService；以装配测试确保 Token、Authorize、UserInfo、Introspection、Revocation 仍使用原有效性合同。
6. 存量缺少可信会话来源或 SID 时，不放宽到仅凭 subject 字符串登出其他会话；返回本地已退出、IdP 未确认的明确结果。
7. 提示使用范围受当前浏览器会话与短时 BFF 登出事务约束；不为此无限保留全部历史 Token。现有 retention 不足时应安全失败并作为兼容问题报告，不能越界恢复已清理凭据。

## 10. POJO and Data Model Design

### 10.1 既有对象分工

| 对象 | 归属 | 本次变化 |
| --- | --- | --- |
| AuthenticatedIdentity / AuthenticationContext | IDP-C | 保留稳定 subject 与既有强度词汇；明确 PASSWORD 复验语义 |
| OAuthClientBO/PO 与管理 DTO/VO | IDP-A | 增加 postLogoutRedirectUris；密码/Secret 仍不参与日志输出 |
| RegisteredClient | SAS SPI | 将同一权威 Client 转换为原生注册信息，映射 postLogoutRedirectUris |
| OAuthAuthorizationBO / OAuthAuthorizationAttributesBO | IDP-A | 对不可变绑定和可变化过程分别校验；PendingConsent 不永久冻结 |
| OAuthTokenBO / TokenMetadata / ID Token Claims | IDP-A | 明确实际 Scope、单次使用、SID/认证来源的 ID Token 专用映射；不改变 Access JWT 类型 |
| IdpAuthenticationToken / VerifiedPrincipal / Rbac3ContextAuthentication | Starter | 保留对外类型，统一生成和必要包装的位置 |
| EdgeSessionBindingBO | EDGE | 原 OPEN/ACTIVE/CLOSING/CLOSED 及 generation 合同保持 |
| EdgeLogoutRevocationIntent | EDGE | 原持久撤销意图与重试合同保持 |
| GatewayLogoutResult | SDK | 原 remoteState 枚举不变 |

### 10.2 必要的新对象

| 拟新增对象 | 最小内容 | 保存/暴露规则 |
| --- | --- | --- |
| PasswordChangeChallengeBO | 随机挑战摘要、issuer、subject、凭据版本、保存请求摘要、issuedAt/expiresAt、失败计数 | 仅受限 Session，TTL 5 分钟；不含密码、Token 或 GrantedAuthority |
| PasswordChangeFormDTO | 挑战、旧/新/确认密码及 CSRF 所需输入 | 边界校验；敏感字段排除 toString/日志；不进入持久层 |
| EdgeLogoutTransactionBO | state 摘要、浏览器绑定摘要、issuer、Client/registration、subject、原绑定 ID/generation、固定 callback、远端状态、issuedAt/expiresAt、消费标志 | 现有 Redis，TTL 120 秒；不直接暴露身份/Token到回调 |
| EdgeLogoutResultView | 本地退出结果、独立远端/IdP 流程结果与安全错误码 | 用于退出结果页；不扩大旧 JSON GatewayLogoutResult |

不得为每一步单独新增 VO/Manager/Factory。PO 的审计、乐观锁、逻辑删除和租户字段保持原类型与填充约定。新增字段遵守现有 MapStruct 严格映射，不能用宽泛 Map 隐藏字段丢失。

### 10.3 字段与状态不变量

- 身份绑定：issuer/分区、clientPk、principalName/type、grantType、resource/audience 不可在同一授权事务里变换。
- 认证事实：auth_time、acr 对该次认证有固定意义；Refresh 不能伪造提升。新的真实认证创建新的授权上下文。
- 期限：absolute_expires_at 不因刷新延长。Access/Refresh 期限沿用当前配置范围。
- Scope：按集合规范化比较；顺序变化不等于权限变化，增加未获准值必须拒绝。
- 授权取消/撤销与 Token 消费：只能沿允许的转换，CAS 冲突不能当作成功。
- 受限改密挑战、BFF 登出事务：每个只能成功消费一次，不可序列化为已认证主体。
- SID：仅用于相应 OIDC Session 关联；不替代 API Tenant/Subject 校验，不在普通 API 响应中泄露。

## 11. Database Design

### 11.1 Table Inventory

| Table / Store | 本次读写范围 | DDL |
| --- | --- | --- |
| tianquan_oauth.oauth_client | 已有 Client 管理和注册，新增回跳集合 | 新增一列及类型约束 |
| tianquan_oauth.oauth_authorization | 合法生命周期/获批 Scope/属性保存，保留审计与版本 | 无 |
| tianquan_oauth.oauth_token | 单次消费、轮换与提示目的的只读查询 | 无 |
| tianquan_oauth.oauth_identity_user | 既有账号状态/认证事实 | 无 |
| tianquan_oauth.oauth_identity_credential | 既有改密与凭据版本 | 无 |
| 现有 realm/grant/security-state/consent/outbox | 既有授权和撤销事务 | 无 |
| Spring Session / BFF Redis | 受限挑战、短时登出关联与既有 Session/撤销补偿 | 无 SQL 表 |

### 11.2 唯一计划迁移

拟在 IDP-A src/main/resources/db/egon-mp 下追加 V20261023_001__add_oidc_post_logout_redirect_uris.sql，并在现有 repository-manifest.json 追加该新项及真实 SHA。**本轮只写设计，不创建该脚本或修改 manifest。** 若实施时该版本已被其他任务占用，在写脚本前选择下一有效版本，仍只创建本逻辑变更的一份版本文件。

目标变更：oauth_client.post_logout_redirect_uris，JSONB，NOT NULL，默认 []；增加与附近列一致的 JSON array 类型检查。URI 元素、数量、长度和安全性由管理/注册边界校验。没有新增索引需求，不回填外部地址，不根据旧登录回调推导登出地址。

已有行得到 []，因此旧登录/Token 流程保持可用；当前第一方 Client 经原管理接口显式登记 callback 后，才允许开启浏览器 IdP 登出。

当前 managed DDL family=tianquan-oauth，schema=tianquan_oauth；旧 classpath:db/migration 的 V1–V6 不动。已有 dated scripts、SHA、迁移顺序、数据库状态和原始数据保持。不得在错误的 Flyway 链再加一份重复迁移。

### 11.3 关系与事务

~~~mermaid
erDiagram
    OAUTH_REALM ||--o{ OAUTH_CLIENT : contains
    OAUTH_CLIENT ||--o{ OAUTH_AUTHORIZATION : owns
    OAUTH_AUTHORIZATION ||--o{ OAUTH_TOKEN : issues
    OAUTH_IDENTITY_USER ||--o{ OAUTH_IDENTITY_CREDENTIAL : authenticates
~~~

此图为本次相关的逻辑关系，不新增外键或修改现有全局身份/分区设计。授权码消费、签发记录、Outbox 的事务管理器/数据源同源规则保留。外部 HTTP 与浏览器跳转不能置于 SQL 长事务中。

## 12. Frontend Page Design

不进行 UI 重设计。当前门户、Tianquan 两个控制台及使用同一认证 SDK 的 Tianshu/Yuheng/Yaoguang 控制台，只做必要调用适配：

- 当前“退出登录”调用新增 SDK logoutBrowser；旧 logout 方法保留给既有 JSON 调用方。
- 取得 CSRF/提交前失败时保持明确可重试状态，不声称已经退出。
- 服务端本地关闭之后，不因远端 PENDING/UNKNOWN 恢复登录 UI。
- 退出结果页只展示安全状态、必要说明与显式登录入口，不自动重走授权码流程。
- 当前 Login/Consent HTML 页维持项目风格；强制改密页只为既有临时密码/重置链路提供受限表单。
- 角色激活或管理策略要求 MFA/STRONG 时，提示当前能力不足或保留既有 STEP_UP_REQUIRED 语义；不能循环进行密码复验以假装已满足。
- postLogoutRedirectUris 在现有 Client 配置页面中按当前表单方式编辑/展示，复用既有权限和提交版本；不新建客户端管理产品。
- SDK 源码、必要消费声明/锁文件和制品合同测试保持一致；不复制 SDK，不在本 Spec 授权发布 registry 制品。

## 13. Design Patterns and Architecture Principles

| Pattern / Principle | 具体使用 | 为什么需要 |
| --- | --- | --- |
| Adapter | IdentityFacade → AuthenticationProvider；已验证 Token → 标准 Authentication；只读登出事实 → SAS Logout SPI | 框架协议与已有领域模型不同，避免 Filter 同时承载领域和协议职责 |
| Decorator | 原生 grant/provider 的事务；AuthorizedClientManager 外围的并发/缓存/审计 | 保留原生算法，集中现有平台约束 |
| 现有领域状态校验 | Repository 保存前允许的生命周期转换 | 区分身份不变量与合法过程变化，不引入状态机框架 |
| 单一权威事实 | Client 注册、Token 验证结果、BFF canonical binding | 避免多个层维护不一致身份或资源选择 |
| 失败关闭 | 依赖不可用、身份不明、状态冲突 | 不因结构整理降低原有安全保障 |

不引入认证 Provider 注册平台、通用多因素框架、全局 Session 编排引擎、工厂层次、每方法一个策略类或重复 Gateway/BFF。方法提取以独立职责和真实复杂度为依据；较短且清晰的业务方法保持直接实现。

## 14. Test Design

### 14.1 验证层次与执行边界

L1：纯领域/转换/校验单元测试。L2：实际 Spring FilterChain、Provider、ClientManager 和实际 Repository 类的组件合同测试。L3：真实 PostgreSQL/Redis 的持久化、事务和并发验证。L4：用户已启动并明确授权的当前应用浏览器验收。

L2 的“实际 Repository 类”允许隔离底层 Mapper，但必须执行 Repository 的不可变/版本检查；不能再用 Map 直接代替整个 Repository.save。L3 验证真实 SQL、事务与锁，不能由 L2 代替。测试中的原生 SAS Provider/Filter 不得全部 mock 成成功。

本轮不执行这些业务测试。未来实现中的 L1/L2 不得隐式启动容器或外部服务；L3/L4 由用户提供或明确授权运行环境后执行。

### 14.2 Test Case Inventory

| Test ID | Layer / Stage | 场景与判定 | Requirements |
| --- | --- | --- | --- |
| TEST-001 | 文档 / ALL | 三阶段、排除项、审核门槛与变更文件一致 | REQ-001, REQ-026 |
| TEST-002 | L1/L2 / ALL | 旧 issuer/API/Bean/配置/公共类型兼容；物理模块正确 | REQ-002 |
| TEST-003 | L2/L3 / P1 | Pending → Approved 执行实际 Repository，允许 Scope/过程变化，保留身份绑定 | REQ-003 |
| TEST-004 | L2/L3 / P1 | 部分同意、空选择、取消、历史 Consent 未勾选范围不会重加 | REQ-004 |
| TEST-005 | L2/L3 / P1 | 篡改 issuer/client/subject/resource、Session/state 不匹配和 CAS 冲突拒绝 | REQ-003, REQ-006 |
| TEST-006 | L2/L3 / P1 | 同一个 Code 并发交换，最多一次成功 | REQ-005 |
| TEST-007 | L2/L3 / P1 | 签名、Token 保存、授权保存或 Outbox 故障整体回滚 | REQ-005, REQ-014 |
| TEST-008 | L2/L3 / P1 | Refresh 轮换、旧凭据重放、绝对到期、实际 Scope 重载均受约束 | REQ-004, REQ-005 |
| TEST-009 | L2 / P1 | 缺失/错误/plain PKCE、非法回调、重复参数、state/nonce/resource 边界 | REQ-006 |
| TEST-010 | L2 / P1 | PUBLIC USER 既有流程可用且无 Refresh；SERVICE 无 USER/ID/Refresh | REQ-006, REQ-007 |
| TEST-011 | L2/L3 / P1 | CC Client/Resource/Tenant/Platform/Scope/凭据版本交叉组合和撤销 | REQ-007 |
| TEST-012 | L2 / P1 | prompt=login/max_age/时钟边界要求真实同一主体复验 | REQ-009 |
| TEST-013 | L1/L2 / P1 | 密码复验仍 PASSWORD，不能通过 MFA/STRONG 管理策略 | REQ-008, REQ-009 |
| TEST-014 | L2/L3 / P1 | 临时密码 → 受限改密 → 重新认证；成功前无 Code/业务 Token | REQ-010 |
| TEST-015 | L2/L3 / P1 | 改密挑战跨 Session/issuer/subject、过期、重放、5 次失败、重置竞争均拒绝 | REQ-010, REQ-012 |
| TEST-016 | L2 / P2 | C1–C4 路由矩阵、原生 CORS/OPTIONS、Consent/Login/改密 CSRF、兜底拒绝 | REQ-011, REQ-014 |
| TEST-017 | L2 / P2 | API 无凭据或坏 Bearer 返回 API 错误，不跳转 HTML；不被浏览器 Session 放行 | REQ-011, REQ-013 |
| TEST-018 | L2 / P2 | 每请求主认证/验签/可信主体生成和必要审计只执行一次，Context 清理正确 | REQ-012, REQ-013, REQ-014 |
| TEST-019 | L2/L3 / P2 | 撤销/安全版本/资源/审计不可用仍拒绝，401/403/503 含义保持 | REQ-013, REQ-014 |
| TEST-020 | L2 / P2 | 原生 Login/ClientManager 完成真实协议组件交互，参数和字段不丢失 | REQ-015, REQ-016 |
| TEST-021 | L1/L2 / P2 | SERVICE 缓存键隔离、单飞、Secret 轮换失效、GET 单次重试、写操作不重放 | REQ-015 |
| TEST-022 | L2/L3 / P3 | BFF 跨 subject/issuer/tenant/resource/registration 篡改均拒绝 | REQ-017 |
| TEST-023 | L4 / P3 | 当前至少两个应用同身份域复用 IdP 登录，各自 Resource Token 正确 | REQ-017 |
| TEST-024 | L2/L3 / P3 | 并发刷新与退出竞争、锁超时、进程中断/结果未知不能复活旧 generation | REQ-018 |
| TEST-025 | L1/L2 / P3 | idle/absolute 时间上限与原始会话创建时间保持，刷新不能延长绝对期限 | REQ-018 |
| TEST-026 | L2 / P3 | 旧 /bff/logout 204/503 以及旧 SDK logout 行为逐字段兼容 | REQ-019 |
| TEST-027 | L2/L3/L4 / P3 | 新浏览器 POST → 原生 OP 登出 → 受控回调；本地关闭和 IdP Session 结束 | REQ-020 |
| TEST-028 | L2/L3 / P3 | 过期/撤销授权仅能形成受限登出事实；原 Token/Resource 服务仍拒绝 | REQ-021 |
| TEST-029 | L2 / P3 | 错误/重放 state、错 Cookie、未登记回跳、跨 Client/issuer/subject/SID 拒绝 | REQ-020, REQ-021, REQ-022 |
| TEST-030 | L2/L3/L4 / P3 | IdP/Redis/撤销服务不可用，结果明确；本地已关不回滚为在线 | REQ-018, REQ-020 |
| TEST-031 | L2 / P3 | 登出关联 120 秒过期、回调单次消费、敏感值不落日志/JSON/storage | REQ-020, REQ-014 |
| TEST-032 | L2/L3/L4 / P3 | 账号禁用、改密、现有全部撤销影响正确 USER，不误伤其他账号/SERVICE | REQ-023 |
| TEST-033 | 静态/L3 / P3 | 唯一新迁移、旧 SHA/字节保留、旧行默认 []、实际 schema 正确 | REQ-024 |
| TEST-034 | L1/L2/L3 / P3 | Client 元数据创建/保留/清空、版本冲突、URI 边界、SERVICE 空值限制 | REQ-022 |
| TEST-035 | 前端合同 / P3 | 当前调用方只做必要适配；未复制 SDK；旧 logout 与新浏览器入口分开 | REQ-025 |
| TEST-036 | 受控演练 / P1/P3 | 旧的无因素证据 STRONG 授权不能继续 Refresh 维持假强度 | REQ-008, REQ-023 |
| TEST-037 | L2 / P1 | 元数据宣告与当前真实开放 grant/Client auth/endpoint 一致 | REQ-006, REQ-007 |
| TEST-038 | 构建/L2 / ALL | 受影响模块编译与实际测试，Spring SPI 校验/装配规则合法 | REQ-016, REQ-026 |
| TEST-039 | L2/L3 / P3 | SessionRegistry 与真实 Session Repository 同源；存量无 SID 安全降级 | REQ-020, REQ-021 |
| TEST-040 | L2 / ALL | 既有 issuer/JWKS/kid、签名和资源校验回归，未引入新算法/凭据路线 | REQ-002, REQ-013 |

### 14.3 测试数据与故障注入

至少覆盖两个可信 tenant issuer、一个 Platform issuer、两个用户、两个 Resource、两个 CONFIDENTIAL USER Client、一个既有 PUBLIC USER Client、两个 SERVICE Client。测试标识可以是 fixture；密码、Secret、JWT、Code、Cookie、state/nonce 不写入报告或日志。

故障注入使用明确位置的 Mapper/签名/Outbox/Redis/HTTP 失败，不以全局 catch-and-allow 消除失败。并发测试使用可控同步屏障，不依赖固定 sleep 判断成功。

### 14.4 证据输出

每项结果标为 Not run / Passed / Failed / Runtime unverified；记录实际命令、退出码、关联源码基线与测试层。不得把文档校验、编译、fixture 或单节点结果替代 L3/L4。本 Spec 交付时全部业务测试状态均为 Not run。

## 15. Non-functional and Cross-cutting Design

### 15.1 安全、观测与失败语义

- 密码、Secret、授权码、Access/Refresh/ID Token、Cookie、原始 state/nonce/挑战值不进入日志、错误响应、指标标签或 Spec 验收附件。
- OAuth/OIDC 标准跳转所需敏感参数只出现于协议交换；日志、链路记录和代理访问日志必须屏蔽，页面设置 no-store/no-referrer。
- 保留现有严格审计故障处理和 Outbox 保证，不用异步“尽力而为”替换已要求的持久确认。
- 复用现有低基数指标；新增组件不重复上报同一认证/Token 使用事件。
- Redis/SQL/签名/审计不可用时保持当前失败关闭，不能返回正常 Token 或空权限当成功。
- 请求验证、认证、授权和基础设施失败各自有可追踪错误码，但不暴露具体凭据或非必要个人资料。

### 15.2 并发与性能

Code/Refresh/Consent 使用现有事务、行锁/版本校验与单次消费，不增加全局 JVM 锁代替分布式一致性。BFF 的生命周期与续期锁按既有 canonical binding/资源维度复用；严禁退出后在 finally 或迟到响应中把旧会话重新写成 ACTIVE。

密码哈希、阻塞数据库/JWKS/Redis 调用不得新增到 Netty event loop。现有同步服务 Token Client 的 boundedElastic 隔离及 finally 上下文清理继续保留。目标是消除不必要的重复协议处理，不在无数据情况下承诺吞吐或时延提升。

### 15.3 配置与有界状态

| 配置 / 状态 | 决定 |
| --- | --- |
| 现有 issuer/publicOrigin/可信注册/Resource 映射 | 保留键与语义，禁止从不可信 Header 推导 |
| 现有 BFF idle/absolute/refresh lock/timeout | 保留已校验范围；当前默认 idle 30 分钟、absolute 8 小时，不扩大 |
| 改密挑战 | 固定 5 分钟、最多 5 次失败；复用受限 Session |
| 浏览器登出关联 | 固定 120 秒、单次消费；只复用现有 Redis |
| egon.yuheng.edge.browser-logout.enabled（拟新增） | 默认 false；仅在 Client 回跳登记与服务端合同验证完成后启用 |
| BFF callback | 配置的 publicOrigin + 固定 /bff/logout/callback，不接受请求动态选择 |
| IdP SessionRegistry | 复用当前 Spring Session 支持索引的 Repository 和标准会话登记；不另建内存权威 |

SID/Session index 的接入必须验证存量 Session 序列化、Cookie、namespace 和多实例行为；不得清库或改用新的无关 Redis 实例来绕开兼容性问题。新 flag 是发布闸门，不是永久并行的两套认证实现。

## 16. Compatibility, Migration, Rollout, and Rollback

### 16.1 兼容矩阵

| 对象 | 必须保持 | 本规格有意改变 |
| --- | --- | --- |
| issuer、subject、API 基础路径、配置前缀 | 全部原标识 | 无 |
| USER/SERVICE、Tenant/Platform、audience、Access Token 类型 | 原合同 | 无 |
| 原 /bff/logout / SDK logout | 原输入/状态/结果 | 无 |
| 新浏览器退出 | 不改变旧消费者 | 新增第一方入口、callback 与 SDK 方法 |
| Client 管理 | 原字段/权限/expectedVersion | 可选 postLogoutRedirectUris；遗漏兼容 |
| 初始/强制改密 | 原密码策略/重置/撤销 | 受限流程可以完成改密，不提前授予权限 |
| Consent | 仍阻止身份/Scope 越权 | 允许原本合法的状态转换 |
| 密码复验 | 仍可满足认证新鲜度 | 不再伪装 STRONG/MFA |
| 数据库 | 旧脚本、表和数据 | 一列可向后兼容的 Client 元数据 |
| 公共 Java 类与接口 | 原有已知调用方 | 必要适配或兼容重载；不得无必要破坏签名 |

### 16.2 三阶段交付闸门

P1 的结构调整仅限完成合同所需。P1 必须先使真实 Repository 测试能够发现并覆盖原缺陷，再进入大范围装配整理。P2 先按一个受影响应用安全链验证兼容，再扩大到其必要当前调用方；不一次删除所有自定义 Filter。P3 在客户端回跳登记、SessionRegistry 与原生 Logout Provider 的合同通过后，才启用新浏览器退出。

本期当前应用的明确适配集是 PORTAL、IDP-W、AUTHZ-W，以及已使用同一共享认证 SDK 的 tianshu-web、yuheng-web、yaoguang-web 的认证包装。其他平台后端只因已发布 Starter 合同做必要回归，不自动纳入功能改造。

### 16.3 数据与存量认证事实

- OAuth managed DDL 只追加 §11 的一个版本；先应用兼容 schema，再发布读取新字段的代码；旧行 [] 不触发自动回跳配置。
- 使用既有受权 Client 管理接口登记当前第一方 callback；不直接批量 SQL 猜测/回填 URL。
- 存量因密码复验得到 STRONG、又无可信因素证据的 USER 授权不能通过 Refresh 长期延续。发布计划必须识别受影响主体/授权，使用既有受控撤销路径使其重新登录；禁止把存量 JWT/加密属性静默改写为另一个强度。
- 此安全修正可能使原本依赖错误 STRONG 的高风险操作被拒绝。本期不降低 RBAC3 门槛来掩盖缺少 MFA，也不新增 MFA；审核时应确认这个有意行为变化。
- 存量 BFF/IdP 登录缺少必要 SID 或登出关联时，保留原本地退出并明确 IdP 状态未确认；不制造可信会话。新会话经过标准登记后进入完整流程。
- Cookie、Redis namespace、加密 key purpose/AAD、授权快照与用户数据不得被清理重建来“简化迁移”。

### 16.4 失败与回滚

先关闭新浏览器登出入口的使用和开关，保留原 JSON 退出与撤销补偿，再按依赖顺序回滚结构装配。数据库新增列保留，不修改已执行迁移、不 drop 回去、不运行 Flyway repair。

安全修复不能回滚成旧的假 STRONG 或删除不可变身份校验。若回滚版本不能正确处理当前安全事实，应停止该版本发布并以前向修复恢复。不得为恢复 UI 可用性绕过认证强度、撤销或审计失败。

任何真实部署、账号撤销、迁移、发布、SDK 上传或运行操作都需要后续明确授权；本 Spec 的批准仅进入下一步 Plan/实施安排，不执行这些副作用。

## 17. Alternatives and Decisions

| 方案 | 决定 | 原因 |
| --- | --- | --- |
| 推倒现有 IdP 重建或改用另一套产品 | 不采用 | 当前已有 SAS 与必要平台能力，本次需求是收敛 |
| 用官方演示配置直接替换整个安全系统 | 不采用 | 会丢失资源、租户、撤销、审计与 RBAC3 约束 |
| 删除所有自定义 Filter/Decorator | 不采用 | 存在必要的 realm、事务、载体和观测适配 |
| 保持所有自定义流程，只拆文件 | 不采用 | 不能解决协议职责重复和生命周期矛盾 |
| 直接放宽普通 findByToken 来支持登出 | 不采用 | 会污染 API/刷新/授权的有效性边界 |
| 延迟撤销授权族以等待浏览器完成 IdP 登出 | 不采用 | 浏览器可能中断，且会扩大有效凭据窗口 |
| 目的受限只读登出事实 Adapter + 原生 OIDC Provider | 采用，须专项验证 | 解决历史登录提示与有效访问授权之间的目的差异 |
| 改旧 /bff/logout 为 302/303 | 不采用 | 破坏当前 SDK 的 204/503 合同，fetch 也不等于顶层导航 |
| 用同邮箱/用户名匹配另一用户或 issuer | 禁止 | 身份、会话和授权绑定不能被显示属性替代 |
| 为强度不足加入自动降级策略 | 禁止 | 会改变已批准的安全边界 |

目的受限登出视图是本规格选定的兼容设计，**不是**原生 Provider 默认允许任意已失效 ID Token 的声明。必须通过真实原生 Provider 和负向隔离测试；若解析后的依赖版本无法安全装配该受限视图，应返回 Spec 审核，不擅自重写标准协议端点或延迟安全撤销。

## 18. Risks and Open Questions

### 18.1 已识别风险与处理

| Risk ID | 风险 | 处理 / 闸门 |
| --- | --- | --- |
| RISK-001 | 产品名与目录历史名相反 | 使用 §2.1 映射，实施前核对实际类；不重命名 |
| RISK-002 | 多仓库现有脏文件且可能并行演进 | 实施前重建基线，限定文件，不回滚/提交无关修改 |
| RISK-003 | 只用 fixture 掩盖实际 Repository 拒绝 | TEST-003/005/007 必须执行实际类和真实 DB 层 |
| RISK-004 | 标准组件替换导致多次认证或审计丢失 | TEST-016–021，逐链迁移 |
| RISK-005 | 登出与撤销竞争、提示过期、SID 缺失 | 受限只读适配、原生 SessionRegistry、独立结果与 TEST-027–031/039 |
| RISK-006 | 修正假 STRONG 后部分当前管理动作不能通过 | 明确安全变化；保持拒绝，不降级门槛；核对旧授权退出 |
| RISK-007 | 增加客户端字段导致 old/new SDK 或节点不兼容 | 默认 []、更新省略保持、服务端先行、原接口继续可用 |
| RISK-008 | 本地样例版本与平台 BOM 不同 | 先解析版本，不升级依赖来强行套用示例 |
| RISK-009 | 必要接口被扩展成注册/找回/全局登出平台 | 只允许本规格原子操作，超出返回范围审核 |
| RISK-010 | 真实 SSO 与多实例行为尚未验证 | L3/L4 标为 Runtime unverified，不能按源码通过宣布完成 |

### 18.2 待审核决定与外部事实

待用户审核的是本 Spec 全文，重点包括 DEC-007 受限改密、DEC-008 兼容的浏览器退出入口、DEC-009 登出只读目的边界，以及 DEC-010/013 的客户端元数据和唯一迁移。

不存在可由实施者自行扩展的开放功能选择。部署 origin、Client/registration 实际 ID、可用 PostgreSQL/Redis 环境与允许的浏览器验收时间属于后续环境事实；不在本轮索取秘密或启动环境。若事实迫使设计变化，先修订 Spec。

## 19. Traceability Matrix

| Requirement | Acceptance | 设计位置 | 验证 | 阶段 |
| --- | --- | --- | --- | --- |
| REQ-001 | AC-001 | §1、§3、§20 | TEST-001 | ALL |
| REQ-002 | AC-002 | §2.1、§8、§16 | TEST-002、TEST-040 | ALL |
| REQ-003 | AC-003 | §7.3、§10.3 | TEST-003、TEST-005 | P1 |
| REQ-004 | AC-004 | §7.3、§9.2 | TEST-004、TEST-008 | P1 |
| REQ-005 | AC-005 | §7.3、§11.3 | TEST-006、TEST-007、TEST-008 | P1 |
| REQ-006 | AC-006 | §9.1、§9.2 | TEST-005、TEST-009、TEST-010、TEST-037 | P1 |
| REQ-007 | AC-007 | §7.1、§9.2 | TEST-010、TEST-011、TEST-037 | P1 |
| REQ-008 | AC-008 | §7.3、§16.3 | TEST-013、TEST-036 | P1 |
| REQ-009 | AC-009 | §7.3、§10.3 | TEST-012、TEST-013 | P1 |
| REQ-010 | AC-010 | §7.4、§9.2、§10.2 | TEST-014、TEST-015 | P1 |
| REQ-011 | AC-011 | §7.2 | TEST-016、TEST-017 | P2 |
| REQ-012 | AC-012 | §7.3、§8、§9.3 | TEST-015、TEST-018 | P2 |
| REQ-013 | AC-013 | §8.3、§9.3、§15 | TEST-017、TEST-018、TEST-019、TEST-040 | P2 |
| REQ-014 | AC-014 | §9.2、§15.1 | TEST-007、TEST-016、TEST-018、TEST-019、TEST-031 | P2 |
| REQ-015 | AC-015 | §8、§9.3 | TEST-020、TEST-021 | P2 |
| REQ-016 | AC-016 | §8、§13 | TEST-020、TEST-038 | P2 |
| REQ-017 | AC-017 | §7.1、§9.2、§10 | TEST-022、TEST-023 | P3 |
| REQ-018 | AC-018 | §7.5、§15.2 | TEST-024、TEST-025、TEST-030 | P3 |
| REQ-019 | AC-019 | §9.2、§16.1 | TEST-026 | P3 |
| REQ-020 | AC-020 | §7.5、§9.2、§15.3 | TEST-027、TEST-029、TEST-030、TEST-031、TEST-039 | P3 |
| REQ-021 | AC-021 | §9.4 | TEST-028、TEST-029、TEST-039 | P3 |
| REQ-022 | AC-022 | §9.2、§11 | TEST-029、TEST-034 | P3 |
| REQ-023 | AC-023 | §9.3、§16.3 | TEST-032、TEST-036 | P3 |
| REQ-024 | AC-024 | §11、§16 | TEST-033 | ALL |
| REQ-025 | AC-025 | §12、§16.2 | TEST-035 | ALL |
| REQ-026 | AC-026 | §14、§20 | TEST-001、TEST-038 | ALL |

## 20. Review and Acceptance

### 20.1 原始要求核对

- 三阶段与用户已审核方案一致；AIoT、LDAP 和远期扩展完全排除。
- 当前只写 Spec；没有生成实施 Plan、代码、测试代码、配置或数据库脚本。
- 产品职责使用用户命名，真实路径明确映射，不误改模块。
- 官方示例用来确认标准扩展点，现有领域与安全约束继续保留。
- 必要的具体接口/字段新增列为本 Spec 待审核决定，不声称已经批准或实现。

### 20.2 文档校验

已执行文档检查：20 个章节完整；26 个 REQ/AC 与 40 个 TEST 的追踪闭合；17 个本地引用目标存在；23 个 HTTP 合同清单行无重复编号；三个阶段与排除项一致；图示围栏配对。Git 空白检查修正了文件末尾多余空行后复验通过（新增文件的 diff 返回码为 1，无空白诊断）。上述均为文档校验，不是业务测试或协议运行验证。

本工作区未发现可执行的 egon-coding-writing-spec / validate_spec.py，因此采用明确的结构、链接和追踪检查，不声称运行过该历史 strict validator。

### 20.3 实施验收门槛

- P1/P2/P3 分别提交需求满足情况与各层实际证据。
- 只通过静态、编译或 L2 时，不能将真实数据库/多实例/浏览器 SSO 标为通过。
- 既有功能因本规格明确安全修复而改变时，必须按 §16 解释，不通过降低校验恢复旧错误行为。
- 新增接口必须有实际原生链测试，新增字段必须有真实迁移验证；计划中的测试用例不是已执行证据。
- 已知必需测试失败或必需运行验收缺失时，标记对应阶段未完成，不宣告整体完成。

### 20.4 最终状态

**Spec：Superseded，整体查看新版待审核规格。本文未实施；本轮也未执行业务测试或运行验收。**

用户审核通过后再编写实施 Plan；未经进一步指令，不启动项目、不运行迁移、不打开浏览器、不提交或发布制品。

### 20.5 来源与核对材料

以下历史文档只提供保留合同与格式，最新范围以用户批准的三阶段方案和本 Spec 审核结果为准。

- [OAuth/OIDC 主规格](../../history/egon/spec/2026-09-22-17-14-tianquan-multitenant-oauth-oidc-design.md)
- [当前代码对齐规格](../../history/egon/spec/2026-10-08-10-18-oauth-current-code-alignment.md)
- [自身安全规格](../../history/egon/spec/2026-10-10-12-36-tianquan-security-self-hardening.md)
- [当前 IdP 协议配置](../../../../tianquan-shoubing-service/stellar-enclosure-tianquan-shoubing-admin/src/main/java/top/egon/cola/platform/tianquan/shoubing/admin/oauth/config/AuthorizationServerConfiguration.java)
- [当前登录 Filter](../../../../tianquan-shoubing-service/stellar-enclosure-tianquan-shoubing-admin/src/main/java/top/egon/cola/platform/tianquan/shoubing/admin/oauth/controller/filter/TenantLoginAuthenticationFilter.java)
- [当前授权保存](../../../../tianquan-shoubing-service/stellar-enclosure-tianquan-shoubing-admin/src/main/java/top/egon/cola/platform/tianquan/shoubing/admin/oauth/service/impl/TenantAuthorizationServiceImpl.java)
- [当前持久层不可变检查](../../../../tianquan-shoubing-service/stellar-enclosure-tianquan-shoubing-admin/src/main/java/top/egon/cola/platform/tianquan/shoubing/admin/oauth/repository/impl/OAuthAuthorizationRepositoryImpl.java)
- [当前原生链 fixture](../../../../tianquan-shoubing-service/stellar-enclosure-tianquan-shoubing-admin/src/test/java/top/egon/cola/platform/tianquan/shoubing/admin/oauth/OAuthConsentRoundTripTest.java)
- [当前身份领域](../../../../tianquan-shoubing-service/stellar-enclosure-tianquan-shoubing-core/src/main/java/top/egon/cola/platform/tianquan/shoubing/core/identity/IdentityFacade.java)
- [当前强度策略](../../../../tianquan-jianshen-service/stellar-enclosure-tianquan-jianshen-core/src/main/java/top/egon/cola/platform/tianquan/jianshen/core/delegation/ManagementPolicySpecification.java)
- [当前 EDGE 安全配置](../../../../yuheng-service/stellar-enclosure-yuheng-edge-gateway/src/main/java/top/egon/cola/component/yuheng/edge/config/EdgeSecurityConfiguration.java)
- [当前 BFF 退出合同](../../../../yuheng-service/stellar-enclosure-yuheng-edge-gateway/src/main/java/top/egon/cola/component/yuheng/edge/controller/EdgeSessionController.java)
- [当前共享 SDK](../../../../web-sdk/packages/stellar-enclosure-web-shared/src/auth/gatewayAuthClient.ts)
- [当前 OAuth DDL manifest](../../../../tianquan-shoubing-service/stellar-enclosure-tianquan-shoubing-admin/src/main/resources/db/egon-mp/repository-manifest.json)
- [Spring 官方本地样例对应源码：Authorization Server](https://github.com/spring-projects/spring-security-samples/tree/2e3f349b/servlet/spring-boot/java/oauth2/authorization-server)
- [Spring 官方本地样例对应源码：Reactive OAuth2](https://github.com/spring-projects/spring-security-samples/tree/2e3f349b/reactive/webflux/java/oauth2)
- [Spring Security 授权服务器配置模型](https://docs.spring.io/spring-security/reference/servlet/oauth2/authorization-server/configuration-model.html)
- [Spring Security Reactive OIDC Logout](https://docs.spring.io/spring-security/reference/reactive/oauth2/login/logout.html)
- [Spring Security 7.1.2 原生 OIDC Logout Provider](https://github.com/spring-projects/spring-security/blob/7.1.2/oauth2/oauth2-authorization-server/src/main/java/org/springframework/security/oauth2/server/authorization/oidc/authentication/OidcLogoutAuthenticationProvider.java)
- [OAuth 安全最佳实践 RFC 9700](https://www.rfc-editor.org/rfc/rfc9700.html)
- [OIDC RP-Initiated Logout](https://openid.net/specs/openid-connect-rpinitiated-1_0.html)
