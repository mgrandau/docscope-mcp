---
applyTo: "**"
---

# Project Intent & Design

This project follows the [Human-AI Intent Transfer Principles](https://mgrandau.medium.com/human-ai-intent-transfer-principles-b6e7404e3d26?source=friends_link&sk=858917bd3f4a686974ed6b6c9c059ac8) — making documentation quality measurable and triageable.

**Context chain (read in order when making design decisions):**

1. [🧭 Intent](../../README.md#-intent) — project philosophy: documentation quality should be measurable
2. [PROJECT_PLAN.md](../../docs/PROJECT_PLAN.md) — phase goals, risk posture, intent evolution, issue mapping
3. [Journal entries](../../docs/journal/) — design alternatives explored and rejected, with rationale
4. [Architecture](../../src/docscope_mcp/README.md) — component map, invariants, DI contracts, AI-accessibility map
5. [Analyzer architecture](../../src/docscope_mcp/analyzers/README.md) — language-specific analyzer patterns
6. Source code — the implementation

**Core design values (from rejection patterns in the journal):**

- **Zero runtime dependencies** — stdlib only. MCP servers are spawned processes; startup time and install simplicity matter.
- **AST when free, regex otherwise** — Python gets AST (stdlib). Other languages get regex (no external parsers). Accuracy cost is accepted and tracked (#11–#16).
- **Protocol over ABC** — structural typing, no inheritance coupling. `BaseAnalyzer` is a Protocol.
- **Shared scoring, separate parsing** — mixins for quality/priority calculation, individual analyzers for language-specific parsing.
- **Extension-based routing** — deterministic language detection over content-based guessing.
- **MCP + CLI** — interactive analysis in conversations, automated analysis in pipelines. One engine, two interfaces.
- **Security limits on all inputs** — MCP servers accept arbitrary input. Treat them like web servers.

When proposing new features or changes, check the journal for prior art — the alternative you're considering may have already been evaluated and rejected.

# GitHub CLI Quick Reference

Requires: `gh auth status` (authenticated).

## Project Conventions

| Action | Command |
| --- | --- |
| Bug | `gh issue create --label "bug"` |
| Feature | `gh issue create --label "enhancement"` |
| Start work | `gh issue edit N --add-label "in-progress" --add-assignee @me` |
| Submit fix | `gh pr create --title "Fix #N"` (auto-links issue) |
| Merge | `gh pr merge N --squash --delete-branch` |

## Release Process

### Version Badge

The README badge auto-updates from GitHub releases — no manual badge edits needed.

### Release Steps

1. Update version in `src/docscope_mcp/__version__.py`
2. Commit changes: `git commit -am "release: bump version to X.X.X"`
3. Create and push tag: `git tag vX.X.X && git push origin vX.X.X`
4. Create GitHub release with **changelog notes** covering:
   - **Bug Fixes** — issues fixed with brief description
   - **Features** — new functionality added
   - **Documentation** — significant doc improvements
   - Link to full changelog comparison: `https://github.com/mgrandau/docscope-mcp/compare/vPREV...vX.X.X`

### Changelog Requirements

- Every release **must** have human-written changelog notes — do not rely solely on `--generate-notes`
- Reference issue numbers (e.g., "Fixed #9: MFC macro false positives")
- Keep notes concise but meaningful — someone reading them should understand what changed and why
- Also update `CHANGELOG.md` following Keep a Changelog format

## Tips

- `--web`: open in browser
- `--json field1,field2 --jq '...'`: scriptable output
- `gh <cmd> --help`: full options

## Markdown

All markdown files must pass linting. Fix errors before committing.
