---
inclusion: auto
---

# IADP Data Models - Consumer 360

Schema: `consumer_360_secure` | Database: `dev` | Redshift

## Tables and Columns (Verified)

### dim_consumer (5000 rows)
Customer dimension - one row per customer.

| Column | Type | Description |
|--------|------|-------------|
| dim_consumer_key | VARCHAR(64) | PK - MD5 hash |
| first_name | VARCHAR(100) | First name |
| last_name | VARCHAR(100) | Last name |
| email | VARCHAR(200) | Email address |
| phone | VARCHAR(50) | Phone number |
| state | VARCHAR(50) | US state code |
| zipcode | VARCHAR(20) | ZIP code |
| region | VARCHAR(50) | Geographic region |
| tier | VARCHAR(50) | Loyalty tier: Bronze, Silver, Gold, Platinum, Diamond |
| current_spend | DECIMAL(12,2) | Total lifetime spend |
| data_source | VARCHAR(50) | Source: AMPERITY, PREDICT_SPRING, SFCC |
| gender | VARCHAR(50) | Male, Female, Non-Binary |
| consumer_segment | VARCHAR(100) | Active Runner, Casual Lifestyle, Outdoor Enthusiast, Fashion Forward, Value Seeker |
| modality | VARCHAR(100) | Road Running, Trail Running, Walking, Hiking, Casual |
| join_date | TIMESTAMP | Customer join date |
| last_activity_date | TIMESTAMP | Last activity |
| last_purchase_date | TIMESTAMP | Last purchase |

### dim_consumer_xref (~6500 rows)
Cross-reference table for source system IDs.

| Column | Type | Description |
|--------|------|-------------|
| dim_consumer_key | VARCHAR(64) | FK to dim_consumer |
| source_system | VARCHAR(50) | AMPERITY, PREDICT_SPRING, SFCC |
| source_system_key | VARCHAR(256) | Source system customer ID |

### dim_product_sku (200 rows)
Product catalog dimension.

| Column | Type | Description |
|--------|------|-------------|
| product_sku_key | VARCHAR(64) | PK - MD5 hash |
| sku_id | VARCHAR(50) | SKU identifier |
| upc | VARCHAR(50) | UPC barcode |
| product_name | VARCHAR(200) | Product name |
| brand | VARCHAR(50) | HOKA, UGG, TEVA, Koolaburra, Sanuk |
| category | VARCHAR(50) | Running, Trail, Boots, Slippers, Sandals, Casual |
| price | DECIMAL(10,2) | List price |

### fact_consumer_purchase_transaction (25000 rows)
Purchase transactions - one row per order.

| Column | Type | Description |
|--------|------|-------------|
| transaction_id | VARCHAR(50) | PK |
| dim_consumer_key | VARCHAR(64) | FK to dim_consumer |
| product_sku_key | VARCHAR(64) | FK to dim_product_sku |
| order_date | DATE | Order date |
| quantity | INT | Items purchased |
| revenue | DECIMAL(12,2) | Revenue after discount |
| discount_amount | DECIMAL(12,2) | Discount applied |
| sales_channel | VARCHAR(50) | DTC, Wholesale, Retail, Online |
| region | VARCHAR(50) | North America, Europe, Asia Pacific, Latin America |
| brand | VARCHAR(50) | Brand name |

### fact_consumer_merkle_loyalty_event (15000 rows)
Loyalty program events - one row per event.

| Column | Type | Description |
|--------|------|-------------|
| loyalty_event_id | VARCHAR(50) | PK |
| dim_consumer_key | VARCHAR(64) | FK to dim_consumer |
| event_type | VARCHAR(50) | PURCHASE, POINTS_EARNED, POINTS_REDEEMED, SIGNUP, TIER_UPGRADE, REFERRAL, BIRTHDAY_BONUS |
| transaction_date | DATE | Event date |
| points | INT | Points earned |
| redeemed_points | INT | Points redeemed |
| value | DECIMAL(12,2) | Transaction value |
| channel | VARCHAR(50) | ONLINE, IN_STORE, APP, EMAIL |

