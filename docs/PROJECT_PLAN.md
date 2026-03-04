# Project Plan — docscope-mcp

This is a **historical record** of what was actually built, when, and why. For the philosophy and design intent behind this project, see [🧭 Intent](../README.md#-intent) in the README.

Current state: **v1.1.007** — 5 language analyzers, CLI + MCP interfaces, 6 open issues (regex false positives).

---

## Phase 1: Foundation (2025-12-01 → 2025-12-13)

**Goal:** Build an MCP server that can analyze Python documentation quality and surface the worst gaps — accurate enough to be useful, fast enough for interactive use.

Built the core architecture in ~2 weeks: MCP server with JSON-RPC 2.0, Python AST analyzer, quality scoring engine, priority calculation, security protections, CLI installer, and full test suite.

| Date | Work |
| ---- | ---- |
| 2025-12-01 | Initial development release (v0.1.0) |
| 2025-12-11 | Core models, server, mock filesystem, CLI, prompts, CI, v1.0.0 |
| 2025-12-12–13 | Code refactoring and cleanup |

**Key decisions:**

- MCP server over standalone CLI — analysis happens in the conversation flow, not a separate workflow
- AST parsing for Python — `ast.get_docstring()` is free and accurate
- Protocol-based `BaseAnalyzer` — structural typing, no inheritance coupling
- Security limits from day one — 5MB code size, 100 AST depth, 5s timeout, path traversal protection
- Architecture documentation with AI-accessibility maps

**Risk posture:** Low — single developer, Python-only, proving the concept works.

**Design discussions (journal):**

- [2025-12-11](journal/2025-12-11.md) — Origin story: why MCP over CLI-only (rejected context-switching), AST vs regex (use AST when it's free), Protocol over ABC, security limits rationale

---

## Phase 2: Multi-Language Support (2026-01-11 → 2026-01-24)

**Goal:** Extend analysis to the languages that actually matter for the legacy codebase — C#, VB.NET, VB6, C/C++ — without adding external dependencies.

Added 4 regex-based analyzers, extracted shared logic into mixins (~800 lines of dedup), added CLI `analyze` command, and dealt with the first wave of regex false positives.

| Date | Work | Issues |
| ---- | ---- | ------ |
| 2026-01-11 | Comprehensive test suite for language detection and analyzers | — |
| 2026-01-12 | Multi-language release v1.1.0, utility script improvements | #2, #3, #4, #5 |
| 2026-01-14–19 | C++ and C# regex pattern fixes | — |
| 2026-01-22 | PDM lock cleanup | — |
| 2026-01-24 | CLI `analyze` command, prompt templates, VB6 comment fix | #6, #7, #8 |

**Issues resolved:** #1 (CLI rename), #2 (quality false negative), #3 (output format), #4–#5 (C# regex backtracking), #6 (CLI analyze), #7 (multi-language prompts), #8 (VB6 comment false positives)

**Intent evolution:** Phase 2 exposed a fundamental tradeoff: **regex parsing has a ceiling.** The zero-dependency constraint means no external AST libraries, which means regex for non-Python languages, which means false positives on comments, macros, and preprocessor directives. This tradeoff was accepted deliberately — the tool is useful enough with regex to justify shipping, and the false positive issues (#11–#16) are tracked for future improvement.

**Key decisions:**

- Regex for non-Python languages — zero runtime dependencies over parsing accuracy
- `QualityAssessmentMixin` + `PriorityCalculationMixin` — shared scoring, language-specific parsing
- Extension-based language routing — deterministic over content-based guessing
- CLI `analyze` command added for CI/CD pipelines — same engine, different interface

**Risk posture:** High — schema decisions (quality levels, priority scoring, result format) affect every consumer. Regex false positives are a known issue but the tool is still net-positive for doc triage. Mixin refactor touched all 5 analyzers simultaneously.

---

## Phase 3: Polish & Ecosystem (2026-01-26 → 2026-02-20)

**Goal:** Stabilize the release process, add MFC macro filtering, document project conventions, and extend reach via community.

Final polish: CI/CD improvements, badge conventions, project conventions documentation, C++ MFC macro handling, and community links.

| Date | Work | Issues |
| ---- | ---- | ------ |
| 2026-01-26 | Codecov integration (then removed), badge auto-versioning, release docs | — |
| 2026-02-02 | Project conventions, parallel analysis prompts, MFC macro filtering | #9, #10 |
| 2026-02-20 | Discord community link | — |

**Issues resolved:** #9 (MFC macro false positives), #10 (parallel analysis prompt)

**Key decisions:**

- Codecov added then removed — added CI complexity without matching value for a project this size
- MFC macro filtering in C++ analyzer — pattern-based exclusion for `BEGIN_MESSAGE_MAP`, `DECLARE_DYNAMIC`, etc.
- Project conventions in `.github/instructions/` — SOLID principles, new analyzer checklist, security limits reference

**Risk posture:** Medium — additive changes only. MFC filtering reduces false positives without changing the analysis engine. Convention docs prevent regressions from future contributors.

---

## Version History

| Version | Date | Highlights |
| ------- | ---- | ---------- |
| v0.1.0 | 2025-12-01 | Initial development release |
| v1.0.0 | 2025-12-11 | MCP server, Python analyzer, 111 tests, 98% coverage |
| v1.1.0 | 2026-01-12 | C#, VB.NET, VB6, C/C++ analyzers, mixin DRY refactor |
| v1.1.006 | 2026-01-24 | CLI analyze command, VB6 comment fix |
| **v1.1.007** | **2026-02-02** | **MFC macro filtering, project conventions** |

---

## Roadmap (Open Issues)

| Issue | Description | Category |
| ----- | ----------- | -------- |
| [#11](https://github.com/mgrandau/docscope-mcp/issues/11) | C# false positives for void/parameterless methods | regex accuracy |
| [#12](https://github.com/mgrandau/docscope-mcp/issues/12) | Non-UTF-8 file encoding failures | robustness |
| [#13](https://github.com/mgrandau/docscope-mcp/issues/13) | C# detects commented-out methods | regex accuracy |
| [#14](https://github.com/mgrandau/docscope-mcp/issues/14) | C/C++ detects patterns in comments | regex accuracy |
| [#15](https://github.com/mgrandau/docscope-mcp/issues/15) | C/C++ detects preprocessor macros | regex accuracy |
| [#16](https://github.com/mgrandau/docscope-mcp/issues/16) | C/C++ detects English words in Doxygen comments | regex accuracy |

**Pattern:** 5 of 6 open issues are regex false positives — the known cost of zero-dependency parsing. See [journal 2025-12-11](docs/journal/2025-12-11.md) for the design tradeoff analysis.
