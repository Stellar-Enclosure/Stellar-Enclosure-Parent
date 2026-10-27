# Tianquan 权限工程优化：基线与验证

记录日期：2026-10-27。状态：**离线工程改动和定向回归完成；真实环境测量与发布验收未执行**。未启动服务、数据库、容器或浏览器，未执行真实注册、激活、迁移、数据清理、提交或发布。

## 源码基线

| 仓库 | 本次开始时 HEAD |
| --- | --- |
| tianquan-jianshen-service | `14fdade65cfd82068f64b1b85c6f01aa72e965c1` |
| tianquan-shoubing-service | `bb59c718157ca15aa32e8d5877c19f2f85c357d5` |
| tianquan-jianshen-web | `0373c365f8748d5f6e83db7030b428ccf4da5fd5` |
| tianquan-shoubing-web | `bd0a8f4453151a96bc186d5113b855c4d23acaa9` |
| web-sdk | `36e577a5def74761b22eedd6c8388340ec00c7a8` |

以上是实施开始时的 HEAD。离线构建和测试发生在后续改动尚未提交时，因此其本地制品不是下面提交的正式构建证明。执行期间 Components 代码生成器存在其他工作，未纳入本任务。

## 可核对的前后对比

选取角色权限保存操作的声明，分别统计改动前 HEAD 与当前源码：

| 对象 | 之前 | 当前 | 统计口径 |
| --- | ---: | ---: | --- |
| 前端角色权限字符手写字面量 | 5 | 0 | permissions、resources 和角色权限声明中的 read/manage 两个字符；现通过固定 Manifest 生成引用 |
| 前端 5 个角色授权 DTO FIELD Key 手写字面量 | 10 | 0 | 原 FORM_FIELD 和 DTO 分组各一份；现在使用生成引用和同一组显式字段声明 |
| 后端 manage 字符手写字面量 | 13 | 1 | 原 Service 常量/返回字段及 DTO 5 个字段；现在由域常量引用 |
| 角色按钮、权限引用和字段用途所在前端声明文件 | 3 | 1 | 针对本操作的声明集中在 `rolePermissionResources.ts`；原有公共清单仍用于其他业务 |
| 两个前端 CI 适配器 | 各 279 行重复实现 | 各 80 行固定工具启动器 + SDK 共用 279 行实现 | 保留首次读取固定 SDK commit 的独立启动与信任检查 |
| 本地后端与前端构建入口 | 2 | 2 | 前端扫描自动生成引用，无需再手工执行生成命令；新增一次性的后端 Manifest 路径配置 |

新增一个完整业务操作的“8 个文件 → 约 7 个文件”仍是基于当前文件结构的估算，本次没有虚构一个真实新业务操作来声称已实测该数字。注册、显式激活与角色授予仍为不同操作。

## Manifest 与制品

以下均为本地离线证据，完整 manifestDigest 因 buildId/commit 和产物变化可能不同；比较的是规范化的策略和元数据投影。两个 Java 制品在隔离源码副本与隔离 Maven 仓库构建；分别核对了另一个服务的更新后 Starter JAR 已嵌入，未覆盖本机 Maven 制品。

| producer | 策略 digest 前后 | 元数据 digest 前后 |
| --- | --- | --- |
| Jianshen Java | `0d59473bfc82df31968e9b94992d25111f551f8a4d60c2ccbf75dd52aa827cf4`，相同 | `43e0c912c9bd161e85cda4ff828991abc40be8bb94d8e30af8295ab2ef363794`，相同 |
| Shoubing Java | `8ec4256cbf8b575795f915323f3b4ead3d18e09d1bcdfb68dcf6e9cccc548236`，相同 | `b00ca1502cb165eb98cbe3aa881cb31ace69e9d1d9d428121795efe6faef7170`，相同 |
| Jianshen Web | `641be3710acf69e8aaee8c2c585724bd3dc9b0e0628f787dfededd86c33801db`，相同 | `df8772b6c262ad6375fe554da940aaa2a05c84773673d309e39cf7987599c0ba`，相同 |
| Shoubing Web | `31cec0034b736cd23636c14d3c3e90bcea262c55b1148c44dd10e565218ef92e`，相同 | `8d90b0232918eb479b6107f53012a489eac4ec87142a3fa3af05a67371f9b6fd`，相同 |

Jianshen Java 前值来自 2026-10-26 保留的本地 FULL Manifest；Shoubing Java 前值由本次 HEAD 在独立目录重新构建。两个前端前值由 HEAD 权限声明进行离线扫描，后值由当前构建输出。两个 Java 的新制品分别通过 `permission-producer` 最终 JAR 核验，两个前端最终制品通过 SDK `ci.mjs --phase validate`。这些结果不证明生产部署、资格或 READY。

