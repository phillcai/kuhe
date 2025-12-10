WITH 
-- 筛选符合条件的商品ID
valid_commodity AS (
    SELECT id 
    FROM commodity 
    WHERE commodity_type=1
),

-- 基础订单筛选（共用条件）
base_orders AS (
    SELECT 
        order_no,
        point_id
    FROM `order`
   WHERE 
       order_mode = 1
      AND status IN (7, 8)
      [[ and point_id IN ({{point_id}}) ]]
),

-- 订单商品汇总（基础数据）
order_product_summary AS (
    SELECT 
        DATE(create_time) AS dt,
        order_no,
        COUNT(1) AS dish_cnt,
        create_time  -- 保留原始时间用于后续时间范围过滤
    FROM order_product
    WHERE is_wms_out = 1
      AND commodity_id IN (SELECT id FROM valid_commodity)
      AND {{dt}}  -- create_time
    GROUP BY dt, order_no, create_time
),

-- 同期订单商品汇总（当天相同时间段）
same_period_order_summary AS (
    SELECT 
        dt,
        order_no,
        dish_cnt
    FROM order_product_summary
    WHERE TIME(create_time) < CURRENT_TIME()
),

-- 上周同期订单汇总（修复版）
last_week_same_period_summary AS (
    SELECT 
        DATE_ADD(op.dt, INTERVAL 7 DAY) AS current_dt,  -- 上周日期+7天=当前周对应日期
        op.order_no,
        op.dish_cnt
    FROM (
        -- 先筛选出上周的原始数据
        SELECT 
            DATE(create_time) AS dt,
            order_no,
            COUNT(1) AS dish_cnt,
            create_time
        FROM order_product
        WHERE is_wms_out = 1
          AND commodity_id IN (SELECT id FROM valid_commodity)
          -- 日期在查询范围内的上周同期（核心修复点）
          AND DATE(create_time) BETWEEN 
              DATE_SUB((SELECT MIN(dt) FROM order_product_summary), INTERVAL 7 DAY)
              AND DATE_SUB((SELECT MAX(dt) FROM order_product_summary), INTERVAL 7 DAY)
       
        GROUP BY dt, order_no, create_time
    ) op
    -- 关联基础订单表过滤
    INNER JOIN base_orders bo ON op.order_no = bo.order_no
)

-- 主查询
SELECT 
    a.dt AS '日期',
    a.dish_cnt AS '盒菜销量',
    a.point_cnt AS '有销量点位数量',
    b.dish_cnt_2 AS '截止当前时间同期盒菜销量',
    -- 处理空值显示为0或保持NULL
    COALESCE(lw.dish_cnt_3, 0) AS '上周同期盒菜销量'  -- 新增空值处理
FROM (
    -- 基础统计
    SELECT 
        ops.dt,
        SUM(ops.dish_cnt) AS dish_cnt,
        COUNT(DISTINCT bo.point_id) AS point_cnt
    FROM order_product_summary ops
    INNER JOIN base_orders bo ON ops.order_no = bo.order_no
    GROUP BY ops.dt
) a
LEFT JOIN (
    -- 同期统计
    SELECT 
        spo.dt,
        SUM(spo.dish_cnt) AS dish_cnt_2
    FROM same_period_order_summary spo
    INNER JOIN base_orders bo ON spo.order_no = bo.order_no
    GROUP BY spo.dt
) b ON a.dt = b.dt
LEFT JOIN (
    -- 上周同期统计（修复版）
    SELECT 
        lwsp.current_dt AS dt,
        SUM(lwsp.dish_cnt) AS dish_cnt_3
    FROM last_week_same_period_summary lwsp
    GROUP BY lwsp.current_dt
) lw ON a.dt = lw.dt
-- where DAYOFWEEK(a.dt) = 2
ORDER BY a.dt;
