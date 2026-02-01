-- 缺货率：当日 vs 上周同期（按自然日对齐）
-- 数据源：point_session_log（commodity_list JSON）+ smart_cooker_sg.commodity / point_ext / ai_device
-- 参数：{{day}} 最近天数（含今天）；{{snippet: chill+ points}} 排除的点位 id 列表

WITH
  -- 0) 完整自然日窗口（包含今天）
  params AS (
    SELECT
      -- cur：最近 {{day}} 天（包含今天）
      TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL {{day}} - 1 DAY)) AS cur_start,
      TIMESTAMP(DATE_ADD(CURDATE(), INTERVAL 1 DAY)) AS cur_end,
      -- lw：上周同期（整体前移 7 天）
      TIMESTAMP(
        DATE_SUB(
          DATE_SUB(CURDATE(), INTERVAL 7 DAY),
          INTERVAL {{day}} - 1 DAY
        )
      ) AS lw_start,
      TIMESTAMP(
        DATE_SUB(
          DATE_ADD(CURDATE(), INTERVAL 1 DAY),
          INTERVAL 7 DAY
        )
      ) AS lw_end
  ),
  -- 1) 展开 JSON + 两个 period（cur / lw）
  raw_items AS (
    -- 当前窗口（包含今天）
    SELECT
      'cur' AS period,
      DATE(psl.create_time) AS dt,
      psl.point_id,
      psl.session_id,
      jt.id AS commodity_id,
      jt.qty AS qty
    FROM
      point_session_log psl
      JOIN params p
      JOIN JSON_TABLE(
        psl.commodity_list,
        '$[*]' COLUMNS (id INT PATH '$.id', qty INT PATH '$.qty')
      ) jt
    WHERE
      psl.create_time >= '2026-01-01 00:00:00'
      AND psl.create_time >= p.cur_start
      AND psl.create_time < p.cur_end
      AND jt.qty > 0
      AND psl.point_id NOT IN ({{snippet: chill+ points}})
    UNION ALL
    -- 上周同期（完整自然日）
    SELECT
      'lw' AS period,
      DATE(psl.create_time) AS dt,
      psl.point_id,
      psl.session_id,
      jt.id AS commodity_id,
      jt.qty AS qty
    FROM
      point_session_log psl
      JOIN params p
      JOIN JSON_TABLE(
        psl.commodity_list,
        '$[*]' COLUMNS (id INT PATH '$.id', qty INT PATH '$.qty')
      ) jt
    WHERE
      psl.create_time >= '2026-01-01 00:00:00'
      AND psl.create_time >= p.lw_start
      AND psl.create_time < p.lw_end
      AND jt.qty > 0
      AND psl.point_id NOT IN ({{snippet: chill+ points}})
  ),
  -- 2) 商品 & 设备过滤
  valid_items AS (
    SELECT
      r.period,
      r.dt,
      r.point_id,
      r.session_id,
      r.commodity_id
    FROM
      raw_items r
      JOIN smart_cooker_sg.commodity c ON c.id = r.commodity_id
      AND c.commodity_type = 1
    WHERE
      NOT EXISTS (
        SELECT 1
        FROM ai_device d
        WHERE d.point_id = r.point_id
          AND d.point_id <> 0
          AND d.spice_cabinet_type = 5
          AND d.device_type = 8
      )
  ),
  -- 3) session 粒度：在线 SKU 数
  session_online AS (
    SELECT
      period,
      dt,
      point_id,
      session_id,
      COUNT(DISTINCT commodity_id) AS online_dish_cnt
    FROM valid_items
    GROUP BY period, dt, point_id, session_id
  ),
  -- 4) 点位满配
  point_full AS (
    SELECT
      pe.point_id,
      CASE
        WHEN pe.point_size IN (1, 2) THEN 8
        WHEN pe.point_size = 3 THEN 6
        ELSE NULL
      END AS full_session_dish_cnt
    FROM smart_cooker_sg.point_ext pe
  ),
  -- 5) session KPI
  session_kpi AS (
    SELECT
      s.period,
      s.dt,
      s.point_id,
      s.session_id,
      LEAST(s.online_dish_cnt, pf.full_session_dish_cnt) AS session_dish_cnt,
      CASE
        WHEN s.online_dish_cnt < pf.full_session_dish_cnt THEN 1
        ELSE 0
      END AS is_shortage_session,
      pf.full_session_dish_cnt
    FROM session_online s
    JOIN point_full pf ON pf.point_id = s.point_id
      AND pf.full_session_dish_cnt IS NOT NULL
  ),
  -- 6) 日聚合
  daily AS (
    SELECT
      period,
      dt,
      1 - SUM(session_dish_cnt) / SUM(full_session_dish_cnt) AS shortage_rate_sku_w,
      SUM(is_shortage_session) / COUNT(*) AS shortage_rate_session,
      COUNT(DISTINCT CONCAT(point_id, '-', session_id)) AS session_cnt
    FROM session_kpi
    GROUP BY period, dt
  ),
  -- 7) 对齐上周同期（cur.dt ↔ lw.dt + 7）
  cur_vs_lw AS (
    SELECT
      c.dt,
      c.shortage_rate_sku_w AS 缺货率,
      l.shortage_rate_sku_w AS 上周缺货率,
      c.session_cnt AS session_cnt,
      l.session_cnt AS 上周session_cnt
    FROM daily c
    LEFT JOIN daily l
      ON c.period = 'cur'
      AND l.period = 'lw'
      AND l.dt = DATE_SUB(c.dt, INTERVAL 7 DAY)
    WHERE c.period = 'cur'
  )
SELECT *
FROM cur_vs_lw
ORDER BY dt;
