#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分拣批次时效分析

统计近7天（默认，不含今天）或指定日期区间内，每天分拣任务中各批次餐食的时效分布。

CK 在当日 16:00 生产完成当天批次，预期次日 16:00 前完成分拣。
按实际分拣时间与预期截止时间的差距，将每份餐食分为：
  - 周期内：分拣时间 ≤ 批次日 + 1天 + 16小时
  - 晚1天：超出截止时间 0~24 小时
  - 晚2天：超出截止时间 24~48 小时
  - 更久：超出截止时间超过 48 小时
  - 批次缺失：production_date 为空或格式异常

用法:
    python analyze_picking_timeliness.py                      # 近7天不含今天
    python analyze_picking_timeliness.py 2026-03-01 2026-03-06  # 指定区间（左闭右闭）
"""

import sys
import os
import json
import argparse
import pandas as pd
from datetime import datetime, timedelta

# 引入项目公共库
sys.path.append(os.path.join(os.path.dirname(__file__), '../../code'))
from lib import create_db_connection

# 时效分类顺序
TIMELINESS_LABELS = ['周期内', '晚1天', '晚2天', '更久', '批次缺失']


def parse_args():
    """解析命令行参数，返回 (start_date, end_date)"""
    parser = argparse.ArgumentParser(
        description='分拣批次时效分析',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例:
  python analyze_picking_timeliness.py
  python analyze_picking_timeliness.py 2026-03-01 2026-03-06"""
    )
    parser.add_argument(
        'start_date',
        nargs='?',
        help='起始日期，格式 YYYY-MM-DD（默认: 7天前）'
    )
    parser.add_argument(
        'end_date',
        nargs='?',
        help='结束日期，格式 YYYY-MM-DD（默认: 昨天）'
    )
    args = parser.parse_args()

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    if args.start_date is None and args.end_date is None:
        # 默认近7天不含今天
        start = today - timedelta(days=7)
        end = today - timedelta(days=1)
    elif args.start_date is not None and args.end_date is not None:
        try:
            start = datetime.strptime(args.start_date, '%Y-%m-%d')
        except ValueError:
            print(f"错误: 起始日期格式不正确 '{args.start_date}'，应为 YYYY-MM-DD", file=sys.stderr)
            sys.exit(1)
        try:
            end = datetime.strptime(args.end_date, '%Y-%m-%d')
        except ValueError:
            print(f"错误: 结束日期格式不正确 '{args.end_date}'，应为 YYYY-MM-DD", file=sys.stderr)
            sys.exit(1)
        if start > end:
            print(f"错误: 起始日期 {args.start_date} 不能晚于结束日期 {args.end_date}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.error('请同时提供起始日期和结束日期，或都不提供')

    return start, end


def get_timeliness_label(picking_time: datetime, production_date_str: str) -> str:
    """
    计算时效分类。

    截止时间 = production_date + 1天 + 16小时（即次日 16:00）
    - picking_time ≤ cutoff          → 周期内
    - cutoff < t ≤ cutoff + 24h      → 晚1天
    - cutoff + 24h < t ≤ cutoff + 48h → 晚2天
    - t > cutoff + 48h               → 更久
    - 无法解析                        → 批次缺失
    """
    pd_str = production_date_str.strip()
    if not pd_str or len(pd_str) != 8:
        return '批次缺失'
    try:
        prod_date = datetime.strptime(pd_str, '%Y%m%d')
    except ValueError:
        return '批次缺失'

    cutoff = prod_date + timedelta(days=1, hours=16)

    if picking_time <= cutoff:
        return '周期内'
    elif picking_time <= cutoff + timedelta(days=1):
        return '晚1天'
    elif picking_time <= cutoff + timedelta(days=2):
        return '晚2天'
    else:
        return '更久'


def fetch_tasks(start_date: datetime, end_date: datetime) -> list:
    """从数据库查询指定日期区间的分拣任务（不含取消任务）"""
    db = create_db_connection(mysql_database='smart_cooker_sg')

    sql = """
    SELECT
        id,
        picking_no,
        car_type,
        shift_number,
        update_time,
        frame_inventory_info
    FROM central_kitchen_picking_task
    WHERE DATE(update_time) >= %s
      AND DATE(update_time) <= %s
      AND (canceled_at IS NULL OR canceled_at = '0000-00-00 00:00:00')
      AND frame_inventory_info IS NOT NULL
      AND frame_inventory_info != ''
    ORDER BY update_time
    """

    print("正在连接数据库并查询...")
    with db.connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, (start_date.date(), end_date.date()))
            rows = cursor.fetchall()

    print(f"共查询到 {len(rows)} 条分拣任务")
    return rows


