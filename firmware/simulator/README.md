# ABC 统一控制器纯软件模拟（RC-08B）

本目录是 [TASKS.md](../../TASKS.md) 中 RC-08B-01、RC-08C-01、RC-08C-02 的纯软件实现：一个不依赖 ESP32、NFC 读卡器或 SD 卡的确定性控制器，加上一组可重复运行的测试。

**状态：** 仅模拟层。测试通过只说明控制逻辑符合已确认的 D 编号规则，**不代表**任何硬件、读卡时延、音频或 SD 掉电行为已验证（D086）。

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
| X01–X12 | 全部覆盖 |
| L 系列 | L02、L03、L05、L06、L08–L10、L12–L15、L20–L23、L25–L29 |
| C 系列 | C02、C07、C08、C15、C16、C21、C22 |
| E 系列 | E01–E03、E06–E10、E15–E18、E20、E21 |

每个事件都会写入一条日志，字段与 [interfaces.md](../../product/interfaces.md) RC-08 的状态输出建议一致：`event_seq`、`placement_id`、`session_id`、`mode_kind`、`audio_state`、`selected_track_id`、`playlist_snapshot_revision`、`media_revision`、`saved_binding_revision`、`successful_commit_seq`、`last_error`。

## 未确认的规则（不猜测）

**RC-08A-01 跨 B/C 替换：** 一个 B/C 仍活动时放入另一张 B/C，控制器只报告 `UNRESOLVED_CROSS_MODE` 并保持旧模式。这是占位行为，不是产品决定；确认后修改 `_trigger` 中对应分支和 `test_rc08a01_*` 测试即可。

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
