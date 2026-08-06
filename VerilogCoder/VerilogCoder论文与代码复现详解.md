# VerilogCoder：多 Agent、TCRG 规划与 AST 波形追踪复现详解

> 论文：*VerilogCoder: Autonomous Verilog Coding Agents with Graph-based Planning and Abstract Syntax Tree (AST)-based Waveform Tracing Tool*  
> 作者：Chia-Tung Ho、Haoxing Ren、Brucek Khailany（NVIDIA Research）  
> 本地论文：[2408.08927_VerilogCoder.pdf](./2408.08927_VerilogCoder.pdf)  
> 论文地址：https://arxiv.org/abs/2408.08927  
> 论文 PDF：https://arxiv.org/pdf/2408.08927  
> 代码地址：https://github.com/NVlabs/VerilogCoder  
> 本地核对日期：2026-08-02  
> 本地代码提交：`8b13108869f276c7b644dd88beabcb401a5cfa92`

---

```text
┌─────────────────────────────────────────────────────────────────┐
│ P1 任务定义                                                        │
├─────────────────────────────────────────────────────────────────┤
│ Input      │ VerilogEval-Human v2 自然语言规格 + 模块接口 + golden testbench │
├─────────────────────────────────────────────────────────────────┤
│ Output     │ 能通过 testbench（Mismatches: 0 in N）的功能正确 Verilog 模块 │
├─────────────────────────────────────────────────────────────────┤
│ Supervision│ Icarus 编译/仿真错误 + mismatch 计数 + AST 反向追踪波形证据   │
├─────────────────────────────────────────────────────────────────┤
│ Why-hard   │ 自然语言规格模糊，需先转成带信号/转移/示例的电路级计划；传统   │
│            │ mismatch 日志难以定位根因，需要沿 RTL AST 做依赖锥追踪       │
└─────────────────────────────────────────────────────────────────┘
```

## 0. 结论先行

VerilogCoder 不是一个新训练的 Verilog 基座模型，而是一个构建在 AutoGen 上的多 Agent 推理系统。它把 spec-to-RTL 拆成两大阶段：

1. 用 Task and Circuit Relation Graph（TCRG）生成带信号、状态转移和示例的细粒度计划；
2. 按计划逐步写 RTL，最后用 Icarus 仿真和 AST-based Waveform Tracing（AST-WT）反复修正功能错误。

它相比普通“生成—编译—把日志返给 LLM”的核心增量有两个：

- 规划反馈不是通用文本 RAG，而是面向当前规格临时构建的电路关系图；
- 调试反馈不只给失配数，而是从错误输出沿 DUT 的 AST 反向追踪 RVALUE 依赖，并输出 DUT/REF 波形对照表。

本地已经取得三类强证据：

| 层级 | 本地证据 | 结论 |
|---|---|---|
| 单工具 | 正确 AND 门 0/219；故意错误 OR 门 126/219 | 编译/仿真路径可用 |
| AST-WT | 得到 `a,b -> and1 -> out`，生成 DUT/REF 波形表 | 核心调试工具可用 |
| 全量保存产物 | 仓库 147 个常规生成 RTL 全部重新编译、仿真通过 | `147/156=94.2308%`，与论文 94.2% 一致 |

但这里必须严格区分：

> 本机重新验证了仓库保存的最终 RTL 和确定性工具链，没有重新调用 GPT-4 Turbo/Llama3 生成 156 题，因此没有复现随机 Agent 对话、平均调用次数和 13 倍 token 开销。

当前复现等级建议记为 **B+：官方保存结果已全量重验，核心工具已实跑，模型生成阶段未重跑**。

---

## 1. 论文版本与定位

本地 PDF 信息：

- arXiv:2408.08927v2；
- 版本日期 2025-03-05；
- 8 页；
- 首页标注 AAAI 2025 copyright；
- 论文和代码均给出 NVIDIA Research 作者信息。

论文关注的是 VerilogEval-Human v2 的 specification-to-RTL 任务：输入比旧版仅有 module header 的 prompt 更完整，更接近“自然语言详细规格 -> RTL”。

论文报告：

- VerilogCoder + GPT-4 Turbo：94.2%；
- VerilogCoder + Llama3 70B：67.3%；
- GPT-4 Turbo 非 Agent baseline：60.3%；
- 相对该 baseline 提高 33.9 个百分点。

这是一次 Agent 运行每题一次的 pass rate，不是对同一题采样多次后计算 pass@k。

---

## 2. 研究动机

### 2.1 普通高层计划会丢电路细节

通用 LLM 容易给出：

```text
1. Define interface
2. Define state encoding
3. Implement state transition
4. Implement output logic
```

这类计划“听起来正确”，但没有告诉代码 Agent：

- 哪个状态在什么输入下跳到哪个状态；
- 哪个 output 对应哪个组合逻辑；
- 波形示例中某个时刻应该发生什么；
- 当前子任务需要哪些信号，而不是整个规格的全部信息。

论文 Figure 1(a) 展示了传统规划漏掉 FSM 转移，而 TCRG 计划把相关转移直接挂到具体子任务上。

### 2.2 原始 mismatch 日志不足以定位根因

testbench 可能只说：

```text
Output 'q' has 12 mismatches.
First mismatch occurred at time ...
```

输出 `q` 的根因可能在内部 `and1`，而 `and1` 又由 `a_in`、`b_in` 控制。人类设计者会沿逻辑锥逐层看波形；论文将这个动作形式化成 AST RVALUE 反向追踪。

