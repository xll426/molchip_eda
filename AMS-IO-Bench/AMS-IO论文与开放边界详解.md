# AMS-IO-Bench / AMS-IO-Agent：论文、流程与开放边界详解

> 论文：*AMS-IO-Bench and AMS-IO-Agent: Benchmarking and Structured Reasoning for Analog and Mixed-Signal Integrated Circuit Input/Output Design*  
> 会议：AAAI-26  
> DOI：<https://doi.org/10.1609/aaai.v40i2.37134>  
> 论文原文：[AAAI26_AMS-IO-Bench_and_AMS-IO-Agent.pdf](./AAAI26_AMS-IO-Bench_and_AMS-IO-Agent.pdf)  
> Benchmark：<https://github.com/Arcadia-1/AMS-IO-Bench>  
> Agent：<https://github.com/Arcadia-1/AMS-IO-Agent>  
> 本地核验日期：2026-08-02

---

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ P1 任务定义                                                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ Input    │ 自然语言 I/O ring 规格、pad location list、工艺节点（28/180 nm）、│
│          │ library/cell/view 名称、电源域与信号顺序约束                    │
├──────────┼────────────────────────────────────────────────────────────────┤
│ Output   │ Intent Graph（JSON）、Virtuoso 原理图/版图 SKILL、Calibre      │
│          │ DRC/LVS 脚本、可编辑 OA cellview、DRC+LVS 验证报告              │
├──────────┼────────────────────────────────────────────────────────────────┤
│ Supervision │ IG 语义校验、VLM shape score、Calibre DRC/LVS pass/fallback  │
├──────────┼────────────────────────────────────────────────────────────────┤
│ Why-hard │ AMS I/O 环涉及模拟/数字/时钟/参考/偏置信号隔离、多电压域、ESD  │
│          │ 规则、封装 bonding 顺序、定制 pad cell 上下文依赖，且依赖        │
│          │ Virtuoso/Calibre/PDK/pad library 等商业/NDA 资产                │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 1. 先给结论

这项工作值得分享，但应把它定义成“**工业 AMS 版图自动化的前沿案例与开放边界分析**”，而不是“本地已经完整复现的开源模型”。

它的研究价值来自三点：

1. 任务不是常见的文字到 RTL，而是把 AMS I/O 规划转成 Virtuoso 原理图和版图，并以 DRC、LVS 作为闭环反馈。
2. LLM 不直接凭空输出几何图形，而是先生成结构化 Intent Graph，再由确定性 adaptor 计算坐标并生成 SKILL/csh 脚本。
3. 论文报告了真实 28 nm 流片案例：人完成 AMS core，Agent 完成 48-pad I/O ring，最终 DRC/LVS 通过并在硅后验证正确。

但本地只有 benchmark 文本，缺少可公开复现完整论文实验所需的商业 EDA、PDK、pad library、内部知识库及设计服务器环境。Agent 仓库虽可访问，仓库许可证写明 `Proprietary - All rights reserved`，因此不能把”公开可读”写成”开源”。

### 1.1 三个核心概念的通俗理解（装修房子类比）

论文的三个核心组件——**设计意图结构化、意图图适配器、领域知识库**——如果缺乏电路背景会比较抽象。下面用一个完全不涉及电路的「装修房子」场景来类比。

#### 场景：你要装修一套 120 平米的房子

---

**① 设计意图结构化 = 把你的模糊要求翻译成施工清单**

你对设计师说：「主卧要大、朝南、带独卫，儿童房靠近主卧，厨房挨着餐厅，客厅要够亮。」

这话太模糊——「够亮」是多大的窗户？「挨着」是多近？设计师翻完规范手册后，给你出了一张**结构化的施工清单**：

```json
{
  “房子”: { “面积”: “120平米”, “楼层”: “5楼” },
  “房间列表”: [
    { “名”: “主卧”,   “朝向”: “南”, “面积”: 18, “带独卫”: true, “窗宽”: 2.4 },
    { “名”: “儿童房”, “朝向”: “南”, “面积”: 12, “紧挨主卧”: true, “窗宽”: 1.5 },
    { “名”: “厨房”,   “位置”: “北”, “面积”: 8,  “紧挨”: “餐厅” },
    { “名”: “客厅”,   “朝向”: “南”, “面积”: 30, “窗宽”: 3.6 }
  ],
  “约束”: [
    { “类型”: “相邻”, “房间A”: “厨房”, “房间B”: “餐厅” },
    { “类型”: “靠近”, “房间A”: “主卧”, “房间B”: “儿童房”, “距离”: “隔壁墙” }
  ]
}
```

**核心转变**：模糊的「想要舒服的家」→ 每间房叫什么、多大、朝哪、跟谁挨着的**清单**。AI 只负责这一步——把话说清楚、写成结构化数据，不负责画施工图。

---

**② 意图图适配器 = 根据清单算出每堵墙的精确坐标**

拿到施工清单后，施工队开始画 CAD 施工图。这不需要任何创造力，全是确定性数学：

