import ast
from pathlib import Path

files_to_inspect = [
    'drywall_detection/classification/classifier.py',
    'drywall_detection/pipeline/fusion.py',
    'drywall_detection/pipeline/router.py',
    'drywall_detection/pipeline/annotate.py',
    'drywall_detection/vector/spatial_matcher.py',
]

print("=== AST ANALYSIS: CHECKING FOR DUMMY / CONSTANT RETURN FUNCTIONS ===")
for fpath in files_to_inspect:
    p = Path(fpath)
    tree = ast.parse(p.read_text(encoding='utf-8'), filename=fpath)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Check if function body is only 'pass', 'return <constant>', or 'raise NotImplementedError'
            body = [stmt for stmt in node.body if not (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant))]
            if len(body) == 1:
                stmt = body[0]
                if isinstance(stmt, ast.Pass):
                    print(f"[FACADE] {fpath}:{node.lineno} Function '{node.name}' has only 'pass'")
                elif isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Constant):
                    # Check if it's not a trivial boolean/None check
                    print(f"[FACADE / CONSTANT RETURN] {fpath}:{node.lineno} Function '{node.name}' returns constant {stmt.value.value}")
                elif isinstance(stmt, ast.Raise) and isinstance(stmt.exc, ast.Name) and stmt.exc.id == 'NotImplementedError':
                    print(f"[UNIMPLEMENTED] {fpath}:{node.lineno} Function '{node.name}' raises NotImplementedError")

print("AST facade analysis completed.")
