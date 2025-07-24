-- 最终目标：计算每个商品的实际可补充数量及是否受中央厨房库存限制
SELECT  
  commodity_id,
  -- 实际可补充数量：取“点位需补充量”和“中央厨房库存”的较小值
  CASE 
    WHEN COALESCE(point_need_supplement.main_food_cnt, 0) > COALESCE(ck_inventory.qty, 0) 
    THEN COALESCE(ck_inventory.qty, 0)  
    ELSE COALESCE(point_need_supplement.main_food_cnt, 0) 
  END AS actual_supplement_qty,
  -- 补充类型：1=受中央厨房库存限制；0=不受限制
  CASE 
    WHEN COALESCE(point_need_supplement.main_food_cnt, 0) > COALESCE(ck_inventory.qty, 0) 
    THEN 1  
    ELSE 0 
  END AS supplement_type
FROM 
  -- 步骤3：点位需补充的数量（扣减点位现有库存后）
  point_need_supplement
LEFT JOIN 
  -- 步骤4：中央厨房库存（作为补充上限）
  ck_inventory 
  ON point_need_supplement.commodity_id = ck_inventory.commodity_id;


-- 步骤1：基础数据准备：点位属性、商品列表、时间参数等
WITH base_params AS (
  -- 点位基础信息（筛选监控中且指定ID的点位）
  SELECT  
    id AS point_id,
    device_type,
    -- 点位最大库存（根据设备类型和特殊点位ID定义）
    CASE 
      WHEN device_type = 1 THEN 108
      WHEN id = 55 THEN 72  
      ELSE 96 
    END AS point_max_stock,
    -- 点位开业日期（无订单记录则默认为当前日期）
    CASE WHEN min_dt IS NULL THEN CURRENT_DATE ELSE min_dt END AS open_date
  FROM 
    smart_cooker_sg.point
  WHERE 
    is_monitor = 1
    AND id = ?  -- 传入指定点位ID
  LEFT JOIN 
    -- 点位首单日期（用于判断开业时间）
    (SELECT  
      point_id,
      MIN(DATE(create_time)) AS min_dt
     FROM smart_cooker_sg.`order`
     WHERE create_time >= DATE_SUB(CURRENT_DATE, INTERVAL 90 DAY)
       AND status IN (7, 8)  -- 已完成/已确认订单
       AND order_mode = 1
     GROUP BY point_id
    ) AS first_order_dt 
    ON id = first_order_dt.point_id
),

