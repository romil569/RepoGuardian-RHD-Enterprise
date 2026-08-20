from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import ast
import re

from app.core.config import settings
from app.platform.stores import LocalGraphStore

IGNORED_DIRS = {".git", "node_modules", "vendor", "dist", "build", "coverage", ".venv", "venv", "__pycache__"}
BINARY_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".tar", ".gz", ".exe", ".dll", ".so"}
LANGUAGE_BY_EXTENSION = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".c": "C",
    ".h": "C/C++",
    ".cpp": "C++",
    ".cc": "C++",
    ".go": "Go",
}


@dataclass(frozen=True)
class CodeSymbol:
    repository_id: int
    file_path: str
    language: str
    symbol_name: str
    symbol_type: str
    start_line: int
    end_line: int


@dataclass(frozen=True)
class CodeFileFeatures:
    file_path: str
    language: str
    size_bytes: int
    line_count: int
    function_count: int
    class_count: int
    imports: int
    test_file: bool
    comment_lines: int


def detect_language(path: Path) -> str | None:
    return LANGUAGE_BY_EXTENSION.get(path.suffix.lower())


def iter_source_files(root: Path) -> list[Path]:
    files: list[Path] = []
    total_bytes = 0
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in IGNORED_DIRS for part in path.parts):
            continue
        if path.suffix.lower() in BINARY_EXTENSIONS:
            continue
        if detect_language(path) is None:
            continue
        size = path.stat().st_size
        if size > settings.max_code_file_bytes:
            continue
        if total_bytes + size > settings.max_initial_code_bytes:
            break
        files.append(path)
        total_bytes += size
        if len(files) >= settings.max_initial_code_files:
            break
    return files


def extract_python_symbols(repository_id: int, relative_path: str, text: str) -> list[CodeSymbol]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    symbols: list[CodeSymbol] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            symbols.append(CodeSymbol(repository_id, relative_path, "Python", node.name, "class", node.lineno, getattr(node, "end_lineno", node.lineno)))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.append(CodeSymbol(repository_id, relative_path, "Python", node.name, "function", node.lineno, getattr(node, "end_lineno", node.lineno)))
    return symbols


def extract_regex_symbols(repository_id: int, relative_path: str, language: str, text: str) -> list[CodeSymbol]:
    symbols: list[CodeSymbol] = []
    for index, line in enumerate(text.splitlines(), start=1):
        function_match = re.search(r"\b(function|func)\s+([A-Za-z_][A-Za-z0-9_]*)|([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\([^)]*\)\s*=>", line)
        class_match = re.search(r"\bclass\s+([A-Za-z_][A-Za-z0-9_]*)", line)
        if class_match:
            symbols.append(CodeSymbol(repository_id, relative_path, language, class_match.group(1), "class", index, index))
        if function_match:
            name = function_match.group(2) or function_match.group(3)
            if name:
                symbols.append(CodeSymbol(repository_id, relative_path, language, name, "function", index, index))
    return symbols


def file_features(relative_path: str, language: str, text: str, size_bytes: int, symbols: list[CodeSymbol]) -> CodeFileFeatures:
    lines = text.splitlines()
    comment_prefix = "#" if language == "Python" else "//"
    return CodeFileFeatures(
        file_path=relative_path,
        language=language,
        size_bytes=size_bytes,
        line_count=len(lines),
        function_count=sum(1 for symbol in symbols if symbol.symbol_type == "function"),
        class_count=sum(1 for symbol in symbols if symbol.symbol_type == "class"),
        imports=sum(1 for line in lines if line.strip().startswith(("import ", "from ", "require(", "import{", "import {"))),
        test_file="test" in Path(relative_path).name.lower() or relative_path.lower().endswith((".spec.ts", ".test.ts", ".spec.js", ".test.js")),
        comment_lines=sum(1 for line in lines if line.strip().startswith(comment_prefix)),
    )


def analyze_source_tree(repository_id: int, root: Path) -> dict[str, object]:
    files = iter_source_files(root)
    symbols: list[CodeSymbol] = []
    features: list[CodeFileFeatures] = []
    for path in files:
        language = detect_language(path)
        if not language:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        relative_path = str(path.relative_to(root)).replace("\\", "/")
        extracted = extract_python_symbols(repository_id, relative_path, text) if language == "Python" else extract_regex_symbols(repository_id, relative_path, language, text)
        symbols.extend(extracted)
        features.append(file_features(relative_path, language, text, path.stat().st_size, extracted))
    return {
        "scan_scope": {
            "files_scanned": len(files),
            "max_files": settings.max_initial_code_files,
            "bounded": len(files) >= settings.max_initial_code_files,
        },
        "languages": sorted({feature.language for feature in features}),
        "symbols": [symbol.__dict__ for symbol in symbols],
        "features": [feature.__dict__ for feature in features],
    }


def build_code_graph(repository_id: int, analysis: dict[str, object]) -> LocalGraphStore:
    graph = LocalGraphStore()
    repo_node = f"repo:{repository_id}"
    graph.add_node(repo_node, ["Repository"], {"repository_id": repository_id})
    for feature in analysis.get("features", []):
        if not isinstance(feature, dict):
            continue
        file_node = f"file:{repository_id}:{feature['file_path']}"
        graph.add_node(file_node, ["File"], feature)
        graph.add_edge(repo_node, file_node, "CONTAINS")
    for symbol in analysis.get("symbols", []):
        if not isinstance(symbol, dict):
            continue
        symbol_node = f"symbol:{repository_id}:{symbol['file_path']}:{symbol['symbol_name']}"
        graph.add_node(symbol_node, ["Symbol"], symbol)
        graph.add_edge(f"file:{repository_id}:{symbol['file_path']}", symbol_node, "DEFINES")
    return graph


def root_cause_hypotheses(issue_text: str, code_analysis: dict[str, object], limit: int = 3) -> list[dict[str, object]]:
    terms = {token.lower() for token in re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", issue_text)}
    candidates = []
    for feature in code_analysis.get("features", []):
        if not isinstance(feature, dict):
            continue
        haystack = str(feature["file_path"]).lower()
        overlap = sorted(term for term in terms if term in haystack)
        if overlap:
            candidates.append({"hypothesis": f"{feature['file_path']} may be related to the issue terms.", "score": min(0.9, 0.35 + len(overlap) * 0.12), "evidence": overlap, "confidence": "Medium"})
    for symbol in code_analysis.get("symbols", []):
        if not isinstance(symbol, dict):
            continue
        haystack = f"{symbol['symbol_name']} {symbol['file_path']}".lower()
        overlap = sorted(term for term in terms if term in haystack)
        if overlap:
            candidates.append({"hypothesis": f"{symbol['symbol_name']} in {symbol['file_path']} may be related to the issue terms.", "score": min(0.92, 0.45 + len(overlap) * 0.14), "evidence": overlap, "confidence": "Medium"})
    return sorted(candidates, key=lambda item: item["score"], reverse=True)[:limit] or [{"hypothesis": "INSUFFICIENT_EVIDENCE", "score": 0.0, "evidence": [], "confidence": "Low"}]
