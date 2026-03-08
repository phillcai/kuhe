-- RIAR（补货间隔达成率）周趋势
-- 修复说明：
--   1. 使用各点位真实最大库存（point_max_stock）替代固定值108
--   2. LEAD 窗口函数去除 year_week 分区，保留跨周补货间隔
-- 计算逻辑：
--   goal_interval = 最大库存 * 0.8 / 日均销量，上限5天
--   act_interval  = 相邻两次补货的实际间隔天数，上限5天
--   riar          = act_interval / goal_interval，上限1

WITH stock_data AS (
    SELECT
        DATE_SUB(DATE(a.start_pick), INTERVAL WEEKDAY(a.start_pick) DAY) AS week_start,
        DATE_ADD(
            DATE_SUB(DATE(a.start_pick), INTERVAL WEEKDAY(a.start_pick) DAY),
            INTERVAL 6 DAY
        ) AS week_end,
        DATE_FORMAT(a.start_pick, '%x-%v') AS year_week,
        a.point_id,
        -- 取真实容量，无数据时兜底用108
        COALESCE(p.point_max_stock, 108) AS point_max_stock,
        -- 只按 point_id 分区，保留跨周补货间隔（修复：原版按 point_id, year_week 分区会丢失跨周间隔）
        TIMESTAMPDIFF(
            HOUR,
            a.start_pick,
            LEAD(a.start_pick) OVER (
                PARTITION BY a.point_id
                ORDER BY a.start_pick
            )
        ) / 24 AS diff_days
    FROM smart_cooker_sg.central_kitchen_car_task a
    LEFT JOIN report.t_point_wide p
        ON a.point_id = p.id
        AND p.dt IN (SELECT MAX(dt) FROM report.t_point_wide)
    WHERE a.task_type = 4
      AND LENGTH(a.ext) > 0
      AND a.state = 2
      AND a.start_pick >= '2025-12-01'
      AND a.start_pick < CURRENT_TIME
),

point_sales AS (
    SELECT
        DATE_SUB(DATE(a.create_time), INTERVAL WEEKDAY(a.create_time) DAY) AS week_start,
        DATE_FORMAT(a.create_time, '%x-%v') AS year_week,
        a.point_id,
        COUNT(1) / COUNT(DISTINCT DATE(a.create_time)) AS day_sales
    FROM smart_cooker_sg.`order` a
    INNER JOIN smart_cooker_sg.order_product b
        ON a.order_no = b.order_no
    WHERE a.create_time >= '2025-12-01'
      AND a.create_time < CURRENT_TIME
      AND a.order_mode = 1
      AND a.status IN (7, 8)
      AND b.commodity_id IN (
          SELECT id FROM smart_cooker_sg.commodity
          WHERE commodity_type = 1
      )
    GROUP BY
        DATE_SUB(DATE(a.create_time), INTERVAL WEEKDAY(a.create_time) DAY),
        DATE_FORMAT(a.create_time, '%x-%v'),
        a.point_id
)

SELECT
    m.year_week,
    m.week_start,
    m.week_end,
    SUM(m.riar) / COUNT(1) AS total_riar
FROM (
    SELECT
        k.*,
        LEAST(LEAST(k.act_interval, 5) / k.goal_interval, 1) AS riar
    FROM (
        SELECT
            a.year_week,
            a.week_start,
            a.week_end,
            a.point_id,
            b.day_sales,
            a.point_max_stock,
            LEAST(a.point_max_stock * 0.8 / b.day_sales, 5) AS goal_interval,
            a.diff_days AS act_interval
        FROM stock_data a
        LEFT JOIN point_sales b
            ON a.point_id = b.point_id
           AND a.year_week = b.year_week
        WHERE a.diff_days IS NOT NULL
    ) k
) m
GROUP BY
    m.year_week,
    m.week_start,
    m.week_end
ORDER BY
    m.week_start
