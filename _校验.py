#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验 论文深度讲解*.md 是否符合 _合并规范.md。

用法：
    python3 _校验.py            # 校验全部
    python3 _校验.py MAGE ACE   # 只校验指定目录
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

# 骨架必备内容（按「主题」而非固定标题匹配，允许规范授权的标题变体：
# 综述类用 taxonomy / 分类维度替代输入输出与公式；benchmark 类用
# 「Benchmark 构建方法 / 评测协议与打分 / 评测公平性」；跨领域类
# （光子/模拟/PCB/RF）用「本领域流程 vs 数字芯片 17 阶段」对照表。）
REQUIRED_TOPICS = [
    ('一句话定位', r'一句话定位'),
    ('阶段映射', r'阶段映射|17\s*阶段|芯片流程|设计流程映射|领域与设计流程'),
    ('输入/输出', r'输入|输出|分类体系|taxonomy'),
    ('方法/架构/构建', r'方法|架构|模型流程|流程|构建|分类体系|taxonomy'),
    ('公式/判据', r'公式|分类维度|判据|定义|指标'),
    ('训练/实验/评测协议', r'训练|实验|评测协议|打分|评测'),
    ('创新点', r'创新点|贡献'),
    ('缩写表', r'缩写'),
    ('与芯片流程的关系', r'芯片流程|流程的关系|全流程|阶段映射|领域与设计流程|17\s*阶段'),
    ('讨论与局限', r'讨论|局限|公平性|可信度'),
    ('复现信息', r'复现'),
    ('一分钟复述', r'复述|小结|总结'),
]

STAGE_MARKS = '①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰'
UNICODE_MATH = '∑∏∈∉≤≥≠≈∀∃∪∩⊆⊂√∞∇∂×÷±⋅→←↔'


def strip_code_blocks(text):
    """移除 ``` 围栏代码块，返回（去代码后的文本, 代码块列表）。

    按行判定围栏（markdown 的开/闭围栏都必须位于行首，最多 3 空格缩进），
    这样代码块内被引用的行内 ``` 不会导致配对错位。
    占位符保留「这里有实质内容」的信号，避免把「只有一张 ASCII 框图的
    小节」误判为空节。
    """
    blocks, out, cur = [], [], None
    for ln in text.split('\n'):
        if ln.lstrip(' ')[:3] == '```' and len(ln) - len(ln.lstrip(' ')) <= 3:
            if cur is None:            # 开围栏
                cur = [ln]
            else:                      # 闭围栏
                cur.append(ln)
                block = '\n'.join(cur)
                blocks.append(block)
                out.append('[CODEBLOCK]' + 'x' * min(len(block), 200))
                cur = None
            continue
        if cur is not None:
            cur.append(ln)
        else:
            out.append(ln)
    if cur is not None:                # 未闭合，按正文处理（另有围栏配对检查报错）
        out.extend(cur)
    return '\n'.join(out), blocks


def expand_stage_ranges(text):
    """把 ⑭-⑰ / ⑭~⑰ 这类区间记法展开成逐个阶段符号。"""
    def grab(m):
        a, b = STAGE_MARKS.index(m.group(1)), STAGE_MARKS.index(m.group(2))
        return STAGE_MARKS[min(a, b):max(a, b) + 1]
    return re.sub(rf'([{STAGE_MARKS}])\s*[-~—－]\s*([{STAGE_MARKS}])', grab, text)


