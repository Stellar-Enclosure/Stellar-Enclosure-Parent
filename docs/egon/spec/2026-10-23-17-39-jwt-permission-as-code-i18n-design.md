# Boot 4 / JDK 25：JWT 无 Session 身份与 Permission as Code 统一治理规格

| Field | Value |
| --- | --- |
| Document | 2026-10-23-17-39-jwt-permission-as-code-i18n-design.md |
| Template Version | 7；沿用仓库 RFC 结构与需求追踪格式 |
| Revision | 2；基于用户新增要求重设架构与范围 |
| Status | Accepted；用户已确认设计与 Plan，开始按计划实施 |
| Type | Architecture / Feature / Breaking Redesign |
| Complexity | Complex |
| Created | 2026-10-23 17:39 Asia/Shanghai |
| Updated | 2026-10-24 06:25 Asia/Shanghai；执行授权与进度关联更新，技术设计仍为 Revision 2 |
| Owner | mario |
| Repository | Stellar-Enclosure-Parent；跨仓库设计文档 |
| Scope | Boot 4/JDK 25；JWT 无框架 Session；必要状态 PostgreSQL；Java + React/TypeScript Permission as Code；统一注册/角色授权/字段读写；Tianshu 多语言元数据；CI/CD 与本地测试环境同步 |
| Source Requirement | 用户明确允许破坏式更新、项目未上线且无线上数据；禁止 Session，权威状态使用数据库；资源涵盖字段/page/API/component/button；权限字符与 ALL/ANY；自动 Manifest 注册；最新指定 React，不使用 Vue |
| Supersedes | 整体替代[上一版三阶段 Spec](2026-10-23-16-17-jianshen-oauth2-idp-sso-convergence.md)；旧版不再作为实施依据，尤其撤销其 Session/BFF Session、Redis 安全状态、旧 API 兼容和旧资源授权模型保留决定 |
| Related Specs | 历史 OAuth/RBAC/i18n 资料仅作现状证据，不得覆盖本轮用户的新决定 |
| Related Plans | [三阶段实施 Plan](../plan/2026-10-23-20-14-jwt-permission-as-code-i18n-implementation.md)；In progress，按用户批准实施 |

## 1. Summary

目标为 **Permission as Code + DevOps 自动注册 + RBAC 统一授权 + Tianshu 多语言元数据**。代码拥有权限定义、资源结构和资源到权限表达式；权限中心分配资源 ID、管理版本和角色授权；Tianshu 管理这些资源的多语言展示内容。

服务实例不保存跨请求登录上下文，不使用 HttpSession、WebSession、Spring Session、SessionRegistry、Redis Session 或以 opaque Cookie 查询长期 SecurityContext 的变相 Session。每个请求通过 JWT 还原请求期身份；OAuth 授权事务、Refresh 轮换、Consent、撤销、安全版本、授权快照、注册和发布等必要权威状态持久化到 PostgreSQL。

“无 Session”不等于 OAuth 协议没有状态，也不等于所有请求可以只验 JWT 签名。撤销和授权版本仍需数据库权威事实；数据库不可用时受保护操作拒绝。

本轮允许删除旧 API/DTO/SDK/角色资源授予路径，不做双轨兼容，不迁移线上数据。不会因此自动删除本地数据、重写已有迁移或开始实施。设计与实施 Plan 已确认；代码实施进度及中断位置按 Plan 记录。

## 2. Background and Current State

### 2.1 技术与职责基线

父 POM 已明确 Spring Boot 4.1.2、Java 25。本规格适配已完成的升级，不再沿用 Boot 3 / JDK 21 设计。当前业务前端均为 React + TypeScript；不引入 Vue，也不迁移现有前端框架。

用户产品命名：Jianshen = IdP；Shoubing = RBAC。物理目录仍保留历史相反命名，下表防止改错模块。本需求不要求仓库整体改名。

| 职责别名 | 当前物理位置 | HEAD |
| --- | --- | --- |
| DOC | Stellar-Enclosure-Parent | c2a3bff |
| IDP | tianquan-shoubing-service | 49122f8 |
| RBAC | tianquan-jianshen-service | b2e80d3 |
| META | tianshu-service | a7d0407 |
| EDGE | yuheng-service/stellar-enclosure-yuheng-edge-gateway | 7380a48 |
| SDK | web-sdk | d407317 |
| RBAC-W | tianquan-jianshen-web | 763b54b |
| META-W | tianshu-web | bf5ca46 |
| PORTAL | portal | f82568a |

基线来自本轮只读检查；实施前重验工作树和 resolved dependencies。当前实际代码是设计输入，不是必须兼容的目标。

### 2.2 关键代码事实

| Evidence | 当前实现 | 设计结论 |
| --- | --- | --- |
| EVD-001 | 父 POM Boot 4.1.2 / Java 25；平台父 POM 已有 annotationProcessorPaths | 新扫描器显式声明处理器，保留现有必要编译处理器 |
| EVD-002 | IDP 使用 HttpSessionRequestCache、HttpSessionCsrfTokenRepository、SessionAuthenticationStrategy | 不能只改 STATELESS；必须替换全部跨请求保存机制 |
| EVD-003 | EDGE 使用 WebSession 安全上下文/CSRF/授权请求存储与 Spring Session Redis | 移除旧 Session BFF；EDGE 保留无 Session OAuth 客户端/转发责任 |
| EVD-004 | 现有权限/撤销读路径以 Redis 为安全状态来源 | 本次安全权威状态与并发控制转 PostgreSQL |
| EVD-005 | RBAC 当前前端类型 MENU/ROUTE/ACTION/FIELD；权限仅 suggestedPermissionCode | 新角色授予及资源表达式是一项模型替换 |
| EVD-006 | RoleResourceGrantPage 直接提交 resourceIds，页面/按钮关联 API 按并集派生授权 | 删除该隐式授予路径，角色直接授予权限字符 |
| EVD-007 | 当前一致性脚本禁止 RolePermission/permissionIds | 必须同步替换旧约束和测试，不留两套授权事实 |
| EVD-008 | 前端 report:resources 读取 JSON；后端另有 register-application-catalog CLI | 统一成一个 Manifest schema、一个注册协议、同一个 CI/本地 CLI |
| EVD-009 | 前端 markStale 按 application + CI_REGISTRATION 处理缺席；后端 API 也使用该 source_type | 必须按 producer 所有权限定快照，消除跨端误废弃 |
| EVD-010 | Java 方法鉴权为逐项 ALL，缺少显式 ANY | 建立 Java/TS 共享的有版本纯函数语义 |
| EVD-011 | 已有字段读脱敏与显式写字段检查；不能自动覆盖所有入口 | 全面覆盖提交字段、序列化、导出与替代写入路径 |
| EVD-012 | Tianshu 是 scope/page/key 的草稿与发布中心，已有 CAS、Bundle、fallback | 复用语言治理，增加代码来源层和资源关联索引 |
| EVD-013 | Tianshu initialize 只补缺失页面；现有写接口依赖 USER 的 Rbac3UserDetails | 新增机器专用 source-import，不复用整页人工 draft/publish |
| EVD-014 | 现有语言加载器有身份隔离缓存和迟到响应防护 | 替换 sessionGeneration 含义，保留请求隔离与取消机制 |
| EVD-015 | 现有 GitHub/GitLab CI 未调用权限注册阶段 | 增加受控注册/激活阶段，PR 校验不持写凭据 |
| EVD-016 | 当前实际 RBAC 迁移已删除旧 Manifest 表，旧 api-and-manifest 文档有偏差 | 不把旧文档当成现存完整 Manifest 实现 |

均为源码事实，不是本轮编译、数据库或浏览器验证结果。

## 3. Goals and Non-goals

### 3.1 本次目标

- G-01：无 Session 的 JWT 认证与 SSO，保留 Authorization Code + PKCE + OIDC、Client Credentials 两条主线。
- G-02：每个受管资源有稳定 registrationKey、中心资源 ID、明确权限表达式和多语言引用。
- G-03：Java 注解与 React/TS 声明静态生成统一 Manifest；CI 与本地同步共用协议。
- G-04：角色授予权限字符；前端 UX Guard 和后端 API/字段强制鉴权语义一致。
- G-05：资源/权限/i18n 版本、幂等、差异、废弃、部署激活可追踪。
- G-06：Boot 4/JDK 25 原生组件接入与完整前后端管理能力。

### 3.2 排除项

NG-001：Vue。NG-002：AIoT、设备身份、AI 委托、Token Exchange。NG-003：LDAP/AD/SAML/外部身份联邦。NG-004：新增 MFA/Passkey/移动端长期登录产品。NG-005：Password/Implicit/Device Grant、通用动态客户端注册。NG-006：旧 Session/API/SDK 双轨兼容与线上数据迁移。NG-007：自动给角色授权或 CI 管理用户角色。NG-008：新分布式事务、通用工作流/审批平台。NG-009：全量重写无关服务发现、业务缓存或业务模块。NG-010：本轮代码、数据库、CI 执行、远端注册、服务启动和发布。

### 3.3 重新划分三个交付阶段

| 阶段 | 内容 | 完成边界 |
| --- | --- | --- |
| P1 身份与状态基础 | Boot 4/JDK 25；移除框架 Session；JWT 目的隔离；OAuth/SSO 流程状态 PostgreSQL；撤销/刷新正确性 | 登录与服务认证通过实际原生链测试，服务实例无会话依赖 |
| P2 权限与元数据模型 | Java/React/TS 声明；Manifest；权限字符角色授予；资源/producer/版本；Tianshu 来源与翻译分层；管理 API/UI | 代码定义和中心治理一致；候选注册、差异、幂等、元数据投影可测试 |
| P3 执行与交付 | 前端 Guard、API/字段强制鉴权、数据库快照/fence；CI/CD、本地测试环境同步、部署激活与验收 | 注册产物与运行构建匹配，后端安全边界生效，异常/并发/回滚有证据 |

这三阶段取代上一版阶段内容。P2 的候选登记不能提前作为 P3 已部署/已授权证明。

## 4. Requirements and Acceptance Criteria

