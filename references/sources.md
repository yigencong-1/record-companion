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

## ESP32-S31官方候选资料：2026-10-08

- [乐鑫ESP32-S31产品页](https://www.espressif.com/en/products/socs/esp32-s31)：已读取官方产品说明，双核32位RISC-V最高320 MHz、512 KB SRAM、芯片标称60 GPIO、双I2S及250 MHz 8位DDR PSRAM接口；NRV16/NRV32标示16/32 MB PSRAM，WROOM模组标示54 GPIO。这些不等于开发板实际可用引脚、并发结果或整机扩展余量。
- 产品页列出[Function CoreBoard-1](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s31/esp32-s31-function-coreboard-1/user_guide.html)、[Korvo-1](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s31/esp32-s31-korvo-1/user_guide.html)及购买入口。后续主控专项已核对板型资料、原理图及资源草案，证据集中维护在[公开依据](../features/platform/README.md#本轮公开依据)；国内到手价、库存和本项目移植仍未验证。
- [S31 Developer Platform](https://esp32-s31.espressif.com/en)和[ESP-IDF S31指南](https://docs.espressif.com/projects/esp-idf/en/latest/esp32s31/index.html)为官方入口。主控专项已核到[stable入门文档](https://docs.espressif.com/projects/esp-idf/en/stable/esp32s31/get-started/index.html)标示v6.1、I2S/SDMMC指南及音频组件自v2.5.0支持S31的声明；固定组件包、编译/移植、运行稳定性和并发仍需实现验证，不以文档支持当整机通过。

以上为资料依据，未复制第三方工程。阶段方向已按D063确定为S3模块验证、S31成品主线，准确开发板/内存和成品芯片或模组仍未定稿。

## 2026-10-09 · NFC唱片机与实体音乐播放器参考工程登记

本轮是**开源工程取证与复用筛选**，不是采购、克隆、编译、烧录或实测。对嘉立创项目读取公开详情中的描述/附件列表，尚未取得或解压ZIP、7z，也未逐网检验在线EDA；对以下GitHub仓库已实际读取根目录、相关子目录和部分源码/配置，仍未构建。作者宣称实现与本项目已验证要严格区分。为避免“同名ABC”，以下出现的电路路线与Record Companion产品ABC行为没有关系。

| 编号 | 工程 / 来源 | 已核实的资料层级 | 适合借鉴 / 风险及许可 |
|---|---|---|---|
| OSH-01 | [lueer：卡片音乐播放器-终极版](https://oshwhub.com/lueer/card-music-player-ultimate-editi)；更新2024-12-25 | 页面载ESP32-WROOM-32E、RC522、PCM5102A+PAM8403、SD、AP/STA网页、作者称Arduino程序和SD网页资源；附件字节/EDA/BOM尚未取得 | 嘉立创**主对照**：网页管理、NFC与音乐架构；项目使用标签写入信息，须改成本体UID→ABC映射；GPL-3.0与“未经作者授权禁止转载”并存，复用前核许可 |
| OSH-02 | [yio-lab：NFC唱片机](https://oshwhub.com/yio-lab/record-player)；更新2025-12-12 | 页面有ESP32、RC522、SD、MAX98357与转盘实物描述、简易物料表；设计图预览未生成、BOM为空、可编译程序未确认 | 音频/NFC/运动空间参考；其“标签写关键词找歌”与本项目数字身份映射不同；GPL-3.0和转载限制 |
| OSH-03 | [lo_startnet：Minecraft我的世界唱片机](https://oshwhub.com/lo_startnet/project_zqmulhqj)；更新2026-06-10 | STM32F103+RC522+SDIO+I2S HT513，页面有材料/结构与作者报告的FatFs、拨轮时序缺陷；固件`JukeBox.zip`和结构附件仅确认列表存在 | 取放、状态机、机械和真实缺陷参考，代码不可直接烧到S3；CERN-OHL-S-2.0、转载限制，ZIP未解压 |
| OSH-04 | [yurix：北极熊NFC唱片机](https://oshwhub.com/yurix/project_nfhqsyjx)；更新2026-05-19 | STC15+RC522+DFPlayer Mini，页面含UID到歌曲文件夹流程；程序ZIP、结构ZIP、元器件清单DOCX仅确认存在 | UID查本机内容的行为与本项目吻合，但卡表写死于程序、不是在线可改映射；GPL-3.0及转载限制，非成品音频/供电基线 |
| OSH-05 | [mengmeng666666：集成一体化NFC唱片机](https://oshwhub.com/mengmeng666666/integrated-all-in-one-nfc-record)；更新2026-01-07 | 页面描述单PCB集成、SD改音乐、电机转盘与音量，作者填报复刻成本￥60；当前未取到原理图/BOM/代码 | 集成布局备查，证据不足不列首要复刻；GPL-3.0，￥60不能当本项目BOM |
| OSH-06 | [misteting：mc唱片机](https://oshwhub.com/misteting/mc-record-player)；更新2025-05-26 | 公开USB改歌/USB扬声器功能与`STM32_project.7z`、3D模型附件列表；尚未解压/验证 | 后续USB与小体量体验参考，当前优先级低；GPL-3.0/转载限制，作者续航/价格非本项目数据 |
| GH-01 | [lucadentella/NFCMusicPlayer](https://github.com/lucadentella/NFCMusicPlayer)；读取提交`222db99589f277d404772c99f920af41ca0a4905` | **已实际确认**KiCad 8的`.kicad_sch`/`.kicad_pcb`、原理图PDF存在；Arduino源码`NFCMusicPlayer.ino`/`MappingsFile.ino`/`Webserver.ino`、`platformio.ini`、SD网页HTML/JS/CSS及映射文本；未编译 | **优先完整架构参考**：PN532→UID映射→SD MP3→MAX98357A、AP网页增删映射/上传；实际固件读卡间隔`NFC_READ_INTERVAL=2000ms`且单次读取超时1000ms、一次失败可能直接停歌，**不适合照搬B快速可靠离座**。上传处理直接在回调向SD写入，不能据此宣称D054并发不中断。README标CC-BY-NC-SA徽章、未见根目录独立LICENSE，复制前须审查适用条款 |
| GH-02 | [DeltaBravoCharlie/NFCmusicplayer](https://github.com/DeltaBravoCharlie/NFCmusicplayer)；读取提交`07b76338b1ff3182cd94336f62209e143d36de81` | **已实际确认**MIT LICENSE、PlatformIO、`src/RFID_Manager.cpp`、`MappingStore.cpp`、`Audio_Manager.cpp`、`WebSetupServer.cpp`等；README注明仍为WIP，原理图/BOM待公布；未编译 | **优先软件模块参考**：UID→SD路径、临时文件再重命名与网页设置；RFID使用`PICC_IsNewCardPresent()`，必须核实持续在位重检与离座，不直接复用去抖阈值。原WROVER引脚、TLV320 DAC及浏览器配置不可直接套到S3 |
| GH-03 | [mhier/LauraBox](https://github.com/mhier/LauraBox)；读取提交`d5a38651540be0f8bf845375e812ba1b64feade0` | **已实际确认**Arduino固件、KiCad原理图/PCB与Gerber、外壳文件、根目录GPL-3.0 LICENSE；未编译/制造 | **驻留型实物交互对照**：RC522、SD MP3、PCM5102+PAM8403立体声、电池与取走暂停再放恢复；**与我们B退出清空/下次从头不同**，不可照搬会话行为。Wi-Fi下载经验可参考，D054并发需另测 |
| GH-04 | [Schop/esp32-rfid-jukebox](https://github.com/Schop/esp32-rfid-jukebox)；读取提交`4e314ae1b1764907f1f7b8d7845c2605bc25becd` | 已确认MIT LICENSE、PlatformIO、`src/main.cpp`和`data/index.html`存在，网页API/播放列表为README所述；未编译 | 低成本网页/播放器指令参考；音频实际为DFPlayer Mini串口、不是本项目I2S双声道，优先级低于GH-01/GH-02 |

**优先级**：先审GH-01的完整工程结构与Web/文件操作，GH-02的身份映射/模块分层，OSH-01/OSH-02的本地相近实体形式；B可靠离座对照GH-03/OSH-03，注意绝不直接继承其取走规则。OSH-05/OSH-06与GH-04留备查，不再无目的扩大候选。现有PN7160 MINI与RC522皆非正式器件，须按板型、预算和B离座验证选；识别方案选择与软件参考源选择是两项不同决策。

**发布与许可控制**：GPL/CERN硬件许可、项目所附的“禁止转载”、平台复刻与非商业说明，以及GH-01的许可徽章需要区分；即使是MIT来源也要保留原作者版权及许可声明。未经源文件许可与范围核查，不复制源代码、图片、EDA、第三方音频/模型到公开分支；先仅记录上述事实和链接。下一步在确切版本、授权范围与依赖确定后才选择“借鉴接口思想”或“引入可再发布源码”，均须在采用记录登记源提交及改动。

## 后续采用记录

每次真正采用组件、技能或素材时追加：

- 名称、作用与采用日期；
- 作者与源仓库/原始链接；
- 采用分支、提交、版本或文件发布信息；
- 公开来源链接与仓库内目标相对路径；
- 许可证及素材单独声明；
- 必要依赖、本地修改和实际验证结果。

这些字段用于追溯实际采用的材料。更新源仓库后按本项目需要同步，并保留项目改动。
