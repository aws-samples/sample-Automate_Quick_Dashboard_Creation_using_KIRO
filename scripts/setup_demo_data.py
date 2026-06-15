"""
Setup demo data in Redshift using Redshift Data API (no direct connection needed).
Creates: demo_shoes schema with dim_brand, dim_region, dim_product, fact_orders (~10K rows)

Usage:
  python scripts/setup_demo_data.py
  python scripts/setup_demo_data.py --drop
"""

import boto3
import json
import json
import os
import random
import time
import argparse
from datetime import datetime, timedelta

random.seed(42)

SCHEMA = _cfg.get("schema", "demo_shoes")

# Load config
import os as _os
_cfg_path = _os.path.join(_os.path.dirname(__file__), "..", "config", "datasource.json")
with open(_cfg_path) as _f:
    _cfg = json.loads(_f.read())
_rs = _cfg["redshift"]

CLUSTER = _rs["cluster_id"]
DATABASE = _rs["database"]
DB_USER = _rs["db_user"]
REGION = _cfg["region"]
SECRET_ARN = _rs.get("credentials_secret_arn", "")


def run_sql(client, sql, wait=True):
    """Execute SQL via Redshift Data API."""
    resp = client.execute_statement(
        ClusterIdentifier=CLUSTER,
        Database=DATABASE,
        SecretArn=SECRET_ARN,
        Sql=sql,
    )
    stmt_id = resp["Id"]
    if not wait:
        return stmt_id

    # Poll for completion
    for _ in range(120):
        time.sleep(1)
        status = client.describe_statement(Id=stmt_id)
        state = status["Status"]
        if state == "FINISHED":
            return stmt_id
        elif state == "FAILED":
            print(f"    FAILED: {status.get('Error', 'unknown')}")
            return None
        elif state == "ABORTED":
            print(f"    ABORTED")
            return None
    print("    TIMEOUT waiting for SQL")
    return None


def run_batch(client, sqls):
    """Execute multiple SQL statements via batch API."""
    resp = client.batch_execute_statement(
        ClusterIdentifier=CLUSTER,
        Database=DATABASE,
        SecretArn=SECRET_ARN,
        Sqls=sqls,
    )
    stmt_id = resp["Id"]
    for _ in range(120):
        time.sleep(1)
        status = client.describe_statement(Id=stmt_id)
        state = status["Status"]
        if state == "FINISHED":
            return True
        elif state in ("FAILED", "ABORTED"):
            print(f"    {state}: {status.get('Error', 'unknown')}")
            return False
    print("    TIMEOUT")
    return False


BRANDS = [
    (1, "HOKA", "Performance"),
    (2, "UGG", "Lifestyle"),
    (3, "TEVA", "Outdoor"),
    (4, "Koolaburra", "Lifestyle"),
    (5, "Sanuk", "Casual"),
]

REGIONS = [
    (1, "North America", "USA", "DTC"),
    (2, "North America", "USA", "Wholesale"),
    (3, "North America", "Canada", "DTC"),
    (4, "Europe", "UK", "DTC"),
    (5, "Europe", "Germany", "Wholesale"),
    (6, "Asia Pacific", "Japan", "DTC"),
    (7, "Asia Pacific", "Australia", "Retail"),
    (8, "Latin America", "Brazil", "Wholesale"),
]