Jianshen Web 当前输入 pin 指向的本地历史后端 Manifest digest 为 `1a916a4231bd811e28f097c6a6383f1ce9d720328c6ca50fbbc4c8f198a7dff0`。它是本地试点固定输入，并非对当前线上激活版本的声明。正式 CI 必须取得并审核其不可变来源、固定 SDK commit 与目标配置；当前锁仍是 `LOCAL_UNCOMMITTED`，不能在线注册或激活。

Jianshen Web 的 npm lock 已更新为本次本地打包的 Shared SDK 完整性摘要；隔离消费者中已用该 tarball 安装并验证，用户原工作区的 node_modules 没有被替换。其他机器需要先按现有 SDK 流程准备匹配 tarball 并安装；此本地产物没有发布到 npm。若目标 registry 已存在同版本制品，不能覆盖其不可变内容，应按发布流程选择新版本并重新锁定。

## 请求路径与性能证据边界

| 场景 | 可从源码确认 | SQL/远程次数、P95/P99 |
| --- | --- | --- |
| 普通 USER 查询 | Bearer 加载与受保护方法入口各有快照加载点；实现可能是本地 Runtime，也可能是远端 | 未采集，不能从调用点推断实际次数 |
| USER 列表 | 字段读取主要使用已绑定快照；不可变 FIELD 索引现在按 DTO 类型复用 | 未采集 |
| 敏感字段 | 保留明文/脱敏/省略和逐字段策略判断；现有 EMAIL 测试是夹具，不是生产流量 | 未采集 |
| 写入 | 每次字段绑定最多执行一次 DTO 元数据内省；输入 checkpoint 和写 fence 未移除 | 未采集 |
| SERVICE 字段 | 仍按现有边界访问权威 Runtime；没有声称网络调用已减少 | 未采集 |

Runtime 的数据范围权限成员查找由线性列表查找改为集合查找；未改变 SQL、账号有效性读取或授权版本读取。Shoubing 新增 `oauth.audit.delivery.duration` 计时器，测量严格远端 handoff 至回执验证结束的耗时，成功与失败均计时；它不能单独说明数据库提交耗时，也尚无实时 P95/P99 数据。

后续由操作者在**已有且获准的隔离环境**采集前后版本：使用同一租户、角色、数据量、实例数及并发，分别采集 GET `/api/tianquan-jianshen/v1/iam/roles` 的分页列表、GET/PUT `/api/v1/roles/{roleId}/permissions` 及一条实际敏感字段路径。写入使用可恢复的隔离数据。按 trace 统计各服务身份权威读取、Runtime 调用、SQL 次数和耗时，分开计审计提交/投递/回执与鉴权总 P95/P99；实际敏感字段路径和 SQL/trace 采集能力需先确认，不能把测试夹具当生产测量。采样结果、数据规模、失败率、冷/热状态和版本一并保存。

## 发布与拒绝诊断

- SDK 离线发布计划的两成员 fixture 覆盖“前端候选 + 后端复用”和“后端候选 + 前端复用”：每次选择 2 个 producer，其中 1 个选择旧版本。还覆盖资格过期、缺失引用、无变更和服务端 Diff 报告授权扩大。此为离线测试，**不是实际部署或流量切换**。
- 计划支持使用经授权提供的角色有效权限集合对 API/页面和字段表达式做前后对比；结果明确不包含 OAuth Scope、数据范围、当前角色事实或字段 inputBinding，不是最终授权结论。
- API USER 拒绝新增稳定内部原因、decisionId、traceId 和可用版本/制品信息；外部错误状态与原因合同保持原样，响应附不透明决策编号。现有 HTTP 客户端/页面可展示合法编号；IdP 和 RBAC Runtime 出站请求传播现有 W3C trace。日志不会记录 Token、字段值或完整角色权限。
- 已补充本机 Jianshen USER API 的 decisionId 历史诊断与角色直接授予来源，范围和证据见下文；跨服务及所有拒绝类型的完整持久化证据仍未完成。不可把当前版本反推为历史判定。

## 离线验证

