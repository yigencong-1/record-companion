# Record Companion · 唱片桌搭

一套通用音乐唱片桌搭：桌面本体可离线播放音乐，配合灯光和唱片转动，也能不放唱片直接播放。邓紫棋、汪苏泷和通用唱片用于选择不同内容，小唱片同时可作为书包挂件。另保留一张可配置的生日唱片和一个生日菜单入口，具体内容与交互待设计。

当前阶段：**首版功能与操作审阅，材料待盘点**。功能范围、操作建议与验收计划集中在[功能规格评审稿](docs/function-spec.md)。本体离线操作覆盖基本全部功能；日常显示采用时间/日期、播放器状态、事件页面和静态图片切换，参考墨水屏项目。唱片放入即播、取走暂停、换片播放新绑定内容，无唱片仍可使用；AI留到后续扩展。具体操作仍需细化，尚未整体冻结首版。原型阶段同步争取更好的音质，芯片与模块经过候选比较、试验和审阅后选择，再集成单主板。联网通过本地AP网页配置外部Wi-Fi，基础功能离线可用。内置电池、Type-C边充边用，续航尽量长。嘉立创免费打样资格与工艺条件每轮核对，功能和硬件均未实现或实测。

## 从这里接手

1. 阅读 [项目简报](docs/project-brief.md)，了解已确认要求与待定事项。
   阅读 [功能规格](docs/function-spec.md)及[目录职责](docs/repository-map.md)，查看当前评审项和实际工程状态。
2. 按 [Codex App 接手步骤](docs/app-setup.md) 创建项目和主控聊天。
3. 发送接手步骤中的短启动消息，让新聊天读取 [完整主控提示词](docs/controller-prompt.md)。
4. 后续决定写入 [决策记录](docs/decisions.md)，制作证据写入 [验证记录](docs/verification.md)。

| 项目 | 设置 |
|---|---|
| 项目名称 | Record Companion · 唱片桌搭 |
| 工作位置 | 当前仓库根目录 |
| 外部参考资料 | 由协作者自行配置，按只读约定查阅 |
| GitHub 仓库 | [yigencong-1/record-companion](https://github.com/yigencong-1/record-companion) |
| 仓库可见性 | Public，所有人可查看 |
| 本地分支 / 远程 | main / origin |

## 一起参与设计

同学通过 Fork 和 Pull Request 提交设计、文档与代码，不授予原仓库写权限；`main` 由所有者 `yigencong-1` 审阅并合并。参与步骤见[贡献说明](CONTRIBUTING.md)。目前正在核对材料和小模块方案，可以从结构布局、声音、电源、墨水屏或网页中的一个明确问题开始讨论。

## 文件组织

| 位置 | 内容 |
|---|---|
| AGENTS.md | 本项目工作约定 |
| docs/ | 项目设定、决定、主控提示词、技能安排、接手和验证文档 |
| references/ | 开源作品、本地资料、组件与技能来源 |
| assets/ | 后续唱片封面、图案、音频和灯光主题素材 |
| firmware/ | 后续模块原型程序与正式固件 |
| hardware/ | 后续接线、BOM、原理图与 PCB |
| mechanical/ | 后续可编辑结构模型与打印文件 |
| web/ | 设备AP与局域网管理网页源码，当前只有入口说明 |
| .agents/skills/ | 后续采用的项目级技能完整副本 |

工程目录中的保留标记用于让 Git 保存目录结构，不代表已有代码、模型或已安装技能。

目录职责、文档事实来源与完善顺序见[仓库说明](docs/repository-map.md)。固件、硬件、结构和网页目录已有职责说明，尚无实际工程或构建入口。

## 推进顺序

~~~mermaid
flowchart TD
    A["功能梳理与候选调研"] --> B["审阅试验方案，逐块模块验证"]
    B --> C["证据与集成选型评审"]
    C --> D["单主板原理图与试验PCB"]
    D --> E["核对免费券条件，试制与测试"]
    E -->|"针对问题改版"| D
    E -->|"方案稳定"| F["成品PCB与外壳并行设计"]
    F --> G["成品材料、装配与验收"]
~~~

## 相关入口

- [第一轮方案审阅与材料清单](docs/first-round-review.md)
- [下一步规划](docs/next-stage-plan.md)
- [首版功能规格与操作评审](docs/function-spec.md)
- [仓库职责与完善顺序](docs/repository-map.md)
- [开发流程、选型评审与免费打样规则](docs/development-process.md)
- [墨水屏唱片桌搭实体效果图](assets/concepts/epaper-player-3d.png)（外观概念，未验证制造尺寸）
- [材料与制作条件盘点](hardware/inventory.md)
- [已确认决定](docs/decisions.md)
- [技能选择与迁移](docs/skill-plan.md)
- [参考索引](references/index.md)
- [来源与版本记录](references/sources.md)
- [Git 日常使用](docs/git-workflow.md)
- [参与设计与提交PR](CONTRIBUTING.md)

本仓库保存可共同设计的技术方案与验证记录。外部作品、组件和技能按实际采用情况保留来源、版本和许可；本机绝对路径与个人背景不纳入公开文件。

