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
