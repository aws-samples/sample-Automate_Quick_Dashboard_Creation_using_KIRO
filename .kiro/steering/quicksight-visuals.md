---
inclusion: auto
---

# QuickSight Visual Components — Knowledge Base

CRITICAL RULES (learned from production deployment):
1. Use PieChartVisual (NOT DonutChartVisual) — DonutChartVisual does not exist in the API
2. Every DateDimensionField MUST have a "HierarchyId" field, and a matching DateTimeHierarchy in the visual's ColumnHierarchies. Set HierarchyId = FieldId for simplicity.
3. DateTimeParameterDeclaration does NOT support "ParameterValueType" — omit it
4. TableVisual and InsightVisual do NOT support ColumnHierarchies — omit for those
5. PaginationConfiguration PageSize must be one of: 100, 500, 1000, 10000
6. ColumnHierarchies supported by: LineChartVisual, BarChartVisual, PieChartVisual, KPIVisual, ComboChartVisual, ScatterPlotVisual, RadarChartVisual, WordCloudVisual
7. Grid is 36 columns wide (NOT 12). KPIs span 8-10 cols, charts 13-22 cols.
8. Filter controls go in SheetControlLayouts (separate section), NOT in the main Layouts GridLayout
9. Use FilterControls with SourceFilterId (NOT ParameterControls) for working filters
10. CategoryFilter with SelectAllOptions must NOT also have CategoryValues — use one or the other
11. Calculated field expressions use {column} syntax, not SQL. Use Over functions for partitioned calcs.
12. Dashboard Definition does NOT support "QueryExecutionOptions" — only Analysis does. The deploy script strips it automatically.

Built from real production QuickSight AnalysisDefinition exports + AWS API documentation.
Use these patterns to generate valid AnalysisDefinition JSON.

## AnalysisDefinition Top-Level Structure

```json
{
  "DataSetIdentifierDeclarations": [
    { "Identifier": "DS1", "DataSetArn": "arn:aws:quicksight:REGION:ACCOUNT:dataset/ID" }
  ],
  "ParameterDeclarations": [ ... ],
  "CalculatedFields": [ ... ],
  "FilterGroups": [ ... ],
  "ColumnConfigurations": [ ... ],
  "Sheets": [ ... ],
  "AnalysisDefaults": {
    "DefaultNewSheetConfiguration": {
      "InteractiveLayoutConfiguration": {
        "Grid": { "CanvasSizeOptions": { "ScreenCanvasSizeOptions": { "ResizeOption": "RESPONSIVE" } } }
      },
      "SheetContentType": "INTERACTIVE"
    }
  },
  "Options": { "WeekStart": "SUNDAY" },
  "QueryExecutionOptions": { "QueryExecutionMode": "AUTO" }
}
```

LAYOUT RULES FOR FULL-WIDTH DASHBOARDS:
- Use ResizeOption "RESPONSIVE" (not "FIXED") so visuals stretch to fill browser width
- Every row MUST have ColumnSpan values adding to exactly 12
- Standard row heights: filters=2, KPIs=4, charts=8, tables=10
- Example rows: 12 (full), 6+6 (half+half), 4+4+4 (thirds), 4+8 (sidebar+main)
- NEVER leave empty columns in a row

## Layouts

### GridLayout (standard dashboards)
36-column grid (not 12). Each element:
```json
{ "ElementId": "visual-id", "ElementType": "VISUAL", "ColumnIndex": 0, "RowIndex": 0, "ColumnSpan": 18, "RowSpan": 8 }
```
ElementType: "VISUAL", "FILTER_CONTROL", "PARAMETER_CONTROL"

Standard sizing (36-col grid):
- KPI cards: ColumnSpan 8-10, RowSpan 5 (4 KPIs across = 8+9+9+10 = 36)
- Charts: ColumnSpan 13-22, RowSpan 7-12
- Tables: ColumnSpan 15-20, RowSpan 10-12
- Full width: ColumnSpan 36
- Half width: ColumnSpan 18
- Third width: ColumnSpan 12

Filter controls go in SheetControlLayouts (separate from main Layouts):
```json
{
  "SheetControlLayouts": [{
    "Configuration": {
      "GridLayout": {
        "Elements": [
          { "ElementId": "ctrl-id", "ElementType": "FILTER_CONTROL", "ColumnSpan": 2, "RowSpan": 1 }
        ]
      }
    }
  }]
}
```
Controls auto-flow left to right (no ColumnIndex/RowIndex needed).

### FreeFormLayout (pixel-perfect positioning)
```json
{
  "FreeFormLayout": {
    "Elements": [{
      "ElementId": "visual-id", "ElementType": "VISUAL",
      "XAxisLocation": "0px", "YAxisLocation": "0px",
      "Width": "800px", "Height": "400px",
      "Visibility": "VISIBLE",
      "BorderStyle": { "Visibility": "HIDDEN" },
      "SelectedBorderStyle": { "Visibility": "HIDDEN" },
      "BackgroundStyle": { "Visibility": "HIDDEN" }
    }]
  }
}
```

