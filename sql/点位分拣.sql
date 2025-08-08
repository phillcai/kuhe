-- 使用WITH子句重构的点位分拣单查询
WITH 
-- 基础商品信息
base_commodity AS (
    SELECT *
    FROM smart_cooker_sg.commodity
    WHERE commodity_type = 1
    AND id IN (?)
),

-- 基础点位信息
base_point AS (
    SELECT *
    FROM smart_cooker_sg.point
    WHERE  id = ?
),

-- 点位开始营业时间
point_open_date AS (
    SELECT point_id,
           MIN(date(create_time)) min_dt
    FROM smart_cooker_sg.order
    WHERE create_time >= date_sub(current_date, interval 90 day)
    AND status IN (7, 8)
    AND order_mode = 1
    GROUP BY point_id
),

-- 点位最大库存配置
point_max_stock_config AS (
    SELECT a.id point_id,
           CASE WHEN device_type = 1 THEN 108
                WHEN a.id = 55 THEN 72 
                ELSE 96 END point_max_stock,
           CASE WHEN min_dt is null THEN current_date 
                ELSE min_dt END open_date
    FROM base_point a
    LEFT JOIN smart_cooker_sg.ai_device b ON a.id = b.point_id
    LEFT JOIN point_open_date c ON a.id = c.point_id
),

-- 5日预测销量数据
forecast_5day_data AS (
    SELECT point_id,
           round(coalesce(5_day_main_food_cnt,50),0) 5_day_main_food_cnt
    FROM (
        SELECT point_id,
               SUM(sale) 5_day_main_food_cnt
        FROM (
            SELECT t.point_id,
                   t.date,
                   (jt.h - 1) AS hour_index,
                   CAST(jt.val AS UNSIGNED) AS sale
            FROM report.t_point_hour_forecast_sale t, 
                 JSON_TABLE(t.hour_forecast_sale, '$[*]' COLUMNS(h FOR ORDINALITY, val INT PATH '$')) jt
            WHERE TIMESTAMP(t.date, SEC_TO_TIME((jt.h-1)*3600)) >= TIMESTAMP(CURDATE(), MAKETIME(HOUR(NOW()), 0, 0))
            AND TIMESTAMP(t.date, SEC_TO_TIME((jt.h-1)*3600)) < TIMESTAMP(CURDATE(), MAKETIME(HOUR(NOW()), 0, 0)) + INTERVAL 120 HOUR
            AND t.date >= CURRENT_DATE
            AND t.date <= date_add(CURRENT_DATE, interval 5 day)
            ORDER BY t.point_id, t.date, hour_index
        ) a
        GROUP BY point_id
    ) a
    GROUP BY point_id
),

-- 历史平均销量数据
avg_cnt_5day_data AS (
    SELECT a.point_id,
           coalesce(a.main_food_cnt,b.main_food_cnt,50) avg_cnt_5day
    FROM (
        SELECT point_id,
               CASE WHEN point_size = 3 THEN day7_avg_dish_cnt*5*1.0 
                    ELSE day7_avg_dish_cnt*5 END main_food_cnt
        FROM smart_cooker_sg.point_ext
    ) a
    LEFT JOIN (
        SELECT point_id,
               COUNT(1) main_food_cnt
        FROM t_order_wide
        WHERE country = 'Singapore'
        AND dt >= date_sub(current_date, interval 7 day)
        AND dt <= date_sub(current_date , interval 1 day)
        AND commodity_type = 1
        GROUP BY point_id
    ) b ON a.point_id = b.point_id
),

-- 全量补货点位
full_restock_points AS (
    SELECT distinct point_id
    FROM t_full_restock_order
    WHERE current_date >= date(date_sub(start_date, interval 1 day))
    AND current_date <= date(end_date)
),

-- 点位剩余库存
point_remain_stock AS (
    SELECT point_id,
           SUM(abs(amount))-SUM(abs(locked_amount)) point_remain_stock
    FROM smart_cooker_sg.inventory_point
    WHERE commodity_id IN (SELECT id FROM smart_cooker_sg.commodity WHERE commodity_type = 1)
    AND amount > 0
    AND point_id in (select id from base_point)
    GROUP BY point_id
),

-- 商品比重权重基础数据
commodity_ratio_base AS (
    SELECT point_id,
           commodity_id,
           ratio,
           COUNT(1) as cnt
    FROM t_commodity_ratio_weight
    WHERE dt IN (SELECT MAX(dt) FROM t_commodity_ratio_weight)
    and ratio>0
    GROUP BY point_id, commodity_id, ratio
),

-- 点位最小比重
point_min_ratio AS (
SELECT  a.point_id
       ,coalesce(a.ratio,b.ratio) ratio
FROM
(
	SELECT  point_id
	       ,ratio
	FROM
	(
		SELECT  point_id
		       ,ROW_NUMBER() OVER (PARTITION BY point_id ORDER BY  ratio DESC) rn
		       ,ratio
		FROM commodity_ratio_base
	) a
	WHERE rn = 6 
) a
LEFT JOIN
(
	SELECT  point_id
	       ,AVG(ratio) ratio
	FROM commodity_ratio_base
	GROUP BY  point_id
) b
ON a.point_id = b.point_id
),

-- 商品平均比重
commodity_avg_ratio AS (
    SELECT commodity_id,
           AVG(ratio) ratio
    FROM commodity_ratio_base
    GROUP BY commodity_id
),

-- 全局平均比重
global_avg_ratio AS (
    SELECT AVG(ratio) ratio
    FROM (
        SELECT point_id,
               AVG(ratio) ratio
        FROM commodity_ratio_base
        GROUP BY point_id
    ) a
),