| Requirement | Stage | 必须满足的要求 | Acceptance |
| --- | --- | --- | --- |
| REQ-001 | ALL | 最新范围和审核门槛优先 | AC-001：仅文档变更；React 纳入，Vue/远期项排除 |
| REQ-002 | P1 | 按已升级 Boot 4/JDK 25 和受管 Security API 实现 | AC-002：实际版本解析、编译和原生链测试，无旧框架配置复制 |
| REQ-003 | P1 | 不创建或依赖任何框架/变相服务器 Session | AC-003：无 Session Cookie、Session Repository 或 opaque 登录上下文查询 |
| REQ-004 | P1 | 本范围跨请求/跨实例权威状态全部 PostgreSQL | AC-004：无 Redis/进程内权威，故障拒绝，DB 并发可恢复 |
| REQ-005 | P1 | JWT 类型/audience/用途和浏览器凭据隔离 | AC-005：SSO/Access/ID/CSRF 不可互换，JS 不长期保存认证凭据 |
| REQ-006 | P1 | Authorization Code + S256/OIDC 使用一次性数据库事务关联 | AC-006：state/nonce/PKCE/Client/资源/浏览器绑定均有效 |
| REQ-007 | P1 | CC 为独立 SERVICE，不冒充 USER | AC-007：注册客户端仅拥有绑定应用/producer/环境的机器 Scope |
| REQ-008 | P1 | Code/Refresh/Consent/强度/新鲜度规则正确 | AC-008：无重复消费、半签发、虚假 STRONG 或 Scope 扩张 |
| REQ-009 | P1 | SSO 与退出基于 JWT 和数据库撤销 | AC-009：退出不依赖 SessionRegistry，复制的被撤销 JWT 也拒绝 |
| REQ-010 | P2 | 稳定资源 Key 与中心 ID 分离 | AC-010：同 Key 稳定 ID，URL/翻译/环境变化不生成新身份 |
| REQ-011 | P2 | 权限字符有唯一语义所有者，角色直接授予字符 | AC-011：无旧资源派生 API 授权，注册不替管理员授权 |
| REQ-012 | P2 | 覆盖 APP/MENU/PAGE/COMPONENT/BUTTON/API/FIELD | AC-012：受管资源有显式保护/公开/内部声明和 i18n 引用 |
| REQ-013 | P2 | ALL/ANY 与组外层 AND 语义统一 | AC-013：空集/未知规则拒绝，Java/TS 真值合同一致 |
| REQ-014 | P2 | Java 注解在编译期静态导出 | AC-014：不启动应用、不执行类初始化，继承/路径/字段可解析 |
| REQ-015 | P2 | React/TS 通过 AST 静态导出 | AC-015：不执行模块，不用正则猜测权限，动态不确定声明使构建失败 |
| REQ-016 | P2 | 唯一有版本 Manifest/schema/canonical hash | AC-016：产物可重现，服务端独立校验，生成端不带资源 ID |
| REQ-017 | P2 | producer 为持久所有权与快照边界 | AC-017：前端上报不废弃后端，局部/失败扫描不推导删除 |
| REQ-018 | P2 | 注册幂等、CAS、乱序与未知结果可处理 | AC-018：同操作同摘要同回执，异内容冲突，旧流水线不能覆盖新事实 |
| REQ-019 | P2 | Diff 识别权限授予面变化 | AC-019：新资源绑定旧权限、ALL→ANY、PUBLIC 化和字段放宽均可见 |
| REQ-020 | P2/P3 | 候选注册与部署激活分离 | AC-020：未激活不生效，激活/回滚均有新序号和明确版本 |
| REQ-021 | P3 | CI 与本地共用同一个 CLI/协议 | AC-021：PR 只读校验，测试环境手动同步与 CI 结果一致 |
| REQ-022 | P2/P3 | 注册身份与目标范围在服务端绑定 | AC-022：CI 不能跨 app/env/producer、不能授予角色权限 |
| REQ-023 | P2 | 每个资源和权限定义都关联 Tianshu 多语言元数据 | AC-023：中心可查询类型/Key/权限关联与文案来源，非仅存页面标题 |
| REQ-024 | P2 | 代码默认层、人工草稿、人工已发布覆盖分离 | AC-024：CI 不覆盖翻译或发布人工草稿，词条版本可追踪 |
| REQ-025 | P2/P3 | 跨中心使用数据库 Outbox、匹配回执与唯一激活指针 | AC-025：无跨库原子假设，无两个 latest 指针竞争 |
| REQ-026 | P3 | React 页面/组件/按钮/字段 UI 依权限字符控制 | AC-026：未知/加载失败默认隐藏或禁用，不能以 resourceId 绕开表达式 |
| REQ-027 | P3 | 后端每个受管 API 独立强制鉴权 | AC-027：绕过前端调用仍拒绝，PUBLIC 不清除其他边界 |
| REQ-028 | P3 | 字段读、脱敏、写入独立且覆盖真实提交集合 | AC-028：null/PATCH/嵌套/批量/导出/别名与替代入口无绕过 |
| REQ-029 | P3 | 授权快照与 fence 的版本一致性在数据库保证 | AC-029：过期快照不可用，撤权保证范围不夸大 |
| REQ-030 | P3 | 运行二进制绑定中心已激活的 policy digest | AC-030：旧代码不能执行新宽松策略，请求 Header 不能选择版本 |
| REQ-031 | P2/P3 | RBAC/Tianshu 前端管理与缓存按新模型完成 | AC-031：角色选择权限字符，来源只读，身份/版本切换拒绝迟到响应 |
| REQ-032 | ALL | 安全失败、审计和敏感信息处理一致 | AC-032：数据库故障不放行；无明文凭据/令牌日志 |
| REQ-033 | ALL | 允许破坏式替换，不保留冲突旧轨道 | AC-033：旧资源角色授予、Session API 和旧注册协议退出目标实现 |
| REQ-034 | ALL | 清洁环境部署，旧迁移不可改，无自动清数据 | AC-034：各 DB owner 单一必要新版本；本轮无 SQL 执行 |
| REQ-035 | ALL | 验证分层与追踪诚实 | AC-035：结构/单元/实际 DB/浏览器/CI 证据分别记录 |
| REQ-036 | P2 | RBAC 与 Tianshu 权威边界明确 | AC-036：翻译改变不改权限，资源关系不隐式授予角色 |

## 5. Constraints, Assumptions, and Decisions

### 5.1 本轮取代的决定

上一版“保留 Session BFF、保持旧 /bff/logout、Redis 会话/撤销、保证旧 API 兼容”均不再成立。新的身份/权限服务可以采用新 API/DTO/表结构；旧接口可删除，无需兼容层。仍遵守范围控制、现有合理工程风格、历史迁移不可变及用户审核门槛。

“有状态都基于数据库”针对本次服务端认证、授权、注册、发布、幂等、并发和审计权威状态。请求期 Authentication、React 页面状态、构建文件和不参与授权的展示缓存不是服务器 Session；安全正确性不能依赖它们。无关的服务发现/业务缓存不在本次重写范围。

### 5.2 核心决定

| Decision | 选择 |
| --- | --- |
| DEC-001 | React + TypeScript；不设计或安装 Vue 适配 |
| DEC-002 | IdP 保持 Servlet/SAS，EDGE 保持 Reactive；标准协议组件通过数据库/无 Session 适配扩展 |
| DEC-003 | 浏览器默认使用 HttpOnly JWT/Refresh Cookie；API/OpenAPI 使用 Bearer，按明确入口隔离 |
| DEC-004 | IdP SSO 凭据是独立 purpose/audience 的认证 JWT，固定绝对 TTL，不滑动续签 |
| DEC-005 | 授权码与轮换 Refresh 可使用高熵一次性值/摘要存储；不强迫所有协议凭据都改为 JWT |
| DEC-006 | RBAC 角色只授予 permissionCode；资源映射由代码权威声明 |
| DEC-007 | 逻辑引用为 business + application + key；物理唯一性为完整 catalogScopeId + key；producer 是所有者属性，迁移所有者不改变同一 scope 内资源 ID |
| DEC-008 | 环境/namespace/tenant 放同步目标信封，不进入稳定资源 Key 或跨环境携带资源 ID |
| DEC-009 | 同一 permissionCode 在应用内只有一个定义所有者；其他 producer 只能引用 |
| DEC-010 | 自动缺席处理限定成功完整 producer 快照；废弃与删除/停用分开 |
| DEC-011 | Tianshu 接受不可变来源候选版本；RBAC 持有唯一 catalog activation 指针 |
| DEC-012 | 同库本地事务 + Outbox + 幂等收据；不用分布式事务 |
| DEC-013 | 无线上迁移/旧协议兼容；本地数据操作仍须后续明确授权 |

### 5.3 审核重点

本 Spec 的 JWT Cookie、数据库 OAuth 事务、角色权限字符授予、生产者所有权和跨中心激活已由用户确认，按关联 Plan 细化执行顺序。现阶段不要求用户提供真实 Client Secret、数据库口令或测试环境地址。

## 6. Project Technology Context

- Java 25：使用现有 Maven Wrapper/父 POM 的 release=25。注解处理器必须显式登记，并与现有 Lombok/MapStruct 处理器共存；不得启用整个依赖 classpath 中的任意处理器。
- Spring Boot 4：使用当前 BOM 管理的 Spring Framework/Security、Jakarta 包、现有 Jackson 配置与错误风格；以实际解析版本校验 SPI，不沿用 Boot 3/旧 Security 示例。
- Spring Security：使用原生 FilterChain、AuthenticationProvider、AuthorizationManager、JWT Encoder/Decoder、OAuth2 授权服务扩展；不修改框架源码。
- React/TS：声明核心、类型与纯函数规则保持框架中立；本次仅提供 React Hook/Guard/Router/Form 适配。
- PostgreSQL：本范围所有权威状态、CAS、行锁、版本/快照、Outbox 与可恢复作业。首版授权和撤销检查使用权威读，不依赖 Redis 或陈旧缓存放行。
- 现有 ORM/数据访问按模块实际技术复用；不为“统一数据库状态”额外重写所有 ORM。

## 7. Architecture Design

### 7.1 目标架构

~~~mermaid
flowchart LR
    J[Java 注解 / 编译期处理器] --> M[标准 Permission Manifest]
    T[React / TS 声明与 AST] --> M
    M --> C[统一 CLI / CI]
    C -->|SERVICE JWT + 目标范围| R[RBAC 注册与治理]
    R --> D[(RBAC PostgreSQL)]
    D --> O[数据库 Outbox]
    O --> I[Tianshu 多语言来源导入]
    I --> L[(Tianshu PostgreSQL)]
    I -->|版本与摘要匹配回执| R
    R --> A[唯一 Catalog 激活版本]
    U[浏览器] --> E[无 Session EDGE]
    E -->|Code + PKCE + OIDC| IDP[JWT IdP]
    IDP --> P[(OAuth / 账号 PostgreSQL)]
    E --> API[资源 API]
    API -->|JWT + 当前权限快照| D
    U -->|指定 Catalog 版本语言包| I
~~~

### 7.2 无 Session 身份设计

禁止：HttpSession/WebSession/Spring Session、SessionRegistry、Session 保存的 SavedRequest/CSRF/AuthorizedClient，以及长期 opaque Cookie → 数据库 SecurityContext/用户 Token 仓库查询。

允许且必须：有界一次性 OAuth 事务、授权族、Consent、凭据与安全版本、撤销记录、幂等操作和审计。事务 ID 只关联一个短期流程，不能被业务 API 当作登录身份，不能滑动续期或装入长期 SecurityContext。

Servlet 设置 STATELESS 和不持久化 SecurityContext；Reactive 使用无 WebSession 的上下文/请求存储。每次请求由验证过的 JWT 重建请求期 Authentication，结束后清理。仅写 STATELESS 并保留旧 Session 组件不算完成。

### 7.3 JWT 与浏览器传输

| 凭据 | 用途 | 存储与校验 |
| --- | --- | --- |
| Access JWT | 某 Resource 的 USER/SERVICE API 调用 | 校验签名、typ、iss、aud、时效、主体/租户、授权族/安全版本 |
| IdP Authentication JWT | 证明刚才在 IdP 完成的认证，以便 SSO | 独立 typ/purpose，aud 仅 IdP；含 sub/issuer/auth_time/acr/jti/身份版本；固定绝对期限 |
| ID Token | OIDC Client 的认证结果 | aud 为 Client；不能作为 API Bearer |
| Refresh Token | 续期已批准的 OAuth 授权族 | HttpOnly Cookie 或服务端安全凭据；数据库摘要、代际、消费和撤销 |
| CSRF Proof | Cookie 写请求的防伪 | 独立目的、短时、随机，并绑定当前浏览器认证上下文与 Client |

JWT 不放完整角色图、所有权限或敏感资料。IdP Authentication JWT 不由 Access/Refresh 自动续活；真正重新认证才产生新的 auth_time 和新认证 JWT。密码复验仍是 PASSWORD，不假装 MFA/STRONG。