### FreeFormLayout — Conditional Visibility (RenderingRules)
Show/hide visuals based on parameter values:
```json
{
  "ElementId": "visual-id", "ElementType": "VISUAL",
  "XAxisLocation": "464px", "YAxisLocation": "1328px",
  "Width": "1104px", "Height": "384px",
  "Visibility": "HIDDEN",
  "RenderingRules": [{
    "Expression": "${paramName} = \"someValue\"",
    "ConfigurationOverrides": { "Visibility": "VISIBLE" }
  }]
}
```
Functions in expressions: `locate(${param}, "text") > 0`, `${param} = "value"`

---

## Visual Types

### KPIVisual

```json
{
  "KPIVisual": {
    "VisualId": "kpi-revenue",
    "Title": { "Visibility": "VISIBLE", "FormatText": { "PlainText": "Total Revenue" } },
    "Subtitle": { "Visibility": "HIDDEN" },
    "ChartConfiguration": {
      "FieldWells": {
        "Values": [{
          "NumericalMeasureField": {
            "FieldId": "rev-kpi",
            "Column": { "DataSetIdentifier": "DS1", "ColumnName": "revenue" },
            "AggregationFunction": { "SimpleNumericalAggregation": "SUM" }
          }
        }],
        "TargetValues": [],
        "TrendGroups": [{
          "DateDimensionField": {
            "FieldId": "date-trend",
            "Column": { "DataSetIdentifier": "DS1", "ColumnName": "order_date" },
            "DateGranularity": "MONTH"
          }
        }]
      },
      "KPIOptions": {
        "Comparison": { "ComparisonMethod": "PERCENT_DIFFERENCE" },
        "PrimaryValueDisplayType": "ACTUAL",
        "PrimaryValueFontConfiguration": { "FontSize": { "Relative": "EXTRA_SMALL" }, "FontColor": "#FFFFFF" },
        "Sparkline": { "Visibility": "VISIBLE", "Type": "AREA" },
        "VisualLayoutOptions": { "StandardLayout": { "Type": "VERTICAL" } }
      }
    },
    "Actions": [], "ColumnHierarchies": []
  }
}
```
- TrendGroups optional. Sparkline types: AREA, LINE.
- For categorical count: use `CategoricalMeasureField` with `"AggregationFunction": "DISTINCT_COUNT"`
- Aggregations: SUM, AVERAGE, COUNT, MIN, MAX, DISTINCT_COUNT

### BarChartVisual

```json
{
  "BarChartVisual": {
    "VisualId": "bar-by-region",
    "Title": { "Visibility": "VISIBLE", "FormatText": { "PlainText": "Revenue by Region" } },
    "ChartConfiguration": {
      "FieldWells": {
        "BarChartAggregatedFieldWells": {
          "Category": [{
            "CategoricalDimensionField": {
              "FieldId": "region-cat",
              "Column": { "DataSetIdentifier": "DS1", "ColumnName": "region" }
            }
          }],
          "Values": [{
            "NumericalMeasureField": {
              "FieldId": "rev-bar",
              "Column": { "DataSetIdentifier": "DS1", "ColumnName": "revenue" },
              "AggregationFunction": { "SimpleNumericalAggregation": "SUM" },
              "FormatConfiguration": {
                "FormatConfiguration": {
                  "NumberDisplayFormatConfiguration": {
                    "DecimalPlacesConfiguration": { "DecimalPlaces": 0 },
                    "NumberScale": "NONE"
                  }
                }
              }
            }
          }],
          "Colors": []
        }
      },
      "SortConfiguration": {
        "CategorySort": [{ "FieldSort": { "FieldId": "rev-bar", "Direction": "DESC" } }],
        "CategoryItemsLimit": { "OtherCategories": "INCLUDE" }
      },
      "Orientation": "HORIZONTAL",
      "BarsArrangement": "CLUSTERED",
      "DataLabels": { "Visibility": "VISIBLE", "Position": "INSIDE", "Overlap": "ENABLE_OVERLAP" },
      "Legend": { "Visibility": "HIDDEN" },
      "Tooltip": {
        "TooltipVisibility": "VISIBLE", "SelectedTooltipType": "DETAILED",
        "FieldBasedTooltip": { "AggregationVisibility": "HIDDEN", "TooltipTitleType": "PRIMARY_VALUE" }
      }
    },
    "Actions": [], "ColumnHierarchies": []
  }
}
```
- Orientation: HORIZONTAL, VERTICAL
- BarsArrangement: CLUSTERED, STACKED, STACKED_PERCENT
- Multiple Values = grouped/stacked bars
- CategoryAxis, ValueAxis for axis customization (hide labels, gridlines, log scale)

### LineChartVisual