### fact_consumer_customer_support_contact (8000 rows)
Customer service contacts - one row per contact.

| Column | Type | Description |
|--------|------|-------------|
| contact_id | VARCHAR(50) | PK |
| dim_consumer_key | VARCHAR(64) | FK to dim_consumer |
| channel | VARCHAR(50) | email, chat, phone, social, sms |
| status | VARCHAR(50) | RESOLVED, ESCALATED, PENDING |
| queued_at | TIMESTAMP | When contact was queued |
| contact_handle_time | DECIMAL(10,2) | Handle time in seconds |
| messages_total | INT | Total messages |
| messages_from_customer | INT | Customer messages |
| messages_from_agent | INT | Agent messages |

## Join Patterns

All fact tables join to dim_consumer via `dim_consumer_key`:
```sql
fact_table.dim_consumer_key = dim_consumer.dim_consumer_key
```

Purchase transactions also join to dim_product_sku:
```sql
fact_consumer_purchase_transaction.product_sku_key = dim_product_sku.product_sku_key
```

Cross-reference lookups:
```sql
dim_consumer_xref.dim_consumer_key = dim_consumer.dim_consumer_key
-- Filter by: source_system = 'AMPERITY' | 'PREDICT_SPRING' | 'SFCC'
```

## Key Measures

| Metric | Column | Table | Aggregation |
|--------|--------|-------|-------------|
| Total Customers | dim_consumer_key | dim_consumer | DISTINCT_COUNT |
| Total Revenue | revenue | fact_consumer_purchase_transaction | SUM |
| Total Orders | transaction_id | fact_consumer_purchase_transaction | COUNT |
| Avg Order Value | revenue | fact_consumer_purchase_transaction | AVERAGE |
| Total Points Earned | points | fact_consumer_merkle_loyalty_event | SUM |
| Points Redeemed | redeemed_points | fact_consumer_merkle_loyalty_event | SUM |
| Total Contacts | contact_id | fact_consumer_customer_support_contact | COUNT |
| Avg Handle Time | contact_handle_time | fact_consumer_customer_support_contact | AVERAGE |
| Total Spend | current_spend | dim_consumer | SUM |

## Key Dimensions

| Dimension | Column | Table | Values |
|-----------|--------|-------|--------|
| Tier | tier | dim_consumer | Bronze, Silver, Gold, Platinum, Diamond |
| Data Source | data_source | dim_consumer | AMPERITY, PREDICT_SPRING, SFCC |
| Gender | gender | dim_consumer | Male, Female, Non-Binary |
| Consumer Segment | consumer_segment | dim_consumer | Active Runner, Casual Lifestyle, Outdoor Enthusiast, Fashion Forward, Value Seeker |
| Modality | modality | dim_consumer | Road Running, Trail Running, Walking, Hiking, Casual |
| State | state | dim_consumer | US state codes |
| Brand | brand | dim_product_sku / fact_consumer_purchase_transaction | HOKA, UGG, TEVA, Koolaburra, Sanuk |
| Category | category | dim_product_sku | Running, Trail, Boots, Slippers, Sandals, Casual |
| Sales Channel | sales_channel | fact_consumer_purchase_transaction | DTC, Wholesale, Retail, Online |
| Loyalty Event Type | event_type | fact_consumer_merkle_loyalty_event | PURCHASE, POINTS_EARNED, POINTS_REDEEMED, SIGNUP, TIER_UPGRADE, REFERRAL, BIRTHDAY_BONUS |
| Support Channel | channel | fact_consumer_customer_support_contact | email, chat, phone, social, sms |
| Contact Status | status | fact_consumer_customer_support_contact | RESOLVED, ESCALATED, PENDING |
