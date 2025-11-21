-- 查询点位商品和对应调料的库存情况
-- 筛选出调料库存-商品库存 <= 2 的数据

WITH point_commodity_stock AS (
  -- 获取每个点位的商品库存（commodity_type = 1）
  SELECT 
    A.id AS point_id,
    CASE
      WHEN C.point_size = 2 THEN 3
      WHEN C.point_size = 3 THEN 5
      WHEN C.point_size = 1 THEN 1
      ELSE 3
    END AS point_type,
    B.commodity_id,
    COALESCE(GREATEST(SUM(ABS(B.amount)) - SUM(ABS(B.locked_amount)), 0), 0) AS commodity_stock
  FROM 
    point A
    LEFT JOIN inventory_point B ON A.id = B.point_id
    LEFT JOIN point_ext C ON A.id = C.point_id
    INNER JOIN commodity D ON B.commodity_id = D.id AND D.commodity_type = 1
  WHERE 
    A.is_monitor = 1
  GROUP BY 
    A.id, B.commodity_id, C.point_size
),
point_spices_stock AS (
  -- 获取每个点位的调料库存（commodity_type = 3）
  SELECT 
    A.id AS point_id,
    B.commodity_id AS spices_id,
    COALESCE(GREATEST(SUM(ABS(B.amount)) - SUM(ABS(B.locked_amount)), 0), 0) AS spices_stock
  FROM 
    point A
    LEFT JOIN inventory_point B ON A.id = B.point_id
    LEFT JOIN point_ext C ON A.id = C.point_id
    INNER JOIN commodity D ON B.commodity_id = D.id AND D.commodity_type = 3
  WHERE 
    A.is_monitor = 1
  GROUP BY 
    A.id, B.commodity_id
)
SELECT 
  pcs.point_id,
  pcs.point_type,
  pcs.commodity_id,
  cm.name AS commodity_name,
  pcs.commodity_stock,
  cs.with_spices_id AS spices_id,
  sp.name AS spices_name,
  COALESCE(pss.spices_stock, 0) AS spices_stock,
  COALESCE(pss.spices_stock, 0) - pcs.commodity_stock AS stock_diff
FROM 
  point_commodity_stock pcs
  INNER JOIN commodity_spices cs ON pcs.commodity_id = cs.commodity_id
  LEFT JOIN point_spices_stock pss ON pcs.point_id = pss.point_id 
    AND cs.with_spices_id = pss.spices_id
  LEFT JOIN commodity cm ON pcs.commodity_id = cm.id
  LEFT JOIN commodity sp ON cs.with_spices_id = sp.id
WHERE 
  -- 筛选调料库存 - 商品库存 <= 2
  COALESCE(pss.spices_stock, 0) - pcs.commodity_stock <= 2
ORDER BY 
  pcs.point_id, 
  stock_diff ASC,
  pcs.commodity_id;