```json
{
  "LineChartVisual": {
    "VisualId": "line-trend",
    "Title": { "Visibility": "VISIBLE", "FormatText": { "PlainText": "Monthly Revenue Trend" } },
    "ChartConfiguration": {
      "FieldWells": {
        "LineChartAggregatedFieldWells": {
          "Category": [{
            "DateDimensionField": {
              "FieldId": "date-line",
              "Column": { "DataSetIdentifier": "DS1", "ColumnName": "order_date" },
              "DateGranularity": "MONTH"
            }
          }],
          "Values": [{
            "NumericalMeasureField": {
              "FieldId": "rev-line",
              "Column": { "DataSetIdentifier": "DS1", "ColumnName": "revenue" },
              "AggregationFunction": { "SimpleNumericalAggregation": "SUM" }
            }
          }],
          "Colors": [],
          "SmallMultiples": []
        }
      },
      "ReferenceLines": [{
        "DataConfiguration": {
          "DynamicConfiguration": {
            "Column": { "DataSetIdentifier": "DS1", "ColumnName": "revenue" },
            "Calculation": { "SimpleNumericalAggregation": "AVERAGE" }
          }
        },
        "StyleConfiguration": { "Color": "#3366FF", "Pattern": "DOTTED" },
        "LabelConfiguration": { "CustomLabelConfiguration": { "CustomLabel": "Average" } }
      }]
    },
    "Actions": [], "ColumnHierarchies": []
  }
}
```
- DateGranularity: DAY, WEEK, MONTH, QUARTER, YEAR
- Colors field = multi-line (one line per color dimension value)
- SmallMultiples = trellis/faceted charts
- ReferenceLines: StaticConfiguration (fixed value) or DynamicConfiguration (aggregate)

### PieChartVisual (use for donut/pie charts)

NOTE: QuickSight API uses PieChartVisual, NOT DonutChartVisual. Use DonutOptions for donut style.

```json
{
  "PieChartVisual": {
    "VisualId": "donut-brand",
    "Title": { "Visibility": "VISIBLE", "FormatText": { "PlainText": "Revenue by Brand" } },
    "ChartConfiguration": {
      "FieldWells": {
        "PieChartAggregatedFieldWells": {
          "Category": [{
            "CategoricalDimensionField": {
              "FieldId": "brand-cat",
              "Column": { "DataSetIdentifier": "DS1", "ColumnName": "brand" }
            }
          }],
          "Values": [{
            "NumericalMeasureField": {
              "FieldId": "rev-donut",
              "Column": { "DataSetIdentifier": "DS1", "ColumnName": "revenue" },
              "AggregationFunction": { "SimpleNumericalAggregation": "SUM" }
            }
          }]
        }
      },
      "DonutOptions": { "ArcOptions": { "ArcThickness": "MEDIUM" } }
    },
    "Actions": [], "ColumnHierarchies": []
  }
}
```
- ArcThickness: SMALL, MEDIUM, LARGE, WHOLE (WHOLE = full pie, no hole)

### TableVisual

```json
{
  "TableVisual": {
    "VisualId": "table-detail",
    "Title": { "Visibility": "VISIBLE", "FormatText": { "PlainText": "Detail View" } },
    "ChartConfiguration": {
      "FieldWells": {
        "TableAggregatedFieldWells": {
          "GroupBy": [{
            "CategoricalDimensionField": {
              "FieldId": "region-grp",
              "Column": { "DataSetIdentifier": "DS1", "ColumnName": "region" }
            }
          }],
          "Values": [{
            "NumericalMeasureField": {
              "FieldId": "rev-tbl",
              "Column": { "DataSetIdentifier": "DS1", "ColumnName": "revenue" },
              "AggregationFunction": { "SimpleNumericalAggregation": "SUM" }
            }
          }]
        }
      },
      "SortConfiguration": {
        "RowSort": [{ "FieldSort": { "FieldId": "rev-tbl", "Direction": "DESC" } }],
        "PaginationConfiguration": { "PageSize": 25, "PageNumber": 1 }
      },
      "TableOptions": {
        "HeaderStyle": {
          "FontConfiguration": { "FontSize": { "Relative": "LARGE" }, "FontColor": "#FFFFFF" },
          "BackgroundColor": "#232F3E", "Height": 30
        },
        "CellStyle": {
          "FontConfiguration": { "FontSize": { "Relative": "MEDIUM" } },
          "TextWrap": "WRAP", "Height": 30,
          "Border": { "UniformBorder": { "Color": "#E0E0E0", "Style": "SOLID" } }
        },
        "RowAlternateColorOptions": {
          "Status": "ENABLED", "RowAlternateColors": ["#F5F5F5"], "UsePrimaryBackgroundColor": "ENABLED"
        }
      },
      "TotalOptions": { "TotalsVisibility": "VISIBLE", "Placement": "END" },
      "FieldOptions": {
        "SelectedFieldOptions": [
          { "FieldId": "region-grp", "Width": "200px", "CustomLabel": "Region" }
        ]
      }
    },
    "Actions": []
  }
}
```
- URLStyling for image columns: `"URLStyling": { "ImageConfiguration": { "SizingOptions": { "TableCellImageScalingConfiguration": "FIT_TO_CELL_HEIGHT" } } }`
- Hide columns: `"Visibility": "HIDDEN"` in SelectedFieldOptions
- NullValueFormatConfiguration for fallback values

