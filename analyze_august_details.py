#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
8月份点位过期数据详细分析脚本
深入分析8月份的过期趋势、模式和改进机会
"""

import csv
from datetime import datetime
from collections import defaultdict, Counter

def analyze_august_details(csv_file):
    """
    详细分析8月份的点位过期数据
    
    Args:
        csv_file: CSV文件路径
    """
    print("=" * 70)
    print("8月份点位过期数据详细分析报告")
    print("=" * 70)
    
    # 读取数据
    data = []
    august_data = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            record = {
                'dt': row['dt'],
                'point_id': int(row['point_id']),
                'point_size': int(row['point_size']),
                'dish_cnt': int(row['dish_cnt'])
            }
            data.append(record)
            # 筛选8月份数据
            if record['dt'].startswith('2025-8-'):
                august_data.append(record)
    
    print(f"\n📊 8月份数据概览:")
    print(f"8月份记录数: {len(august_data)} (占总数据的 {len(august_data)/len(data)*100:.1f}%)")
    print(f"8月份涉及点位: {len(set(r['point_id'] for r in august_data))}个")
    print(f"8月份总过期菜品: {sum(r['dish_cnt'] for r in august_data)}份")
    
    # 按日期详细分析
    print(f"\n📅 8月份逐日过期分析:")
    daily_stats = defaultdict(lambda: {
        'point_count': 0, 
        'dish_sum': 0, 
        'points': set(), 
        'max_single': 0,
        'records': []
    })
    
    for row in august_data:
        date = row['dt']
        daily_stats[date]['point_count'] += 1
        daily_stats[date]['dish_sum'] += row['dish_cnt']
        daily_stats[date]['points'].add(row['point_id'])
        daily_stats[date]['max_single'] = max(daily_stats[date]['max_single'], row['dish_cnt'])
        daily_stats[date]['records'].append(row)
    
    # 按日期排序显示
    sorted_dates = sorted(daily_stats.keys())
    print(f"{'日期':<12} {'过期次数':<8} {'点位数':<8} {'总菜品':<8} {'单次最高':<8} {'日均每点位':<10}")
    print("-" * 65)
    
    for date in sorted_dates:
        stats = daily_stats[date]
        unique_points = len(stats['points'])
        avg_per_point = stats['dish_sum'] / unique_points if unique_points > 0 else 0
        print(f"{date:<12} {stats['point_count']:<8} {unique_points:<8} {stats['dish_sum']:<8} {stats['max_single']:<8} {avg_per_point:<10.1f}")
    
    # 8月份点位风险分析
    print(f"\n⚠️ 8月份高风险点位详细分析:")
    august_point_stats = defaultdict(lambda: {
        'freq': 0, 
        'dish_sum': 0, 
        'dates': [],
        'dish_counts': [],
        'point_size': 0
    })
    
    for row in august_data:
        point_id = row['point_id']
        august_point_stats[point_id]['freq'] += 1
        august_point_stats[point_id]['dish_sum'] += row['dish_cnt']
        august_point_stats[point_id]['dates'].append(row['dt'])
        august_point_stats[point_id]['dish_counts'].append(row['dish_cnt'])
        august_point_stats[point_id]['point_size'] = row['point_size']
    
    # 找出8月份高风险点位
    august_high_risk = []
    for point_id, stats in august_point_stats.items():
        avg_dish = stats['dish_sum'] / stats['freq']
        max_dish = max(stats['dish_counts'])
        min_dish = min(stats['dish_counts'])
        
        # 8月份高风险标准：频次≥3次 或 总过期≥30份
        if stats['freq'] >= 3 or stats['dish_sum'] >= 30:
            august_high_risk.append({
                'point_id': point_id,
                'point_size': stats['point_size'],
                'freq': stats['freq'],
                'dish_sum': stats['dish_sum'],
                'avg_dish': avg_dish,
                'max_dish': max_dish,
                'min_dish': min_dish,
                'dates': stats['dates']
            })
    
    # 按总过期菜品排序
    august_high_risk.sort(key=lambda x: x['dish_sum'], reverse=True)
    
    print(f"8月份高风险点位数量: {len(august_high_risk)}")
    print(f"{'点位ID':<8} {'规模':<4} {'频次':<4} {'总菜品':<6} {'均值':<6} {'最高':<4} {'最低':<4} {'首次日期':<10}")
    print("-" * 60)
    
    for point in august_high_risk[:15]:  # 显示前15个
        first_date = min(point['dates'])
        print(f"{point['point_id']:<8} {point['point_size']:<4} {point['freq']:<4} "
              f"{point['dish_sum']:<6} {point['avg_dish']:<6.1f} {point['max_dish']:<4} "
              f"{point['min_dish']:<4} {first_date:<10}")
    
    # 8月份异常情况分析
    print(f"\n🚨 8月份异常情况详细分析:")
    
    # 单日大量过期
    august_high_waste = [row for row in august_data if row['dish_cnt'] >= 20]
    if august_high_waste:
        print(f"8月份单次过期≥20份的情况: {len(august_high_waste)}次")
        august_high_waste.sort(key=lambda x: x['dish_cnt'], reverse=True)
        print("详细情况:")
        for row in august_high_waste:
            size_name = {0: '小型', 1: '小型', 2: '中型', 3: '大型'}[row['point_size']]
            print(f"  {row['dt']} - 点位{row['point_id']} ({size_name}): {row['dish_cnt']}份")
    
    # 小型点位异常
    august_small_high = [row for row in august_data if row['point_size'] <= 1 and row['dish_cnt'] >= 8]
    if august_small_high:
        print(f"\n8月份小型点位过期≥8份的异常: {len(august_small_high)}次")
        for row in august_small_high:
            print(f"  {row['dt']} - 点位{row['point_id']}: {row['dish_cnt']}份")
    
    # 连续过期分析
    print(f"\n📈 8月份连续过期模式分析:")
    
    # 统计每个点位的过期日期，查找连续过期
    consecutive_patterns = []
    for point_id, stats in august_point_stats.items():
        if stats['freq'] >= 3:  # 至少过期3次才分析连续性
            dates = sorted(stats['dates'])
            date_objects = []
            for date_str in dates:
                try:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    date_objects.append(date_obj)
                except:
                    continue
            
            # 查找连续日期
            consecutive_count = 1
            max_consecutive = 1
            for i in range(1, len(date_objects)):
                if (date_objects[i] - date_objects[i-1]).days <= 2:  # 2天内算连续
                    consecutive_count += 1
                    max_consecutive = max(max_consecutive, consecutive_count)
                else:
                    consecutive_count = 1
            
            if max_consecutive >= 3:  # 连续3次以上
                consecutive_patterns.append({
                    'point_id': point_id,
                    'point_size': stats['point_size'],
                    'max_consecutive': max_consecutive,
                    'total_freq': stats['freq'],
                    'total_dish': stats['dish_sum']
                })
    
    if consecutive_patterns:
        consecutive_patterns.sort(key=lambda x: x['max_consecutive'], reverse=True)
        print(f"发现 {len(consecutive_patterns)} 个点位存在连续过期模式:")
        print(f"{'点位ID':<8} {'规模':<4} {'最长连续':<8} {'总频次':<6} {'总菜品':<6}")
        print("-" * 35)
        for pattern in consecutive_patterns:
            print(f"{pattern['point_id']:<8} {pattern['point_size']:<4} "
                  f"{pattern['max_consecutive']:<8} {pattern['total_freq']:<6} {pattern['total_dish']:<6}")
    
    # 8月份改善趋势分析
    print(f"\n📊 8月份趋势分析:")
    
    # 按周分析
    weekly_stats = defaultdict(lambda: {'point_count': 0, 'dish_sum': 0, 'dates': []})
    for row in august_data:
        try:
            date_obj = datetime.strptime(row['dt'], '%Y-%m-%d')
            week_num = date_obj.isocalendar()[1]  # ISO周数
            week_key = f"第{week_num}周"
            weekly_stats[week_key]['point_count'] += 1
            weekly_stats[week_key]['dish_sum'] += row['dish_cnt']
            weekly_stats[week_key]['dates'].append(row['dt'])
        except:
            continue
    
    print("8月份按周统计:")
    print(f"{'周次':<8} {'过期次数':<8} {'过期菜品':<8} {'日均过期':<8}")
    print("-" * 35)
    for week in sorted(weekly_stats.keys()):
        stats = weekly_stats[week]
        unique_dates = len(set(stats['dates']))
        daily_avg = stats['dish_sum'] / unique_dates if unique_dates > 0 else 0
        print(f"{week:<8} {stats['point_count']:<8} {stats['dish_sum']:<8} {daily_avg:<8.1f}")
    
    # 8月份业务洞察
    print(f"\n💡 8月份专项业务洞察:")
    
    august_total_waste = sum(r['dish_cnt'] for r in august_data)
    august_daily_avg = august_total_waste / len(set(r['dt'] for r in august_data))
    worst_august_day = max(daily_stats.keys(), key=lambda x: daily_stats[x]['dish_sum'])
    worst_august_waste = daily_stats[worst_august_day]['dish_sum']
    
    print(f"1. 8月份整体表现:")
    print(f"   - 8月份总过期: {august_total_waste}份")
    print(f"   - 8月份日均过期: {august_daily_avg:.1f}份")
    print(f"   - 8月份最严重日期: {worst_august_day} ({worst_august_waste}份)")
    print(f"   - 8月份高风险点位: {len(august_high_risk)}个")
    
    if consecutive_patterns:
        print(f"   - 存在连续过期模式的点位: {len(consecutive_patterns)}个")
    
    print(f"\n2. 8月份关键问题:")
    if august_high_waste:
        print(f"   - 单次大量过期事件: {len(august_high_waste)}次，需重点关注")
    
    top_problem_point = august_high_risk[0] if august_high_risk else None
    if top_problem_point:
        print(f"   - 最严重点位: 点位{top_problem_point['point_id']} "
              f"({top_problem_point['freq']}次过期，{top_problem_point['dish_sum']}份)")
    
    print(f"\n3. 8月份改进建议:")
    print(f"   - 重点监控前10个高风险点位的补货策略")
    print(f"   - 对连续过期点位实施紧急干预措施")
    print(f"   - 分析8月份过期模式，制定9月份预防策略")
    
    if august_small_high:
        print(f"   - 核查小型点位异常过期的原因")

if __name__ == "__main__":
    csv_file = "data/点位过期.csv"
    analyze_august_details(csv_file)

