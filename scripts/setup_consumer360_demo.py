"""
Setup Consumer 360 demo data in Redshift.
Creates: consumer_360_secure schema with dimensions and fact tables.

Tables created:
  - dim_consumer (~5000 customers)
  - dim_consumer_xref (~8000 cross-references)
  - dim_product_sku (~200 products)
  - fact_consumer_purchase_transaction (~25000 orders)
  - fact_consumer_merkle_loyalty_event (~15000 loyalty events)
  - fact_consumer_customer_support_contact (~8000 support contacts)

Usage:
  python scripts/setup_consumer360_demo.py
  python scripts/setup_consumer360_demo.py --drop   # drop and recreate
"""

import boto3, json, os, random, time, argparse, hashlib
from datetime import datetime, timedelta

random.seed(42)

# Load config
cfg_path = os.path.join(os.path.dirname(__file__), "..", "config", "datasource.json")
with open(cfg_path) as f:
    cfg = json.load(f)

rs = cfg["redshift"]
CLUSTER = rs["cluster_id"]
DATABASE = rs["database"]
DB_USER = rs["db_user"]
REGION = cfg["region"]
SECRET_ARN = rs.get("credentials_secret_arn", "")
SCHEMA = "consumer_360_secure"


def run_sql(client, sql):
    """Execute SQL via Redshift Data API and wait for completion."""
    params = dict(ClusterIdentifier=CLUSTER, Database=DATABASE, Sql=sql)
    if SECRET_ARN:
        params["SecretArn"] = SECRET_ARN
    else:
        params["DbUser"] = DB_USER
    resp = client.execute_statement(**params)
    stmt_id = resp["Id"]
    for _ in range(180):
        time.sleep(1)
        status = client.describe_statement(Id=stmt_id)
        if status["Status"] == "FINISHED":
            return stmt_id
        if status["Status"] in ("FAILED", "ABORTED"):
            print(f"    FAILED: {status.get('Error', 'unknown')}")
            return None
    print("    TIMEOUT")
    return None


# ============================================================
# Data generators
# ============================================================

FIRST_NAMES = ["James","Mary","John","Patricia","Robert","Jennifer","Michael","Linda","David","Elizabeth",
    "William","Barbara","Richard","Susan","Joseph","Jessica","Thomas","Sarah","Christopher","Karen",
    "Charles","Lisa","Daniel","Nancy","Matthew","Betty","Anthony","Margaret","Mark","Sandra",
    "Donald","Ashley","Steven","Dorothy","Paul","Kimberly","Andrew","Emily","Joshua","Donna"]

LAST_NAMES = ["Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis","Rodriguez","Martinez",
    "Hernandez","Lopez","Gonzalez","Wilson","Anderson","Thomas","Taylor","Moore","Jackson","Martin",
    "Lee","Perez","Thompson","White","Harris","Sanchez","Clark","Ramirez","Lewis","Robinson"]

STATES = ["CA","NY","TX","FL","IL","PA","OH","GA","NC","MI","NJ","VA","WA","AZ","MA",
    "TN","IN","MO","MD","WI","CO","MN","SC","AL","LA","KY","OR","OK","CT","UT"]

TIERS = ["Bronze", "Silver", "Gold", "Platinum", "Diamond"]
TIER_WEIGHTS = [35, 30, 20, 10, 5]

DATA_SOURCES = ["AMPERITY", "PREDICT_SPRING", "SFCC"]
DS_WEIGHTS = [50, 30, 20]

GENDERS = ["Male", "Female", "Non-Binary", None]
GENDER_WEIGHTS = [40, 45, 5, 10]

CONSUMER_SEGMENTS = ["Active Runner", "Casual Lifestyle", "Outdoor Enthusiast", "Fashion Forward", "Value Seeker", None]
SEGMENT_WEIGHTS = [25, 20, 15, 20, 15, 5]

MODALITIES = ["Road Running", "Trail Running", "Walking", "Hiking", "Casual", None]
MODALITY_WEIGHTS = [20, 15, 20, 15, 20, 10]

BRANDS = ["HOKA", "UGG", "TEVA", "Koolaburra", "Sanuk"]
BRAND_WEIGHTS = [35, 30, 15, 10, 10]

