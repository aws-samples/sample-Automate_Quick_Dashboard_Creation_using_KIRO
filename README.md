# QuickSight Agentic Dashboard Generator

> **Important**: This code is provided as a sample implementation for educational purposes.
> It is NOT intended for production use without additional security hardening.
> See [SECURITY.md](SECURITY.md) for production recommendations.

Generate QuickSight dashboards from natural language using Kiro's multi-agent pipeline. Describe what you need, agents generate the code, deploy script creates DataSet + Analysis + Dashboard in QuickSight.

## Architecture

![Architecture](quicksight-architecture.png)

```
You: "Show me sales and revenue by brand, region, over time"
  │
  ▼
Agent 1 (Planner) ─── Asks dashboard type, parses into structured plan
  │
  ▼ [hook: on-plan-created]
Agent 2 (Dataset Builder) ─── Picks tables, defines joins
  │
  ▼ [hook: validate-dataset-config]
Agent 3 (Dashboard Designer) ─── Builds AnalysisDefinition (visuals, filters, layout)
  │
  ▼ [hook: validate-dashboard-definition]
deploy.py ─── Creates DataSource → DataSet → Analysis → Dashboard
  │
  ▼
QuickSight (via Redshift VPC Connection + Secrets Manager)
```

---

## Project Structure

```
├── config/
│   ├── datasource.json            # Connection config (placeholders — safe for git)
│   └── datasource.local.json      # Real credentials (git-ignored)
├── agents/
│   ├── agent1-planner.md          # NL request → structured plan
│   ├── agent2-dataset-builder.md  # Plan → dataset config (tables + joins)
│   └── agent3-dashboard-designer.md # Plan → AnalysisDefinition (visuals + layout)
├── scripts/
│   ├── deploy.py                  # QuickSight orchestrator (DataSource → DataSet → Analysis → Dashboard)
│   ├── discover_schema.py         # Redshift schema discovery utility
│   ├── setup_consumer360_demo.py  # Demo data setup
│   └── setup_demo_data.py         # Alternative demo data loader
├── output/                        # Generated artifacts (git-ignored)
│   ├── plan.json                  # Agent 1 output
│   ├── dataset-config.json        # Agent 2 output
│   ├── dashboard-definition.json  # Agent 3 output
│   └── deployment-info.json       # Deploy results with URLs
├── .kiro/
│   ├── steering/                  # Always-loaded LLM context
│   │   ├── iadp-data-models.md              # Star schema: tables, columns, joins
│   │   ├── quicksight-visuals.md            # Visual JSON patterns (KPI, Bar, Line, Pie, Table, Combo, etc.)
│   │   ├── dashboard-types.md              # Layout rules per dashboard type
│   │   ├── quicksight-calculated-fields.md  # Calculated field function reference
│   │   ├── quicksight-validation-rules.md   # Deployment error prevention rules
│   │   └── agent-orchestration.md           # Multi-agent pipeline instructions
│   ├── hooks/                     # Auto-trigger automation
│   │   ├── on-plan-created.json             # Triggers Agents 2+3 after plan is written
│   │   ├── validate-dataset-config.json     # Validates dataset config on save
│   │   └── validate-dashboard-definition.json # Validates dashboard def on save
│   └── skills/
│       └── quicksight-validator.md          # Manual validation skill (#quicksight-validator)
├── README.md
├── quicksight-architecture.png
├── quicksight-agentic-dashboard-guide.md
└── apj-pattern-submission.md
```

---

## Data Model (Consumer 360)

Agents build dashboards against the `consumer_360_secure` schema (Redshift star schema):

### Core Tables

| Table | Type | Purpose |
|-------|------|---------|
| `dim_consumer` | Dimension | Unified customer profile (5000 rows) |
| `dim_consumer_xref` | Dimension | Cross-reference for source system IDs |
| `dim_product_sku` | Dimension | Product catalog: SKU, brand, category, price |
| `fact_consumer_purchase_transaction` | Fact | Purchase transactions (25000 rows) |
| `fact_consumer_merkle_loyalty_event` | Fact | Loyalty points and events (15000 rows) |
| `fact_consumer_customer_support_contact` | Fact | Customer service contacts (8000 rows) |

### Key Dimensions
Brands: HOKA, UGG, TEVA, Koolaburra, Sanuk
Regions: North America, Europe, Asia Pacific, Latin America
Channels: DTC, Wholesale, Retail, Online
Tiers: Bronze, Silver, Gold, Platinum, Diamond

---

## Quick Start

### Prerequisites

- Python 3.9+
- `pip install boto3`
- AWS CLI configured
- QuickSight Enterprise subscription
- Redshift cluster with `consumer_360_secure` schema

### Step 1: Configure credentials

Copy the template and fill in your values:
```bash
cp config/datasource.json config/datasource.local.json
# Edit config/datasource.local.json with your real account details
```

The deploy script auto-detects `datasource.local.json` and uses it over the template.

### Step 2: Create DataSource (one-time)

```bash
python scripts/deploy.py --create-datasource
```

### Step 3: Ask for a dashboard

In Kiro chat:
> "Show me sales and revenue by brand and region, weekly/monthly/quarterly trends"

The agent pipeline handles the rest:
1. Agent 1 creates the plan → asks for confirmation
2. Hooks auto-trigger Agents 2+3 → generates dataset + dashboard configs
3. Validation hooks catch errors before deploy