当前 Web 默认采用无 Session EDGE OAuth Client：Code/PKCE 交换在服务端完成；Access/Refresh 写入 HttpOnly、Secure、host-only Cookie，React 不读取、不写 localStorage/sessionStorage。Cookie 是凭据载体，不是服务器 Session ID。

多 Resource 不能共用一个通用 JWT。由服务端固定 appAlias/路由选择目标 audience 和 Cookie，Cookie 路径限制在对应应用 API/刷新入口，限制数量与总 Header 大小。不存在正确资源凭据时进入该资源授权，不能借用其他 audience。EDGE 向业务上游只转发选中的 Bearer，并剥离 Cookie 和伪造身份头。

直连 Bearer API 与浏览器 Cookie 入口按固定路径/域名策略区分；匹配入口之后采用唯一凭据模式，禁止失败后自动切换另一种。Cookie 写请求校验可信 Origin/CORS 和签名双提交 CSRF；刷新、退出、改密、Consent 不通过 GET 执行副作用。默认 SameSite=Lax + GET Code 回调；本期不默认支持跨站 form_post。Cookie Path 只减少暴露，不替代资源、主体和租户校验。

未登录的 login POST 同样防止 login CSRF：使用短期一次性预认证事务、随机浏览器绑定和专用 CSRF Proof；事务只能继续本次已验证授权请求，不能用于长期身份查询。认证后 CSRF 绑定当前 JWT/授权上下文与 Client，不只签一个固定用户名。

### 7.4 OAuth 与 SSO 的数据库状态

Authorization Code 主路径仍是标准授权码 + S256 + OIDC。身份平台登录页只完成本地身份认证并建立认证 JWT，然后继续授权请求；不得新增“用户名密码直接换业务 Access Token”的 Password Grant。

授权请求/回调事务保存：操作摘要、issuer/Client/resource、state/nonce/PKCE、精确回调、受控返回位置、浏览器绑定摘要、过期时间、消费状态。事务在校验可信 Client/回调后创建，短 TTL、一次性消费。PKCE verifier 需要恢复时加密存储，不写日志。不得用原始 Cookie 或任意 returnTo 查询/覆盖该事务。

SAS 的 Code/Client Credentials/Token/UserInfo/Revocation 原生组件继续复用；默认组件涉及 Session 的部分必须通过标准 Converter/Provider/Repository 扩展替换，不能认为官方演示天然无 Session。Consent 绑定数据库授权事务和已验证认证 JWT，而非 Session ID。

SSO：访问另一个当前应用时，IdP 验证认证 JWT 与数据库撤销/身份状态，决定是否可免再次输入凭据；另一个 Client 仍取得自己的资源授权。固定认证 JWT 到期后重新认证，业务 Refresh 不延长其 SSO 寿命。

退出当前应用：撤销该 Client 授权族并清除对应 Cookie。退出当前 SSO：撤销当前认证 JWT 的 jti 及数据库中关联的授权族，清除 IdP 凭据；其他独立认证 JWT 不被误伤。账号禁用/全部撤销：推进用户安全版本，使相关 JWT/授权族失效。删除 Cookie 本身不等于撤销。

OIDC RP-Initiated Logout 可通过 JWT/数据库适配实现，不使用 SID/SessionRegistry；GET 只验证/展示确认，实际撤销必须有可信 POST/CSRF 或已认证服务端协议调用。登记回跳精确匹配，不把失效 ID Token 当访问凭据。任意外部 RP 的通用 Back-Channel Logout 不在本期。

### 7.5 刷新并发和未知结果

数据库按授权族/代际原子消费；EDGE 的数据库操作记录协调跨实例并发，前端可用跨 Tab 协调减少重复，但它不是安全权威。

首版采取保守规则：数据库操作有 IN_PROGRESS/SUCCEEDED/FAILED/UNKNOWN/CLOSED 与短时租约、终止期限；只有获胜请求获得新凭据。同一代际确有 IN_PROGRESS 时，竞争请求返回明确冲突，不重复向 IdP 提交旧 Refresh，也不清除可能已更新的 Cookie。同 operationId 的查询/重试只返回原操作状态，不重新兑换或返回凭据；完成后用不同 operationId 提交旧代际属于重放，拒绝换取新凭据并按既定授权族撤销策略处理。Edge 崩溃、租约到期或提交结果未知时，关闭/撤销相关授权并要求重新认证，不能永久悬挂或盲目再提交。协调记录不保存可由 Cookie ID 长期提取的 SecurityContext/Token 仓库。

不承诺网络重试无感，也不承诺服务器能让浏览器拒绝乱序 Set-Cookie。账号切换必须先关闭旧浏览器认证上下文关联的授权族/撤销旧认证凭据，再建立新身份；多资源 Cookie 不能一部分仍为旧用户。迟到响应可能覆盖 Cookie，但下一次校验必须因旧授权关闭而拒绝，必要时重新登录，不能恢复旧身份。测试覆盖提交成功但响应丢失、响应乱序、重复请求和刷新/退出/切换竞争；失败响应不清除其他成功请求的新凭据。

### 7.6 权限资源与元数据的权威

RBAC 是 resourceKey→resourceId、permissionCode 定义、表达式、角色权限、版本/生命周期的唯一权威。Tianshu 是多语言来源文本、人工翻译草稿和已发布覆盖的唯一权威。两者通过稳定引用关联，不允许修改文案来改变授权，也不允许 Tianshu 的资源投影反向编辑权限表达式。

## 8. Permission as Code：声明与执行模型

### 8.1 资源类型、身份和覆盖

| type | 语义 | 声明位置 |
| --- | --- | --- |
| APP | 应用入口及资源集合根 | 应用权限契约 |
| MENU | 导航节点 | React/TS 导航声明 |
| PAGE | 页面及路由 | React/TS 路由声明 |
| COMPONENT | 有独立访问规则的业务组件/区域 | React/TS 资源声明 |
| BUTTON | 按钮/用户触发的业务动作 | React/TS 动作声明 |
| API | 后端接口操作及映射 | Java Controller/Service 注解与映射 |
| FIELD | 请求/响应模型字段及读写规则 | Java DTO 字段权威声明；React 引用绑定 |

受管范围包括对外 DTO/JSON 字段、业务表单/列表/详情字段、页面路由、有权限含义的组件和动作、所有被纳入业务 API 目录的操作。内部数据库列、纯装饰组件不自动变成公开资源；应明确 INTERNAL/PUBLIC/PROTECTED 分类。不能靠静态扫描猜出任意代码的业务含义：受管目录必须使用受约束声明和调用组件，配合覆盖检查、接口清单比对及集成测试。

OAuth/OIDC 自身协议端点以系统资源元数据登记，准入仍归原生协议认证，不能通过角色给某人“免 Client 认证”的权限。登录/健康等公开资源必须显式列出；公开文案不等于公开权限目录。

逻辑资源引用为 (businessCode, applicationCode, registrationKey)，Key 文本不含环境、租户 ID、中文名、URL、Java 类名、数据库 ID 或构建号。物理目录明确按 catalogScope=(tenantId,businessCode,applicationCode,namespaceCode,environment) 隔离；中心分配 catalogScopeId，资源唯一键为 (catalogScopeId,registrationKey)。此决定与 Tianshu scope 对齐，不建立可被任一租户覆盖的平台公共定义。同 scope 同 Key 的显示名/路径可版本化变化；type 或业务含义改变需新 Key 或显式治理动作。资源 ID 由中心生成且以字符串返回；跨 scope/环境相同逻辑 Key 不意味着共用物理 ID。

producerId 是定义所有者，不进入稳定 Key。本期默认一条定义只有一个 producer；迁移 producer 需明确的所有权转移操作，不能通过“先删除再抢占”取得同 Key。不同环境可以有不同物理 ID，Manifest 不携带测试环境 ID 推向其他环境。

### 8.2 权限字符与角色

permissionCode 是有稳定含义的原子授权能力，例如 order:read、order:create、order:amount:read、order:amount:write。物理唯一键为 catalogScopeId + code；角色授予明确绑定同一目录 scope，不因字符串相同跨租户、namespace、环境或应用共享。namespace 是稳定的目录配置空间，不使用 Pod 名或蓝绿部署槽位作为 namespace。

一个权限可被多个资源引用，一个资源可要求多个权限。注册 Key、权限字符、i18n Key 是三个不同标识，必须显式关联，不强制相等。角色管理写入权限字符集合，中心解析到内部 permissionId；资源关系仅用于治理/展示/影响分析，不再自动生成角色 API 权限。

已有“角色绑定页面/按钮资源 → 关联 API 并集授权”以及 suggestedPermissionCode/人工二次映射退出目标模型。代码拥有资源→权限表达式；管理员可以授权、停用或按策略治理，但不能在 UI 静默覆盖代码声明形成第二事实源。

新增资源引用已经授予某角色的权限，也会扩大持有者能力。Diff 必须识别这一变化，不能仅因 permissionCode 没变就判断无安全变化。权限字符不得删除后复用于不同业务语义。

### 8.3 ALL/ANY 的统一语义

受保护的每一组必须是非空、去重、已定义的 codes：

- ALL：本组所有权限都满足。
- ANY：本组至少一个权限满足。
- 组之间固定 AND；Java 类型、接口/继承、方法上的独立要求均保留。
- PUBLIC 只免除该组的权限字符判断，不移除身份、Tenant、OAuth Scope、资源有效性、数据权限等前置条件。
- 方法 PUBLIC 不能抹掉类型级保护；UI 结构父子关系不自动变成后端授权关系。
- 空集合、未知 code、缺少 mode、无法解析声明、未登记/停用资源、缺少有效版本都不能通过。

Java 与 TypeScript 使用同一版本的真值合同 fixture。任意 SpEL、JS、正则或自定义表达式执行不进入 Manifest；只使用已定义的枚举与集合运算。

### 8.4 Java 注解设计

以下是拟定声明语法示意，不是本轮已实现 API：

~~~java
@PermissionResource(
    key = "order.api.detail",
    type = ResourceType.API,
    labelPage = "order.catalog",
    labelKey = "api.detail.label")
@RequiresPermissions(mode = PermissionMode.ALL, codes = {"order:read"})
@GetMapping("/orders/{id}")
OrderDetail detail(@PathVariable String id) { /* business */ }
~~~

权限定义本身在同一应用的权威契约声明处登记 code、描述和 i18nRef；其他模块通过引用使用，不能各自重新定义同一 code。字段声明独立包含 plainRead、maskedRead、write 规则及明确 masker，不能用一个 permission 属性同时代表所有读写能力。

Java 处理器在编译期读取类型/注解/常量与 Spring Mapping 合并结果，输出目标目录的不可变片段；禁止启动 Spring、反射初始化业务类或调用应用网络。无法解析的动态路径/权限、未标记的受管字段、重复定义、跨模块缺失引用导致构建失败。

Java 25 下必须显式登记本处理器，并保留已有 Lombok/MapStruct 所需处理器。多轮处理、继承/接口/泛型/组合注解的解析结果与运行时统一鉴权器必须一致，不支持的组合明确拒绝，不能静默漏扫。

### 8.5 React / TypeScript 声明设计

声明集中到明确的 permissions.ts / resources.ts；用 TS AST 读取限定常量语法，不执行模块或任意函数：

