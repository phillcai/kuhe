#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取最近几天车辆的回库记录
查询 central_kitchen_task_log 表中指定车辆最近几天的回库任务记录
统计每条记录中 car_ext 字段的数据，按 commodity_type 聚合 qty 之和
"""

import sys
import os
import json
from datetime import datetime
from collections import defaultdict
import pandas as pd

# 添加 code 目录到 Python 路径，以便导入 lib 模块
code_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../code'))
sys.path.insert(0, code_dir)

from lib import create_db_connection


def get_recent_return_records(car_ids=None, task_type=8, days=3, db=None):
    """
    获取指定车辆最近几天的回库记录
    
    Args:
        car_ids: 车辆ID列表或单个车辆ID，默认为[2, 14, 15]。可以是列表、元组或单个整数
        task_type: 任务类型，默认为8（回库任务）
        days: 查询最近几天的数据，默认为3天
        db: 数据库连接对象，如果为None则创建新连接
    
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
    
    # 处理 car_ids 参数：支持单个整数、列表或元组
    if car_ids is None:
        car_ids = [2, 14, 15]
    elif isinstance(car_ids, int):
        car_ids = [car_ids]
    elif isinstance(car_ids, (list, tuple)):
        car_ids = list(car_ids)
    else:
        raise ValueError(f"car_ids 必须是整数、列表或元组，当前类型: {type(car_ids)}")
    
    car_ids_str = ', '.join(map(str, car_ids))
    print(f"正在查询车辆 {car_ids_str} 最近 {days} 天的回库记录 (task_type={task_type})...")
    
    # 构建 SQL 查询，使用 IN 子句
    placeholders = ','.join(['%s'] * len(car_ids))
    sql = f"""
        SELECT * 
        FROM central_kitchen_task_log
        WHERE car_id IN ({placeholders})
          AND task_type = %s
          AND DATE(create_time) >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
        ORDER BY id DESC
    """
    
    try:
        # 构建参数元组：car_ids + task_type + days
        params = tuple(car_ids) + (task_type, days)
        results = db.execute_query(sql, params)
        print(f"✅ 查询成功！共查询到 {len(results)} 条记录\n")
        return results, db
    except Exception as e:
        print(f"❌ 查询失败: {e}")
        return [], db


def get_commodity_types(db, commodity_ids):
    """
    批量查询商品ID对应的商品类型
    
    Args:
        db: 数据库连接对象
        commodity_ids: 商品ID列表
    
    Returns:
        dict: {commodity_id: commodity_type} 的字典
    """
    if not commodity_ids:
        return {}
    
    # 构建查询SQL，使用 IN 子句批量查询
    placeholders = ','.join(['%s'] * len(commodity_ids))
    sql = f"""
        SELECT id, commodity_type
        FROM commodity
        WHERE id IN ({placeholders})
    """
    
    try:
        results = db.execute_query(sql, tuple(commodity_ids))
        return {row['id']: row['commodity_type'] for row in results}
    except Exception as e:
        print(f"⚠️ 查询商品类型失败: {e}")
        return {}