- Jianshen Java：隔离 Maven 仓库、Java 25、`-Ppermission-producer` 的 63 项定向测试通过，包含 API scope、FIELD、快照、fence、Diff、制品绑定、激活和 trace 构造；最终 JAR 及 FULL Manifest 校验通过。
- Shoubing Java：相同隔离方式的 35 项定向测试通过，包含 IdP 状态读取、审计回执/计时、trace 传播、保留、设备相关的现有 producer 覆盖和 MVC 入口；最终 JAR 及 FULL Manifest 校验通过。HEAD 基线制品单独构建时有意跳过测试，仅用于摘要比较。
- SDK：完整 `npm test` 中 React SDK 37 项、Shared SDK 80 项和权限 Node 工具 151 项通过。首次未设置本地工具锁直接运行返回 ENOENT；按现有文档设置 `PAC_TOOLCHAIN_LOCK` 后通过。
- Jianshen Web：在隔离消费者中安装本次 SDK 实际 tarball 后，82 项前端测试通过；最终字段声明调整后另跑 13 项针对性测试与构建通过。Shoubing Web 原有全部 65 项测试及构建通过。
- 两个前端 Python CI 边界测试各 11 项通过，包含固定 commit、重复 JSON 键、脏 SDK checkout 拒绝及现有资格/凭据边界；四份修改后的 CI YAML 通过语法解析。没有运行远端 CI。
- Jianshen Web typecheck、lint、浏览器包静态检查、Manifest/构建证据一致性检查通过；两前端的本地制品证据通过 SDK 验证。未进行浏览器测试。

## 留待后续

1. 采集真实每请求身份/RBAC/SQL、审计耗时和 P95/P99；按结果决定是否进一步优化 SQL。不得因本次纯计算优化声称远程调用已经下降。
2. SERVICE 逐字段权威复验与 USER 输入/方法边界的重复读取仍保留；只有证明撤权时点及版本检查等价后才可合并。
3. 扩展其他服务、逐对象数据范围和身份入口的 decisionId 诊断并设计受权持久汇聚；本机 USER API、字段写入、范围策略及制品绑定记录不能代表所有拒绝。
4. 历史快照、OAuth 操作回执、审计和 Outbox 的增长、归档与告警阈值需真实数据及保留责任；过期死信目前保守保留并告警，不应视作归档完成。
5. 使用真实固定 SDK commit、Manifest、受信 CI/部署资格和目标数据执行两个实际发布场景。当前离线计划没有自动读取真实环境，也未证明流量切换。

## 后续实施：本机 USER API 的 decisionId 诊断

### 实际变化与边界

此前响应只有不透明编号，管理员主要靠 trace / 各服务日志查找。现在，当 Jianshen 本机的 USER API 在已经获得有效授权快照后，因 scope、权限表达式或主体类型被拒绝，严格 IdP 拒绝审计确认成功后，进程内事件会向现有租户审计表追加一条 `AUTHORIZATION_DENIED_DIAGNOSTIC`。审计页在“决策编号”填入响应 `X-Permission-Decision-Id`，确认时间范围后查询并打开详情：可以看到 reasonCode、资源 Key、规则、缺少的 scope、相关权限和角色直接授予来源、快照时间、授权/目录版本、producer 与摘要。审计入口和 `afterSnapshot` 沿用 `system:audit:read`、服务端当前租户和读取审计。事件只携带被检查的权限与角色事实，不携带 Token、完整权限集合或业务字段值。

角色授权表会原位更新。补充来源时按 scope → 租户策略版本 → 用户版本顺序尝试取得 `NOWAIT` 共享锁，检查目录版本，在原快照时间匹配有效直接授予；锁冲突、版本已改变、证据不完整或查询失败时，显示 `*_VERSION_CHANGED`、`INCOMPLETE` 或 `UNAVAILABLE`，不推断为历史来源。已有事务结束后才调度这项辅助记录，并以独立事务写审计。辅助写入失败只记安全日志，不替代或改变原 IdP 严格回执、API 拒绝或写入 fence；进程事件在成功落库前不是持久消息，进程崩溃或数据库故障可导致记录缺失。

此段描述上一轮范围；下一节已补充本机字段写入、范围策略和制品绑定的部分路径。它仍**不是所有拒绝的通用查询**：IdP / 网关提前拒绝、远端 Runtime 提前拒绝、逐对象数据范围、其他资源服务产生的事件，以及过去没有落库的决策，都可能没有记录。同一请求可能产生多条记录。拒绝的常规外部响应仍只暴露编号及原错误，完整事实只经过已有审计授权提供。管理员可能还需要按 trace 到对应服务查日志。

