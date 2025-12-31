#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
读取 ck_box_commodity_fenjian_log 表最近 7 天的数据
"""

import sys
import os
from datetime import datetime
import pandas as pd

# 添加 code 目录到 Python 路径，以便导入 lib 模块
code_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../code'))
sys.path.insert(0, code_dir)

from lib import create_db_connection


def get_fenjian_log_last_7_days(db=None):
    """
    获取 ck_box_commodity_fenjian_log 表最近 7 天的数据
    
    Args:
        db: 数据库连接对象，如果为None则创建新连接
    
    Returns:
        tuple: (查询结果列表, 数据库连接对象)
    """
    if db is None:
        print(f"正在连接数据库 (smart_cooker_sg)...")
        try:
            db = create_db_connection(mysql_database='smart_cooker_sg')
        except Exception as e:
            print(f"连接数据库失败: {e}")
            return [], None
    
    print(f"正在查询 ck_box_commodity_fenjian_log 表最近 7 天的数据...")
    
    # 构建 SQL 查询
    sql = """
        SELECT * 
        FROM ck_box_commodity_fenjian_log
        WHERE DATE(create_time) >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
        ORDER BY id DESC
    """
    
    try:
        results = db.execute_query(sql)
        print(f"✅ 查询成功！共查询到 {len(results)} 条记录\n")
        return results, db
    except Exception as e:
        print(f"❌ 查询失败: {e}")
        return [], db


def display_and_save_results(results):
    """
    显示查询结果并保存到CSV文件
    
    Args:
        results: 查询结果列表
    """
    if not results:
        print("未查询到任何记录。")
        return
    
    # 转换为 DataFrame 以便更好地显示
    df = pd.DataFrame(results)
    
    print("=" * 100)
    print(f"ck_box_commodity_fenjian_log 最近 7 天数据 (共 {len(df)} 条)")
    print("=" * 100)
    
    # 显示前10条记录
    print("\n前 10 条记录预览：")
    print("-" * 100)
    try:
        print(df.head(10).to_markdown(index=False))
    except ImportError:
        # 如果没有安装 tabulate，使用默认格式
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        print(df.head(10).to_string(index=False))
    
    # 显示基本统计信息
    print("\n" + "=" * 100)
    print("数据统计信息：")
    print("=" * 100)
    print(f"总记录数: {len(df)}")
    print(f"列数: {len(df.columns)}")
    print(f"列名: {', '.join(df.columns.tolist())}")
    
    # 如果有时间字段，显示时间范围
    if 'create_time' in df.columns:
        print(f"\n时间范围:")
        print(f"  最早: {df['create_time'].min()}")
        print(f"  最晚: {df['create_time'].max()}")
    
    # 保存到 CSV 文件
    output_dir = os.path.dirname(os.path.abspath(__file__))
    date_str = datetime.now().strftime('%Y%m%d')
    csv_path = os.path.join(output_dir, f'fenjian_log_7days_{date_str}.csv')
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"\n✅ 数据已保存至: {csv_path}")
    
    # 保存到 Excel 文件（可选）
    try:
        excel_path = os.path.join(output_dir, f'fenjian_log_7days_{date_str}.xlsx')
        df.to_excel(excel_path, index=False, engine='openpyxl')
        print(f"✅ 数据已保存至: {excel_path}")
    except Exception as e:
        print(f"⚠️ 保存 Excel 文件失败: {e}")


def main():
    """
    主函数
    """
    results, db = get_fenjian_log_last_7_days()
    
    if results:
        display_and_save_results(results)
    else:
        print("未查询到任何记录。")


if __name__ == "__main__":
    main()