```
已知：房子 10m × 12m，主卧 18 平米朝南

计算主卧四面墙：
  南墙：(0, 0) → (4.5, 0)
  东墙：(4.5, 0) → (4.5, 4)
  北墙：(4.5, 4) → (0, 4)
  西墙：(0, 4) → (0, 0)
门的位置：北墙中间 (2.25, 4)，宽 0.9m
窗的位置：南墙中间 (1.05, 0) 到 (3.45, 0)，宽 2.4m

儿童房紧挨主卧 → 儿童房西墙 = 主卧东墙 → 儿童房 3m × 4m
...
```

**关键特性**：18 平米的房间永远是 4m×4.5m，不会第一次算成 4m×4.5m、第二次算成 3.8m×4.7m。同样的清单，永远输出同样的施工图。**LLM 在这一步完全不参与**——适配器是纯 Python 代码，只做数学和格式转换。

适配器还负责**约束消解**：清单写了「厨房挨着餐厅」，适配器检查两者是否真的相邻；清单写了「主卧靠南、儿童房靠北」但儿童房标记了「紧挨主卧」——适配器检测到冲突，把儿童房调整到主卧旁边。

---

**③ 领域知识库 = 装修规范和老师傅经验**

你不能随心所欲地盖房，有规范约束你：

```
📋 装修知识库（类比论文的 6000-token KB）

强制规范（不遵守就验收不过）：
  - 卧室门宽 ≥ 0.8m，卫生间门宽 ≥ 0.7m
  - 燃气灶和冰箱距离 ≥ 0.6m（消防要求）
  - 卫生间防水层淋浴区 ≥ 1.8m 高
  - 插座离地面 ≥ 0.3m（防进水）

经验惯例（老师傅总结，不遵守会翻车）：
  - 厨房和卫生间不要共用一堵墙（水管噪音）
  - 空调外机别挂在卧室外墙（吵）
  - 沙发到电视墙距离 ≈ 屏幕尺寸 × 3

常见踩坑记录：
  - ❌ 插座装在床头正后方 → 床一靠墙就挡住
  - ❌ 卫生间门朝里开 → 里面有人摔倒时门推不开
```

知识库在两个阶段起作用：
- **约束设计师写清单时**：你说「开放式厨房」，知识库说「开放式厨房不能挨着卧室」，设计师在清单里把厨房放到远离卧室的位置。
- **约束施工队画图时**：适配器算出主卧门宽只有 0.6m → 知识库说「卧室门 ≥ 0.8m」→ 自动修正为 0.8m。

---

**三者的关系（一张图总结）**

```text
┌──────────────────────────────────────────────────────────────┐
│                    领域知识库 (KB)                            │
│  器件选型、隔离规则、间距规范、命名惯例……                      │
│  约 6000 tokens，直接放入 LLM 上下文                          │
└────────────┬────────────────────────────┬────────────────────┘
             │ 约束 LLM 输出              │ 约束适配器行为
             ▼                            ▼
┌────────────────────────┐    ┌────────────────────────────────┐
│  设计意图结构化         │    │  意图图适配器                   │
│                        │    │                                │
│  自然语言 ──LLM──► JSON │───►│  JSON ──Python──► SKILL 脚本   │
│                        │    │               ──► Calibre 脚本  │
│  “左边3个模拟pad”      │    │               ──► 坐标/旋转角   │
│       ↓                │    │                                │
│  {side:”left”,         │    │  约束求解 + 几何计算 + 脚本生成  │
│   type:”analog_io”,    │    │  (确定性代码，LLM不参与)         │
│   domain:”analog”}     │    │                                │
└────────────────────────┘    └────────────────────────────────┘
     LLM 负责（语义理解）          确定性代码负责（几何计算）
```

| 概念 | 技术定义 | 通俗类比 |
|---|---|---|
| **设计意图结构化** | 将自然语言需求转为结构化 JSON 图，显式表示器件配置、空间关系和电气连接 | 设计师听你描述需求，翻完规范手册后给你出一张装修清单 |
| **意图图适配器** | 解析 JSON 图以求解约束、执行几何计算并导出实现参数 | 施工队拿到清单画 CAD 施工图——每堵墙的精确坐标 |
| **领域知识库** | 提供设计规则、器件规范和布局惯例，用于约束检查与设计一致性 | 建筑规范 + 老师傅踩过的坑，设计师和施工队都得遵守 |

> **核心思想**：不要让 LLM 直接画版图（它会犯错），而是让 LLM 只做它擅长的事（理解自然语言、整理结构化需求），然后由确定性的 Python 代码去做精确的几何计算和脚本生成，整个过程受团队经验知识库的约束。

## 2. 它解决芯片流程中的哪一步

论文目标是 wirebond 封装 AMS 芯片的外围 I/O ring 自动生成：

```text
自然语言 I/O 需求 / pad location list
        ↓
LLM 理解信号、pad 类型、电源域、顺序和约束
        ↓
结构化 Intent Graph（JSON）
        ↓
确定性 adaptor：约束消解、坐标计算、器件实例化
        ↓
SKILL 脚本 → Cadence Virtuoso schematic/layout
        ↓
csh 脚本 → Siemens Calibre DRC/LVS
        ↓
错误反馈 → 修改 intent / 再执行
        ↓
可编辑的原理图、版图和验证报告
```

