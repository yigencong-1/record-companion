# PC 仿真实际结果摘录

2026-10-10；实现 `0.2.2-batch2`；Python `3.13.5`。

本文件与 [results.json](results.json) 摘录两份已执行结果：

- `run-20261010-batch1-confirmed/results.json`：首批控制行为回归。
- `run-20261010-batch2-confirmed/results.json`：内容保存与 PC 文件/进程恢复。

完整原轨迹和 DB/WAV 运行材料留在本机。摘录保留原场景状态、覆盖标识、断言数和未执行原因，未补造测试结果。

| 批次 | PASS | FAIL | UNRESOLVED | DEFERRED |
|---|---:|---:|---:|---:|
| 1 | 26 | 0 | 0 | 0 |
| 2 | 21 | 0 | 0 | 3 |
| 合计 | 47 | 0 | 0 | 3 |

PASS 仅对应执行过的确定性断言。NFC 与音频使用假适配器；持久化案例使用真实 PC 文件和独立进程终止/重启，1000ms 仅为模拟参数。

| 场景 | 实际状态 | 覆盖或未执行原因 |
|---|---|---|
| X01 | PASS | D066,D067,D069;L01,L02 |
| X02 | PASS | D066,D075;L26,L29 |
| X03 | PASS | D067,D071,D079,D082;L08,L09,E02 |
| X04 | PASS | D052,D073;L19,L23 |
| X05 | PASS | D074;L13,L24 |
| X06 | PASS | D072;L18,L28 |
| L05 | PASS | D066;L04,L05 |
| L06 | PASS | D067;L06 |
| L27 | PASS | D071,D075;E03,C24-partial |
| L12 | PASS | D068,D079;L12,L20-partial |
| E01 | PASS | D079;L22,E01 |
| E15 | PASS | D082;E15 |
| L15 | PASS | D068;L15 |
| RACE01 | PASS | D068,D082 |
| RACE02 | PASS | D075,D082 |
| L13 | PASS | D074;L13 |
| L25 | PASS | D066,D074;L14,L25 |
| L10 | PASS | D068;L10 |
| D074-A | PASS | D074 |
| ADAPTER01 | PASS | D072;L07-domain-only,L16-suggestion |
| RACE03 | PASS | D068 |
| LOOP01 | PASS | D067 |
| IDENTITY01 | PASS | D069;RC-08A-02 |
| BOOT02 | PASS | D052,D073;L19 |
| ADAPTER02 | PASS | D072;adapter boundary |
| RC-08A-01 | PASS | User confirmed 2026-10-10;D074 |
| X07 | PASS | D077,D078;C06,C07,E13 |
| SNAP-C | PASS | D071,D077,D078 |
| SNAP-A | PASS | D078;C02,C06 |
| X08 | PASS | D076,D083;C08,C09,E06 |
| REF-ACTIVE | PASS | D076,D077,D083;C23,E05 |
| REF-AUDIO | PASS | D076;C09 |
| REF-RACE | PASS | D076,D083,D085;E04,E21 |
| X09 | PASS | D080,D084;C21,E07,E16,E17 |
| MEDIA-OLD | PASS | D084;RC-08C-02 |
| MEDIA-FAIL | PASS | D084;C10,E12 |
| RUNTIME-OPEN | PASS | D074,D080 |
| X10 | PASS | D080,D084;C22,E08,E18 |
| X11 | PASS | D085;C05,E09,E19 |
| X12 | PASS | D085;C19,E10,E20 |
| PROC-TXN | PASS | D085;C20,RC-08C-01 |
| PROC-DUP | PASS | D085;RC-08C-01 |
| PROC-MEDIA | PASS | D084;C11,RC-08C-02 |
| PROC-BOOT | PASS | D052,D073 |
| PROC-PARTIAL | PASS | D084;C10,C11,E16 |
| RC-08B2-01 | PASS | User confirmed 2026-10-10;D080,D084 |
| RECOVERY-ORDER | PASS | User confirmed 2026-10-10;D077 |
| SD-POWER | DEFERRED | Physical SD/FAT power loss and ESP32 recovery require actual storage/electrical bench |
| REAL-ADAPTERS | DEFERRED | 03/04 real audio/NFC callbacks, thresholds, UI/HTTP and concurrency timing |
| CODEC-MP3 | DEFERRED | Real MP3 validation/decoding; PC publisher only validates synthetic PCM WAV |

X01–X12 对应 [行为验证计划](../../../../product/validation.md) 的确定序列；其他场景补充回调竞态、引用占用、事务中断和媒体版本检查。它们不代表全部 L/C/E 用例、完整 R2 或 T01–T04 实物验收完成。

仍未执行：真实 SD/FAT 掉电及 ESP32 恢复、真实音频/NFC/UI/HTTP 适配器和并发时序、实际 MP3 校验/解码。
