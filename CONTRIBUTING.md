# 参与设计

Record Companion 是公开的音乐唱片桌搭与唱片挂件项目。当前处于功能审阅、候选比较和模块原型规划阶段。

## 从哪里开始

先读 [整机规划](product/README.md)、[接口约束](product/interfaces.md) 和 [对应功能专项](features/)。一个PR围绕一个明确的问题，说明对应的F编号或专项、改动原因、影响范围、来源和验证状态，并遵守本页的公开边界。

| 主题 | 入口 |
|---|---|
| 音频、存储、左右声道 | [features/audio](features/audio/README.md) |
| 显示与本体操作 | [features/display](features/display/README.md) |
| 唱片挂件与识别 | [features/records](features/records/README.md) |
| 灯光与转动 | [features/lighting-motion](features/lighting-motion/README.md) |
| 网络与网页 | [features/network](features/network/README.md) |
| 电池与充电 | [features/power](features/power/README.md) |
| 结构、音腔与材料 | [features/enclosure](features/enclosure/README.md) |

## 提交方式

1. 在 [原仓库](https://github.com/yigencong-1/record-companion) 点击 Fork。
2. 在自己的 Fork 中创建分支，围绕一个功能或工程阶段提交改动。
3. 源码、PCB、网页和结构文件放入对应工程目录；规划规则放入对应 `product/` 或 `features/` 入口。
4. 发起 Pull Request，目标为 `yigencong-1/record-companion` 的 `main`。
5. 描述已验证内容和未验证内容；区分概念图、模拟、编译、烧录、总线观测、实物运行和使用体验。
6. 所有者审阅并合并；需要调整时继续向自己的分支提交。

外部代码、设计、字体、图片和音频须记录来源、版本和许可。不要上传令牌、Wi-Fi密码、本机凭据或私人生日内容。
