"""
QuickSight Orchestrator — Single deploy script.
Creates: DataSource -> DataSet -> Analysis -> Dashboard
Applies all known fixes to the definition before deploying.

Usage:
  python scripts/deploy.py --create-datasource   # one-time Redshift connection
  python scripts/deploy.py                        # deploy dataset + analysis + dashboard
  python scripts/deploy.py --cleanup              # delete existing, recreate
  python scripts/deploy.py --dry-run              # preview only
"""

import json, sys, os, time, copy, argparse, boto3
from collections import Counter


# ============================================================
# Config
# ============================================================

def load_json(path):
    with open(path) as f:
        return json.load(f)


def load_config():
    local_path = "config/datasource.local.json"
    default_path = "config/datasource.json"
    path = local_path if os.path.exists(local_path) else default_path
    cfg = load_json(path)
    return {
        "account_id": cfg["aws_account_id"],
        "region": cfg["region"],
        "user_arn": cfg["quicksight_user_arn"],
        "cluster_id": cfg["redshift"]["cluster_id"],
        "host": cfg["redshift"]["host"],
        "port": cfg["redshift"]["port"],
        "database": cfg["redshift"]["database"],
        "db_user": cfg["redshift"]["db_user"],
        "secret_arn": cfg["redshift"].get("credentials_secret_arn", ""),
        "vpc_connection_arn": cfg["redshift"].get("vpc_connection_arn", ""),
        "schema": cfg.get("schema", "public"),
        "datasource_id": cfg.get("datasource_id", f"qs-datasource-{cfg.get('schema', 'default')}"),
    }


def perms(arn, actions):
    return [{"Principal": arn, "Actions": actions}]


def delete_qs(qs, aid, rtype, rid):
    try:
        fn_map = {"data_set": qs.delete_data_set, "analysis": qs.delete_analysis,
                  "dashboard": qs.delete_dashboard}
        key_map = {"data_set": "DataSetId", "analysis": "AnalysisId", "dashboard": "DashboardId"}
        fn_map[rtype](AwsAccountId=aid, **{key_map[rtype]: rid})
        print(f"    Deleted {rtype}: {rid}", flush=True)
        time.sleep(2)
    except Exception:
        pass


