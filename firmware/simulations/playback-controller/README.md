# 播放与内容 PC 仿真

版本 `0.2.2-batch2`。这是可独立复跑的控制、内容保存与 PC 文件恢复参考实现：两批已执行结果为 **47 PASS、0 FAIL、0 UNRESOLVED、3 DEFERRED**，见 [结果摘录](evidence/summary.md) 和 [机器可读结果](evidence/results.json)。

需要 **Python 3.10 及以上**，原结果实际使用 **Python 3.13.5**。全部依赖都是 Python 标准库，无需安装额外包。六个源码来自本项目已执行的仿真版本，保持原源码内容；测试用 PCM WAV 由代码合成，无需提供音乐文件或硬件。

## 运行

进入本目录，选择尚不存在的输出目录：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; python -B run.py --batch all --output runs/rerun-all"
```

`--batch 1` 只运行首批 26 个控制场景；`--batch 2` 运行第二批 21 个场景并列出 3 项 DEFERRED。可用重复的 `--case` 参数选取场景，例如 `--batch 2 --case PROC-TXN --case PROC-MEDIA`。每次运行使用新输出目录，运行器拒绝覆盖既有结果。

输出包含 `summary.md`、`results.json`、完整事件轨迹 `traces.jsonl` 和第二批的 DB/WAV 夹具。`runs/` 与默认输出 `evidence/latest/` 已被本包忽略规则排除。完整运行结果可能包含本机路径，应按仓库公开规则检查后再分享；本包附带的结果是已脱敏摘录。

退出码 0 表示本次执行没有 FAIL，仍应检查 UNRESOLVED 和 DEFERRED；断言或运行失败返回 1，参数错误或输出目录已存在返回 2。

## 已验证什么

| 范围 | 已执行内容 | 产品与验收对应 |
|---|---|---|
| 控制与可信事件 | ABC 会话、停止锁、同片抑制、开机等待明确播放、预检与启动失败分开、迟到回调拒绝、新 B/C 完整替换旧模式且不自动恢复 | F02/F03；T02/T03 的逻辑层；X01–X06 |
| 内容语义 | 保存版与活动快照分开、提交时引用保护、坏曲版本屏蔽及有界跳过、修复不插播、明确 PLAY 沿原快照找可播曲、最新成功保存和请求幂等 | F01/F02/F03/F07/F10/F11 的相关语义；T03/T04 的逻辑层；X07–X12 |
| PC 持久化与恢复 | SQLite 配置/提交序号/原回执事务；合成 WAV 完整校验与不可变版本发布；真实进程终止/重启、半文件盘点、旧真实文件句柄 | T04 的 PC 文件与进程子集；PROC-TXN/DUP/MEDIA/BOOT/PARTIAL |

音频使用 `FakeAudio` 记录命令和注入回调，不真实发声；NFC 使用 `FakeNFC` 注入可信事件，不读取标签。网页与本体显示只由抽象 `ClientView` 检查通知顺序。写失败与 ENOSPC 是软件注入，未填满真实磁盘。1000ms 读卡故障保护值仅为模拟参数。

| 未执行项 | 对应验收边界 |
|---|---|
| `SD-POWER` | 真实 SD/FAT 掉电与 ESP32 恢复；T04/C11/C20 的硬件持久化层 |
| `REAL-ADAPTERS` | 真实 NFC/音频回调、保护阈值、UI/HTTP、IO 并发与时延；T01–T04 的实物及适配器层 |
| `CODEC-MP3` | 实际 MP3 校验和解码；F01/T01；当前发布器只验证合成 PCM WAV |

这些结果覆盖 X01–X12 的确定序列及补充场景，未完成全部 L/C/E、完整 R2、固件烧录或整机验收。产品用例见 [验证计划](../../../product/validation.md)，公开接口交接见 [CONTRACT.md](CONTRACT.md)。

## 文件

| 文件 | 用途 |
|---|---|
| `controller.py` | 活动状态、控制规则、失败版本与内容引用占用 |
| `content_store.py` | SQLite 事务、WAV 发布、抽象 UI 通知 |
| `scenarios.py` | 首批独立期望与 RAM 夹具 |
| `batch2_scenarios.py` | 第二批内容及文件/进程故障场景 |
| `process_worker.py` | 独立进程事务屏障、恢复与启动盘点 |
| `run.py` | 分批/单场景运行与证据导出 |

共同规格基线为 `5262430cb385316403daadc68f4142c04d6f2259`，另包含 2026-10-10 已确认的新 B/C 完整替换和全坏后 PLAY 恢复搜索行为。SQLite、字段及错误码是 PC 参考实现，接入设备时按共享接口落实。