### PivotTableVisual

```json
{
  "PivotTableVisual": {
    "VisualId": "pivot-analysis",
    "Title": { "Visibility": "VISIBLE", "FormatText": { "PlainText": "Revenue by Region and Month" } },
    "ChartConfiguration": {
      "FieldWells": {
        "PivotTableAggregatedFieldWells": {
          "Rows": [{
            "CategoricalDimensionField": {
              "FieldId": "region-row",
              "Column": { "DataSetIdentifier": "DS1", "ColumnName": "region" }
            }
          }],
          "Columns": [{
            "DateDimensionField": {
              "FieldId": "date-col",
              "Column": { "DataSetIdentifier": "DS1", "ColumnName": "order_date" },
              "DateGranularity": "MONTH"
            }
          }],
          "Values": [{
            "NumericalMeasureField": {
              "FieldId": "rev-pivot",
              "Column": { "DataSetIdentifier": "DS1", "ColumnName": "revenue" },
              "AggregationFunction": { "SimpleNumericalAggregation": "SUM" }
            }
          }]
        }
      },
      "TableOptions": {
        "MetricPlacement": "COLUMN",
        "ColumnNamesVisibility": "VISIBLE",
        "ColumnHeaderStyle": { "FontConfiguration": { "FontColor": "#FFFFFF" }, "BackgroundColor": "#232F3E" },
        "RowHeaderStyle": { "FontConfiguration": { "FontSize": { "Relative": "LARGE" } } },
        "CellStyle": { "TextWrap": "WRAP", "HorizontalTextAlignment": "CENTER" },
        "RowsLayout": "HIERARCHY",
        "CollapsedRowDimensionsVisibility": "HIDDEN"
      },
      "TotalOptions": {
        "RowSubtotalOptions": { "TotalsVisibility": "VISIBLE" },
        "RowTotalOptions": { "Placement": "AUTO" },
        "ColumnTotalOptions": { "Placement": "END" }
      }
    },
    "Actions": []
  }
}
```

### WordCloudVisual

```json
{
  "WordCloudVisual": {
    "VisualId": "wordcloud-keywords",
    "Title": { "Visibility": "VISIBLE", "FormatText": { "PlainText": "Top Keywords" } },
    "ChartConfiguration": {
      "FieldWells": {
        "WordCloudAggregatedFieldWells": {
          "GroupBy": [{
            "CategoricalDimensionField": {
              "FieldId": "keyword-grp",
              "Column": { "DataSetIdentifier": "DS1", "ColumnName": "keyword" }
            }
          }],
          "Size": [{
            "NumericalMeasureField": {
              "FieldId": "count-size",
              "Column": { "DataSetIdentifier": "DS1", "ColumnName": "count" },
              "AggregationFunction": { "SimpleNumericalAggregation": "SUM" }
            }
          }]
        }
      },
      "WordCloudOptions": {
        "WordOrientation": "HORIZONTAL",
        "WordScaling": "NORMAL",
        "CloudLayout": "FLUID",
        "WordCasing": "EXISTING_CASE",
        "WordPadding": "SMALL"
      }
    },
    "Actions": [], "ColumnHierarchies": []
  }
}
```

### RadarChartVisual

```json
{
  "RadarChartVisual": {
    "VisualId": "radar-comparison",
    "Title": { "Visibility": "VISIBLE", "FormatText": { "PlainText": "Multi-Metric Comparison" } },
    "ChartConfiguration": {
      "FieldWells": {
        "RadarChartAggregatedFieldWells": {
          "Category": [{
            "CategoricalDimensionField": {
              "FieldId": "dim-cat",
              "Column": { "DataSetIdentifier": "DS1", "ColumnName": "category" }
            }
          }],
          "Color": [],
          "Values": [{
            "NumericalMeasureField": {
              "FieldId": "metric-val",
              "Column": { "DataSetIdentifier": "DS1", "ColumnName": "score" },
              "AggregationFunction": { "SimpleNumericalAggregation": "SUM" }
            }
          }]
        }
      },
      "Shape": "POLYGON",
      "BaseSeriesSettings": { "AreaStyleSettings": { "Visibility": "HIDDEN" } },
      "StartAngle": 90.0,
      "AlternateBandColorsVisibility": "HIDDEN"
    },
    "Actions": [], "ColumnHierarchies": []
  }
}
```

### CustomContentVisual (Images, Banners, Embedded Content)

```json
{
  "CustomContentVisual": {
    "VisualId": "banner-image",
    "Title": { "Visibility": "HIDDEN" },
    "ChartConfiguration": {
      "ContentUrl": "https://example.com/banner.png",
      "ContentType": "IMAGE",
      "ImageScaling": "SCALE_TO_VISUAL"
    },
    "Actions": [{
      "CustomActionId": "nav-action",
      "Name": "NavigateToSheet",
      "Status": "ENABLED",
      "Trigger": "DATA_POINT_CLICK",
      "ActionOperations": [{
        "NavigationOperation": {
          "LocalNavigationConfiguration": { "TargetSheetId": "target-sheet-id" }
        }
      }]
    }],
    "DataSetIdentifier": "DS1"
  }
}
```
- ImageScaling: SCALE_TO_VISUAL, FIT_TO_HEIGHT, DO_NOT_SCALE
- ContentType: IMAGE, OTHER_EMBEDDED_CONTENT