def wait_for(check_fn, ok_status, label, timeout=120):
    for _ in range(timeout // 2):
        time.sleep(2)
        try:
            s = check_fn()
            if s == ok_status:
                print(f"  {label}: {s}", flush=True)
                return True
            if "FAILED" in str(s) or "ERROR" in str(s):
                print(f"  {label}: {s}", flush=True)
                return False
        except Exception:
            pass
    print(f"  {label}: TIMEOUT", flush=True)
    return False


# ============================================================
# Step 1: Create DataSource (one-time)
# ============================================================

def step1_create_datasource(qs, cfg):
    ds_id = cfg["datasource_id"]
    aid = cfg["account_id"]

    try:
        qs.delete_data_source(AwsAccountId=aid, DataSourceId=ds_id)
        print(f"    Deleted existing: {ds_id}", flush=True)
        time.sleep(2)
    except Exception:
        pass

    print(f"\n  [Step 1] Creating DataSource: {ds_id}", flush=True)

    # Get credentials
    creds = {"CredentialPair": {"Username": cfg["db_user"],
             "Password": os.environ.get("REDSHIFT_PASSWORD", "PLACEHOLDER")}}
    if cfg.get("secret_arn"):
        try:
            sm = boto3.client("secretsmanager", region_name=cfg.get("region", "us-east-1"))
            secret = sm.get_secret_value(SecretId=cfg["secret_arn"])
            secret_dict = json.loads(secret["SecretString"])
            creds = {"CredentialPair": {"Username": secret_dict.get("username", cfg["db_user"]),
                     "Password": secret_dict["password"]}}
            print(f"    Credentials from Secrets Manager", flush=True)
        except Exception as e:
            print(f"    Warning: {e}. Using REDSHIFT_PASSWORD env var.", flush=True)

    create_args = {
        "AwsAccountId": aid, "DataSourceId": ds_id,
        "Name": "IADP Redshift DataSource",
        "Type": "REDSHIFT",
        "DataSourceParameters": {"RedshiftParameters": {
            "Host": cfg["host"], "Port": cfg["port"], "Database": cfg["database"]
        }},
        "Credentials": creds,
        "Permissions": perms(cfg["user_arn"], [
            "quicksight:DescribeDataSource", "quicksight:DescribeDataSourcePermissions",
            "quicksight:PassDataSource", "quicksight:UpdateDataSource",
            "quicksight:DeleteDataSource", "quicksight:UpdateDataSourcePermissions"
        ])
    }

    if cfg.get("vpc_connection_arn"):
        create_args["VpcConnectionProperties"] = {"VpcConnectionArn": cfg["vpc_connection_arn"]}
        print(f"    VPC: {cfg['vpc_connection_arn'].split('/')[-1]}", flush=True)

    resp = qs.create_data_source(**create_args)
    print(f"    ARN: {resp.get('Arn', '')}", flush=True)
    print(f"    Status: {resp.get('CreationStatus', '?')}", flush=True)
    return resp.get("Arn", "")


def get_datasource_arn(qs, cfg):
    try:
        resp = qs.describe_data_source(AwsAccountId=cfg["account_id"], DataSourceId=cfg["datasource_id"])
        arn = resp["DataSource"]["Arn"]
        print(f"    DataSource: {cfg['datasource_id']} ({resp['DataSource']['Status']})", flush=True)
        return arn
    except Exception:
        print(f"    ERROR: DataSource '{cfg['datasource_id']}' not found.", flush=True)
        print(f"    Run: python scripts/deploy.py --create-datasource", flush=True)
        sys.exit(1)


# ============================================================
# Step 2: Create DataSet (direct table refs + joins)
# ============================================================

def safe_key(k):
    """QuickSight map keys must match [0-9a-zA-Z-]*"""
    return k.replace("_", "-")


def step2_create_dataset(qs, cfg, ds_cfg, ds_arn, cleanup):
    aid = cfg["account_id"]
    did = ds_cfg["dataset_id"]
    if cleanup:
        delete_qs(qs, aid, "data_set", did)

    print(f"\n  [Step 2] Creating DataSet: {did}", flush=True)

    tables = ds_cfg.get("tables", {})
    joins = ds_cfg.get("joins", [])

    # Fallback to CustomSql if no tables defined
    if "sql" in ds_cfg and not tables:
        type_map = {"STRING": "STRING", "INTEGER": "INTEGER", "DECIMAL": "DECIMAL", "DATETIME": "DATETIME"}
        cols = [{"Name": c["name"], "Type": type_map.get(c["type"], "STRING")} for c in ds_cfg["columns"]]
        resp = qs.create_data_set(
            AwsAccountId=aid, DataSetId=did, Name=ds_cfg.get("dataset_name", did),
            ImportMode=ds_cfg.get("import_mode", "DIRECT_QUERY"),
            PhysicalTableMap={"main": {"CustomSql": {"DataSourceArn": ds_arn, "Name": did, "SqlQuery": ds_cfg["sql"], "Columns": cols}}},
            Permissions=perms(cfg["user_arn"], [
                "quicksight:DescribeDataSet","quicksight:DescribeDataSetPermissions","quicksight:PassDataSet",
                "quicksight:DescribeIngestion","quicksight:ListIngestions","quicksight:UpdateDataSet",
                "quicksight:DeleteDataSet","quicksight:CreateIngestion","quicksight:CancelIngestion","quicksight:UpdateDataSetPermissions"]))
        print(f"    ARN: {resp.get('Arn', '')}", flush=True)
        return resp.get("Arn", "")

    # Build PhysicalTableMap
    type_map = {"STRING": "STRING", "INTEGER": "INTEGER", "DECIMAL": "DECIMAL", "DATETIME": "DATETIME"}
    physical_map = {}
    for tk, td in tables.items():
        schema = td.get("schema", cfg.get("schema", "public"))
        cols = [{"Name": c["name"], "Type": type_map.get(c["type"], "STRING")} for c in td["columns"]]
        physical_map[safe_key(tk)] = {"RelationalTable": {"DataSourceArn": ds_arn, "Schema": schema, "Name": td["name"], "InputColumns": cols}}
        print(f"    Table: {schema}.{td['name']} ({len(cols)} cols)", flush=True)

    # Build LogicalTableMap with column conflict resolution
    logical_map = {}
    first_table = list(tables.keys())[0]
    all_cols = Counter()
    for tk, td in tables.items():
        for col in td["columns"]:
            all_cols[col["name"]] += 1
    dupes = {name for name, count in all_cols.items() if count > 1}
    renamed = {}

    for tk in tables:
        sk = safe_key(tk)
        transforms = []
        if tk != first_table:
            for col in tables[tk]["columns"]:
                if col["name"] in dupes:
                    new_name = f"{tk}_{col['name']}"
                    transforms.append({"RenameColumnOperation": {"ColumnName": col["name"], "NewColumnName": new_name}})
                    renamed[(tk, col["name"])] = new_name
        entry = {"Alias": sk, "Source": {"PhysicalTableId": sk}}
        if transforms:
            entry["DataTransforms"] = transforms
        logical_map[sk] = entry

    # Build join chain (single root)
    last_join_id = None
    for i, j in enumerate(joins):
        join_id = f"join-{i+1}"
        left = safe_key(j["left"]) if last_join_id is None else last_join_id
        right = safe_key(j["right"])
        left_col = renamed.get((j["left"], j["on"]["left_column"]), j["on"]["left_column"])
        right_col = renamed.get((j["right"], j["on"]["right_column"]), j["on"]["right_column"])
        jtype = j.get("type", "INNER")

        logical_map[join_id] = {"Alias": join_id, "Source": {"JoinInstruction": {
            "LeftOperand": left, "RightOperand": right, "Type": jtype,
            "OnClause": f"{left_col} = {right_col}"
        }}}
        print(f"    Join: {left}.{left_col} = {right}.{right_col} ({jtype})", flush=True)
        last_join_id = join_id

    resp = qs.create_data_set(
        AwsAccountId=aid, DataSetId=did, Name=ds_cfg.get("dataset_name", did),
        ImportMode=ds_cfg.get("import_mode", "DIRECT_QUERY"),
        PhysicalTableMap=physical_map, LogicalTableMap=logical_map,
        Permissions=perms(cfg["user_arn"], [
            "quicksight:DescribeDataSet","quicksight:DescribeDataSetPermissions","quicksight:PassDataSet",
            "quicksight:DescribeIngestion","quicksight:ListIngestions","quicksight:UpdateDataSet",
            "quicksight:DeleteDataSet","quicksight:CreateIngestion","quicksight:CancelIngestion","quicksight:UpdateDataSetPermissions"]))
    print(f"    ARN: {resp.get('Arn', '')}", flush=True)
    return resp.get("Arn", "")


# ============================================================
# Definition Fixer — applies all known API fixes
# ============================================================

HIERARCHY_CAPABLE = {"LineChartVisual", "BarChartVisual", "PieChartVisual",
                     "KPIVisual", "ComboChartVisual", "ScatterPlotVisual",
                     "RadarChartVisual", "WordCloudVisual"}


def fix_definition(defn):
    """Apply all known QuickSight API fixes to the definition."""

    # Fix: Remove ParameterValueType from DateTimeParameterDeclaration
    for p in defn.get("ParameterDeclarations", []):
        if "DateTimeParameterDeclaration" in p:
            p["DateTimeParameterDeclaration"].pop("ParameterValueType", None)

    # Fix: Pagination must be 100/500/1000/10000
    def fix_pagination(obj):
        if isinstance(obj, dict):
            if "PaginationConfiguration" in obj:
                ps = obj["PaginationConfiguration"].get("PageSize", 100)
                valid = [100, 500, 1000, 10000]
                obj["PaginationConfiguration"]["PageSize"] = min((v for v in valid if v >= ps), default=10000)
            for val in obj.values():
                fix_pagination(val)
        elif isinstance(obj, list):
            for item in obj:
                fix_pagination(item)
    fix_pagination(defn)

    # Fix: Add RESPONSIVE layout
    defn["AnalysisDefaults"] = {
        "DefaultNewSheetConfiguration": {
            "InteractiveLayoutConfiguration": {
                "Grid": {"CanvasSizeOptions": {"ScreenCanvasSizeOptions": {"ResizeOption": "RESPONSIVE"}}}
            },
            "SheetContentType": "INTERACTIVE"
        }
    }

    for sheet in defn.get("Sheets", []):
        new_visuals = []
        for v in sheet.get("Visuals", []):
            vtype = list(v.keys())[0]
            visual = v[vtype]

            # Fix: DonutChartVisual -> PieChartVisual
            if vtype == "DonutChartVisual":
                fw = visual["ChartConfiguration"]["FieldWells"]["DonutChartAggregatedFieldWells"]
                v = {"PieChartVisual": {
                    "VisualId": visual["VisualId"],
                    "Title": visual.get("Title", {}), "Subtitle": visual.get("Subtitle", {}),
                    "ChartConfiguration": {
                        "FieldWells": {"PieChartAggregatedFieldWells": {"Category": fw["Category"], "Values": fw["Values"]}},
                        "DonutOptions": visual["ChartConfiguration"].get("DonutOptions", {})
                    },
                    "Actions": [], "ColumnHierarchies": []
                }}
                vtype = "PieChartVisual"
                visual = v[vtype]

            # Fix: DateDimensionField must have HierarchyId + matching ColumnHierarchies
            counter = [0]
            hierarchies = []

            def patch_dates(obj):
                if isinstance(obj, dict):
                    if "DateDimensionField" in obj:
                        ddf = obj["DateDimensionField"]
                        if "HierarchyId" not in ddf:
                            counter[0] += 1
                            h_id = f"dth-{visual['VisualId']}-{counter[0]}"
                            ddf["HierarchyId"] = h_id
                            hierarchies.append({"DateTimeHierarchy": {"HierarchyId": h_id, "DrillDownFilters": []}})
                        else:
                            hierarchies.append({"DateTimeHierarchy": {"HierarchyId": ddf["HierarchyId"], "DrillDownFilters": []}})
                        return
                    for val in obj.values():
                        patch_dates(val)
                elif isinstance(obj, list):
                    for item in obj:
                        patch_dates(item)

            patch_dates(visual.get("ChartConfiguration", {}))

            if vtype in HIERARCHY_CAPABLE:
                visual["ColumnHierarchies"] = hierarchies
            else:
                visual.pop("ColumnHierarchies", None)

            new_visuals.append(v)
        sheet["Visuals"] = new_visuals

    return defn


# ============================================================
# Step 3: Create Analysis
# ============================================================

def step3_create_analysis(qs, cfg, defn, analysis_id, name, dataset_arns, cleanup):
    aid = cfg["account_id"]
    if cleanup:
        delete_qs(qs, aid, "analysis", analysis_id)

    print(f"\n  [Step 3] Creating Analysis: {analysis_id}", flush=True)

    adef = copy.deepcopy(defn)
    adef.pop("DataSetConfigurations", None)
    if "DataSetIdentifierDeclarations" not in adef:
        adef["DataSetIdentifierDeclarations"] = [
            {"Identifier": ph, "DataSetArn": arn} for ph, arn in dataset_arns.items()
        ]

    adef = fix_definition(adef)

    resp = qs.create_analysis(AwsAccountId=aid, AnalysisId=analysis_id, Name=name,
        Definition=adef,
        Permissions=perms(cfg["user_arn"], [
            "quicksight:RestoreAnalysis","quicksight:UpdateAnalysisPermissions",
            "quicksight:DeleteAnalysis","quicksight:DescribeAnalysisPermissions",
            "quicksight:QueryAnalysis","quicksight:DescribeAnalysis","quicksight:UpdateAnalysis"]))
    print(f"    {resp.get('CreationStatus','?')}", flush=True)

    def chk():
        d = qs.describe_analysis(AwsAccountId=aid, AnalysisId=analysis_id)
        s = d["Analysis"]["Status"]
        if "ERROR" in s:
            for e in d["Analysis"].get("Errors",[]): print(f"      {e}", flush=True)
        return s
    wait_for(chk, "CREATION_SUCCESSFUL", "Analysis")
    return resp.get("Arn", "")


# ============================================================
# Step 4: Create Dashboard
# ============================================================

def step4_create_dashboard(qs, cfg, defn, dashboard_id, name, dataset_arns, cleanup):
    aid = cfg["account_id"]
    if cleanup:
        delete_qs(qs, aid, "dashboard", dashboard_id)

    print(f"\n  [Step 4] Creating Dashboard: {dashboard_id}", flush=True)

    ddef = copy.deepcopy(defn)
    ddef.pop("DataSetConfigurations", None)
    if "DataSetIdentifierDeclarations" not in ddef:
        ddef["DataSetIdentifierDeclarations"] = [
            {"Identifier": ph, "DataSetArn": arn} for ph, arn in dataset_arns.items()
        ]

    ddef = fix_definition(ddef)

    # Dashboard doesn't support QueryExecutionOptions
    ddef.pop("QueryExecutionOptions", None)

    resp = qs.create_dashboard(AwsAccountId=aid, DashboardId=dashboard_id, Name=name,
        Definition=ddef,
        Permissions=perms(cfg["user_arn"], [
            "quicksight:DescribeDashboard","quicksight:ListDashboardVersions",
            "quicksight:UpdateDashboardPermissions","quicksight:QueryDashboard",
            "quicksight:UpdateDashboard","quicksight:DeleteDashboard",
            "quicksight:UpdateDashboardPublishedVersion","quicksight:DescribeDashboardPermissions"]),
        DashboardPublishOptions={"AdHocFilteringOption":{"AvailabilityStatus":"ENABLED"},
            "ExportToCSVOption":{"AvailabilityStatus":"ENABLED"},
            "SheetControlsOption":{"VisibilityState":"EXPANDED"}})
    print(f"    {resp.get('CreationStatus','?')}", flush=True)

    def chk():
        d = qs.describe_dashboard(AwsAccountId=aid, DashboardId=dashboard_id)
        v = d["Dashboard"]["Version"]
        s = v["Status"]
        if "FAILED" in s:
            for e in v.get("Errors",[]): print(f"      {e}", flush=True)
        return s
    wait_for(chk, "CREATION_SUCCESSFUL", "Dashboard")
    return resp.get("Arn", "")


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="QuickSight Orchestrator")
    parser.add_argument("--create-datasource", action="store_true", help="One-time: create Redshift DataSource")
    parser.add_argument("--cleanup", action="store_true", help="Delete existing resources first")
    parser.add_argument("--dry-run", action="store_true", help="Preview, no API calls")
    args = parser.parse_args()

    cfg = load_config()
    print("=" * 55, flush=True)
    print("  QuickSight Orchestrator", flush=True)
    print("=" * 55, flush=True)
    print(f"  Account:    {cfg['account_id']}", flush=True)
    print(f"  Region:     {cfg['region']}", flush=True)
    print(f"  Cluster:    {cfg['cluster_id']}", flush=True)
    print(f"  Database:   {cfg['database']}", flush=True)
    print(f"  Schema:     {cfg['schema']}", flush=True)

    qs = boto3.client("quicksight", region_name=cfg["region"])

    # One-time datasource creation
    if args.create_datasource:
        step1_create_datasource(qs, cfg)
        print("\n  DataSource created. Now run: python scripts/deploy.py", flush=True)
        return

    # Load agent-generated artifacts
    for p in ["output/dataset-config.json", "output/dashboard-definition.json"]:
        if not os.path.exists(p):
            print(f"\n  ERROR: {p} not found.", flush=True)
            print("  Ask Kiro to generate a dashboard first.", flush=True)
            sys.exit(1)

    ds_cfg = load_json("output/dataset-config.json")
    dash_def = load_json("output/dashboard-definition.json")

    # Support single or multiple datasets
    is_multi = "datasets" in ds_cfg
    dataset_list = ds_cfg["datasets"] if is_multi else [ds_cfg]

    analysis_id = dash_def.get("analysis_id", dataset_list[0]["dataset_id"].replace("-dataset", "-analysis"))
    dashboard_id = dash_def.get("dashboard_id", dataset_list[0]["dataset_id"].replace("-dataset", "-dashboard"))
    name = dash_def.get("dashboard_name", "Dashboard")
    defn = dash_def["definition"]

    vis = sum(len(s.get("Visuals", [])) for s in defn.get("Sheets", []))
    flt = len(defn.get("FilterGroups", []))
    par = len(defn.get("ParameterDeclarations", []))

    print(f"\n  Datasets:   {len(dataset_list)}", flush=True)
    for d in dataset_list:
        tbl_count = len(d.get("tables", {}))
        print(f"    - {d['dataset_id']} ({tbl_count} tables)", flush=True)
    print(f"  Analysis:   {analysis_id}", flush=True)
    print(f"  Dashboard:  {dashboard_id}", flush=True)
    print(f"  Visuals: {vis}  Filters: {flt}  Params: {par}", flush=True)

    if args.dry_run:
        for d in dataset_list:
            if "sql" in d:
                print(f"\n  [{d['dataset_id']}] SQL: {d['sql'][:150]}...", flush=True)
            else:
                print(f"\n  [{d['dataset_id']}] Tables: {list(d.get('tables', {}).keys())}", flush=True)
                for j in d.get("joins", []):
                    print(f"    Join: {j['left']}.{j['on']['left_column']} = {j['right']}.{j['on']['right_column']}", flush=True)
        print("\n  [DRY RUN] No API calls.", flush=True)
        return

    # Step 1: Verify DataSource
    print("\n  [Step 1] Verify DataSource", flush=True)
    ds_arn = get_datasource_arn(qs, cfg)

    # Step 2: Create all datasets
    placeholders = dash_def.get("dataset_placeholders", {})
    dataset_arns = {}
    for i, d in enumerate(dataset_list):
        arn = step2_create_dataset(qs, cfg, d, ds_arn, args.cleanup)
        ph = placeholders.get(d["dataset_id"], f"DS{i+1}" if is_multi else "DS1")
        dataset_arns[ph] = arn

    # Step 3: Create Analysis
    analysis_arn = step3_create_analysis(qs, cfg, defn, analysis_id, f"{name} (Analysis)", dataset_arns, args.cleanup)

    # Step 4: Create Dashboard
    dashboard_arn = step4_create_dashboard(qs, cfg, defn, dashboard_id, name, dataset_arns, args.cleanup)

    # Save result
    region = cfg["region"]
    result = {
        "datasets": {ph: arn for ph, arn in dataset_arns.items()},
        "analysis_id": analysis_id, "analysis_arn": analysis_arn,
        "analysis_url": f"https://{region}.quicksight.aws.amazon.com/sn/analyses/{analysis_id}",
        "dashboard_id": dashboard_id, "dashboard_arn": dashboard_arn,
        "dashboard_url": f"https://{region}.quicksight.aws.amazon.com/sn/dashboards/{dashboard_id}",
    }
    os.makedirs("output", exist_ok=True)
    with open("output/deployment-info.json", "w") as f:
        json.dump(result, f, indent=2)

    print(f"\n  Analysis:  {result['analysis_url']}", flush=True)
    print(f"  Dashboard: {result['dashboard_url']}", flush=True)
    print(f"\n  Done!", flush=True)


if __name__ == "__main__":
    main()
