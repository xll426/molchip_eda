#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""定位「独立公式下方缺少符号解释」告警对应的真实文件行号。

用法： python3 _locate.py <md 文件> [...]
"""
import re
import sys

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from _校验 import strip_code_blocks   # noqa: E402


def main():
    for path in sys.argv[1:]:
        with open(path, encoding='utf-8') as f:
            raw = f.read()
        body, _ = strip_code_blocks(raw)
        lines = raw.split('\n')
        for m in re.finditer(r'\n\$\$\n(.*?)\n\$\$\n(.{0,300})', body, flags=re.S):
            formula, after = m.group(1), m.group(2)
            bare = re.sub(r'\\(?:text|mathrm|mbox|operatorname)\{[^}]*\}', '', formula)
            bare = re.sub(r'\\[A-Za-z]+', '', bare)
            if not set(re.findall(r'[A-Za-z]', bare)):
                continue
            if re.search(r'^\s*-\s+', after, flags=re.M) or '$' in after:
                continue
            # 用公式首行在原文里反查真实行号
            key = formula.split('\n')[0].strip()
            real = next((i for i, ln in enumerate(lines, 1) if ln.strip() == key), None)
            print(f'\n--- {path}  真实行号 L{real}')
            print('公式：', formula.replace('\n', ' ⏎ ')[:160])
            print('后文：', after.replace('\n', ' ⏎ ')[:160])


if __name__ == '__main__':
    main()
