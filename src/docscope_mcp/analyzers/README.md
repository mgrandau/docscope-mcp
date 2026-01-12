# DocScope Analyzers Package

Language-specific documentation analyzers for the DocScope MCP server.

## Overview

| Analyzer | Language | Parsing | Doc Format |
| --- | --- | --- | --- |
| `PythonAnalyzer` | Python | AST | Google/NumPy docstrings |
| `CSharpAnalyzer` | C# | Regex | XML documentation |
| `VBAnalyzer` | VB.NET | Regex | XML documentation |
| `VB6Analyzer` | VB6 | Regex | Comment blocks |
| `CCppAnalyzer` | C/C++ | Regex | Doxygen |

## Code Layout

```
analyzers/
├── __init__.py          # Package exports
├── base.py              # BaseAnalyzer Protocol
├── priority.py          # PriorityCalculationMixin
├── routing.py           # Language detection & analyzer factory
├── python/
│   ├── __init__.py
│   └── analyzer.py      # AST-based Python analyzer
├── csharp/
│   ├── __init__.py
│   └── analyzer.py      # C# XML doc analyzer
├── vb/
│   ├── __init__.py
│   └── analyzer.py      # VB.NET XML doc analyzer
├── vb6/
│   ├── __init__.py
│   └── analyzer.py      # VB6 comment block analyzer
└── c_cpp/
    ├── __init__.py
    └── analyzer.py      # C/C++ Doxygen analyzer
```

## Public API

### Routing Functions

```python
from docscope_mcp.analyzers import (
    analyze_code,          # Analyze code string with explicit language
    analyze_file,          # Analyze file (auto-detect language)
    detect_language,       # Get language from file extension
    get_analyzer,          # Get analyzer instance for language
    get_analyzer_for_file, # Get analyzer instance for file
    get_supported_extensions,
    is_supported_file,
    SUPPORTED_LANGUAGES,   # ['python', 'csharp', 'vb', 'vb6', 'c_cpp']
    EXTENSION_MAP,         # {'.py': 'python', '.cs': 'csharp', ...}
)
```

### Analyzer Classes

```python
from docscope_mcp.analyzers import (
    BaseAnalyzer,          # Protocol defining analyzer interface
    PriorityCalculationMixin,  # Shared priority scoring logic
    PythonAnalyzer,
    CSharpAnalyzer,
    VBAnalyzer,
    VB6Analyzer,
    CCppAnalyzer,
)
```

## Dependencies

- `docscope_mcp.models`: `AnalysisConfig`, `FunctionInfo`, `QualityAssessment`
- Python stdlib: `ast` (Python only), `re`, `logging`

## Invariants

1. All analyzers implement `BaseAnalyzer` Protocol
2. All analyzers inherit from `PriorityCalculationMixin` for consistent priority scoring
3. Results sorted by priority descending (highest priority first)
4. Empty list returned when all functions have excellent documentation
5. Error dict `[{"error": "message"}]` returned on failure

## Adding a New Analyzer

1. Create `analyzers/<lang>/__init__.py` - export analyzer class
2. Create `analyzers/<lang>/analyzer.py`:
   - Inherit from `PriorityCalculationMixin`
   - Implement `analyze()`, `get_language()`, `assess_docstring_quality()`, `calculate_priority()`
3. Update `routing.py`:
   - Add extensions to `EXTENSION_MAP`
   - Add language to `ANALYZER_MAP`
4. Update `analyzers/__init__.py` - add exports
5. Create `tests/test_analyzer_<lang>.py`
6. Update this README

## AI Task Map

| Task | Start Here |
| --- | --- |
| Add new language | `routing.py` → new `<lang>/analyzer.py` |
| Modify quality scoring | `priority.py` or analyzer's `assess_docstring_quality()` |
| Change priority algorithm | `priority.py` (`PriorityCalculationMixin`) |
| Add file extension | `routing.py` `EXTENSION_MAP` |
| Customize thresholds | `models/quality.py` `QualityThresholds` |