这是全芯片外围 I/O 子系统，不是：

- 数字 RTL 生成；
- 模拟核心电路的晶体管尺寸优化；
- 标准单元数字 place-and-route；
- 不经 PDK 和 signoff 工具就直接生成可流片 GDS。

## 3. 为什么 AMS I/O ring 难以只靠传统脚本

数字 I/O 往往能用较固定的规则放置，AMS I/O 却同时受以下约束影响：

- 模拟、数字、时钟、参考和偏置信号具有不同敏感性；
- 多个电压域需要隔离、独立电源和局部 ESD 供电；
- pad 顺序受封装、bonding 和顶层 pinout 限制；
- 不同 pad、filler、corner、isolation cell 有上下文依赖；
- 定制低电容模拟 I/O 等器件不能用统一模板替代；
- 临近流片的 pin-order 改动会牵动大量实例和连线。

论文认为，固定脚本不擅长理解这些项目相关的语义和隐含约束；纯 LLM 又容易生成不可执行或不满足物理规则的脚本。因此系统把语言推理和确定性几何执行分开。

## 4. 核心方法：不是让 LLM 直接画版图

![论文 Figure 3：知识库、Intent Graph、Python adaptor、SKILL 与 Virtuoso 的分层架构](./figures/paper-fig3-agent-architecture.png)

### 4.1 Domain-specific Knowledge Base

知识库约 6k tokens，来自一个专业 AMS 团队 10 余名工程师的培训材料和设计惯例，并由 50 余次成功流片经验验证。内容覆盖：

- 器件选择；
- 版图惯例；
- 电源域与隔离；
- ESD 规则；
- 命名规范；
- 常见设计技巧。

论文没有为此训练专用模型，也没有复杂 RAG；知识库足够小，可直接放入上下文。这里真正起作用的是领域知识的结构化与可复用，而不是新的 Transformer 架构。

### 4.2 Intent Graph

Intent Graph 是自然语言需求和 EDA 脚本之间的中间表示。它把模糊需求整理为机器可检查的对象，例如：

```json
{
  "chip": {"width_um": 1000, "height_um": 1000},
  "ordering": "clockwise",
  "pads_per_side": 12,
  "instances": [
    {
      "name": "VINP",
      "side": "right",
      "type": "custom_analog_io",
      "power_domain": "analog_1"
    }
  ]
}
```

上面只是便于理解的概念例，字段应以 Agent 实际 schema 为准。Intent Graph 的价值是：pad 是否缺失、命名是否合法、电源域是否完整等问题能在进入昂贵 EDA 执行前检查。

### 4.3 Deterministic adaptor

Adaptor 不依赖 LLM 每次重新发明脚本，而是复用确定性工具完成：

- 结构化数据解析；
- 约束解析；
- cell 坐标和方向计算；
- schematic/layout SKILL 生成；
- Calibre DRC/LVS 调用脚本生成。

这是工程上最关键的一层：LLM 负责高层语义，确定性代码负责可重复的几何和 API 翻译。

### 4.4 端到端流程实例：从一句需求到一张版图

下面用一个具体的 4×4 I/O ring 任务，完整展示从输入到输出的每一步，标注每一步**谁在干活**。

#### 第 0 步：准备知识库（一次性工作）

```text
📋 知识库（精简示意，实际约 6000 tokens）

规则1: 模拟 pad 和数字 pad 之间必须插隔离单元
规则2: 时钟 pad 要用带屏蔽的特殊型号（CLK_IO_SHIELDED），不能拿普通数字 pad 凑合
规则3: 芯片四个角必须放 corner cell，不然边缘封环会断开
规则4: 每边相邻 pad 中心间距 ≥ 90µm
规则5: 同一个电源域的 pad 要放在一起，不能东一个西一个
规则6: 空位必须填 filler cell，不能空着（会触发密度 DRC 违规）
规则7: ESD 保护：每个电源域 VDD-VSS 之间必须放置 ESD clamp cell
```

#### 第 1 步：输入——自然语言 + pad location list

```text
【task_001.txt】

Task: Generate IO ring for Cadence Virtuoso.
Technology: 28nm
Chip size: 1.2mm × 1.2mm
4 pads per side, total 16 pads, single ring, clockwise order.

Signals:
  Left side   (top→bottom): VINP, VINN, AVDD, AGND
  Top side    (left→right): CLK, NC_1, NC_2, DVDD
  Right side  (top→bottom): GPIO1, GPIO2, DGND, NC_3
  Bottom side (left→right): VREF, NC_4, NC_5, NC_6

Power domains: analog (3.3V), digital (1.8V)
Library: MyChipLib    Cell name: IO_RING_DEMO
```

这份输入介于纯自然语言和结构化数据之间——列出了每边有什么信号，但很多关键信息缺失：`NC_1`~`NC_6` 是空着还是填什么？CLK 用哪种 cell？模拟域和数字域在左上角交接要不要隔离？

#### 第 2 步：设计意图结构化——LLM 读懂需求，写出 JSON 清单

> **谁干活**：LLM（同时看到 task_001.txt 和知识库）

