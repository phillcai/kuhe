SELECT  u.dt
       ,AVG(u.online_dish_cnt / p.sku_cnt) AS `菜品充足度(SUM(每个sesion有库存菜品数)/(session数*14))`
       ,COUNT(DISTINCT u.session_id)       AS `session数量`
FROM
(
	SELECT  dt
	       ,point_id
	       ,session_id
	       ,COUNT(DISTINCT commodity_id) AS online_dish_cnt
	FROM t_user_bhv_dish
	WHERE {{dt}}
	AND country = 'Singapore'
	AND stock > 0
	AND commodity_id IN ( SELECT id FROM smart_cooker_sg.commodity WHERE commodity_type = 1)
	GROUP BY  dt
	         ,point_id
	         ,session_id
) u
JOIN
(
	SELECT  id
	       ,CASE WHEN device_type = 1 THEN 15
	             WHEN device_type = 5 THEN 10  ELSE 15 END AS sku_cnt
	FROM t_point
	WHERE country = 'Singapore'
	AND {{point_name}} -- 例如：name LIKE '%xxx%' 
 
) p
ON p.id = u.point_id
GROUP BY  u.dt;