PRODUCTS = [
    (1, "Clifton 9", 1, "Running", 149.99, "Unisex"),
    (2, "Bondi 8", 1, "Running", 164.99, "Unisex"),
    (3, "Speedgoat 5", 1, "Trail", 154.99, "Unisex"),
    (4, "Mach 6", 1, "Running", 139.99, "Unisex"),
    (5, "Classic Short Boot", 2, "Boots", 169.99, "Women"),
    (6, "Classic Mini Boot", 2, "Boots", 149.99, "Women"),
    (7, "Neumel Boot", 2, "Boots", 139.99, "Men"),
    (8, "Tasman Slipper", 2, "Slippers", 119.99, "Unisex"),
    (9, "Fluff Yeah Slide", 2, "Slippers", 99.99, "Women"),
    (10, "Hurricane XLT2", 3, "Sandals", 74.99, "Unisex"),
    (11, "Original Universal", 3, "Sandals", 54.99, "Unisex"),
    (12, "Tirra", 3, "Sandals", 79.99, "Women"),
    (13, "Terra Fi 5", 3, "Sandals", 89.99, "Men"),
    (14, "Lainey Slipper", 4, "Slippers", 59.99, "Women"),
    (15, "Aira Short Boot", 4, "Boots", 79.99, "Women"),
    (16, "Burro Boot", 4, "Boots", 69.99, "Men"),
    (17, "Vagabond", 5, "Casual", 64.99, "Men"),
    (18, "Yoga Sling", 5, "Casual", 39.99, "Women"),
    (19, "Sidewalk Surfer", 5, "Casual", 54.99, "Men"),
    (20, "Donna Hemp", 5, "Casual", 49.99, "Women"),
]