LLM 对照知识库翻译你的需求，后台推理过程：

```
LLM 思考：
- VINP/VINN/AVDD/AGND → 全是模拟信号 → domain="analog"
- CLK → 查规则2 → type 必须是 clock_io_shielded（不能是普通 digital_io）
- NC_1~NC_6 → 输入写的是 "reserved pins" → 查规则6 → type="filler_cell"
- 上边有 CLK(digital) 和 DVDD(digital)，NC_1/NC_2 分配 digital 域
- 左上角：analog 域(左边) 和 digital 域(上边) 交接 → 查规则1 → 需要隔离单元
- 四角 → 查规则3 → 必须放 corner cell
```

LLM 输出——**Intent Graph**：

```json
{
  "meta": {
    "technology": "28nm", "library": "MyChipLib",
    "cell_name": "IO_RING_DEMO",
    "chip_width_um": 1200, "chip_height_um": 1200,
    "pads_per_side": 4, "ring_type": "single", "ordering": "clockwise"
  },
  "power_domains": [
    { "name": "analog",  "supply": "AVDD", "ground": "AGND", "voltage": 3.3 },
    { "name": "digital", "supply": "DVDD", "ground": "DGND", "voltage": 1.8 }
  ],
  "corners": [
    { "name": "CORNER_TL", "side": "top_left" },
    { "name": "CORNER_TR", "side": "top_right" },
    { "name": "CORNER_BR", "side": "bot_right" },
    { "name": "CORNER_BL", "side": "bot_left" }
  ],
  "instances": [
    { "name": "VINP",  "side": "left",   "idx": 0, "type": "custom_analog_io",  "domain": "analog" },
    { "name": "VINN",  "side": "left",   "idx": 1, "type": "custom_analog_io",  "domain": "analog" },
    { "name": "AVDD",  "side": "left",   "idx": 2, "type": "analog_supply_pad", "domain": "analog" },
    { "name": "AGND",  "side": "left",   "idx": 3, "type": "analog_ground_pad", "domain": "analog" },
    { "name": "CLK",   "side": "top",    "idx": 0, "type": "clock_io_shielded", "domain": "digital" },
    { "name": "NC_1",  "side": "top",    "idx": 1, "type": "filler_cell",       "domain": "digital" },
    { "name": "NC_2",  "side": "top",    "idx": 2, "type": "filler_cell",       "domain": "digital" },
    { "name": "DVDD",  "side": "top",    "idx": 3, "type": "digital_supply_pad","domain": "digital" },
    { "name": "GPIO1", "side": "right",  "idx": 0, "type": "digital_io",        "domain": "digital" },
    { "name": "GPIO2", "side": "right",  "idx": 1, "type": "digital_io",        "domain": "digital" },
    { "name": "DGND",  "side": "right",  "idx": 2, "type": "digital_ground_pad","domain": "digital" },
    { "name": "NC_3",  "side": "right",  "idx": 3, "type": "filler_cell",       "domain": "digital" },
    { "name": "VREF",  "side": "bottom", "idx": 0, "type": "reference_pad",     "domain": "analog" },
    { "name": "NC_4",  "side": "bottom", "idx": 1, "type": "filler_cell",       "domain": "analog" },
    { "name": "NC_5",  "side": "bottom", "idx": 2, "type": "filler_cell",       "domain": "analog" },
    { "name": "NC_6",  "side": "bottom", "idx": 3, "type": "filler_cell",       "domain": "analog" }
  ],
  "isolation": [
    { "between_domains": ["analog", "digital"],
      "at_boundaries": ["top_left"],
      "action": "insert_isolation_cell" }
  ]
}
```

| 输入里模糊的东西 | Intent Graph 里的明确结果 | 起作用的 KB 规则 |
|---|---|---|
| `NC_1` ~ `NC_6` 没说是啥 | 全部标记为 `filler_cell` | 规则6：空位必须填 filler |
| `CLK` 没指定型号 | `type: "clock_io_shielded"` | 规则2：时钟用屏蔽型 |
| 没说 corner 怎么处理 | 显式加了 4 个 corner cell | 规则3：四角必须放 corner |
| 没提模拟/数字交接 | `isolation` 标记了需要隔离的角 | 规则1：不同域交接要隔离 |

#### 第 3 步：语义验证——检查清单有没有低级错误

> **谁干活**：确定性 Python 脚本（不靠 LLM）

在进入昂贵的 EDA 执行之前，先花几毫秒验证：

```python
# 自动验证规则（示例）
assert all(inst["domain"] in ["analog", "digital"] for inst in graph["instances"])
assert sum(1 for inst in graph["instances"] if inst["side"] == "left") == 4
assert is_valid_cell_type("clock_io_shielded")  # 库里有这个 cell
assert graph["power_domains"][0]["supply"] and graph["power_domains"][0]["ground"]
```

通过后才放行进入适配器；不通过则打回让 LLM 重写。

#### 第 4 步：适配器——把 JSON 算成精确坐标

> **谁干活**：确定性 Python 代码（LLM 完全退场）

