# Source Documentation Improvement

## Workflow

Repeat until `total_functions_to_improve: 0`:

1. Run analysis
2. Document highest priority functions
3. Re-run analysis
4. Continue until zero issues

## Step 1: Analyze

```bash
.venv/bin/python utils/analyze_all_source.py --pretty --output analysis_report.json
```

Output file: `analysis_report.json` (gitignored, workspace root)

Read summary to check progress:

```bash
.venv/bin/python -c "import json; r=json.load(open('analysis_report.json')); print(f\"To improve: {r['summary']['total_functions_to_improve']}\")"
```

## Step 2: Document by Priority

Reference `analysis_report.json` for function locations and missing sections.

- **8-10**: Full docstrings immediately
- **5-7**: Add missing sections
- **1-4**: Complete all remaining

## Step 3: Re-analyze and Repeat

Re-run analysis after each batch. Continue until:

```json
"total_functions_to_improve": 0
```

## Documentation Templates by Language

### Python (Google Style)

#### Function Template

```python
def func(param1: T1, param2: T2) -> RT:
    """Brief summary.

    Detailed purpose/behavior. Business context: why this matters.

    Args:
        param1: Type, constraints, valid ranges, examples.
        param2: Type, units, defaults, relation to other params.

    Returns:
        Type, structure, value ranges, edge cases.

    Raises:
        ValueError: When param1 < 0.
        TypeError: Invalid param types.

    Example:
        >>> result = func(val1, val2)
        >>> func(edge, config={'opt': True})
    """
```

#### Class Template

```python
class Name:
    """Brief summary.

    Detailed role/usage. Business context: why this exists.

    Attributes:
        attr: Type, purpose, constraints.

    Raises:
        ValueError: Init error conditions.

    Example:
        >>> obj = Name(config)
        >>> obj.method()
    """
```

---

### VB6 (Visual Basic 6)

#### Sub/Function Template

```vb
'******************************************************************************
' Sub/Function: ProcedureName
'******************************************************************************
' Purpose:
'   Brief summary of what this procedure does.
'   Detailed behavior and business context.
'
' Parameters:
'   @param ParamName  - [In/Out] Type, description, constraints
'   @param OtherParam - [In] Type, valid ranges, defaults
'
' Returns:
'   Type - Description of return value, edge cases.
'
' Raises:
'   Error description and conditions.
'
' Business Context:
'   Why this procedure exists, how it fits in the workflow.
'
' See Also:
'   RelatedProcedure(), OtherModule.Function()
'******************************************************************************
Public Sub ProcedureName(ByVal ParamName As Type, ByRef OtherParam As Type)
```

#### Module Header Template

```vb
'******************************************************************************
' Module: ModuleName.bas
'******************************************************************************
' Purpose:
'   Brief summary of module responsibility.
'
' Description:
'   Detailed role in the application. Business context.
'
' Dependencies:
'   - OtherModule.bas - Description
'   - ExternalDLL - Purpose
'
' Public Interface:
'   - MainFunction() - Primary entry point
'   - HelperSub() - Supporting functionality
'******************************************************************************
```

---

### VB.NET (Visual Basic .NET)

#### Function Template

```vb
''' <summary>
''' Brief summary of what this function does.
''' </summary>
''' <remarks>
''' Detailed behavior and business context.
''' Why this function exists and how it fits in the workflow.
''' </remarks>
''' <param name="paramName">Type, description, constraints, valid ranges.</param>
''' <param name="otherParam">Type, defaults, relation to other params.</param>
''' <returns>Type - Description of return value, edge cases.</returns>
''' <exception cref="ArgumentException">When paramName is invalid.</exception>
''' <exception cref="InvalidOperationException">When state is incorrect.</exception>
''' <example>
''' <code>
''' Dim result = FunctionName(value1, value2)
''' </code>
''' </example>
''' <seealso cref="RelatedFunction"/>
Public Function FunctionName(ByVal paramName As T1, ByVal otherParam As T2) As RT
```

#### Class Template

