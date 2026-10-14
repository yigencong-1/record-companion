# ABC 统一控制器纯软件模拟（RC-08B）

本目录提供 ABC 控制规则的轻量 `unittest` 交叉回归模型：一个不依赖 ESP32、NFC 读卡器或 SD 卡的确定性控制器，加上一组可重复运行的测试。活动任务见 [TASKS.md](../../TASKS.md)。

[playback-controller](../simulations/playback-controller/README.md) 的 47 项 PC 工程继续作为主交接、真实文件及进程恢复验证入口。本目录便于单独检查规则与提交语义，保存后端为简化 JSON；两套结果各自报告，不将数量相加宣称新增产品或硬件覆盖。

**状态：** 仅模拟层。测试通过只说明控制逻辑符合已确认的 D 编号规则，**不代表**任何硬件、读卡时延、音频或 SD 掉电行为已验证（D086）。

2026-10-14联合审阅后运行43项测试全部通过；原37项中的跨B/C待定占位已改为现行决定，故障计时与文件错误另补回归。复跑结果及边界见[V021](../../product/validation.md#v0212026-10-14-两套pc控制器联合回归)。

## 运行

只需要 Python 3.10 及以上，不需要安装任何第三方库：

```
cd firmware/simulator
python3 -m unittest discover -s tests -v
```

仓库的 GitHub Actions 会在相关文件改动时自动运行同一条命令（`.github/workflows/simulator.yml`）。

## 结构

| 文件 | 内容 |
|---|---|
| `rc_sim/controller.py` | 统一控制器：物理事件、用户命令、音频回调、内容管理 |
| `rc_sim/store.py` | 带持久化语义的虚拟存储：曲库、歌单、绑定、提交序号与 request_id 回执 |
| `tests/test_x_scenarios.py` | [validation.md](../../product/validation.md) 的 X01–X12，每条一个测试 |
| `tests/test_abc_rules.py` | L/C/E 系列中已确认、可纯逻辑验证的规则 |
| `tests/test_commit_protocol.py` | D085 最后成功保存覆盖、幂等重试、写入失败、重启恢复 |

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

## 实现时补充的假设

以下几点规格里没有写明，模拟器按最保守的方式处理，需要审阅：

1. **B/C 播放或暂停时按 NEXT：** 直接播放下一首（STOP 状态下按 D082 只选曲）。
2. **A 或点歌的歌曲自然结束：** 停止，不循环（interfaces.md 中标为“建议”）。
3. **进入 B/C 时第一首就不可播：** 按会话内坏曲处理，跳到下一首（D080）。
4. **座上有片时又读到另一张 UID：** 记 `SEAT_CONFLICT`，不切换（L16 为“建议”）。
5. **读卡器恢复后看到的 UID 与故障前不同：** 视为无法证明取放，记 `NEEDS_RESEAT`，不自动触发。
6. **读卡故障保护阈值：** 默认 3000 ms，仅为检验规则的候选参数，真实阈值待实测（D072）。

## 不能用模拟验证的内容

真实 NFC 身份隔离与离座时延、邻片干扰、音频欠载与断音、SD 写阻塞与掉电原子性、功耗、音质、按键手感和墨水屏刷新，仍需按 T01–T04 实物测试。虚拟存储使用“写临时文件再替换”的语义，只说明协议设计，不代表真实文件系统掉电安全。