CATEGORIES = ["Running", "Trail", "Boots", "Slippers", "Sandals", "Casual"]

CHANNELS = ["email", "chat", "phone", "social", "sms"]
CHANNEL_WEIGHTS = [30, 25, 25, 10, 10]

CONTACT_STATUSES = ["RESOLVED", "RESOLVED", "RESOLVED", "ESCALATED", "PENDING"]

LOYALTY_EVENT_TYPES = ["PURCHASE", "POINTS_EARNED", "POINTS_REDEEMED", "SIGNUP", "TIER_UPGRADE", "REFERRAL", "BIRTHDAY_BONUS"]
LOYALTY_WEIGHTS = [30, 25, 15, 10, 10, 5, 5]


def md5_key(source, key):
    return hashlib.md5(f"{source}::{key}".encode(), usedforsecurity=False).hexdigest()


def generate_consumers(n=5000):
    consumers = []
    start_date = datetime(2020, 1, 1)
    end_date = datetime(2026, 3, 31)
    days_range = (end_date - start_date).days

    for i in range(1, n + 1):
        source = random.choices(DATA_SOURCES, weights=DS_WEIGHTS)[0]
        source_key = f"{source[:2]}-{i:05d}"
        dim_key = md5_key(source, source_key)

        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        email = f"{first.lower()}.{last.lower()}{i}@example.com"
        phone = f"555-{random.randint(100,999)}-{random.randint(1000,9999)}"
        state = random.choice(STATES)
        zipcode = f"{random.randint(10000, 99999)}"
        tier = random.choices(TIERS, weights=TIER_WEIGHTS)[0]
        gender = random.choices(GENDERS, weights=GENDER_WEIGHTS)[0]
        segment = random.choices(CONSUMER_SEGMENTS, weights=SEGMENT_WEIGHTS)[0]
        modality = random.choices(MODALITIES, weights=MODALITY_WEIGHTS)[0]
        spend = round(random.uniform(50, 5000), 2)

        join_offset = random.randint(0, days_range)
        join_date = start_date + timedelta(days=join_offset)
        last_activity = join_date + timedelta(days=random.randint(1, min(365, (end_date - join_date).days or 1)))
        last_purchase = join_date + timedelta(days=random.randint(1, min(300, (end_date - join_date).days or 1)))

        consumers.append({
            "dim_consumer_key": dim_key,
            "first_name": first,
            "last_name": last,
            "email": email,
            "phone": phone,
            "state": state,
            "zipcode": zipcode,
            "region": state,
            "tier": tier,
            "current_spend": spend,
            "data_source": source,
            "gender": gender,
            "consumer_segment": segment,
            "modality": modality,
            "join_date": join_date.strftime("%Y-%m-%d"),
            "last_activity_date": last_activity.strftime("%Y-%m-%d"),
            "last_purchase_date": last_purchase.strftime("%Y-%m-%d"),
            "source_key": source_key,
        })
    return consumers


def generate_products(n=200):
    products = []
    for i in range(1, n + 1):
        brand = random.choices(BRANDS, weights=BRAND_WEIGHTS)[0]
        cat = random.choice(CATEGORIES)
        name = f"{brand} {cat} {random.choice(['Pro','Elite','Classic','Sport','Lite','Max','Ultra'])} {i}"
        sku = f"SKU-{brand[:3].upper()}-{i:04d}"
        upc = f"{random.randint(100000000000, 999999999999)}"
        price = round(random.uniform(39.99, 249.99), 2)
        products.append({
            "product_sku_key": md5_key("PRODUCT", sku),
            "sku_id": sku,
            "upc": upc,
            "product_name": name,
            "brand": brand,
            "category": cat,
            "price": price,
        })
    return products


