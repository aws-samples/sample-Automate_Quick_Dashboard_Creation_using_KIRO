"""
Redshift Schema Discovery — queries actual tables, columns, row counts, and sample values.
Writes output/schema-discovery.json for agents to use when planning dashboards.

Usage:
  python scripts/discover_schema.py                # discover configured schema
  python scripts/discover_schema.py --sample       # include 5 sample rows per table
  python scripts/discover_schema.py --values       # include distinct values for string columns (top 20)
"""

import json, sys, time, argparse, boto3


def load_config():
    with open("config/datasource.json") as f:
        return json.load(f)


def run_query(client, cluster_id, database, db_user, sql):
    resp = client.execute_statement(
        ClusterIdentifier=cluster_id, Database=database, DbUser=db_user, Sql=sql
    )
    stmt_id = resp["Id"]
    for _ in range(60):
        time.sleep(2)
        status = client.describe_statement(Id=stmt_id)
        if status["Status"] == "FINISHED":
            break
        if status["Status"] in ("FAILED", "ABORTED"):
            print(f"  Query failed: {status.get('Error', 'unknown')}", flush=True)
            return None
    try:
        return client.get_statement_result(Id=stmt_id)
    except Exception as e:
        print(f"  Error: {e}", flush=True)
        return None


def cell_value(cell):
    if cell.get("isNull", False):
        return None
    for key in ("stringValue", "longValue", "doubleValue", "booleanValue"):
        if key in cell:
            return cell[key]
    return None


QS_TYPE_MAP = {
    "character varying": "STRING", "varchar": "STRING", "text": "STRING",
    "integer": "INTEGER", "bigint": "INTEGER", "smallint": "INTEGER",
    "numeric": "DECIMAL", "decimal": "DECIMAL", "double precision": "DECIMAL",
    "real": "DECIMAL", "float": "DECIMAL",
    "timestamp without time zone": "DATETIME", "timestamp with time zone": "DATETIME",
    "date": "DATETIME",
    "boolean": "STRING",
}


def discover(cfg, include_sample=False, include_values=False):
    region = cfg["region"]
    cluster_id = cfg["redshift"]["cluster_id"]
    database = cfg["redshift"]["database"]
    db_user = cfg["redshift"]["db_user"]
    schema = cfg.get("schema", "consumer_360_secure")

    client = boto3.client("redshift-data", region_name=region)
    print(f"\n{'='*60}", flush=True)
    print(f"Schema Discovery: {schema}", flush=True)
    print(f"Cluster: {cluster_id} | Database: {database}", flush=True)
    print(f"{'='*60}\n", flush=True)

    # 1. Get all tables and columns
    sql = f"""
    SELECT table_name, column_name, data_type, ordinal_position
    FROM information_schema.columns
    WHERE table_schema = '{schema}'
    ORDER BY table_name, ordinal_position;
    """
    print("Fetching table/column metadata...", flush=True)
    result = run_query(client, cluster_id, database, db_user, sql)
    if not result:
        print("FAILED: Could not read schema metadata.", flush=True)
        sys.exit(1)

    tables = {}
    for row in result.get("Records", []):
        tname = cell_value(row[0])
        cname = cell_value(row[1])
        dtype = cell_value(row[2])
        tables.setdefault(tname, {"columns": [], "row_count": None, "sample_data": [], "distinct_values": {}})
        tables[tname]["columns"].append({
            "name": cname,
            "data_type": dtype,
            "quicksight_type": QS_TYPE_MAP.get(dtype, "STRING")
        })

    print(f"Found {len(tables)} tables\n", flush=True)

    # 2. Row counts
    for tname in tables:
        print(f"  [{tname}] counting rows...", flush=True)
        r = run_query(client, cluster_id, database, db_user, f"SELECT COUNT(*) FROM {schema}.{tname};")
        if r and r.get("Records"):
            tables[tname]["row_count"] = cell_value(r["Records"][0][0])

    # 3. Sample data
    if include_sample:
        print("\nFetching sample data...", flush=True)
        for tname in tables:
            print(f"  [{tname}] sampling 5 rows...", flush=True)
            r = run_query(client, cluster_id, database, db_user, f"SELECT * FROM {schema}.{tname} LIMIT 5;")
            if r and r.get("Records"):
                col_names = [c["name"] for c in r.get("ColumnMetadata", [])]
                for row in r["Records"]:
                    tables[tname]["sample_data"].append(
                        {col_names[i]: cell_value(cell) for i, cell in enumerate(row)}
                    )

    # 4. Distinct values for string columns (top 20)
    if include_values:
        print("\nFetching distinct values for string columns...", flush=True)
        for tname in tables:
            string_cols = [c["name"] for c in tables[tname]["columns"]
                          if c["quicksight_type"] == "STRING"
                          and not c["name"].startswith("au_")
                          and c["name"] not in ("dim_consumer_key", "email", "name", "zipcode")]
            for col in string_cols:
                print(f"  [{tname}.{col}] distinct values...", flush=True)
                r = run_query(client, cluster_id, database, db_user,
                    f"SELECT {col}, COUNT(*) as cnt FROM {schema}.{tname} WHERE {col} IS NOT NULL GROUP BY {col} ORDER BY cnt DESC LIMIT 20;")
                if r and r.get("Records"):
                    tables[tname]["distinct_values"][col] = [
                        {"value": cell_value(row[0]), "count": cell_value(row[1])}
                        for row in r["Records"]
                    ]

    return {"schema": schema, "database": database, "cluster_id": cluster_id, "tables": tables}


def print_summary(discovery):
    schema = discovery["schema"]
    tables = discovery["tables"]
    print(f"\n{'='*60}", flush=True)
    print(f"DISCOVERY SUMMARY: {schema}", flush=True)
    print(f"{'='*60}\n", flush=True)

    for tname, tdata in sorted(tables.items()):
        rc = tdata["row_count"]
        nc = len(tdata["columns"])
        print(f"  {tname} ({rc:,} rows, {nc} columns)", flush=True)
        for col in tdata["columns"]:
            print(f"    - {col['name']:40s} {col['data_type']:30s} -> {col['quicksight_type']}", flush=True)

        if tdata.get("distinct_values"):
            print(f"    Distinct values:", flush=True)
            for col, vals in tdata["distinct_values"].items():
                val_str = ", ".join([f"{v['value']}({v['count']})" for v in vals[:5]])
                print(f"      {col}: {val_str}{'...' if len(vals) > 5 else ''}", flush=True)
        print()


def main():
    parser = argparse.ArgumentParser(description="Discover Redshift schema for dashboard generation")
    parser.add_argument("--sample", action="store_true", help="Include 5 sample rows per table")
    parser.add_argument("--values", action="store_true", help="Include distinct values for string columns")
    args = parser.parse_args()

    cfg = load_config()
    discovery = discover(cfg, include_sample=args.sample, include_values=args.values)

    # Write output
    out_path = "output/schema-discovery.json"
    with open(out_path, "w") as f:
        json.dump(discovery, f, indent=2, default=str)
    print(f"\nWritten to {out_path}", flush=True)

    print_summary(discovery)
    print(f"Total tables: {len(discovery['tables'])}", flush=True)
    total_rows = sum(t["row_count"] or 0 for t in discovery["tables"].values())
    print(f"Total rows: {total_rows:,}", flush=True)


if __name__ == "__main__":
    main()
