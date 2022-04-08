#!/usr/bin/env python3

import ast
import sys

path = sys.argv[1]
parsed = ast.parse(open(path).read())
for node in parsed.body:
    if not isinstance(node, ast.Expr):
        continue
    if not isinstance(node.value, ast.Call):
        continue
    if node.value.func.id != "setup":
        continue
    for keyword in node.value.keywords:
        if keyword.arg == "install_requires":
            requirements = ast.literal_eval(keyword.value)
            print("\n".join(requirements))