~~~typescript
export const resources = defineResources([
  {
    key: 'order.page.list',
    type: 'PAGE',
    target: { route: '/orders' },
    requirement: { mode: 'ALL', codes: ['order:read'] },
    i18n: { pageCode: 'order.list', labelKey: 'title' }
  },
  {
    key: 'order.button.create',
    type: 'BUTTON',
    target: { pageKey: 'order.page.list', actionKey: 'create' },
    requirement: { mode: 'ALL', codes: ['order:create'] },
    i18n: { pageCode: 'order.list', labelKey: 'actions.create' }
  }
] as const);
~~~

defineResources/definePermissions 是 schema/类型和静态标记，不是构建时执行的任意 DSL。动态条件、网络值、运行期拼接、无法解析 import 及重复 Key 冲突使扫描失败。React JSX 通过已生成类型的 resourceKey 引用，不手写不受校验的权限字符串。

前端 FIELD 引用后端权威字段 Key，可声明本地表单/列绑定；不能对同一个业务字段建立第二套读写策略。页面到 API 的 calls 引用只作完整性检查与影响分析，不自动授予 API 权限。不引入 Vue 解析器/SDK/依赖。

### 8.6 后端字段强制边界

plainRead 满足则输出原值；否则 maskedRead 满足且 masker 合法则输出脱敏值；否则默认省略字段。masker 失败不回退原值；输出类型必须符合公开 JSON schema，不能把数值字段任意改成字符串或伪造 0。脱敏不得修改持久化实体本身。

WRITE 不隐含 READ。写入依据真实提交字段集合：缺席与显式 null 区分；覆盖 PATCH、嵌套对象、数组、批量、别名、派生/只读字段。任何越权字段在持久化前整体拒绝；未知属性拒绝，不能静默丢掉后部分成功。没有声明安全语义的 PATCH 操作不自动支持。

字段检查必须落在统一业务调用/绑定边界，不能只依赖前端 disabled 或普通 Jackson 返回路径。导出、下载、RPC/批处理、非 Jackson 输出和直接调用写入口需对应适配及测试；受管入口未接入时构建/验收失败。先按激活角色、继承和约束得到同一有效权限集合，再分别求值资源、数据和字段规则，外层 AND。不同组可以由不同角色授予的权限满足，不要求所有权限来自同一角色；禁止用某个资源组成功替代字段/数据组检查，本期不引入任意复合策略分支拼接。

## 9. Manifest 与版本注册合同

### 9.1 标准 Manifest

Manifest 只含源定义、引用和构建来源；目标环境在独立注册信封中。下例为前端片段，权限由后端权威 producer 定义：

~~~json
{
  "schemaVersion": "1.0",
  "application": {"businessCode": "trade", "applicationCode": "order"},
  "producer": {
    "id": "order-web",
    "kind": "REACT_TYPESCRIPT",
    "snapshotMode": "FULL",
    "ownedKeyPrefixes": ["order.page.", "order.component.", "order.button."]
  },
  "artifact": {
    "repository": "order-web",
    "commit": "<full-commit-sha>",
    "buildId": "<ci-build-id>",
    "version": "0.1.0"
  },
  "permissionDefinitions": [],
  "permissionReferences": ["order:read", "order:create"],
  "resources": [
    {
      "key": "order.page.list",
      "type": "PAGE",
      "target": {"route": "/orders"},
      "requirement": {"mode": "ALL", "codes": ["order:read"]},
      "i18n": {"pageCode": "order.list", "labelKey": "title"}
    },
    {
      "key": "order.button.create",
      "type": "BUTTON",
      "target": {"pageKey": "order.page.list", "actionKey": "create"},
      "requirement": {"mode": "ALL", "codes": ["order:create"]},
      "i18n": {"pageCode": "order.list", "labelKey": "actions.create"}
    }
  ],
  "resourceReferences": [
    {"key": "order.field.amount", "usage": "FORM_FIELD"}
  ],
  "messages": [
    {
      "pageCode": "order.list",
      "key": "title",
      "defaultLocale": "zh-CN",
      "defaults": {"zh-CN": "订单列表", "en-US": "Orders"}
    },
    {
      "pageCode": "order.list",
      "key": "actions.create",
      "defaultLocale": "zh-CN",
      "defaults": {"zh-CN": "新增订单", "en-US": "Create order"}
    }
  ]
}
~~~

示例不是可立即同步的真实产物。后端片段负责声明引用的权限和字段；解析引用时可使用同一候选发布集合或明确已登记版本，不能引用未知定义。

唯一 schema 约束 Java 导出、TS 导出、CLI、注册服务和测试；不得继续让 CLI payload 与 SDK type 各维护不同定义。canonical 规则明确对象键排序、集合去重/排序、UTF-8、换行、数字/字符串边界；ID 一律字符串。服务器独立重新计算摘要。

摘要分工：policyDigest 只覆盖权限/资源执行语义；metadataDigest 覆盖来源文本及引用；manifestDigest 覆盖完整规范内容与来源。人工翻译发布不修改 policyDigest。构建来源另有不可变 artifactDigest，不能把任意 commit 字符串当作可信发布资格。

### 9.2 目标信封和所有权

注册目标包含完整 catalogScope 与 producer；tenant 和可写范围由已验证 SERVICE JWT/客户端授权确定。请求体只作一致性断言，不是租户来源。资源、权限、producer revision、幂等、Outbox、Tianshu 收据、角色授予和激活 CAS 都绑定同一个 catalogScopeId，不能在某环节丢掉 namespace 或 environment。

同一应用多 producer 分别完整上报自身片段。ownedKeyPrefixes 由服务端登记授权决定，Manifest 自报不能扩大范围。跨 producer 的相同 Key 定义拒绝；引用与拥有明确区分。同一 permissionCode 只有一个定义所有者。

FULL 只在扫描成功、模块列表完整、覆盖校验通过时允许缺席比较。PARTIAL/扫描失败/未知引用/缺失模块不废弃任何旧资源。空产物默认拒绝执行全量废弃；确实清空 producer 必须显式声明清空意图及相应发布权限。

### 9.3 幂等、CAS 与 Diff

- operationId + 目标 + producer + manifestDigest 唯一绑定；同内容重放返回原回执，复用 operationId 携带不同内容返回冲突。
- expectedProducerRevision 与 expectedActiveRevision 各自 CAS；buildId/时间戳/commit SHA 不能代替数据库顺序。
- 数据库事务原子保存候选版本、diff、资源 ID 映射与 Outbox；不在该事务内调用 Tianshu。
- 客户端超时/提交结果未知先查询原 operationId，不换 ID 盲目再次 apply。
- Diff 包含 ADD/CHANGE/REFERENCE/DEPRECATE/RETIRE/OWNER_TRANSFER/CONFLICT；权限字符改义、ALL→ANY、删条件、PUBLIC 化、字段明文/写范围放宽、新资源绑定已授权权限均标记授权面变化。
- 可信分支/环境发布策略决定哪些变化可激活；本地测试凭据不能借 --force 绕过服务端范围。无需新建业务审批平台，但不能忽略变化风险。

### 9.4 候选、激活、废弃和回滚

~~~mermaid
stateDiagram-v2
    [*] --> VALIDATED
    VALIDATED --> REGISTERED: 本地事务与 Outbox
    REGISTERED --> METADATA_PENDING
    METADATA_PENDING --> READY: 匹配 Tianshu 收据
    READY --> READY: 可被多个激活集合引用
    REGISTERED --> FAILED: 不可恢复校验错误
    METADATA_PENDING --> METADATA_PENDING: 幂等重试
~~~

上图是单个 producerVersion 的登记状态；metadataReady 表示它达到 READY。另有完整 catalogScope 下的 ActivationSet，状态为 CANDIDATE/ACTIVE/SUPERSEDED。catalogActivationVersion 是该 scope 唯一运行目录指针，包含完整 producerVersion 集合与匹配收据。复用未变化的后端片段时，它仍可被新集合引用，不因旧 ActivationSet 被替代而失效。

注册成功不等于部署生效。CI 先登记候选并取得 metadataReady，再准备匹配构建、通过发布资格检查，最后 CAS 激活并切换流量。配置激活与外部部署不声称跨系统原子；失败保持旧版本或明确 fail closed，不运行未匹配策略。

FULL 缺席在登记时只生成候选版本 diff，不修改 ACTIVE 资源资格。DEPRECATED 是定义版本的提示；资源在新激活版本缺席时不能靠历史数据库行继续运行，旧部署能否运行取决于明确允许的版本集合。人工 DISABLED/RETIRED 是优先于所有有效版本的禁止状态，注册或回滚不能清除它。缺席不物理删除角色授权、共享权限或翻译；退役 code 不可改义复用。

回滚产生新的激活序号指向已验证版本，不倒退管理员角色分配、账号授权或人工翻译，也不自动复活已显式停用的权限。旧、新构建同时运行必须有明确允许的版本集合，不能取权限并集；首版优先受控切换，不能伪装为已解决任意滚动发布问题。

## 10. Tianshu 多语言元数据协同

### 10.1 资源全部纳入、权威不重复

Tianshu 增加资源来源索引，覆盖 APP/MENU/PAGE/COMPONENT/BUTTON/API/FIELD 和权限定义的展示信息。可按应用、环境、producer、类型、registrationKey、permissionCode 查询并编辑语言内容。

该索引中的 resourceId/key/type/权限关联/生命周期是 RBAC 的只读投影；Tianshu 不编辑授权表达式、不分配角色权限。每个资源至少有 labelKey，必要时有 descriptionKey/help/placeholder/validation 引用。Key 指向稳定的 pageCode + messageKey；同一个公共词条也有唯一来源所有者，其他 producer 只能引用。

### 10.2 三层文案与独立版本

| 层 | 谁拥有 | 何时运行生效 |
| --- | --- | --- |
| Code Source Version | 受权 producer 的 Manifest | 指定 catalogActivationVersion 所引用的 sourceVersion |
| Human Draft | 翻译/元数据管理员 | 不参与运行包 |
| Published Human Override | 人工发布流程 | 与指定源版本兼容时覆盖默认文本 |

source import 不能调用现有整页 replaceDraft/publish，不能推进人工草稿 revision 或把同页未发布编辑带上线。源文案变化标记待复核，不覆盖已有人工翻译。占位符集合不兼容时，该源版本忽略不匹配覆盖，回退相应默认文本，保留旧翻译与诊断；其他仍运行版本不受影响。

运行包可输出的 Key 集合由指定源快照决定；人工覆盖只影响该快照仍声明且兼容的 Key，不能把已移除的旧 Key 合并回来。旧覆盖保留供旧版本使用和人工治理。对每个 Key，顺序固定为请求 locale 的人工已发布覆盖 → 该 locale 源默认 → 页面默认 locale 的人工已发布覆盖 → 该默认 locale 源默认 → 稳定 Key。page 词条优先于 common；common 只补该 page 未声明的 Key。草稿永不参与合成。文案失败可用同版本默认文本，不改变权限结果。

### 10.3 跨中心一致性

RBAC 的候选注册与数据库 Outbox 同事务写入。Tianshu 在自己的本地事务保存不可变 sourceVersion=manifestDigest、资源投影和幂等回执。回执绑定 operationId、完整目标、producer、manifestDigest、metadataDigest。

metadataReady 仅证明候选来源可被解析，**不切换运行文案**。只有 RBAC CAS 激活 catalogActivationVersion；Tianshu 按该版本解析源层，不维护一个必须与 RBAC 同时切换的独立 latest 指针。

