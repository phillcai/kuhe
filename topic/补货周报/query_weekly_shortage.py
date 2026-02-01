#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查询周缺货率数据脚本
从 report.t_commodity_shortage 表查询最近90天的周缺货率统计
"""

import sys
import os

# 添加 code 目录到 Python 路径，以便导入 lib 模块
code_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../code'))
sys.path.insert(0, code_dir)

from lib import create_db_connection
import pandas as pd
from datetime import datetime


def query_weekly_shortage():
    """
    查询周缺货率数据
    使用新的活跃session数据源
    
    Returns:
        list: 周缺货率数据列表
    """
    print("正在连接数据库 (report)...")
    # 使用 report 数据库
    db = create_db_connection(mysql_database='report')
    
    print("正在查询周缺货率数据...")
    
    # 主查询：结合缺货率和session数据
    sql = """
        WITH 
        -- 高流量点位列表（排除这些点位）
        high_traffic_points AS (
            SELECT DISTINCT
                dt,
                point_id
            FROM t_user_bhv_session
            WHERE 
                source = 'offline'
                AND country = 'Singapore'
                AND point_id IN ( SELECT id FROM report.t_point WHERE country = 'Singapore')
                AND point_id IN ( SELECT id FROM smart_cooker_sg.point_ext WHERE 1 = 1)
                AND dt >= date_sub(current_date(), interval 42 day) 
                AND dt <= current_date()
            GROUP BY dt, point_id
            HAVING COUNT(DISTINCT menu_uid) > 500
        ),
        -- APP渠道每日活跃session数
        app_sessions AS (
            SELECT  
                dt,
                COUNT(DISTINCT CASE WHEN length(activity_uid) > 4 THEN session_id END) AS session_cnt
            FROM t_user_bhv_session
            WHERE 
                source = 'app'
                AND country = 'Singapore'
                AND point_id IN ( SELECT id FROM report.t_point WHERE country = 'Singapore' )
                AND point_id IN ( SELECT id FROM smart_cooker_sg.point_ext WHERE 1 = 1 )
                AND dt >= date_sub(current_date(), interval 42 day) 
                AND dt <= current_date()
            GROUP BY dt
        ),
        -- 点餐屏渠道每日活跃session数（排除高流量点位）
        offline_sessions AS (
            SELECT  
                a.dt,
                COUNT(DISTINCT CASE WHEN length(a.menu_uid) > 4 THEN a.session_id END) AS session_cnt
            FROM t_user_bhv_session a
            LEFT JOIN high_traffic_points b 
                ON a.dt = b.dt AND a.point_id = b.point_id
            WHERE 
                a.source = 'offline'
                AND a.country = 'Singapore'
                AND a.point_id IN ( SELECT id FROM report.t_point WHERE country = 'Singapore')
                AND a.point_id IN ( SELECT id FROM smart_cooker_sg.point_ext WHERE 1 = 1 )
                AND a.dt >= date_sub(current_date(), interval 42 day) 
                AND a.dt <= current_date()
                AND b.dt IS NULL  -- 排除高流量点位
            GROUP BY a.dt
        ),
        -- 合并APP和点餐屏的session数据（每日一条记录）
        session_data_old AS (
            SELECT 
                dt,
                SUM(session_cnt) AS daily_session_cnt
            FROM (
                SELECT dt, session_cnt FROM app_sessions
                UNION ALL
                SELECT dt, session_cnt FROM offline_sessions
            ) combined
            GROUP BY dt
        ),
        -- 点位 session 数（按日聚合，口径：point_session_log 最近 42 天）
        session_data AS (
            SELECT
                DATE(psl.create_time) AS dt,
                COUNT(psl.session_id) AS session_cnt
            FROM smart_cooker_sg.point_session_log psl
            WHERE psl.create_time >= DATE_SUB(CURDATE(), INTERVAL 42 DAY)
            GROUP BY dt
        ),
        -- 缺货率数据（按日期聚合，避免重复计算session）
        shortage_by_date AS (
            SELECT
                dt,
                SUM(online_dish_cnt) AS total_online_dish_cnt,
                SUM(max_commodity_cnt) AS total_max_commodity_cnt
            FROM t_commodity_shortage
            WHERE
                commodity_type = 'main'
                AND dt BETWEEN DATE_SUB(CURDATE(), INTERVAL 42 DAY) AND CURDATE()
            GROUP BY dt
        ),
        weekly_data AS (
          SELECT
            -- 周标识：取该周的周日（格式：YYYY-MM-DD），作为每周的唯一标识
            DATE_FORMAT(
              STR_TO_DATE(t1.dt, '%Y-%m-%d') - INTERVAL (DAYOFWEEK(STR_TO_DATE(t1.dt, '%Y-%m-%d')) - 1) DAY,
              '%Y-%m-%d'
            ) AS '周起始日(周日)',
            
            -- 周缺货率（sku权重）：按周聚合后计算
            CASE 
              WHEN IFNULL(SUM(t1.total_max_commodity_cnt), 0) = 0 THEN 0
              ELSE ROUND(1 - IFNULL(SUM(t1.total_online_dish_cnt), 0) / SUM(t1.total_max_commodity_cnt), 4)
            END AS '缺货率(sku权重)',
            
            -- 周session数：直接求和每日session数（不会重复）
            SUM(IFNULL(s.session_cnt, 0)) AS 'session数',
            
            -- 统计该周有几天的数据
            COUNT(DISTINCT t1.dt) AS days_count
          
          FROM shortage_by_date t1
          LEFT JOIN session_data s ON t1.dt = s.dt
          
          GROUP BY
            DATE_FORMAT(
              STR_TO_DATE(t1.dt, '%Y-%m-%d') - INTERVAL (DAYOFWEEK(STR_TO_DATE(t1.dt, '%Y-%m-%d')) - 1) DAY,
              '%Y-%m-%d'
            )
        )
        SELECT
          `周起始日(周日)`,
          `缺货率(sku权重)`,
          `session数`
        FROM weekly_data
        # WHERE days_count >= 7  -- 只显示完整的周（7天数据）
        ORDER BY `周起始日(周日)` DESC
    """
    
    results = db.execute_query(sql)
    print(f"✅ 查询成功！共查询到 {len(results)} 周的数据\n")
    
    # 将缺货率转换为百分比（乘以100）
    for row in results:
        if '缺货率(sku权重)' in row and row['缺货率(sku权重)'] is not None:
            row['缺货率(sku权重)'] = round(row['缺货率(sku权重)'] * 100, 2)
    
    return results


def display_shortage_data(data):
    """
    显示周缺货率数据
    
    Args:
        data: 周缺货率数据列表
    """
    if not data:
        print("没有查询到任何数据")
        return
    
    # 转换为 DataFrame 以便更好地展示
    df = pd.DataFrame(data)
    
    print("=" * 100)
    print("周缺货率数据统计（最近42天）")
    print("=" * 100)
    print(f"\n总计周数: {len(df)}")
    
    # 显示列信息
    print(f"\n数据列: {', '.join(df.columns.tolist())}")
    
    # 显示所有数据（因为数据量不大）
    print("\n详细数据:")
    print("-" * 100)
    print(df.to_string(index=False))
    
    # 显示数据统计信息
    print("\n" + "=" * 100)
    print("数据统计摘要")
    print("=" * 100)
    
    # 缺货率统计（已经是百分比格式）
    if '缺货率(sku权重)' in df.columns:
        shortage_rate = df['缺货率(sku权重)']
        print(f"\n缺货率(sku权重)统计:")
        print(f"  平均值: {shortage_rate.mean():.2f}%")
        print(f"  最小值: {shortage_rate.min():.2f}%")
        print(f"  最大值: {shortage_rate.max():.2f}%")
        print(f"  中位数: {shortage_rate.median():.2f}%")
    
    # session数统计
    if 'session数' in df.columns:
        session_cnt = df['session数']
        print(f"\nsession数统计:")
        print(f"  总计: {session_cnt.sum():,}")
        print(f"  平均值: {session_cnt.mean():.2f}")
        print(f"  最小值: {session_cnt.min()}")
        print(f"  最大值: {session_cnt.max()}")
    
    return df


def export_to_csv(data, output_file=None):
    """
    导出数据到 CSV 文件
    
    Args:
        data: 周缺货率数据列表
        output_file: 输出文件路径（可选）
    """
    if not data:
        print("没有数据可以导出")
        return
    
    # 如果没有指定输出文件，使用默认文件名
    if not output_file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'weekly_shortage_{timestamp}.csv'
    
    # 转换为 DataFrame
    df = pd.DataFrame(data)
    
    # 导出到 CSV
    output_path = os.path.join(os.path.dirname(__file__), output_file)
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    
    print(f"\n✅ 数据已导出到: {output_path}")
    print(f"   文件大小: {os.path.getsize(output_path) / 1024:.2f} KB")


def export_to_excel(data, output_file=None):
    """
    导出数据到 Excel 文件（带格式）
    
    Args:
        data: 周缺货率数据列表
        output_file: 输出文件路径（可选）
    """
    if not data:
        print("没有数据可以导出")
        return
    
    try:
        # 如果没有指定输出文件，使用默认文件名
        if not output_file:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f'周缺货率_{timestamp}.xlsx'
        
        # 转换为 DataFrame
        df = pd.DataFrame(data)
        
        # 确保数值列是数值类型
        if '缺货率(sku权重)' in df.columns:
            df['缺货率(sku权重)'] = pd.to_numeric(df['缺货率(sku权重)'], errors='coerce')
        if 'session数' in df.columns:
            df['session数'] = pd.to_numeric(df['session数'], errors='coerce')
        
        # 导出到 Excel
        output_path = os.path.join(os.path.dirname(__file__), output_file)
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='周缺货率', index=False)
            
            # 获取工作表
            worksheet = writer.sheets['周缺货率']
            
            # 导入样式模块
            from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
            
            # 设置列宽
            column_widths = {
                'A': 18,  # 周起始日(周日)
                'B': 20,  # 缺货率(sku权重)
                'C': 15,  # session数
            }
            
            for col, width in column_widths.items():
                worksheet.column_dimensions[col].width = width
            
            # 设置表头样式
            header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
            header_font = Font(bold=True, color='FFFFFF', size=11)
            
            for cell in worksheet[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center', vertical='center')
            
            # 设置数据行格式
            for row_idx in range(2, len(df) + 2):
                # 周起始日 - 居中对齐
                worksheet[f'A{row_idx}'].alignment = Alignment(horizontal='center', vertical='center')
                
                # 缺货率 - 百分比格式（保留2位小数，带%符号）
                worksheet[f'B{row_idx}'].number_format = '0.00"%"'
                worksheet[f'B{row_idx}'].alignment = Alignment(horizontal='right', vertical='center')
                
                # session数 - 数值格式（千位分隔符）
                worksheet[f'C{row_idx}'].number_format = '#,##0'
                worksheet[f'C{row_idx}'].alignment = Alignment(horizontal='right', vertical='center')
            
            # 设置边框
            thin_border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )
            
            for row in worksheet.iter_rows(min_row=1, max_row=len(df) + 1, min_col=1, max_col=3):
                for cell in row:
                    cell.border = thin_border
        
        print(f"\n✅ 数据已导出到 Excel: {output_path}")
        print(f"   文件大小: {os.path.getsize(output_path) / 1024:.2f} KB")
        
    except Exception as e:
        print(f"\n⚠️  Excel 导出失败: {str(e)}")
        print("   已自动导出为 CSV 格式")


def main():
    """
    主函数
    """
    print("=" * 100)
    print("周缺货率数据查询工具")
    print("=" * 100)
    print()
    
    try:
        # 查询数据
        data = query_weekly_shortage()
        
        # 显示数据
        df = display_shortage_data(data)
        
        
        # 导出数据到 Excel
        export_to_excel(data)
        
        print("\n" + "=" * 100)
        print("✅ 所有操作完成！")
        print("=" * 100)
        
    except Exception as e:
        print(f"\n❌ 发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

