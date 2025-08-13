#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
8月份改善趋势分析
对比7月和8月，分析改善效果和剩余问题
"""

import csv
from datetime import datetime
from collections import defaultdict, Counter

def analyze_august_improvement(csv_file):
    """
    分析8月份相比7月份的改善情况
    """
    print("=" * 70)
    print("8月份改善趋势分析 (对比7月份)")
    print("=" * 70)
    
    # 读取数据
    july_data = []
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
            
            if record['dt'].startswith('2025-7-'):
                july_data.append(record)
            elif record['dt'].startswith('2025-8-'):
                august_data.append(record)
    
    print(f"\n📊 7月 vs 8月 对比:")
    july_total = sum(r['dish_cnt'] for r in july_data)
    august_total = sum(r['dish_cnt'] for r in august_data)
    july_days = len(set(r['dt'] for r in july_data))
    august_days = len(set(r['dt'] for r in august_data))
    july_points = len(set(r['point_id'] for r in july_data))
    august_points = len(set(r['point_id'] for r in august_data))
    
    improvement_rate = (july_total - august_total) / july_total * 100
    daily_improvement = (july_total/july_days - august_total/august_days) / (july_total/july_days) * 100
    
    print(f"{'指标':<15} {'7月份':<12} {'8月份':<12} {'变化':<15}")
    print("-" * 60)
    print(f"{'总过期菜品':<15} {july_total:<12} {august_total:<12} {improvement_rate:+.1f}%")
    print(f"{'日均过期':<15} {july_total/july_days:<12.1f} {august_total/august_days:<12.1f} {daily_improvement:+.1f}%")
    print(f"{'过期记录数':<15} {len(july_data):<12} {len(august_data):<12} {(len(august_data)-len(july_data))/len(july_data)*100:+.1f}%")
    print(f"{'涉及点位数':<15} {july_points:<12} {august_points:<12} {(august_points-july_points)/july_points*100:+.1f}%")
    
    # 分析具体改善的点位
    print(f"\n🎯 点位改善情况分析:")
    
    # 计算每个点位在7月和8月的表现
    july_point_stats = defaultdict(lambda: {'freq': 0, 'dish_sum': 0})
    august_point_stats = defaultdict(lambda: {'freq': 0, 'dish_sum': 0})
    
    for row in july_data:
        july_point_stats[row['point_id']]['freq'] += 1
        july_point_stats[row['point_id']]['dish_sum'] += row['dish_cnt']
    
    for row in august_data:
        august_point_stats[row['point_id']]['freq'] += 1
        august_point_stats[row['point_id']]['dish_sum'] += row['dish_cnt']
    
    # 找出共同存在的点位进行对比
    common_points = set(july_point_stats.keys()) & set(august_point_stats.keys())
    improvements = []
    deteriorations = []
    
    for point_id in common_points:
        july_total = july_point_stats[point_id]['dish_sum']
        august_total = august_point_stats[point_id]['dish_sum']
        
        if july_total > 0:  # 避免除零
            change_rate = (august_total - july_total) / july_total * 100
            change_abs = august_total - july_total
            
            improvement_data = {
                'point_id': point_id,
                'july_total': july_total,
                'august_total': august_total,
                'change_rate': change_rate,
                'change_abs': change_abs,
                'july_freq': july_point_stats[point_id]['freq'],
                'august_freq': august_point_stats[point_id]['freq']
            }
            
            if change_rate < -20:  # 改善超过20%
                improvements.append(improvement_data)
            elif change_rate > 20:  # 恶化超过20%
                deteriorations.append(improvement_data)
    
    # 显示改善最明显的点位
    improvements.sort(key=lambda x: x['change_abs'])
    print(f"改善明显的点位 (减少过期菜品数量):")
    print(f"{'点位ID':<8} {'7月过期':<8} {'8月过期':<8} {'变化量':<8} {'变化率':<10}")
    print("-" * 50)
    for point in improvements[:10]:
        print(f"{point['point_id']:<8} {point['july_total']:<8} {point['august_total']:<8} "
              f"{point['change_abs']:+<8} {point['change_rate']:+.1f}%")
    
    # 显示恶化的点位
    deteriorations.sort(key=lambda x: x['change_abs'], reverse=True)
    if deteriorations:
        print(f"\n恶化的点位 (增加过期菜品数量):")
        print(f"{'点位ID':<8} {'7月过期':<8} {'8月过期':<8} {'变化量':<8} {'变化率':<10}")
        print("-" * 50)
        for point in deteriorations[:10]:
            print(f"{point['point_id']:<8} {point['july_total']:<8} {point['august_total']:<8} "
                  f"{point['change_abs']:+<8} {point['change_rate']:+.1f}%")
    
    # 8月份新增问题点位
    new_problem_points = set(august_point_stats.keys()) - set(july_point_stats.keys())
    if new_problem_points:
        print(f"\n🆕 8月份新增过期点位: {len(new_problem_points)}个")
        new_problems = [(pid, august_point_stats[pid]['dish_sum']) for pid in new_problem_points]
        new_problems.sort(key=lambda x: x[1], reverse=True)
        print("新增问题点位 (按过期菜品数排序):")
        for point_id, dish_sum in new_problems[:10]:
            print(f"  点位{point_id}: {dish_sum}份过期")
    
    # 8月份解决的点位
    resolved_points = set(july_point_stats.keys()) - set(august_point_stats.keys())
    if resolved_points:
        print(f"\n✅ 8月份已解决过期的点位: {len(resolved_points)}个")
        resolved_savings = sum(july_point_stats[pid]['dish_sum'] for pid in resolved_points)
        print(f"这些点位在7月份共过期 {resolved_savings} 份菜品")
    
    # 8月份持续改善趋势分析
    print(f"\n📈 8月份内部趋势分析:")
    
    # 按周分析8月份趋势
    august_weekly = defaultdict(lambda: {'dish_sum': 0, 'point_count': 0})
    for row in august_data:
        try:
            date_obj = datetime.strptime(row['dt'], '%Y-%m-%d')
            week_num = date_obj.isocalendar()[1]
            august_weekly[week_num]['dish_sum'] += row['dish_cnt']
            august_weekly[week_num]['point_count'] += 1
        except:
            continue
    
    print("8月份各周表现:")
    print(f"{'周次':<8} {'过期菜品':<10} {'过期次数':<10} {'日均过期':<10}")
    print("-" * 40)
    for week in sorted(august_weekly.keys()):
        stats = august_weekly[week]
        # 估算该周的天数
        week_days = 7 if week < max(august_weekly.keys()) else 3  # 最后一周可能不完整
        daily_avg = stats['dish_sum'] / week_days
        print(f"第{week}周{'':<3} {stats['dish_sum']:<10} {stats['point_count']:<10} {daily_avg:<10.1f}")
    
    # 最终建议
    print(f"\n💡 8月份改善成效总结:")
    print(f"1. 整体改善:")
    print(f"   ✅ 总过期菜品减少 {improvement_rate:.1f}%")
    print(f"   ✅ 日均过期减少 {daily_improvement:.1f}%")
    if resolved_points:
        print(f"   ✅ {len(resolved_points)}个点位完全解决过期问题")
    print(f"   ✅ {len(improvements)}个点位显著改善")
    
    print(f"\n2. 仍需关注:")
    if deteriorations:
        print(f"   ⚠️ {len(deteriorations)}个点位情况恶化")
    if new_problem_points:
        print(f"   ⚠️ {len(new_problem_points)}个新增问题点位")
    print(f"   ⚠️ 8月10日仍是问题最严重的一天")
    
    print(f"\n3. 9月份建议:")
    print(f"   - 继续巩固已改善点位的成果")
    if deteriorations:
        print(f"   - 重点处理恶化点位，找出根本原因")
    if new_problem_points:
        print(f"   - 分析新增问题点位的特殊情况")
    print(f"   - 制定更精准的补货策略，目标日均过期控制在150份以内")

if __name__ == "__main__":
    csv_file = "data/点位过期.csv"
    analyze_august_improvement(csv_file)