def generate_orders(n=10000):
    orders = []
    start = datetime(2024, 1, 1)
    end = datetime(2026, 3, 31)
    days = (end - start).days

    brand_products = {}
    for p in PRODUCTS:
        brand_products.setdefault(p[2], []).append(p)

    brand_weights = {1: 0.35, 2: 0.30, 3: 0.15, 4: 0.10, 5: 0.10}
    region_weights = [0.25, 0.15, 0.08, 0.12, 0.10, 0.12, 0.10, 0.08]

    for i in range(1, n + 1):
        day_offset = random.randint(0, days)
        order_date = start + timedelta(days=day_offset)

        brand_id = random.choices(list(brand_weights.keys()), weights=list(brand_weights.values()))[0]
        product = random.choice(brand_products[brand_id])
        region = random.choices(REGIONS, weights=region_weights)[0]

        quantity = random.choices([1, 2, 3, 4, 5], weights=[50, 30, 12, 5, 3])[0]
        discount = random.choices([0, 0.05, 0.10, 0.15, 0.20, 0.25],
                                  weights=[40, 20, 20, 10, 7, 3])[0]
        revenue = round(product[4] * quantity * (1 - discount), 2)
        customer_id = f"CUST-{random.randint(1, 2000):04d}"

        orders.append((i, order_date.strftime("'%Y-%m-%d'"), product[0], region[0],
                       quantity, revenue, discount, f"'{customer_id}'"))
    return orders


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--drop", action="store_true")
    args = parser.parse_args()

    print("=" * 50)
    print("  Demo Data Setup: SoleMetrics Shoes")
    print(f"  Cluster: {CLUSTER}  DB: {DATABASE}")
    print("=" * 50)

    client = boto3.client("redshift-data", region_name=REGION)

    # Drop if requested
    if args.drop:
        print("\n  Dropping schema...")
        run_sql(client, f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")

    # Create schema
    print("\n  Creating schema...")
    run_sql(client, f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")

    # Create tables
    print("  Creating tables...")
    ddl_stmts = [
        f"DROP TABLE IF EXISTS {SCHEMA}.fact_orders",
        f"DROP TABLE IF EXISTS {SCHEMA}.dim_product",
        f"DROP TABLE IF EXISTS {SCHEMA}.dim_region",
        f"DROP TABLE IF EXISTS {SCHEMA}.dim_brand",
        f"""CREATE TABLE {SCHEMA}.dim_brand (
            brand_id INT, brand_name VARCHAR(50), brand_category VARCHAR(50),
            PRIMARY KEY (brand_id)) DISTSTYLE ALL""",
        f"""CREATE TABLE {SCHEMA}.dim_region (
            region_id INT, region_name VARCHAR(50), country VARCHAR(50), channel VARCHAR(20),
            PRIMARY KEY (region_id)) DISTSTYLE ALL""",
        f"""CREATE TABLE {SCHEMA}.dim_product (
            product_id INT, product_name VARCHAR(100), brand_id INT,
            category VARCHAR(50), price DECIMAL(10,2), gender VARCHAR(10),
            PRIMARY KEY (product_id)) DISTSTYLE ALL""",
        f"""CREATE TABLE {SCHEMA}.fact_orders (
            order_id INT, order_date DATE, product_id INT, region_id INT,
            quantity INT, revenue DECIMAL(12,2), discount DECIMAL(5,2), customer_id VARCHAR(20),
            PRIMARY KEY (order_id)) DISTKEY(product_id) SORTKEY(order_date)""",
    ]
    for stmt in ddl_stmts:
        run_sql(client, stmt)

    # Insert dim_brand
    print("  Inserting dim_brand...")
    vals = ",".join([f"({b[0]}, '{b[1]}', '{b[2]}')" for b in BRANDS])
    run_sql(client, f"INSERT INTO {SCHEMA}.dim_brand VALUES {vals}")

    # Insert dim_region
    print("  Inserting dim_region...")
    vals = ",".join([f"({r[0]}, '{r[1]}', '{r[2]}', '{r[3]}')" for r in REGIONS])
    run_sql(client, f"INSERT INTO {SCHEMA}.dim_region VALUES {vals}")

    # Insert dim_product
    print("  Inserting dim_product...")
    vals = ",".join([f"({p[0]}, '{p[1]}', {p[2]}, '{p[3]}', {p[4]}, '{p[5]}')" for p in PRODUCTS])
    run_sql(client, f"INSERT INTO {SCHEMA}.dim_product VALUES {vals}")

    # Generate and insert orders in batches
    print("  Generating 10,000 orders...")
    orders = generate_orders(10000)

    batch_size = 500
    total_batches = (len(orders) + batch_size - 1) // batch_size
    print(f"  Inserting fact_orders ({len(orders)} rows in {total_batches} batches)...")

    for i in range(0, len(orders), batch_size):
        batch = orders[i:i + batch_size]
        vals = ",".join([f"({o[0]},{o[1]},{o[2]},{o[3]},{o[4]},{o[5]},{o[6]},{o[7]})" for o in batch])
        run_sql(client, f"INSERT INTO {SCHEMA}.fact_orders VALUES {vals}")
        batch_num = (i // batch_size) + 1
        if batch_num % 5 == 0 or batch_num == total_batches:
            print(f"    Batch {batch_num}/{total_batches} done")

    # Verify
    print("\n  Verifying...")
    stmt_id = run_sql(client, f"SELECT COUNT(*) FROM {SCHEMA}.fact_orders")
    if stmt_id:
        result = client.get_statement_result(Id=stmt_id)
        count = result["Records"][0][0].get("longValue", 0)
        print(f"  fact_orders: {count} rows")

    stmt_id = run_sql(client, f"""
        SELECT b.brand_name, COUNT(*) as orders, CAST(SUM(f.revenue) AS DECIMAL(12,2)) as revenue
        FROM {SCHEMA}.fact_orders f
        JOIN {SCHEMA}.dim_product p ON f.product_id = p.product_id
        JOIN {SCHEMA}.dim_brand b ON p.brand_id = b.brand_id
        GROUP BY b.brand_name ORDER BY revenue DESC
    """)
    if stmt_id:
        result = client.get_statement_result(Id=stmt_id)
        print("\n  Revenue by Brand:")
        for row in result["Records"]:
            brand = row[0].get("stringValue", "?")
            orders = row[1].get("longValue", 0)
            rev = row[2].get("stringValue", "0")
            print(f"    {brand:15s}  {orders:6d} orders  ${float(rev):>12,.2f}")

    print(f"\n  Done! Schema: {SCHEMA}")


if __name__ == "__main__":
    main()
