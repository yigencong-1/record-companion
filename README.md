# Record Companion · 唱片桌搭

Record Companion 是一个可共同设计的音乐唱片桌搭：本体离线播放本地音乐，配合前置显示、灯光和可选的唱片转动；小唱片既是内容入口，也可以作为书包挂件。首版保留三类常规唱片和一张生日唱片，基础功能不依赖互联网。

当前阶段是首版功能、跨功能接口和模块选型审阅。正式芯片、PCB、外壳和成品材料都要在候选比较与原型证据之后确定。AI问答留作后续扩展，不能成为首版联网或电源设计的前提。

## 先看这里

| 入口 | 内容 |
|---|---|
| [整机规划](product/README.md) | 已确认产品、F01–F17功能范围与跨功能目标 |
| [共享接口](product/interfaces.md) | 音频、屏幕、识别、网络、电源、空间和功耗约束 |
| [决策记录](product/decisions.md) | D001–D048用户决定及其状态 |
| [开发流程](product/development.md) | 并行规划、候选比较、模块验证、嘉立创试验板和成品板流程 |
| [整机验收](product/validation.md) | T01–T12计划和V001–V012公开证据边界 |
| [功能专项](features/) | 音频、显示、唱片、灯光运动、网络、电源、结构七条专项 |
| [参考来源](references/README.md) | 外部作品、器件、技能与许可记录 |

## 已确认的产品行为

- 本体是通用本地音乐播放器，无唱片也能通过本体或网页播放。
- 左右独立声道与前置屏是当前评估方向；音质优先于盲目压缩体量，最终尺寸由扬声器、音腔、电池和装配证据共同确定。
- 三类常规唱片对应可重设的内容绑定；另只保留一张生日唱片和一个生日菜单入口。
- 唱片是并列播放入口：放片即播、取走暂停、换片播放新绑定内容；同一张持续在位不重复启动。
- 本体离线覆盖基本全部首版功能；手机网页用于控制、上传、绑定和AP配网，外部网络断开时本地功能继续。
- 内置电池支持Type-C边充边用，续航目标为尽量长；容量、输入功率和时长尚待测量。

## 功能专项

| 目录 | 关注范围 |
|---|---|
| [audio](features/audio/README.md) | 本地文件、左右声道、存储、功放与试听 |
| [display](features/display/README.md) | 墨水屏候选、时间/日期、播放器状态、事件和静态图片 |
| [records](features/records/README.md) | 挂件、身份识别、在位/取走判断、绑定和播放触发 |
| [lighting-motion](features/lighting-motion/README.md) | 灯光、唱片转动、噪声、夜间模式 |
| [network](features/network/README.md) | 本地网页、AP配网、上传、保存和断网边界 |
| [power](features/power/README.md) | 电池、Type-C电源路径、充电、温升和续航 |
| [enclosure](features/enclosure/README.md) | 音腔、尺寸、固定、维护和成品材料 |

工程入口仍按实际交付划分为 [firmware](firmware/README.md)、[hardware](hardware/README.md)、[web](web/README.md) 和 [mechanical](mechanical/README.md)。当前尚无可运行固件、网页、嘉立创原理图/PCB或可制造结构模型。

## 参与方式

项目公开可读。同学通过 Fork 创建分支并提交 Pull Request，目标为 `main`；所有者审阅并合并，不能直接修改原仓库 `main`。开始前阅读本页、[整机规划](product/README.md) 与 [贡献说明](CONTRIBUTING.md)。

公开仓库只保存技术规划、来源和脱敏证据。实际库存、私人素材、本机设置、凭据和会话记录由协作者留在各自仓库之外。
