-- =============================
-- 售货机点位补货召回主查询SQL
-- 优化结构，提升可读性和性能
-- =============================

-- 1. 点位基础信息
WITH point_base AS (
  SELECT
    a.id AS point_id,
    a.point_type,
    CASE
      WHEN c.min_dt IS NULL OR DATEDIFF(CURRENT_DATE, c.min_dt) <= 7 THEN 1
      ELSE 0
    END AS is_new,
    CASE
      WHEN device_type = 1 THEN 108
      WHEN a.id = 55 THEN 72
      ELSE 96
    END AS point_max_stock
  FROM smart_cooker_sg.point a
  LEFT JOIN smart_cooker_sg.ai_device b ON a.id = b.point_id
  LEFT JOIN (
    SELECT point_id, MIN(DATE(create_time)) AS min_dt
    FROM smart_cooker_sg.order
    WHERE create_time >= DATE_SUB(CURRENT_DATE, INTERVAL 90 DAY)
      AND status IN (7, 8) AND order_mode = 1
    GROUP BY point_id
  ) c ON a.id = c.point_id
  WHERE a.is_monitor = 1
    AND a.id NOT IN (
      SELECT point_id FROM t_calendar
      WHERE impact_weight = 1
        AND date_begin >= CURRENT_DATE
        AND date_end < CURRENT_DATE
    )
    -- 可根据实际业务加点位筛选
    -- AND a.id IN ({{point_ids}})
),

-- 2. 点位库存与SKU
point_stock AS (
  SELECT
    point_id,
    SUM(ABS(amount)) - SUM(ABS(locked_amount)) AS point_stock,
    COUNT(DISTINCT CASE WHEN ABS(amount) - ABS(locked_amount) > 0 THEN commodity_id END) AS sku_cnt
  FROM smart_cooker_sg.inventory_point
  WHERE commodity_id IN (
    SELECT id FROM smart_cooker_sg.commodity WHERE commodity_type = 1
  ) AND amount > 0
  GROUP BY point_id
),

-- 3. 点位扩展信息
point_ext AS (
  SELECT
    point_id,
    day7_avg_dish_cnt,
    day7_avg_dish_cnt / 24 AS avg_dish_cnt
  FROM smart_cooker_sg.point_ext
  WHERE point_id IN (SELECT id FROM smart_cooker_sg.point WHERE is_monitor = 1)
),

-- 4. 补货时间窗口
point_time_window AS (
  SELECT
    a.point_id,
    CASE WHEN b.point_id IS NOT NULL THEN 1 ELSE 0 END AS is_time_open
  FROM (
    SELECT point_id FROM t_delivery_point_restrictions_detail GROUP BY point_id
  ) a
  LEFT JOIN (
    SELECT point_id
    FROM (
      SELECT
        point_id,
        jt.data_type,
        start_time,
        end_time
      FROM t_delivery_point_restrictions_detail a,
        JSON_TABLE(a.data_type, "$[*]" COLUMNS (data_type INT PATH "$")) AS jt
    ) b
    WHERE data_type = WEEKDAY(CURDATE()) + 1
      AND HOUR(NOW()) >= HOUR(start_time)
      AND HOUR(NOW()) <= IF(HOUR(end_time) = 23, 23, HOUR(end_time - INTERVAL 1 HOUR))
    GROUP BY point_id
  ) b ON a.point_id = b.point_id
),

-- 5. 车辆库存
car_stock AS (
  SELECT
    b.point_id,
    SUM(
      CASE
        WHEN COALESCE(qty, 0) >= COALESCE(main_food_cnt, 0) THEN COALESCE(main_food_cnt, 0)
        ELSE COALESCE(qty, 0)
      END
    ) AS qty
  FROM (
    SELECT
      commodity_id,
      SUM(qty) AS qty
    FROM t_car
    WHERE car_id = {{car_id}}
      AND commodity_id IN (SELECT id FROM smart_cooker_sg.commodity WHERE commodity_type = 1)
    GROUP BY commodity_id
  ) a
  INNER JOIN (
    SELECT
      point_id,
      commodity_id,
      SUM(shelf_max - (ABS(amount) - ABS(lock_amount))) AS main_food_cnt
    FROM smart_cooker_sg.inventory_device_shelf
    WHERE commodity_id IN (SELECT id FROM smart_cooker_sg.commodity WHERE commodity_type = 1)
    GROUP BY point_id, commodity_id
  ) b ON a.commodity_id = b.commodity_id
  GROUP BY b.point_id
  HAVING SUM(COALESCE(qty, 0)) > 25
)

-- 6. 主查询
SELECT
  pb.point_id,
  pb.point_type,
  ps.point_stock,
  COALESCE(ps.sku_cnt, 0) AS sku_cnt,
  pe.day7_avg_dish_cnt,
  pe.avg_dish_cnt,
  ptw.is_time_open,
  pb.is_new,
  cs.qty AS car_qty,
  -- 业务CASE逻辑（可根据实际业务继续细化）
  CASE
    WHEN -- 补货条件
      (ps.point_stock <= 65 AND (ps.point_stock - pe.avg_dish_cnt <= 25))
      OR ps.point_stock <= 40
      OR COALESCE(ps.sku_cnt, 0) <= 6
    THEN 1 ELSE 0
  END AS is_restock
FROM point_base pb
LEFT JOIN point_stock ps ON pb.point_id = ps.point_id
LEFT JOIN point_ext pe ON pb.point_id = pe.point_id
LEFT JOIN point_time_window ptw ON pb.point_id = ptw.point_id
LEFT JOIN car_stock cs ON pb.point_id = cs.point_id
WHERE
  (pb.point_type IN (5, 6, 7) AND (cs.qty IS NULL OR cs.qty > 12))
  OR pb.point_type IN (0.5, 1, 1.5, 2, 3);