def generate_transactions(consumers, products, n=25000):
    txns = []
    start = datetime(2023, 1, 1)
    end = datetime(2026, 3, 31)
    days_range = (end - start).days

    for i in range(1, n + 1):
        c = random.choice(consumers)
        p = random.choice(products)
        order_date = start + timedelta(days=random.randint(0, days_range))
        qty = random.choices([1, 2, 3, 4], weights=[55, 30, 10, 5])[0]
        discount = random.choices([0, 0.05, 0.10, 0.15, 0.20, 0.25], weights=[40, 20, 20, 10, 7, 3])[0]
        revenue = round(p["price"] * qty * (1 - discount), 2)
        channel = random.choice(["DTC", "Wholesale", "Retail", "Online"])
        region = random.choice(["North America", "Europe", "Asia Pacific", "Latin America"])

        txns.append({
            "transaction_id": f"TXN-{i:06d}",
            "dim_consumer_key": c["dim_consumer_key"],
            "product_sku_key": p["product_sku_key"],
            "order_date": order_date.strftime("%Y-%m-%d"),
            "quantity": qty,
            "revenue": revenue,
            "discount_amount": round(p["price"] * qty * discount, 2),
            "sales_channel": channel,
            "region": region,
            "brand": p["brand"],
        })
    return txns


def generate_loyalty_events(consumers, n=15000):
    events = []
    start = datetime(2023, 1, 1)
    end = datetime(2026, 3, 31)
    days_range = (end - start).days

    for i in range(1, n + 1):
        c = random.choice(consumers)
        event_type = random.choices(LOYALTY_EVENT_TYPES, weights=LOYALTY_WEIGHTS)[0]
        event_date = start + timedelta(days=random.randint(0, days_range))
        points = random.randint(10, 500) if event_type in ("POINTS_EARNED", "PURCHASE", "REFERRAL", "BIRTHDAY_BONUS") else 0
        redeemed = random.randint(50, 300) if event_type == "POINTS_REDEEMED" else 0
        value = round(random.uniform(10, 500), 2) if event_type == "PURCHASE" else 0

        events.append({
            "loyalty_event_id": f"LEV-{i:06d}",
            "dim_consumer_key": c["dim_consumer_key"],
            "event_type": event_type,
            "transaction_date": event_date.strftime("%Y-%m-%d"),
            "points": points,
            "redeemed_points": redeemed,
            "value": value,
            "channel": random.choice(["ONLINE", "IN_STORE", "APP", "EMAIL"]),
        })
    return events


def generate_support_contacts(consumers, n=8000):
    contacts = []
    start = datetime(2023, 6, 1)
    end = datetime(2026, 3, 31)
    days_range = (end - start).days

    for i in range(1, n + 1):
        c = random.choice(consumers)
        channel = random.choices(CHANNELS, weights=CHANNEL_WEIGHTS)[0]
        queued = start + timedelta(days=random.randint(0, days_range), hours=random.randint(8, 20), minutes=random.randint(0, 59))
        handle_time = round(random.uniform(60, 1800), 2)
        messages = random.randint(2, 20)
        status = random.choice(CONTACT_STATUSES)

        contacts.append({
            "contact_id": f"CON-{i:06d}",
            "dim_consumer_key": c["dim_consumer_key"],
            "channel": channel,
            "status": status,
            "queued_at": queued.strftime("%Y-%m-%d %H:%M:%S"),
            "contact_handle_time": handle_time,
            "messages_total": messages,
            "messages_from_customer": random.randint(1, messages),
            "messages_from_agent": random.randint(1, messages),
        })
    return contacts


# ============================================================
# SQL helpers
# ============================================================

def escape(val):
    if val is None:
        return "NULL"
    if isinstance(val, (int, float)):
        return str(val)
    return "'" + str(val).replace("'", "''") + "'"


