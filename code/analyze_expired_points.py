#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
点位过期数据分析脚本
分析点位过期菜品的分布特征、时间趋势和业务洞察
"""

import csv
from datetime import datetime
from collections import defaultdict, Counter

def analyze_expired_points_data(csv_file):
    """
    分析点位过期数据
    
    Args:
        csv_file: CSV文件路径
    """
    print("=" * 60)
    print("点位过期数据分析报告")
    print("=" * 60)
    
    # 读取数据
    data = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append({
                'dt': row['dt'],
                'point_id': int(row['point_id']),
                'point_size': int(row['point_size']),
                'dish_cnt': int(row['dish_cnt'])
            })
    
    # 基本数据概览
    dates = [row['dt'] for row in data]
    point_ids = [row['point_id'] for row in data]
    dish_counts = [row['dish_cnt'] for row in data]
    
    print("\n📊 数据概览:")
    print(f"总记录数: {len(data)}")
    print(f"时间范围: {min(dates)} 到 {max(dates)}")
    print(f"涉及点位数量: {len(set(point_ids))}")
    print(f"总过期菜品数: {sum(dish_counts)}")
    
    # 按日期统计
    print("\n📅 按日期统计过期情况:")
    daily_stats = defaultdict(lambda: {'point_count': 0, 'dish_sum': 0})
    for row in data:
        daily_stats[row['dt']]['point_count'] += 1
        daily_stats[row['dt']]['dish_sum'] += row['dish_cnt']
    
    # 按日期排序，显示最近10天
    sorted_dates = sorted(daily_stats.keys(), reverse=True)[:10]
    print(f"{'日期':<12} {'过期点位数':<10} {'过期菜品数':<10}")
    print("-" * 35)
    for date in sorted_dates:
        stats = daily_stats[date]
        print(f"{date:<12} {stats['point_count']:<10} {stats['dish_sum']:<10}")
    
    # 点位规模分析
    print("\n🏪 点位规模分析:")
    size_mapping = {0: '小型', 1: '小型', 2: '中型', 3: '大型'}
    size_stats = defaultdict(lambda: {'count': 0, 'dish_sum': 0, 'dish_list': []})
    
    for row in data:
        size_name = size_mapping[row['point_size']]
        size_stats[size_name]['count'] += 1
        size_stats[size_name]['dish_sum'] += row['dish_cnt']
        size_stats[size_name]['dish_list'].append(row['dish_cnt'])
    
    print(f"{'规模':<6} {'过期次数':<8} {'总过期菜品':<10} {'平均过期菜品':<10}")
    print("-" * 40)
    for size_name in ['小型', '中型', '大型']:
        if size_name in size_stats:
            stats = size_stats[size_name]
            avg_dish = stats['dish_sum'] / stats['count'] if stats['count'] > 0 else 0
            print(f"{size_name:<6} {stats['count']:<8} {stats['dish_sum']:<10} {avg_dish:<10.2f}")
    
    # 高风险点位分析
    print("\n⚠️ 高风险点位分析:")
    point_risk = defaultdict(lambda: {'freq': 0, 'dish_sum': 0, 'dish_list': []})
    
    for row in data:
        point_id = row['point_id']
        point_risk[point_id]['freq'] += 1
        point_risk[point_id]['dish_sum'] += row['dish_cnt']
        point_risk[point_id]['dish_list'].append(row['dish_cnt'])
    
    # 计算平均值并找出高风险点位
    high_risk_points = []
    for point_id, stats in point_risk.items():
        avg_dish = stats['dish_sum'] / stats['freq']
        if stats['freq'] >= 5 or stats['dish_sum'] >= 50:
            high_risk_points.append({
                'point_id': point_id,
                'freq': stats['freq'],
                'dish_sum': stats['dish_sum'],
                'avg_dish': avg_dish
            })
    
    # 按总过期菜品排序
    high_risk_points.sort(key=lambda x: x['dish_sum'], reverse=True)
    
    print(f"高风险点位数量: {len(high_risk_points)}")
    print("前10个高风险点位:")
    print(f"{'点位ID':<8} {'过期频次':<8} {'总过期菜品':<10} {'平均过期菜品':<10}")
    print("-" * 42)
    for point in high_risk_points[:10]:
        print(f"{point['point_id']:<8} {point['freq']:<8} {point['dish_sum']:<10} {point['avg_dish']:<10.2f}")
    
    # 过期菜品数量分布
    print("\n🍽️ 过期菜品数量分布:")
    dish_distribution = Counter(dish_counts)
    sorted_distribution = sorted(dish_distribution.items())
    print("过期菜品数量分布（前15项）:")
    total_records = len(data)
    for count, freq in sorted_distribution[:15]:
        print(f"  {count}份: {freq}次 ({freq/total_records*100:.1f}%)")
    
    # 异常情况分析
    print("\n🚨 异常情况分析:")
    
    # 大量过期的情况
    high_waste = [row for row in data if row['dish_cnt'] >= 30]
    if len(high_waste) > 0:
        print(f"单次过期≥30份的情况: {len(high_waste)}次")
        print("详情:")
        for row in high_waste:
            print(f"  {row['dt']} - 点位{row['point_id']} (规模{row['point_size']}): {row['dish_cnt']}份")
    
    # 小型点位大量过期
    small_high_waste = [row for row in data if row['point_size'] <= 1 and row['dish_cnt'] >= 10]
    if len(small_high_waste) > 0:
        print(f"\n小型点位(规模≤1)过期≥10份的异常情况: {len(small_high_waste)}次")
        for row in small_high_waste:
            print(f"  {row['dt']} - 点位{row['point_id']}: {row['dish_cnt']}份")
    
    # 时间趋势分析
    print("\n📈 时间趋势分析:")
    
    # 按周统计 - 简化版本，按月统计
    month_stats = defaultdict(lambda: {'point_count': 0, 'dish_sum': 0})
    for row in data:
        # 提取月份 (假设格式为 YYYY-M-DD)
        month = row['dt'][:7]  # 取前7位 YYYY-M 或 YYYY-MM
        month_stats[month]['point_count'] += 1
        month_stats[month]['dish_sum'] += row['dish_cnt']
    
    print("按月统计过期情况:")
    print(f"{'月份':<10} {'过期点位数':<10} {'过期菜品数':<10}")
    print("-" * 35)
    for month in sorted(month_stats.keys()):
        stats = month_stats[month]
        print(f"{month:<10} {stats['point_count']:<10} {stats['dish_sum']:<10}")
    
    # 周内分布 - 简化版本，通过日期推算星期几
    from datetime import datetime
    weekday_stats = defaultdict(lambda: {'point_count': 0, 'dish_sum': 0})
    weekday_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    
    for row in data:
        try:
            # 解析日期
            date_obj = datetime.strptime(row['dt'], '%Y-%m-%d')
            weekday = date_obj.weekday()  # 0=周一, 6=周日
            weekday_name = weekday_names[weekday]
            weekday_stats[weekday_name]['point_count'] += 1
            weekday_stats[weekday_name]['dish_sum'] += row['dish_cnt']
        except:
            continue
    
    print("\n一周内过期分布:")
    print(f"{'星期':<6} {'过期点位数':<10} {'过期菜品数':<10}")
    print("-" * 30)
    for weekday_name in weekday_names:
        if weekday_name in weekday_stats:
            stats = weekday_stats[weekday_name]
            print(f"{weekday_name:<6} {stats['point_count']:<10} {stats['dish_sum']:<10}")
    
    # 业务洞察
    print("\n💡 业务洞察与建议:")
    
    total_waste = sum(dish_counts)
    avg_daily_waste = sum(stats['dish_sum'] for stats in daily_stats.values()) / len(daily_stats)
    
    # 找出最严重的日期
    worst_day = max(daily_stats.keys(), key=lambda x: daily_stats[x]['dish_sum'])
    worst_day_waste = daily_stats[worst_day]['dish_sum']
    
    print(f"1. 总体情况:")
    print(f"   - 总过期菜品: {total_waste}份")
    print(f"   - 日均过期: {avg_daily_waste:.1f}份")
    print(f"   - 最严重日期: {worst_day} ({worst_day_waste}份)")
    
    total_points = len(set(point_ids))
    print(f"\n2. 点位风险分级:")
    print(f"   - 高风险点位: {len(high_risk_points)}个 (占比{len(high_risk_points)/total_points*100:.1f}%)")
    print(f"   - 需重点关注大型点位的补货策略")
    
    frequent_expired = [p for p in high_risk_points if p['freq'] >= 10]
    if len(frequent_expired) > 0:
        print(f"   - 频繁过期点位(≥10次): {len(frequent_expired)}个")
    
    print(f"\n3. 改进建议:")
    print(f"   - 对高风险点位实施更精准的需求预测")
    print(f"   - 优化大型点位的补货频次和数量")
    print(f"   - 建立过期预警机制，提前处理临期商品")
    
    if len(small_high_waste) > 0:
        print(f"   - 检查小型点位异常过期情况，可能存在数据错误或特殊情况")

if __name__ == "__main__":
    csv_file = "data/点位过期.csv"
    analyze_expired_points_data(csv_file)
