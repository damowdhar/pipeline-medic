SELECT
    c.cust_id                            AS customer_id,
    c.full_name                          AS customer_name,
    c.signup_date                        AS signup_date,
    COUNT(o.order_id)                    AS lifetime_orders,
    COALESCE(SUM(o.amount), 0)           AS lifetime_value,
    MAX(o.ordered_on)                    AS last_order_date
FROM `medic_demo.raw_customers` AS c
LEFT JOIN `medic_demo.raw_orders` AS o
    ON o.cust_id = c.cust_id
GROUP BY
    c.cust_id,
    c.full_name,
    c.signup_date