![Planning and AST motivation](./figures/paper-fig1-planning-and-ast-motivation.png)

图源：论文 Figure 1，本地 PDF 第 2 页截图。

---

## 3. 总体架构

![Overall multi-agent flow](./figures/paper-fig2-overall-multi-agent-flow.png)

图源：论文 Figure 2，本地 PDF 第 3 页截图。

系统主流程：

```text
自然语言规格 + module interface + golden testbench
                    |
                    v
              TCRG Task Planner
       /              |                 \
高层任务规划      信号/转移/示例抽取      建图与逐任务检索
       \              |                 /
                    v
          enriched sequential task plans
                    |
                    v
             Code Agent 逐任务写 RTL
                    |
            syntax checker (iverilog)
                    |
                    v
               Debug Agent
        simulator <-> AST-WT <-> RTL 修改
                    |
           [Function Check Success]
                    |
                    v
              保存最终 .v / .sv
```

论文把角色归纳为：

- Planner；
- Plan Verify Assistant；
- Verilog Engineer；
- Verilog Verify Assistant。

代码实际上创建了多个不同的 `HardwareAgent`/GroupChat，每个阶段可重复使用同一底层模型配置，但 system prompt、工具和终止条件不同。

---

## 4. 从入口到最终文件的代码调用链

### 4.1 入口

文件：

```text
hardware_agent/examples/VerilogCoder/run_verilog_coder.py
```

主要步骤：

```python
case_manager = VerilogCaseManager(...)
coding_agent = VerilogCoder(...)
success = coding_agent.write_Verilog_module(
    cur_task_id=...,
    spec=...,
    golden_test_bench=...
)
```

五种 LLM 配置键是：

```text
task_planner_llm
kg_llm
graph_retrieval_llm
verilog_writing_llm
verilog_debug_llm
```

示例入口把五者都指向 `OAI_CONFIG_LIST` 中同一 `gpt-4-turbo`，但架构允许分别替换。

### 4.2 主类

文件：

```text
hardware_agent/examples/VerilogCoder/verilogcoder.py
```

主调用链：

```text
write_Verilog_module()
  |
  +-- VerilogToolKits.load_test_bench()
  |
  +-- make_plans()
  |     +-- TaskPlanAgent.make_plans()
  |     +-- KnowledgeGraphToolKits.create_knowledge_graph()
  |     +-- plan_gr_agent.initiate_chat()
  |
  +-- complete_functional_correct_code()
        +-- 为每个 plan 配置 Code Agent
        +-- 末尾追加 Debug Agent task
        +-- BaseTaskFlowManager.create_DAG_task_graph()
        +-- check_sequential_task_flow()
        +-- execute_task_flows()
        +-- validate_correct_parse()
        +-- VerilogToolKits.write_verilog_file()
```

### 4.3 数据怎样流过子任务

`Task.execute()` 收集父任务的 `output`，拼到：

```text
[Previous Task Implementation]
{PreviousTaskOutput}
```

Code Agent 每个任务的 `verilog_output_parse()` 从聊天历史倒序寻找最后一个：

````markdown
```verilog
...
```
````

并把它作为当前 task output，传入下一任务。

因此每一步并不是只产出一个局部 patch，而是继续传递一个当前完整 RTL 文本。

---

## 5. TCRG 规划到底是什么

TCRG 是 Task and Circuit Relation Graph。

它的节点类型：

| 节点 | 含义 |
|---|---|
| Plan | 高层子任务 |
| Signal | 信号定义 |
| StateTransition | 状态/信号转移描述 |
| SignalExample | 规格里的输入输出或波形示例 |

关系类型：

| 边 | 方向 | 含义 |
|---|---|---|
| IMPLEMENTS | Plan -> Signal | 子任务实现该信号 |
| SIGNALTRANSITION | Signal -> StateTransition | 转移涉及该信号 |
| EXAMPLES | Signal -> SignalExample | 示例描述该信号 |

这不是从外部 Verilog 语料库检索相似代码，也不是用 embedding 查论文段落。图只由当前问题的规格、计划和抽取实体构成。

### 5.1 高层 Planner

`TaskPlanAgent._create_rough_plans()` 让 Planner 生成 JSON `subtasks`。

GroupChat 角色：

- `planner`：拆分任务，不直接写代码；
- `plan_verify_assistant`：核对计划与规格、规则是否一致；
- `user`：无人工输入，执行可用工具。

聊天采用 round-robin，最大 100 round。验证 Agent 认为计划足够时，在响应末尾写 `TERMINATE`。

### 5.2 计划被强制改成顺序链

Planner 原始 JSON 即使带其他依赖，`TaskPlanAgent.make_plans()` 仍重新写入：

```python
task[0]["parent_tasks"] = []
task[i]["parent_tasks"] = [task[i-1]["id"]]
```

所以真实执行图是：

```text
Task 1 -> Task 2 -> ... -> Task N -> Debug task
```

论文和类名使用“task dependency graph / DAG”，但当前实现明确拒绝有分叉的图：`check_sequential_task_flow()` 发现任一节点 child 数大于 1 就返回 False。

因此它是“用 DAG 数据结构表达的顺序任务链”，不是并行执行多个独立 RTL 子模块。

### 5.3 实体抽取 Agent

`_extract_entity()` 要求 LLM 返回 JSON，至少含：

```json
{
  "signal": [],
  "state_transitions_description": [],
  "signal_examples": []
}
```

