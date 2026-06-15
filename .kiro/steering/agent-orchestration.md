---
inclusion: auto
---

# Agent Orchestration

When a user asks for a dashboard, you are the LLM powering a 4-agent pipeline. Follow this process:

## Step 1: Planner (Agent 1)
Read `agents/agent1-planner.md` for full instructions.
- Parse the user's natural language request
- Identify metrics, dimensions, filters, audience, visual suggestions
- Use the data model from `iadp-data-models.md` steering file to find the right tables/columns
- Write `output/plan.json`
- Ask user for confirmation before proceeding

## Step 2: Dataset Builder (Agent 2)
Read `agents/agent2-dataset-builder.md` for full instructions.
- Take the plan and build QuickSight dataset config
- Use direct Redshift table references (NOT SQL)
- Define joins via QuickSight LogicalTableMap
- Write `output/dataset-config.json`

## Step 3: Dashboard Designer (Agent 3)
Read `agents/agent3-dashboard-designer.md` for full instructions.
- Take the plan + dataset config and build the AnalysisDefinition
- Use visual patterns from `quicksight-visuals.md` steering file
- Create parameters, filters, controls, visuals, layout
- Write `output/dashboard-definition.json`

## Step 4: Deploy (Agent 4 = scripts/deploy.py)
- User runs: `python scripts/deploy.py --create-datasource` (one-time)
- User runs: `python scripts/deploy.py --cleanup` (creates DataSet + Analysis + Dashboard)

## Automation
A hook (`.kiro/hooks/on-plan-created.json`) automatically triggers Steps 2+3 when `output/plan.json` is created. So the user only needs to:
1. Describe the dashboard → you create the plan
2. Confirm → hook runs agents 2+3 automatically
3. Run deploy script

## Key Files
- `agents/agent1-planner.md` — Planner instructions
- `agents/agent2-dataset-builder.md` — Dataset Builder instructions
- `agents/agent3-dashboard-designer.md` — Dashboard Designer instructions
- `output/plan.json` — Agent 1 output (triggers hook)
- `output/dataset-config.json` — Agent 2 output
- `output/dashboard-definition.json` — Agent 3 output
- `scripts/deploy.py` — Agent 4 (QuickSight Orchestrator)
