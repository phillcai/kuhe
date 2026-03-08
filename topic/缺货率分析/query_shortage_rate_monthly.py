#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
盒菜缺货率按月汇总分析
逐天查询 2026-01-01 到今天的缺货率，写入 CSV，最后按月汇总日均缺货率。

口径：027_盒菜缺货率.md
- 缺货率 = 1 - SUM(session_dish_cnt) / SUM(full_session_dish_cnt)
- 排除 chill+ 点位（ai_device.device_type=8）
- 排除 spice_cabinet_type=5 的设备点位
- 仅统计盒菜（commodity_type=1）
- 满仓：大/中点位(point_size 1,2)=8，小点位(point_size 3)=6
"""

import json
import os
import time
import urllib.request
from datetime import date, timedelta

import pandas as pd

# Metabase 配置
METABASE_URL = os.environ.get('METABASE_URL', 'https://metabase.cookhere.com')
METABASE_API_KEY = os.environ.get(
    'METABASE_API_KEY',
    'mb_NUQJxEWsIOto6qmK7ESRrI5Y8AhBMUQ91lras5XrNGA=',
)
DATABASE_ID = 35  # smart_cooker_sg


def metabase_query(sql: str, timeout: int = 120) -> list[dict]:
    """通过 Metabase API 执行 SQL 查询"""
    url = f"{METABASE_URL.rstrip('/')}/api/dataset"
    payload = json.dumps({
        'database': DATABASE_ID,
        'type': 'native',
        'native': {'query': sql},
    }).encode('utf-8')

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            'Content-Type': 'application/json',
            'x-api-key': METABASE_API_KEY,
        },
    )

    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode('utf-8'))

    if data.get('status') == 'failed':
        raise RuntimeError(f"查询失败: {data.get('error', 'unknown')}")

    cols = [c['name'] for c in data['data']['cols']]
    rows = data['data']['rows']
    return [dict(zip(cols, row)) for row in rows]


def query_day_shortage_rate(day: date) -> dict:
    """查询单天的盒菜缺货率"""
    next_day = day + timedelta(days=1)
    sql = f"""
WITH
  raw_items AS (
    SELECT psl.point_id, psl.session_id, jt.id AS commodity_id
    FROM point_session_log psl
      JOIN JSON_TABLE(psl.commodity_list, '$[*]' COLUMNS (id INT PATH '$.id', qty INT PATH '$.qty')) jt
    WHERE psl.create_time >= '{day} 00:00:00'
      AND psl.create_time < '{next_day} 00:00:00'
      AND jt.qty > 0
      AND psl.point_id NOT IN (
        SELECT DISTINCT point_id FROM ai_device WHERE device_type = 8 AND point_id > 0
      )
      AND psl.point_id NOT IN (
        SELECT DISTINCT point_id FROM ai_device WHERE device_type = 8 AND point_id <> 0 AND spice_cabinet_type = 5
      )
      AND jt.id IN (SELECT id FROM smart_cooker_sg.commodity WHERE commodity_type = 1)
  ),
  session_online AS (
    SELECT point_id, session_id, COUNT(DISTINCT commodity_id) AS online_dish_cnt
    FROM raw_items GROUP BY point_id, session_id
  ),
  point_full AS (
    SELECT pe.point_id,
      CASE WHEN pe.point_size IN (1,2) THEN 8 WHEN pe.point_size = 3 THEN 6 ELSE NULL END AS full_cnt
    FROM smart_cooker_sg.point_ext pe WHERE pe.point_size IN (1,2,3)
  )
SELECT
  SUM(LEAST(s.online_dish_cnt, pf.full_cnt))  AS sum_session_dish,
  SUM(pf.full_cnt)                             AS sum_full_dish,
  COUNT(*)                                     AS session_cnt
FROM session_online s
JOIN point_full pf ON pf.point_id = s.point_id
"""
    rows = metabase_query(sql)
    if not rows:
        return {'dt': str(day), 'shortage_rate': None, 'session_cnt': 0}

    r = rows[0]
    sum_session = r['sum_session_dish']
    sum_full = r['sum_full_dish']
    session_cnt = r['session_cnt']

    if not sum_full or sum_full == 0:
        shortage_rate = None
    else:
        shortage_rate = round((1 - sum_session / sum_full) * 100, 2)

    return {'dt': str(day), 'shortage_rate': shortage_rate, 'session_cnt': session_cnt}


def main():
    start_date = date(2026, 1, 1)
    end_date = date.today()

    # 生成所有需要查询的日期
    dates = []
    d = start_date
    while d <= end_date:
        dates.append(d)
        d += timedelta(days=1)

    print(f"查询范围：{start_date} ~ {end_date}，共 {len(dates)} 天")

    # 逐天查询
    results = []
    for i, day in enumerate(dates):
        print(f"[{i+1}/{len(dates)}] 查询 {day}...", end='', flush=True)
        try:
            row = query_day_shortage_rate(day)
            results.append(row)
            rate_str = f"{row['shortage_rate']}%" if row['shortage_rate'] is not None else "N/A"
            print(f" 缺货率={rate_str}, sessions={row['session_cnt']}")
        except Exception as e:
            print(f" 失败: {e}")
            results.append({'dt': str(day), 'shortage_rate': None, 'session_cnt': 0})

        # 避免请求过快
        time.sleep(0.3)

    # 写入每日 CSV
    df_daily = pd.DataFrame(results)
    os.makedirs('output', exist_ok=True)
    daily_csv = 'output/shortage_rate_daily.csv'
    df_daily.to_csv(daily_csv, index=False, encoding='utf-8-sig')
    print(f"\n每日数据已写入：{daily_csv}")

    # 按月汇总：日均缺货率
    df_valid = df_daily[df_daily['shortage_rate'].notna()].copy()
    df_valid['month'] = df_valid['dt'].str[:7]

    monthly = (
        df_valid.groupby('month')
        .agg(
            统计天数=('shortage_rate', 'count'),
            日均缺货率=('shortage_rate', 'mean'),
        )
        .reset_index()
        .rename(columns={'month': '月份'})
    )
    monthly['日均缺货率'] = monthly['日均缺货率'].round(2)

    monthly_csv = 'output/shortage_rate_monthly.csv'
    monthly.to_csv(monthly_csv, index=False, encoding='utf-8-sig')
    print(f"月度汇总已写入：{monthly_csv}")

    print("\n=== 近3个月日均缺货率汇总 ===")
    print(monthly.to_string(index=False))


if __name__ == '__main__':
    main()
