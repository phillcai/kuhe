-- BI 库

SELECT
  c.id,
  c.point_name,
  e.point_type,
  c.point_max_stock,
  c.latitude,
  c.longitude,
  c.point_address,
  c.create_time,
  CASE
    WHEN investor_id >= 6 THEN 1
    ELSE 0
  END AS '是否加盟商',
  d.data_type,
  d.start_time,
  d.end_time,
  d.remark,
  d.escort,
  car_type_limit,
  open_date,
  is_monitor,
  e.bd_sales,
  e.is_esg
FROM
  (
    SELECT
      a.id,
      a.point_name,
      investor_id,
      CASE
        WHEN device_type = 1 THEN 108
        WHEN a.id = 55 THEN 72
        ELSE 96
      END AS point_max_stock,
      a.latitude,
      a.longitude,
      a.point_address,
      a.create_time,
      is_monitor
    FROM
      (
        SELECT
          id,
          point_name,
          latitude,
          longitude,
          point_address,
          create_time,
          investor_id,
          is_monitor
        FROM
          smart_cooker_sg.point
      ) a
      LEFT JOIN (
        SELECT
          point_id,
          device_type
        FROM
          smart_cooker_sg.ai_device
      ) b ON a.id = b.point_id
  ) c
  LEFT JOIN (
    SELECT
      point_id,
      data_type,
      start_time,
      end_time,
      remark,
      escort
    FROM
      report.t_delivery_point_restrictions_detail
  ) d ON c.id = d.point_id
  LEFT JOIN (
    SELECT
      point_id,
      CASE
        WHEN point_size = 2 THEN '中'
        WHEN point_size = 3
        AND point_id IN (
          SELECT
            id
          FROM
            smart_cooker_sg.point
          WHERE
            is_monitor = 1
            AND investor_id <> 4
        ) THEN '中-加盟商'
        WHEN point_size = 3 THEN '小'
        WHEN point_size = 1 THEN '大'
        ELSE point_size
      END AS point_type,
      day7_avg_dish_cnt AS avg_dish_cnt,
      car_type_limit,
      open_date,
      bd_sales,
      is_esg
    FROM
      smart_cooker_sg.point_ext
  ) e ON e.point_id = c.id
  where is_monitor = 1 or open_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)