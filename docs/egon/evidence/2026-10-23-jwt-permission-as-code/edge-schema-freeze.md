> S01 design review snapshot. Original DRAFT/pre-creation statements below are historical; current migration hashes and execution status are in execution-status.json. This is not executed PostgreSQL validation. Final migrations are immutable.

# EDGE S01 数据库结构草案（等待冻结）

- Owner：`yuheng-service/stellar-enclosure-yuheng-edge-gateway`。
- 本文件和相邻 `edge-schema.sql` 仅为临时草案；未创建最终迁移、未执行 SQL。
- 最终文件目标：`src/main/resources/db/migration/V1__edge_oauth_state.sql`。
- 现状：EDGE 模块无已有 SQL/Flyway owner；Yuheng admin 的 V1–V13 等历史文件全部保持原样。
- 使用独立 EDGE PostgreSQL database/最小权限 DataSource；Flyway history 使用独立名字 `flyway_edge_oauth_history`。运行角色只访问四张 EDGE 表，不写 IdP 表。
- 实现沿用现有 JDBC/Flyway 能力，不加 R2DBC。整个同步事务在独立有界调度器内执行。

## 1. 不变量与边界

四张表只有一次性 OAuth 请求、刷新协调事实、撤销交付意图与回执。没有可恢复 SecurityContext/Principal/OAuth2AuthorizedClient 的 JSON/二进制序列化列；没有 Access/ID Token 存储、没有返回最新 Refresh 的接口、没有浏览器 opaque ID 查长期身份仓库。

浏览器身份来自逐次验证的 JWT。数据库负向关闭记录只能拒绝请求，不能凭它创建身份。刷新上下文允许采用专用的“签名/typ/iss/aud/client 等均验证，仅为 refresh/CSRF 放宽 Access exp”的分支；仍要校验授权绝对期、数据库状态及原 Refresh 摘要，不得用于 API 认证。

`target_digest` 是对版本化、长度前缀编码的 `(appAlias, registrationId, canonical issuer, tenantId, clientId, resource)` 求 SHA-256。它只缩短复合索引，并非外部授权凭据；写入/读取都独立比较冻结的完整目标字段。URL/回调/returnPath 在业务边界进行严格规范化、固定注册匹配和路径安全校验，SQL 的 https/非空检查不替代这些校验。

`request_digest` 绑定操作用途、operationId、targetDigest、已验证身份/族/代际、浏览器绑定摘要及原凭据摘要。外部 operationId 必须 UUID、不可跨身份/Client/Resource/浏览器复用；状态查询也重新验证上下文，不按裸 operationId 读取。

所有时间使用 UTC `TIMESTAMPTZ`。时钟由同一个数据库事务观察值/受控 Clock 提供；租约、期限、epoch、摘要、目标和创建时间不允许通过普通更新滑动延长。每次变更用 `version + expected state + owner` CAS，冲突即拒绝。

## 2. 表与唯一性

| 表 | 权威事实 | 唯一性/检索 |
| --- | --- | --- |
| `edge_oauth_transaction` | 一次性 authorize/callback 事务 | UUID PK；target+state 摘要唯一；exchangeAttempt 唯一；pending到期/交换租约/保留期索引 |
| `edge_oauth_refresh_operation` | 单代际最多一次向 IdP 发请求及终态 | UUID operation PK；target+Refresh摘要唯一；已知授权族+代际额外唯一；租约和关闭查询索引 |
| `edge_oauth_revocation_intent` | 恢复/退出/切换/重放的持久撤销意图 | intent PK；target+idempotency摘要唯一；每refresh operation最多一个预置恢复意图；due/lease/negative deny索引 |
| `edge_oauth_revocation_receipt` | 标准revoke响应已收到且本地确认提交 | receipt PK；intent唯一；FK禁止不经回执处理删除意图 |

本地 FK 只连接 EDGE 表。授权族/认证jti 是 IdP事实引用，不建立跨数据库 FK。正常Refresh操作必须从已验证USER证明取得授权族/认证jti/代际/绝对期，操作表这些列必填；只有恢复撤销意图在尚未得到完整Token响应时允许族引用为空，撤销必须使用原Refresh与标准revoke，不能以局部JTI撤销伪装成关族。

## 3. 一次性 OAuth 事务

字段完整保存冻结的 app/registration/issuer/tenant/client/resource、精确 redirectUri、受控 returnPath、requestedScopes、state摘要、nonce摘要、浏览器绑定摘要与 S256 challenge。

PKCE verifier 与原始 OIDC nonce 使用分别区分 purpose 的 AES-256-GCM envelope 加密；同一 encryptionKeyId/version，随机nonce在密文envelope内；AAD绑定schema version、表类型、transactionId和targetDigest。保留原nonce加密值是为了可接原生OAuth/OIDC请求恢复/nonce验证，不保存任意授权请求序列化对象。

