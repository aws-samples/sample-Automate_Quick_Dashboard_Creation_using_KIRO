---
inclusion: auto
---

# Dashboard Types & Layouts

When a user asks for a dashboard, ALWAYS ask them which type they want before proceeding. Present these options:

## Options to Present

1. **Executive Dashboard** — Quick overview for VPs/Directors. KPI cards + 1-2 charts. Insight in 5 seconds. Minimal filters.
2. **Operational Dashboard** — Day-to-day monitoring for managers. Real-time metrics, alerts, SLA tracking. More filters.
3. **Analytical Dashboard** — Deep dive for analysts. Highly interactive, drill-downs, cohorts, many filters.
4. **Sales Dashboard** — Revenue tracking. Pipeline, targets vs actual, top customers.
5. **Financial Dashboard** — Money tracking for CFO/finance. Revenue vs cost, margins, budget vs actual.
6. **Marketing Dashboard** — Campaign performance. CTR, conversions, funnel, channel comparison.
7. **Customer Analytics Dashboard** — User behavior for product/marketing. Retention, churn, cohorts, funnels.
8. **Strategic Dashboard** — Long-term goals for leadership. OKRs, growth trends, forecasts.

## Layout Rules Per Type

### 1. Executive Dashboard
- Grid: 36 columns
- Row 0: 3-4 KPI cards (ColumnSpan 9 each, RowSpan 5)
- Row 5: 1 bar chart (ColumnSpan 18) + 1 line chart (ColumnSpan 18), RowSpan 8
- Row 13: 1 pie/donut chart (ColumnSpan 14) + 1 table (ColumnSpan 22), RowSpan 9
- Filters: 1-2 max (brand dropdown + date range) in SheetControlLayouts
- Total visuals: 6-8
- NO clutter. Clean. White space is good.

### 2. Operational Dashboard
- Grid: 36 columns
- Row 0: 4-5 KPI cards with sparklines (ColumnSpan 7-8 each, RowSpan 5)
- Row 5: 2 line charts (trends over time) side by side, RowSpan 8
- Row 13: 1 combo chart (bar+line) + 1 table with alerts, RowSpan 10
- Row 23: 1 bar chart (breakdown) + 1 insight visual, RowSpan 8
- Filters: 3-4 (date range, status, region, category)
- Total visuals: 8-12

### 3. Analytical Dashboard
- Grid: 36 columns
- Row 0: 3 KPI cards (ColumnSpan 12 each, RowSpan 4)
- Row 4: 1 combo chart (full width, ColumnSpan 36), RowSpan 10
- Row 14: 1 scatter plot (ColumnSpan 18) + 1 treemap (ColumnSpan 18), RowSpan 10
- Row 24: 1 table (full width, ColumnSpan 36), RowSpan 12
- Row 36: 2-3 insight visuals, RowSpan 5
- Filters: 4-6 (date, region, brand, category, channel, customer segment)
- Total visuals: 10-14
- Highly interactive. Many drill-downs.

### 4. Sales Dashboard
- Row 0: 4 KPIs (Total Revenue, Orders, Avg Order Value, Unique Customers)
- Row 5: Bar chart (revenue by brand/product) + Line chart (revenue trend)
- Row 13: Pie chart (revenue by region/channel) + Table (top customers)
- Row 22: Combo chart (revenue vs quantity trend)
- Filters: brand, region, date range

### 5. Financial Dashboard
- Row 0: 4 KPIs (Revenue, Discount Total, Avg Discount Rate, Revenue After Discount)
- Row 5: Combo chart (revenue bars + discount line over time)
- Row 13: Bar chart (revenue by category) + Pie chart (discount distribution)
- Row 22: Table (detailed financial breakdown)
- Filters: date range, brand, category

### 6. Marketing Dashboard
- Row 0: 3 KPIs (Total Orders, Conversion Rate, Avg Discount)
- Row 5: Line chart (orders trend by channel) + Bar chart (revenue by channel)
- Row 13: Pie chart (channel distribution) + Scatter plot (discount vs revenue)
- Row 22: Table (campaign/channel detail)
- Filters: channel, date range, region

### 7. Customer Analytics Dashboard
- Row 0: 4 KPIs (Unique Customers, Avg Orders per Customer, Avg Days Between Orders, Revenue per Customer)
- Row 5: Line chart (customer count trend) + Bar chart (customers by region)
- Row 13: Scatter plot (order frequency vs revenue) + TreeMap (top customers)
- Row 22: Table (customer detail with revenue, orders, last order date)
- Filters: region, brand, date range, customer segment

### 8. Strategic Dashboard
- Row 0: 3 KPIs (Revenue Growth %, Order Growth %, Customer Growth %)
- Row 5: Line chart with forecast (revenue trend + 6 month forecast)
- Row 13: Combo chart (revenue + orders trend) + Insight visuals (growth rate, top movers)
- Row 22: Bar chart (YoY comparison by brand) + Table (quarterly summary)
- Filters: date range only
