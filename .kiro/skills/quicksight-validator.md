---
inclusion: manual
---

# QuickSight Config Validator

You are a validation agent. When triggered, read the generated JSON files and check for known deployment errors BEFORE the user runs deploy.

## Files to Validate
- `output/dataset-config.json` — Dataset configuration
- `output/dashboard-definition.json` — Dashboard/Analysis definition

## Validation Rules for dataset-config.json

### Rule 1: Table keys must be alphanumeric only
Table keys in the `tables` object must NOT contain hyphens or underscores. The deploy script uses table keys in auto-renamed column names (for duplicate resolution). Hyphens in table keys produce column names like `dim-product_col` which cause SYNTAX_ERROR in QuickSight's OnClause.

**Check:** Every key in `tables` matches `^[a-zA-Z0-9]+$`
**Bad:** `"dim-product-sku"`, `"fact_purchases"`
**Good:** `"dimproduct"`, `"factpurchases"`, `"dimconsumer"`

### Rule 2: Join references must match table keys
Every `left` and `right` value in the `joins` array must exist as a key in `tables`.

### Rule 3: Join columns must exist in their respective tables
The `left_column` must exist in the left table's columns. The `right_column` must exist in the right table's columns.

### Rule 4: PaginationConfiguration PageSize
If present anywhere, PageSize must be one of: 100, 500, 1000, 10000.

## Validation Rules for dashboard-definition.json

### Rule 5: No DataSetIdentifierDeclarations with placeholder ARNs
The `definition` object must NOT contain `DataSetIdentifierDeclarations`. The deploy script auto-injects real ARNs. If present with placeholder values, deployment fails with "resource not reachable".

**Check:** `definition.DataSetIdentifierDeclarations` should not exist.

### Rule 6: DateTimePicker cannot reference TimeRangeFilter
A `DateTimePicker` FilterControl cannot have a `SourceFilterId` pointing to a `TimeRangeFilter`. Valid pairings:
- `RelativeDateTime` control → `RelativeDatesFilter`
- `DateTimePicker` control → single-value date filter only
- `Dropdown` control → `CategoryFilter`

**Check:** For each FilterControl, verify the SourceFilterId points to a compatible filter type in FilterGroups.

### Rule 7: DateDimensionField must have HierarchyId
Every `DateDimensionField` in any visual's FieldWells MUST have a `HierarchyId` property. Additionally, the visual must have a matching `DateTimeHierarchy` entry in its `ColumnHierarchies` array (except TableVisual and InsightVisual which don't support ColumnHierarchies).

### Rule 8: No DonutChartVisual
QuickSight API does not have `DonutChartVisual`. Use `PieChartVisual` with `DonutOptions` instead.

### Rule 9: TableVisual must not have ColumnHierarchies
`TableVisual` does not support the `ColumnHierarchies` property. It should be absent or the visual will fail.

### Rule 10: GridLayout elements must reference existing visuals/controls
Every `ElementId` in `Layouts[].Configuration.GridLayout.Elements` must match either a visual's VisualId or a control's FilterControlId/ParameterControlId.

### Rule 11: SheetControlLayouts elements must reference existing controls
Every `ElementId` in `SheetControlLayouts` must match a FilterControlId or ParameterControlId defined in the sheet.

### Rule 12: CategoryFilter SelectAllOptions vs CategoryValues
A `CategoryFilter` with `FilterListConfiguration` must NOT have both `SelectAllOptions` and `CategoryValues` — use one or the other.

### Rule 13: FieldIds must be unique
Every `FieldId` across all visuals in the definition must be unique. Duplicate FieldIds cause silent failures.

### Rule 14: VisualIds must be unique
Every visual must have a unique VisualId.

### Rule 15: Measure field type must match column data type
- STRING columns (IDs, names, categories) must use `CategoricalMeasureField` with `"AggregationFunction": "COUNT"` or `"DISTINCT_COUNT"`
- INTEGER/DECIMAL columns must use `NumericalMeasureField` with `"AggregationFunction": { "SimpleNumericalAggregation": "..." }`
- Using `NumericalMeasureField` on a STRING column causes COLUMN_TYPE_INCOMPATIBLE error.

**Check:** Cross-reference each measure field's column name against the dataset-config.json column types. If the column type is STRING, it must be CategoricalMeasureField.

## Output Format

After validation, report:
```
✅ PASS: [rule description]
❌ FAIL: [rule description] — [specific issue and how to fix]
```

If any rules FAIL, fix the issues automatically in the JSON files and report what was changed.