RBAC 提供受认证、只读、不可变的 ActivationDescriptor：完整 catalogScope、activationVersion、producer/sourceVersion 集合及摘要。Tianshu 通过该契约取得可信映射，可将结果只读投影到 PostgreSQL，但不另建 active 指针，也不接受浏览器自行拼装 producer 集合。资源来源索引同样按 sourceVersion 保存，候选导入不覆盖当前运行版本的类型、权限关联或生命周期显示。

~~~mermaid
sequenceDiagram
    participant CI as CI / 本地 CLI
    participant R as RBAC
    participant RD as RBAC DB
    participant T as Tianshu
    participant TD as Tianshu DB
    CI->>R: plan + register(expectedRevision)
    R->>RD: 候选/ID/diff/Outbox 原子提交
    R-->>CI: operationId / METADATA_PENDING
    RD->>T: source-import(目标 + producer + digest)
    T->>TD: 不可变源版本 + 幂等回执
    T-->>R: 匹配版本收据
    R->>RD: METADATA_READY
    CI->>R: activate(完整 producer 集合 + CAS)
    R->>RD: 新 catalogActivationVersion
~~~

乱序/重复消息不能推进不匹配版本。Tianshu 不可用时当前 ACTIVE 授权继续按原版本运行；新候选显示 pending，CI 不得将其报告为已完成激活。恢复后使用原 operationId 重试，无分布式事务。

### 10.4 React 加载与管理页面

共享 SDK 权限视图绑定 issuer/subject/完整 catalogScope/catalogVersion/authVersion/policyVersion/activeRoleContext/snapshotExpiresAt。401/403、版本冲突、角色激活/身份变化时丢弃相应权限视图并重取，不能只等 Manifest 版本变化。文案请求键还包含 pageCode/locale/认证请求代次，bundleVersion/ETag 必须覆盖 producer/sourceVersion 集合及 page/common 的 publishedOverrideRevision，草稿 revision 不参与。原 sessionGeneration 改为本地请求取消代次，保留迟到响应拒绝；它不是服务器 Session。

RBAC 管理页展示权限字符及关联资源/i18n 名称，角色选择的是字符集合。Tianshu 管理页展示源默认值、人工草稿、发布覆盖、来源版本和待复核提示。两边都能追踪同一资源 Key/ID；任何“按页面勾选”便利操作必须展示最终显式权限字符集合，不能恢复旧的关联 API 自动并集。

匿名请求只加载明确配置的登录/公共页包，不提供受保护资源或权限管理目录。其 scope 来自已验证的 Client/固定服务端配置，不允许调用方任意选择其他 tenant/namespace/environment。

## 11. Runtime Authorization

### 11.1 授权判定

USER 请求的允许条件为：

~~~text
JWT 验证
AND 账号/成员/授权族/安全版本有效
AND audience 与服务端目标资源一致
AND OAuth Scope 满足接口的粗粒度能力上界
AND 当前部署资源策略有效
AND ALL/ANY 权限表达式满足
AND 数据范围及对象关系允许
AND 字段读写规则满足
~~~

OAuth Scope 与 RBAC permissionCode 不混为一套“任一满足即可”。SERVICE 请求走声明允许的服务 Scope/Grant，不回退为 USER。PUBLIC 仅在显式声明的边界免除本组权限判断。

React PermissionGate/usePermission/路由守卫/受控按钮/字段控件消费同一声明与可信权限快照；未知、未加载或失效默认拒绝展示。绕过 UI 直接调用 API 必须仍由后端拒绝。

### 11.2 数据库授权快照与 fence

角色分配、角色权限、激活角色、资源策略及版本为数据库权威。可复用当前授权快照机制，但快照、生成任务、fence 和当前版本均落 PostgreSQL。

同一次鉴权读取一致的版本组合，不能先读旧权限再拼新资源规则。快照派生自明确源版本；JWT 不携带永久有效的权限全集。角色/权限变更不必重新发一份全权限 JWT，而是使数据库授权版本/快照生效或关闭 fence；未就绪时受保护请求拒绝/不可用。

权威读取使用能满足承诺的一致性来源，首版不以副本延迟或旧 Redis 缓存放行。多节点查询同一数据库事实，不要求粘性路由。

### 11.3 撤权与业务事务边界

同数据库同事务可在业务提交前检查/锁定所需版本。业务库与权限库不在同一事务时，只能保证规定鉴权点的权限有效；撤权发生在鉴权之后、业务提交之前仍有时间窗口。

敏感写入需明确提交前复核点和失败不落库规则；若业务要求跨库严格原子撤权，必须另行设计业务提交协议，不能声称单独 snapshot/fence 已消除所有竞态。本期不引入通用分布式事务。

### 11.4 构建与策略绑定

运行产物嵌入 producerId、buildId、manifestDigest、policyDigest；完成打包后才计算最终 artifactDigest，存于受信发布记录/构建证明，由部署控制面绑定到实例，避免把整个产物的摘要嵌入自身造成自引用。中心记录激活资格；实例只执行与自己构建匹配的有效策略。请求 Header、前端自报摘要或用户选择不能成为可信版本来源。

未注册、未激活、digest 不匹配或已停用时阻止相关实例承接请求或拒绝操作；不得只记日志后继续。前端一次加载周期使用一致 catalogVersion 的权限视图/文案，版本切换清缓存、取消旧请求；后端仍独立检查。

## 12. DevOps 与本地同步

### 12.1 唯一工具链

目标过程为：

~~~text
Java 编译期片段 + React/TS AST 片段
→ merge / schema validation / coverage / canonical hash
→ dry-run diff
→ register candidate
→ wait metadataReady
→ deploy matching artifact / non-business readiness
→ CAS activate catalog
→ protected-flow verification / evidence
~~~

本地与 CI 使用同一 CLI、Manifest 和注册 API，不启动业务应用扫描，不通过初始化全部 Spring Bean 获取目录。不得保留前端 JSON 手工上报与后端 DB CLI 两套权威协议。

激活前只检查产物/摘要、依赖、部署资格和不授予业务权限的 readiness；不得靠测试后门访问未激活资源。CAS 激活并受控切流后，再执行受保护业务流程验收。分别记录部署就绪、目录已激活、业务授权验收结果，失败用新的激活序号回滚到获准版本。

拟提供的命令语义为 scan、validate、diff、sync、status、activate；命令尚未实现。本地 sync 默认要求显式 --target test 与配置的受限目标，dry-run 不写入；apply 必须带同一摘要、预期版本和操作 ID。生产环境不能因切换 URL 就绕过服务端授权。

### 12.2 CI 阶段

| 流水线 | 动作 | 凭据 |
| --- | --- | --- |
| PR / 不可信分支 | 生成、校验、覆盖检查、Diff Artifact | 无注册写凭据 |
| 可信测试分支 / 测试环境手动作业 | 注册候选、等待投影、部署/激活、验证 | 仅绑定测试目标的 SERVICE Client |
| 已受控发布分支 | 经发布策略允许后对相应目标执行相同步骤 | 与测试隔离的目标绑定身份 |
| 本地开发 | 使用同一工具向测试环境刷新自己的 producer | 受限开发凭据或专用测试 SERVICE Client |

流水线 concurrency group 可按 environment/application/producer 串行，但服务器 CAS 仍必须存在。取消、旧流水线、失败扫描、未部署产物不会自动成为 ACTIVE。

### 12.3 注册身份与秘密

SERVICE JWT 必须验证正确 audience、专用 Scope、principalType、来源应用和允许的 target/producer。register、activate 与角色授权分离；注册身份不能给自己角色、修改别的 producer、选择任意 tenant。

Secret 来自受保护 CI Secret/本机安全凭据或受限文件，不能进入 Manifest、仓库、argv、日志、Diff Artifact。CLI 输出只含摘要、版本、差异与回执，不打印 Token。

首次部署只允许显式 one-shot bootstrap 建立最小注册身份与初始管理员授权；bootstrap 是独立操作者动作，不由普通注册自动创建超级管理员。无 Session 方案不新增匿名管理入口。

## 13. Interface and Operation Contracts

### 13.1 身份入口

以下是新目标接口族，不是对旧 /bff/session、/bff/logout 的兼容承诺；最终 URI 在实施 Plan 中按同一命名集中落地，不能同时保留冲突语义。

| Contract | 入口 / 参与者 | 规范 |
| --- | --- | --- |
| AUTH-01 | 浏览器启动/继续 Code 授权 | 创建一次性 SQL 事务；issuer/Client/resource/回调来自登记；不创建 Session |
| AUTH-02 | IdP 登录/Consent/受限改密 | JWT/预认证事务 + 无 Session CSRF；密码验证不直接签业务 Access Token |
| AUTH-03 | 标准 OAuth Token Endpoint | 仅两条主线及既有 Refresh；JSON 响应由标准协议处理 |
| AUTH-04 | 当前应用显式 Refresh | 固定 Client/resource 入口；CSRF、数据库代际与操作状态；禁止失败后自动重放写操作 |
| AUTH-05 | 当前身份/权限 bootstrap | 从 JWT 与数据库事实返回最小身份和有版本权限视图；不返回原始凭据 |
| AUTH-06 | 当前应用退出 / 当前 SSO 退出 | 明确撤销范围、SQL 结果与 Cookie 清理；副作用通过 POST |
| AUTH-07 | 内部身份安全状态/授权 Runtime | 机器身份绑定调用 Resource；用户证明来自已验证 JWT，不接受浏览器自报权限 |

Runtime 查询复用当前内部鉴权服务责任，不建立通用代理/Token Exchange。资源服务本地验证 JWT；通过受认证内部 Runtime 获取 owner 数据库的权威状态/权限。Runtime 独立验证调用服务的 audience/Scope 与目标 Resource、用户证明及目标 scope，不能只信一个 userId Header。IdP 自身状态查询在本地数据库终止，不形成递归认证调用。

账号禁用、权限变化的保证以 §11 的明确鉴权点为准。数据库/权威 Runtime 不可用时拒绝受保护请求。不同进程的信任边界可各自验证 JWT，同一边界内避免重复构建互相矛盾主体。

### 13.2 Permission Manifest 注册 API

路径为拟定的新协议，本轮不创建 Controller 或执行请求。

| API ID | 方法 / 路径 | 输入核心 | 输出 / 副作用 |
| --- | --- | --- | --- |
| API-001 | POST /api/v1/permission-manifests/plans | Manifest、完整 target、expectedProducerRevision、expectedActiveRevision | planId、摘要、差异、风险/冲突；不变更运行目录 |
| API-002 | POST /api/v1/permission-manifests/registrations | planId、同一摘要、operationId、预期版本 | 注册候选/ID 映射/Outbox；返回原子回执或冲突 |
| API-003 | GET /api/v1/permission-manifests/registrations/{operationId} | 操作标识 | 原回执与精确 pending/ready/failed，不由客户端自报 |
| API-004 | POST /api/v1/permission-catalogs/activations | 完整 producerVersion 集合、目标、artifact 发布证明、expectedActiveRevision | 新 activationVersion；不授予角色权限 |
| API-005 | GET /api/v1/permission-catalogs/versions | 受权目标/分页 | 不可变历史与当前指针 |
| API-006 | GET /internal/v1/permission-catalogs/{catalogScopeId}/activations/{version} | 绑定 scope 的服务身份 | 不可变 ActivationDescriptor，供 Tianshu/部署查询 |
| API-007 | PUT /api/v1/roles/{roleId}/permissions | 同 scope permissionCodes 完整目标集合、expectedVersion | 管理员显式角色授权，原子校验角色/约束/版本 |
| API-008 | GET /api/v1/authorization/effective-permissions | 当前身份与受权应用上下文 | codes、authVersion/policyVersion/activeRoleContext、catalogVersion、expiresAt |
| API-009 | POST /internal/v1/i18n/source-imports | 完整 scope、producer/sourceVersion、资源投影、源词条、operationId | Tianshu 本地事务保存不可变候选与幂等收据 |
| API-010 | GET /internal/v1/i18n/source-imports/{operationId} | 绑定 scope 的投影服务身份 | 来源/摘要匹配回执 |
| API-011 | 现有 Tianshu bundle/page draft/publish 责任 | 指定 catalogVersion、pageCode、locale / 人工 CAS | 新三层模型；生产者导入不调用人工发布 |
| API-012 | 资源/权限停用、退役、所有权转移管理操作 | 显式命令、引用检查、expectedVersion、管理权限 | 安全治理状态，普通 CI 不能自行撤销禁止状态 |