代码从 chat history 倒序找最后一个 JSON code block；没有 code block 就断言失败。

### 5.4 建图成本

`KnowledgeGraphToolKits.build_knowledge_graph()` 不只是一次 LLM 调用：

1. 每个 Plan/Signal/Transition/Example 都调用 LLM 生成 node ID；
2. 每个 Plan × Signal 对调用 LLM 判断 `IMPLEMENTS/NORELATION`；
3. 每个 Signal × Transition 对调用 LLM 判断关系；
4. 每个 Signal × Example 对调用 LLM 判断关系。

节点和实体多时，关系判断调用数近似组合乘积，可能成为 token/时延主要来源。论文只报告整个系统 token 约为 baseline 的 13 倍，没有单列 TCRG 建图开销。

### 5.5 检索是精确匹配 + BFS

图检索函数：

```text
KnowledgeGraphToolKits.networkx_bfs_knowledge_graph_query()
```

输入：

- `current_plan`：当前 plan 的完整 description；
- `BFS_retrival_level`：Agent 自己决定的 hop 数。

代码首先用 description 精确查 `description -> node ID` 映射；没有相同字符串就返回错误，当前没有 similarity search。

命中后沿有向 successor 做 BFS，返回 k-hop 相关节点 description 和 type。

![TCRG retrieval](./figures/paper-fig3-tcrg-retrieval.png)

图源：论文 Figure 3，本地 PDF 第 4 页截图。

Agent 可以先查 1 hop，只拿到 Signal，再把 k 增大到 2，继续拿到 StateTransition/Example，最后整理成 enriched plan。

### 5.6 本地计划文件审计

`verilog-eval-v2/plans/` 有 156 个与数据集任务一一对应的最终 `_plan.json`。

本地解析结果：

| 指标 | 数值 |
|---|---:|
| 成功解析计划 | 156/156 |
| 符合顺序 parent 链 | 156/156 |
| 总子任务 | 725 |
| 每题最少/最多 | 1 / 25 |
| 平均每题 | 4.6474 |
| 中位数 | 4 |
| 含 `Retrieved Related Information` 的 plan 节点 | 677 |

AND 门计划只有两步：

1. 定义 `a,b,out` 接口，并附三者 Signal 信息；
2. 用 `a & b` 实现 `out`，并附 AND gate 规格来源。

---

## 6. Code Agent 怎样写代码

每个普通 plan task 都使用 `verilog_complete_agent`。

### 6.1 角色

Code Agent 的 GroupChat 有：

- `verilog_engineer`：根据当前子任务继续写完整 RTL；
- `verilog_verification_assistant`：检查子任务一致性并调用 syntax tool；
- `user`：自动执行工具，无人工输入。

### 6.2 轮转与终止

- speaker selection：round-robin；
- 最大 round：100；
- Engineer temperature：0.1；
- Verify Assistant temperature：0；
- 两个 assistant 仅保留最近 3 条消息的 HistoryLimit；
- Verify Assistant 确认代码符合子任务且语法正确后，必须先返回完整 Verilog code block，再在外面写 `TERMINATE`。

论文文字说“保留原始 query 和最后四条 chat”，当前代码的主要 Code/Debug Agent transform 配置是 `max_messages=3`。这是论文描述和提交代码的一个小差异。

### 6.3 Syntax Checker

工具：

```text
VerilogToolKits.verilog_syntax_check_tool()
```

它把：

```text
golden testbench + RefModule + generated TopModule
```

拼为 `test.sv`，并运行：

```bash
iverilog -Wall -Winfloop -Wno-timescale -g2012 -s tb \
  -o <workdir>/test.vpp <workdir>/test.sv
```

编译有任何 stdout/stderr 合并输出都会进入失败报告。工具尝试：

- 找到报错行；
- 判断报错是否位于 testbench 之后的 generated module；
- 截取错误前后约 5 行；
- 在行尾加 `## Error line: ... ##`；
- 返回给 Verify Assistant。

通过时返回：

````text
[Compiled Success Verilog Module]:
```verilog
<latest RTL>
```
````

---

## 7. Debug Agent 闭环

所有 Code task 完成后，系统追加一个：

```text
Debugging and Fixing the waveform
```

其 parent 是最后一个 code task。

### 7.1 角色和工具

Debug Agent 的 GroupChat 只有：

- `verilog_engineer`；
- `user` 工具执行代理。

Engineer 可调用：

- `verilog_simulation_tool`；
- `waveform_trace_tool`。

最大 40 round，temperature 0.2，HistoryLimit 为最近 3 条消息。

system prompt 要求只有看到 Function Check Success 才写 `TERMINATE`。

### 7.2 Simulator tool

`verilog_simulation_tool()` 先按 Syntax Checker 相同方式编译，再运行：

```bash
vvp <workdir>/test.vpp
```

`check_functionality()` 接受两种输出：

```text
Mismatches: M in N samples
```

或：

```text
Hint: Total mismatched samples is M out of N samples
```

`M==0` 时返回：

```text
[Compiled Success]
[Function Check Success]
```

否则返回：

```text
[Compiled Success]
[Function Check Failed]
==Tool Output==
<完整 vvp stdout>
==Tool Output End==
```

并明确提示 Agent 把这个工具输出输入 `waveform_trace_tool`，从 `trace_level=2` 开始。

### 7.3 最终成功判定

`validate_correct_parse()` 不重新调用仿真。它倒序扫描 Debug Agent 的 `chat_history`，只要某条消息同时包含：