---

## Parameters

### StringParameterDeclaration — Static Default

```json
{
  "StringParameterDeclaration": {
    "ParameterValueType": "SINGLE_VALUED",
    "Name": "SelectedRegion",
    "DefaultValues": { "StaticValues": ["All"] },
    "ValueWhenUnset": { "ValueWhenUnsetOption": "RECOMMENDED_VALUE" }
  }
}
```

### StringParameterDeclaration — Dynamic Default (from dataset)

```json
{
  "StringParameterDeclaration": {
    "ParameterValueType": "SINGLE_VALUED",
    "Name": "recipename",
    "DefaultValues": {
      "DynamicValue": {
        "UserNameColumn": { "DataSetIdentifier": "DS1", "ColumnName": "Name" },
        "DefaultValueColumn": { "DataSetIdentifier": "DS1", "ColumnName": "Name" }
      },
      "StaticValues": ["Default Value"]
    },
    "ValueWhenUnset": { "ValueWhenUnsetOption": "RECOMMENDED_VALUE" }
  }
}
```

### StringParameterDeclaration — Multi-Valued

```json
{
  "StringParameterDeclaration": {
    "ParameterValueType": "MULTI_VALUED",
    "Name": "SelectedBrands",
    "DefaultValues": { "StaticValues": ["HOKA", "UGG", "TEVA"] }
  }
}
```

### DateTimeParameterDeclaration — Rolling Date

```json
{
  "DateTimeParameterDeclaration": {
    "ParameterValueType": "SINGLE_VALUED",
    "Name": "StartDate",
    "TimeGranularity": "DAY",
    "DefaultValues": { "RollingDate": { "Expression": "NOW() - 90d" } }
  }
}
```

### IntegerParameterDeclaration

```json
{
  "IntegerParameterDeclaration": {
    "ParameterValueType": "SINGLE_VALUED",
    "Name": "TopN",
    "DefaultValues": { "StaticValues": [10] }
  }
}
```

---

## Filters

### CategoryFilter — Static Value

```json
{
  "FilterGroupId": "fg-region",
  "Filters": [{
    "CategoryFilter": {
      "FilterId": "filter-region",
      "Column": { "DataSetIdentifier": "DS1", "ColumnName": "region" },
      "Configuration": {
        "CustomFilterConfiguration": {
          "MatchOperator": "EQUALS",
          "CategoryValue": "US",
          "NullOption": "NON_NULLS_ONLY"
        }
      }
    }
  }],
  "ScopeConfiguration": { "SelectedSheets": { "SheetVisualScopingConfigurations": [{ "SheetId": "sheet-1", "Scope": "ALL_VISUALS" }] } },
  "Status": "ENABLED",
  "CrossDataset": "SINGLE_DATASET"
}
```

### CategoryFilter — Parameter-Driven (dynamic)

```json
{
  "CategoryFilter": {
    "FilterId": "filter-region-param",
    "Column": { "DataSetIdentifier": "DS1", "ColumnName": "region" },
    "Configuration": {
      "CustomFilterConfiguration": {
        "MatchOperator": "EQUALS",
        "ParameterName": "SelectedRegion",
        "NullOption": "NON_NULLS_ONLY"
      }
    }
  }
}
```

### CategoryFilter — FilterListConfiguration (multi-value)

```json
{
  "CategoryFilter": {
    "FilterId": "filter-brands",
    "Column": { "DataSetIdentifier": "DS1", "ColumnName": "brand" },
    "Configuration": {
      "FilterListConfiguration": {
        "MatchOperator": "CONTAINS",
        "CategoryValues": ["HOKA", "UGG"],
        "NullOption": "NON_NULLS_ONLY"
      }
    }
  }
}
```

### NumericRangeFilter

```json
{
  "NumericRangeFilter": {
    "FilterId": "filter-revenue-min",
    "Column": { "DataSetIdentifier": "DS1", "ColumnName": "revenue" },
    "IncludeMinimum": true, "IncludeMaximum": false,
    "RangeMinimum": { "StaticValue": 1000 },
    "NullOption": "ALL_VALUES"
  }
}
```

### TopBottomFilter

```json
{
  "TopBottomFilter": {
    "FilterId": "filter-top10",
    "Column": { "DataSetIdentifier": "DS1", "ColumnName": "product" },
    "Limit": 10,
    "AggregationSortConfigurations": [{
      "Column": { "DataSetIdentifier": "DS1", "ColumnName": "revenue" },
      "SortDirection": "DESC",
      "AggregationFunction": { "NumericalAggregationFunction": { "SimpleNumericalAggregation": "SUM" } }
    }]
  }
}
```

### TimeRangeFilter — Parameter-Driven

