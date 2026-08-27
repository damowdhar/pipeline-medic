"""Restore the demo to its broken state.

Once the agent starts opening pull requests and you merge one, the model is
fixed and the demo no longer breaks. This puts the original broken SQL back so
you can run the demo again -- useful between recording takes.

Run:  python -m demo.reset
"""

from __future__ import annotations

from pathlib import Path

BROKEN_SQL = """\
-- Customer dimension with lifetime order totals.
--
-- This model was written when raw_customers exposed `customer_id`. Upstream
-- has since renamed that column to `cust_id`, so this SQL no longer compiles.
-- The agent's job is to work that out from the live schema and repair it.

SELECT
    c.customer_id                        AS customer_id,
    c.full_name                          AS customer_name,
    c.signup_date                        AS signup_date,
    COUNT(o.order_id)                    AS lifetime_orders,
    COALESCE(SUM(o.amount), 0)           AS lifetime_value,
    MAX(o.ordered_on)                    AS last_order_date
FROM `medic_demo.raw_customers` AS c
LEFT JOIN `medic_demo.raw_orders` AS o
    ON o.cust_id = c.customer_id
GROUP BY
    c.customer_id,
    c.full_name,
    c.signup_date
"""

TARGET = Path(__file__).resolve().parent / "models" / "dim_customers.sql"


def main() -> None:
    TARGET.write_text(BROKEN_SQL, encoding="utf-8")
    print(f"restored broken model: {TARGET}")
    print("the pipeline will now fail again -- run `python -m demo.break_it`")


if __name__ == "__main__":
    main()