状态：`PENDING → EXCHANGING → SUCCEEDED | FAILED | CLOSED`；`PENDING → EXPIRED/FAILED/CLOSED`。

回调先验证state/浏览器绑定/目标/时效；同一数据库事务锁定PENDING行，解密出请求期verifier/nonce、写code摘要和一次exchange attempt、设置租约、清空DB密文字段，提交后才调用token端点。只有当前请求在内存中持有本次交换秘密，其他实例不得重发；节点死亡/网络结果未知转CLOSED要求重新授权。授权码从不明文入库。

若交换响应已到达而后续验证/落Cookie准备失败且有Refresh，创建CODE_RECOVERY意图撤销；若IdP响应完全未知且未得到Refresh，不能伪造关族证明，关闭客户端事务并要求重认证。IdP的Code一次性约束阻止重放；无凭据返回浏览器。

默认交互5分钟；交换deadline不超过事务expire。终态保留无秘密的摘要/目标/错误码，密文在离开PENDING时即清空。failureCode仅允许预定义码，不保存HTTP正文/异常堆栈/密码/nonce/Token。

## 4. 刷新 claim 与未知结果

正常 JWT 新合同（IdP owner已告知root确认）：`authorization_id`为既有十进制字符串；`authn_jti`为认证JWT jti；`refresh_generation`为非负十进制字符串；`authorization_expires_at`和`authn_expires_at`为NumericDate秒。EDGE以签名后的Access claims为权威，不能把浏览器JSON输入当事实。

AUTH-07的专用请求包含purpose=REFRESH_CONTEXT、accessToken、expectedResource、expectedClientId、refreshTokenDigest、browserBindingDigest。IdP验证签名/目的/登记/族/代际/安全状态与原Refresh摘要，只为该目的放宽Access exp；响应只包含eligible、关联事实、版本与reasonCode，无凭据。tenant来自可信issuer/服务身份，不接自报subject/roles。只有eligible=true且完整事实与签名JWT/固定目标一致时才能创建refresh operation。

浏览器绑定合同：EDGE创建随机HttpOnly绑定Cookie，authorize携带`browser_binding=sha256(cookie)`；只有登记browserBound=true的EDGE client要求此扩展。IdP将其冻结到family.client_browser_binding_digest；callback EDGE核对自身SQL事务及Cookie；REFRESH_CONTEXT核对同一个摘要。IdP自己的登录Cookie绑定不与EDGE混用。该绑定Cookie不能用于查询长期身份，API请求仍凭JWT。

1. 严格验证签名、typ、固定issuer/client/resource、族绝对期、浏览器绑定与CSRF；SHA-256原Refresh，不记录原值。先查已绑定operation/凭据摘要：同operationId+相同requestDigest只返回状态，确有IN_PROGRESS则竞争冲突，完成后的异操作旧代际进入拒绝/单向关族。不得先要求currentGeneration的REFRESH_CONTEXT而使已消费旧RT的状态查询/重放处置永远被遮住；这条专用旧证明路径只可查绑定状态或单向关闭，不能创建身份/新凭据。
2. 只有无既存operation、将首次dispatch的新请求才要求IdP REFRESH_CONTEXT返回currentGeneration eligible=true，并重新核对完整绑定。随后同库原子创建IN_PROGRESS操作和ARMED撤销意图。ARMED只有原Refresh短期密文，绝无Access/新Refresh。
3. CAS将`upstream_attempts=0`变1并写upstreamStartedAt，提交后才发送一次token请求。无论换节点/网络重试都不能把同一操作的attempt归零或复用旧Refresh。
4. 只有leaseOwner、version、deadline均匹配且族未被关闭，才可同库SUCCEEDED+DISARMED预置意图并清空密文。然后本请求设置新Cookie；数据库不保存新Token，重查只返回状态/期限。
5. 竞争请求若现有操作仍IN_PROGRESS返回冲突；同operationId+相同requestDigest的重复只查状态；异operationId复用已消费代际按重放关闭并建立持久撤销意图。
6. 未知、超时、lease到期或进程死亡恢复：同库操作CLOSED（可先记录UNKNOWN再立即关闭）+ARMED转PENDING；当前及后续请求拒绝，后台继续标准revoke交付。FAILED指已收到确定拒绝；若无法证明原族关闭，同样持久化撤销意图，不开放重试旧代际。

operation字段仅有上下文、摘要、代际、owner/lease、次数上限1、成功期限与终态；不得保存response body、新Access/Refresh、Cookie串。授权族绝对期固定，refresh operation不滑动延长它。

## 5. 撤销意图、交付与负向关闭

明确与root/IdP owner已协同的依赖：标准 `/oauth2/revoke` 必须能用**已消费Refresh的摘要定位原族并关闭族**；仍严格绑定认证Client和issuer，不放宽Token兑换，保留历史摘要至少到族绝对到期+安全窗。RFC7009的HTTP200不泄露token是否存在。EDGE不新增通用family撤销端点。

状态：

