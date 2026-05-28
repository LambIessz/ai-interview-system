"""
题库初始化脚本 - 预置面试题并向量化存储
运行方式: python scripts/init_question_bank.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import settings
from app.models.question_bank import QuestionBank, HAS_PGVECTOR
from app.services.common.embedding import get_embedding

PRESET_QUESTIONS = [
    # === Python 基础 ===
    {
        "question_text": "请解释 Python 中深拷贝和浅拷贝的区别，以及分别在什么场景下使用。",
        "category": "Python",
        "difficulty": "medium",
        "reference_answer": "浅拷贝只复制对象本身，不复制嵌套对象，使用 copy.copy() 实现；深拷贝递归复制整个对象树，使用 copy.deepcopy() 实现。浅拷贝适用于简单对象的独立副本创建，深拷贝适用于需要完全独立的嵌套结构副本的场景。要注意循环引用可能导致深拷贝出错。",
        "key_points": ["能区分浅拷贝和深拷贝的概念", "知道对应的实现方法", "了解使用场景和注意事项"]
    },
    {
        "question_text": "什么是 Python 的 GIL（全局解释器锁）？它对多线程编程有什么影响？",
        "category": "Python",
        "difficulty": "medium",
        "reference_answer": "GIL 是 CPython 解释器中的一个互斥锁，保证同一时刻只有一个线程执行 Python 字节码。这导致 CPU 密集型任务多线程无法利用多核优势，但 I/O 密集型任务因为线程在等待 I/O 时会释放 GIL，仍能获得性能提升。替代方案包括多进程（multiprocessing）和使用 C 扩展来释放 GIL。",
        "key_points": ["能解释 GIL 的概念和存在原因", "理解对多线程的影响", "知道应对方案（多进程/C扩展）"]
    },
    {
        "question_text": "请解释 Python 中生成器的工作原理，以及使用 yield 关键字的优势。",
        "category": "Python",
        "difficulty": "easy",
        "reference_answer": "生成器是一种特殊的迭代器，通过 yield 关键字在函数中逐个产出值而非一次性返回全部。每次调用 yield 时，函数状态被保存，下次迭代从上次暂停处继续。优势包括：惰性求值节省内存、无需预先计算所有值、可以表示无限序列、代码更简洁易读。",
        "key_points": ["能解释生成器的概念", "理解 yield 的工作原理", "知道惰性求值的优势"]
    },
    {
        "question_text": "请解释 Python 装饰器的原理，并写一个简单的日志装饰器示例。",
        "category": "Python",
        "difficulty": "medium",
        "reference_answer": "装饰器本质上是一个接受函数作为参数并返回新函数的高阶函数。它使用 @语法糖在定义时包装目标函数，常用于日志记录、权限校验、缓存等横切关注点。原理是利用闭包特性，在 wrapper 中执行额外逻辑后调用原函数。functools.wraps 用于保留原函数的元信息。",
        "key_points": ["理解装饰器是高阶函数", "能写出基本装饰器", "了解 functools.wraps 的作用", "知道常见应用场景"]
    },
    {
        "question_text": "Python 中 is 和 == 有什么区别？分别在什么时候使用？",
        "category": "Python",
        "difficulty": "easy",
        "reference_answer": "is 比较两个对象的身份（内存地址），== 比较两个对象的值（通过 __eq__ 方法）。is 通常用于与 None、True、False 等单例比较；== 用于值比较。注意小整数和短字符串的 intern 机制可能导致 is 和 == 意外返回相同结果。",
        "key_points": ["能区分身份比较和值比较", "知道 is 用于 None 判断", "了解 intern 机制"]
    },
    # === 数据库 ===
    {
        "question_text": "请解释数据库索引的工作原理，以及 B+ 树索引的优势。",
        "category": "数据库",
        "difficulty": "medium",
        "reference_answer": "索引是一种数据结构，用于加速数据库表的数据检索。B+ 树索引是最常用的索引结构，所有数据存储于叶子节点，叶子节点之间通过指针相连形成有序链表。优势包括：查询效率稳定 O(log n)、支持范围查询、叶子节点链接使范围扫描高效、树高度低减少磁盘 I/O。",
        "key_points": ["能解释索引的基本概念", "理解B+树的结构特点", "知道索引的优缺点"]
    },
    {
        "question_text": "什么是数据库事务的 ACID 特性？请分别解释每个特性的含义。",
        "category": "数据库",
        "difficulty": "easy",
        "reference_answer": "ACID 是数据库事务的四个基本特性：原子性（Atomicity）- 事务中的操作要么全部成功要么全部回滚；一致性（Consistency）- 事务执行前后数据库都处于一致状态；隔离性（Isolation）- 并发事务之间互不干扰；持久性（Durability）- 已提交的事务结果永久保存。",
        "key_points": ["能说出 ACID 全称", "分别解释四个特性", "理解数据库如何保证这些特性"]
    },
    {
        "question_text": "请解释 SQL 中 JOIN 的类型（INNER、LEFT、RIGHT、FULL）及其区别。",
        "category": "数据库",
        "difficulty": "easy",
        "reference_answer": "INNER JOIN 返回两表匹配的行；LEFT JOIN 返回左表所有行，右表无匹配则填充 NULL；RIGHT JOIN 返回右表所有行，左表无匹配则填充 NULL；FULL JOIN 返回两表所有行，无匹配部分填充 NULL。LEFT JOIN 最常用，常用于主表关联子表时需要保留主表所有记录的场景。",
        "key_points": ["能区分四种 JOIN", "理解 NULL 填充机制", "知道 LEFT JOIN 的最常用场景"]
    },
    {
        "question_text": "什么是慢查询？如何优化慢查询？",
        "category": "数据库",
        "difficulty": "medium",
        "reference_answer": "慢查询是执行时间超过阈值的 SQL 语句。优化方法：1）使用 EXPLAIN 分析执行计划；2）添加合适的索引；3）避免 SELECT *，只查需要的列；4）优化 WHERE 条件，避免函数运算导致索引失效；5）合理设计表结构，适当反范式化；6）分库分表或读写分离。",
        "key_points": ["能识别慢查询", "知道 EXPLAIN 工具", "掌握常见优化策略", "了解索引失效场景"]
    },
    {
        "question_text": "请解释数据库连接池的作用和工作原理。",
        "category": "数据库",
        "difficulty": "medium",
        "reference_answer": "连接池预先创建并维护一组数据库连接，应用程序需要时从池中获取，用完归还。避免了频繁创建和销毁连接的开销。工作原理：初始化时创建最小连接数，请求时分配空闲连接，连接用完回收，超过最大连接数时等待或报错。需设置合理的池大小（通常为 CPU 核数 * 2 + 磁盘数）。",
        "key_points": ["理解连接池的必要性", "知道池化机制", "了解连接池大小设置原则"]
    },
    # === Redis ===
    {
        "question_text": "Redis 有哪些常见的数据类型？分别适用于什么场景？",
        "category": "Redis",
        "difficulty": "easy",
        "reference_answer": "五种基本类型：String（缓存、计数器）、Hash（存储对象属性）、List（消息队列、时间线）、Set（标签、共同好友）、Sorted Set（排行榜、延迟队列）。还有高级类型：Bitmap（签到统计）、HyperLogLog（UV 统计）、GEO（地理位置）、Stream（消息队列）。",
        "key_points": ["能列举五种基本类型", "各类型有对应场景举例", "了解高级数据类型"]
    },
    {
        "question_text": "什么是缓存穿透、缓存击穿和缓存雪崩？如何应对？",
        "category": "Redis",
        "difficulty": "hard",
        "reference_answer": "缓存穿透：查询不存在的数据，缓存和数据库都没有，请求穿透到数据库。应对：布隆过滤器过滤不存在 key、缓存空值。缓存击穿：热点 key 过期瞬间大量请求打到数据库。应对：互斥锁更新缓存、永不过期。缓存雪崩：大量 key 同时过期或 Redis 宕机。应对：过期时间加随机值、主从 + 哨兵/集群高可用、限流降级。",
        "key_points": ["能区分三种缓存问题", "理解各自的成因", "掌握对应的解决方案"]
    },
    {
        "question_text": "Redis 的持久化方式有哪些？各自优缺点？",
        "category": "Redis",
        "difficulty": "medium",
        "reference_answer": "RDB：定时快照持久化，fork 子进程将内存数据写入磁盘。优点：恢复快、文件紧凑适合备份；缺点：可能丢失最后一次快照后的数据。AOF：记录每次写操作日志。优点：数据安全性高，最多丢失 1 秒数据；缺点：文件较大、恢复慢。实际生产常使用 RDB + AOF 混合持久化。",
        "key_points": ["能区分 RDB 和 AOF", "了解各自的优缺点", "知道混合持久化方案"]
    },
    {
        "question_text": "Redis 的内存淘汰策略有哪些？",
        "category": "Redis",
        "difficulty": "medium",
        "reference_answer": "当内存达到 maxmemory 时的淘汰策略：noeviction（不淘汰，拒绝写入）、allkeys-lru（LRU 淘汰任意 key）、volatile-lru（LRU 淘汰设了过期时间的 key）、allkeys-random（随机淘汰）、volatile-random（随机淘汰有过期时间的）、volatile-ttl（淘汰 TTL 最小的）。LRU 和 LFU 是常用策略，LRU 关注最近使用，LFU 关注使用频率。",
        "key_points": ["能列举主要淘汰策略", "理解 LRU 和 LFU 的区别", "知道 volatile 系列策略"]
    },
    # === 系统设计 ===
    {
        "question_text": "请设计一个短链接系统，考虑高可用和可扩展性。",
        "category": "系统设计",
        "difficulty": "hard",
        "reference_answer": "核心流程：长链接 → 生成唯一短码 → 存储映射关系 → 访问时重定向。关键设计：1）短码生成可用 base62 编码自增 ID 或 MurmurHash；2）存储使用 MySQL + Redis 缓存热点链接；3）高可用通过读写分离、主从复制；4）分布式场景使用雪花算法生成全局唯一 ID；5）用 CDN 加速重定向；6）限流防恶意请求。",
        "key_points": ["理解短链接核心流程", "知道短码生成方案", "考虑缓存和高可用设计", "了解分布式 ID 方案"]
    },
    {
        "question_text": "如何设计一个高并发的秒杀系统？",
        "category": "系统设计",
        "difficulty": "hard",
        "reference_answer": "秒杀系统的核心挑战是瞬时高并发流量。设计要点：1）前端限流：按钮置灰、验证码；2）网关层：令牌桶/漏桶限流；3）Redis 预减库存，Lua 脚本保证原子性；4）消息队列异步下单削峰；5）数据库乐观锁防止超卖；6）多级缓存减少数据库压力；7）服务降级和熔断保护。",
        "key_points": ["理解秒杀的核心挑战", "掌握限流策略", "了解库存扣减原子性方案", "知道异步削峰和缓存策略"]
    },
    {
        "question_text": "请解释 RESTful API 的设计原则。",
        "category": "系统设计",
        "difficulty": "easy",
        "reference_answer": "RESTful API 设计原则：1）资源导向，URL 使用名词复数形式；2）使用 HTTP 方法表达操作（GET/POST/PUT/DELETE）；3）无状态，请求包含所有需要的信息；4）使用 HTTP 状态码表示结果；5）支持过滤、排序、分页；6）版本控制（URL 路径或 Header）；7）HATEOAS 超媒体驱动。",
        "key_points": ["理解资源导向设计", "正确使用 HTTP 方法", "知道状态码的使用", "了解版本控制和分页"]
    },
    {
        "question_text": "常用的微服务间通信方式有哪些？各有什么优劣？",
        "category": "系统设计",
        "difficulty": "medium",
        "reference_answer": "同步通信：REST（简单通用但耦合高）、gRPC（高性能强类型但调试困难）。异步通信：消息队列（解耦削峰但增加复杂度）、事件总线（松耦合但追踪困难）。选择标准：实时性要求高用同步（查询类），对可用性要求高用异步（命令类）。实际中常采用混合模式，写操作异步、读操作同步。",
        "key_points": ["能区分同步和异步通信", "了解 REST 和 gRPC 的区别", "理解消息队列的优劣势", "知道CQRS模式"]
    },
    # === 计算机网络 ===
    {
        "question_text": "请解释 TCP 三次握手和四次挥手的过程。",
        "category": "计算机网络",
        "difficulty": "medium",
        "reference_answer": "三次握手：1）客户端发送 SYN；2）服务端回复 SYN-ACK；3）客户端回复 ACK。防止已失效的连接请求到达服务端造成资源浪费。四次挥手：1）主动关闭方发送 FIN；2）被动方回复 ACK；3）被动方数据发送完毕后发送 FIN；4）主动方回复 ACK 并等待 2MSL。TIME_WAIT 状态确保最后的 ACK 能被收到。",
        "key_points": ["能清晰描述握手和挥手过程", "理解为什么需要三次握手", "知道 TIME_WAIT 的作用", "了解每个状态的转换"]
    },
    {
        "question_text": "HTTP 和 HTTPS 有什么区别？HTTPS 的加密过程是怎样的？",
        "category": "计算机网络",
        "difficulty": "medium",
        "reference_answer": "HTTP 明文传输，HTTPS 通过 SSL/TLS 加密。区别：HTTPS 需要 CA 证书、端口 443 vs 80、加密传输更安全。加密过程：1）客户端发送支持的加密套件；2）服务端返回证书和公钥；3）客户端验证证书，生成对称密钥，用公钥加密发送；4）服务端用私钥解密获取对称密钥；5）后续通信使用对称密钥加密。这是混合加密：非对称加密用于密钥交换，对称加密用于数据传输。",
        "key_points": ["能区分 HTTP 和 HTTPS", "理解混合加密机制", "了解证书的作用", "知道TLS握手流程"]
    },
    {
        "question_text": "什么是跨域请求？常见的跨域解决方案有哪些？",
        "category": "计算机网络",
        "difficulty": "easy",
        "reference_answer": "跨域请求是浏览器同源策略的限制，协议、域名、端口任一不同即为跨域。解决方案：1）CORS（服务端设置 Access-Control-Allow-Origin）；2）JSONP（利用 script 标签无跨域限制，只支持 GET）；3）Nginx 反向代理统一域名；4）WebSocket（不受同源策略限制）；5）postMessage（iframe 通信）。CORS 是最标准和常用的方案。",
        "key_points": ["理解同源策略", "知道 CORS 的标准方案", "了解 JSONP 的局限性", "知道代理方案"]
    },
    # === 操作系统 ===
    {
        "question_text": "进程和线程的区别是什么？",
        "category": "操作系统",
        "difficulty": "easy",
        "reference_answer": "进程是资源分配的基本单位，拥有独立的内存空间；线程是 CPU 调度的基本单位，共享进程的内存空间。区别：进程创建和切换开销大，线程开销小；进程间通信复杂（IPC），线程间通信简单（共享内存）；进程崩溃不影响其他进程，线程崩溃可能导致整个进程崩溃。",
        "key_points": ["能从资源分配角度区分", "了解调度开销差异", "知道通信方式的区别", "理解崩溃的影响范围"]
    },
    {
        "question_text": "什么是死锁？如何避免和解决死锁？",
        "category": "操作系统",
        "difficulty": "medium",
        "reference_answer": "死锁是多个进程/线程互相等待对方释放资源而无法继续执行的状态。四个必要条件：互斥、持有并等待、不可剥夺、循环等待。预防：破坏任一条件（如一次性申请所有资源）；避免：银行家算法动态检测；检测：资源分配图；恢复：强制终止进程或回滚事务。",
        "key_points": ["能定义死锁", "能说出四个必要条件", "了解预防和避免策略"]
    },
    # === Git & DevOps ===
    {
        "question_text": "请解释 Git 中 merge 和 rebase 的区别，分别适用于什么场景？",
        "category": "DevOps",
        "difficulty": "medium",
        "reference_answer": "Merge 创建一个新的合并提交保留分支历史，安全但提交记录复杂；Rebase 将分支提交移到目标分支顶端重写历史，提交记录线性清晰但有风险。场景：公共分支合并用 merge 保留完整历史；个人特性分支合并到主分支前用 rebase 保持历史整洁。关键规则：不要对已推送的分支 rebase。",
        "key_points": ["能区分 merge 和 rebase", "理解历史记录的差异", "知道 rebase 的黄金规则", "了解适用场景"]
    },
    {
        "question_text": "什么是 CI/CD？请描述一个典型的工作流程。",
        "category": "DevOps",
        "difficulty": "easy",
        "reference_answer": "CI（持续集成）指频繁将代码合并到主干并自动构建测试；CD 可指持续交付（自动部署到测试环境）或持续部署（自动部署到生产环境）。典型流程：1）开发 push 代码触发 CI；2）运行 lint、单元测试、构建；3）生成制品推送到镜像仓库；4）自动部署到测试环境运行集成测试；5）审批后自动部署到生产。工具链：GitLab CI/GitHub Actions + Docker + K8s。",
        "key_points": ["理解 CI/CD 的概念", "知道典型工作流程", "了解常见工具链", "区分持续交付和持续部署"]
    },
    {
        "question_text": "Docker 容器和虚拟机的区别是什么？",
        "category": "DevOps",
        "difficulty": "medium",
        "reference_answer": "虚拟机通过 Hypervisor 模拟硬件，每个 VM 有完整 OS，隔离性强但资源占用大、启动慢。容器共享宿主机内核，通过 Namespace 和 Cgroup 实现隔离，轻量级、启动快、资源利用率高。关键区别：容器是进程级别的隔离，VM 是操作系统级别的隔离。容器更适合微服务部署，VM 更适合需要强隔离或不同内核的场景。",
        "key_points": ["理解容器和 VM 的架构差异", "知道各自的优缺点", "了解 Namespace 和 Cgroup", "知道适用场景"]
    },
    # === 数据结构与算法 ===
    {
        "question_text": "请解释哈希表的原理，以及如何处理哈希冲突。",
        "category": "数据结构与算法",
        "difficulty": "medium",
        "reference_answer": "哈希表通过哈希函数将键映射到数组索引，实现 O(1) 平均查找。冲突处理：1）链地址法 - 每个槽位存链表，冲突时追加；2）开放地址法 - 冲突时按探测序列找下一个空位（线性探测/平方探测/双重哈希）。Python 的 dict 使用开放地址法，负载因子超过 2/3 时自动扩容。",
        "key_points": ["理解哈希表的核心原理", "知道至少两种冲突解决方案", "了解负载因子和扩容机制", "了解实际语言的实现"]
    },
    {
        "question_text": "常见排序算法的时间复杂度和空间复杂度是多少？",
        "category": "数据结构与算法",
        "difficulty": "easy",
        "reference_answer": "冒泡/选择/插入排序：O(n²) 时间、O(1) 空间。归并排序：O(n log n) 时间、O(n) 空间。快速排序：平均 O(n log n)/最坏 O(n²) 时间、O(log n) 递归栈空间。堆排序：O(n log n) 时间、O(1) 空间。稳定排序：冒泡、插入、归并；不稳定：选择、快排、堆排序。Python 的 Timsort 是归并+插入的混合排序。",
        "key_points": ["能说出各排序的复杂度", "了解稳定和不稳定的区别", "知道快速排序最坏情况的触发场景", "了解实际语言的排序实现"]
    },
    # === 设计模式 ===
    {
        "question_text": "请解释单例模式和工厂模式，并给出 Python 中的实现示例。",
        "category": "设计模式",
        "difficulty": "medium",
        "reference_answer": "单例模式保证一个类只有一个实例，并提供全局访问点。Python 实现：使用 __new__ 方法或模块级别的全局变量实现。工厂模式定义一个创建对象的接口，让子类决定实例化哪个类。Python 实现：通过 if-else 或字典映射根据参数返回不同子类实例。单例适用于配置管理、连接池；工厂适用于需要根据不同条件创建不同对象的场景。",
        "key_points": ["理解两种模式的核心思想", "知道 Python 的实现方式", "了解适用场景"]
    },
    {
        "question_text": "什么是观察者模式？在什么场景下使用？",
        "category": "设计模式",
        "difficulty": "medium",
        "reference_answer": "观察者模式定义对象间一对多依赖关系，当一个对象状态改变时，所有依赖它的对象都会收到通知并自动更新。核心角色：Subject（被观察者）维护观察者列表并通知变化，Observer（观察者）定义更新接口。应用场景：事件驱动系统、发布订阅系统、GUI 事件处理。类似但不同于发布-订阅模式，观察者模式中 Subject 和 Observer 是松耦合但有直接关联。",
        "key_points": ["理解一对多的依赖关系", "知道Subject和Observer角色", "了解与发布订阅的区别", "能举出应用场景"]
    },
    # === 安全 ===
    {
        "question_text": "请解释 SQL 注入的原理和防护措施。",
        "category": "安全",
        "difficulty": "medium",
        "reference_answer": "SQL 注入是攻击者通过构造恶意 SQL 片段插入到查询语句中，欺骗数据库执行非预期操作。原理是未对用户输入做充分过滤和参数化处理。防护：1）使用参数化查询/预编译语句；2）ORM 框架的安全查询方法；3）输入校验和白名单过滤；4）最小权限原则，数据库账号仅授予必要权限；5）WAF 防火墙检测异常请求。",
        "key_points": ["理解注入原理", "知道参数化查询是最佳防护", "了解最小权限原则"]
    },
    {
        "question_text": "XSS 攻击和 CSRF 攻击分别是什么？如何防范？",
        "category": "安全",
        "difficulty": "medium",
        "reference_answer": "XSS（跨站脚本攻击）：攻击者注入恶意脚本到网页中，用户浏览时执行。防护：输出编码、CSP 策略、HttpOnly Cookie。CSRF（跨站请求伪造）：攻击者诱导用户点击链接，利用用户已登录状态发起恶意请求。防护：CSRF Token、SameSite Cookie、Referer/Origin 检查、关键操作二次验证。",
        "key_points": ["能区分 XSS 和 CSRF", "理解各自的攻击原理", "知道对应的防护措施", "了解 SameSite Cookie"]
    },
]


async def init_question_bank():
    """批量向量化并写入题库"""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

    db_url = (
        f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    )

    engine = create_async_engine(db_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as db:
        print(f"开始初始化题库，共 {len(PRESET_QUESTIONS)} 道题目...")

        for i, q in enumerate(PRESET_QUESTIONS, 1):
            try:
                question_data = {
                    "question_text": q["question_text"],
                    "category": q["category"],
                    "difficulty": q["difficulty"],
                    "reference_answer": q["reference_answer"],
                    "key_points": q["key_points"],
                }

                if HAS_PGVECTOR:
                    text = f"{q['category']} {q['question_text']}"
                    question_data["embedding"] = await get_embedding(text)

                question = QuestionBank(**question_data)
                db.add(question)
                print(f"[{i}/{len(PRESET_QUESTIONS)}] ✓ {q['category']}: {q['question_text'][:40]}...")
            except Exception as e:
                print(f"[{i}/{len(PRESET_QUESTIONS)}] ✗ 失败: {e}")

        await db.commit()
        print(f"\n题库初始化完成！共写入 {len(PRESET_QUESTIONS)} 道题目。")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_question_bank())