def parse_car_ext(car_ext_str):
    """
    解析 car_ext JSON 字段，提取商品ID、商品类型和数量
    
    Args:
        car_ext_str: car_ext 字段的字符串（JSON格式）
    
    Returns:
        list: [(commodity_id, commodity_type, qty), ...] 列表
    """
    if not car_ext_str:
        return []
    
    try:
        car_ext = json.loads(car_ext_str)
        items = []
        
        def extract_items_from_dict(obj):
            """递归提取字典中的商品信息"""
            if isinstance(obj, dict):
                # 检查是否是商品对象（包含 commodity_id 和 qty）
                if 'commodity_id' in obj and 'qty' in obj:
                    commodity_id = obj.get('commodity_id')
                    commodity_type = obj.get('commodity_type')  # 可能直接包含在JSON中
                    qty = obj.get('qty', 0)
                    if commodity_id is not None and qty:
                        items.append((int(commodity_id), commodity_type, int(qty)))
                else:
                    # 遍历字典的值，可能是嵌套结构
                    for value in obj.values():
                        extract_items_from_dict(value)
            elif isinstance(obj, list):
                # 遍历数组元素
                for item in obj:
                    extract_items_from_dict(item)
        
        # 处理不同的JSON结构
        if isinstance(car_ext, dict):
            # 结构1: {"frame_id": [{"commodity_id": 227, "commodity_type": 6, "qty": 14}, ...], ...}
            # 结构2: {"commodity_id": {"qty": 10}, ...}
            # 结构3: {"commodity_id": qty, ...}
            for key, value in car_ext.items():
                if isinstance(value, dict):
                    # 检查是否是商品对象
                    if 'commodity_id' in value and 'qty' in value:
                        commodity_id = value.get('commodity_id') or key
                        commodity_type = value.get('commodity_type')
                        qty = value.get('qty', 0)
                        if commodity_id and qty:
                            items.append((int(commodity_id), commodity_type, int(qty)))
                    else:
                        # 递归处理嵌套结构
                        extract_items_from_dict(value)
                elif isinstance(value, list):
                    # 值是数组，遍历数组元素
                    for item in value:
                        extract_items_from_dict(item)
                elif isinstance(value, (int, float)):
                    # 结构: {"commodity_id": qty, ...}
                    items.append((int(key), None, int(value)))
        
        elif isinstance(car_ext, list):
            # 结构: [{"commodity_id": 1, "commodity_type": 6, "qty": 10}, ...]
            for item in car_ext:
                extract_items_from_dict(item)
        
        return items
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        print(f"⚠️ 解析 car_ext 失败: {e}, 内容: {car_ext_str[:200] if car_ext_str else 'None'}")
        return []


def aggregate_by_commodity_type(results, db):
    """
    统计每条记录中 car_ext 的数据，按 commodity_type 聚合 qty 之和
    
    Args:
        results: 查询结果列表
        db: 数据库连接对象
    
    Returns:
        list: 统计结果列表，每条记录包含 id, car_id, 各商品类型的 qty 之和
    """
    if not results:
        return []
    
    # 商品类型名称映射
    COMMODITY_TYPE_NAMES = {
        1: '盒菜',
        3: '调料',
        5: '饮料',
        6: '甜品'
    }
    
    # 第一步：解析所有 car_ext，收集所有商品ID和商品类型
    all_commodity_ids = set()
    record_items = []  # [(record_id, car_id, [(commodity_id, commodity_type, qty), ...]), ...]
    
    for record in results:
        record_id = record.get('id')
        car_id = record.get('car_id')
        car_ext = record.get('car_ext')
        items = parse_car_ext(car_ext)
        record_items.append((record_id, car_id, items))
        # 收集商品ID（用于查询缺失的商品类型）
        all_commodity_ids.update([item[0] for item in items if item[1] is None])
    
    # 第二步：批量查询缺失的商品类型（如果JSON中没有commodity_type字段）
    if all_commodity_ids:
        print(f"正在查询 {len(all_commodity_ids)} 个商品ID的商品类型...")
        commodity_type_map = get_commodity_types(db, list(all_commodity_ids))
    else:
        commodity_type_map = {}
    
    # 第三步：按 commodity_type 聚合统计
    aggregated_results = []
    
    for record_id, car_id, items in record_items:
        # 按 commodity_type 聚合
        type_qty_map = defaultdict(int)
        # 统计盒菜类型（commodity_type=1）且 qty>0 的不同 commodity_id
        box_meal_commodity_ids = set()
        
        for commodity_id, commodity_type, qty in items:
            # 优先使用JSON中的commodity_type，如果没有则从数据库查询
            if commodity_type is None:
                commodity_type = commodity_type_map.get(commodity_id)
            
            # 统计盒菜类型且 qty>0 的不同 commodity_id
            if commodity_type == 1 and qty > 0:
                box_meal_commodity_ids.add(commodity_id)
            
            if commodity_type is not None:
                type_qty_map[commodity_type] += qty
            else:
                # 如果找不到商品类型，记录为未知类型
                type_qty_map['unknown'] += qty
        
        # 构建结果记录
        result = {
            'id': record_id,
            'car_id': car_id,
            '盒菜种类数': len(box_meal_commodity_ids)  # 盒菜 qty>0 的不同 commodity_id 数量
        }
        
        # 添加各类型的数量，使用中文名称作为列名
        for commodity_type, qty_sum in sorted(type_qty_map.items()):
            if commodity_type in COMMODITY_TYPE_NAMES:
                type_name = COMMODITY_TYPE_NAMES[commodity_type]
                result[type_name] = qty_sum
            else:
                # 未知类型使用原值
                result[f'未知类型_{commodity_type}'] = qty_sum
        
        aggregated_results.append(result)
    
    return aggregated_results


