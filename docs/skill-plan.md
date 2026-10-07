# 技能选择与迁移计划

## 当前状态

本项目 .agents/skills/ 目前只包含目录保留标记，尚未安装领域技能。
关联硬件参考目录与自动发现它的技能是不同的机制；领域技能按实际方案采用。

## 全局辅助技能

| 技能 | 用途 |
|---|---|
| agent-browser | 查找、核实作品、模块和工具资料 |
| pdf:pdf | 器件手册、尺寸图与硬件文档 |
| frontend-design | 手机配置网页的视觉与操作设计 |
| visualize:visualize | 需要交互时展示流程、灯光或状态变化 |
| openai-docs | 需要核实Codex设置、项目或技能机制时 |

全局技能沿用已有安装，按需调用，不为本项目重复复制。工具能力与依赖在使用时核实。

## 当前硬件库的项目级候选

来源为制作者自行配置的外部硬件资料库，公开文档不记录实际本机路径。采用时核实完整技能包与公开来源。

| 技能 | 采用条件 | 来源 |
|---|---|---|
| stm32cubemx2-cli | 使用STM32CubeMX2及.ioc2工程 | 本地维护的项目技能，参照ST官方文档 |
| kk-oled-port | 新接入或迁移KK_OLED | keysking/kk_oled |
| kk-oled-use | 已采用KK_OLED后的应用绘图、动画与刷新 | keysking/kk_oled |
| kk-oled-font | KK_OLED中文字模、缺字或字体裁剪 | keysking/kk_oled；字模服务另按其声明 |
| kk-ui-port | 接入基于KK_OLED的KK_UI | keysking/kk_ui，依赖KK_OLED |
| kk-ui-use | 已接入KK_UI后的产品页面与交互 | keysking/kk_ui |
| kk-ui-extend | 有公共组件扩展价值，且已获得明确同意 | keysking/kk_ui |

当前尚未确认OLED、KK库或STM32CubeMX2，不据此决定产品是否增加屏幕，也不提前迁入这些技能。

## 其他项目中已检查的技能

- ESP-Claw 的 http_server_lua_demo 使用设备端 lua_run_script_async 能力，是设备代理的运行技能。可参考源码思路，不能直接作为本项目Codex嵌入式开发技能。
- esp-claw_6 的 OpenSpec 技能位于 .opencode/skills，依赖OpenSpec CLI，并使用原环境的工具约定。当前采用项目文档记录决定；需要该流程时再评估适配。
- 已检查的候选尚未确认可直接用于本项目音频、唱片识别与外壳制作。后续依据实际平台、工具和需求继续筛选。

## 采用与更新

1. 确认任务与技能范围一致，阅读SKILL.md并核实依赖、许可与工具能力。
2. 按需要复制完整技能目录，包括引用的references、assets、scripts和必要的关联技能。
3. 保存为本项目快照，记录公开来源仓库、采用提交或版本、仓库内目标相对路径和本地改动。
4. 按客户端机制重新发现技能，核实新聊天能使用并且引用文件存在。
5. 按技能接入要求建立工程源码副本；维护项目已有修改。
6. 上游更新时按本项目需要检查和同步，而不以“最新版本”替代已验证版本。

真正跑通音频、唱片识别或网页更新流程后，可把有复用价值的步骤、脚本和证据整理成项目专用技能。

机制参考：[官方本地技能加载说明](https://learn.chatgpt.com/docs/build-skills.md)。

