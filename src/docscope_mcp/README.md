# DocScope MCP - Architecture Contract

## 1. Component Overview

| Attribute | Value |
| --------- | ----- |
| **Name** | `docscope_mcp` |
| **Type** | Package (MCP Server) |
| **Responsibility** | Documentation quality analysis via JSON-RPC 2.0 MCP protocol |
| **Language** | Python 3.13+ |
| **Runtime** | stdio transport (spawned by VS Code/Claude Desktop) |
| **State** | Stateless (no persistence between requests) |

### Boundaries

- **Context**: VS Code Copilot, Claude Desktop, MCP-compatible clients
- **Public Surface**: `server.py:DocScopeMCPServer`, `analyzers:get_analyzer_for_file`, all `*Analyzer` classes

### Patterns

- Protocol-based DI (structural typing)
- AST-based analysis (Python), regex-based (C#, VB.NET, VB6, C/C++)
- Multi-criteria quality scoring
- Extension-based language routing

### Entry Points

| Entry | Purpose |
| ----- | ------- |
| `python -m docscope_mcp.server` | Start MCP server (stdio) |
| `docscope-mcp install` | Configure VS Code mcp.json |
| `analyze_file(path)` | Read file, auto-detect, analyze (adds file_path to results) |
| `analyze_code(code, language, file_path)` | Analyze string with explicit language |
| `get_analyzer_for_file(path)` | Get analyzer instance for file extension |
| `*Analyzer.analyze(code)` | Direct API usage (no file_path in results) |

### Key Decisions

| Decision | Rationale | Risk |
| -------- | --------- | ---- |
| Protocol over ABC | Structural typing, no inheritance | Duck typing errors at runtime |
| Auto-detect language | UX - no manual selection needed | Unknown extensions fail |
| AST parsing (Python) | Accurate function extraction | Memory on large files |
| Regex parsing (others) | No external AST libs needed | Less accurate than AST |
| Signal-based timeout | DoS protection | Unix-only (no Windows timeout) |

---

## 2. Code Layout

```text
src/docscope_mcp/
├── __init__.py          # Package exports, version re-export
├── __version__.py       # Version metadata (0.1.0)
├── server.py            # MCP server, JSON-RPC handler
├── cli.py               # CLI: install/uninstall commands
├── filesystem.py        # FS abstraction, path security
├── analyzers/
│   ├── __init__.py      # Re-exports all analyzers and routing
│   ├── base.py          # BaseAnalyzer Protocol definition
│   ├── routing.py       # Language detection, analyzer factory
│   ├── python/
│   │   ├── __init__.py  # Re-exports PythonAnalyzer
│   │   └── analyzer.py  # Python AST analyzer (Google/NumPy docstrings)
│   ├── csharp/
│   │   ├── __init__.py  # Re-exports CSharpAnalyzer
│   │   └── analyzer.py  # C# regex analyzer (XML /// docs)
│   ├── vb/
│   │   ├── __init__.py  # Re-exports VBAnalyzer
│   │   └── analyzer.py  # VB.NET regex analyzer (XML ''' docs)
│   ├── vb6/
│   │   ├── __init__.py  # Re-exports VB6Analyzer
│   │   └── analyzer.py  # VB6 regex analyzer (' comment blocks)
│   └── c_cpp/
│       ├── __init__.py  # Re-exports CCppAnalyzer
│       └── analyzer.py  # C/C++ regex analyzer (Doxygen @/\ commands)
└── models/
    ├── __init__.py      # Aggregates all model exports
    ├── analysis.py      # ArgInfo, FunctionInfo, FunctionAnalysis
    ├── config.py        # AnalysisConfig, DEFAULT_CONFIG
    └── quality.py       # QualityLevel, QualityIndicators, QualityAssessment
```

---

## 3. Public Surface

### Frozen APIs (DO NOT MODIFY without approval)

#### `DocScopeMCPServer`

```python
class DocScopeMCPServer:
    def __init__(config: AnalysisConfig | None, logger: Logger | None) -> None
    async def handle_message(message: dict[str, Any]) -> dict[str, Any]
    async def run() -> None  # stdio event loop
```

**Change Impact**: Breaks MCP protocol compatibility with all clients

#### `BaseAnalyzer` Protocol

```python
class BaseAnalyzer(Protocol):
    def analyze(code: str) -> list[dict[str, Any]]
    def get_language() -> str
    def assess_docstring_quality(docstring, func_name, func_info) -> QualityAssessment
    def calculate_priority(func_info, quality_assessment) -> int
```

**Change Impact**: Breaks all language analyzer implementations

#### Language Analyzers

| Analyzer | Language | Doc Style | Parsing |
| -------- | -------- | --------- | ------- |
| `PythonAnalyzer` | Python | Google/NumPy docstrings | AST |
| `CSharpAnalyzer` | C# | XML `///` comments | Regex |
| `VBAnalyzer` | VB.NET | XML `'''` comments | Regex |
| `VB6Analyzer` | VB6 | `'` comment blocks | Regex |
| `CCppAnalyzer` | C/C++ | Doxygen `@`/`\` | Regex |

**Change Impact**: Breaks MCP tool `analyze_functions`

### Internal APIs

| API | Stability |
| --- | --------- |
| `_validate_code_security()` | internal |
| `_parse_with_timeout()` | internal |
| `_extract_functions_needing_improvement()` | internal |
| `PathSecurityValidator` | internal |

### Data Contracts

**Input** (MCP `tools/call`):

```json
{"code": "str", "file_path": "str", "language": "str?"}
```

- `file_path`: Required - used for auto-detection of language from extension
- `language`: Optional override - if omitted, detected from `file_path` extension

**Output** (per function):

```json
{
  "function_name": "str",
  "line_number": "int",
  "file_path": "str",
  "current_docstring": "str",
  "quality_assessment": {"quality": "poor|basic|good|excellent", "score": "0.0-1.0", "missing": ["str"]},
  "priority": "int (0-13+)"
}
```

---

## 4. Dependencies

### Internal

| Module | Depends On | Required By |
| ------ | ---------- | ----------- |
| `server` | `analyzers.*`, `models` | CLI clients |
| `analyzers.routing` | all `*Analyzer` classes | `server` |
| `analyzers.python` | `models` | `routing` |
| `analyzers.csharp` | `models` | `routing` |
| `analyzers.vb` | `models` | `routing` |
| `analyzers.vb6` | `models` | `routing` |
| `analyzers.cpp` | `models` | `routing` |
| `models` | (none) | All modules |
| `filesystem` | (none) | (testing infra) |
| `cli` | `__version__` | Entry point |

### External

| Package | Purpose |
| ------- | ------- |
| Python stdlib | `ast`, `json`, `asyncio`, `signal`, `logging`, `argparse` |

### IO Boundaries

| Type | Details |
| ---- | ------- |
| stdio | JSON-RPC 2.0 messages (stdin→stdout) |
| filesystem | `cli.py` reads/writes `.vscode/mcp.json` |

---

## 5. Invariants & Errors

### MUST PRESERVE

| Invariant | Threshold | Violation |
| --------- | --------- | --------- |
| Code size limit | 5MB max | Returns error dict |
| AST depth limit | 100 max | Returns error dict |
| Parse timeout | 5s max | Returns error dict |
| File path length | 4096 chars | Raises `ValueError` |
| No null bytes in path | - | Raises `ValueError` |

### Security Constraints

- Path traversal blocked via `PathSecurityValidator`
- Symlink targets validated against workspace boundary
- `../` patterns logged as warnings

### Errors Raised

| Error | When | Handler |
| ----- | ---- | ------- |
| `ValueError` | Path escapes workspace | `validate_path()` |
| `TypeError` | file_path not string | `_validate_file_path()` |
| `TimeoutError` | Parse exceeds timeout | `_parse_with_timeout()` |
| `SyntaxError` | Invalid Python | Caught, returned as error dict |

### Side Effects

- `cli.py`: Writes `.vscode/mcp.json` or `~/.config/Code/User/mcp.json`
- `server.py`: Writes to stdout (JSON-RPC responses)
- Logging to stderr

---

## 6. Usage

### Quick Start

```python
# Analyze a file (auto-detect language, adds file_path to results)
from docscope_mcp.analyzers import analyze_file

results = analyze_file("example.py")
for r in results:
    print(f"{r['function_name']}: priority={r['priority']}")

# Analyze code string with explicit language
from docscope_mcp.analyzers import analyze_code

results = analyze_code(code, language="python", file_path="example.py")

# Direct analyzer usage (internal API - no file_path in results)
from docscope_mcp.analyzers import PythonAnalyzer, CSharpAnalyzer

analyzer = PythonAnalyzer()
results = analyzer.analyze(code)  # No file_path parameter
```

### Configuration

| Env/Config | Default | Purpose |
| ---------- | ------- | ------- |
| `AnalysisConfig.max_code_size` | 5MB | DoS protection |
| `AnalysisConfig.quality_thresholds` | `{excellent: 0.8, good: 0.6, basic: 0.3}` | Score→level mapping |

### Testing

```bash
pytest tests/ -v           # All tests
pytest tests/test_analyzer.py  # Analyzer only
```

### Pitfalls

| Issue | Fix |
| ----- | --- |
| Timeout not working | Windows lacks SIGALRM—timeout skipped |
| Import error in venv | Use `python -m docscope_mcp.server` not script |

---

## 7. AI-Accessibility Map

| Task | Target | Guards | Change Impact |
| ---- | ------ | ------ | ------------- |
| Add language analyzer | `analyzers/<lang>/analyzer.py` | Implement `BaseAnalyzer` Protocol (`analyze(code)` signature) | Register in `routing.py:ANALYZER_MAP` |
| Modify quality scoring | `models/quality.py`, `analyzer.py:_calculate_quality_indicators` | Update thresholds in `config.py` | May change priority rankings |
| Add MCP tool | `server.py:tools`, `handle_message` | Follow JSON-RPC 2.0 | Update tool schema |
| Change security limits | `models/config.py:AnalysisConfig` | Test DoS scenarios | May allow attacks |
| Add file extension | `routing.py:EXTENSION_MAP` | Map to existing language | Affects auto-detection |

---

## 8. Architecture Diagram

```mermaid
%%{init: {'theme': 'neutral'}}%%
flowchart TB
    subgraph Clients
        VSCode[VS Code Copilot]
        Claude[Claude Desktop]
    end

    subgraph docscope_mcp
        Server[server.py<br/>DocScopeMCPServer]
        Routing[routing.py<br/>Language Detection]
        subgraph Analyzers
            Python[PythonAnalyzer<br/>AST]
            CSharp[CSharpAnalyzer<br/>Regex]
            VB[VBAnalyzer<br/>Regex]
            VB6[VB6Analyzer<br/>Regex]
            Cpp[CCppAnalyzer<br/>Regex]
        end
        Models[models/<br/>TypedDicts + Config]
    end

    VSCode -->|stdio JSON-RPC| Server
    Claude -->|stdio JSON-RPC| Server
    Server -->|detect language| Routing
    Routing -->|get analyzer| Analyzers
    Analyzers -->|uses| Models
    Server -->|uses| Models
```

```mermaid
%%{init: {'theme': 'neutral'}}%%
classDiagram
    class BaseAnalyzer {
        <<Protocol>>
        +analyze(code) list
        +get_language() str
        +assess_docstring_quality() QualityAssessment
        +calculate_priority() int
    }

    class PythonAnalyzer {
        +analyze(code) list
    }
    class CSharpAnalyzer {
        +analyze(code) list
    }
    class VBAnalyzer {
        +analyze(code) list
    }
    class VB6Analyzer {
        +analyze(code) list
    }
    class CCppAnalyzer {
        +analyze(code) list
    }

    class DocScopeMCPServer {
        +tools: dict
        +handle_message(message) dict
        +run() None
    }

    BaseAnalyzer <|.. PythonAnalyzer : implements
    BaseAnalyzer <|.. CSharpAnalyzer : implements
    BaseAnalyzer <|.. VBAnalyzer : implements
    BaseAnalyzer <|.. VB6Analyzer : implements
    BaseAnalyzer <|.. CCppAnalyzer : implements
    DocScopeMCPServer --> BaseAnalyzer : uses via routing
```
