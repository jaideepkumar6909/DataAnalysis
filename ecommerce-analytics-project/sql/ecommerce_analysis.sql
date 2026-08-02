-- ============================================================================
-- E-COMMERCE ANALYTICS: DATA CLEANING + 5 BUSINESS QUESTIONS
-- Dialect: PostgreSQL (uses DATE_TRUNC, NTILE, FILTER, window functions).
-- For BigQuery: DATE_TRUNC works the same. For MySQL 8+/SQL Server: replace
-- DATE_TRUNC('month', d) with DATE_FORMAT(d,'%Y-%m-01') / DATEFROMPARTS(...),
-- and FILTER (WHERE ...) with CASE WHEN inside the aggregate.
-- ============================================================================


-- ============================================================================
-- STEP 0: CLEANING LAYER
-- Build reusable clean views so every downstream query starts from
-- consistent, de-duped, correctly-typed data.
-- ============================================================================

CREATE OR REPLACE VIEW customers_clean AS
SELECT
    customer_id,
    TRIM(first_name)                                   AS first_name,
    TRIM(last_name)                                     AS last_name,
    CASE WHEN age BETWEEN 13 AND 100 THEN age ELSE NULL END AS age,   -- strip impossible ages
    COALESCE(NULLIF(TRIM(gender), ''), 'Unknown')        AS gender,
    LOWER(TRIM(email))                                   AS email,
    NULLIF(TRIM(phone_number), '')                       AS phone_number,
    CAST(signup_date AS DATE)                            AS signup_date,
    loyalty_tier,
    INITCAP(TRIM(city))                                  AS city,
    UPPER(TRIM(state))                                   AS state,
    INITCAP(TRIM(country))                               AS country,
    COALESCE(NULLIF(TRIM(acquisition_channel), ''), 'Unknown') AS acquisition_channel,
    COALESCE(marketing_opt_in, FALSE)                    AS marketing_opt_in
FROM customers
WHERE customer_id IS NOT NULL;

CREATE OR REPLACE VIEW orders_clean AS
SELECT
    order_id,
    customer_id,
    CAST(order_date AS DATE)                             AS order_date,
    TRIM(product_category)                               AS product_category,
    TRIM(product_name)                                   AS product_name,
    CASE WHEN quantity > 0 THEN quantity ELSE NULL END   AS quantity,
    CASE WHEN unit_price > 0 THEN unit_price ELSE NULL END AS unit_price,
    COALESCE(discount_percent, 0)                        AS discount_percent,
    subtotal,
    COALESCE(shipping_cost, 0)                           AS shipping_cost,
    COALESCE(tax_amount, 0)                              AS tax_amount,
    total_amount,
    COALESCE(NULLIF(TRIM(payment_method), ''), 'Unknown') AS payment_method,
    TRIM(order_status)                                   AS order_status,
    COALESCE(NULLIF(TRIM(shipping_method), ''), 'Unknown') AS shipping_method,
    order_channel,
    coupon_code,                                          -- NULL is meaningful (no coupon used); leave as-is
    estimated_delivery_days,
    customer_rating,                                      -- NULL is meaningful (no rating given); leave as-is
    return_reason