```
子步骤 4a — 约束消解：
  isolation 标记了 "top_left" → 在 AGND(analog左) 和 CLK(digital上) 之间插入 ISO_TL 隔离单元
  "bot_left" 处 VINP(analog左) 和 VREF(analog下) 都是 analog → 不需要隔离

子步骤 4b — 几何计算：
  pitch = 1200 / 4 = 300µm    offset = 150µm
  left 边 (x=0, y从大到小):   VINP(0,1050), VINN(0,750), AVDD(0,450), AGND(0,150)
  top 边 (y=1200, x从小到大): CLK(150,1200), NC_1(450,1200), NC_2(750,1200), DVDD(1050,1200)
  right 边 (x=1200):          GPIO1(1200,1050), GPIO2(1200,750), DGND(1200,450), NC_3(1200,150)
  bottom 边 (y=0):            VREF(150,0), NC_4(450,0), NC_5(750,0), NC_6(1050,0)
  四角:                       CORNER_TL(0,1200), CORNER_TR(1200,1200), CORNER_BR(1200,0), CORNER_BL(0,0)

子步骤 4c — 器件 cell 名映射（查知识库）：
  "custom_analog_io"   → cell "ANA_IO_LC"
  "clock_io_shielded"  → cell "CLK_IO_SHIELDED"
  "digital_io"         → cell "DIG_IO_STD"
  "filler_cell"        → cell "FILLER_STD_28nm"
  "isolation_cell"     → cell "ISO_DEEP_NWELL"
  "corner_cell"        → cell "CORNER_WB_STD"
  ...
```

#### 第 5 步：输出 SKILL 脚本 → Cadence Virtuoso 画版图

> **谁干活**：适配器继续（把坐标翻译成 SKILL 语句）

```lisp
;; 适配器自动生成的 SKILL 脚本（节选）

;; 放置 VINP 模拟输入 pad（左边第 0 个）
schCreateInst(
  ?libName  "MyChipLib"    ?cellName "ANA_IO_LC"
  ?viewName "layout"       ?instName "VINP"
  ?xy       list(0.0 1050.0)
  ?orient   "R90"
)

;; 放置时钟 pad（上边第 0 个）——用的是 CLK_IO_SHIELDED
schCreateInst(
  ?libName  "MyChipLib"    ?cellName "CLK_IO_SHIELDED"
  ?viewName "layout"       ?instName "CLK"
  ?xy       list(150.0 1200.0)
  ?orient   "R0"
)

;; 放置隔离单元（左上角，模拟和数字域之间）
schCreateInst(
  ?libName  "MyChipLib"    ?cellName "ISO_DEEP_NWELL"
  ?viewName "layout"       ?instName "ISO_TL"
  ?xy       list(50.0 1150.0)
  ?orient   "R0"
)
;; ... 其余 14 个 instance 同理 ...
```

#### 第 6 步：输出 Calibre 脚本 + 运行 DRC/LVS

> **谁干活**：适配器生成 .csh 脚本，Calibre 执行检查

```csh
#!/bin/csh
# DRC 检查：间距、宽度、包围等物理规则
calibre -drc -hier -hyper \
  -rules $PDK_DIR/drc/drc_rules_28nm.cal \
  -topcell IO_RING_DEMO \
  -gds   ./layout/IO_RING_DEMO.gds

# LVS 检查：layout 和 schematic 是否一致
calibre -lvs -hier -hyper \
  -rules $PDK_DIR/lvs/lvs_rules_28nm.cal \
  -spice ./netlist/IO_RING_DEMO.sp \
  -gds   ./layout/IO_RING_DEMO.gds
```

#### 第 7 步：错误反馈 → 修复 → 重新生成

> **谁干活**：Agent 分析错误，修改 Intent Graph 后重新跑步骤 3→6

```text
第一轮结果：
  ❌ DRC: M1.D.3 - Metal spacing violation at (452, 1198) — NC_1 filler 内部金属冲突
  ❌ DRC: NW.S.2 - N-well spacing violation at (0, 1202)   — 隔离单元和 corner cell 间距不足
  ⚠  LVS: layout 有 17 个 instance，schematic 只有 16 个  — 多了一个

Agent 修复：
  错误1 → 查 KB: "密集 filler 内部金属可能冲突" → NC_1 从 filler_cell 改为 spacer_cell
  错误2 → 适配器修正: corner cell 外移，ISO_TL 偏移 50µm
  错误3 → 适配器修正: 隔离单元去重逻辑

第二轮结果：
  ✅ DRC: 0 violations
  ✅ LVS: schematic and layout match — 通过！
```

#### 完整流程图（标注每一步谁在干活）

