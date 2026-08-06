# PICBench 论文与代码复现详解

> 面向组会分享：从自然语言需求出发，解释 PICBench 如何生成 JSON 网表、用 SAX 做光子仿真、用 Golden Response 判分，并说明本地 24 题的复现结果与 GRPO 改造路径。

---

## 1. 任务定位：这是拓扑综合 benchmark，不是版图生成

```text
┌─────────────────────────────────────────────────────────────────────┐
│  PICBench = 光子集成电路拓扑综合 benchmark                          │
│  自然语言需求 → LLM → 器件级 JSON Netlist → SAX 仿真 → 功能判定   │
│  不是版图生成 / 不是直接预测频响 / 不是端到端流片工具链             │
└─────────────────────────────────────────────────────────────────────┘
```

PICBench 要求大语言模型根据自然语言电路规格，生成器件级 JSON 网表，再用 SAX 计算光信号的传播与干涉，最后和预存的 Golden Response 比较，判断功能是否正确。

~~~mermaid
flowchart LR
    A["自然语言设计需求"] --> B["LLM 理解功能与拓扑"]
    B --> C["生成 JSON Netlist"]
    C --> D["SAX 构建光子电路"]
    D --> E["计算输入—输出传输响应"]
    E --> F["Evaluator 与 Golden Response 比较"]
    F --> G["成功或失败"]
~~~

---

## 2. 为什么电子电路的经验不能直接搬过来？

```text
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  为什么电子电路的经验不能直接搬过来？                            ┃
┃                                                                  ┃
┃  光子电路处理的是复光场 E = A·e^(jφ)。                           ┃
┃  两条支路合并时，光场直接相加：E_out = E_1 + E_2。               ┃
┃  但功率 P ∝ |E_out|²，因此同相增强、反相相消。                   ┃
┃  结论：拓扑“连通”≠ 功能正确，必须用 SAX 执行物理仿真。           ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

传统电子电路处理电压、电流；光子电路处理的是光场的振幅与相位。两份网表即使器件数量相同，只要支路长度、连接端口或相移不同，最终传输曲线就可能完全不同。这正是 PICBench 必须使用 SAX 仿真的根本原因。

---

## 3. 在 EDA 流程中的位置

~~~mermaid
flowchart TD
    A["功能需求"] --> B["系统与架构设计"]
    B --> C["电路设计"]
    C --> D["Netlist 网表"]
    D --> E["电路仿真"]
    E --> F["版图设计"]
    F --> G["DRC / LVS / 工艺验证"]
    G --> H["流片制造"]
~~~

PICBench 覆盖“功能需求 → 器件选择 → 拓扑设计 → 网表 → 功能仿真”这一段，尚未覆盖真实版图、波导布局布线、PDK 工艺规则、制造偏差、热串扰和封装 sign-off。

| 传统电子 EDA | PICBench 中的对应物 |
|---|---|
| 自然语言/系统规格 | PIC 自然语言设计题 |
| 原理图或 RTL | JSON Netlist |
| 标准单元/器件库 | `devices.py` |
| 网表展开 | `sax.circuit()` |
| SPICE/功能仿真 | SAX 散射参数仿真 |
| Testbench | Golden Response Evaluator |
| 综合或设计 Agent | LLM |

因此更准确的研究定位是：**光子 EDA 前端 + 功能级验证环境**。

---

## 4. 本机运行结果

![论文 Table III / IV：不同模型、Restrictions 和 Error Feedback 下的 Syntax/Function Pass@k](./figures/paper-table3-table4-results.png)

> 上图是论文第 6 页结果；下面 `24/24`、`10/24` 是本地用 `gpt-5.4` 独立运行，二者不要混写。

**[本地结果：gpt-5.4 / 24 题]**

- **syntax Pass@1 = 1.0**：24/24 至少生成过一个能进入功能比较阶段的 Netlist。
- **functional Pass@1 = 0.4167**：10/24 功能正确。
- 日志文件：`PICBench/log_gpt-5.4_pass1_res1.json`。
- 共保存 33 个 Netlist：通常初始通过的题保存 1 个，失败并反馈的题保存 2 个。

功能通过的 10 题：

- Benes_4x4
- Benes_8x8
- Crossbar_4x4
- Direct modulator
- MZM
- Optical hybrid
- Spanke_4x4
- Spanke_8x8
- Spanke–Benes_4x4
- WDM_demux

这说明 gpt-5.4 在结构化生成上已较稳定，但精确的光子拓扑综合仍有限，真正的瓶颈是**相位、端口方向与物理响应**，而不仅是 JSON 格式。

---

## 5. 全流程 ASCII 全景

```text
┌──────────────┐   ┌─────┐   ┌──────────────┐   ┌──────┐   ┌──────────────┐
│ 自然语言需求 │ → │ LLM │ → │ JSON Netlist │ → │ SAX  │ → │ Golden 比较  │
└──────────────┘   └─────┘   └──────────────┘   └──────┘   └──────────────┘
       ↑                                                       │
       └──────────── 错误反馈重试（max_iterations=1）───────────┘
