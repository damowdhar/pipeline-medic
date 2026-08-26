"""Create the demo warehouse: a small dataset with a deliberate break.

The scenario is the most common real cause of a 3am pipeline failure: an
upstream producer renamed a column. `raw_customers` now exposes `cust_id`,
but `demo/models/dim_customers.sql` still joins on `customer_id`, so the model
fails to compile. Nothing about the error message says "renamed" -- the agent
has to inspect the live schema to work that out.

Run:  python -m demo.seed
"""

from __future__ import annotations

from google.cloud import bigquery

from app.config import config


def main() -> None:
    client = bigquery.Client(project=config.project_id)
    dataset_id = f"{config.project_id}.{config.bq_dataset}"

    dataset = bigquery.Dataset(dataset_id)
    dataset.location = config.bq_location
    client.create_dataset(dataset, exists_ok=True)
    print(f"dataset ready: {dataset_id}")

    # Note the column is `cust_id` here -- this is the post-rename world.
    client.query(
        f"""
        CREATE OR REPLACE TABLE `{dataset_id}.raw_customers` AS
        SELECT * FROM UNNEST([
          STRUCT(1  AS cust_id, 'Ada Lovelace'   AS full_name, DATE '2024-01-15' AS signup_date),
          STRUCT(2,             'Alan Turing',                 DATE '2024-02-02'),
          STRUCT(3,             'Grace Hopper',                DATE '2024-03-19'),
          STRUCT(4,             'Katherine Johnson',           DATE '2024-05-30')
        ])
        """,
        location=config.bq_location,
    ).result()
    print("created raw_customers (cust_id, full_name, signup_date)")

    client.query(
        f"""
        CREATE OR REPLACE TABLE `{dataset_id}.raw_orders` AS
        SELECT * FROM UNNEST([
          STRUCT(101 AS order_id, 1 AS cust_id, 42.50  AS amount, DATE '2024-04-01' AS ordered_on),
          STRUCT(102,             1,            17.00,            DATE '2024-04-11'),
          STRUCT(103,             2,           220.10,            DATE '2024-05-02'),
          STRUCT(104,             3,             9.99,            DATE '2024-06-14'),
          STRUCT(105,             3,            75.25,            DATE '2024-06-21'),
          STRUCT(106,             4,           310.00,            DATE '2024-07-04')
        ])
        """,
        location=config.bq_location,
    ).result()
    print("created raw_orders (order_id, cust_id, amount, ordered_on)")

    print("\nDemo warehouse is seeded and the pipeline is now broken by design.")
    print("Reproduce the failure with:  python -m demo.break_it")


if __name__ == "__main__":
    main()