FROM orders
WHERE order_id IS NOT NULL
  AND customer_id IS NOT NULL
  AND total_amount IS NOT NULL;               -- drop any order with no financial data (shouldn't exist, but defensive)


-- ============================================================================
-- Q1: Which customer cohorts are most valuable, and how does that value
--     decay over time?
-- Approach: monthly signup cohorts, tracked month-by-month against order
-- activity, showing % of cohort still active and revenue per cohort member.
-- ============================================================================

WITH cohorts AS (
    SELECT
        customer_id,
        DATE_TRUNC('month', signup_date)::date AS cohort_month
    FROM customers_clean
),
cohort_sizes AS (
    SELECT cohort_month, COUNT(*) AS cohort_size
    FROM cohorts
    GROUP BY cohort_month
),
order_activity AS (
    SELECT
        customer_id,
        DATE_TRUNC('month', order_date)::date AS order_month,
        total_amount
    FROM orders_clean
    WHERE order_status <> 'Cancelled'
),
cohort_month_activity AS (
    SELECT
        c.cohort_month,
        oa.order_month,
        COUNT(DISTINCT oa.customer_id) AS active_customers,
        SUM(oa.total_amount)           AS cohort_revenue
    FROM cohorts c
    JOIN order_activity oa ON oa.customer_id = c.customer_id
    GROUP BY c.cohort_month, oa.order_month
)
SELECT
    cma.cohort_month,
    cma.order_month,
    (EXTRACT(YEAR FROM cma.order_month) - EXTRACT(YEAR FROM cma.cohort_month)) * 12
      + (EXTRACT(MONTH FROM cma.order_month) - EXTRACT(MONTH FROM cma.cohort_month)) AS months_since_signup,
    cs.cohort_size,
    cma.active_customers,
    ROUND(cma.active_customers::numeric / cs.cohort_size, 3)       AS pct_of_cohort_active,
    cma.cohort_revenue,
    ROUND(cma.cohort_revenue / cs.cohort_size, 2)                  AS revenue_per_cohort_member
FROM cohort_month_activity cma
JOIN cohort_sizes cs ON cs.cohort_month = cma.cohort_month
ORDER BY cma.cohort_month, cma.order_month;


-- ============================================================================
-- Q2: What's driving the Nov-Dec spike, and is it healthy growth or
--     discount-fueled?
-- Approach: (a) holiday vs. non-holiday comparison, (b) month-by-month
-- time series so the shape of the spike and any discount/return pattern
-- is visible.
-- ============================================================================

-- (a) Holiday vs. non-holiday summary
SELECT
    CASE WHEN EXTRACT(MONTH FROM order_date) IN (11, 12)
         THEN 'Holiday (Nov-Dec)' ELSE 'Non-Holiday' END          AS period_type,
    COUNT(*)                                                       AS order_count,
    ROUND(AVG(total_amount), 2)                                    AS avg_order_value,
    ROUND(AVG(discount_percent), 2)                                AS avg_discount_pct,
    ROUND(100.0 * SUM(CASE WHEN discount_percent > 0 THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_orders_discounted,
    ROUND(100.0 * SUM(CASE WHEN order_status = 'Returned' THEN 1 ELSE 0 END) / COUNT(*), 1)  AS return_rate_pct,
    ROUND(100.0 * SUM(CASE WHEN order_status = 'Cancelled' THEN 1 ELSE 0 END) / COUNT(*), 1) AS cancel_rate_pct,
    SUM(total_amount)                                              AS total_revenue
FROM orders_clean
GROUP BY 1;

-- (b) Month-by-month time series
SELECT
    DATE_TRUNC('month', order_date)::date AS order_month,
    COUNT(*)                              AS order_count,
    SUM(total_amount)                     AS revenue,
    ROUND(AVG(discount_percent), 2)       AS avg_discount_pct,
    ROUND(100.0 * SUM(CASE WHEN order_status = 'Returned' THEN 1 ELSE 0 END) / COUNT(*), 1) AS return_rate_pct
FROM orders_clean
GROUP BY 1
ORDER BY 1;


-- ============================================================================
-- Q3: Which product categories have the best margin-adjusted performance,
--     not just the most revenue?
-- Approach: category rollup with revenue, discount depth, return/cancel
-- rate, and a return-adjusted revenue figure, ranked two ways.
-- ============================================================================

WITH category_stats AS (
    SELECT
        product_category,
        COUNT(*)                                                        AS order_count,
        SUM(quantity)                                                   AS units_sold,
        SUM(total_amount)                                               AS total_revenue,
        AVG(discount_percent)                                           AS avg_discount_pct,
        SUM(shipping_cost)                                              AS total_shipping_cost,
        ROUND(100.0 * SUM(CASE WHEN order_status = 'Returned' THEN 1 ELSE 0 END) / COUNT(*), 1)  AS return_rate_pct,
        ROUND(100.0 * SUM(CASE WHEN order_status = 'Cancelled' THEN 1 ELSE 0 END) / COUNT(*), 1) AS cancel_rate_pct,
        ROUND(AVG(customer_rating), 2)                                  AS avg_rating
    FROM orders_clean
    WHERE order_status <> 'Cancelled'         -- cancelled orders never realized revenue
    GROUP BY product_category
)
SELECT
    product_category,
    order_count,
    units_sold,
    total_revenue,
    ROUND(total_revenue / NULLIF(order_count, 0), 2)                    AS avg_order_value,
    avg_discount_pct,
    return_rate_pct,
    cancel_rate_pct,
    avg_rating,
    ROUND(total_shipping_cost / NULLIF(order_count, 0), 2)              AS avg_shipping_cost_per_order,
    ROUND(total_revenue * (1 - return_rate_pct / 100.0), 2)             AS return_adjusted_revenue,
    RANK() OVER (ORDER BY total_revenue DESC)                                                AS revenue_rank,
    RANK() OVER (ORDER BY total_revenue * (1 - return_rate_pct / 100.0) DESC)                 AS margin_adjusted_rank
FROM category_stats
ORDER BY total_revenue DESC;


-- ============================================================================
-- Q4: Is there a gap between shipping/payment method and order outcomes
--     (cancellations, returns, ratings)?
-- Approach: separate rollups by shipping_method and payment_method.
-- ============================================================================

-- (a) By shipping method
SELECT
    shipping_method,
    COUNT(*)                                                       AS order_count,
    ROUND(100.0 * SUM(CASE WHEN order_status = 'Cancelled' THEN 1 ELSE 0 END) / COUNT(*), 1) AS cancel_rate_pct,
    ROUND(100.0 * SUM(CASE WHEN order_status = 'Returned' THEN 1 ELSE 0 END) / COUNT(*), 1)  AS return_rate_pct,
    ROUND(AVG(customer_rating), 2)                                 AS avg_rating,
    ROUND(AVG(total_amount), 2)                                    AS avg_order_value
FROM orders_clean
GROUP BY shipping_method
ORDER BY cancel_rate_pct DESC;

-- (b) By payment method
SELECT
    payment_method,
    COUNT(*)                                                       AS order_count,
    ROUND(100.0 * SUM(CASE WHEN order_status = 'Cancelled' THEN 1 ELSE 0 END) / COUNT(*), 1) AS cancel_rate_pct,
    ROUND(100.0 * SUM(CASE WHEN order_status = 'Returned' THEN 1 ELSE 0 END) / COUNT(*), 1)  AS return_rate_pct,
    ROUND(AVG(customer_rating), 2)                                 AS avg_rating,
    ROUND(AVG(total_amount), 2)                                    AS avg_order_value
FROM orders_clean
GROUP BY payment_method
ORDER BY cancel_rate_pct DESC;

-- (c) Combined view, for spotting interaction effects (e.g. Next-Day + Gift Card)
SELECT
    shipping_method,
    payment_method,
    COUNT(*)                                                       AS order_count,
    ROUND(100.0 * SUM(CASE WHEN order_status IN ('Cancelled','Returned') THEN 1 ELSE 0 END) / COUNT(*), 1) AS problem_rate_pct
FROM orders_clean
GROUP BY shipping_method, payment_method
HAVING COUNT(*) >= 20        -- ignore tiny/noisy combinations
ORDER BY problem_rate_pct DESC;


-- ============================================================================
-- Q5: What distinguishes the top-value customers from the customers who
--     signed up but never ordered?
-- Approach: (a) Pareto/decile breakdown of revenue concentration,
-- (b) acquisition-channel conversion rate, to find which channel
-- overproduces signups that never convert.
-- ============================================================================

-- (a) Revenue concentration by decile (classic 80/20 check)
WITH customer_value AS (
    SELECT customer_id, SUM(total_amount) AS monetary
    FROM orders_clean
    WHERE order_status <> 'Cancelled'
    GROUP BY customer_id
),
deciles AS (
    SELECT
        customer_id,
        monetary,
        NTILE(10) OVER (ORDER BY monetary DESC) AS decile   -- decile 1 = highest spenders
    FROM customer_value
)
SELECT
    decile,
    COUNT(*)                                                         AS customers,
    SUM(monetary)                                                    AS decile_revenue,
    ROUND(100.0 * SUM(monetary) / SUM(SUM(monetary)) OVER (), 1)      AS pct_of_total_revenue
FROM deciles
GROUP BY decile
ORDER BY decile;

-- (b) Acquisition channel conversion rate (signup -> at least one order)
SELECT
    cc.acquisition_channel,
    COUNT(*)                                                         AS total_customers,
    COUNT(oc.customer_id)                                            AS customers_with_orders,
    COUNT(*) - COUNT(oc.customer_id)                                 AS zero_order_customers,
    ROUND(100.0 * COUNT(oc.customer_id) / COUNT(*), 1)               AS conversion_rate_pct
FROM customers_clean cc
LEFT JOIN (SELECT DISTINCT customer_id FROM orders_clean) oc
       ON oc.customer_id = cc.customer_id
GROUP BY cc.acquisition_channel
ORDER BY conversion_rate_pct ASC;

-- (c) Optional: profile of zero-order customers (demographics/tenure)
SELECT
    cc.acquisition_channel,
    cc.loyalty_tier,
    ROUND(AVG(cc.age), 1)                                            AS avg_age,
    ROUND(AVG(CURRENT_DATE - cc.signup_date), 0)                     AS avg_days_since_signup,
    COUNT(*)                                                         AS zero_order_customers
FROM customers_clean cc
LEFT JOIN (SELECT DISTINCT customer_id FROM orders_clean) oc
       ON oc.customer_id = cc.customer_id
WHERE oc.customer_id IS NULL
GROUP BY cc.acquisition_channel, cc.loyalty_tier
ORDER BY zero_order_customers DESC;