```text
[Compiled Success]
[Function Check Success]
```

就返回 `Pass`，否则返回 `Failed`。

成功后，`write_verilog_file()` 保存工具对象中“最近一次传给 simulator/syntax checker 的 completed_verilog”。

所以最终 RTL 的选择逻辑不是候选排名，也不是多数投票：

> Debug Agent 持续修改一个当前版本；最后一次通过工具的版本保存在 `VerilogToolKits.completed_verilog`，聊天历史出现成功标记后保存该版本。

---

## 8. AST-WT 如何工作

![Debug Agent and AST-WT](./figures/paper-fig4-debug-agent-trace.png)

图源：论文 Figure 4，本地 PDF 第 5 页截图。

### 8.1 输入

`waveform_trace_tool()` 需要：

- simulator tool 的完整输出字符串；
- `trace_level`，由 Agent 动态选择；
- 当前 `test.v`；
- 当前 `wave.vcd`。

### 8.2 解析首个失配

`parse_mismatch()` 在日志中寻找：

```text
Hint: Output '<signal>' has ... First mismatch occurred at time <t>.
```

返回：

- 所有带 first mismatch 的 output signal 名；
- 其中最早的 timestamp。

如果日志没有这种行，代码对空字典执行 `min()` 会失败。

### 8.3 构建 AST 逻辑依赖图

`DebugGraph` 调用仓库 vendor 的 Pyverilog：

```text
generate_top_logic_graph([<workdir>/test.v])
```

图中既有 signal，也可能有 Always、Assign、Module、IntConst 等逻辑节点。

`get_k_control_signals(..., signal_only=True)` 从错误 output 开始，沿 graph predecessor 做 BFS，并过滤部分非 signal 节点，得到每层：

```text
predecessor -> controlled signal
```

### 8.4 波形列重命名

VCD 层级名按 VerilogEval testbench 约定转换：

- `top_module1.<signal>` -> `<signal>_dut`；
- `good1.<signal>` -> `<signal>_ref`；
- `tb.<signal>` -> testbench signal；
- clock 单独处理。

所以工具高度依赖 testbench instance 名：

```text
top_module1
good1
tb
```

换成自定义 testbench 命名后，波形列选择可能失效。

### 8.5 生成表格

`get_tabular()` 用 `vcdvcd` 读取 VCD，构造 timestamp × signal 的 DataFrame：

1. 信号变化点填入矩阵；
2. 前向填充保持值；
3. 选择 mismatch、AST traced signal 和 input port；
4. 转成十六进制/字符串；
5. 给出失配前窗口和之后若干行；
6. 附上第一失配行的 DUT/REF 值。

当前 `waveform_trace_tool()` 设置 `full_module=True`，所以除了波形表，还把整个 DUT 再放回 Debug Agent；代码中存在只返回相关行片段的分支，但默认未启用。

### 8.6 输出提示

最终工具输出包含：

- AST control-signal backtrace；
- testbench input 列表；
- traced signal 列表；
- DUT/REF 波形表；
- 完整 DUT；
- 不允许修改 input/testbench 的提示；
- 若信息不足，增大 `trace_level` 再查的提示；
- 若首个 mismatch 很早，检查初始化的启发式提示。

这比仅返回 `126 mismatches` 更容易让 LLM定位内部逻辑。

---

## 9. 本地 AND 门核心工具复现

### 9.1 复现范围

任务：VerilogEval-Human v2 `Prob014_andgate`。

验证：

1. 官方 loader 合并 testbench 与 RefModule；
2. syntax checker；
3. simulator；
4. mismatch 解析；
5. VCD 移动与读取；
6. Pyverilog AST 图；
7. k=2 依赖 BFS；
8. DUT/REF 波形表。

没有调用 LLM。

### 9.2 正确实现

仓库保存的 `andgate_0.v`：

```verilog
module TopModule(
  input  logic a,
  input  logic b,
  output logic out
);
  assign out = a & b;
endmodule
```

本地输出：

```text
[Compiled Success]
[Function Check Success]
Mismatches: 0 in 219 samples
```

### 9.3 受控错误实现

故意加入内部节点并把 AND 改成 OR：

```verilog
logic and1;
assign and1 = a | b;
assign out = and1;
```

本地输出：

```text
[Compiled Success]
[Function Check Failed]
Hint: Output 'out' has 126 mismatches.
First mismatch occurred at time 20.
Mismatches: 126 in 219 samples
```

### 9.4 AST 回溯

实际 BFS frontier：

```text
and1 -> out
a -> and1
b -> and1
```

实际 traced signals：

```text
out, and1, a, b
```

波形表的关键行：

```text
a_dut=0, b_dut=1, and1_dut=1, out_dut=1, out_ref=0
```

这恰好说明根因：OR 在 `0,1` 时为 1，而 AND 应为 0。

### 9.5 本地产物

- [工具运行记录](./runs/tool_smoke_andgate/record.json)
- [关键 trace 摘录](./runs/tool_smoke_andgate/trace_excerpt.md)
- [运行目录](./runs/tool_smoke_andgate/work/)

工作目录包含：

- `test.sv`：testbench + RefModule + 最后错误 DUT；
- `test.v`：最后错误 DUT；
- `test.vpp`；
- `wave.vcd`；
- `tmp.vcd`。

### 9.6 第一次加载失败揭示的必要路径

直接把 `Prob014_andgate_test.sv` 传给 toolkit 会报：

```text
Unknown module type: RefModule
```

