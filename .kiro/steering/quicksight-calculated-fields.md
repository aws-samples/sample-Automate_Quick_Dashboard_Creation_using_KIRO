---
inclusion: auto
---

# QuickSight Calculated Fields — Rulebook

Reference for writing valid calculated field expressions in QuickSight AnalysisDefinition JSON.
Source: [AWS QuickSight Documentation](https://docs.aws.amazon.com/quicksight/latest/user/adding-a-calculated-field-analysis.html)

## Expression Syntax Rules

1. Column references use curly braces: `{column_name}`
2. Parameter references use dollar + curly braces: `${parameterName}`
3. String literals use double quotes: `"value"`
4. Date literals use double quotes: `"2024-01-01"`
5. Period literals for date functions use double quotes: `"YYYY"`, `"MM"`, `"DD"`
6. Comments use `/* comment */` syntax
7. Expressions are NOT SQL — do not use SQL functions or syntax
8. Max expression length: 32,000 characters
9. Max calculated field name length: 128 characters

## Operators (PEMDAS order)

| Operator | Description |
|----------|-------------|
| `+` | Addition |
| `-` | Subtraction |
| `*` | Multiplication |
| `/` | Division (floating point) |
| `%` | Modulo |
| `^` | Power/Exponent |
| `=` | Equal (case-sensitive) |
| `<>` | Not equal |
| `>` `>=` `<` `<=` | Comparison |
| `AND` | Logical AND |
| `OR` | Logical OR |
| `NOT` | Logical NOT |

## JSON Structure in AnalysisDefinition

```json
{
  "CalculatedFields": [
    {
      "DataSetIdentifier": "DS1",
      "Name": "field_name",
      "Expression": "sum({revenue}) / count({transaction_id})"
    }
  ]
}
```

CRITICAL RULES:
- `DataSetIdentifier` must match the dataset identifier used in visuals
- `Name` becomes a column you can reference in visuals like any other column
- Expression must use QuickSight syntax, NOT SQL

---

## Aggregate Functions

Available ONLY in analysis-level calculated fields (not dataset-level).

| Function | Syntax | Description |
|----------|--------|-------------|
| `avg` | `avg({measure})` | Average |
| `avgIf` | `avgIf({measure}, condition)` | Conditional average |
| `count` | `count({field})` | Count (includes duplicates) |
| `countIf` | `countIf({field}, condition)` | Conditional count |
| `distinct_count` | `distinct_count({field})` | Distinct count |
| `distinct_countIf` | `distinct_countIf({field}, condition)` | Conditional distinct count |
| `max` | `max({measure})` | Maximum |
| `maxIf` | `maxIf({measure}, condition)` | Conditional max |
| `median` | `median({measure})` | Median |
| `medianIf` | `medianIf({measure}, condition)` | Conditional median |
| `min` | `min({measure})` | Minimum |
| `minIf` | `minIf({measure}, condition)` | Conditional min |
| `percentile` | `percentile({measure}, percentile_value)` | Nth percentile |
| `percentileCont` | `percentileCont({measure}, percentile_value)` | Continuous percentile |
| `stdev` | `stdev({measure})` | Sample standard deviation |
| `stdevp` | `stdevp({measure})` | Population standard deviation |
| `sum` | `sum({measure})` | Sum |
| `sumIf` | `sumIf({measure}, condition)` | Conditional sum |
| `var` | `var({measure})` | Sample variance |
| `varp` | `varp({measure})` | Population variance |

### Aggregation Rules
- Custom aggregations CANNOT contain nested aggregate functions: `sum(avg({x}))` is INVALID
- Custom aggregations CANNOT mix aggregated and non-aggregated fields: `sum({sales}) + {quantity}` is INVALID
- Nesting non-aggregated functions inside aggregates IS valid: `avg(ceil({x}))` ✓
- Nesting aggregates inside non-aggregated functions IS valid: `ceil(avg({x}))` ✓

---

## Conditional Functions

| Function | Syntax | Description |
|----------|--------|-------------|
| `ifelse` | `ifelse(condition1, result1, condition2, result2, ..., else_result)` | If/else chain |
| `coalesce` | `coalesce({field1}, {field2}, default)` | First non-null value |
| `in` | `in({field}, ["val1", "val2"])` | Value in list |
| `notIn` | `notIn({field}, ["val1", "val2"])` | Value not in list |
| `isNull` | `isNull({field})` | Check if null |
| `isNotNull` | `isNotNull({field})` | Check if not null |
| `nullIf` | `nullIf({field1}, {field2})` | Null if equal |
| `switch` | `switch({field}, "val1", result1, "val2", result2, default)` | Switch/case |

### ifelse Examples
```
ifelse({region} = "North America", "NA", {region} = "Europe", "EU", "Other")
ifelse(sum({revenue}) > 10000, "High", sum({revenue}) > 5000, "Medium", "Low")
```

---

## Date Functions

| Function | Syntax | Description |
|----------|--------|-------------|
| `addDateTime` | `addDateTime(amount, "period", {date})` | Add/subtract time |
| `addWorkDays` | `addWorkDays(amount, {date})` | Add work days |
| `dateDiff` | `dateDiff({date1}, {date2}, "period")` | Difference between dates |
| `epochDate` | `epochDate({epoch_field})` | Epoch to date |
| `extract` | `extract("portion", {date})` | Extract date part |
| `formatDate` | `formatDate({date}, "pattern")` | Format as string |
| `isWorkDay` | `isWorkDay({date})` | Check if work day |
| `netWorkDays` | `netWorkDays({date1}, {date2})` | Working days between |
| `now` | `now()` | Current timestamp |
| `truncDate` | `truncDate("period", {date})` | Truncate to period |

### Period Values
`"YYYY"` (year), `"Q"` (quarter), `"MM"` (month), `"WK"` (week), `"DD"` (day), `"HH"` (hour), `"MI"` (minute), `"SS"` (second)

### Date Examples
```
dateDiff({order_date}, now(), "DD")
truncDate("MM", {order_date})
addDateTime(-30, "DD", now())
extract("MM", {order_date})
formatDate({order_date}, "yyyy-MM-dd")
```

---

## String Functions

| Function | Syntax | Description |
|----------|--------|-------------|
| `concat` | `concat("str1", {field}, "str2")` | Concatenate |
| `contains` | `contains({field}, "substring")` | Contains check |
| `endsWith` | `endsWith({field}, "suffix")` | Ends with check |
| `startsWith` | `startsWith({field}, "prefix")` | Starts with check |
| `left` | `left({field}, n)` | Left n characters |
| `right` | `right({field}, n)` | Right n characters |
| `locate` | `locate({field}, "substring")` | Find position |
| `ltrim` | `ltrim({field})` | Trim left spaces |
| `rtrim` | `rtrim({field})` | Trim right spaces |
| `trim` | `trim({field})` | Trim both sides |
| `replace` | `replace({field}, "old", "new")` | Replace substring |
| `split` | `split({field}, "delimiter", position)` | Split and get part |
| `strlen` | `strlen({field})` | String length |
| `substring` | `substring({field}, start, length)` | Get substring |
| `toLower` | `toLower({field})` | Lowercase |
| `toUpper` | `toUpper({field})` | Uppercase |
| `toString` | `toString({field})` | Convert to string |

---

## Numeric / Math Functions

| Function | Syntax | Description |
|----------|--------|-------------|
| `abs` | `abs({field})` | Absolute value |
| `ceil` | `ceil({field})` | Round up |
| `floor` | `floor({field})` | Round down |
| `round` | `round({field}, decimals)` | Round |
| `sqrt` | `sqrt({field})` | Square root |
| `exp` | `exp({field})` | e^x |
| `log` | `log({field})` | Log base 10 |
| `ln` | `ln({field})` | Natural log |
| `mod` | `mod({field}, divisor)` | Modulo |
| `intToDecimal` | `intToDecimal({field})` | Int to decimal |
| `decimalToInt` | `decimalToInt({field})` | Decimal to int |
| `parseInt` | `parseInt({string_field})` | Parse string to int |
| `parseDecimal` | `parseDecimal({string_field})` | Parse string to decimal |
| `parseDate` | `parseDate({string_field}, "format")` | Parse string to date |

---

## Table Calculations (Window Functions)

### Over Functions (LAC-W)
Partition data and compute within windows.

| Function | Syntax |
|----------|--------|
| `sumOver` | `sumOver({measure}, [{partition}], LEVEL)` |
| `avgOver` | `avgOver({measure}, [{partition}], LEVEL)` |
| `countOver` | `countOver({measure}, [{partition}], LEVEL)` |
| `distinctCountOver` | `distinctCountOver({measure}, [{partition}], LEVEL)` |
| `maxOver` | `maxOver({measure}, [{partition}], LEVEL)` |
| `minOver` | `minOver({measure}, [{partition}], LEVEL)` |
| `stdevOver` | `stdevOver({measure}, [{partition}], LEVEL)` |
| `stdevpOver` | `stdevpOver({measure}, [{partition}], LEVEL)` |
| `varOver` | `varOver({measure}, [{partition}], LEVEL)` |
| `varpOver` | `varpOver({measure}, [{partition}], LEVEL)` |
| `percentileOver` | `percentileOver({measure}, percentile, [{partition}], LEVEL)` |

**LEVEL values:** `PRE_FILTER`, `PRE_AGG`, `POST_AGG_FILTER` (default if omitted)

**Rules:**
- With `PRE_FILTER` or `PRE_AGG`: use RAW (unaggregated) measure: `sumOver({revenue}, [{brand}], PRE_AGG)`
- Without level (default POST_AGG_FILTER): use AGGREGATED measure: `sumOver(sum({revenue}), [{brand}])`

### Ranking Functions

| Function | Syntax |
|----------|--------|
| `rank` | `rank([{sort_field} ASC/DESC], [{partition}], LEVEL)` |
| `denseRank` | `denseRank([{sort_field} ASC/DESC], [{partition}], LEVEL)` |
| `percentileRank` | `percentileRank({measure}, [{partition}], LEVEL)` |

### Running Functions

| Function | Syntax |
|----------|--------|
| `runningSum` | `runningSum(sum({measure}), [{sort_field} ASC], [{partition}])` |
| `runningAvg` | `runningAvg(sum({measure}), [{sort_field} ASC], [{partition}])` |
| `runningCount` | `runningCount({measure}, [{sort_field} ASC], [{partition}])` |
| `runningMax` | `runningMax(sum({measure}), [{sort_field} ASC], [{partition}])` |
| `runningMin` | `runningMin(sum({measure}), [{sort_field} ASC], [{partition}])` |

### Lookup Functions

| Function | Syntax |
|----------|--------|
| `lag` | `lag(sum({measure}), [{sort_field} ASC], offset, [{partition}])` |
| `lead` | `lead(sum({measure}), [{sort_field} ASC], offset, [{partition}])` |
| `difference` | `difference(sum({measure}), [{sort_field} ASC], offset, [{partition}])` |
| `percentDifference` | `percentDifference(sum({measure}), [{sort_field} ASC], offset, [{partition}])` |

### Window Functions

| Function | Syntax |
|----------|--------|
| `windowSum` | `windowSum(sum({measure}), [{sort_field} ASC], start, end, [{partition}])` |
| `windowAvg` | `windowAvg(sum({measure}), [{sort_field} ASC], start, end, [{partition}])` |
| `windowCount` | `windowCount(sum({measure}), [{sort_field} ASC], start, end, [{partition}])` |
| `windowMax` | `windowMax(sum({measure}), [{sort_field} ASC], start, end, [{partition}])` |
| `windowMin` | `windowMin(sum({measure}), [{sort_field} ASC], start, end, [{partition}])` |
| `firstValue` | `firstValue(sum({measure}), [{sort_field} ASC], [{partition}])` |
| `lastValue` | `lastValue(sum({measure}), [{sort_field} ASC], [{partition}])` |

### Other Table Calculations

| Function | Syntax |
|----------|--------|
| `percentOfTotal` | `percentOfTotal(sum({measure}), [{partition}])` |
| `periodOverPeriodDifference` | `periodOverPeriodDifference(sum({measure}), {date_field}, "period", offset)` |
| `periodOverPeriodLastValue` | `periodOverPeriodLastValue(sum({measure}), {date_field}, "period", offset)` |
| `periodOverPeriodPercentDifference` | `periodOverPeriodPercentDifference(sum({measure}), {date_field}, "period", offset)` |

---

## Level-Aware Calculations (LAC-A)

Specify aggregation level independent of visual dimensions.

```
sum({sales}, [{Country}])                           -- Sum grouped by Country only
sum({sales}, [{Country}, {Product}])                -- Sum grouped by Country + Product
sum({sales}, [${visualDimensions}, {Country}])      -- Visual dims + Country
sum({sales}, [${visualDimensions}, !{Country}])     -- Visual dims minus Country
```

**Supported functions:** avg, count, distinct_count, max, median, min, percentile, percentileCont, percentileDisc, stdev, stdevp, sum, var, varp

**NOT supported:** conditional functions (sumIf, countIf, etc.) and periodToDate functions

**Nesting rules:**
- ✅ `max(sum({sales}, [{country}]))` — Aggregate wrapping LAC-A
- ✅ `sum(sumOver({sales}, [{product}], PRE_AGG), [{country}])` — LAC-A wrapping LAC-W
- ❌ `sum(max({sales}), [{country}])` — LAC-A wrapping aggregate
- ❌ `sum(max({sales}, [{country}]), [{category}])` — LAC-A wrapping LAC-A
- ❌ `sumOver(sum({sales}, [{product}]), [{country}], PRE_AGG)` — LAC-W wrapping LAC-A

---

## Common Patterns & Examples

### Revenue per order
```
sum({revenue}) / count({transaction_id})
```

### Discount rate
```
sum({discount_amount}) / sum({revenue})
```

### Year-over-year growth
```
percentOverPeriodDifference(sum({revenue}), {order_date}, "YYYY", 1)
```

### Percent of total by brand
```
percentOfTotal(sum({revenue}), [{brand}])
```

### Running total
```
runningSum(sum({revenue}), [{order_date} ASC])
```

### Customer count per region (pre-aggregate)
```
countOver({dim_consumer_key}, [{region}], PRE_AGG)
```

### Rank brands by revenue
```
rank([sum({revenue}) DESC], [{brand}])
```

### Current year sales only
```
ifelse(dateDiff({order_date}, truncDate("YYYY", now()), "YYYY") = 0, {revenue}, 0)
```

### Moving average (3-period)
```
windowAvg(sum({revenue}), [{order_date} ASC], -2, 0)
```

---

## Common Mistakes to Avoid

| Mistake | Why it fails | Fix |
|---------|-------------|-----|
| `SUM(revenue)` | SQL syntax, wrong case | `sum({revenue})` |
| `{revenue} + {quantity}` mixed with `sum({revenue})` | Can't mix agg + non-agg | Use all agg or all non-agg |
| `sum(avg({revenue}))` | Nested aggregates | Use LAC-A: `avg({revenue}, [{dim}])` |
| `sumOver({revenue}, [{brand}])` without level | Default is POST_AGG, needs aggregated input | `sumOver(sum({revenue}), [{brand}])` or add `PRE_AGG` |
| Using SQL functions like `CASE WHEN` | Not QuickSight syntax | Use `ifelse()` or `switch()` |
| `count(*)` | No wildcard in QS | `count({any_field})` |
| `DATEDIFF(d1, d2)` | SQL syntax | `dateDiff({d1}, {d2}, "DD")` |
| Missing curly braces around column | Won't resolve | Always use `{column_name}` |
