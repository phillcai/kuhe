WITH
  -- 高流量点位列表（排除这些点位）
  high_traffic_points AS (
    SELECT DISTINCT
      dt,
      point_id
    FROM
      t_user_bhv_session
    WHERE
      source = 'offline'
      AND country = 'Singapore'
      AND point_id IN (
        SELECT
          id
        FROM
          report.t_point
        WHERE
          country = 'Singapore'
      )
      AND point_id IN (
        SELECT
          id
        FROM
          smart_cooker_sg.point_ext
        WHERE
          1 = 1
      )
      AND dt >= date_sub(current_date(), INTERVAL 42 DAY)
      AND dt <= current_date()
    GROUP BY
      dt,
      point_id
    HAVING
      COUNT(DISTINCT menu_uid) > 500
  ),
  -- APP渠道每日活跃session数
  app_sessions AS (
    SELECT
      dt,
      COUNT(
        DISTINCT CASE
          WHEN length(activity_uid) > 4 THEN session_id
        END
      ) AS session_cnt
    FROM
      t_user_bhv_session
    WHERE
      source = 'app'
      AND country = 'Singapore'
      AND point_id IN (
        SELECT
          id
        FROM
          report.t_point
        WHERE
          country = 'Singapore'
      )
      AND point_id IN (
        SELECT
          id
        FROM
          smart_cooker_sg.point_ext
        WHERE
          1 = 1
      )
      AND dt >= date_sub(current_date(), INTERVAL 42 DAY)
      AND dt <= current_date()
    GROUP BY
      dt
  ),
  -- 点餐屏渠道每日活跃session数（排除高流量点位）
  offline_sessions AS (
    SELECT
      a.dt,
      COUNT(
        DISTINCT CASE
          WHEN length(a.menu_uid) > 4 THEN a.session_id
        END
      ) AS session_cnt
    FROM
      t_user_bhv_session a
      LEFT JOIN high_traffic_points b ON a.dt = b.dt
      AND a.point_id = b.point_id
    WHERE
      a.source = 'offline'
      AND a.country = 'Singapore'
      AND a.point_id IN (
        SELECT
          id
        FROM
          report.t_point
        WHERE
          country = 'Singapore'
      )
      AND a.point_id IN (
        SELECT
          id
        FROM
          smart_cooker_sg.point_ext
        WHERE
          1 = 1
      )
      AND a.dt >= date_sub(current_date(), INTERVAL 42 DAY)
      AND a.dt <= current_date()
      AND b.dt IS NULL -- 排除高流量点位
    GROUP BY
      a.dt
  ),
  -- 合并APP和点餐屏的session数据（每日一条记录）
  session_data_old AS (
    SELECT
      dt,
      SUM(session_cnt) AS daily_session_cnt
    FROM
      (
        SELECT
          dt,
          session_cnt
        FROM
          app_sessions
        UNION ALL
        SELECT
          dt,
          session_cnt
        FROM
          offline_sessions
      ) combined
    GROUP BY
      dt
  ),
  -- 点位 session 数（按日聚合，口径：point_session_log 最近 42 天）
  session_data AS (
    SELECT
      DATE(psl.create_time) AS dt,
      COUNT(psl.session_id) AS session_cnt
    FROM
      smart_cooker_sg.point_session_log psl
    WHERE
      psl.create_time >= DATE_SUB(CURDATE(), INTERVAL 42 DAY)
    GROUP BY
      dt
  ),
  -- 缺货率数据（按日期聚合，避免重复计算session）
  shortage_by_date AS (
    SELECT
      dt,
      SUM(online_dish_cnt) AS total_online_dish_cnt,
      SUM(max_commodity_cnt) AS total_max_commodity_cnt
    FROM
      t_commodity_shortage
    WHERE
      commodity_type = 'main'
      AND dt BETWEEN DATE_SUB(CURDATE(), INTERVAL 42 DAY) AND CURDATE()
    GROUP BY
      dt
  ),
  weekly_data AS (
    SELECT
      -- 周标识：取该周的周日（格式：YYYY-MM-DD），作为每周的唯一标识
      DATE_FORMAT(
        STR_TO_DATE(t1.dt, '%Y-%m-%d') - INTERVAL(DAYOFWEEK(STR_TO_DATE(t1.dt, '%Y-%m-%d')) - 1) DAY,
        '%Y-%m-%d'
      ) AS '周起始日(周日)',
      -- 周缺货率（sku权重）：按周聚合后计算
      CASE
        WHEN IFNULL(SUM(t1.total_max_commodity_cnt), 0) = 0 THEN 0
        ELSE ROUND(
          1 - IFNULL(SUM(t1.total_online_dish_cnt), 0) / SUM(t1.total_max_commodity_cnt),
          4
        )
      END AS '缺货率(sku权重)',
      -- 周session数：直接求和每日session数（不会重复）
      SUM(IFNULL(s.session_cnt, 0)) AS 'session数',
      -- 统计该周有几天的数据
      COUNT(DISTINCT t1.dt) AS days_count
    FROM
      shortage_by_date t1
      LEFT JOIN session_data s ON t1.dt = s.dt
    GROUP BY
      DATE_FORMAT(
        STR_TO_DATE(t1.dt, '%Y-%m-%d') - INTERVAL(DAYOFWEEK(STR_TO_DATE(t1.dt, '%Y-%m-%d')) - 1) DAY,
        '%Y-%m-%d'
      )
  )
SELECT
  `周起始日(周日)`,
  `缺货率(sku权重)`,
  `session数`
FROM
  weekly_data
  # WHERE days_count >= 7  -- 只显示完整的周（7天数据）
ORDER BY
  `周起始日(周日)` DESC