def insert_batch(client, table, rows, columns, batch_size=200):
    total = len(rows)
    batches = (total + batch_size - 1) // batch_size
    for i in range(0, total, batch_size):
        batch = rows[i:i + batch_size]
        vals = ",".join([
            "(" + ",".join([escape(r[c]) for c in columns]) + ")"
            for r in batch
        ])
        sql = f"INSERT INTO {SCHEMA}.{table} ({','.join(columns)}) VALUES {vals}"
        run_sql(client, sql)
        batch_num = (i // batch_size) + 1
        if batch_num % 10 == 0 or batch_num == batches:
            print(f"    {table}: batch {batch_num}/{batches}", flush=True)


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--drop", action="store_true", help="Drop and recreate schema")
    args = parser.parse_args()

    print("=" * 60)
    print("  Consumer 360 Demo Data Setup")
    print(f"  Cluster: {CLUSTER}  DB: {DATABASE}  Schema: {SCHEMA}")
    print("=" * 60)

    client = boto3.client("redshift-data", region_name=REGION)

    if args.drop:
        print("\n  Dropping schema...", flush=True)
        run_sql(client, f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")

    print("\n  Creating schema...", flush=True)
    run_sql(client, f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")

    # DDL
    print("  Creating tables...", flush=True)

    ddls = [
        f"DROP TABLE IF EXISTS {SCHEMA}.fact_consumer_customer_support_contact",
        f"DROP TABLE IF EXISTS {SCHEMA}.fact_consumer_merkle_loyalty_event",
        f"DROP TABLE IF EXISTS {SCHEMA}.fact_consumer_purchase_transaction",
        f"DROP TABLE IF EXISTS {SCHEMA}.dim_consumer_xref",
        f"DROP TABLE IF EXISTS {SCHEMA}.dim_consumer",
        f"DROP TABLE IF EXISTS {SCHEMA}.dim_product_sku",
        f"""CREATE TABLE {SCHEMA}.dim_consumer (
            dim_consumer_key VARCHAR(64) NOT NULL,
            first_name VARCHAR(100),
            last_name VARCHAR(100),
            email VARCHAR(200),
            phone VARCHAR(50),
            state VARCHAR(50),
            zipcode VARCHAR(20),
            region VARCHAR(50),
            tier VARCHAR(50),
            current_spend DECIMAL(12,2),
            data_source VARCHAR(50),
            gender VARCHAR(50),
            consumer_segment VARCHAR(100),
            modality VARCHAR(100),
            join_date TIMESTAMP,
            last_activity_date TIMESTAMP,
            last_purchase_date TIMESTAMP,
            PRIMARY KEY (dim_consumer_key)
        ) DISTSTYLE KEY DISTKEY(dim_consumer_key)""",

        f"""CREATE TABLE {SCHEMA}.dim_consumer_xref (
            dim_consumer_key VARCHAR(64) NOT NULL,
            source_system VARCHAR(50) NOT NULL,
            source_system_key VARCHAR(256) NOT NULL,
            PRIMARY KEY (dim_consumer_key, source_system, source_system_key)
        ) DISTSTYLE ALL""",

        f"""CREATE TABLE {SCHEMA}.dim_product_sku (
            product_sku_key VARCHAR(64) NOT NULL,
            sku_id VARCHAR(50),
            upc VARCHAR(50),
            product_name VARCHAR(200),
            brand VARCHAR(50),
            category VARCHAR(50),
            price DECIMAL(10,2),
            PRIMARY KEY (product_sku_key)
        ) DISTSTYLE ALL""",

        f"""CREATE TABLE {SCHEMA}.fact_consumer_purchase_transaction (
            transaction_id VARCHAR(50) NOT NULL,
            dim_consumer_key VARCHAR(64),
            product_sku_key VARCHAR(64),
            order_date DATE,
            quantity INT,
            revenue DECIMAL(12,2),
            discount_amount DECIMAL(12,2),
            sales_channel VARCHAR(50),
            region VARCHAR(50),
            brand VARCHAR(50),
            PRIMARY KEY (transaction_id)
        ) DISTKEY(dim_consumer_key) SORTKEY(order_date)""",

        f"""CREATE TABLE {SCHEMA}.fact_consumer_merkle_loyalty_event (
            loyalty_event_id VARCHAR(50) NOT NULL,
            dim_consumer_key VARCHAR(64),
            event_type VARCHAR(50),
            transaction_date DATE,
            points INT,
            redeemed_points INT,
            value DECIMAL(12,2),
            channel VARCHAR(50),
            PRIMARY KEY (loyalty_event_id)
        ) DISTKEY(dim_consumer_key) SORTKEY(transaction_date)""",

        f"""CREATE TABLE {SCHEMA}.fact_consumer_customer_support_contact (
            contact_id VARCHAR(50) NOT NULL,
            dim_consumer_key VARCHAR(64),
            channel VARCHAR(50),
            status VARCHAR(50),
            queued_at TIMESTAMP,
            contact_handle_time DECIMAL(10,2),
            messages_total INT,
            messages_from_customer INT,
            messages_from_agent INT,
            PRIMARY KEY (contact_id)
        ) DISTKEY(dim_consumer_key) SORTKEY(queued_at)""",
    ]

    for ddl in ddls:
        run_sql(client, ddl)

    # Generate data
    print("\n  Generating fake data...", flush=True)
    consumers = generate_consumers(5000)
    products = generate_products(200)
    transactions = generate_transactions(consumers, products, 25000)
    loyalty_events = generate_loyalty_events(consumers, 15000)
    support_contacts = generate_support_contacts(consumers, 8000)

    # Generate xref entries
    xrefs = []
    for c in consumers:
        xrefs.append({"dim_consumer_key": c["dim_consumer_key"], "source_system": c["data_source"], "source_system_key": c["source_key"]})
        # Some customers have multiple source system entries
        if random.random() < 0.3:
            other_source = random.choice([s for s in DATA_SOURCES if s != c["data_source"]])
            xrefs.append({"dim_consumer_key": c["dim_consumer_key"], "source_system": other_source, "source_system_key": f"{other_source[:2]}-X{random.randint(10000,99999)}"})

    print(f"    dim_consumer: {len(consumers)} rows")
    print(f"    dim_consumer_xref: {len(xrefs)} rows")
    print(f"    dim_product_sku: {len(products)} rows")
    print(f"    fact_consumer_purchase_transaction: {len(transactions)} rows")
    print(f"    fact_consumer_merkle_loyalty_event: {len(loyalty_events)} rows")
    print(f"    fact_consumer_customer_support_contact: {len(support_contacts)} rows")

    # Insert data
    print("\n  Inserting dim_consumer...", flush=True)
    insert_batch(client, "dim_consumer", consumers,
        ["dim_consumer_key","first_name","last_name","email","phone","state","zipcode","region","tier","current_spend","data_source","gender","consumer_segment","modality","join_date","last_activity_date","last_purchase_date"])

    print("  Inserting dim_consumer_xref...", flush=True)
    insert_batch(client, "dim_consumer_xref", xrefs,
        ["dim_consumer_key","source_system","source_system_key"])

    print("  Inserting dim_product_sku...", flush=True)
    insert_batch(client, "dim_product_sku", products,
        ["product_sku_key","sku_id","upc","product_name","brand","category","price"])

    print("  Inserting fact_consumer_purchase_transaction...", flush=True)
    insert_batch(client, "fact_consumer_purchase_transaction", transactions,
        ["transaction_id","dim_consumer_key","product_sku_key","order_date","quantity","revenue","discount_amount","sales_channel","region","brand"])

    print("  Inserting fact_consumer_merkle_loyalty_event...", flush=True)
    insert_batch(client, "fact_consumer_merkle_loyalty_event", loyalty_events,
        ["loyalty_event_id","dim_consumer_key","event_type","transaction_date","points","redeemed_points","value","channel"])

    print("  Inserting fact_consumer_customer_support_contact...", flush=True)
    insert_batch(client, "fact_consumer_customer_support_contact", support_contacts,
        ["contact_id","dim_consumer_key","channel","status","queued_at","contact_handle_time","messages_total","messages_from_customer","messages_from_agent"])

    # Verify
    print("\n  Verifying...", flush=True)
    for table in ["dim_consumer", "dim_consumer_xref", "dim_product_sku",
                  "fact_consumer_purchase_transaction", "fact_consumer_merkle_loyalty_event",
                  "fact_consumer_customer_support_contact"]:
        stmt_id = run_sql(client, f"SELECT COUNT(*) FROM {SCHEMA}.{table}")
        if stmt_id:
            result = client.get_statement_result(Id=stmt_id)
            count = result["Records"][0][0].get("longValue", 0)
            print(f"    {table}: {count} rows")

    print(f"\n  Done! Schema '{SCHEMA}' is ready.")
    print(f"  Update config/datasource.json with: \"schema\": \"{SCHEMA}\"")


if __name__ == "__main__":
    main()