```vb
''' <summary>
''' Brief summary of class purpose.
''' </summary>
''' <remarks>
''' Detailed role and usage patterns. Business context.
''' </remarks>
''' <example>
''' <code>
''' Dim obj As New ClassName(config)
''' obj.Method()
''' </code>
''' </example>
Public Class ClassName
```

---

### C# (C-Sharp)

#### Method Template

```csharp
/// <summary>
/// Brief summary of what this method does.
/// </summary>
/// <remarks>
/// Detailed behavior and business context.
/// Why this method exists and how it fits in the workflow.
/// </remarks>
/// <param name="paramName">Type, description, constraints, valid ranges.</param>
/// <param name="otherParam">Type, defaults, relation to other params.</param>
/// <returns>Type - Description of return value, edge cases.</returns>
/// <exception cref="ArgumentException">When paramName is invalid.</exception>
/// <exception cref="InvalidOperationException">When state is incorrect.</exception>
/// <example>
/// <code>
/// var result = MethodName(value1, value2);
/// </code>
/// </example>
/// <seealso cref="RelatedMethod"/>
public ReturnType MethodName(T1 paramName, T2 otherParam)
```

#### Class Template

```csharp
/// <summary>
/// Brief summary of class purpose.
/// </summary>
/// <remarks>
/// Detailed role and usage patterns. Business context.
/// Thread-safety considerations if applicable.
/// </remarks>
/// <example>
/// <code>
/// var obj = new ClassName(config);
/// obj.Method();
/// </code>
/// </example>
public class ClassName
```

---

### C/C++ (Doxygen Style)

#### Function Template

```c
/**
 * @brief Brief summary of what this function does.
 *
 * Detailed behavior and business context.
 * Why this function exists and how it fits in the workflow.
 *
 * @param[in]  paramName   Type, description, constraints, valid ranges.
 * @param[out] outParam    Type, what gets written, buffer requirements.
 * @param[in,out] ioParam  Type, input/output behavior.
 *
 * @return Type - Description of return value, edge cases.
 * @retval 0  Success
 * @retval -1 Error condition description
 *
 * @throws std::invalid_argument When paramName is invalid (C++ only).
 *
 * @note Important usage notes or constraints.
 * @warning Critical warnings about misuse.
 *
 * @see RelatedFunction(), OtherModule.h
 *
 * @code
 * int result = FunctionName(value1, &output);
 * if (result != 0) { handle_error(); }
 * @endcode
 */
int FunctionName(int paramName, char* outParam, double* ioParam);
```

#### Struct/Class Template

```cpp
/**
 * @brief Brief summary of struct/class purpose.
 *
 * Detailed role and usage patterns. Business context.
 * Memory management responsibilities if applicable.
 *
 * @note Thread-safety considerations.
 *
 * @code
 * ClassName obj(config);
 * obj.method();
 * @endcode
 */
class ClassName {
```

#### File Header Template

```c
/**
 * @file filename.c
 * @brief Brief description of file contents.
 *
 * Detailed description of module responsibility.
 * Business context and dependencies.
 *
 * @author Author Name
 * @date YYYY-MM-DD
 *
 * @copyright Thermo Fisher Scientific
 */
```

## Priority Requirements (All Languages)

| Priority | Required Sections |
| --- | --- |
| 8-10 | brief/summary, detailed/remarks, business context, params, returns, errors/exceptions, example |
| 5-7 | brief/summary, detailed/remarks, params, returns, errors/exceptions |
| 1-4 | brief/summary, params, returns |

## Language Detection

| Extension | Language | Doc Style |
| --- | --- | --- |
| `.py`, `.pyi` | Python | Google docstrings |
| `.bas`, `.frm`, `.cls` | VB6 | Comment blocks (`'`) |
| `.vb` | VB.NET | XML comments (`'''`) |
| `.cs` | C# | XML comments (`///`) |
| `.c`, `.h` | C | Doxygen (`/** */`) |
| `.cpp`, `.hpp`, `.cxx` | C++ | Doxygen (`/** */`) |

## Constraints

- Documentation only, preserve functionality
- Address missing elements from JSON
- Business context for public APIs

## Success Criteria

- `total_functions_to_improve: 0`
- All functions rated "excellent"
- No missing sections in any function