-- 步骤2：计算点位对每个商品的“理论需求数量”（未扣减现有库存）
point_commodity_demand AS (
  SELECT  
    point_id,
    commodity_id,
    -- 根据点位总需求和商品权重分配理论需求数量
    CASE 
      -- 点位总需求≤30时：按比例四舍五入，最低1个
      WHEN point_total_demand <= 30 
      THEN IF(ROUND(point_total_demand * (dish_score / point_total_score), 0) < 1, 1, 
              ROUND(point_total_demand * (dish_score / point_total_score), 0))
      -- 点位总需求>30时：按比例除以3取整后×3（确保是3的倍数，最低3个）
      ELSE IF(ROUND(point_total_demand * (dish_score / point_total_score) / 3, 0) * 3 <= 3, 3, 
              ROUND(point_total_demand * (dish_score / point_total_score) / 3, 0) * 3)
    END AS theory_demand  -- 理论需求数量（未扣减库存）
  FROM (
    -- 点位总需求（综合最大库存、历史销售数据）
    SELECT  
      bp.point_id,
      -- 点位总可供应数量（不超过最大库存）
      CASE WHEN point_amount <= 30 THEN point_amount ELSE point_max_stock END AS point_total_demand,
      bp.point_max_stock
    FROM (
      SELECT  
        point_id,
        point_max_stock,
        -- 基础需求：取“5天平均销量”和“最大库存”的较小值
        CASE 
          WHEN DATEDIFF(CURRENT_DATE, open_date) <= 7 THEN point_max_stock  -- 新开业≤7天用最大库存
          WHEN COALESCE(5day_avg_demand, avg_5day) > point_max_stock THEN point_max_stock  -- 超过最大库存则取最大
          ELSE COALESCE(5day_avg_demand, avg_5day)  -- 否则用历史平均
        END AS point_amount
      FROM base_params AS bp
      -- 关联5天平均需求（来自历史销售和点位规模）
      LEFT JOIN (
        SELECT  
          point_id,
          -- 按点位规模调整5天平均需求（规模3时×1.0系数）
          CASE WHEN point_size = 3 THEN ROUND(COALESCE(5day_sum_demand, 0) * 1.0, 0) 
               ELSE ROUND(COALESCE(5day_sum_demand, 0), 0) END AS 5day_avg_demand
        FROM (
          SELECT  
            point_id,
            point_size,
            -- 120小时（5天）的总需求（按小时权重汇总）
            ROUND(SUM(CASE WHEN rn <= 119 THEN hour_demand END), 0) AS 5day_sum_demand
          FROM (
            -- 每个小时的需求（基于历史权重计算）
            SELECT  
              phw.point_id,
              phw.point_size,
              phw.weekday_name,
              phw.dt_hour,
              -- 小时需求=历史权重×基础销量
              ROUND(COALESCE(phw.hour_weight, 0) * COALESCE(pdw.day_weight, 0), 3) AS hour_demand,
              rn
            FROM t_point_hour_weight AS phw  -- 点位小时权重表
            LEFT JOIN t_point_dt_weight AS pdw  -- 点位日期权重表
              ON phw.point_id = pdw.point_id AND phw.weekday_name = pdw.weekday_name
            LEFT JOIN (
              -- 生成时间序列（最近5天的小时）
              SELECT  
                DATE_ADD(TIMESTAMP(DATE_FORMAT(NOW(), "%Y-%m-%d %H:00:00")), INTERVAL rn HOUR) AS ds,
                HOUR(DATE_ADD(TIMESTAMP(DATE_FORMAT(NOW(), "%Y-%m-%d %H:00:00")), INTERVAL rn HOUR)) AS dt_hour,
                -- 转换星期几（1=周一，7=周日）
                CASE WHEN DAYOFWEEK(ds) = 1 THEN 7 
                     WHEN DAYOFWEEK(ds) = 2 THEN 1 
                     ELSE DAYOFWEEK(ds) - 1 END AS weekday_name,
                rn
              FROM t_numbers 
              WHERE rn BETWEEN 0 AND 119  -- 0-119小时（5天）
            ) AS time_series 
              ON phw.dt_hour = time_series.dt_hour AND phw.weekday_name = time_series.weekday_name
          ) AS hour_demand_detail
          GROUP BY point_id, point_size
        ) AS demand_by_point
      ) AS history_demand 
        ON bp.point_id = history_demand.point_id
      -- 关联默认5天平均（无历史数据时用此值）
      LEFT JOIN (
        SELECT  
          point_id,
          -- 按点位规模和7天平均计算5天默认需求（规模3时×5×1.0）
          COALESCE(a.default_5day, b.order_5day, 50) AS avg_5day
        FROM (
          SELECT  
            point_id,
            CASE WHEN point_size = 3 THEN day7_avg_dish_cnt * 5 * 1.0 
                 ELSE day7_avg_dish_cnt * 5 END AS default_5day
          FROM smart_cooker_sg.point_ext
        ) AS a
        LEFT JOIN (
          -- 最近7天的订单量（作为默认需求参考）
          SELECT  
            point_id,
            COUNT(1) AS order_5day
          FROM t_order_wide
          WHERE country = 'Singapore'
            AND dt >= DATE_SUB(CURRENT_DATE, INTERVAL 7 DAY)
            AND dt <= DATE_SUB(CURRENT_DATE, INTERVAL 1 DAY)
            AND commodity_type = 1  -- 主食品类
          GROUP BY point_id
        ) AS b 
          ON a.point_id = b.point_id
      ) AS default_demand 
        ON bp.point_id = default_demand.point_id
    ) AS point_total_amount
  ) AS point_demand_total
  -- 关联商品评分（用于按权重分配需求）
  LEFT JOIN (
    -- 每个商品的评分（优先取点位专属评分，无则取点位平均，再无则取全局平均）
    SELECT  
      bc.point_id,
      bc.commodity_id,
      COALESCE(c.ratio, d.point_avg_ratio, e.global_avg_ratio) AS dish_score
    FROM (
      -- 筛选需计算的商品（主食品类）
      SELECT  
        b.point_id,
        b.commodity_id
      FROM smart_cooker_sg.commodity AS a
      INNER JOIN (
        -- 点位关联的商品（通过菜单）
        SELECT  
          b.commodity_id,
          a.id AS point_id
        FROM smart_cooker_sg.point AS a
        INNER JOIN smart_cooker_sg.menu_commodity AS b 
          ON a.menu_id = b.menu_id
        GROUP BY b.commodity_id, a.id
      ) AS b 
        ON a.id = b.commodity_id
      WHERE a.commodity_type = 1  -- 主食品类
        AND a.id IN (?)  -- 传入指定商品ID
    ) AS bc
    -- 商品在点位的专属评分
    LEFT JOIN (
      SELECT  
        point_id,
        commodity_id,
        ratio
      FROM t_commodity_ratio
      WHERE dt IN (SELECT MAX(dt) FROM t_commodity_ratio)  -- 最新日期的评分
      GROUP BY point_id, commodity_id, ratio
    ) AS c 
      ON bc.commodity_id = c.commodity_id AND bc.point_id = c.point_id
    -- 点位的平均商品评分（无专属时用）
    LEFT JOIN (
      SELECT  
        point_id,
        AVG(ratio) AS point_avg_ratio
      FROM t_commodity_ratio
      WHERE dt IN (SELECT MAX(dt) FROM t_commodity_ratio)
      GROUP BY point_id
    ) AS d 
      ON bc.point_id = d.point_id
    -- 全局平均商品评分（无点位数据时用）
    LEFT JOIN (
      SELECT  
        AVG(ratio) AS global_avg_ratio
      FROM (
        SELECT  
          point_id,
          AVG(ratio) AS point_ratio
        FROM t_commodity_ratio
        WHERE dt IN (SELECT MAX(dt) FROM t_commodity_ratio)
        GROUP BY point_id
      ) AS a
    ) AS e 
      ON 1 = 1
  ) AS commodity_score 
    ON point_demand_total.point_id = commodity_score.point_id
  -- 关联点位的总评分（用于比例分配）
  LEFT JOIN (
    -- 点位的所有商品总评分（用于计算单个商品的占比）
    SELECT  
      point_id,
      SUM(dish_score) AS point_total_score
    FROM (
      -- 复用上面的商品评分逻辑（避免重复计算）
      SELECT  
        bc.point_id,
        bc.commodity_id,
        COALESCE(c.ratio, d.point_avg_ratio, e.global_avg_ratio) AS dish_score
      FROM (
        SELECT  
          b.point_id,
          b.commodity_id
        FROM smart_cooker_sg.commodity AS a
        INNER JOIN (
          SELECT  
            b.commodity_id,
            a.id AS point_id
          FROM smart_cooker_sg.point AS a
          INNER JOIN smart_cooker_sg.menu_commodity AS b 
            ON a.menu_id = b.menu_id
          GROUP BY b.commodity_id, a.id
        ) AS b 
          ON a.id = b.commodity_id
        WHERE a.commodity_type = 1 
          AND a.id IN (?)
      ) AS bc
      LEFT JOIN t_commodity_ratio AS c 
        ON bc.commodity_id = c.commodity_id AND bc.point_id = c.point_id
      LEFT JOIN (
        SELECT  
          point_id,
          AVG(ratio) AS point_avg_ratio
        FROM t_commodity_ratio
        WHERE dt IN (SELECT MAX(dt) FROM t_commodity_ratio)
        GROUP BY point_id
      ) AS d 
        ON bc.point_id = d.point_id
      LEFT JOIN (
        SELECT  
          AVG(point_ratio) AS global_avg_ratio
        FROM (
          SELECT  
            point_id,
            AVG(ratio) AS point_ratio
          FROM t_commodity_ratio
          WHERE dt IN (SELECT MAX(dt) FROM t_commodity_ratio)
          GROUP BY point_id
        ) AS a
      ) AS e 
        ON 1 = 1
    ) AS commodity_score_detail
    GROUP BY point_id
  ) AS point_total_score 
    ON commodity_score.point_id = point_total_score.point_id
),

