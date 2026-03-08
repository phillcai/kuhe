#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
订单回库商品判断工具
输入订单号，判断该订单中的盒菜是否可能为回库商品。

核心逻辑：
通过 order_product + order 获取订单的 点位+层架+商品ID，
LEFT JOIN central_kitchen_commodity_again 匹配回库记录。
如果该位置在下单前7天内有回库商品记录，则标记为 is_callback=Y。

注意：该方法判断的是"该层架位置存在回库商品"，而非"用户买到的这一份一定是回库的"，
因为同一层架可能同时有正常配送和回库商品混在一起。
"""

import argparse
import json
import os
import urllib.request
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

# 加载项目根目录的 .env 文件
load_dotenv(Path(__file__).parents[2] / '.env')

# Metabase 配置
METABASE_URL = os.environ.get('METABASE_URL', 'https://metabase.cookhere.com')
METABASE_API_KEY = os.environ['METABASE_API_KEY']
# DB=2: sg_readonly（central_kitchen_commodity_again 仅在此库上存在）
DATABASE_ID = 2


def metabase_query(sql, database_id=DATABASE_ID, timeout=60):
    """通过 Metabase API 执行 SQL 查询"""
    url = f"{METABASE_URL.rstrip('/')}/api/dataset"
    payload = json.dumps({
        'database': database_id,
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
        raise RuntimeError(f"Metabase 查询失败: {data.get('error', 'unknown')}")

    cols = [c['name'] for c in data['data']['cols']]
    rows = data['data']['rows']
    return [dict(zip(cols, row)) for row in rows]


def query_order_callback(order_no):
    """
    查询订单中盒菜是否可能为回库商品

    思路：
    1. order_product 获取 commodity_id, save_shelf_id
    2. order 获取 point_id
    3. LEFT JOIN central_kitchen_commodity_again 匹配回库记录
       条件: next_point_id = point_id, next_shelf_id = save_shelf_id,
             commodity_id 相同, callback_time 在下单前 7 天内
    4. 有匹配 → is_callback=Y, 无匹配 → is_callback=N
    """
    sql = f"""
        SELECT
            op.order_no,
            op.commodity_id,
            op.commodity_name,
            o.point_id,
            p.point_name,
            op.save_shelf_id,
            op.create_time AS order_time,
            CASE WHEN COUNT(DISTINCT ca.id) > 0 THEN 'Y' ELSE 'N' END AS is_callback,
            COUNT(DISTINCT ca.id) AS callback_count,
            MIN(ca.callback_time) AS earliest_callback,
            MAX(ca.callback_time) AS latest_callback,
            GROUP_CONCAT(DISTINCT ca.from_picking_no ORDER BY ca.from_picking_no) AS from_picking_nos
        FROM order_product op
        JOIN commodity c
            ON c.id = op.commodity_id
        JOIN `order` o
            ON o.order_no = op.order_no
        JOIN point p
            ON p.id = o.point_id
        LEFT JOIN central_kitchen_commodity_again ca
            ON ca.next_point_id = o.point_id
            AND ca.next_shelf_id = op.save_shelf_id
            AND ca.commodity_id = op.commodity_id
            AND ca.callback_time >= DATE_SUB(op.create_time, INTERVAL 7 DAY)
            AND ca.callback_time <= op.create_time
        WHERE op.order_no = '{order_no}'
          AND c.commodity_type = 1
        GROUP BY
            op.order_no, op.commodity_id, op.commodity_name,
            o.point_id, p.point_name, op.save_shelf_id, op.create_time
        ORDER BY op.commodity_id
    """

    print(f"\n查询订单 {order_no} 盒菜回库情况...")
    results = metabase_query(sql)

    if not results:
        print(f"未找到订单 {order_no} 的盒菜商品，请检查订单号")
        return

    df = pd.DataFrame(results)

    # 汇总
    callback_items = df[df['is_callback'] == 'Y']
    total = len(df)
    callback_count = len(callback_items)

    print(f"找到 {total} 个盒菜商品，其中 {callback_count} 个存在回库记录：\n")

    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', 40)
    try:
        print(df.to_markdown(index=False))
    except ImportError:
        print(df.to_string(index=False))

    if callback_count > 0:
        print(f"\n注意：is_callback=Y 表示该层架在下单前7天内有回库商品记录，")
        print(f"但不代表用户购买的这一份一定是回库商品（同层架可能混有正常配送商品）。")


def main():
    parser = argparse.ArgumentParser(description='判断订单盒菜是否可能为回库商品')
    parser.add_argument('order_no', help='订单号')
    args = parser.parse_args()

    query_order_callback(args.order_no)


if __name__ == '__main__':
    main()