```text
┌─────────────────────────────────────────────────────────────────┐
│  你写的 task_001.txt                                             │
│  "4 pads per side, VINP/VINN/AVDD/AGND on left..."              │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  步骤 2: 设计意图结构化                                          │
│  ▸ 谁干活: LLM + 知识库                                         │
│  ▸ 干了啥: 把模糊 NL 翻译成结构化 JSON                           │
│  ▸ 例子: "NC_1" → type:"filler_cell", domain:"digital"          │
│  ▸ 输出: Intent Graph (JSON)                                    │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  步骤 3: 语义校验                                                │
│  ▸ 谁干活: 确定性 Python（不靠 LLM）                              │
│  ▸ 干了啥: pad 数、命名合法性、电源域完整性、type 是否存在        │
│  ▸ 不通过 → 打回 LLM 重写 Intent Graph                          │
└────────────────────────────┬────────────────────────────────────┘
                             │ ✅ 通过
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  步骤 4+5+6: 适配器 — 约束消解 → 坐标计算 → 脚本生成             │
│  ▸ 谁干活: 确定性 Python（LLM 完全退场）                          │
│  ▸ 4a. 约束消解: 检测域边界 → 插入隔离单元                       │
│  ▸ 4b. 坐标计算: VINP → (0, 1050), rot=90                       │
│  ▸ 4c. cell 映射: "custom_analog_io" → "ANA_IO_LC"              │
│  ▸ 5.  SKILL 脚本: schCreateInst(?xy list(0.0 1050.0) ...)     │
│  ▸ 6.  Calibre 脚本: calibre -drc -topcell IO_RING_DEMO ...     │
└────────────────────────────┬────────────────────────────────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
              ▼                             ▼
        ✅ DRC+LVS 通过               ❌ 有错误
              │                             │
              ▼                             ▼
         交付！                    ┌─────────────────────────────┐
                                  │  步骤 7: 错误反馈修复         │
                                  │  ▸ Agent 分析 DRC/LVS 报告    │
                                  │  ▸ 修改 Intent Graph          │
                                  │  ▸ 重新跑步骤 3→6             │
                                  │  ▸ 循环直到通过               │
                                  └─────────────────────────────┘
```

#### 一句话总结每一步的分工

| 步骤 | 谁干活 | 职责 |
|---|---|---|
| 意图结构化 | **LLM** | 语义推理——"你要什么？"写成 JSON |
| 语义验证 | **确定性代码** | 检查 JSON 有无逻辑错误 |
| 约束消解 | **确定性代码** | 检测域边界、插入隔离单元 |
| 坐标计算 | **确定性代码** | 纯数学——pad 间距、位置、旋转 |
| SKILL 生成 | **确定性代码** | JSON → Virtuoso 可执行的 .il 脚本 |
| Calibre 验证 | **Calibre 工具** | 物理规则检查 (DRC) + 一致性检查 (LVS) |
| 错误修复 | **Agent (LLM)** | 分析 DRC/LVS 报告 → 改 Intent Graph → 重跑 |

> **核心逻辑**：LLM 负责「你要什么？」（语义 → JSON），适配器负责「怎么画出来？」（JSON → 坐标 → SKILL），知识库负责「规矩是什么？」（约束两者），DRC/LVS 负责「画对了没？」（最终裁判）。LLM 绝不直接画版图——它的「创造力」在几何精度面前就是 bug。

## 5. Benchmark：论文版本和当前仓库版本必须分开

### 5.1 论文中的 30 题

论文 benchmark 来源于过去 5 年 10 个真实 tapeout 项目，经简化、增强和变换构造 30 题：

| 难度 | 数量 | 主要特征 |
|---|---:|---|
| Simple | 10 | 小尺寸、单信号域 |
| Medium | 10 | 约 1 mm × 1 mm、单排 I/O、多电源域 |
| Hard | 10 | 大尺寸、双排/局部双排、定制 cell、复杂局部 ESD 供电 |

每题提供结构化 pad location 信息，包括 signal assignment、power domain 和 routing hint。

### 5.2 本地公开仓库的 60 题

当前本地 `AMS-IO-Bench` README 标记为 v1.0（2025-11-22），包含 60 个文本任务：

```text
28nm_wirebonding/   30 cases
180nm_wirebonding/  30 cases
```

任务覆盖 3×3 到 18×18、单/双 ring、数字/模拟/混合信号和多电压域。它显然比论文表格中的 30 题多，但公开 README 没有提供足够依据证明“这 60 题就是论文 30 题的逐一双工艺映射”。因此报告时应写：

> 论文评测使用 30 题；当前公开仓库版本包含 60 个 prompt 文件，属于后续或扩展发布，不能直接把仓库数量代入论文结果。

## 6. 输入和输出到底是什么

本地任务输入是自然语言/结构化混合文本，例如：

```text
Task: Generate IO ring schematic and layout design for Cadence Virtuoso.
10 pads per side. Double ring. Counterclockwise...
Technology: 180nm
Library: LLM_Layout_Design
Cell name: IO_RING_10x10...
```

完整系统的中间与最终输出应包括：

1. 规范化 Intent Graph；
2. pad/corner/filler/isolation 实例和坐标；
3. Virtuoso schematic SKILL；
4. Virtuoso layout SKILL；
5. Calibre 运行脚本；
6. DRC/LVS 报告；
7. 可编辑的 OA library/cell/view 设计数据。

只生成 JSON 或 SKILL 文本，不等于完成论文任务。论文的总体成功条件是布局同时通过 DRC 和 LVS。

## 7. 论文评价指标