### Step 4: Deploy

```bash
python scripts/deploy.py --cleanup
```

Dashboard URL printed on success.

---

## Deploy Commands

```bash
python scripts/deploy.py                    # First-time deploy
python scripts/deploy.py --cleanup          # Delete + recreate (iterating)
python scripts/deploy.py --dry-run          # Preview without API calls
python scripts/deploy.py --create-datasource # One-time DataSource setup
```

---

## Validation Pipeline

Errors are caught automatically before deployment via hooks and steering rules:

| Rule | What it prevents |
|------|-----------------|
| Alphanumeric table keys only | SYNTAX_ERROR in join OnClause |
| No DataSetIdentifierDeclarations in definition | "Resource not reachable" error |
| Filter control ↔ filter type matching | "Filter doesn't support control" error |
| STRING columns use CategoricalMeasureField | COLUMN_TYPE_INCOMPATIBLE error |
| DateDimensionField requires HierarchyId | Missing hierarchy error |
| No DonutChartVisual | Use PieChartVisual + DonutOptions |
| Unique FieldIds and VisualIds | Silent visual failures |

Validation triggers automatically on file save. Can also be invoked manually with `#quicksight-validator` in chat.

---

## Supported Dashboard Types

| Type | Best for |
|------|----------|
| Executive | VPs — KPIs + 1-2 charts, minimal filters |
| Sales | Revenue tracking — pipeline, targets, top customers |
| Analytical | Deep dive — many filters, drill-downs, interactive |
| Customer Analytics | Retention, churn, cohorts, behavior |
| Financial | Revenue vs cost, margins, budget tracking |
| Marketing | Campaigns, CTR, conversions, channel comparison |
| Operational | Day-to-day monitoring, real-time metrics |
| Strategic | Long-term goals, OKRs, forecasts |

---

## Example Prompts

```
"Executive dashboard: total revenue, orders, AOV, top 5 brands"
"Customer analytics: retention by tier, purchase frequency, churn risk"
"Sales dashboard: revenue by brand and region, weekly/monthly/quarterly trends"
"Loyalty dashboard: points earned vs redeemed, tier upgrades over time"
"Support dashboard: contact volume by channel, avg handle time, resolution rates"
```

---

## Setup Guide (New Account)

### 1. Get QuickSight User ARN
```bash
aws quicksight list-users --aws-account-id <ACCOUNT_ID> --namespace default --region <IDENTITY_REGION>
```

### 2. Get Redshift Cluster Details
```bash
aws redshift describe-clusters --region <REGION>
```

### 3. VPC Connection (private Redshift only)
```bash
aws quicksight list-vpc-connections --aws-account-id <ACCOUNT_ID> --region <REGION>
```
If none exists, create via QuickSight Console → Manage → VPC Connections.

### 4. Secrets Manager ARN
```bash
aws secretsmanager list-secrets --region <REGION> --query "SecretList[?contains(Name, 'redshift')].{Name:Name,ARN:ARN}"
```

### 5. Fill in `config/datasource.local.json`

```json
{
  "aws_account_id": "123456789012",
  "region": "us-east-1",
  "quicksight_user_arn": "arn:aws:quicksight:us-east-1:123456789012:user/default/YourUser",
  "redshift": {
    "cluster_id": "your-cluster",
    "host": "your-endpoint.region.redshift.amazonaws.com",
    "port": 5439,
    "database": "dev",
    "db_user": "awsuser",
    "credentials_secret_arn": "arn:aws:secretsmanager:...",
    "vpc_connection_arn": "arn:aws:quicksight:...:vpcConnection/..."
  },
  "schema": "consumer_360_secure",
  "datasource_id": "my-redshift-ds"
}
```

### 6. Verify permissions
- QuickSight service role has Redshift + VPC + Secrets Manager access
- Security group allows QuickSight VPC SG → Redshift port

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `SYNTAX_ERROR` on CreateDataSet | Table keys in dataset-config.json have hyphens — use alphanumeric only |
| "Resource not reachable in region" | Remove `DataSetIdentifierDeclarations` from dashboard definition |
| "Filter doesn't support DATE_PICKER" | Use `RelativeDateTime` control with `RelativeDatesFilter` |
| `COLUMN_TYPE_INCOMPATIBLE` | STRING column used as NumericalMeasureField — use CategoricalMeasureField |
| `CREATION_FAILED` (no visible error) | Run `aws quicksight describe-dashboard --query "Dashboard.Version.Errors"` |
| "Unable to route to host" | VPC connection missing or wrong endpoint |
| Security group blocking | Add SG-to-SG inbound rule on Redshift port |
| `AccessDeniedException: identity region` | Use identity region for QuickSight user calls |

---

## Extending

| Want to... | Do this |
|------------|---------|
| Add new data source tables | Update `.kiro/steering/iadp-data-models.md` |
| Add new visual types | Update `.kiro/steering/quicksight-visuals.md` |
| Add new dashboard layouts | Update `.kiro/steering/dashboard-types.md` |
| Add validation rules | Update `.kiro/steering/quicksight-validation-rules.md` + hooks |
| Connect different Redshift | Create new `config/datasource.local.json` |
| Add calculated field patterns | Update `.kiro/steering/quicksight-calculated-fields.md` |
