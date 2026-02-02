# Parallel Source Documentation (Supervisor/Worker)

## Quality: EXCELLENT ONLY
⚠️ "Good" NOT acceptable. Excellent requires: Purpose, Parameters, Returns, **Raises**, **Example**, Business Context, See Also
**Note:** Always include all sections. Use "None" for void returns and parameterless methods.

## ⚠️ CRITICAL: Document ALL Files and Functions
**ALL files and functions require full documentation to add discoverable context.**
- **NO SKIPPING** - Document every file regardless of type (including `.Designer.cs`, auto-generated, etc.)
- Documentation enables AI/search discoverability of legacy code patterns and business logic
- Even auto-generated code contains domain knowledge worth preserving
- Workers MUST document, not decide to skip based on file origin

## Architecture
**Supervisor:** Routes files, decides format, collects artifacts | **Workers (4):** ONE file each, artifacts only, no narrative

## Workflow

### Step 1: Analyze State
Run analyzer directly:
```powershell
.venv\Scripts\python.exe utils/analyze_all_source.py --pretty --output analysis_report.json
```

Read `analysis_report.json` → check `summary.total_functions_to_improve`
- If `0`: ✅ Done!
- If `> 0`: Continue to Step 2

### Step 2: Select 4 Files from JSON
Read `analysis_report.json` → pick any 4 files where `functions_needing_improvement > 0`

JSON structure:
```json
{
  "summary": { "total_functions_to_improve": N },
  "files": [
    { "file": "path", "functions_needing_improvement": N, "functions": [...] }
  ]
}
```

### Step 3: Format by Extension
| Ext | Format |
| --- | --- |
| `.bas/.frm/.cls` | VB6 comment block (`'***`) |
| `.cs` | XML doc (`///`) |
| `.c/.h` | Doxygen (`/** */`) |

### Step 4: Launch 4 Workers (runSubagent parallel)

---

## WORKER PROMPT TEMPLATE

```
## WORKER - EXCELLENT QUALITY MODE
Process ONE file, return artifacts only. **100% EXCELLENT required.**

### FILE: [PATH] Type: [EXT]

### TEMPLATES (use based on extension)

**VB6 (.bas/.frm/.cls):**
'******************************************************************************
' Sub/Function: [NAME]
'******************************************************************************
' Purpose: [summary]
' Parameters: @param [Name] - [ByVal/ByRef] [Type]. [desc] (or "None" if no params)
' Returns: [Type] - [desc] (or "None" for Sub/void)
' Raises: [Error] - [condition] (or "None")
' Example: [1-2 line usage]
' Business Context: [XRF workflow relevance]
' See Also: [related] (or "None")
'******************************************************************************

**C# (.cs):**
/// <summary>[purpose]</summary>
/// <param name="p">[desc]</param>        <!-- Use "None" comment if no parameters -->
/// <returns>[desc or "None" for void]</returns>
/// <exception cref="T">[condition]</exception>
/// <example><code>[usage]</code></example>
/// <remarks><para><b>Business Context:</b> [XRF]</para><para><b>See Also:</b> <see cref="X"/></para></remarks>

**C (.c/.h):**
/** @brief [purpose]
 * @param[in] p [desc]    // Use "None" if no parameters
 * @return [desc or "None" for void]
 * @retval 0 Success
 * @throws None
 * @par Example: @code [usage] @endcode
 * @par Business Context: [XRF]
 * @see [related] */

### RULES
- **Void methods:** Use `<returns>None</returns>` or `@return None`
- **Parameterless methods:** Add comment noting "None" for params section
- Document ALL functions with ANY missing sections (not just undocumented)
- Upgrade existing partial docs to EXCELLENT quality
- **MUST NOT SKIP FILES** - Document all files including auto-generated Designer.cs
- Documentation adds discoverable context for AI/search tools

### EXECUTION
1. Read file → 2. Find ALL functions with missing sections → 3. Add/upgrade docs to EXCELLENT → 4. replace_string_in_file → 5. Return:

DONE: [FILENAME]
New Docs: [N]
Upgraded: [N]
Already Excellent: [N]
Status: complete|partial|failed

### CRITICAL: No questions, no explanations. Edit all needing work → return DONE → stop.
```

---

## Supervisor Post-Processing
1. Collect artifacts → 2. Parse "DONE:" + counts → 3. Log round summary → 4. Re-run analysis → 5. Loop if needed → 6. Final verification

## Config
Workers=4 | Files/worker=1 | Return=artifacts | State=analysis_report.json

## Anti-Patterns
❌ Worker narrative | ❌ Supervisor asks worker | ❌ Wrong comment style for language | ❌ Skipping files

## Success Criteria
- `total_functions_to_improve == 0` in analysis_report.json
- Quality distribution shows majority excellent
- No code logic changes (docs only)

## Loop
Repeat Steps 1-4 until `total_functions_to_improve == 0`