因为 v2 数据集把 golden `RefModule` 单独放在 `_ref.sv`。

正式入口 `load_verilog_eval2_cases()` 会执行：

```python
task['test'] = task['test'] + "\n" + task['ref']
```

然后才传给 `load_test_bench()`。本次成功复现严格沿该 loader 路径。

---

## 10. 147 个保存结果的全量重验

### 10.1 仓库产物分布

本地数据：

| 目录 | 数量 |
|---|---:|
| dataset prompt | 156 |
| dataset ref | 156 |
| dataset test | 156 |
| 最终 `_plan.json` | 156 |
| 常规生成 `*_0.v` | 147 |
| 常规组合测试 `*_0.sv` | 147 |

另有一组 `2014_q3fsm_0_success.v/.sv` 备用成功产物，不计入常规 147。

### 10.2 本地重验方法

对每个常规 `task_0.v`：

```text
*_test.sv + *_ref.sv + task_0.v -> isolated /tmp/case.sv
```

编译：

```bash
iverilog -Wall -Winfloop -Wno-timescale -g2012 -s tb \
  -o case.vvp case.sv
```

仿真：

```bash
vvp case.vvp
```

每题用独立临时目录，避免 `wave.vcd` 覆盖。最后解析标准 `Mismatches: M in N samples` 行。

### 10.3 实际结果

| 检查项 | 数量 |
|---|---:|
| 任务映射成功 | 147/147 |
| 编译通过 | 147/147 |
| 有标准 mismatch 行 | 147/147 |
| `M==0` | 147/147 |

因此：

```text
147 / 156 = 0.9423076923 = 94.2308%
```

保留一位小数就是论文 Table 1 的 94.2%。

额外的 `2014_q3fsm_0_success.v` 也单独重验通过：

```text
Mismatches: 0 in 1414 samples
```

### 10.4 没有常规成功输出的 9 题

```text
count_clock
ece241_2013_q2
ece241_2013_q4
ece241_2014_q5a
fsm_ps2data
gshare
lemmings4
review2015_fancytimer
review2015_fsm
```

仓库仍有这 9 题的计划和数据，只是 `plan_output` 没有常规 `*_0.v` 成功结果。

### 10.5 证据文件

- [全量保存结果验证记录](./runs/bundled_outputs_validation_20260802.json)

这个验证强于只数文件，但仍不等于重新生成：它证明作者保存的 147 个最终 RTL 在当前本地 Icarus 12.0 上全部过原 testbench。

---

## 11. 论文主结果

![Main results](./figures/paper-table1-main-results.png)

图源：论文 Table 1，本地 PDF 第 6 页截图。

| 方法 | 模型 | pass rate |
|---|---|---:|
| RTL-Coder | 6.7B open | 36.5% |
| DeepSeek Coder | 6.7B open | 28.2% |
| CodeGemma | 7B open | 23.1% |
| DeepSeek Coder | 33B open | 37.2% |
| CodeLlama | 70B open | 41.0% |
| Llama 3 | 70B open | 41.7% |
| Mistral Large | closed | 48.7% |
| GPT-4 | closed | 50.6% |
| GPT-4 Turbo | closed | 60.3% |
| VerilogCoder | Llama3 70B | 67.3% |
| VerilogCoder | GPT-4 Turbo | 94.2% |

比较口径需要谨慎：

- VerilogCoder 是每题 Agent 完整流程运行一次；
- 非 Agent 方法取 Revisiting VerilogEval 中 0-shot/1-shot 和 sample size 1–20 里最好的 pass@1；
- 因此表格比较的是最终任务成功率，不是相同 token、相同延迟或相同调用次数。

论文还报告：

- 高层 Planner 平均 GroupChat rounds：1.58；
- TCRG Retrieval Agent 平均 rounds：1.09；
- 论文把“code agent”工具统计写为平均 simulator calls 2.37；
- AST-WT 平均 calls 1.37；
- 总 token 约为 GPT-4 Turbo baseline 的 13 倍。

最后一点非常重要：94.2% 是用显著更多推理计算换来的，不能只看准确率。

---

## 12. 论文消融

![Ablation and taxonomy](./figures/paper-table2-fig5-ablation-taxonomy.png)

图源：论文 Table 2 和 Figure 5，本地 PDF 第 7 页截图。

### 12.1 四种组合

| 规划 | 无 AST-WT | 有 AST-WT |
|---|---:|---:|
| Planner1：普通多 LLM planner | 66.7% | 78.2% |
| Planner2：TCRG planner | 74.4% | 94.2% |

以 Planner1 无 AST-WT 为 baseline：

- 单加 TCRG planning：+7.7 个百分点；
- 单加 AST-WT：+11.5 个百分点；
- 二者同时：+27.5 个百分点。

组合增益大于两项单独增益的简单相加，说明细规划与结构化调试存在协同：计划减少初始遗漏，AST-WT 处理剩余功能错误。

### 12.2 题型差异

论文对四种组合的失败题并集分类：

| 类别 | 数量 | 占比 |
|---|---:|---:|
| Application description | 19 | 29.2% |
| Comb+Seq+FSM description | 23 | 35.4% |
| Comb+Seq+FSM waveform | 8 | 12.3% |
| Combinational K-map | 6 | 9.2% |
| FSM transition table | 9 | 13.9% |

论文观察：

