# 术语与编号速查

本页只解释项目文档里反复出现的术语和编号，不新增或修改任何规则。具体含义以各编号所在的权威文件为准。

## 唱片的三种模式（ABC）

唱片挂件只提供电子身份，A/B/C 类型由本体根据身份决定（D069）。

| 模式 | 名称 | 放上 | 取走 | 依据 |
|---|---|---|---|---|
| A | 单曲点播 | 播放绑定的一首歌 | 继续播放 | D066 |
| B | 驻留模式 | 进入模式，运行单曲、歌单或特殊行为，默认循环 | 确认取走后退出模式，停止并清空播放任务 | D066、D067 |
| C | 锁存模式 | 同 B | 模式继续运行；需要显式退出 | D066、D077 |

其他常见状态：

- **STOP_AUDIO / PAUSE_AUDIO**：B/C 中停止或暂停音乐，都不退出模式（D075、D079）。
- **跨 B/C 替换**：旧 C 已离座但仍在运行时放入新的 B/C 怎么处理，尚未确认（RC-08A-01）。

## 编号体系

| 前缀 | 含义 | 权威位置 |
|---|---|---|
| D001–D088 | 已确认的用户决定 | [product/decisions.md](product/decisions.md) |
| F01–F17 | 功能范围条目 | [product/README.md](product/README.md#功能范围) |
| P0–P7 | 项目阶段：范围 → 选型 → 模块原型 → 联合评审 → 主板 → 试制 → 成品 PCB/外壳 → 交付验收 | [product/plan.md](product/plan.md#项目总计划) |
| RC-xx | 规划工作包，如 RC-05A（ABC 边界）、RC-06（曲库与歌单）、RC-08（统一控制器模拟） | [product/plan.md](product/plan.md)、[TASKS.md](TASKS.md) |
| U1–U5、Q-C01–Q-C06、Q-I01–Q-I04 | 待用户确认的问题；确认后登记为 D071–D085 | [product/decisions.md](product/decisions.md) |
| T01–T12 | 整机验收计划，按功能对应 F 编号 | [product/validation.md](product/validation.md#整机验收计划) |
| X01–X12 | 控制器纯软件模拟的验收场景，尚未运行 | [product/validation.md](product/validation.md) |
| V001–V017 | 已产生的历史产物与证据记录 | [product/validation.md](product/validation.md) |
| R0–R3 | 复用参考工程的门槛：来源与许可核验 → 最小链路 → NFC 检测比较 → ABC 整机联合 | [features/records/README.md](features/records/README.md) |

注意：`features/platform/resource-allocation.md` 中的 `[R1]`、`[R2]` 等是该文件的参考资料编号，与上表的 R0–R3 门槛无关。

## 硬件与平台

| 术语 | 含义 |
|---|---|
| S3 | ESP32-S3，当前用于模块验证的主控（D063） |
| S31 | ESP32-S31，成品主线主控；准确模组和外围尚未冻结（D063） |
| NFC 标签 | 挂件内的无源标签，只提供身份编号，不存歌曲或行为（D058、D069） |
| 两条声音路线 | “音质”和“性价比”两套完整音频方案，按约 1 米听距比较（D064） |
| AP 配网 | 手机连接设备自身热点，用本地网页管理内容和配置外部 Wi-Fi（D024） |

## 验证状态用词

文档区分以下几种证据，它们不能互相替代：概念图、模拟、编译、烧录、总线观测、实物运行、使用体验。编译通过不代表实物功能通过（D086）。
