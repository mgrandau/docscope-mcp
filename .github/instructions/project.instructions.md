---
applyTo: "**"
---

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

## Release

```bash
# Update src/docscope_mcp/__version__.py, then:
git commit -am "Bump to X.X.X" && git tag vX.X.X && git push origin vX.X.X
gh release create vX.X.X --title "vX.X.X" --generate-notes
```

## Tips

- `--web`: open in browser
- `--json field1,field2 --jq '...'`: scriptable output
- `gh <cmd> --help`: full options

## Markdown

All markdown files must pass linting. Fix errors before committing.