def build_records(rows: list) -> pd.DataFrame:
    """
    解析每条任务的 frame_inventory_info，
    将 production_date 逗号展开为逐份记录。
    """
    records = []
    for row in rows:
        picking_time = row['update_time']
        if isinstance(picking_time, str):
            picking_time = datetime.fromisoformat(picking_time)

        picking_date = picking_time.date()

        try:
            fii = json.loads(row['frame_inventory_info'])
        except (json.JSONDecodeError, TypeError):
            continue

        for shelf in fii:
            # qty=0 是空格子，没有实际货物，跳过
            if shelf.get('qty', 0) == 0:
                continue

            commodity_id = shelf.get('commodity_id')
            prod_dates_raw = shelf.get('production_date', '')
            prod_dates = prod_dates_raw.split(',') if prod_dates_raw else ['']

            for pd_str in prod_dates:
                label = get_timeliness_label(picking_time, pd_str.strip())
                records.append({
                    'picking_date': picking_date,
                    'picking_no': row['picking_no'],
                    'commodity_id': commodity_id,
                    'production_date': pd_str.strip(),
                    'timeliness': label,
                })

    return pd.DataFrame(records)


def print_daily_summary(df: pd.DataFrame):
    """按分拣日期打印时效分布表格（份数 + 占比）"""
    print()
    print("=" * 90)
    print("按分拣日期统计时效分布")
    print("=" * 90)

    # 统计份数
    pivot = df.groupby(['picking_date', 'timeliness']).size().unstack(fill_value=0)
    for col in TIMELINESS_LABELS:
        if col not in pivot.columns:
            pivot[col] = 0
    pivot = pivot[TIMELINESS_LABELS]
    pivot['合计'] = pivot.sum(axis=1)

    # 打印表头
    header = f"{'日期':>12}  {'合计':>6}"
    for label in TIMELINESS_LABELS:
        header += f"  {label:>8} {'占比':>6}"
    print(header)
    print("-" * 90)

    # 打印每天数据
    for date, row in pivot.iterrows():
        total = row['合计']
        line = f"{str(date):>12}  {int(total):>6}"
        for label in TIMELINESS_LABELS:
            cnt = int(row[label])
            pct = cnt / total * 100 if total > 0 else 0.0
            line += f"  {cnt:>8} {pct:>5.1f}%"
        print(line)

    print("-" * 90)

    # 合计行
    totals = pivot.sum()
    grand = int(totals['合计'])
    line = f"{'合计':>12}  {grand:>6}"
    for label in TIMELINESS_LABELS:
        cnt = int(totals[label])
        pct = cnt / grand * 100 if grand > 0 else 0.0
        line += f"  {cnt:>8} {pct:>5.1f}%"
    print(line)
    print()

    return pivot


def print_overall_summary(df: pd.DataFrame):
    """打印整体汇总"""
    print("=" * 50)
    print("整体时效汇总")
    print("=" * 50)
    grand_total = len(df)
    for label in TIMELINESS_LABELS:
        cnt = (df['timeliness'] == label).sum()
        pct = cnt / grand_total * 100 if grand_total > 0 else 0.0
        bar = '█' * int(pct / 2)
        print(f"  {label:6s}: {cnt:6d} 份 ({pct:5.1f}%) {bar}")
    print(f"  {'合计':6s}: {grand_total:6d} 份")
    print()


def save_csv(df: pd.DataFrame, pivot: pd.DataFrame, output_dir: str):
    """保存明细和汇总 CSV"""
    detail_path = os.path.join(output_dir, '分拣时效明细.csv')
    summary_path = os.path.join(output_dir, '按日时效汇总.csv')

    df.to_csv(detail_path, index=False, encoding='utf-8-sig')

    # 汇总表：将份数和占比合并为可读格式（pivot 已含 '合计' 列）
    summary = pivot.reset_index().copy()
    for label in TIMELINESS_LABELS:
        pct_col = f'{label}占比%'
        summary[pct_col] = (summary[label] / summary['合计'] * 100).round(1)
        summary[pct_col] = summary[pct_col].fillna(0)
    summary.to_csv(summary_path, index=False, encoding='utf-8-sig')

    print(f"已保存: {detail_path}")
    print(f"已保存: {summary_path}")


def main():
    start_date, end_date = parse_args()

    print(f"分析区间: {start_date.date()} 到 {end_date.date()}")

    rows = fetch_tasks(start_date, end_date)
    if not rows:
        print("该区间内无分拣任务数据。")
        return

    print("正在解析批次数据...")
    df = build_records(rows)
    print(f"共解析出 {len(df):,} 份餐食记录")

    pivot = print_daily_summary(df)
    print_overall_summary(df)

    output_dir = os.path.dirname(os.path.abspath(__file__))
    save_csv(df, pivot, output_dir)


if __name__ == '__main__':
    main()