```json
{
  "TimeRangeFilter": {
    "FilterId": "filter-date-range",
    "Column": { "DataSetIdentifier": "DS1", "ColumnName": "order_date" },
    "RangeMinimumValue": { "Parameter": "StartDate" },
    "RangeMaximumValue": { "Parameter": "EndDate" },
    "NullOption": "NON_NULLS_ONLY"
  }
}
```

### RelativeDatesFilter

```json
{
  "RelativeDatesFilter": {
    "FilterId": "filter-last-12m",
    "Column": { "DataSetIdentifier": "DS1", "ColumnName": "order_date" },
    "AnchorDateConfiguration": { "AnchorOption": "NOW" },
    "TimeGranularity": "MONTH",
    "RelativeDateType": "LAST",
    "RelativeDateValue": 12,
    "MinimumGranularity": "DAY",
    "NullOption": "NON_NULLS_ONLY"
  }
}
```

### Filter Scope — ALL_VISUALS vs SELECTED_VISUALS

```json
{ "Scope": "ALL_VISUALS" }
{ "Scope": "SELECTED_VISUALS", "VisualIds": ["bar-by-region", "table-detail"] }
```

---

## Filter & Parameter Controls

### Dropdown ParameterControl (linked to dataset column)

```json
{
  "Dropdown": {
    "ParameterControlId": "pctrl-region",
    "Title": "Region",
    "SourceParameterName": "SelectedRegion",
    "DisplayOptions": {
      "SelectAllOptions": { "Visibility": "VISIBLE" },
      "TitleOptions": { "Visibility": "VISIBLE", "FontConfiguration": { "FontSize": { "Relative": "LARGE" } } },
      "InfoIconLabelOptions": { "Visibility": "HIDDEN" }
    },
    "Type": "SINGLE_SELECT",
    "SelectableValues": {
      "LinkToDataSetColumn": { "DataSetIdentifier": "DS1", "ColumnName": "region" }
    }
  }
}
```
Type: SINGLE_SELECT, MULTI_SELECT

### DateTimePicker ParameterControl

```json
{
  "DateTimePicker": {
    "ParameterControlId": "pctrl-start",
    "Title": "Start Date",
    "SourceParameterName": "StartDate",
    "DisplayOptions": { "TitleOptions": { "Visibility": "VISIBLE" }, "DateTimeFormat": "YYYY-MM-DD" }
  }
}
```

### Dropdown FilterControl

```json
{
  "Dropdown": {
    "FilterControlId": "ctrl-brand",
    "Title": "Brand",
    "SourceFilterId": "filter-brand",
    "Type": "MULTI_SELECT",
    "DisplayOptions": { "TitleOptions": { "Visibility": "VISIBLE" }, "SelectAllOptions": { "Visibility": "VISIBLE" } }
  }
}
```

---

## Custom Actions

### NavigationOperation (sheet-to-sheet)

```json
{
  "CustomActionId": "nav-to-detail",
  "Name": "GoToDetail",
  "Status": "ENABLED",
  "Trigger": "DATA_POINT_CLICK",
  "ActionOperations": [{
    "NavigationOperation": { "LocalNavigationConfiguration": { "TargetSheetId": "detail-sheet" } }
  }]
}
```

### SetParametersOperation — From clicked data point

```json
{
  "SetParametersOperation": {
    "ParameterValueConfigurations": [
      { "DestinationParameterName": "SelectedRegion", "Value": { "SourceField": "region-field-id" } },
      { "DestinationParameterName": "ViewMode", "Value": { "CustomValuesConfiguration": { "IncludeNullValue": false, "CustomValues": { "StringValues": ["detail"] } } } }
    ]
  }
}
```

### Combined Navigation + SetParameters (drill-through pattern)

```json
{
  "ActionOperations": [
    { "NavigationOperation": { "LocalNavigationConfiguration": { "TargetSheetId": "detail-sheet" } } },
    { "SetParametersOperation": { "ParameterValueConfigurations": [
      { "DestinationParameterName": "SelectedItem", "Value": { "SourceField": "item-field-id" } }
    ] } }
  ]
}
```

---

## Calculated Fields

Top-level in AnalysisDefinition:
```json
{
  "CalculatedFields": [
    { "DataSetIdentifier": "DS1", "Name": "revenue_per_order", "Expression": "sum({total_amount}) / count({order_id})" },
    { "DataSetIdentifier": "DS1", "Name": "discount_rate", "Expression": "sum({discount_dollars}) / sum({sub_total})" },
    { "DataSetIdentifier": "DS1", "Name": "rank_col", "Expression": "rank([{revenue} DESC], [{region}])" },
    { "DataSetIdentifier": "DS1", "Name": "pct_of_total", "Expression": "percentOfTotal(sum({revenue}), [{brand}])" },
    { "DataSetIdentifier": "DS1", "Name": "clean_time", "Expression": "replace({cook_time}, 'PT', '')" },
    { "DataSetIdentifier": "DS1", "Name": "running_total", "Expression": "runningCount({order_id}, [{order_date} ASC], [{region}])" }
  ]
}
```
Functions: sum, count, avg, min, max, distinctCount, rank, percentOfTotal, runningCount, replace, ifelse, toString, locate, concat, dateDiff, addDateTime, now, truncDate