AUTH-07/API-008 如由服务代取用户视图，必须通过受信服务身份与原始用户证明绑定；不能让用户请求任意 subject/tenant。注册、投影、激活、角色授权是不同能力，不能共用一个“管理员万能 Scope”。

### 13.3 字段边界与失败语义

- registrationKey/producer/code 使用版本化 schema 的 ASCII 标识规则，区分大小写且拒绝仅大小写混淆的重复定义；code 最长 128、Key 最长 200、producer 最长 128。
- ALL/ANY 每组 1–64 个去重 code；URI/路径声明最长 2048；Manifest 有服务端有限大小/资源数量/嵌套深度限制，配置不能由请求扩大。
- 目标 scope 必须存在且启用；source owner、引用、字段模式和 i18nRef 必须完整。
- 注册无权限 403，身份无效 401；版本/operationId 内容冲突 409；结构/未知引用/不支持表达式 422；权威依赖不可用 503。协议 OAuth 错误仍遵循 OAuth，不套注册错误码。
- apply 只有在对应 plan 仍匹配摘要与预期版本时可写；plan 过期或任一权威版本变化需重新 diff。
- response 不含 Secret、Token、密码、PKCE verifier 或原始敏感业务字段；测试产物和日志遵循相同规则。

### 13.4 管理 UI

RBAC 管理 UI 必须具备：按 source/type/Key/permissionCode 查询，资源与权限映射，ALL/ANY/字段规则只读展示，Manifest 历史/Diff/候选/激活状态，明确的角色权限字符分配与影响预览。

Tianshu 管理 UI 必须具备：资源索引筛选、对应 Key/permissionCode/来源版本展示，label/description/字段文案编辑，人工草稿/已发布覆盖/源默认对照，源变化待复核和占位符冲突提示。权限策略字段不可在该页编辑。

现有 React 页面按新模型改造，不保留旧 resourceIds 角色授予页面或禁止 permissionCode 语义的旧一致性规则；管理权限仍由后端强制。

## 14. Database and State Design

### 14.1 权威存储与必要表族

名称是领域表族规划，实施时使用所属模块现有命名风格，不代表本轮已建表。

| Owner | 表族 / 事实 | 关键约束 |
| --- | --- | --- |
| IDP | 用户/凭据/成员/Client/Resource Grant/密钥与安全版本 | 当前身份权威；不存在 Session 表 |
| IDP | oauth_interaction、oauth_authorization、oauth_token、token_revocation | 事务单次消费、授权族版本、jti/凭据摘要、到期与撤销 |
| EDGE | oauth_client_transaction、refresh_operation | 只存一次性客户端协议/并发协调事实，短 TTL；不存长期 SecurityContext |
| RBAC | catalog_scope、producer_owner | 完整 scope 唯一；owner/前缀/目标授权 |
| RBAC | permission_definition、resource_definition、resource_requirement | scope 内稳定 Key/ID/code，唯一所有者，规则版本化 |
| RBAC | manifest_version、registration_operation、manifest_diff | 不可变内容、幂等/CAS、原始回执、候选差异 |
| RBAC | activation_set、activation_producer、active_catalog_pointer | 单 scope 激活指针、完整 producer 集合、单调序号 |
| RBAC | role_permission、既有用户角色/约束/激活角色事实 | 显式权限字符授予，不保留资源派生角色授权 |
| RBAC | authorization_state、effective_permission_snapshot、fence、Outbox | 版本一致、发布原子、未就绪拒绝 |
| META | source_version、resource_metadata_projection、source_message | scope + producer + sourceVersion 不可变，候选不覆盖运行投影 |
| META | translation_draft、published_override、bundle/version | 独立人工 CAS/发布，草稿不参与运行 |
| META | import_receipt、activation_descriptor_projection | 幂等与只读描述符；无第二个 active/latest |
| 各 owner | 现有审计与 Outbox | 同库本地事务和可靠重试 |

跨请求恢复需要的操作、锁/租约、幂等结果不能只存在 JVM/Redis。数据库身份存储并不意味着每个 JWT 都必须保存完整明文；使用摘要、必要元数据和受保护加密内容。私钥/Secret 使用现有加密或秘密管理，不写明文列/日志。

### 14.2 约束和关系