def check_file(path):
    """返回该文件的问题列表。"""
    problems = []
    with open(path, encoding='utf-8') as f:
        raw = f.read()
    body, code_blocks = strip_code_blocks(raw)
    lines = raw.split('\n')

    # ---- 0. 代码围栏配对（最优先：不配对会吞掉后续整段内容）----
    # 行首围栏必须成对；正文里为了「谈论」围栏而写的 ``` 会破坏配对，
    # 这类应改用 <code>```verilog</code> 转义。
    fence_lines = [i + 1 for i, ln in enumerate(lines) if ln.lstrip().startswith('```')]
    if len(fence_lines) % 2 != 0:
        problems.append(
            f'代码围栏 ``` 数量为奇数（{len(fence_lines)} 个），有未闭合围栏，'
            f'渲染时会吞掉后续内容；行号 {fence_lines}')
    # 行内出现 ``` 且不在围栏内 → 会破坏围栏配对
    # （围栏内的 ``` 是被引用的内容，合法；markdown 闭合围栏必须在行首）
    in_fence = False
    for i, ln in enumerate(lines, 1):
        s = ln.lstrip()
        if s.startswith('```'):
            in_fence = not in_fence
            continue
        if '```' in s and not in_fence:
            problems.append(
                f'L{i}: 正文行内出现 ``` ，会破坏围栏配对，'
                f'应改用 <code>```lang</code> → {s[:60]}')

    # ---- 1. 骨架主题齐全 ----
    headings = re.findall(r'^#{1,3}\s+(.+)$', body, flags=re.M)
    heading_text = '\n'.join(headings)
    for name, pat in REQUIRED_TOPICS:
        if not re.search(pat, heading_text, flags=re.I):
            problems.append(f'缺少骨架主题「{name}」（匹配 /{pat}/）')
    # 顶级章节数量（十二节骨架，benchmark/对比类可以更多）
    top = re.findall(r'^##\s+(.+)$', body, flags=re.M)
    if len(top) < 12:
        problems.append(f'顶级章节仅 {len(top)} 个，骨架要求 ≥12 节')

    # ---- 2. 空节检测：标题后到下一个标题之间实质内容 < 40 字 ----
    parts = re.split(r'^(#{1,3}\s+.+)$', body, flags=re.M)
    for i in range(1, len(parts) - 1, 2):
        title = parts[i].lstrip('# ').strip()
        content = parts[i + 1].strip()
        # 顶级标题（文档标题）和纯容器节允许短
        if len(content) < 40 and not re.match(r'^#{1,2}\s', parts[i]):
            problems.append(f'空节或内容过少：「{title}」（{len(content)} 字）')

    # ---- 3. 公式排版 ----
    # 3a. $$ 必须独占行
    for i, ln in enumerate(lines, 1):
        s = ln.strip()
        if '$$' in s and s != '$$':
            # 允许 $$ 单独成行；其余形式都是违规
            problems.append(f'L{i}: $$ 未独占行 → {s[:70]}')

    # 3b. $$ 前后需空行 + 成对
    dollar_lines = [i for i, ln in enumerate(lines) if ln.strip() == '$$']
    if len(dollar_lines) % 2 != 0:
        problems.append(f'$$ 数量为奇数（{len(dollar_lines)}），公式块未闭合')
    for k, i in enumerate(dollar_lines):
        is_open = (k % 2 == 0)
        if is_open and i > 0 and lines[i - 1].strip() != '':
            problems.append(f'L{i+1}: 公式块开头 $$ 前缺空行')
        if not is_open and i + 1 < len(lines) and lines[i + 1].strip() != '':
            nxt = lines[i + 1].strip()
            # 符号解释列表紧跟是允许的
            if not nxt.startswith('- $'):
                problems.append(f'L{i+1}: 公式块结尾 $$ 后缺空行 → {nxt[:50]}')

    # 3c. 禁用 \begin{align}（不带 ed）
    for m in re.finditer(r'\\begin\{align\}', body):
        ln = body[:m.start()].count('\n') + 1
        problems.append(f'第 ~{ln} 行附近: 禁用 \\begin{{align}}，改用 \\begin{{aligned}} 包在 $$ 内')

    # 3d. 公式内混 Unicode 数学符号 / 中文
    for m in re.finditer(r'\$\$(.*?)\$\$', body, flags=re.S):
        formula = m.group(1)
        ln = body[:m.start()].count('\n') + 1
        bad = [c for c in formula if c in UNICODE_MATH]
        if bad:
            problems.append(f'L~{ln}: 公式内混用 Unicode 数学符号 {"".join(sorted(set(bad)))}，应改 LaTeX')
        # 中文（排除 \text{} 内的）
        cleaned = re.sub(r'\\(?:text|mathrm|mbox)\{[^}]*\}', '', formula)
        cn = re.findall(r'[\u4e00-\u9fff]+', cleaned)
        if cn:
            problems.append(f'L~{ln}: 公式内含中文 {cn[:3]}，应移到符号解释里')

    # 3e. 独立公式下方应有符号解释。
    # 接受多种合法形式：`- $符号$：含义` 列表、「其中 $x$ 是…」散文、
    # 提到公式中出现过的行内符号的散文、或以 - 开头的术语解释列表。
    # 若公式的变量全部包在 \text{}/\mathrm{} 里（自解释命名，如
    # \text{PassRate}），则不强制要求符号表。
    for m in re.finditer(r'\n\$\$\n(.*?)\n\$\$\n(.{0,300})', body, flags=re.S):
        formula, after = m.group(1), m.group(2)
        ln = body[:m.start()].count('\n') + 2

        # 公式里「裸」变量名（不在 \text{}/\mathrm{}/命令名 中的字母）
        bare = re.sub(r'\\(?:text|mathrm|mbox|operatorname)\{[^}]*\}', '', formula)
        bare = re.sub(r'\\[A-Za-z]+', '', bare)          # 去掉 LaTeX 命令
        bare_vars = set(re.findall(r'[A-Za-z]', bare))
        if not bare_vars:
            continue                                      # 自解释公式，跳过

        has_list = re.search(r'^\s*-\s+', after, flags=re.M)
        has_prose_math = '$' in after                     # 散文里引用了行内符号
        if not (has_list or has_prose_math):
            problems.append(
                f'L~{ln}: 独立公式下方缺少符号解释'
                f'（`- $符号$：含义` 列表 或 引用符号的散文说明）')

    # ---- 4. 阶段映射 ----
    # 定位「阶段映射 / 流程对照」那一节（标题措辞允许变体）
    stage_sec = None
    for m in re.finditer(r'^##[ \t]+([^\n]+)\n(.*?)(?=^##[ \t]|\Z)', body, flags=re.M | re.S):
        if re.search(r'阶段映射|17\s*阶段|设计流程|流程映射|流程 vs', m.group(1)):
            stage_sec = m.group(2)
            break
    if stage_sec is None:
        problems.append('找不到「阶段映射 / 流程对照」章节')
    else:
        sec = expand_stage_ranges(stage_sec)
        found = {c for c in STAGE_MARKS if c in sec}
        # 跨领域论文（光子/模拟/PCB/RF/FPGA）允许用「本领域 vs 17 阶段」
        # 对照表替代逐阶段表，此时只要求提到多数阶段并给出定位结论
        is_crossdomain = re.search(r'对比|对照|vs\.?\s*数字|无对应|不适用', sec)
        need = 10 if is_crossdomain else 17
        if len(found) < need:
            missing = ''.join(c for c in STAGE_MARKS if c not in found)
            problems.append(
                f'阶段映射覆盖不足：仅提到 {len(found)}/17 个阶段'
                f'（缺 {missing}）'
                + ('，跨领域对照表也应交代主要阶段的有无' if is_crossdomain else ''))
        if not re.search(r'覆盖率|覆盖\s*[:：]|/17', sec):
            problems.append('阶段映射章节缺少「覆盖率：N/17」之类的定位结论')

    # ---- 5. 历史注释残留 ----
    for tag in ('glm-review', 'kimi-review'):
        if tag in raw:
            problems.append(f'残留历史审阅注释 <!-- {tag} -->')

    # ---- 6. 具体例子（代码块）----
    if len(code_blocks) < 2:
        problems.append(f'代码块仅 {len(code_blocks)} 个，第 3 节缺少具体输入/输出例子')

    # ---- 7. 套话 ----
    for phrase in ('近年来', '随着人工智能的发展', '具有重要意义', '具有重要的意义'):
        if phrase in body:
            problems.append(f'含套话「{phrase}」')

    # ---- 8. 重复的一句话定位 ----
    if len(re.findall(r'一句话定位', heading_text)) > 1:
        problems.append('「一句话定位」标题出现多次，应只保留第 1 节')

    return problems