-- 步骤3：计算“点位需补充的数量”（理论需求 - 点位现有库存）
point_need_supplement AS (
  SELECT  
    pcd.point_id,
    pcd.commodity_id,
    -- 需补充数量：理论需求 > 现有库存则补差额，否则不补（0）
    CASE 
      WHEN pcd.theory_demand - COALESCE(ip.commodity_stock, 0) > 0 
      THEN pcd.theory_demand - COALESCE(ip.commodity_stock, 0) 
      ELSE 0 
    END AS main_food_cnt
  FROM point_commodity_demand AS pcd
  -- 关联点位现有库存（按商品）
  LEFT JOIN (
    SELECT  
      point_id,
      commodity_id,
      -- 有效库存=总库存 - 锁定库存
      SUM(ABS(amount)) - SUM(ABS(locked_amount)) AS commodity_stock
    FROM smart_cooker_sg.inventory_point
    WHERE commodity_id IN (
      SELECT id FROM smart_cooker_sg.commodity WHERE commodity_type = 1
    )
      AND amount > 0  -- 有效库存
      AND point_id = ?  -- 指定点位
    GROUP BY point_id, commodity_id
  ) AS ip 
    ON pcd.commodity_id = ip.commodity_id AND pcd.point_id = ip.point_id
),

-- 步骤4：中央厨房的商品库存（作为补充上限）
ck_inventory AS (
  SELECT  
    commodity_id,
    SUM(qty) AS qty  -- 中央厨房总库存
  FROM smart_cooker_sg.central_kitchen_frame_inventory
  WHERE frame_id IN (
    -- 关联可用的框架（状态为2的车辆框架）
    SELECT DISTINCT frame_id 
    FROM smart_cooker_sg.central_kitchen_car_frame 
    WHERE state = 2  -- 可用状态
      AND car_id = ?  -- 指定车辆ID
  )
    AND commodity_type = 1  -- 主食品类
    AND qty > 0  -- 有库存
  GROUP BY commodity_id
)