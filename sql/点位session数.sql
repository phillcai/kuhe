-- 指定日期之后的 session 数（按 point_id、按天聚合）
-- 数据源：report.t_user_bhv_session，口径与周缺货率中的「活跃 session」一致
-- 参数：{{dt}} 起始日期，如 '2025-01-15'（统计 dt >= 该日期的数据）

WITH
-- APP 渠道：按点位、按天的活跃 session 数（activity_uid 有效）
app_sessions AS (
    SELECT
        point_id,
        dt,
        COUNT(DISTINCT session_id) AS session_cnt
    FROM report.t_user_bhv_session
    WHERE source = 'app'
      AND country = 'Singapore'
      AND point_id IN (SELECT id FROM report.t_point WHERE country = 'Singapore')
      AND point_id IN (SELECT id FROM smart_cooker_sg.point_ext WHERE 1 = 1)
      AND dt >= {{dt}}              -- 指定日期之后，如 '2025-01-15'
      AND LENGTH(activity_uid) > 4
    GROUP BY point_id, dt
),
-- 点餐屏渠道：按点位、按天的活跃 session 数（menu_uid 有效）
offline_sessions AS (
    SELECT
        point_id,
        dt,
        COUNT(DISTINCT session_id) AS session_cnt
    FROM report.t_user_bhv_session
    WHERE source = 'offline'
      AND country = 'Singapore'
      AND point_id IN (SELECT id FROM report.t_point WHERE country = 'Singapore')
      AND point_id IN (SELECT id FROM smart_cooker_sg.point_ext WHERE 1 = 1)
      AND dt >= {{dt}}
      AND LENGTH(menu_uid) > 4
    GROUP BY point_id, dt
),
-- 所有有数据的 (point_id, dt)
all_point_dt AS (
    SELECT point_id, dt FROM app_sessions
    UNION
    SELECT point_id, dt FROM offline_sessions
)
SELECT
    d.point_id,
    d.dt,
    IFNULL(a.session_cnt, 0) + IFNULL(o.session_cnt, 0) AS total_session_cnt
FROM all_point_dt d
LEFT JOIN app_sessions a ON d.point_id = a.point_id AND d.dt = a.dt
LEFT JOIN offline_sessions o ON d.point_id = o.point_id AND d.dt = o.dt
HAVING total_session_cnt > 0
ORDER BY d.point_id, d.dt;
