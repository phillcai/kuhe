-- 央厨运营数据统计查询
-- 包含：央厨分拣、饮料甜品装车、点位补货、flash deal销售、损耗等数据
SELECT  a.dt AS '日期'
       ,a.picking_cnt AS '央厨分拣次数'
       ,a.total_qty AS '央厨总分拣盒菜数'
       ,a.t1 AS '盒菜总分拣时间'
       ,b.drink_amount AS '饮料总装车数量'
       ,b.dessert_amount AS '甜品总装车数量'
       ,b.t1 AS '饮料、甜品总分拣装车时间'
       ,c.t0 AS '补货点位次数'
       ,c.t1 AS '补货点位数'
FROM
(
	-- 央厨分拣数据统计
	SELECT  DATE(create_time) AS dt
	       ,COUNT(DISTINCT picking_no) AS picking_cnt
	       ,SUM(total_qty) AS total_qty
	       ,SUM(picking_time) AS t1
	FROM
	(
		-- 解析JSON数据并计算分拣时间和数量
		SELECT  DATE(ckt.create_time) AS create_time
		       ,ckt.picking_no
		       ,SUM(CASE 
		            WHEN JSON_UNQUOTE(JSON_EXTRACT(ckt.actual_ext, CONCAT('$[', n.rn - 1, '].commodity_id'))) != '111' 
		            THEN CAST(JSON_UNQUOTE(JSON_EXTRACT(ckt.actual_ext, CONCAT('$[', n.rn - 1, '].qty'))) AS UNSIGNED) 
		            ELSE 0 
		        END) AS total_qty
		       ,TIMESTAMPDIFF(MINUTE, ctl.kitchen_start_time, ctl.kitchen_end_time) AS picking_time
		FROM central_kitchen_picking_task ckt
		INNER JOIN (
			-- 获取分拣时间范围
			SELECT  task_id
			       ,MAX(CASE WHEN state = 2 THEN create_time END) AS kitchen_start_time
			       ,MAX(CASE WHEN state = 3 THEN create_time END) AS kitchen_end_time
			FROM central_kitchen_task_log
			WHERE car_id IN (SELECT id FROM central_kitchen_car WHERE {{car_no}})
			GROUP BY task_id
		) ctl ON ckt.id = ctl.task_id
		CROSS JOIN report.t_numbers n
		WHERE ckt.state IN (3, 4)
		  AND LENGTH(ckt.actual_ext) > 0
		  AND DATE(ckt.create_time) >= DATE_SUB(CURRENT_DATE, INTERVAL 7 DAY)
		  AND ckt.car_id IN (SELECT id FROM central_kitchen_car WHERE {{car_no}})
		  AND JSON_EXTRACT(ckt.actual_ext, CONCAT('$[', n.rn - 1, ']')) IS NOT NULL
		  AND CAST(JSON_UNQUOTE(JSON_EXTRACT(ckt.actual_ext, CONCAT('$[', n.rn - 1, '].commodity_id'))) AS UNSIGNED) 
		      IN (SELECT id FROM commodity WHERE commodity_type = 1 OR id = 111)
		GROUP BY DATE(ckt.create_time), ckt.picking_no, ctl.kitchen_start_time, ctl.kitchen_end_time
	) picking_data
	GROUP BY DATE(create_time)
) a
LEFT JOIN
(
	-- 饮料甜品装车数据统计
	SELECT  DATE(create_time) AS dt
	       ,SUM(drink_amount) AS drink_amount
	       ,SUM(dessert_amount) AS dessert_amount
	       ,SUM(TIMESTAMPDIFF(MINUTE, min_create_time, max_update_time)) AS t1
	FROM
	(
		-- 解析装车任务JSON数据
		SELECT  cct.create_time
		       ,batch_picking.picking_no AS picking_no_new
		       ,SUM(CASE 
		            WHEN CAST(JSON_UNQUOTE(JSON_EXTRACT(cct.ext, CONCAT('$.commodity[', n.rn - 1, '].c_id'))) AS UNSIGNED) 
		                 IN (SELECT id FROM commodity WHERE commodity_type = 5) 
		            THEN CAST(JSON_UNQUOTE(JSON_EXTRACT(cct.ext, CONCAT('$.commodity[', n.rn - 1, '].qty'))) AS UNSIGNED) 
		            ELSE 0 
		        END) AS drink_amount
		       ,SUM(CASE 
		            WHEN CAST(JSON_UNQUOTE(JSON_EXTRACT(cct.ext, CONCAT('$.commodity[', n.rn - 1, '].c_id'))) AS UNSIGNED) 
		                 IN (SELECT id FROM commodity WHERE commodity_type = 6) 
		            THEN CAST(JSON_UNQUOTE(JSON_EXTRACT(cct.ext, CONCAT('$.commodity[', n.rn - 1, '].qty'))) AS UNSIGNED) 
		            ELSE 0 
		        END) AS dessert_amount
		       ,MAX(cct.update_time) AS max_update_time
		       ,MIN(cct.create_time) AS min_create_time
		FROM central_kitchen_car_task cct
		INNER JOIN (
			-- 获取批次对应的分拣号
			SELECT  batch_no
			       ,picking_no
			FROM central_kitchen_car_task
			WHERE LENGTH(picking_no) > 0
			  AND car_id IN (SELECT id FROM central_kitchen_car WHERE {{car_no}})
			GROUP BY batch_no, picking_no
		) batch_picking ON cct.batch_no = batch_picking.batch_no
		CROSS JOIN report.t_numbers n
		WHERE cct.task_type = 3
		  AND cct.state = 2
		  AND JSON_EXTRACT(cct.ext, CONCAT('$.commodity[', n.rn - 1, ']')) IS NOT NULL
		GROUP BY cct.create_time, batch_picking.picking_no
	) loading_data
	GROUP BY DATE(create_time)
) b
ON a.dt = b.dt
WHERE a.dt >= DATE_SUB(CURRENT_DATE, INTERVAL 7 DAY)
ORDER BY a.dt DESC; 