---

## TextBoxes (Rich Text on Sheets)

```json
{
  "SheetTextBoxes": [
    { "SheetTextBoxId": "title-box", "Content": "<text-box><inline font-size=\"24px\"><b>Dashboard Title</b></inline></text-box>" },
    { "SheetTextBoxId": "param-text", "Content": "<text-box><inline font-size=\"16px\">Selected: </inline><inline><expression>${SelectedRegion}</expression></inline></text-box>" }
  ]
}
```

---

## Number Formatting

```json
{
  "FormatConfiguration": {
    "FormatConfiguration": {
      "NumberDisplayFormatConfiguration": {
        "DecimalPlacesConfiguration": { "DecimalPlaces": 2 },
        "NumberScale": "NONE",
        "SeparatorConfiguration": {
          "DecimalSeparator": "DOT",
          "ThousandsSeparator": { "Symbol": "COMMA", "Visibility": "VISIBLE" }
        },
        "NegativeValueConfiguration": { "DisplayMode": "NEGATIVE" },
        "NullValueFormatConfiguration": { "NullString": "N/A" }
      }
    }
  }
}
```
NumberScale: NONE, AUTO, THOUSANDS, MILLIONS, BILLIONS, TRILLIONS

---

## Visual Selection Guide

| Data pattern | Best visual |
|---|---|
| Single big number | KPIVisual |
| Metric across categories | BarChartVisual (HORIZONTAL, sorted DESC) |
| Trend over time | LineChartVisual |
| Distribution / proportion | PieChartVisual (with DonutOptions) |
| Detailed rows | TableVisual |
| Cross-tab (dim1 x dim2) | PivotTableVisual |
| Tag cloud / frequency | WordCloudVisual |
| Multi-metric comparison | RadarChartVisual |
| Banner / image | CustomContentVisual |

### Layout by Audience

| Audience | Approach |
|---|---|
| Executive / VP | KPI cards top + 1-2 charts. Clean. Max 5-6 visuals. |
| Manager | KPI cards + charts + table. Filters visible. 6-8 visuals. |
| Analyst | Dense. Pivot tables, detail tables, many filters. 8-12 visuals. |

## AWS Account & Data Source

- Account: Read from config/datasource.json at deploy time
- Region: Read from config/datasource.json at deploy time
- Config: config/datasource.json (Redshift, multi-environment, multi-schema)


---

## NEW Visual Types (learned from production analysis)

### TreeMapVisual

```json
{
  "TreeMapVisual": {
    "VisualId": "treemap-products",
    "Title": { "Visibility": "VISIBLE", "FormatText": { "RichText": "<visual-title>Products by Revenue</visual-title>" } },
    "ChartConfiguration": {
      "FieldWells": { "TreeMapAggregatedFieldWells": {
        "Groups": [{ "CategoricalDimensionField": { "FieldId": "f-prod-tree", "Column": { "DataSetIdentifier": "DS1", "ColumnName": "product_name" } } }],
        "Sizes": [{ "NumericalMeasureField": { "FieldId": "f-rev-tree", "Column": { "DataSetIdentifier": "DS1", "ColumnName": "revenue" }, "AggregationFunction": { "SimpleNumericalAggregation": "SUM" } } }],
        "Colors": []
      }},
      "SortConfiguration": { "TreeMapSort": [{ "FieldSort": { "FieldId": "f-rev-tree", "Direction": "DESC" } }], "TreeMapGroupItemsLimitConfiguration": { "ItemsLimit": 25, "OtherCategories": "INCLUDE" } },
      "DataLabels": { "Visibility": "VISIBLE", "Overlap": "DISABLE_OVERLAP" }
    },
    "Actions": [], "ColumnHierarchies": []
  }
}
```

### ComboChartVisual (bar + line on same chart)

```json
{
  "ComboChartVisual": {
    "VisualId": "combo-rev-orders",
    "Title": { "Visibility": "VISIBLE" },
    "ChartConfiguration": {
      "FieldWells": { "ComboChartAggregatedFieldWells": {
        "Category": [{ "DateDimensionField": { "FieldId": "f-date-combo", "Column": { "DataSetIdentifier": "DS1", "ColumnName": "order_date" }, "DateGranularity": "MONTH", "HierarchyId": "dth-combo" } }],
        "BarValues": [{ "NumericalMeasureField": { "FieldId": "f-rev-combo", "Column": { "DataSetIdentifier": "DS1", "ColumnName": "revenue" }, "AggregationFunction": { "SimpleNumericalAggregation": "SUM" } } }],
        "LineValues": [{ "NumericalMeasureField": { "FieldId": "f-qty-combo", "Column": { "DataSetIdentifier": "DS1", "ColumnName": "quantity" }, "AggregationFunction": { "SimpleNumericalAggregation": "SUM" } } }],
        "Colors": []
      }},
      "BarsArrangement": "CLUSTERED",
      "BarDataLabels": { "Visibility": "HIDDEN", "Overlap": "DISABLE_OVERLAP" }
    },
    "Actions": [],
    "ColumnHierarchies": [{ "DateTimeHierarchy": { "HierarchyId": "dth-combo" } }]
  }
}
```
- BarValues = measures shown as bars, LineValues = measures shown as lines
- Tooltip supports TooltipTarget: "BOTH", "BAR", "LINE"