- 对应用描述、一般电路描述、波形描述，AST-WT 的迭代修复更有帮助；
- 对 K-map 和 FSM transition table，TCRG planner 更能完整保留显式映射/状态转移；
- 完整方法在 K-map 和 FSM transition table 达到图中 100%，但这些是相应分类子集结果，不等于所有此类题都普遍解决。

---

## 13. 论文与代码的对应关系

| 论文组件 | 代码实现 |
|---|---|
| High-level Planner Agent | `TaskPlanAgent.plan_agent` |
| Plan Verify Assistant | `task_planner.py` 的 `plan_verify_assistant` |
| entity extraction | `TaskPlanAgent.entity_extraction_agent` |
| TCRG construction | `KnowledgeGraphToolKits.build_knowledge_graph()` |
| TCRG retrieval | `networkx_bfs_knowledge_graph_query()` + `plan_gr_agent` |
| task dependency graph | `BaseTaskFlowManager` |
| Code Agent | `verilog_complete_agent` |
| Verilog Engineer | `verilog_agent_configs.py` |
| Verilog Verify Assistant | 同文件 completion config |
| syntax checker | `verilog_syntax_check_tool()` |
| simulator | `verilog_simulation_tool()` |
| AST-WT | `DebugGraph` + `vcd_waveform_analyzer.py` |
| final pass parse | `validate_correct_parse()` |
| output save | `write_verilog_file()` |

---

## 14. 代码审计发现的复现边界

### 14.1 README 依赖名有拼写问题

README 写：

```bash
pip install network
pip install llangchain_openai==0.2.14
```

实际应至少核对为：

```text
networkx
langchain_openai
```

README 还把多个依赖分散为手工命令，没有提供锁定的完整 requirements/conda environment，容易出现版本漂移。

### 14.2 setup.py 只打包 autogen

`setup.py` 使用：

```python
find_packages(include=["autogen*"])
```

不包含 `hardware_agent*`。所以 `pip install -e .` 安装的是 vendored AutoGen 包，VerilogCoder 自身主要依靠在仓库根目录运行和 `PYTHONPATH` 才能导入。

### 14.3 README quick-start 数据目录不一致

README 先说明 benchmark 在：

```text
<case_dir>/dataset_dumpall
```

但示例命令把：

```text
--verilog_example_dir <case_dir>
```

传给 loader。`load_verilog_eval2_cases()` 需要目录里直接存在 `_prompt/_ref/_test` 文件，所以实际应传 `dataset_dumpall/`。

### 14.4 默认只跑 zero

`run_verilog_coder.py` 硬编码：

```python
user_task_ids = {'zero'}
```

没有命令行参数选择 task set。按 README 原样运行只跑一题，不会跑 156 题。

### 14.5 输出目录必须预先存在且最好带尾斜杠

主类没有统一创建：

- `generate_plan_dir`；
- `generate_verilog_dir`；
- `verilog_tmp_dir`。

`write_verilog_file()` 还拼接：

```python
output_dir + "./" + filename
```

若 `output_dir="/path/out"`，会得到 `/path/out./file`；README 示例依赖路径末尾 `/`，才碰巧变为 `/path/out/./file`。

应改用 `os.path.join()` 或 `pathlib.Path`。

### 14.6 失败分支引用未定义变量

若 plan 不是顺序流：

```python
failed_plan_tasks.append(cur_task_id)
```

当前文件未定义 `failed_plan_tasks`，会再触发 `NameError`，掩盖原始 plan 问题。

### 14.7 `debug_completed_module()` 有返回类型错误

该非常用函数执行：

```python
task_completed_results = validate_correct_parse(response)
```

返回是字符串 `Pass/Failed`，但随后按：

```python
task_completed_results[-1]["task_output"]
```

访问，类型不匹配。README 主流程不走这条分支，但“只调试已有代码”功能当前不可直接信任。

### 14.8 编译器有 warning 也被当成失败

工具通过 `check_output(..., stderr=STDOUT)` 获取所有编译输出，只要输出行数非零就进入 `Compiled Failed Report`。

所以无害 warning 也会阻止继续仿真。

### 14.9 编译错误行解析脆弱

正则：

```python
'sv\:[\d+]'
```

只针对带 `.sv:<digit>` 的文本；错误行索引在 syntax tool 与 simulation tool 还分别有减一/不减一差异。某些 Icarus 信息格式可能无法关联到 generated module，甚至触发行越界。

### 14.10 功能日志格式是硬依赖

`check_functionality()` 找不到两种 mismatch 行时执行：

```python
assert(mismatches is not None)
```

自定义 testbench 即使返回其他清晰 pass/fail 文本，也会直接中断。

### 14.11 VCD 路径不并发安全

testbench 把 `wave.vcd` 写到 Python 当前目录；simulator 运行后再移动到固定：

```text
<workdir>/wave.vcd
```

同一进程工作目录并行跑多题时可能互相覆盖。论文流程当前也是顺序运行，回避了并发问题。

### 14.12 AST cache 标志没有更新

`waveform_trace_tool()` 判断：

```python
if self.cur_graph_verilog != self.completed_verilog:
    self.graph_tracer = DebugGraph(...)
```

但重建后没有把 `cur_graph_verilog` 更新为 `completed_verilog`。因此每次调用 waveform trace 都会重建 AST 图，缓存没有实际生效。

### 14.13 波形时间单位标签硬编码为 ns

工具表头和提示固定写：

```text
time(ns)
clock cycle is 10ns
```

本地 AND 门 benchmark 声明：