def main():
    targets = sys.argv[1:]
    dirs = sorted(
        d for d in os.listdir(ROOT)
        if os.path.isdir(os.path.join(ROOT, d)) and not d.startswith(('.', '_'))
    )
    if targets:
        dirs = [d for d in dirs if d in targets]

    total_files = 0
    total_problems = 0
    clean = []

    for d in dirs:
        dpath = os.path.join(ROOT, d)
        files = sorted(f for f in os.listdir(dpath)
                       if f.startswith('论文深度讲解') and f.endswith('.md'))
        if not files:
            # 重复归档目录：README.md 指向正式目录，不需要重复一份正文
            readme = os.path.join(dpath, 'README.md')
            if os.path.exists(readme):
                with open(readme, encoding='utf-8') as fh:
                    if '论文深度讲解.md)' in fh.read():
                        print(f'\n### {d}\n  ○ 重复归档目录，README 指向正式目录（跳过）')
                        continue
            print(f'\n### {d}\n  ✗ 没有 论文深度讲解*.md')
            total_problems += 1
            continue

        # 残留的待删文件
        leftovers = [f for f in os.listdir(dpath)
                     if f.endswith(('_标准化总结.md', '详细总结.md')) or f == '模型梳理.md']

        for f in files:
            total_files += 1
            probs = check_file(os.path.join(dpath, f))
            size = os.path.getsize(os.path.join(dpath, f))
            if probs or leftovers:
                print(f'\n### {d}/{f}  ({size:,} B)')
                for p in probs:
                    print(f'  ✗ {p}')
                    total_problems += 1
                for lo in leftovers:
                    print(f'  ✗ 未删除旧文档：{lo}')
                    total_problems += 1
                leftovers = []  # 每目录只报一次
            else:
                clean.append(f'{d}/{f} ({size:,} B)')

    print('\n' + '=' * 60)
    print(f'校验 {total_files} 个文件，{total_problems} 处问题，{len(clean)} 个完全通过')
    if clean:
        print('\n通过的文件：')
        for c in clean:
            print(f'  ✓ {c}')
    return 1 if total_problems else 0


if __name__ == '__main__':
    sys.exit(main())
