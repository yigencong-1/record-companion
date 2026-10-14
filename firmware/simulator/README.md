# ABC 统一控制器纯软件模拟（RC-08B）

本目录提供 ABC 控制规则的 `unittest` 仿真工程：一个不依赖 ESP32、NFC 读卡器或 SD 卡的确定性控制器，加上一组可重复运行的测试。活动任务见 [TASKS.md](../../TASKS.md)。

按[D092](../../product/decisions.md)，**本目录是软件开发、调用和回归的唯一主入口**。本轮在协作者控制器上实现D093–D095，并将[playback-controller](../simulations/playback-controller/README.md)的异步代次、媒体版本隔离和进程恢复场景迁入本控制器；不是把两份控制器并排当作整合。补充目录继续保存`0.2.2-batch2`的SQLite、WAV发布、旧文件句柄和多进程实验，本版本仍使用JSON存储，不指定ESP32最终后端。

**状态：** 主控制器的PC实现和回归已完成本轮整合；硬件、读卡时延、音频和SD掉电仍未验证（D086）。主版本测试与补充版47项分别报告，不能相加宣称硬件覆盖。

2026-10-14融合版运行 **70项全部通过**：原43项中首次启动失败的错误期望已按D074修正，新增27项覆盖下表。复跑摘要见[本轮结果](evidence/integration-20261014.json)和[V023](../../product/validation.md#v0232026-10-14-软件主版本实质整合)；此前43项记录仍见[V021](../../product/validation.md#v0212026-10-14-两套pc控制器联合回归)。

## 运行

只需要 Python 3.10 及以上，不需要安装任何第三方库：

```shell
python -B -m unittest discover -s firmware/simulator/tests -v
```

从仓库根目录运行。测试仅使用Python标准库；可设`RC_SIM_TEST_TMP`为既有临时目录，测试会在其下创建并清理独立子目录，不修改系统TEMP。仓库的GitHub Actions仍运行本目录的unittest测试集。

## 本轮实质迁入与新增

| 规则/来源 | 本主版本已执行的能力与场景 |
|---|---|
| D093 | 普通歌曲/歌单选曲持久保存；开机静音；明确PLAY从选曲开头；目标缺失报错；保存失败不替换旧选择；兼容无此字段的旧JSON |
| D094 | 先进入绑定态再捕获新放置；保存/取消/退出页面与持续读到同片均不自动播；真实B离座仍退出；活动C快照保持；已在位才进入页面和已离座捕获不会误保存 |
| D095 | B/C及普通歌单中途暂停NEXT静音选曲，明确PLAY从新曲0:00；未换曲的暂停恢复保留位置；迟到EOF不改选曲 |
| D074、补充版RUNTIME-OPEN | 新模式首曲失败不跳可播第二首，不恢复旧模式；已运行模式的后续打开失败才按D080跳过 |
| D072、补充版X06/ADAPTER边界 | 未读到UID不伪造离座；身份不确定保持原故障计时；保护退出后恢复或显式执行不能绕过可信空座/新放置 |
| 补充版RACE01/02/03 | 可选异步STARTING及开始成功/失败回调；STOP后迟到启动/EOF无效；旧会话、旧操作和重启前完整信封不影响新播放 |
| 补充版MEDIA-OLD | 坏曲按媒体版本屏蔽；旧版本读取错误不污染新版本；修复不插播；全坏修复后仍需PLAY；普通暂停恢复保留当前媒体版本和位置 |
| 补充版PROC-TXN/PARTIAL的JSON适配 | 实际子进程在JSON替换前/后强制退出，重新读取配置、提交序号与回执；已提交请求重试不再提交；未完成临时JSON不提升为权威状态 |

尚未迁入本主版本：SQLite多写者序列化、真实WAV完整校验/不可变文件发布、旧文件句柄释放及媒体文件回收。它们继续保留为补充实验，不算本目录已具备的功能。主版本的`verified`仍是测试注入值，不能用它证明真实音频文件合格。

## 调用语义

| 用途 | 本主版本入口 |
|---|---|
| 普通播放 | `select_track(track_id)`、`select_playlist(playlist_id, track_id=None)`选择并启动；`play()`明确恢复/启动；`next_track()`支持普通歌单中途切曲及转交模式切曲 |
| 开机待启动唱片 | `Controller(store, present_uid=...)`只盘点，`start_held()`明确启动；与恢复的普通选曲分别保留，不替实际按键决定目标优先级 |
| 绑定交互 | `enter_binding_page()`→可信`card_inserted(uid)`→`save_captured_binding(request_id,kind,target)`→`leave_binding_page()`；取消只离开页面 |
| NFC | `card_inserted`/`card_removed`只接可信事件；`reader_recovered(None)`只是没读到身份；`trusted_empty=True`必须由调用方提供可靠空座证据，当前只在PC注入 |
| 音频PC适配 | 默认同步假播放器兼容原场景；`Controller(..., async_audio=True)`先进入STARTING，取`audio_token()`后回传`audio_started(token)`、`audio_start_failed(token)`、`audio_eof(token)`或`audio_read_error(token)` |
| 状态 | `device_state()`输出普通选择、选曲、位置、绑定态、放置/会话、音频信封及配置；`log`保留原规则的逐事件记录 |

音频信封含`boot_id/gen/session_id/track_id/media_version`。整数`gen`仅兼容原PC用例，跨重启边界必须传完整信封。STARTING并非真实解码或出声确认；音频执行端的实际停止屏障、资源释放和延迟尚待适配器验证。

普通选择在明确选歌/歌单及普通NEXT时保存；A唱片点播临时接管，B/C会话不覆盖这份普通选择记忆。当前JSON采用单控制器单写者、临时文件flush/fsync后替换；设备端写入频率、Flash寿命、目录同步和SD掉电保证另行验证。

## 结构

| 文件 | 内容 |
|---|---|
| `rc_sim/controller.py` | 统一控制器：物理事件、用户命令、音频回调、内容管理 |
| `rc_sim/store.py` | 带持久化语义的虚拟存储：曲库、歌单、绑定、提交序号与 request_id 回执 |
| `tests/test_x_scenarios.py` | [validation.md](../../product/validation.md) 的 X01–X12，每条一个测试 |
| `tests/test_abc_rules.py` | L/C/E 系列中已确认、可纯逻辑验证的规则 |
| `tests/test_commit_protocol.py` | D085 最后成功保存覆盖、幂等重试、写入失败、重启恢复 |
| `tests/test_integrated_rules.py` | D093–D095、D074/D072修正及迁入的代次/媒体版本/进程恢复回归 |

## 覆盖范围

| 场景 | 测试 |
|---|---|
| X01–X12 | 已列确定性序列；不代表各场景的全部异常或硬件边界 |
| L 系列 | L02、L03、L05、L06、L08–L10、L12–L15、L20–L23、L25–L29 |
| C 系列 | C02、C07、C08、C15、C16、C21、C22 |
| E 系列 | E01–E03、E06–E10、E15–E18、E20、E21 |

每个事件都会写入一条日志，字段与 [interfaces.md](../../product/interfaces.md) RC-08 的状态输出建议一致：`event_seq`、`placement_id`、`session_id`、`mode_kind`、`audio_state`、`selected_track_id`、`playlist_snapshot_revision`、`media_revision`、`saved_binding_revision`、`successful_commit_seq`、`last_error`。

## 与现行规则的对齐

跨 B/C 替换按 D089：活动 C 已离座时，新的有效 B/C 完整替换旧会话，结束后不恢复旧 C；新目标预检失败保留旧会话，启动失败不回滚。C 同片重放继续按 D071 保留原会话。D090 的明确 PLAY 按活动快照原顺序从当前选曲查找可播曲，修复发布本身不唤醒音频。

补充回归检查连续读卡故障报告不会重置保护起点，以及文件打开/替换发生 `OSError` 后配置、提交序号和回执一起回滚，同请求可重新尝试保存。文件错误通过 `mock` 注入，未实际填满磁盘或验证 SD 掉电。

## 现有实现差异与待验证参数

以下记录实际代码行为及其状态；已有决定的差异按规则修正，真实待定项继续审阅：

1. **启动中NEXT、错误停止NEXT及普通歌单末尾：** STARTING返回未定义状态，普通歌单末尾返回`ORDINARY_QUEUE_END_UNSPECIFIED`；错误停止NEXT保留原PC静音选曲行为，尚不作为新产品决定。PREV、音量和普通歌单自然结束/循环策略待细化。
2. **A 或点歌的歌曲自然结束：** 停止，不循环（interfaces.md 中标为“建议”）。
3. **真实音频/NFC接口：** 已有PC异步回调信封，但UID仍为字符串夹具，未实现技术类型/原始字节编码、真实NCI放取判断、HTTP或屏幕页面。
4. **座上有片时又读到另一张 UID：** 记 `SEAT_CONFLICT`，不切换（L16 为“建议”）。
5. **读卡器恢复后UID不同或未读到：** 保留不确定/故障计时并记`NEEDS_RESEAT`，不合成取走；相同身份或独立可信空座才能结束这次不确定状态。
6. **读卡故障保护阈值：** 默认 3000 ms，仅为检验规则的候选参数，真实阈值待实测（D072）。

## 不能用模拟验证的内容

真实 NFC 身份隔离与离座时延、邻片干扰、音频欠载与断音、SD 写阻塞与掉电原子性、功耗、音质、按键手感和墨水屏刷新，仍需按 T01–T04 实物测试。虚拟存储使用“写临时文件再替换”的语义，只说明协议设计，不代表真实文件系统掉电安全。
