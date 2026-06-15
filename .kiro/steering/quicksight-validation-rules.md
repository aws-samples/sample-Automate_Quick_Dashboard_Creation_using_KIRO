---
inclusion: auto
---

# QuickSight Validation Rules — Learned from Deployment Failures

These rules MUST be checked every time `output/dataset-config.json` or `output/dashboard-definition.json` is generated. Violations cause silent CREATION_FAILED status in QuickSight.

## Summary of All Known Errors

| # | Error | Root Cause | Fix |
|---|-------|-----------|-----|
| 1 | SYNTAX_ERROR on CreateDataSet | Table keys with hyphens produce invalid renamed column names in OnClause | Use alphanumeric-only table keys |
| 2 | Resource not reachable in region | DataSetIdentifierDeclarations has placeholder ARN | Omit it — deploy script injects real ARNs |
| 3 | Filter doesn't support DATE_PICKER control | DateTimePicker control paired with TimeRangeFilter | Use RelativeDateTime + RelativeDatesFilter |
| 4 | COLUMN_TYPE_INCOMPATIBLE | NumericalMeasureField used on STRING column for COUNT | Use CategoricalMeasureField for STRING columns |

---

## Dataset Config Rules (output/dataset-config.json)

### D1: Table keys must be alphanumeric only
```
REGEX: ^[a-zA-Z0-9]+$
BAD:  "dim-product-sku", "fact_purchases", "dim-consumer"
GOOD: "dimproduct", "factpurchases", "dimconsumer"
```
WHY: Deploy script uses table keys in renamed column names. Hyphens/underscores in keys create column names that break QuickSight's OnClause parser.

### D2: Join references must match table keys
Every `left` and `right` in `joins[]` must exist as a key in `tables`.

### D3: Join columns must exist in their tables
`on.left_column` must be in the left table's columns list. `on.right_column` must be in the right table's columns list.

### D4: Column types must be correct
Match Redshift types to QuickSight types:
- `character varying` → STRING
- `integer`, `bigint` → INTEGER
- `numeric`, `decimal`, `double precision` → DECIMAL
- `timestamp`, `date` → DATETIME
- `boolean` → STRING (QuickSight has no boolean)

---

## Dashboard Definition Rules (output/dashboard-definition.json)

### F1: No DataSetIdentifierDeclarations in definition
The `definition` object must NOT contain `DataSetIdentifierDeclarations`. The deploy script auto-injects real ARNs from the dataset created in Step 2.

### F2: Measure field type must match column type
- STRING columns (IDs, names, categories) → use `CategoricalMeasureField` with `"AggregationFunction": "COUNT"` or `"DISTINCT_COUNT"`
- INTEGER/DECIMAL columns (revenue, quantity, price) → use `NumericalMeasureField` with `"AggregationFunction": { "SimpleNumericalAggregation": "SUM|COUNT|AVERAGE|MIN|MAX" }`

NEVER use `NumericalMeasureField` on a STRING column. QuickSight will reject it with COLUMN_TYPE_INCOMPATIBLE.

### F3: Filter control must match filter type
| Control Type | Compatible Filter Type |
|---|---|
| `RelativeDateTime` | `RelativeDatesFilter` |
| `DateTimePicker` | Single-value date filter (NOT TimeRangeFilter) |
| `Dropdown` | `CategoryFilter` with `FilterListConfiguration` |
| `Slider` | `NumericRangeFilter` |

### F4: DateDimensionField must have HierarchyId
Every `DateDimensionField` must include `"HierarchyId"` and the parent visual must have a matching `DateTimeHierarchy` in `ColumnHierarchies` — EXCEPT TableVisual and InsightVisual (they don't support ColumnHierarchies).

### F5: No DonutChartVisual
Use `PieChartVisual` with `DonutOptions` instead. `DonutChartVisual` does not exist in the API.

### F6: TableVisual has no ColumnHierarchies
Never add `ColumnHierarchies` to a TableVisual.

### F7: CategoryFilter — SelectAllOptions vs CategoryValues
A CategoryFilter with FilterListConfiguration must use EITHER `SelectAllOptions` OR `CategoryValues` — never both.

### F8: All IDs must be unique
- Every `FieldId` across all visuals must be unique
- Every `VisualId` must be unique
- Every `FilterControlId` must be unique

### F9: GridLayout ElementIds must reference real visuals/controls
Every `ElementId` in Layouts and SheetControlLayouts must match an existing VisualId or FilterControlId.

### F10: PaginationConfiguration PageSize
Must be one of: 100, 500, 1000, 10000.

---

## How Validation Works

Validation is triggered automatically via hooks AFTER the JSON files are written:

1. **Hook: `validate-dataset-config.json`** — fires on edit of `output/dataset-config.json`
   - Checks rules D1–D4
   - Auto-fixes issues and reports changes

2. **Hook: `validate-dashboard-definition.json`** — fires on edit of `output/dashboard-definition.json`
   - Checks rules F1–F10
   - Auto-fixes issues and reports changes

3. **Manual validation** — use `#quicksight-validator` skill in chat to run full validation on demand

The validation runs BEFORE deployment, catching errors that would otherwise result in silent CREATION_FAILED status.

---

## Quick Reference: Column Type → Measure Field Type

```
STRING column + COUNT        → CategoricalMeasureField, "AggregationFunction": "COUNT"
STRING column + DISTINCT     → CategoricalMeasureField, "AggregationFunction": "DISTINCT_COUNT"
INTEGER/DECIMAL + SUM        → NumericalMeasureField, "AggregationFunction": { "SimpleNumericalAggregation": "SUM" }
INTEGER/DECIMAL + AVG        → NumericalMeasureField, "AggregationFunction": { "SimpleNumericalAggregation": "AVERAGE" }
INTEGER/DECIMAL + COUNT      → NumericalMeasureField, "AggregationFunction": { "SimpleNumericalAggregation": "COUNT" }
```