本改动只在上述拒绝路径新增来源核对和审计追加；正常放行路径不增加这部分 SQL。按源码计，来源可执行最多 5 次原生查询（scope、策略、用户、目录和有效角色授予）及 1 次审计追加；没有已授予的关联权限或版本不一致时更少。这是静态调用上界，不是实际每请求 SQL 计数，也不含原有 IdP 严格回执、ORM 或事务开销。真实 SQL、锁等待、拒绝请求额外耗时、P95/P99 和审计数据增长均为 **NOT_RUN**，需要在获准隔离环境测量后决定索引和保留策略。

### 本轮离线验证

- 工作区离线 Maven 定向回归：Starter 19 项、Admin 23 项通过，覆盖 scope / permission、字段边界、当前快照、角色授予、事务完成后记录、权限声明和租户过滤。另单独执行最新诊断及现有 `AuditRedactionIT`，9 项通过（其中诊断测试与前一批有重叠）；查询边界采用 mock/反射，不能证明真实 PostgreSQL 和 HTTP 隔离。
- 隔离源码副本、隔离 Maven 仓库运行 `-Ppermission-producer ... clean verify`，诊断、脱敏及 producer 覆盖 11 项通过，最终 JAR 与 Manifest 验证通过。Jianshen Java 策略 digest 仍为 `0d59473bfc82df31968e9b94992d25111f551f8a4d60c2ccbf75dd52aa827cf4`，元数据 digest 仍为 `43e0c912c9bd161e85cda4ff828991abc40be8bb94d8e30af8295ab2ef363794`；完整 Manifest 与制品摘要随构建变化，仍须按原流程验证和显式激活。
- 隔离前端消费者执行 24 个测试文件、84 项测试通过；新增页面场景 3 项通过，覆盖编号过滤、来源不可核实及旧记录展示。typecheck、lint 和 Vite 构建通过；Web 策略 digest 仍为 `641be3710acf69e8aaee8c2c585724bd3dc9b0e0628f787dfededd86c33801db`，元数据 digest 仍为 `df8772b6c262ad6375fe554da940aaa2a05c84773673d309e39cf7987599c0ba`。UI 测试使用 jsdom，无浏览器或实际服务。

### 留待真实环境单独验收

1. 使用具备审计读取权限的测试管理员和无此权限的用户，在隔离租户分别触发缺 scope / 缺 permission；确认响应编号、原拒绝结果、严格 IdP 审计回执、记录详情和跨租户/无权限读取拒绝。
2. 在记录时并发改变授权版本、角色授予及目录激活，验证锁、回滚后独立写入和不可核实状态；模拟来源读取/写入失败与进程退出，验证不会改变原拒绝及不会误报持久化成功。
3. 对照实际执行计划和数据量统计审计表查询与上述补充 SQL 的次数、耗时和锁等待，采集拒绝及正常请求 P95/P99；评估增长与现有归档保留约束。以上均未运行，不得将离线测试结果写成真实环境通过。
4. 如果页面跨源访问网关，核对网关允许浏览器读取 `X-Permission-Decision-Id` 响应头；同源代理、跨源配置和实际浏览器显示均未验证。

## 后续实施：字段、数据范围与本机制品绑定

- **字段写入**：在 Manifest 已声明的 USER FIELD 写入失败处，记录字段 Key、写入规则、权限/scope 及输入绑定是否可写；原来的字段拒绝和严格回执保持不变，不记录提交值。绑定器捕获未知字段或别名冲突时，在可验证当前 API 的前提下只记录 API 和输入绑定阶段，不保存用户提供的字段名称或值；解析器在绑定器之前抛出的错误仍可能没有记录。读取时的明文、脱敏或省略仍是投影结果，不伪装为请求拒绝。
- **数据范围**：默认 `AuthorizationService` 将它实际使用的快照与 `decideDataScope` 结果一起交给已有严格审计装饰器；仅当该策略返回 DENY、审计交接确认成功、当前身份和可信 API/快照仍可匹配时补充诊断。记录权限、范围类型和目录/策略版本；在授权版本仍一致时还查询匹配的数据规则 ID、角色、类型及引用数量，不保存组织、用户或业务对象列表。页面明确标明这是范围策略的中间判定，并非逐对象最终检查；即使 HTTP 之后成功，编号也可能对应这一中间结果。自定义决策器、未启用审计装饰器、缺少可信请求边界或交接未确认时不保证生成记录，原决定、严格回执和写入 fence 不变。
- **制品绑定**：已取得可信快照时，比较执行侧 Manifest / policy / artifact 与 Runtime 选定绑定；在本机 Runtime 生成快照前发现绑定失败时，仅传递内部的 scope、激活版本、配置/激活摘要和失败检查，确认原 USER 身份及原严格审计后生成编号。前置失败没有用户授权快照，账号版本显示不可用，主体只记录 SHA-256 摘要，也不查询角色来源。远端服务的 Runtime 拒绝和身份验证失败不在本轮覆盖范围。

