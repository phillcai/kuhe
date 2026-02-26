#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断虚拟车数据 - 分析 req_car_id 月度分布
用于排查为何 1 月份开始虚拟车没有数据
"""

import sys
import os
from datetime import datetime

# 添加 code 目录到 Python 路径
code_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../code'))
sys.path.insert(0, code_dir)

from lib import create_db_connection


def diagnose_req_car_id_by_month():
    """
    按月统计 req_car_id 分布，找出虚拟车数据何时消失
    """
    print("正在连接数据库 (smart_cooker_sg)...")
    db = create_db_connection(mysql_database='smart_cooker_sg')

    # 正常车的 req_car_id
    NORMAL_CAR_IDS = [2, 14, 15]

    print("\n" + "=" * 80)
    print("【诊断】分拣日志 req_car_id 月度分布（最近 180 天）")
    print("=" * 80)

    sql = """
        SELECT
          DATE_FORMAT(a.create_time, '%Y-%m') AS 月份,
          a.req_car_id,
          COUNT(*) AS 记录数
        FROM point_commodity_fenjian_log a
        WHERE a.status = 1
          AND a.req_task_id != 0
          AND a.create_time >= DATE_SUB(CURDATE(), INTERVAL 180 DAY)
        GROUP BY DATE_FORMAT(a.create_time, '%Y-%m'), a.req_car_id
        ORDER BY 月份 DESC, 记录数 DESC
    """

    results = db.execute_query(sql)

    if not results:
        print("未查询到任何数据")
        return

    # 按月份分组展示
    current_month = None
    month_virtual_count = 0
    month_normal_count = 0
    month_total = 0

    for row in results:
        month = row['月份']
        req_car_id = row['req_car_id']
        count = row['记录数']

        if month != current_month:
            if current_month:
                print(f"\n  └─ 虚拟车: {month_virtual_count} 条 | 正常车: {month_normal_count} 条")
            current_month = month
            month_virtual_count = 0
            month_normal_count = 0
            month_total = 0
            print(f"\n📅 {month}:")

        car_type = "正常车" if req_car_id in NORMAL_CAR_IDS else "虚拟车"
        if req_car_id in NORMAL_CAR_IDS:
            month_normal_count += count
        else:
            month_virtual_count += count
        month_total += count

        marker = "  ●" if req_car_id in NORMAL_CAR_IDS else "  ○"
        print(f"  {marker} req_car_id={req_car_id} ({car_type}): {count:,} 条")

    if current_month:
        print(f"\n  └─ 虚拟车: {month_virtual_count} 条 | 正常车: {month_normal_count} 条")

    print("\n" + "=" * 80)
    print("图例: ● 正常车 (req_car_id: 2, 14, 15) | ○ 虚拟车 (其他 req_car_id)")
    print("=" * 80)


def check_central_kitchen_car():
    """
    检查 central_kitchen_car 表中车辆定义
    """
    print("\n" + "=" * 80)
    print("【参考】central_kitchen_car 车辆表")
    print("=" * 80)

    db = create_db_connection(mysql_database='smart_cooker_sg')

    sql = """
        SELECT id, car_no, state, create_time, update_time
        FROM central_kitchen_car
        ORDER BY id
    """
    try:
        results = db.execute_query(sql)
        if results:
            for row in results:
                print(f"  id={row.get('id')} car_no={row.get('car_no')} state={row.get('state')}")
        else:
            print("  (表可能不存在或为空)")
    except Exception as e:
        print(f"  查询失败: {e}")

    print("=" * 80)


def main():
    """
    主函数
    """
    print("\n🔍 虚拟车数据诊断工具")
    diagnose_req_car_id_by_month()
    check_central_kitchen_car()
    print("\n✅ 诊断完成\n")


if __name__ == '__main__':
    main()