```verilog
`timescale 1 ps/1 ps
```

simulation 日志也写 `20`、`1096 ps`。工具却把 DataFrame index 标成 ns。调试值本身可用，但单位标签不可靠，应从 VCD timescale/testbench 自动读取。

### 14.14 testbench instance 命名是隐式协议

AST-WT 波形映射假设：

```text
good1 = reference module
top_module1 = DUT
tb = top testbench
```

换测试台命名就需要改 analyzer。

### 14.15 `get_input_ports()` 不是完整 Verilog parser

它逐行找包含 `input` 的文本并手工分词。复杂 ANSI/non-ANSI port 声明、多个端口同行、interface、注释和 parameterized 类型都可能误解析。

### 14.16 TCRG 不是语义近邻检索

当前 plan query 必须 description 精确匹配；代码注释也写了 similarity search 是 TODO。LLM 调用工具时若改写 plan 字符串，可能直接查不到节点。

### 14.17 `logic_checker_tool()` 使用 exec

该布尔逻辑工具把字符串拼成 Python 并执行，只用是否含 `rm`/`os` 做很弱的安全检查。当前 VerilogCoder 主路径没有注册它，但如果以后开放给不可信 Agent 输入，不应直接使用。

### 14.18 依赖版本和 Python 版本冲突风险

README 指定 Python 3.10.13，setup.py 允许 `<3.13`，并要求 NumPy `<2`。本机为了只跑确定性工具使用现有 Python 3.12/NumPy 2.4.1，因此出现 pandas FutureWarning，但本次功能仍通过。

完整 Agent 复现应严格建 Python 3.10 环境并锁定论文时期依赖。

---

## 15. 如何正确运行

### 15.1 推荐环境

```bash
cd /mnt/d/AI4eda/VerilogCoder
conda create -n verilogcoder python=3.10.13
conda activate verilogcoder
```

先安装仓库包，再补 hardware_agent 所需依赖。README 中两个拼写需要修正。

至少需要：

```text
openai / AutoGen 依赖
pydantic 2.10.1
networkx
matplotlib
pandas
vcdvcd
langchain 0.3.14
langchain_openai 0.2.14
langchain_community 0.3.14
chromadb 0.4.24
sentence_transformers 2.7.0
Pyverilog（仓库已有 vendor copy）
Icarus Verilog
```

### 15.2 配置模型

`OAI_CONFIG_LIST` 格式：

```json
[
  {
    "model": "gpt-4-turbo",
    "api_key": "..."
  }
]
```

不要把真实 key 提交到仓库。

### 15.3 创建目录

```bash
mkdir -p generated_verilog_plans
mkdir -p generated_verilog_code
mkdir -p verilog_tool_tmp
mkdir -p tmp
```

传给当前代码时保留尾 `/`，或先修复路径拼接。

### 15.4 选择任务

当前需要编辑：

```python
user_task_ids = {'zero'}
```

若想全量：

```python
user_task_ids = set()
```

但 loader 的过滤逻辑对空 set 的 v2 分支当前会跳过所有任务，因为它直接判断：

```python
if task_id not in task_ids:
    continue
```

所以更可靠的方式是先从文件名构造完整 156 task ID set，再传入。

### 15.5 正确数据目录

```bash
python hardware_agent/examples/VerilogCoder/run_verilog_coder.py \
  --generate_plan_dir hardware_agent/examples/VerilogCoder/verilog-eval-v2/plans/ \
  --generate_verilog_dir hardware_agent/examples/VerilogCoder/verilog-eval-v2/plan_output/ \
  --verilog_tmp_dir verilog_tool_tmp/ \
  --verilog_example_dir hardware_agent/examples/VerilogCoder/verilog-eval-v2/dataset_dumpall/
