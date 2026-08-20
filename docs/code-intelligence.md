# Code Intelligence

RHD code intelligence is read-only and never executes repository code.

Current implemented foundation:

- bounded source tree scan
- language detection for Python, JavaScript, TypeScript, Java, C, C++, and Go extensions
- ignored directories such as `.git`, `node_modules`, `vendor`, `dist`, `build`, `coverage`, and virtual environments
- file-count, total-byte, and per-file limits
- Python AST symbol extraction
- lightweight regex symbol extraction for common non-Python files
- static file features such as size, line count, functions, classes, imports, test-file flag, and comment lines
- local graph construction for Repository -> File -> Symbol
- cautious root-cause hypotheses that report `INSUFFICIENT_EVIDENCE` when no source relationship is found

This is a foundation for Code-RAG, change-impact analysis, test advice, and patch advice. It is not a complete whole-program analyzer.
