#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统计最近 2 天回库的盒菜 SKU 分布
查询 central_kitchen_task_log 表中最近 2 天的回库任务记录，
提取 car_ext 字段中 commodity_type=1（盒菜）的数据，
按每个 SKU（commodity_id）聚合回库数量。
"""

import sys
import os
import json
from datetime import datetime
import pandas as pd

# 添加 code 目录到 Python 路径，以便导入 lib 模块
code_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../code'))
sys.path.insert(0, code_dir)

from lib import create_db_connection


def get_recent_return_records(days=2, db=None):
    """
    获取最近几天的回库记录（所有车辆）

    Args:
        days: 查询最近几天的数据，默认为 2 天
        db: 数据库连接对象，如果为 None 则创建新连接

    Returns:
        tuple: (回库记录列表, 数据库连接对象)
    """
    if db is None:
        print(f"正在连接数据库 (smart_cooker_sg)...")
        try:
            db = create_db_connection(mysql_database='smart_cooker_sg')
        except Exception as e:
            print(f"连接数据库失败: {e}")
            return [], None

    print(f"正在查询最近 {days} 天的回库记录 (task_type=8)...")

    sql = """
        SELECT id, car_id, create_time, car_ext
        FROM central_kitchen_task_log
        WHERE task_type = 8
          AND DATE(create_time) >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
        ORDER BY id DESC
    """

    try:
        # days=2 表示查今天和昨天，传 days-1=1 使 INTERVAL 覆盖恰好 2 个自然日
        results = db.execute_query(sql, (days - 1,))
        print(f"✅ 查询成功！共查询到 {len(results)} 条回库记录\n")
        return results, db
    except Exception as e:
        print(f"❌ 查询失败: {e}")
        return [], db


def get_commodity_names(db, commodity_ids):
    """
    批量查询商品ID对应的商品名称和类型

    Args:
        db: 数据库连接对象
        commodity_ids: 商品ID列表

    Returns:
        dict: {commodity_id: {'name': ..., 'type': ...}} 的字典
    """
    if not commodity_ids:
        return {}

    placeholders = ','.join(['%s'] * len(commodity_ids))
    # 尝试常见的商品名称字段名
    sql = f"""
        SELECT id, commodity_type, name
        FROM commodity
        WHERE id IN ({placeholders})
    """

    try:
        results = db.execute_query(sql, tuple(commodity_ids))
        return {
            row['id']: {
                'name': row.get('name', f"商品{row['id']}"),
                'type': row['commodity_type']
            }
            for row in results
        }
    except Exception as e:
        print(f"⚠️ 查询商品名称失败，尝试不带 name 字段: {e}")
        # 降级：只查类型
        try:
            sql_fallback = f"""
                SELECT id, commodity_type
                FROM commodity
                WHERE id IN ({placeholders})
            """
            results = db.execute_query(sql_fallback, tuple(commodity_ids))
            return {
                row['id']: {
                    'name': f"商品{row['id']}",
                    'type': row['commodity_type']
                }
                for row in results
            }
        except Exception as e2:
            print(f"⚠️ 查询商品类型也失败: {e2}")
            return {}


def parse_car_ext_boxmeal(car_ext_str):
    """
    解析 car_ext JSON 字段，提取所有商品的 SKU 和数量（不在此阶段过滤类型）。
    盒菜过滤在数据库补全 commodity_type 后由调用方完成。

    Args:
        car_ext_str: car_ext 字段的字符串（JSON 格式）

    Returns:
        dict: {commodity_id: (commodity_type_or_None, qty)} 的字典
              commodity_type 可能为 None，表示 JSON 中未提供，需后续查询数据库补全
    """
    if not car_ext_str:
        return {}

    try:
        car_ext = json.loads(car_ext_str)
        # 收集所有商品条目：{commodity_id: (commodity_type_or_None, qty)}
        raw_items = {}

        def extract_items(obj):
            if isinstance(obj, dict):
                if 'commodity_id' in obj and 'qty' in obj:
                    cid = obj.get('commodity_id')
                    ctype = obj.get('commodity_type')
                    qty = obj.get('qty', 0)
                    if cid is not None and qty:
                        cid = int(cid)
                        qty = int(qty)
                        if cid in raw_items:
                            prev_type, prev_qty = raw_items[cid]
                            raw_items[cid] = (ctype if ctype is not None else prev_type, prev_qty + qty)
                        else:
                            raw_items[cid] = (ctype, qty)
                else:
                    for value in obj.values():
                        extract_items(value)
            elif isinstance(obj, list):
                for item in obj:
                    extract_items(item)

        if isinstance(car_ext, dict):
            for key, value in car_ext.items():
                if isinstance(value, (list, dict)):
                    extract_items(value)
                elif isinstance(value, (int, float)) and value > 0:
                    # 结构: {"commodity_id": qty}
                    try:
                        cid = int(key)
                        raw_items[cid] = (None, int(value))
                    except (ValueError, TypeError):
                        pass
        elif isinstance(car_ext, list):
            extract_items(car_ext)

        return raw_items

    except (json.JSONDecodeError, ValueError, TypeError) as e:
        print(f"⚠️ 解析 car_ext 失败: {e}, 内容: {car_ext_str[:200] if car_ext_str else 'None'}")
        return {}


def aggregate_boxmeal_sku(results, db):
    """
    从回库记录中提取盒菜 SKU 分布，按 commodity_id 汇总回库数量

    Args:
        results: 回库记录列表
        db: 数据库连接对象

    Returns:
        DataFrame: 每行为一个 SKU，包含 commodity_id、商品名称、回库总数量、出现次数等
    """
    if not results:
        return pd.DataFrame()

    # 第一步：解析所有记录，收集盒菜相关的 commodity_id
    # sku_data: {commodity_id: {'qty': 总数量, 'records': 出现次数, 'type_in_json': commodity_type_or_None}}
    all_raw_items = {}  # {commodity_id: (commodity_type_or_None, total_qty, record_count)}

    for record in results:
        car_ext = record.get('car_ext')
        raw_items = parse_car_ext_boxmeal(car_ext)

        for cid, (ctype, qty) in raw_items.items():
            if cid in all_raw_items:
                prev_type, prev_qty, prev_cnt = all_raw_items[cid]
                all_raw_items[cid] = (ctype or prev_type, prev_qty + qty, prev_cnt + 1)
            else:
                all_raw_items[cid] = (ctype, qty, 1)

    if not all_raw_items:
        print("⚠️ 未从 car_ext 中提取到任何商品数据")
        return pd.DataFrame()

    # 第二步：查询没有 commodity_type 的商品 ID，或需要商品名称的所有 ID
    all_cids = list(all_raw_items.keys())
    print(f"正在查询 {len(all_cids)} 个商品的名称和类型...")
    commodity_info = get_commodity_names(db, all_cids)

    # 第三步：筛选出盒菜（commodity_type=1），汇总结果
    rows = []
    for cid, (ctype_in_json, total_qty, record_cnt) in all_raw_items.items():
        # 优先使用数据库查询到的类型，其次用 JSON 中的类型
        info = commodity_info.get(cid, {})
        ctype = info.get('type') if info else ctype_in_json
        if ctype is None:
            ctype = ctype_in_json

        # 仅保留盒菜
        if ctype != 1:
            continue

        name = info.get('name', f"商品{cid}") if info else f"商品{cid}"
        rows.append({
            'commodity_id': cid,
            '商品名称': name,
            '回库总数量': total_qty,
            '出现次数（回库单数）': record_cnt,
            '平均每单数量': round(total_qty / record_cnt, 1) if record_cnt > 0 else 0,
        })

    if not rows:
        print("⚠️ 过滤后没有盒菜数据（commodity_type=1）")
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df = df.sort_values('回库总数量', ascending=False).reset_index(drop=True)
    return df


def display_and_save(df, days):
    """
    展示统计结果并保存 CSV

    Args:
        df: 统计结果 DataFrame
        days: 查询天数
    """
    if df.empty:
        print("无数据可显示。")
        return

    print("\n" + "=" * 80)
    print(f"最近 {days} 天回库盒菜 SKU 分布（共 {len(df)} 个 SKU）")
    print("=" * 80)

    try:
        print(df.to_markdown(index=False))
    except ImportError:
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        print(df.to_string(index=False))

    # 汇总统计
    print(f"\n汇总：")
    print(f"  盒菜 SKU 总数：{len(df)}")
    print(f"  回库盒菜总数量：{df['回库总数量'].sum()}")
    print(f"  回库数量最多的 SKU：{df.iloc[0]['商品名称']}（{df.iloc[0]['commodity_id']}），数量 {df.iloc[0]['回库总数量']}")

    # 保存结果
    output_dir = os.path.dirname(os.path.abspath(__file__))
    date_str = datetime.now().strftime('%Y%m%d')
    csv_path = os.path.join(output_dir, f'boxmeal_return_sku_dist_{date_str}.csv')
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"\n✅ 结果已保存至: {csv_path}")


def main():
    """主函数"""
    days = 2  # 查询最近 2 天

    results, db = get_recent_return_records(days=days)

    if not results:
        print("未查询到任何回库记录。")
        return

    df = aggregate_boxmeal_sku(results, db)
    display_and_save(df, days)


if __name__ == "__main__":
    main()