### ScatterPlotVisual

```json
{
  "ScatterPlotVisual": {
    "VisualId": "scatter-analysis",
    "Title": { "Visibility": "VISIBLE" },
    "ChartConfiguration": {
      "FieldWells": { "ScatterPlotCategoricallyAggregatedFieldWells": {
        "XAxis": [{ "NumericalMeasureField": { "FieldId": "f-x-scatter", "Column": { "DataSetIdentifier": "DS1", "ColumnName": "discount" }, "AggregationFunction": { "SimpleNumericalAggregation": "AVERAGE" } } }],
        "YAxis": [{ "NumericalMeasureField": { "FieldId": "f-y-scatter", "Column": { "DataSetIdentifier": "DS1", "ColumnName": "quantity" }, "AggregationFunction": { "SimpleNumericalAggregation": "AVERAGE" } } }],
        "Category": [{ "CategoricalDimensionField": { "FieldId": "f-cat-scatter", "Column": { "DataSetIdentifier": "DS1", "ColumnName": "category" } } }],
        "Size": [], "Label": []
      }},
      "SortConfiguration": { "ScatterPlotLimitConfiguration": { "ItemsLimit": 2500, "OtherCategories": "EXCLUDE" } }
    },
    "Actions": [], "ColumnHierarchies": []
  }
}
```

### InsightVisual (ML-powered auto-insights)

```json
{
  "InsightVisual": {
    "VisualId": "insight-top-categories",
    "Title": { "Visibility": "VISIBLE" },
    "InsightConfiguration": {
      "Computations": [{
        "TopBottomRanked": {
          "ComputationId": "comp-top3",
          "Name": "Top",
          "Category": { "CategoricalDimensionField": { "FieldId": "f-cat-insight", "Column": { "DataSetIdentifier": "DS1", "ColumnName": "category" } } },
          "Value": { "NumericalMeasureField": { "FieldId": "f-rev-insight", "Column": { "DataSetIdentifier": "DS1", "ColumnName": "revenue" }, "AggregationFunction": { "SimpleNumericalAggregation": "SUM" } } },
          "ResultSize": 3,
          "Type": "TOP"
        }
      }]
    },
    "Actions": [],
    "DataSetIdentifier": "DS1"
  }
}
```
- InsightVisual uses InsightConfiguration (NOT ChartConfiguration)
- Has DataSetIdentifier at visual level
- Computation types: TopBottomRanked, GrowthRate, TotalAggregation, MaximumMinimum, MetricComparison, PeriodOverPeriod, PeriodToDate, Forecast, UniqueValues
- Empty Computations[] = QuickSight auto-generates insights

## Calculated Field Functions (from production)

```
countOver({column}, [{partition}], PRE_AGG)     — count per partition
minOver({column}, [{partition}], PRE_AGG)       — min per partition
maxOver({column}, [{partition}], PRE_AGG)       — max per partition
sumOver({column}, [{partition}], PRE_AGG)       — sum per partition
avgOver({column}, [{partition}], PRE_AGG)       — avg per partition
dateDiff({start_date}, {end_date}, 'DD')        — date difference in days
addDateTime(amount, 'DD', {date_column})        — add days to date
now()                                           — current timestamp
ifelse(condition1, result1, condition2, result2, default)
```

## Filter-to-Control Wiring (CORRECT pattern from production)

Filters work when FilterControls reference them via SourceFilterId:

```json
"FilterGroups": [{
  "FilterGroupId": "fg-1",
  "Filters": [{ "CategoryFilter": { "FilterId": "filter-brand", "Column": {...}, "Configuration": { "FilterListConfiguration": { "MatchOperator": "CONTAINS", "SelectAllOptions": "FILTER_ALL_VALUES", "NullOption": "NON_NULLS_ONLY" } } } }],
  "ScopeConfiguration": {...}, "Status": "ENABLED", "CrossDataset": "SINGLE_DATASET"
}]

"FilterControls": [{
  "Dropdown": { "FilterControlId": "ctrl-brand", "Title": "Brand", "SourceFilterId": "filter-brand", "DisplayOptions": { "SelectAllOptions": { "Visibility": "VISIBLE" } }, "Type": "MULTI_SELECT" }
}]

"SheetControlLayouts": [{ "Configuration": { "GridLayout": { "Elements": [
  { "ElementId": "ctrl-brand", "ElementType": "FILTER_CONTROL", "ColumnSpan": 2, "RowSpan": 1 }
] } } }]
```

DO NOT put filter controls in the main Layouts GridLayout. They go in SheetControlLayouts only.