def display_results(results, db):
    """
    显示查询结果并统计 car_ext 数据
    
    Args:
        results: 查询结果列表
        db: 数据库连接对象
    """
    if not results:
        print("未查询到任何记录。")
        return
    
    # 转换为 DataFrame 以便更好地显示
    df = pd.DataFrame(results)
    
    print("=" * 100)
    print(f"车辆回库记录详情 (共 {len(df)} 条)")
    print("=" * 100)
    
    # 统计 car_ext 数据
    print("\n正在解析和统计 car_ext 字段数据...")
    aggregated_results = aggregate_by_commodity_type(results, db)
    
    if aggregated_results:
        agg_df = pd.DataFrame(aggregated_results)
        
        # 调整列顺序，将 id 和 car_id 放在前面，然后是盒菜种类数，再是商品类型列（按固定顺序）
        cols = agg_df.columns.tolist()
        priority_cols = ['id', 'car_id', '盒菜种类数']
        commodity_type_cols = ['盒菜', '调料', '饮料', '甜品']  # 固定顺序
        # 将优先级列移到前面，然后是商品类型列，最后是其他列
        ordered_cols = [col for col in priority_cols if col in cols]
        ordered_cols.extend([col for col in commodity_type_cols if col in cols])
        ordered_cols.extend([col for col in cols if col not in priority_cols and col not in commodity_type_cols])
        agg_df = agg_df[ordered_cols]
        
        # 填充缺失值为0，确保显示整齐
        for col in commodity_type_cols:
            if col in agg_df.columns:
                agg_df[col] = agg_df[col].fillna(0).astype(int)
        
        print("\n" + "=" * 120)
        print("按 commodity_type 聚合统计结果")
        print("=" * 120)
        
        # 使用 to_markdown 格式化输出，更美观
        try:
            print(agg_df.to_markdown(index=False))
        except ImportError:
            # 如果没有安装 tabulate，使用默认格式但设置列宽
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', None)
            pd.set_option('display.colheader_justify', 'right')
            print(agg_df.to_string(index=False, justify='right'))
        
        # 保存聚合统计结果
        output_dir = os.path.dirname(os.path.abspath(__file__))
        date_str = datetime.now().strftime('%Y%m%d')
        agg_csv_path = os.path.join(output_dir, f'return_records_aggregated_{date_str}.csv')
        agg_df.to_csv(agg_csv_path, index=False, encoding='utf-8-sig')
        print(f"\n✅ 聚合统计结果已保存至: {agg_csv_path}")
    
    # 保存原始记录
    output_dir = os.path.dirname(os.path.abspath(__file__))
    date_str = datetime.now().strftime('%Y%m%d')
    csv_path = os.path.join(output_dir, f'return_records_{date_str}.csv')
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"✅ 原始记录已保存至: {csv_path}")


def main():
    """
    主函数
    """
    # 可以修改这些参数
    car_ids = [2, 14, 15]  # 可以是一个车辆ID或车辆ID列表
    task_type = 8
    days = 3  # 查询最近3天的数据
    
    results, db = get_recent_return_records(car_ids=car_ids, task_type=task_type, days=days)
    
    if results and db:
        display_results(results, db)
    elif not results:
        print("未查询到任何记录。")


if __name__ == "__main__":
    main()

