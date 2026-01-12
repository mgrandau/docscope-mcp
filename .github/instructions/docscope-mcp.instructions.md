---
applyTo: "**"
---

# DocScope MCP - Project Rules

Python 3.13+ MCP server for doc quality analysis. Supports: Python (AST), C#, VB.NET, VB6, C/C++ (regex).

## SOLID

| Principle | Rule |
| --------- | ---- |
| SRP | `server.py`=protocol, `routing.py`=detection, `analyzers/*`=parsing, `models/*`=data |
| OCP | New lang: create `analyzers/<lang>/analyzer.py`, register in `routing.py:ANALYZER_MAP` |
| LSP | All analyzers interchangeable via `BaseAnalyzer` Protocol |
| ISP | Protocol: `analyze()`, `get_language()`, `assess_docstring_quality()`, `calculate_priority()` |
| DIP | Depend on `BaseAnalyzer` Protocol, use `get_analyzer()` factory, inject `AnalysisConfig` |

## Python Rules

**Types**: Complete annotations required. Use `list[str]`, `dict[str, Any]`, `X | None`, `X | Y`.

**Docstrings**: Google style. All public functions need: summary, Args, Returns, Raises, Example.

**Prefer**: comprehensions, `pathlib.Path`, context managers, `dataclass`/`TypedDict`, f-strings, `enumerate()`, `any()`/`all()`.

**Avoid**: bare `except:`, mutable defaults, global state, nesting >3 levels, magic numbers.

**Errors**: Specific exceptions with context. Return `[{"error": "..."}]` for recoverable failures.

## Documentation

Over-document for AI context windows. Keep comments adjacent to relevant code. Each module self-contained with module/class/method docstrings.

Package READMEs: overview table, code layout, public API, dependencies, invariants, AI task map.

## Quality

- Tests: 80%+ coverage, `test_<module>.py`, pytest fixtures, parametrize, edge cases
- Lint: `ruff`, `mypy --strict`, `bandit`. Run: `pdm run check-all`

## Markdown Rules

**Always**: blank line before/after headings, tables, lists, code blocks. Specify language on fenced blocks.

**Tables**: spaces around pipes in separator row (`| --- |` not `|---|`).

**Example**:

    ## Heading

    | Col | Col |
    | --- | --- |
    | val | val |

    - item

    ```python
    code
    ```

## New Analyzer Checklist

1. `analyzers/<lang>/__init__.py` - export class
2. `analyzers/<lang>/analyzer.py` - implement `BaseAnalyzer`
3. `routing.py` - add to `EXTENSION_MAP` + `ANALYZER_MAP`
4. `analyzers/__init__.py` - add exports
5. `tests/test_analyzer_<lang>.py`
6. Update READMEs

## Security Limits

| Limit | Value |
| ----- | ----- |
| Code size | 5MB |
| AST depth | 100 |
| Parse timeout | 5s |
| Path length | 4096 |
| Null bytes | Forbidden |

`PathSecurityValidator`: blocks traversal (`../`), symlink escapes, boundary violations.

## Result Schema

```python
{"function_name": str, "line_number": int, "file_path": str, "current_docstring": str,
 "quality_assessment": {"quality": "poor|basic|good|excellent", "score": 0.0-1.0, "missing": [str]},
 "priority": int}  # 0-13+
```

## Git

Commits: `feat:|fix:|docs:|refactor:|test:|chore:` + description. Branches: `main`, `feature/<x>`, `fix/<x>`.
