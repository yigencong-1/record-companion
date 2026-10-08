# 来源与版本记录

核实日期按各节记录，更新日期2026-10-08。本文件记录外部作品、候选组件和技能的公开出处、版本与采用状态。

## 开源作品

### 墨水屏作品

- 作者作品页：https://oshwhub.com/juno_eda/xiaoshi_epaper
- GitHub：https://github.com/Juno-cyber/Xiaotian_Epaper
- Gitee：https://gitee.com/Juno-cyber/Xiaotian_Epaper
- 核实的GitHub分支：main。
- 分支提交：12ae6d740e2a28a43390a719fc71b2e7cf20b20a。
- 提交时间（API原值）：2025-07-19T09:48:23Z。
- 来源依据：作品页直接指向上述仓库，GitHub仓库及main分支已读取。
- 页面声明许可：CC BY-NC-SA 4.0。具体复用文件的许可仍按仓库与文件声明核实。
- 用途：显示与资料组织参考；2026-10-08按D025优先评估前屏材料、页面和刷新逻辑复用。
- 采用状态：未复制源码；用户实物未盘点，未固定屏幕器件或整套STM32固件路线。
- 2026-10-08通过GitHub API/raw实际读取固定提交的三个文件：

| 文件 | 字节数 | 核实内容 |
|---|---|---|
| [README.md](https://github.com/Juno-cyber/Xiaotian_Epaper/blob/12ae6d740e2a28a43390a719fc71b2e7cf20b20a/README.md) | 17460 | 2.9英寸、296×128屏，STM32F103CBT6、DS1302、VC02；黑白屏全刷约3秒、局刷约0.6秒仅为该说明条件，未实测 |
| [EPAPER.h](https://github.com/Juno-cyber/Xiaotian_Epaper/blob/12ae6d740e2a28a43390a719fc71b2e7cf20b20a/3.Software/Xiaotian_Epaper/Libraries/include/EPAPER.h) | 4596 | 支持黑白及黑白红，代码默认black_white_red；STM32 HAL GPIO底层使用MOSI/SCK/CS/DC/RST/BUSY，含局刷和深睡接口 |
| [Xiaotian_Epaper.ioc](https://github.com/Juno-cyber/Xiaotian_Epaper/blob/12ae6d740e2a28a43390a719fc71b2e7cf20b20a/3.Software/Xiaotian_Epaper/Xiaotian_Epaper.ioc) | 6848 | 原STM32配置及接口，不能直接当作ESP32-S3工程 |

VC02处理预设本地语音指令，不等于通用AI问答。若采用ESP32-S3原型，需移植显示底层与调度，验证刷新不打断播放。本地硬件库本轮按只读约定搜索，未找到同名作品副本；没有修改库或把其中资料当作库存。

2026-10-08功能审阅补充：通过raw地址读取上述固定提交README的功能说明和控制指令。README第5行列出时间显示、倒计时事件显示、累计事件显示和语音控制；第61–71行列出手动校时指令，第72行列出更换图片。第100行说明VC02以预设语句发送串口指令。README未列明天气或在线AI，不能将其视为原作已提供的功能。

本项目的显示候选及待选状态见[显示专项](../features/display/README.md)。此次仅核实公开说明，未读取完整应用逻辑、复制源码、确定原语音模块采用或进行实物验证；参考原作不等于决定沿用全部功能与器件。

### 流体模拟灯板

- 作者作品页：https://oshwhub.com/qiujc/fluid_sim_mcu
- 页面附件：源码和固件.zip。
- 页面声明许可：MIT License；实际附件文件声明在采用时核实。
- GitHub/Gitee地址：本次未在作品页核实到。
- 用途：灯光与互动显示参考。
- 采用状态：本轮未下载附件或复制源码。

## KK组件与技能候选

| 组件 | 作者源仓库 | 已核实参考提交 |
|---|---|---|
| KK_OLED | https://gitee.com/keysking/kk_oled | f01831d63b1d426b629921edaba644732aa29223 |
| KK_UI | https://gitee.com/keysking/kk_ui | 98f0349bdd9e1351353aa34086ac1393c915ba47 |

- 参考副本位于制作者自行配置的外部资料库，不属于本仓库。
- 通过各自Git remote与HEAD核实来源和当前本地版本；该次git status --short均无输出。
- 本地来源说明记录2026-10-06从作者Gitee main分支浅克隆，保留源码、Skills和许可证。
- 第一方组件与技能采用MIT；字体及其他资源按各自声明，不因组件MIT而改变。
- 外部资料库中的六个KK技能为候选快照，未复制到本工程；采用时核实完整包和版本。
- 本项目采用状态：候选。尚未决定增加OLED、KK_OLED或KK_UI。

## STM32CubeMX2技能

- 技能来源：外部资料库候选；本仓库尚未安装。
- 适用对象：cube mx与.ioc2；不作为旧版CubeMX命令行工作流。
- 官方资料：https://dev.st.com/stm32cube-docs/stm32cubemx2。
- 独立Git仓库出处：本次未核实。
- 本项目采用状态：候选，尚未复制或选定平台。

## 第一轮原型候选资料：2026-10-07

以下来源本轮已读取，用于核实接口能力，不表示已经采购、复制源码或通过实物验证。

| 候选/接口 | 实际读取的来源 | 本轮核实内容 |
|---|---|---|
| ESP32-S3-DevKitC-1 | [Espressif板卡入口](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/index.html)、[v1.1用户指南](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide_v1.1.html) | Wi-Fi、外设引出与USB调试；带八线Flash/PSRAM的板型有占用GPIO，实际库存板型需匹配 |
| ESP32-S3 I2S | [Espressif I2S文档](https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/peripherals/i2s.html) | 两个I2S外设，支持数字音频输入/输出；本轮只读取引言与接口说明 |
| ESP-IDF FAT文件系统 | [Espressif FAT文档](https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/storage/fatfs.html) | 挂载后可通过文件接口读写；原型主控直接管理存储是推荐路线 |
| MAX98357A I2S功放 | [Adafruit模块说明](https://learn.adafruit.com/adafruit-max98357-i2s-class-d-mono-amp/overview) | I2S输入、直接驱动扬声器；3.2W@4Ω为5V及10% THD条件，不能当作清晰音质的实测保证；差分扬声器输出不能接地 |
| PN532识别 | [Adafruit接线资料](https://learn.adafruit.com/adafruit-pn532-rfid-nfc/breakout-wiring) | 示例板支持SPI及TTL串口/I2C，3.3V系统接口；具体廉价兼容板供电和接口开关仍需核对 |

版本状态：以上为访问日期对应的公开网页，其中Espressif路径使用latest/stable，不代表已固定固件工具链版本。实际采用时再记录SDK和库版本及许可。模块与标签、扬声器、运动和灯光的组合能力尚未实测。

本地参考证据：ESP32-S3资料目录版本名为V1.1-20230804；显示与灯光目录含YX62877-ws2812全彩LED-20190510.zip；运动目录含TB6612驱动资料。仅核查入口和文件存在，本轮没有解压、复制或修改参考资料库。

## 双声道与电源候选资料：2026-10-08

| 候选/接口 | 本轮实际读取的来源 | 核实内容及边界 |
|---|---|---|
| MAX98357A声道选择 | [Adafruit引脚说明](https://learn.adafruit.com/adafruit-max98357-i2s-class-d-mono-amp/pinouts)的SD / MODE部分 | 可选择左、右或左右混合输出；两个模块分别选左/右可用于立体声原型。具体模块电阻与供电需核对，未实测 |
| BQ25895 | [TI产品页](https://www.ti.com/product/BQ25895)的Features及描述 | 单节锂电池开关充电、NVDC电源路径、系统负载与电池补充模式、温度检测。功率预算、SYS稳压路径与封装设计待数据手册及实物验证 |
| ESP32-S3-DevKitC-1 | [Espressif v1.1指南](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide_v1.1.html)的板卡介绍 | 主控模块包含Wi-Fi；不因联网需求自动增加蜂窝模块。配网、屏幕与音频并发仍需原型验证 |

通过agent-browser的文档读取功能核实上述公开说明。候选没有采购或复制到工程，芯片最大额定值不作为整机能力承诺。本地参考库只读检查显示0.96寸OLED、K210附带LCD资料与ESP32-S3资料入口；本轮没有把这些目录视作实际库存，也没有采用屏幕驱动或修改资料库。

## 嘉立创免费打样官方规则：2026-10-08

本轮通过agent-browser实际读取以下公开页面。三个细则页面标注更新时间均为2026-09-29；活动规则会变化，当前记录不是个人资格或优惠余额证明。

| 官方入口 | 实际核实内容 |
|---|---|
| [领券中心](https://www.jlc.com/coupons) | 通用券与EDA券、领取后30天有效、六层每月仅选其中一张使用、免费沉金面积20%限制，以及开源文件、返单和拆单不支持免费打样的表述 |
| [PCB+SMT免费券细则](https://www.jlc.com/portal/server_guide_37595.html) | 10×10 cm以内、5片、排除小于1 cm的小板表述、单片出货、常规工艺、阻焊颜色、设计软件和下单入口要求 |
| [六层券细则](https://www.jlc.com/portal/server_guide_37576.html) | 真实六层、1.6 mm、5片、绿油、单片不拼板、沉金、不需要阻抗，以及晒单与后续免费资格 |
| [0元福利规则](https://www.jlc.com/portal/server_guide_4114.html) | 每月两次0元福利、规则可能调整、同一客户识别条件，以及页面对免运费和24小时加急的宣传 |

官方领券页未在已读内容中定义自研公开工程是否属于“开源文件”，也未明确真实改版与返单的判定口径。这两项在提交制造文件前核实，不自动改变公开仓库要求或承诺免费迭代。项目处理见[项目计划](../product/plan.md#嘉立创免费打样规则核查)。

本轮未登录个人账号、领取优惠券、上传PCB文件或下单；没有据此确定主板尺寸、层数、材料与成品工艺。本机参考资料库没有新增访问或修改。

## 后续采用记录

每次真正采用组件、技能或素材时追加：

- 名称、作用与采用日期；
- 作者与源仓库/原始链接；
- 采用分支、提交、版本或文件发布信息；
- 公开来源链接与仓库内目标相对路径；
- 许可证及素材单独声明；
- 必要依赖、本地修改和实际验证结果。

这些字段用于追溯实际采用的材料。更新源仓库后按本项目需要同步，并保留项目改动。