-- 点位商品菜单关联
point_commodity_menu AS (
    SELECT b.commodity_id,
           a.id point_id,
           COUNT(1) as cnt
    FROM smart_cooker_sg.point a
    INNER JOIN smart_cooker_sg.menu_commodity b ON a.menu_id = b.menu_id
    GROUP BY b.commodity_id, a.id
),

-- 商品得分计算
commodity_dish_score AS (
    SELECT b.point_id,
           b.commodity_id,
           coalesce(coalesce(coalesce(c.ratio,d.ratio),e.ratio),f.ratio) dish_score
    FROM base_commodity a
    INNER JOIN point_commodity_menu b ON a.id = b.commodity_id
    LEFT JOIN commodity_ratio_base c ON b.commodity_id = c.commodity_id AND b.point_id = c.point_id
    LEFT JOIN point_min_ratio d ON b.point_id = d.point_id
    LEFT JOIN commodity_avg_ratio e ON b.commodity_id = e.commodity_id
    CROSS JOIN global_avg_ratio f
),

-- 点位总菜品得分
point_total_dish_score AS (
    SELECT point_id,
           SUM(dish_score) point_dish_score
    FROM commodity_dish_score
    GROUP BY point_id
),

-- 点位商品得分汇总
point_commodity_score AS (
    SELECT a.point_id,
           a.commodity_id,
           a.dish_score,
           b.point_dish_score
    FROM commodity_dish_score a
    INNER JOIN point_total_dish_score b ON a.point_id = b.point_id
),

-- 计算点位预测数量
point_amount_calc AS (
    SELECT a.point_id,
           point_max_stock,
           CASE WHEN DATEDIFF(current_date,open_date) <= 7 THEN point_max_stock
                WHEN coalesce(5_day_main_food_cnt,avg_cnt_5day) > point_max_stock THEN point_max_stock 
                ELSE coalesce(5_day_main_food_cnt,avg_cnt_5day) END point_amount
    FROM point_max_stock_config a
    LEFT JOIN forecast_5day_data c ON a.point_id = c.point_id
    LEFT JOIN avg_cnt_5day_data e ON a.point_id = e.point_id
),

-- 最终点位数量
final_point_amount AS (
    SELECT a.point_id,
           point_max_stock,
           CASE WHEN b.point_id is not null THEN a.point_max_stock 
                ELSE a.point_amount END point_amount
    FROM point_amount_calc a
    LEFT JOIN full_restock_points b ON a.point_id = b.point_id
),

-- 调整后的点位数量，去到的点位至少补20盒。
adjusted_point_amount AS (
    SELECT a.point_id,
           point_max_stock,
           if(point_amount-coalesce(b.point_remain_stock,0) <= 20,coalesce(b.point_remain_stock,0)+20,if(point_amount >= point_max_stock,point_max_stock,point_amount)) point_amount
    FROM final_point_amount a
    LEFT JOIN point_remain_stock b ON a.point_id = b.point_id
),

-- 商品主食数量计算
commodity_main_food_calc AS (
    SELECT a.point_id,
           b.commodity_id,
           CASE WHEN point_amount <= 60
                THEN if (round(point_amount * (b.dish_score/ point_dish_score),0) < 1,1,round(point_amount * (b.dish_score/ point_dish_score),0) )  
                ELSE if(round(point_amount * (b.dish_score/ point_dish_score)/3,0)*3 <= 3,3,round(point_amount * (b.dish_score/ point_dish_score)/3,0)*3) 
           END main_food_cnt
    FROM adjusted_point_amount a
    LEFT JOIN point_commodity_score b ON a.point_id = b.point_id
),

-- 点位商品库存
point_commodity_stock AS (
    SELECT point_id,
           commodity_id,
           SUM(abs(amount))-SUM(abs(locked_amount)) commodity_stock
    FROM smart_cooker_sg.inventory_point
    WHERE commodity_id IN (SELECT id FROM smart_cooker_sg.commodity WHERE commodity_type = 1)
    AND amount > 0
    AND point_id in (select id from base_point)
    GROUP BY point_id, commodity_id
),

-- 减去现有库存后的需求数量
final_main_food_cnt AS (
    SELECT a.point_id,
           a.commodity_id,
           CASE WHEN main_food_cnt-coalesce(b.commodity_stock,0) > 0 
                THEN main_food_cnt-coalesce(b.commodity_stock,0)  
                ELSE 0 END main_food_cnt
    FROM commodity_main_food_calc a
    LEFT JOIN point_commodity_stock b ON a.commodity_id = b.commodity_id AND a.point_id = b.point_id
),



-- 中央厨房库存
central_kitchen_inventory AS (
    SELECT commodity_id,
           SUM(qty) qty
    FROM smart_cooker_sg.central_kitchen_frame_inventory
    WHERE frame_id IN (SELECT distinct frame_id FROM smart_cooker_sg.central_kitchen_car_frame WHERE state = 2 AND car_id = ?)
    AND commodity_type = 1
    AND qty > 0
    GROUP BY commodity_id
)

-- 最终查询结果
SELECT a.commodity_id AS commodity_id,
       CASE WHEN coalesce(a.main_food_cnt,0) > coalesce(qty,0) 
            THEN coalesce(qty,0)  
            ELSE coalesce(a.main_food_cnt,0) END main_food_cnt,
       CASE WHEN coalesce(a.main_food_cnt,0) > coalesce(qty,0) 
            THEN 1  
            ELSE 0 END main_food_type
FROM final_main_food_cnt a
LEFT JOIN central_kitchen_inventory b ON a.commodity_id = b.commodity_id;