- REFRESH_RECOVERY：`ARMED → DISARMED`（成功清密文）或`ARMED → PENDING`（未知/关闭）；ARMED不可被worker执行。
- LOGOUT/ACCOUNT_SWITCH/REPLAY/CODE_RECOVERY：创建即PENDING。
- `PENDING → IN_PROGRESS → SUCCEEDED`；可恢复失败释放owner后回PENDING；lease过期可重claim，因为revoke本身幂等。
- 认证配置永久错误、密钥不可用、达到固定dispatchDeadline等进入DEAD_LETTER并清密文，记录已拒绝但未证实远端撤销；不能把DEAD_LETTER当CONFIRMED。

撤销密文仅允许在专用worker读取后提交原注册client的标准revoke；AAD绑定intentId/targetDigest/tokenDigest，不能用于Token Endpoint或返回给浏览器。密文在SUCCEEDED、DISARMED、DEAD_LETTER立即删除。正常到期前持续有界重试；超期保留没有可用凭据的拒绝事实与诊断。

expirySource明确区分VERIFIED_CREDENTIAL和CONFIGURED_UPPER_BOUND。前者必须有签名可信的authorizationExpiresAt；后者用于CODE_RECOVERY等没有可信Access响应的场景，该列必须NULL，按服务端为该登记Client冻结的最大族寿命上界，加最大Access寿命/clock skew计算不可滑动的dispatchDeadline/denyUntil。推算上界不能作为真实JWT绝对期返回，也不能因为未知期而忽略撤销或永久保留可解密凭据。每个EDGE登记必须配置与IdP一致的族寿命上限，缺失上限不开放登录。

同库成功处理事务必须同时：验证匹配intent/target/requestDigest/tokenDigest、记录receipt、更新SUCCEEDED+confirmedAt+HTTP200、清密文。HTTP已200但本地提交失败可重新revoke；不得先标成功再补receipt。SQL FK/唯一限制加事务内核对阻止一个回执确认另一目标。

PENDING/IN_PROGRESS/SUCCEEDED/DEAD_LETTER在denyUntil前均是负向关闭事实，ARMED/DISARMED不阻止正常使用。查询按完整已验证上下文+族，必要时关联authn_jti；只拒绝对应应用族，不能因为普通app logout有authn_jti就撤销同认证下其他app。ACCOUNT_SWITCH/SSO全范围关闭由IdP明确的认证上下文撤销事实负责，不能由局部表擅自扩大范围。

logout与refresh claim/完成都取得基于已验证issuer+authn_jti、targetDigest+authorizationId的数据库事务级advisory lock（固定先认证上下文、再授权族顺序），再锁定操作/意图行并复验。此锁用PostgreSQL内建pg_advisory_xact_lock，不加扩展或进程锁；确定性hash碰撞最多增加串行，不产生放行。采用事务锁是为了覆盖“尚无某代际行”的插入竞态，不能只锁已存在操作行。持久关闭优先，迟到成功不发新Cookie；已经发出的迟到Cookie也因本地负向关闭和IdP关族而拒绝。多资源账号切换必须先完成旧认证上下文关闭；数据库不可用时不发新凭据、不代理受保护请求。

## 6. 保留与清理

- 交互秘密：离开PENDING即清；PENDING到期worker也清。无延长原expiresAt。
- ARMED恢复密文：不超过该刷新deadline；故障转PENDING。PENDING密文不超过固定dispatchDeadline，默认不晚于原授权绝对期+最大Access寿命/时钟安全窗。
- 操作/拒绝事实：至少保存到授权绝对期+最大Access寿命+允许clock skew，使清理不复活可用旧凭据；之后另保留默认7天无秘密诊断窗。
- 回执：默认保留30天，可按部署审计策略配置，必须不短于关联负向事实需要的窗口。
- 每条记录创建时冻结retainUntil/denyUntil，清理只删除已终态且超过安全保留的记录；先回执、再意图、再关联操作/事务，ON DELETE RESTRICT防止误级联。
- 清理采用有界批次、数据库行claim/CAS；不是服务启动时执行清库，也不删除既有用户本地文件。

## 7. 实施/验证冻结清单

冻结前必须确认：四表/索引和全部后续S08字段；已协同JWT/REFRESH_CONTEXT/browser_binding字段；revoke已消费Refresh行为；密钥环/轮换策略；调度/timeout/retention界限；独立database/Flyway history。

S07测试：SQL结构与无token-vault负向检查；AES-GCM篡改/purpose/target/keyId错配；真实PostgreSQL双连接claim/事务回滚/receipt原子性；JDBC有界调度器验证；readiness数据库故障拒绝。S08补真实Reactive FilterChain、Cookie/audience/CSRF与Refresh/Logout竞态。

本草案只完成源码与结构检查；没有连接数据库、迁移、运行服务、容器或浏览器。JDK25由root统一定位/准备，此处不下载或改全局JAVA_HOME。