```

全量复现前不要覆盖作者保存的 `plans/` 和 `plan_output/`；应使用新的 timestamped 输出目录。

---

## 16. 真正重跑论文生成阶段需要记录什么

每题至少保存：

```text
task id
Git commit
dataset hash
model exact ID / endpoint
temperature / top_p
每个 Agent 的 chat history
每次 tool call 输入和输出
TCRG JSON
networkx_kg.json
rough plan / enriched plan
每个 subtask 的完整 RTL
最终 RTL
Icarus version
pass/fail/mismatch
input/output tokens
API cost and price date
wall time
failure category
```

特别需要区分：

- Planner LLM calls；
- entity extraction calls；
- KG node-ID calls；
- KG relation classification calls；
- retrieval Agent calls；
- Code Agent calls；
- Debug Agent calls；
- simulator calls；
- AST-WT calls。

论文报告总 token 13 倍，若不拆分就很难知道代价主要来自建图、写代码还是修复。

---

## 17. 与 AutoChip 的直接对比

| 维度 | AutoChip | VerilogCoder |
|---|---|---|
| 规划 | 无显式任务图 | TCRG enriched 顺序计划 |
| 每轮候选 | k 个，rank 后取最好 | 当前版本单一 RTL 持续修改 |
| 功能反馈 | mismatch 比例 + 原日志 | mismatch + AST 依赖 + 波形表 |
| 搜索 | greedy multi-sample | 多 Agent 对话/工具循环 |
| 最终选择 | 历史最高 rank | 最近一次工具验证成功的 RTL |
| testbench | 必需 | 必需 |
| 模型组合 | 可按 depth 切模型 | 各 Agent 阶段可配模型 |
| 代码复杂度 | 较低 | 高 |
| 可解释性 | rank 清楚 | plan/AST trace 更丰富 |
| 论文成本 | 比较 token/USD Pareto | 报告约 13× token baseline |

组会可以把 AutoChip 当基础闭环，把 VerilogCoder 当“加入结构化规划和结构化调试”的增强系统。

---

## 18. 组会分享建议

### 18.1 一句话

> VerilogCoder 用 TCRG 把规格里的信号、转移和示例挂到具体编码子任务上，再用 AST-WT 从错误输出沿 RTL 依赖反向取波形，使多 Agent 能同时减少计划遗漏和功能调试盲目性。

### 18.2 四张图的顺序

1. Figure 1：为什么普通规划和原始 mismatch 不够；
2. Figure 2：TCRG Planner、Code Agent、Debug Agent 总体流；
3. Figure 4：仿真失败 -> AST-WT -> 初始化修复 -> 通过；
4. Table 2/Figure 5：规划与工具的消融和题型差异。

### 18.3 最值得讨论的点

- TCRG 调用大量 LLM 建图，是否可用确定性 parser 代替一部分？
- 既然最终执行强制顺序链，为什么还需要通用 DAG 管理器？
- AST-WT 默认返回完整 DUT，结构化信号筛选到底节省了多少 token？
- 工具依赖 golden testbench 和 RefModule，是否属于 benchmark-visible feedback？
- 94.2% 与 13× token 的性价比如何？
- 对自定义 testbench instance 名、timescale、多模块工程能否泛化？
- 失败 9 题是规划、模型、工具还是上下文上限导致？仓库没有完整失败聊天可直接归因。

### 18.4 不应夸大的结论

不要说：

- 94.2% 的生成过程已在本机重新跑完；
- TCRG 是从大型外部代码库检索；
- AST-WT 能自动修 bug，它只是给 Agent 结构化证据；
- 当前执行支持并行 DAG 子任务；
- 无 testbench 也能判断正确；
- 已覆盖综合、PPA、formal 或多模块 SoC；
- 13× token 的高准确率没有代价。

---

## 19. 最终评价

### 优点

- 规划和调试两个痛点都给出明确机制；
- TCRG 让子任务获得局部电路语义；
- AST-WT 对 mismatch 根因提供结构和波形双证据；
- 论文有完整 2×2 消融；
- 156 题计划与 147 个成功 RTL 已开源保存；
- 本地可全量重验 147 个结果；
- 核心 AST-WT 可在不调用 API 时独立运行。

### 局限

- 依赖 golden testbench 和 reference module；
- Agent token 约 baseline 的 13 倍；
- TCRG 建图本身包含大量 LLM 关系判断；
- 当前任务图实际是顺序链；
- 软件环境、路径和 README 有多处可复现性问题；
- 波形工具依赖 VerilogEval 命名和输出格式；
- 时间单位、并发 VCD、cache 标志等实现需要修复；
- 没有综合/PPA/formal 闭环。

### 复现判定

| 项目 | 状态 |
|---|---|
| 本地论文 | 已归档、逐页核对 |
| 本地代码 | 已核对到类/函数调用链 |
| 数据集 | 156 prompt/ref/test 齐全 |
| TCRG 最终计划 | 156/156 可解析，全部顺序依赖 |
| 官方最终 RTL | 147 常规成功文件 |
| 147 个 RTL 本地再验证 | 147/147 编译、仿真、0 mismatch |
| `147/156=94.2%` | 已本地核算 |
| Syntax/Simulator 工具 | 已实跑 |
| AST-WT | 已实跑并得到正确依赖链 |
| GPT-4 Turbo/Llama3 生成 | 本次未重跑 |
| 论文 token/平均 calls | 本次未重跑 |
| 当前等级 | B+ |

VerilogCoder 是目前这批 RTL Agent 论文中非常值得分享的一篇：论文创新点与代码工具能一一对应，核心工具也可以从商业模型中剥离出来单独验证。它最有价值的启发不是简单堆更多 Agent，而是把 EDA 反馈加工成“当前错误输出的依赖锥 + 局部波形证据”，让模型看到更接近工程师调试时真正使用的信息。

---

## 20. P7 组件一句话角色

| 组件 | 一句话角色 |
|---|---|
| `TaskPlanAgent` / `plan_agent` | 把自然语言规格拆分为带信号、状态转移和示例的细粒度子任务计划。 |
| `KnowledgeGraphToolKits` | 为当前题目构建并检索 Task and Circuit Relation Graph，给每个子任务附加相关电路语义。 |
| `verilog_complete_agent` | 按顺序子任务逐步写 RTL，并在 GroupChat 中由验证助手检查语法。 |
| `verilog_simulation_tool()` | 调用 Icarus 编译并运行 vvp，把 mismatch 信息送回 Debug Agent。 |
| `waveform_trace_tool()` / `DebugGraph` | 从首个失配输出沿 AST 反向追踪 RVALUE 依赖，生成 DUT/REF 对照波形表。 |

---

## 21. 讨论问题

1. TCRG 建图需要大量 LLM 调用判断 Plan/Signal/Transition/Example 之间的关系，是否可以用确定性 parser 或规则系统替代部分关系抽取以降低成本？
2. AST-WT 默认把整个 DUT 送回 Agent，若只返回 traced signal 的局部切片，是否仍能维持 94.2% 的修复成功率并减少 token？
3. 当前 `validate_correct_parse()` 只在聊天记录里找成功标记，没有重跑仿真，这种“文本级成功判定”在 Agent 自我欺骗时会出现什么风险？