```

![论文 Figure 1：PICBench 的生成、SAX 仿真、Golden Response 和错误反馈流程](./figures/paper-fig1-framework.png)

~~~mermaid
flowchart TD
    A["命令行参数"] --> B["读取 24 个自然语言问题"]
    B --> C["构造 Prompt"]
    C --> C1["System Prompt"]
    C --> C2["Restrictions"]
    C --> C3["固定 MZI One-shot 示例"]
    C --> C4["当前题目"]
    C1 --> D["Simplaj Responses API / gpt-5.4"]
    C2 --> D
    C3 --> D
    C4 --> D
    D --> E["模型逐 Token 生成回答"]
    E --> F["提取 result 中的 JSON"]
    F --> G{"JSON 能否解析？"}
    G -- 否 --> G1["格式错误反馈"]
    G -- 是 --> H{"模型名称是否合法？"}
    H -- 否 --> H1["wrong model names"]
    H -- 是 --> I{"SAX 能否构建电路？"}
    I -- 否 --> I1["实例、连接或端口错误"]
    I -- 是 --> J["扫描 1000 个波长点"]
    J --> K["计算每个 I→O 的 |Sio|²"]
    K --> L{"曲线数量正确？"}
    L -- 否 --> L1["wrong ports number"]
    L -- 是 --> M{"与 GT 曲线相同？"}
    M -- 是 --> N["functional check passed"]
    M -- 否 --> O["functional error"]
    G1 --> P{"还有反馈次数？"}
    H1 --> P
    I1 --> P
    L1 --> P
    O --> P
    P -- 是 --> Q["错误文本加入同一对话"]
    Q --> D
    P -- 否 --> R["记录失败"]
    N --> S["记录成功"]
    R --> T["计算 Pass@k 并保存日志"]
    S --> T
~~~

---

## 6. 程序入口、参数与完整调用链

入口位于 `PICBench/PICBench/gen_data.py`。本次关键参数：

| 参数 | 含义 |
|---|---|
| `--path testcases` | 指定测试集目录 |
| `--restriction_label True` | 将 `restrictions.txt` 加入 System Prompt |
| `--max_iterations 1` | 初始失败后最多反馈一次 |
| `--total_samples 1` | 每题只有一个独立 Sample |
| `--pass_k 1` | 计算 Pass@1 |
| `--model gpt-5.4` | 发送给 Simplaj 的模型 ID |

一个 Sample 内可包含初始生成与反馈重试：

```text
Sample 0
├── Attempt 0：初始生成
└── Attempt 1：错误反馈后的修正生成
```

### 代码调用链

| 阶段 | 代码位置 | 关键对象/行为 |
|---|---|---|
| 命令行入口 | `PICBench/gen_data.py::PICBench()` | 读取参数、选 provider、列举题目并进入批量生成 |
| 组织一次 sample | `gen_result_feedback_passk()` | 每题建立新会话，拼 system prompt、restrictions 和 problem |
| 调用模型 | `agent.py::LLMAgent.ASK_LLM_iterate()` | 通过 OpenAI-compatible chat/responses API 保留对话历史 |
| 提取答案 | `gen_data.py` | 用 `<result>\n` 切分 JSON；对标签格式较敏感 |
| JSON/模型检查 | `evaluation.py::evaluate()` | `json.loads` 后把 `models` 字符串映射为 `devices.py` 可调用函数 |
| 构造电路 | `sax.circuit()` | 用 `instances/connections/ports/models` 构造整体散射模型 |
| 功率曲线 | `evaluation.py` | `1.51–1.59 μm`、1000 点，计算每个 I/O 的 `abs(S[i,o])**2` |
| Golden 比较 | `compare_golden()` | round 10 位后把曲线 tuple 转成 set 比较 |
| 错误反馈 | `gen_result_feedback_passk()` | 把 evaluator 文本接回同一会话，要求重写完整 JSON |
| 统计/落盘 | `cal_passk()`、JSON log | 统计 syntax/functional 口径并保存候选 netlist |

`devices.py` 不是静态器件名表：`straight`、coupler、MMI、MZI、MZM、MRR 等函数返回具体 S 参数字典，部分复合器件本身也是通过 `sax.circuit()` 由基础器件组合出来。因此“模型名合法”之后仍有端口和物理响应两层检查。

---

## 7. Prompt 的四个组成部分

### 7.1 System Prompt

`system_prompt.txt` 定义模型身份、合法 JSON 结构、可用器件、器件端口、默认参数、单位和输出格式，相当于给 LLM 一份简化的器件库 API 文档。

### 7.2 Restrictions

`restrictions.txt` 规定：

- 每个器件端口只能连接一次；
- 实例名不能带下划线；
- `result` 中不能出现注释或 Markdown Fence；
- 外部 `I1/O1` 只能出现在 `ports` 中，不能直接出现在内部 `connections` 中；
- `connection` 必须采用“实例名,端口名”形式；
- MMI 反向作为 combiner 时，使用 `O1/O2` 作为两路输入，`I1` 作为合并输出。

系统级端口和器件级端口必须区分。错误写法：

~~~json
"connections": {
  "I1": "mmi1,I1"
}
~~~

正确写法：

~~~json
"ports": {
  "I1": "mmi1,I1"
}
~~~

### 7.3 固定 MZI One-shot 示例

`agent.py` 固定加入一个 MZI 问答示例，用来展示器件分析、`instances`、`connections`、`ports` 和 `models` 的写法。它提高格式正确率，但也可能让模型过度模仿“MZI + 两个 MMI + 两条支路”结构，对微环或大型交换网络形成提示偏置。

### 7.4 当前自然语言问题

当前题目描述功能、输入输出数量、指定器件、参数和网络规模。模型必须从非结构化文字中提取结构化规格：需要什么器件、多少级、怎样连接、参数是多少、外部 I/O 在哪里。

---

## 8. 模型 API 调用与推理本质

当前 Simplaj 配置使用 OpenAI-compatible Responses API：

~~~text
OPENAI_BASE_URL=https://sub2api.simplaj.top/v1
OPENAI_API_MODE=responses
SIMPLAJ_API_KEY=...
~~~

请求发送至 `POST /v1/responses`，包含 `model=gpt-5.4` 和由 system、user、assistant、user 消息构成的 `input`。SSL、超时、429 和 5xx 最多重试 4 次，等待时间为 1、2、4 秒；**这只是网络层重试，和 evaluator 的电路修正重试是两回事**。

LLM 推理时，文本首先被 tokenizer 转成 Token，Transformer 根据上下文计算下一个 Token 的条件概率：

$$P(x_{t+1}\mid x_1,x_2,\ldots,x_t)$$

模型不断预测下一个 Token，最终拼出 analysis 和 JSON。此时权重不变，没有梯度、反向传播或参数更新，所以这是**推理，不是训练**。

模型不会在内部真正运行 SAX。它可能生成看起来合理的端口，例如 `mrr2,I2`，但仓库中的 MRR 实际只有 `I1、O1、O2、O3`，必须由外部确定性仿真器检查。

---

## 9. JSON Netlist 四个核心部分

标准结构：

~~~json
{
  "netlist": {
    "instances": {},
    "connections": {},
    "ports": {}
  },
  "models": {}
}
~~~

### 9.1 instances：电路中有哪些器件

~~~json
"instances": {
  "splitter": "mmi",
  "topwg": {
    "component": "waveguide",
    "settings": {"length": 20}
  },
  "bottomwg": "waveguide",
  "combiner": "mmi"
}
~~~

实例名表示电路中的一个具体器件，`component` 表示逻辑器件类型。多个实例可共享同一个模型，但它们仍是不同的电路实例。

### 9.2 connections：器件之间怎样连接

~~~json
"connections": {
  "splitter,O1": "topwg,I1",
  "topwg,O1": "combiner,O1",
  "splitter,O2": "bottomwg,I1",
  "bottomwg,O1": "combiner,O2"
}
~~~

这部分决定电路拓扑，是生成任务中最关键、最容易出错的部分。

### 9.3 ports：整个电路的边界在哪里

~~~json
"ports": {
  "I1": "splitter,I1",
  "O1": "combiner,I1"
}
~~~

`connections` 表示内部连线，`ports` 表示整个电路暴露给外部的接口。

### 9.4 models：逻辑器件对应哪个数学模型

~~~json
"models": {
  "mmi": "mmi1x2",
  "waveguide": "straight"
}
~~~

映射链路：实例 `splitter` → 逻辑类型 `mmi` → `devices.py` 中的 `mmi1x2` → 返回该器件的 S 参数。

---

## 10. JSON 提取与解析

模型必须输出：

~~~text
<analysis>
设计推理
<result>
{完整 JSON}
</result>
~~~

程序通过 `response.split("<result>\n")[1]` 提取 JSON。这种方式比较脆弱：如果模型写成 `<result> {`、大小写变化或标签后没有紧随换行，即使 JSON 本身正确，也可能得到 `no result part`。

提取后调用 `json.loads(netlist)`。这一层只验证 JSON 文本语法，不验证器件、端口和功能。**JSON 合法 ≠ 电路合法 ≠ 功能正确**。

---

## 11. 器件模型映射

Evaluator 将 `models` 中的字符串映射为 `devices.py` 中真正的 Python/SAX 模型。例如：

~~~json
"models": {"mrr": "mrr"}
~~~

会转换为可调用的 `mrr` 模型。若名称在 `devices.py` 中不存在，就返回 `wrong model names`，类似 SPICE 网表引用了一个不存在的器件模型。

---

## 12. SAX 怎样构建电路

SAX 使用散射参数描述多端口光子器件：

$$b = Sa$$

其中 `a` 是进入各端口的复振幅，`b` 是离开各端口的复振幅，`S` 是散射矩阵。S 参数同时包含振幅和相位，适合描述波导、耦合器、MMI、MZI 和微环中的传播与干涉。

`sax.circuit()` 根据 `instances` 实例化器件，根据 `connections` 连接器件端口，消去内部端口，保留 `ports` 中定义的外部 I/O，最后得到整个电路的等效散射模型。

从图论角度看：器件实例是节点，器件端口是节点接口，`connection` 是边，`ports` 是整个图与外部系统的边界。

SAX 会检查实例是否存在、端口是否存在、端口是否重复连接以及外部端口绑定是否合法。例如 WDM 反馈答案中的 `mrr2,I2` 会失败，因为仓库 MRR 只有 `I1、O1、O2、O3`。

---

## 13. 波长扫描与功率传输

Evaluator 在 1.51–1.59 μm 之间均匀取 1000 个波长点：

~~~python
wl = jnp.linspace(1.51, 1.59, 1000)
S = design(wl=wl)
~~~

对每个输入输出组合计算：

$$T_{i,o}(\lambda)=|S_{i,o}(\lambda)|^2$$

代码为：

~~~python
trans = abs(S[input_port, output_port]) ** 2
~~~

S 是复数光场传输系数，绝对值平方得到功率传输率。严格说横轴是波长，不是直接以 Hz 为单位的频率；二者可通过 `f=c/λ` 转换。

若电路有 NI 个输入和 NO 个输出，总曲线数为 NI×NO：MZI_ps 为 1 条，WDM mux 为 4×1=4 条，4×4 交换网络为 16 条，8×8 网络为 64 条。每条曲线有 1000 个数值点。

---

## 14. Golden Response 与功能比较

GT 来自 `testcases/<design>/<design>_res.json`。它是参考 Netlist 预先经过 SAX 计算得到的响应，不是参考网表字段本身。

Evaluator 先比较生成曲线数和 GT 曲线数，再将曲线四舍五入到小数点后 10 位并转换成集合比较。因此当前实际判断的是：

```text
生成电路的输入输出功率传输曲线集合 == 参考电路的输入输出功率传输曲线集合
```

**[典型案例]** WDM mux 初始答案可以仿真，但连接了 `O1` through port；参考设计使用 `O2 → waveguide → 下一微环 O3`，物理传播路径和曲线不同，最终返回 `functional error`。这说明“语法合法、能构建、能仿真”和“功能正确”是四个不同层次。

---

## 15. 错误反馈重试

初始答案失败后，程序把 evaluator 错误文本加入同一个对话，请模型修复整个 JSON。模型可以看到原始题目、上一版回答和具体错误，再生成修正版。

~~~mermaid
sequenceDiagram
    participant M as gpt-5.4
    participant E as Evaluator
    participant S as SAX
    M->>E: 初始 Netlist
    E->>S: 构建并仿真
    S-->>E: 响应或异常
    E-->>M: 具体错误文本
    M->>E: 修正后的完整 Netlist
    E->>S: 再次构建与仿真
~~~

本次 `max_iterations=1`，每个 Sample 最多只有一个修正版。WDM 示例中，初始答案是 `functional error`，模型修改拓扑后却使用不存在的 `I2`，第二版在 SAX 端口检查阶段失败，并因没有第三次机会而最终失败。

这属于 **verifier-guided inference** 或 **execution feedback**，不是强化学习：错误只改变当前上下文，没有更新模型权重。

---

## 16. Pass@k 与 33 个 Netlist

若同题独立生成 n 个 Sample，其中 c 个成功，从中抽 k 个至少有一个成功的概率估计为：

$$\mathrm{Pass@k}=1-\frac{\binom{n-c}{k}}{\binom{n}{k}}$$

本次 `n=1、k=1`，所以 functional Pass@1 等于功能通过题数除以总题数：`10/24 = 0.4167`。

当前 `syntax Pass` 的名字容易误解。代码把 `syntax check passed` 与 `functional check passed` 相加；这里的 syntax success 实际表示至少有一个候选成功进入功能曲线比较，并非仅仅 `json.loads` 成功。更准确的名称是 **simulation-valid Pass@1** 或 **evaluable Pass@1**。

24 道题每题至少有一个初始候选，因此至少保存 24 个 Netlist。总计 33 个说明额外保存了 9 个可提取的反馈版本。**日志中的 Netlist 数量不等于题目数、独立 Sample 数或 API 请求数**。

严谨实验应分别记录 `design_id`、`sample_id`、`attempt_id`、API call、原始回答、提取结果、SAX 状态、evaluator 错误、reward 和耗时。

---

## 17. 复现阶梯：本机已验证到哪一级

```text
复现阶梯（本机已验证）
  Level 5  ░░░░░  完整 GRPO 训练并收敛      — 尚未实现
  Level 4  ░░░░░  批量采样 + 组内 Advantage   — 尚未实现
  Level 3  ▓▓▓▓▓  自动错误反馈重试          — 已跑通 [24/24]
  Level 2  ▓▓▓▓▓  SAX 构建 + 曲线比较       — 已跑通 [24/24]
  Level 1  ▓▓▓▓▓  JSON 提取 + 模型名检查     — 已跑通 [24/24]
```

本机已经证明：自然语言 → LLM → JSON Netlist → SAX 仿真 → Golden Response 比较这条链路可以端到端跑通。但距离真正的 GRPO 训练，还缺少批量采样、Reward Function 封装、组内 Advantage、Clipped Objective、KL 约束和可训练模型接入。

---

## 18. 当前实现需要修复的问题

| 问题 | 影响 | 建议修复 |
|---|---|---|
| set 比较丢失端口标签 | I1→O1、I1→O2 的身份被丢弃，可能误判 | 保存 `(input_port, output_port) → curve` 映射并逐键比较 |
| 数值比较过于严格 | round 10 位后完全相等易受浮点/平台影响 | 使用 `np.allclose`，同时报告 MSE 与最大误差 |
| result 提取容错不足 | 合法 JSON 可能被判成 `no result part` | 使用稳健正则、JSON 对象定位或 Responses API 结构化输出 |
| 日志信息不足 | 不保存原始回答、错误、reward、重试轮次 | 每次 attempt 保存完整元数据 |
| `feedback_flag` 生命周期问题 | 第一个 Sample 状态可能影响后续 Sample | 每个 Sample 开始时重置状态 |
| 指标可能重复计数 | 初始 functional error、反馈后通过会被同时加 | 每个 Sample 保存最终 `syntax_success` 和 `functional_success` 布尔值 |

---

## 19. 怎样改造成 GRPO

当前流程已经提供 Prompt、生成器、仿真环境和自动判分器。真正 GRPO 还需要对同一个 Prompt 批量采样 G 个回答、为每个回答计算 reward、组内计算相对 Advantage、计算 clipped objective 和 KL、反向传播并更新模型参数。

~~~mermaid
flowchart LR
    A["Prompt q"] --> B["可训练策略模型 πθ"]
    B --> C["同一 q 采样 G 个回答"]
    C --> D["批量 SAX Evaluator"]
    D --> E["得到 r1...rG"]
    E --> F["组内相对 Advantage"]
    F --> G["GRPO Loss + KL"]
    G --> H["反向传播更新 θ"]
    H --> B
~~~

最直接的奖励是 functional check passed 给 1，其余给 0。理论上完全成立，但训练初期一组回答可能全为 0，没有组内方差，模型学不到有效信息。

可以使用**课程式奖励**：

| 里程碑 | 奖励 |
|---|---|
| 成功提取 result | 0.02 |
| JSON 合法 | 0.05 |
| 模型名合法 | 0.10 |
| SAX 可构建 | 0.20 |
| I/O 数量正确 | 0.30 |
| 曲线接近 GT | 0.30–0.90 |
| 完全通过 | 1.00 |

也可以使用 `exp(-α·MSE)` 构造连续曲线奖励，并保留最终通过奖励。

原项目的错误反馈重试仍不是 GRPO，因为它没有 optimizer、Token log probability、Group Advantage、GRPO Loss、反向传播、Reference Policy/KL 或 checkpoint。

---

## 20. 数据是否足以训练

数据格式完全适合 verifier-based RL：Prompt 是自然语言规格，Action 是完整 JSON Token 序列，Environment 是 JSON Parser + SAX，Reward 来自 Evaluator。

但只有 24 个固定题时，直接训练并在同一批题上测试会产生**数据泄漏**。模型可能记住拓扑，而不是学会设计规律。应程序化生成不同 N、路径长度、相移、谐振波长、端口数量、实例名称和自然语言表达，并严格划分 Train、Validation、Test。

---

## 21. 应用与学习路线

### 直接应用

PICBench 的直接应用是让 LLM 充当 PIC 电路拓扑综合助手：工程师用自然语言提出功能，模型生成器件级 Netlist，SAX 快速验证，不满足时继续修改，满足后再进入版图和更高精度仿真。

~~~mermaid
flowchart LR
    A["工程师提出功能需求"] --> B["LLM 生成器件级 Netlist"]
    B --> C["SAX 功能验证"]
    C --> D{"满足规格？"}
    D -- 否 --> B
    D -- 是 --> E["版图与高精度仿真"]
    E --> F["工艺验证、制造与测试"]
~~~

适合写入研究计划的专业描述：

> 利用光子电路仿真器提供的可执行功能奖励，通过 GRPO 训练语言模型，将自然语言光子系统规格自动综合为功能正确的层次化 PIC Netlist。

### 建议学习顺序

1. 先看 **MZI_ps**：从题目到参考 Netlist，手动画出实例、内部连接和外部端口。
2. 阅读 `straight`、`coupler`、`mmi1x2`，理解相位、振幅分配和干涉。
3. 单步理解 Evaluator 中 JSON、Model Mapping、SAX Circuit、`S[(I,O)]` 和 `|S|²` 的数据形状。
4. 区分 JSON 合法、SAX 可构建、功能正确、反馈重试和 Pass@k。
5. 修复端口标签比较、指标重复计数、Sample 状态污染和日志格式。
6. 先实现批量 Reward Function，再接可训练开源模型和 GRPO。

---

## 22. 阶段性结论

本次实验已经证明自然语言、LLM、JSON Netlist、SAX、功能曲线和自动判分能够形成可运行闭环。

- `24/24` 的可评测率说明结构化生成基本可靠；
- `10/24` 的功能正确率说明真正困难在光子拓扑、端口语义和物理功能；
- 当前仍是**推理时的 Verifier-Guided Refinement**，不是 GRPO 训练。

正式训练前必须加固 Evaluator、修正指标统计、保存完整轨迹并建立无数据泄漏的 Train/Validation/Test。

---

## 23. 四种“正确”的层级

对 PICBench 来说，“模型答对了”不是单一概念，而是逐层收紧的四个条件：

1. **文本格式正确**：能够找到 `<result>` 并提取内容。
2. **JSON 语法正确**：`json.loads` 可以解析。
3. **网表可仿真**：模型名、实例、端口和连接合法，SAX 能构造电路。
4. **物理功能正确**：输入—输出功率传输曲线与 Golden Response 相符。

一份答案可能通过前三层，却在第四层失败。WDM mux 初始答案就是典型案例：**它不是“代码写错”，而是“合法电路实现了错误的光学功能”**。

---

## 24. 10 道功能通过题说明了什么

本次通过 Benes_4x4、Benes_8x8、Crossbar_4x4、Direct modulator、MZM、Optical hybrid、Spanke_4x4、Spanke_8x8、Spanke–Benes_4x4 和 WDM_demux。这说明 gpt-5.4 已具备一定的器件选择、拓扑模式识别、JSON 结构生成和多级连接能力。

但 `24/24` 可评测、`10/24` 功能正确也说明：**当前主要瓶颈不是 JSON 格式，而是精确的光子拓扑、端口方向、器件级数和物理响应**。后续优化不应只继续堆格式提示词，还要增强端口 API、拓扑示例、可执行反馈和训练奖励。

---

## 25. 最终结论

PICBench 已经形成“自然语言规格—LLM 网表生成—SAX 功能仿真—自动奖励判定”的闭环。本次 24 题结果证明生成、解析、仿真、反馈和判分链路均能工作，并且可以自然构造 0/1 Executable Reward。

目前它仍是推理时的 Verifier-Guided Refinement，而不是 GRPO 训练。完成 Evaluator 加固、指标修正、轨迹记录和数据集划分后，它可以成为一个**仿真器驱动、面向光子 EDA 的 Verifier-Based RL 环境**。

---

## 组会讨论问题

1. **PICBench 里“语法通过”和“功能通过”的 gap 为什么这么大？** 这 14 道功能失败的题中，哪些属于端口/拓扑错误，哪些属于物理响应错误，怎样设计更细粒度的 reward 来缩小这个 gap？

2. **把当前错误反馈重试改造成 GRPO，最关键的工程难点是什么？** 是 batch SAX 仿真的速度、Reward Hacking 的防范、Group Advantage 的计算，还是 Train/Test 数据泄漏问题？

3. **如果要把 PICBench 扩展到真实 PDK 流片，还需要补哪些模块？** 版图生成、波导布线、DRC/LVS、热串扰、制造偏差中，哪些可以放进当前 RL 循环，哪些必须作为后处理？