~~~mermaid
erDiagram
    CATALOG_SCOPE ||--o{ PRODUCER_OWNER : owns
    CATALOG_SCOPE ||--o{ RESOURCE_DEFINITION : contains
    CATALOG_SCOPE ||--o{ PERMISSION_DEFINITION : contains
    PRODUCER_OWNER ||--o{ MANIFEST_VERSION : publishes
    RESOURCE_DEFINITION ||--o{ RESOURCE_REQUIREMENT : requires
    PERMISSION_DEFINITION ||--o{ ROLE_PERMISSION : granted
    ACTIVATION_SET ||--o{ ACTIVATION_PRODUCER : pins
    MANIFEST_VERSION ||--o{ ACTIVATION_PRODUCER : referenced
~~~

数据库约束至少包括：scope 唯一、scope+resourceKey 唯一、scope+permissionCode 唯一、scope+producer+version 唯一、operationId+目标绑定、scope 激活序号单调、角色授权同 scope、源版本与收据摘要一致。

不跨数据库建立伪外键或声称跨中心原子提交。角色授予、Manifest 激活、人工翻译发布是独立版本轴，不得用一个 version 混用全部并发控制。

### 14.3 清理、失败与迁移

OAuth 短事务、CSRF 事务、Refresh 操作和撤销记录都有明确到期/终态清理规则；清理依据数据库时间与安全保留窗口，不依赖单节点进程存活。删除仍被有效部署/审计/角色引用的版本必须拒绝。

用户允许破坏式更新，因此不设计旧业务数据迁移和 API 兼容。已有 Flyway/managed SQL 历史文件仍不可修改；实施时按 IDP/EDGE、RBAC、META 各自独立数据库 owner 的逻辑变更追加必要版本，同一 owner 本次逻辑变更不拆成多个版本。不同数据库不伪装成一个跨库迁移文件。

仅在后续明确授权的空白/测试环境应用新设计。无线上数据不等于可以自动删除本机数据库、旧文件或其他任务数据；本轮不创建或执行迁移。

## 15. Code Change Surface and Design Patterns

### 15.1 模块范围

| 模块 | 目标改造 |
| --- | --- |
| 父 POM / 模块编译配置 | 已有 Boot 4/JDK 25 基线；显式登记 Java 导出处理器；不复制样例 SNAPSHOT 版本 |
| IDP Admin/Core/Starter | 移除 Session 认证持久化；JWT 登录证明、SQL OAuth 事务/撤销；标准 SAS 接口适配 |
| EDGE | 删除 WebSession/Session BFF 与 Redis 安全权威；无 Session Cookie/Bearer 桥接、SQL 一次性协议协调 |
| RBAC contract/core/starter/admin | 新资源/permissionCode/ALL/ANY、Manifest/注册/激活、DB Runtime、API/字段强制执行 |
| RBAC Java 注解处理器 | 编译期导出统一 IR/Manifest 片段，覆盖校验 |
| web-sdk | TypeScript schema/声明/AST CLI、React guards、统一 JWT transport、版本与缓存控制 |
| META service/web | 来源版本/资源索引/人工覆盖分层，SERVICE source-import，管理 UI 和版本 Bundle |
| RBAC web | 角色权限字符分配、资源/规则/Manifest/Diff/激活视图，替换旧资源授予模型 |
| 当前第一方 React 消费者 | 声明、类型化引用、页面/按钮/组件/字段 guards、多语言引用、认证调用替换 |
| 各仓库 CI | 同一 CLI 的生成/校验/注册/激活阶段与受保护凭据 |
| 旧注册脚本/一致性测试 | 删除冲突双轨，重写为新权威合同，不仅放松断言 |

不顺带重构 Tianshu 其他配置/服务发现、Yuheng 其他协议引擎或业务模块算法。真实受管资源需要的声明和统一入口接入属于本次必要改动。

Manifest schema 是唯一版本化源合同；Java/TS 类型及导出器必须通过同一 schema/样例合同验证。Java 处理器作为编译期制品，Node/TS AST 扫描器作为开发/CI 工具，不把编译器、Node 文件系统或解析依赖打进浏览器运行包。React Guard 只消费精简声明与纯函数，不运行扫描器。

### 15.2 采用与拒绝的模式

Permission as Code 是治理方式：代码声明 + 不可变产物 + 受控注册/激活；不是在服务端执行提交的代码。

采用现有标准扩展点的 Adapter，将数据库/声明模型接入 Spring Security；Java/TS 提取器都转换同一 IR。ALL/ANY 使用简单纯函数/枚举，不为每个权限创建 Strategy 类。已有业务规则合适时复用 Domain Service。跨中心投影复用 Outbox；不引入 Saga/分布式事务框架。

拒绝：双重人工资源映射、页面自动派生 API 授予、通用脚本表达式执行、以翻译服务替代授权、以 Session 改名为数据库登录上下文，以及为本次需求创建通用插件平台。

## 16. Test Design

### 16.1 验证层次

静态/schema/纯函数 → 实际框架组件和扫描器 → 实际 PostgreSQL 并发/事务 → 已授权的浏览器/CI/测试环境。Mock 可以隔离依赖，但不能把原生 Provider、实际 Repository 和注册权威层全部替换为成功返回后声称流程已验收。

本轮仅执行文档与示例检查。未来业务测试不得隐式启动外部环境；需要真实数据库、浏览器或远端注册的验证，待用户提供已启动环境或明确授权后进行。

### 16.2 Test Case Inventory

| Test | 层次 / 阶段 | 场景与判定 | Requirement |
| --- | --- | --- | --- |
| TEST-001 | 文档/ALL | 最新范围、React、无代码/远端注册/服务启动，旧 Spec 已被替代 | REQ-001 |
| TEST-002 | 构建/P1 | 实际 Boot 4/JDK 25/Security SPI、Jakarta 和显式注解处理器配置 | REQ-002 |
| TEST-003 | 原生链/P1 | 登录、授权、回调、API 均无 HttpSession/WebSession/Spring Session 持久化或 Session Cookie | REQ-003 |
| TEST-004 | 原生链/P1 | opaque 流程票据仅一次性使用，不能作为长期登录上下文或 API 凭据 | REQ-003 |
| TEST-005 | DB/故障/P1 | 权威 DB 不可用时拒绝；无 Redis/JVM 安全回退；操作租约恢复有终态 | REQ-004, REQ-032 |
| TEST-006 | 协议/P1 | Access/ID/Authn/CSRF JWT 交叉替换、错误 issuer/aud/typ/版本均拒绝 | REQ-005 |
| TEST-007 | 浏览器合同/P1 | 登录前 CSRF、Origin/CORS、Lax+GET 回调、Cookie/Bearer 入口隔离与多 Resource | REQ-005 |
| TEST-008 | 协议+DB/P1 | state/nonce/PKCE/回调/Client/resource/浏览器绑定篡改、过期和重复消费 | REQ-006 |
| TEST-009 | 浏览器/P1 | 两个当前应用通过认证 JWT SSO，各自资源 Token；认证 JWT 到期不由 Refresh 续活 | REQ-006, REQ-009 |
| TEST-010 | 协议+DB/P1 | CC 仅 SERVICE，目标与 Scope 受限，不产生 USER/ID/Refresh 或角色权限 | REQ-007 |
| TEST-011 | 协议+DB/P1 | Code 并发最多一次；签名/保存/Outbox 失败不半签发 | REQ-008 |
| TEST-012 | 并发/P1 | Refresh in-progress/成功后重放、崩溃、响应丢失、未知结果和终止期限 | REQ-008 |
| TEST-013 | 领域/P1 | PASSWORD 复验不成为 MFA/STRONG；auth_time/max_age 真实，Refresh 不改认证事实 | REQ-008 |
| TEST-014 | 协议+DB/P1 | 当前应用/当前 SSO/账号全部撤销范围正确，复制的旧 JWT 被拒绝 | REQ-009 |
| TEST-015 | 并发+浏览器/P1 | 旧用户刷新迟到响应与账号切换竞争，旧授权关闭，不恢复旧身份 | REQ-009 |
| TEST-016 | DB/P2 | 同 scope Key 保持 ID；显示名/URL变化不换身份；跨 scope/环境严格隔离 | REQ-010 |
| TEST-017 | DB/P2 | 重复 Key、type 改义、producer 抢占和非法转移被拒绝 | REQ-010 |
| TEST-018 | API/UI/P2 | 角色仅授予 permissionCode，旧 resourceIds 与页面派生 API 并集不存在 | REQ-011, REQ-033 |
| TEST-019 | API/P2 | 新登记权限默认无人获授予；CI 不能管理角色或恢复人工禁用 | REQ-011, REQ-033 |
| TEST-020 | 静态覆盖/P2 | APP/MENU/PAGE/COMPONENT/BUTTON/API/FIELD 和 PUBLIC/INTERNAL 明确覆盖 | REQ-012 |
| TEST-021 | 纯函数/P2 | Java/TS ALL/ANY 真值一致，空组/未知/mode异常不放行 | REQ-013 |
| TEST-022 | 集成/P2 | 组外 AND、多个角色合法合并、方法 PUBLIC 不覆盖类型保护 | REQ-013 |
| TEST-023 | 编译/P2 | Java 导出不启动 Spring、不执行静态初始化或网络 | REQ-014 |
| TEST-024 | 编译/P2 | Java 常量/继承/组合注解/Mapping/字段解析，未知动态声明构建失败 | REQ-014 |
| TEST-025 | AST/P2 | TS 限定常量/引用可解析，任意模块执行/动态拼接/缺失 import 拒绝 | REQ-015 |
| TEST-026 | React/类型/P2 | 路由/按钮/组件/字段使用声明 Key，动态未知资源无默认放行 | REQ-015 |
| TEST-027 | 构建/P2 | 相同源产物 canonical 输出一致，policy/metadata/manifest 摘要独立正确 | REQ-016 |
| TEST-028 | schema/P2 | 错误版本、超限、未知引用、非法 masker/输出类型/翻译引用均拒绝 | REQ-016 |
| TEST-029 | DB/P2 | 前端 FULL 不废弃后端 API 或其权限/词条，所有权不能自报扩大 | REQ-017 |
| TEST-030 | DB/P2 | PARTIAL/失败/缺模块/空产物不推导删除；候选缺席不改变 ACTIVE | REQ-017 |
| TEST-031 | DB/P2 | 同 operationId+hash 返回原回执含原 ID/计数，异内容拒绝 | REQ-018 |
| TEST-032 | 并发/P2 | 双流水线 CAS、旧任务、超时未知结果查询，不覆盖较新注册/激活 | REQ-018 |
| TEST-033 | Diff/P2 | 新增绑定旧权限、ALL→ANY、删条件/PUBLIC、字段明文/写扩张被识别 | REQ-019 |
| TEST-034 | 交付/P2/P3 | 候选 READY 不授予运行权限；激活前只非业务 readiness，激活后业务验收 | REQ-020, REQ-030 |
| TEST-035 | 交付/P3 | 最终 artifactDigest 在打包后校验，伪造 Header/前端自报摘要不能选策略 | REQ-020, REQ-030 |
| TEST-036 | CLI/P3 | 本地测试目标与 CI 同一 Manifest/API/结果；dry-run 无写入 | REQ-021 |
| TEST-037 | CI/P3 | PR 无写秘密，可信分支才注册；取消/未部署构建不激活 | REQ-021 |
| TEST-038 | 授权/P2/P3 | 注册身份不能跨 tenant/business/app/namespace/env/producer | REQ-022 |
| TEST-039 | 授权/审计/P2/P3 | 注册 Scope 与角色管理隔离；Secret/Token 不在 argv/log/artifact | REQ-022, REQ-032 |
| TEST-040 | META/P2 | 七类资源与权限定义全部有来源索引/i18nRef/中心 ID 关联 | REQ-023 |
| TEST-041 | META/DB/P2 | CI 来源更新不覆盖人工 draft/published override、不推进人工 revision | REQ-024 |
| TEST-042 | META/P2 | 占位符变化、Key移除、page/common/locale 优先级、旧版本覆盖兼容 | REQ-024 |
| TEST-043 | 跨中心/P2/P3 | 重复/乱序 Outbox、目标或摘要不符回执不能推进 READY | REQ-025, REQ-036 |
| TEST-044 | 跨中心/P2/P3 | 可信 ActivationDescriptor、无第二 latest；Tianshu 失败不改变授权 | REQ-025, REQ-032 |
| TEST-045 | React/P3 | 完整 scope+auth/policy/role/expiry 与翻译版本缓存，401/403/切换拒绝迟到响应 | REQ-026, REQ-031 |
| TEST-046 | API/P3 | 绕过前端直接访问、缺声明/未知资源、Scope/数据边界不满足均拒绝 | REQ-027 |
| TEST-047 | 字段读/P3 | plain/masked/省略、脱敏失败、JSON 类型、实体不被污染 | REQ-028 |
| TEST-048 | 字段写/P3 | 缺席/null/PATCH/嵌套/数组/别名/未知/批量字段整体拒绝且无部分写入 | REQ-028 |
| TEST-049 | 替代入口/P3 | 导出/下载/RPC/批处理/非Jackson/直接服务调用不绕过字段与资源规则 | REQ-028 |
| TEST-050 | DB/P3 | 一致快照/fence、版本错配/权限撤销、同库及跨库保证边界 | REQ-029 |
| TEST-051 | 部署/P3 | 复用未变 producer、明确旧新版本集合、回滚不复活停用或回滚管理员授权 | REQ-030 |
| TEST-052 | UI/P2/P3 | RBAC 权限字符分配与来源只读；Tianshu 源/草稿/发布覆盖管理完整 | REQ-031 |
| TEST-053 | 文档/迁移/ALL | 空白环境策略、各 owner 单一必要版本、旧脚本字节不改、无自动删数据 | REQ-034 |
| TEST-054 | 验收/ALL | 原生链/实际DB/浏览器/CI证据分层；未运行不算成功 | REQ-035 |

### 16.3 必要测试数据

至少两个 tenant、两个 namespace、test/prod 两个环境、两个应用、每应用前后端两个 producer、两个用户、多激活角色、不同 Scope 的 SERVICE Client、七类资源和明文/脱敏/不可读/不可写字段。

同一个逻辑 Key 在不同 scope、同一 permissionCode 被多个资源引用、已授权字符增加新 API、人工草稿未发布时 CI 导入、只发布翻译而 Manifest 不变、更新前端而复用后端 producer，均为必测组合。

## 17. Non-functional and Security Design

### 17.1 有界协议与状态

| 项目 | 首版建议合同 |
| --- | --- |
| Authorization Code | 短时、一次性；默认 60 秒，上限 120 秒 |
| 登录/Code 关联与受限改密事务 | 默认 5 分钟，完成/失败终态不可恢复为身份 |
| IdP 认证 JWT | 固定绝对期限，默认 8 小时；不可由业务 Refresh 滑动续签 |
| USER/SERVICE Access JWT | 默认 5 分钟，配置上限 10 分钟 |
| 当前 Web Refresh 授权族 | 固定绝对期限，默认 8 小时；轮换不延长 |
| CSRF Proof | 短时、绑定目的与浏览器/Client；不得作为访问凭据 |
| Refresh 协调操作 | 有短租约和最终截止；租约过期/未知不能再次提交旧 Refresh |
| Manifest/源版本 | 不可变并有大小/条目/引用边界；被有效部署引用时不清理 |
| 前端权限缓存 | 有明确版本和 expiresAt；仅 UI，不是后端放行依据 |

这些值随新版设计一并确认，允许破坏旧默认值。实现不硬编码绕过配置上限。认证 JWT 不需要为持续刷新读取/保存服务器会话。

Access 已过期但 Refresh 仍有效时，CSRF 获取可通过严格验证该 Refresh 的 Client/浏览器绑定返回专用 CSRF Proof，不消费 Refresh、不签 Access、不返回业务身份数据；不得形成“先有有效 Access 才能刷新”的循环。

### 17.2 失败处理

认证/授权/版本/数据库错误有明确区分，不能把 503 当成无权限名单返回后继续。未知 Resource 或策略缺失不当 PUBLIC。翻译失败允许安全展示降级，不能使 API 或字段降级为可访问。

时间、租约和截止使用可测试的服务端 Clock/数据库事实，不以浏览器时间决定权限。恢复 worker 使用数据库领取/CAS/幂等，不依赖某个节点内存锁。

### 17.3 不夸大一致性和安全效果

不声称 JWT=完全无状态系统、不声称隐藏按钮=安全、不声称 HttpOnly 防止所有 XSS、不声称数据库 fence 自动提供跨业务库原子撤权，也不声称登记成功=实际部署成功。

默认策略是受保护操作 fail closed；可用性代价和登录重试必须如实显示。首版不加入未经验证的缓存宽限、Refresh重放宽限或广泛 PUBLIC 兜底。

## 18. Delivery, Migration and Review Boundaries

### 18.1 三阶段出阶段条件

| 阶段 | 出阶段条件 |
| --- | --- |
| P1 | Boot/JDK 实际构建通过；无 Session 依赖；Code/CC/JWT/SQL 状态、CSRF、SSO 与撤销合同通过；不能只验证普通 API Stateless |
| P2 | 七类资源、权限字符角色授予、Java/TS导出、统一Manifest、producer、版本/差异/幂等、Tianshu分层和管理API/UI通过 |
| P3 | 当前应用全部接入；后端 API/字段独立强制；CI与本地测试环境同步一致；候选/激活/实际部署匹配；运行证据完整 |

阶段可以产出代码和测试，但未达到完整安全前置条件的应用不得承接业务流量。新增权限在管理员显式授予前默认没有角色获得，不能为了验收方便给所有用户通配权限。

### 18.2 破坏式更新范围

目标实现删除旧 Session 路线、旧 BFF 会话 API、旧前后端分裂注册协议、旧 suggestedPermissionCode 人工映射和角色资源→API派生授权。旧数据无需在线迁移；可在获准清洁环境按新模型初始化。

旧 Spec 不再作为兼容约束。清洁环境安装、初始机器身份与管理员 bootstrap、CI秘密配置等由后续实施/部署步骤显式执行，本轮不做。

### 18.3 主要风险与确定处理

| Risk | 处理 |
| --- | --- |
| 无 Session 仅改配置但底层仍保存 SecurityContext | 静态依赖、实际链与 Cookie 负向测试共同验收 |
| producer/tenant/namespace 在某一步丢失 | 完整 catalogScopeId 贯穿所有约束、收据和激活 |
| 新资源绑定旧权限造成隐式扩权 | 作为安全 Diff 与受信发布资格检查 |
| 代码源同步覆盖人工翻译 | 三层内容与独立版本，按精确源版本合成 |
| 双库激活不一致 | RBAC 唯一指针 + 不可变 ActivationDescriptor，不用两个 latest |
| 旧二进制执行新策略 | 内嵌 policy/manifest 标识 + 外部 artifactDigest 发布证明 |
| Refresh/账号切换导致旧凭据回写 | 关闭旧授权、DB版本拒绝；接受重新登录，不能恢复旧身份 |
| 大量字段“声明了”但执行器漏覆盖 | 实际提交字段集合、替代输出/调用路径与强制接入测试 |
| Boot 4/JDK 25 处理器/序列化/SPI差异 | resolved版本与真实编译/框架测试，禁止照抄旧样例 |
| 重构扩大为其他平台治理 | 以 §3 排除项和 §15 变更面审查，超出先回到审核 |

用户已确认这份新版的完整设计，包括 JWT Cookie/数据库协议状态、catalogScope、角色权限字符、翻译来源分层及版本激活。后续实施按已批准 Plan 推进，没有可由实施者自行扩张的远期功能选项。

## 19. Traceability Matrix

| Requirement | Acceptance | 设计 | 计划验证 |
| --- | --- | --- | --- |
| REQ-001 | AC-001 | §1、§3、§20 | TEST-001 |
| REQ-002 | AC-002 | §2、§6 | TEST-002 |
| REQ-003 | AC-003 | §7.2 | TEST-003、TEST-004 |
| REQ-004 | AC-004 | §7、§14 | TEST-005 |
| REQ-005 | AC-005 | §7.3 | TEST-006、TEST-007 |
| REQ-006 | AC-006 | §7.4 | TEST-008、TEST-009 |
| REQ-007 | AC-007 | §7、§12.3 | TEST-010 |
| REQ-008 | AC-008 | §7.4–7.5 | TEST-011、TEST-012、TEST-013 |
| REQ-009 | AC-009 | §7.4–7.5 | TEST-009、TEST-014、TEST-015 |
| REQ-010 | AC-010 | §8.1 | TEST-016、TEST-017 |
| REQ-011 | AC-011 | §8.2 | TEST-018、TEST-019 |
| REQ-012 | AC-012 | §8.1、§8.4–8.5 | TEST-020 |
| REQ-013 | AC-013 | §8.3 | TEST-021、TEST-022 |
| REQ-014 | AC-014 | §8.4、§15 | TEST-023、TEST-024 |
| REQ-015 | AC-015 | §8.5 | TEST-025、TEST-026 |
| REQ-016 | AC-016 | §9.1 | TEST-027、TEST-028 |
| REQ-017 | AC-017 | §9.2 | TEST-029、TEST-030 |
| REQ-018 | AC-018 | §9.3 | TEST-031、TEST-032 |
| REQ-019 | AC-019 | §9.3 | TEST-033 |
| REQ-020 | AC-020 | §9.4、§12.1 | TEST-034、TEST-035 |
| REQ-021 | AC-021 | §12 | TEST-036、TEST-037 |
| REQ-022 | AC-022 | §12.3、§13 | TEST-038、TEST-039 |
| REQ-023 | AC-023 | §10.1 | TEST-040 |
| REQ-024 | AC-024 | §10.2 | TEST-041、TEST-042 |
| REQ-025 | AC-025 | §10.3 | TEST-043、TEST-044 |
| REQ-026 | AC-026 | §8.5、§11 | TEST-045 |
| REQ-027 | AC-027 | §11.1 | TEST-046 |
| REQ-028 | AC-028 | §8.6 | TEST-047、TEST-048、TEST-049 |
| REQ-029 | AC-029 | §11.2–11.3 | TEST-050 |
| REQ-030 | AC-030 | §11.4、§9.4 | TEST-034、TEST-035、TEST-051 |
| REQ-031 | AC-031 | §10.4、§13.4 | TEST-045、TEST-052 |
| REQ-032 | AC-032 | §13.3、§17 | TEST-005、TEST-039、TEST-044 |
| REQ-033 | AC-033 | §5.1、§18.2 | TEST-018、TEST-019 |
| REQ-034 | AC-034 | §14.3 | TEST-053 |
| REQ-035 | AC-035 | §16、§20 | TEST-054 |
| REQ-036 | AC-036 | §7.6、§10 | TEST-043 |

## 20. Review and Acceptance

### 20.1 审核状态

**新版 Spec：Accepted。关联 Plan：In progress。已进入代码实施；三个 subagent 因使用额度限制中断，各项代码与验证状态以 Plan 执行记录为准。**

用户于 2026-10-23 20:14 明确“确认，开始写plan吧”。据此记录设计批准并编写关联 Plan；该次仅更新文档；随后用户又明确批准按 Plan 实施并发开发，当前进度以 Plan 执行记录为准。此前旧版 Spec 的 Superseded 状态保持不变。

原 NG-010/AC-001 中“本轮仅文档”的描述对应设计审核阶段；本轮代码实施已经用户明确授权。数据库、浏览器、远端注册和项目启动仍遵守 Plan 的明确环境与验证边界。

### 20.2 文档检查

已执行文档检查：20 个章节、36 条需求与验收、54 个计划测试的追踪闭合；22 个本地引用目标存在；1 个 Manifest 示例 JSON 可解析；三阶段和排除项一致；Markdown 围栏/表格与 Git 空白检查通过。已完成认证状态、权限模型和跨中心版本的交叉审查，并修正发现的设计矛盾。旧 Spec 标为被替代；本记录不表示业务实现通过验证。

该检查不证明真实扫描器、JWT 无 Session、数据库事务、字段执行、CI 注册或 SSO 已实现。当前工作区没有历史 validate_spec.py，不能声称通过该历史 strict validator。

### 20.3 阶段验收规则

每阶段分别提交静态/构建/框架组件/真实数据库/浏览器/CI 证据。未运行项保持 Not run 或 Runtime unverified。扫描成功不等于 API 已强制鉴权；注册成功不等于已激活；metadataReady 不等于文案已切换；用户接口通过不等于字段/替代路径无绕过。

只要必要安全合同、实际框架行为或必需运行验收未完成，就不能宣告对应阶段全部完成。不得为了展示效果设置通配权限或停用鉴权。

### 20.4 真实源码与参考

- [父 POM：Boot/JDK 基线](../../../pom.xml)
- [平台编译器配置](../../../platform-parent/pom.xml)
- [当前 IdP Session 配置](../../../../tianquan-shoubing-service/stellar-enclosure-tianquan-shoubing-admin/src/main/java/top/egon/cola/platform/tianquan/shoubing/admin/oauth/config/AuthorizationServerConfiguration.java)
- [当前 EDGE WebSession 配置](../../../../yuheng-service/stellar-enclosure-yuheng-edge-gateway/src/main/java/top/egon/cola/component/yuheng/edge/config/EdgeSecurityConfiguration.java)
- [当前 Java 方法鉴权](../../../../tianquan-jianshen-service/stellar-enclosure-tianquan-jianshen-starter/src/main/java/top/egon/cola/platform/tianquan/jianshen/starter/security/Rbac3MethodAuthorizationManager.java)
- [当前字段读执行器](../../../../tianquan-jianshen-service/stellar-enclosure-tianquan-jianshen-starter/src/main/java/top/egon/cola/platform/tianquan/jianshen/starter/field/Rbac3FieldPropertyWriter.java)
- [当前字段写执行器](../../../../tianquan-jianshen-service/stellar-enclosure-tianquan-jianshen-starter/src/main/java/top/egon/cola/platform/tianquan/jianshen/starter/field/Rbac3FieldWriteAuthorizationComponent.java)
- [当前 CI 注册服务](../../../../tianquan-jianshen-service/stellar-enclosure-tianquan-jianshen-admin/src/main/java/top/egon/cola/platform/tianquan/jianshen/admin/registration/ci/service/CiResourceRegistrationService.java)
- [当前缺席处理](../../../../tianquan-jianshen-service/stellar-enclosure-tianquan-jianshen-admin/src/main/java/top/egon/cola/platform/tianquan/jianshen/admin/registration/ci/service/JpaCiResourceRegistrationStore.java)
- [当前后端目录注册](../../../../tianquan-jianshen-service/stellar-enclosure-tianquan-jianshen-admin/src/main/java/top/egon/cola/platform/tianquan/jianshen/admin/authorization/resource/service/GlobalResourceCatalogService.java)
- [当前前端注册脚本](../../../../tianquan-jianshen-web/scripts/report-rbac-resources.mjs)
- [当前角色资源授予页](../../../../tianquan-jianshen-web/src/features/role/RoleResourceGrantPage.tsx)
- [当前旧模型一致性脚本](../../../../tianquan-jianshen-web/scripts/verify-tianquan-jianshen-conformance.mjs)
- [Tianshu 多语言说明](../../../../tianshu-service/docs/page-i18n.md)
- [Tianshu 页面服务](../../../../tianshu-service/stellar-enclosure-tianshu-admin/src/main/java/top/egon/cola/component/tianshu/admin/service/i18n/DdcI18nPageService.java)
- [Tianshu 当前权限校验](../../../../tianshu-service/stellar-enclosure-tianshu-admin/src/main/java/top/egon/cola/component/tianshu/admin/service/i18n/DdcI18nScopeValidator.java)
- [Tianshu 当前初始化](../../../../tianshu-service/stellar-enclosure-tianshu-admin/src/main/java/top/egon/cola/component/tianshu/admin/service/i18n/DdcAdminUiI18nService.java)
- [Tianshu 当前语言表](../../../../tianshu-service/stellar-enclosure-tianshu-admin/src/main/resources/db/egon-mp/V20261022_001__tianshu_page_i18n.sql)
- [当前多语言 SDK](../../../../web-sdk/packages/stellar-enclosure-web-shared/src/i18n/pageI18n.ts)
- [当前 React 权限声明类型](../../../../web-sdk/packages/stellar-enclosure-tianquan-jianshen-react-sdk/src/types.ts)
- [当前 React 动作 Guard](../../../../web-sdk/packages/stellar-enclosure-tianquan-jianshen-react-sdk/src/guards/ActionGuard.tsx)
- [Spring Security 认证持久化与无状态](https://docs.spring.io/spring-security/reference/servlet/authentication/session-management.html)
- [Spring Security Authorization Server 扩展点](https://docs.spring.io/spring-security/reference/servlet/oauth2/authorization-server/configuration-model.html)
- [Maven 显式注解处理器配置](https://maven.apache.org/plugins/maven-compiler-plugin-4.x/examples/annotation-processor.html)
- [OAuth 安全最佳实践 RFC 9700](https://www.rfc-editor.org/rfc/rfc9700.html)