诊断复用原审计页面、租户权限、事件和事务策略，不修改既有 Flyway 文件，也不信任外部请求头选择权限、作用域或版本；未改变注册、激活、撤权和制品资格要求。辅助记录仍是尽力而为，进程退出或落库失败可能缺失。字段拒绝可能触发最多 5 次来源查询及审计追加；数据范围策略还可能多一次数据规则查询；前置绑定失败不查询角色来源。以上是源码分析，实际 SQL 次数和延迟仍为 NOT_RUN。

### 本轮离线回归

- Java 定向回归：首批 Starter 49 项和 Admin 32 项通过，随后字段、范围及绑定定向 42 项通过（与首批重叠）；写入 fence、Runtime 证明、字段读写和失败关闭另有 Starter 14 项及 Admin 11 项通过。数据规则来源、版本变化及 Runtime 失配到过滤器编号的模拟测试中，Admin 17 项通过；新增范围诊断写入失败回归后，范围诊断 5 项通过。这些测试使用 mock 和 Spring 测试对象，不是实际数据库或 HTTP 端到端验收。
- 隔离源码和 Maven 仓库的 `-Ppermission-producer ... clean verify` 中 Starter 22 项及 Admin 19 项通过，最终 JAR 与 FULL Manifest 校验通过；策略 digest 仍为 `0d59473bfc82df31968e9b94992d25111f551f8a4d60c2ccbf75dd52aa827cf4`，元数据 digest 仍为 `43e0c912c9bd161e85cda4ff828991abc40be8bb94d8e30af8295ab2ef363794`。制品及完整 Manifest 摘要变化，不能据此跳过原资格和显式激活。
- 隔离前端消费者 24 个测试文件、87 项通过；后续增加输入绑定展示后又单独运行审计页 7 项通过。覆盖字段、范围中间判定和制品差异展示；typecheck、lint、Vite 构建和浏览器包静态检查通过。Web 策略和元数据 digest 仍为 `641be3710acf69e8aaee8c2c585724bd3dc9b0e0628f787dfededd86c33801db` / `df8772b6c262ad6375fe554da940aaa2a05c84773673d309e39cf7987599c0ba`；测试使用 jsdom，未启动浏览器。

### 留待真实环境单独验收

在获准隔离环境验证字段绑定与序列化、默认范围服务的中间判定与逐对象边界、本地 Runtime 快照前绑定拒绝、权限撤销和旧实例排空；核对审计记录与严格回执、跨租户及无审计权限拒绝、并发更新和故障恢复。采集 SQL/远程调用、额外审计数据、P95/P99 并验证跨源暴露响应头。以上均未运行，也未启动服务或浏览器。

## 本地分步提交

本次提交仅创建本地 Git 提交，未推送、发布、注册或激活。各仓库以实施开始时的 HEAD 为基础，按下列逻辑任务提交：

| 仓库 | 提交（由旧到新） | 说明 |
| --- | --- | --- |
| web-sdk | `0b8e254`, `46814ce` | 决策编号 SDK；Manifest 引用、发布计划和共享 CI 工具 |
| tianquan-shoubing-service | `18e2908`, `40958c6`, `efb9fa8`, `34f552a` | 死信保留、审计耗时、链路传播、本地工具锁 |
| tianquan-jianshen-service | `b38b59c`, `f57bbe2`, `837849e`, `ebd0bde` | 权限声明、链路传播、拒绝诊断、本地工具锁 |
| tianquan-shoubing-web | `9fb8f6f` | 共用 CI 适配器 |
| tianquan-jianshen-web | `9d44559`, `16dcaa9`, `41a5afa` | 管理页诊断、后端 Manifest 引用、共用 CI 适配器 |

工具锁仍为 `LOCAL_UNCOMMITTED`，禁止在线注册和激活。2026-10-27 本地检查 npm 公共 registry 对 `@stellar-enclosure/stellar-enclosure-web-shared@0.0.1` 返回 404；前端锁文件中的完整性值对应本地验证的 tarball，不代表该制品已发布或能从锁文件 URL 获取。需按照既有发布流程提供匹配制品、受信 SDK 固定提交及后端 Manifest 后，才能进行干净环境 CI 与部署验收。

SDK 提交后，使用本地准备的合同及 `LOCAL_UNCOMMITTED` 锁再次运行完整 `npm test`：React SDK 37 项、Shared SDK 80 项及权限工具 151 项通过；未启动服务或浏览器。