| 阶段 | 指标 | 含义 |
|---|---|---|
| 意图理解 | IG pass rate | pad 命名、类型和属性是否正确完整 |
| 形态 | Shape score | VLM 判断与参考的结构/拓扑形态是否对齐 |
| 物理规则 | DRC pass rate | 是否通过 foundry spacing/width/enclosure 等规则 |
| 电气一致性 | LVS pass rate | layout 与 schematic 是否无开路、短路和器件不匹配 |
| 总体 | DRC+LVS pass rate | 是否同时通过两类 signoff 检查 |

其中 Shape 是辅助指标，DRC+LVS 才是论文用来代表接近 production-ready 的总体指标。即使 DRC+LVS clean，也仍不能代替完整的 ESD、可靠性、电源完整性和封装协同审查。

## 8. 论文主结果：应怎样准确引用

![论文 Table 3 / IV：主结果与 KB、Intent Graph、adaptor 消融](./figures/paper-table3-table4-results.png)

论文 Table 3 的 30 题结果如下：

| 方法 | IG | Shape | DRC | LVS | DRC+LVS | 时间/题 | Tokens |
|---|---:|---:|---:|---:|---:|---:|---:|
| Human | 100% | 100% | 100% | 100% | 100% | 约 480 min | — |
| Vanilla GPT-4o | 0% | 0% | 0% | 0% | 0% | 0.2 min | 1k |
| Agent + GPT-4o | 100% | 100% | 76.67% | 66.67% | 63.33% | 4.1 min | 160k |
| Agent + Claude-3.7 | 100% | 100% | 93.33% | 76.67% | 76.67% | 4.2 min | 96k |
| Agent + DeepSeek-V3 | 100% | 100% | 93.33% | 76.67% | 76.67% | 5.1 min | 105k |

准确说法是：Claude-3.7 和 DeepSeek-V3 配合完整 Agent 时达到 23/30 的 DRC+LVS pass；不是“所有题都流片成功”，也不是“LLM 单独达到 76.67%”。

按难度拆分的 DRC+LVS 结果：

| 模型 | Simple | Medium | Hard |
|---|---:|---:|---:|
| GPT-4o | 10/10 | 7/10 | 2/10 |
| Claude-3.7 | 10/10 | 9/10 | 4/10 |
| DeepSeek-V3 | 10/10 | 10/10 | 3/10 |

这说明难点主要仍集中在复杂、定制化和多约束场景。

## 9. 消融实验告诉我们的核心结论

DeepSeek-V3 消融中，只有 KB、Intent Graph 和 adaptor 三者齐全时才取得：

- IG 100%；
- Shape 100%；
- DRC 93.33%；
- LVS 76.67%；
- DRC+LVS 76.67%。

仅让 LLM 直接写 SKILL，或者让它生成 Python 再写 SKILL，都没有得到 DRC+LVS 通过；只有 Intent Graph 而无 adaptor 也无法获得有效版图。可分享的核心不是“多 Agent 越多越好”，而是：

> 高风险 EDA 自动化需要受约束的中间表示、确定性执行器和真实工具反馈，LLM 只承担适合它的语义推理部分。

这与 ChipSeek 的闭环思想相通，但反馈对象从 RTL 编译/仿真扩展到了商业 AMS layout signoff。

## 10. 真实 tapeout 案例的范围

![论文 Figure 5：48-pad I/O ring 与人工 AMS core 的 28 nm tapeout 分工](./figures/paper-fig5-tapeout.png)

论文案例为：

- 28 nm CMOS；
- 1 mm × 1 mm wirebond mixed-signal IC；
- 48 个 I/O pads，每边 12 个；
- 人类工程师完成内部 AMS core；
- Agent 完成外围 I/O ring；
- 中途发生较大的 pin-order 变更，Agent 在数分钟内重生成；
- 最终设计通过 DRC/LVS、完成制造，silicon measurement 验证功能正确。

所以正确说法是“Agent 生成的 I/O ring 被用于一颗真实芯片”，而不是“Agent 独立完成整颗 AMS 芯片”。

## 11. 本地目前能核验什么，不能核验什么

### 已核验

- 论文 PDF 完整可读，共 8 页；
- 本地 benchmark 两个工艺目录各 30 题，共 60 个 prompt；
- prompt 包含 pad 数、ring 形式、顺序、信号、电源域和目标 library/cell/view；
- 论文数据量、主结果、消融和 tapeout 描述已逐项对原文核对。

### 未完成且当前环境不能声称完成

- 没有在本地 Virtuoso 生成 schematic/layout；
- 没有 Calibre DRC/LVS 报告；
- 没有对应 28/180 nm PDK、pad library 和 rule deck；
- 没有论文团队内部 6k-token 知识库的等价版本；
- 没有复现论文 30 题上的 76.67%；
- 没有复现 tapeout。

因此这个目录的状态应标为“**论文与公开 benchmark 已归档；完整工业流程未复现**”。

## 12. 开放性和许可证边界

| 资产 | 当前状态 | 使用判断 |
|---|---|---|
| 论文 | AAAI 官方可下载 | 可阅读、引用 |
| AMS-IO-Bench | GitHub 可访问，但根目录未见独立 LICENSE | 公开可读；复用/再分发前需向作者确认 |
| AMS-IO-Agent | GitHub 可访问，许可证为 proprietary/all rights reserved | 不能称为开源，不能默认允许修改或再分发 |
| Virtuoso / Calibre | 商业软件 | 需合法许可证 |
| PDK / rule deck / pad library | 通常受 NDA/许可约束 | 不应上传到公开仓库 |
| 团队知识库 | 论文描述但不等于完整公开 | 不能假设已获得 |

“代码在 GitHub 上”只说明可访问，不自动等于 OSI 意义上的 open source。

## 13. 如果我们要做可公开复现的后续研究

可以拆成三层，逐步建立可信证据：

### 第一层：纯开放 intent benchmark

- 把 60 个 prompt 解析成统一 JSON schema；
- 检查 pad 数、顺序、唯一性、电源域归属和 ring 拓扑；
- 建立 deterministic validator；
- 报告结构正确率和错误类别。

这一层不需要商业 EDA，但只能证明“理解需求”，不能证明 layout 可制造。

### 第二层：开放几何代理

- 用 KLayout/Python 构造抽象 pad-cell geometry；
- 自定义开放 spacing/enclosure/connectivity 规则；
- 输出 GDS/OASIS 和可检查的 netlist；
- 用 KLayout DRC + Netgen/自建 connectivity checker 做闭环。

结果应称为“开放代理环境验证”，不能和论文 Calibre/PDK signoff 的 76.67% 横向等同。

### 第三层：有授权的工业复现

- 使用合法 Virtuoso/Calibre/PDK/pad library；
- 固定 tool version、rule deck、agent prompt 和模型版本；
- 逐题保存 Intent Graph、SKILL、DRC/LVS log、人工修改量、运行时间和 token；
- 对失败类型做约束理解、geometry、DRC、LVS 分层归因。

## 14. 组会建议

建议把这篇放在 MAGE、PICBench、DeepGate2 之后作为“边界与趋势”案例，用 8–12 分钟讲：

1. 为什么 AMS I/O 比 RTL 更依赖工程知识与商业工具；
2. `自然语言 → Intent Graph → adaptor → Virtuoso → Calibre` 的结构；
3. 23/30 DRC+LVS 与消融实验；
4. 48-pad 28 nm tapeout 的真实范围；
5. 为什么公开 benchmark、公开可读代码和完整可复现之间仍有巨大鸿沟。

这比只展示“LLM 能画版图”更有研究价值，也能自然引出下一步：为 EDA Agent 设计可验证的中间表示和开放代理环境。

## 15. 一页式结论

```text
贡献：首个面向 wirebond AMS I/O ring 的 benchmark + 结构化 Agent
核心：6k-token KB + Intent Graph + deterministic adaptor + DRC/LVS feedback
论文集：10 个真实 tapeout → 30 cases（10 simple / 10 medium / 10 hard）
最佳：23/30 DRC+LVS，约 4.2–5.1 min/题
案例：28 nm、1×1 mm、48 pads；Agent 做 I/O ring，人做 AMS core
本地：60 个公开 prompt 已归档，论文已核对；未运行商业 EDA/signoff
边界：Agent 非开源许可；PDK/库/工具/知识库不完整公开
分享定位：工业前沿与可复现性边界，不是本地完整复现

---

## P7 组件一句话角色

| 组件 | 一句话角色 | 通俗类比（详见 §1.1） |
|---|---|---|
| Domain-specific Knowledge Base | 把 10 余年 AMS 团队设计经验压缩为 6k-token 上下文，约束 LLM 输出到工业可接受范围 | 建筑规范 + 老师傅踩坑手册 |
| Intent Graph | 自然语言需求与 EDA 脚本之间的结构化中间表示，可在进入昂贵工具执行前做语义校验 | 设计师出的装修清单（JSON 格式） |
| Deterministic Adaptor | 把 Intent Graph 解析为实例、坐标、SKILL 和 Calibre 脚本，负责可重复的几何与 API 翻译 | 施工队按清单画 CAD 施工图（每堵墙的坐标） |
| LLM/Agent | 在 KB 和 Intent Graph 约束下承担高层语义推理，不直接生成几何图形 | 设计师：理解需求、写清单（不管施工） |
| AMS-IO-Bench | 来自 10 个真实 tapeout 的 30/60 题文本任务集，用于评测意图理解到 signoff 的完整链路 | 装修验收标准测试题集 |
| DRC/LVS feedback | 以 Calibre signoff 结果驱动 Agent 闭环修复，是判断 production-ready 的最终信号 | 监理公司验房报告，不合格就打回重做 |

> 端到端流程实例（从一句需求到 DRC/LVS 通过的全过程）详见 §4.4。

---

## 讨论问题

1. 为什么 AMS-IO-Agent 不直接让 LLM 输出 SKILL 版图脚本，而必须先经过 Intent Graph 和确定性 adaptor？
2. 论文主实验使用 30 题而公开仓库有 60 题，这一口径差异会如何影响“Agent + Claude-3.7 达到 76.67% DRC+LVS”的解读？
3. 在缺少 Virtuoso、Calibre、PDK 和 pad library 的开放环境下，如何建立一个可公开审计的 AMS I/O 代理评价流程？
```
