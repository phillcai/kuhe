#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成补货周报HTML报告
整合三个数据查询脚本的结果，生成一个完整的HTML报告页面
"""

import sys
import os
from datetime import datetime

# 添加 code 目录到 Python 路径
code_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../code'))
sys.path.insert(0, code_dir)

# 导入三个查询模块
from query_weekly_shortage import query_weekly_shortage
from query_weekly_satisfaction import query_fenjian_log, deduplicate_by_req_task_id, calculate_weekly_satisfaction
from query_weekly_replenishment import query_weekly_replenishment


def generate_html_table(data, table_title, column_formats=None):
    """
    生成HTML表格
    
    Args:
        data: 数据列表
        table_title: 表格标题
        column_formats: 列格式字典，key为列名，value为格式化函数
        
    Returns:
        str: HTML表格代码
    """
    if not data:
        return f"<p>没有{table_title}数据</p>"
    
    # 获取列名
    columns = list(data[0].keys())
    
    # 生成表格HTML
    html = f'''
    <div class="table-container">
        <h2>{table_title}</h2>
        <table>
            <thead>
                <tr>
    '''
    
    # 添加表头
    for col in columns:
        html += f'                    <th>{col}</th>\n'
    
    html += '''                </tr>
            </thead>
            <tbody>
    '''
    
    # 添加数据行
    for row in data:
        html += '                <tr>\n'
        for col in columns:
            value = row[col]
            
            # 应用格式化
            if column_formats and col in column_formats:
                formatted_value = column_formats[col](value)
            else:
                formatted_value = value
            
            html += f'                    <td>{formatted_value}</td>\n'
        html += '                </tr>\n'
    
    html += '''            </tbody>
        </table>
    </div>
    '''
    
    return html


def generate_report():
    """
    生成完整的HTML报告
    """
    print("=" * 100)
    print("开始生成补货周报")
    print("=" * 100)
    print()
    
    # 1. 查询周缺货率数据
    print("【1/3】查询周缺货率数据...")
    try:
        shortage_data = query_weekly_shortage()
        print(f"✅ 成功获取 {len(shortage_data)} 周的缺货率数据\n")
    except Exception as e:
        print(f"❌ 查询周缺货率失败: {str(e)}\n")
        shortage_data = []
    
    # 2. 查询周满足率数据
    print("【2/3】查询周满足率数据...")
    try:
        fenjian_data = query_fenjian_log()
        deduplicated_data = deduplicate_by_req_task_id(fenjian_data)
        satisfaction_data = calculate_weekly_satisfaction(deduplicated_data)
        print(f"✅ 成功获取 {len(satisfaction_data)} 周的满足率数据\n")
    except Exception as e:
        print(f"❌ 查询周满足率失败: {str(e)}\n")
        satisfaction_data = []
    
    # 3. 查询周补货数据
    print("【3/3】查询周补货数据...")
    try:
        replenishment_data = query_weekly_replenishment()
        print(f"✅ 成功获取 {len(replenishment_data)} 周的补货数据\n")
    except Exception as e:
        print(f"❌ 查询周补货数失败: {str(e)}\n")
        replenishment_data = []
    
    # 生成HTML报告
    print("正在生成HTML报告...")
    
    # 定义列格式化函数
    shortage_formats = {
        '缺货率(sku权重)': lambda x: f'{x:.2f}%' if x is not None else 'N/A',
        'session数': lambda x: f'{x:,}' if x is not None else 'N/A'
    }
    
    satisfaction_formats = {
        '全部': lambda x: f'{x:.2f}%' if x is not None else 'N/A',
        '正常车': lambda x: f'{x:.2f}%' if x is not None else 'N/A',
        '虚拟车': lambda x: f'{x:.2f}%' if x is not None else 'N/A'
    }
    
    replenishment_formats = {
        '补货数': lambda x: f'{int(x):,}' if x is not None else 'N/A',
        '日均补货': lambda x: f'{int(x):,}' if x is not None else 'N/A',
        '日均甜品饮料补货数': lambda x: f'{int(x):,}' if x is not None else 'N/A',
        '日最大补货数': lambda x: f'{int(x):,}' if x is not None else 'N/A',
        '日最大甜品饮料补货数': lambda x: f'{int(x):,}' if x is not None else 'N/A',
        '日均点位': lambda x: f'{int(x):,}' if x is not None else 'N/A'
    }
    
    # 生成三个表格
    shortage_table = generate_html_table(shortage_data, "周缺货率统计", shortage_formats)
    satisfaction_table = generate_html_table(satisfaction_data, "周满足率统计", satisfaction_formats)
    replenishment_table = generate_html_table(replenishment_data, "周日均补货数统计", replenishment_formats)
    
    # 生成完整的HTML页面
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    html_content = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>补货周报</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 700;
        }}
        
        .header .subtitle {{
            font-size: 1em;
            opacity: 0.9;
        }}
        
        .content {{
            padding: 40px;
        }}
        
        .table-container {{
            margin-bottom: 50px;
        }}
        
        .table-container:last-child {{
            margin-bottom: 0;
        }}
        
        .table-container h2 {{
            color: #333;
            font-size: 1.8em;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            border-radius: 8px;
            overflow: hidden;
        }}
        
        thead {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}
        
        th {{
            padding: 15px;
            text-align: center;
            font-weight: 600;
            font-size: 0.95em;
            letter-spacing: 0.5px;
        }}
        
        td {{
            padding: 12px 15px;
            text-align: center;
            border-bottom: 1px solid #f0f0f0;
            color: #555;
        }}
        
        tbody tr:hover {{
            background-color: #f8f9ff;
            transition: background-color 0.3s ease;
        }}
        
        tbody tr:last-child td {{
            border-bottom: none;
        }}
        
        /* 数值列右对齐 */
        td:not(:first-child) {{
            text-align: right;
            font-family: 'Courier New', monospace;
        }}
        
        th:first-child,
        td:first-child {{
            text-align: center;
        }}
        
        .footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #666;
            font-size: 0.9em;
            border-top: 1px solid #e0e0e0;
        }}
        
        @media (max-width: 768px) {{
            body {{
                padding: 10px;
            }}
            
            .header {{
                padding: 20px;
            }}
            
            .header h1 {{
                font-size: 1.8em;
            }}
            
            .content {{
                padding: 20px;
            }}
            
            table {{
                font-size: 0.85em;
            }}
            
            th, td {{
                padding: 8px;
            }}
        }}
        
        /* 加载动画 */
        @keyframes fadeIn {{
            from {{
                opacity: 0;
                transform: translateY(20px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}
        
        .table-container {{
            animation: fadeIn 0.6s ease-out;
        }}
        
        .table-container:nth-child(2) {{
            animation-delay: 0.2s;
        }}
        
        .table-container:nth-child(3) {{
            animation-delay: 0.4s;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 补货周报</h1>
            <p class="subtitle">最近42天数据统计 · 生成时间: {current_time}</p>
        </div>
        
        <div class="content">
            {replenishment_table}
            
            {satisfaction_table}
            
            {shortage_table}
        </div>
        
        <div class="footer">
            <p>© 2025 补货数据分析系统 · 自动生成报告</p>
        </div>
    </div>
</body>
</html>
'''
    
    # 保存HTML文件
    output_path = os.path.join(os.path.dirname(__file__), 'report.html')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ HTML报告已生成: {output_path}")
    print(f"   文件大小: {os.path.getsize(output_path) / 1024:.2f} KB")
    
    print("\n" + "=" * 100)
    print("✅ 补货周报生成完成！")
    print("=" * 100)
    print(f"\n请在浏览器中打开: {output_path}")
try:
    import pyperclip
    pyperclip.copy(output_path)
    print("📋 已将报告文件路径复制到剪贴板")
except ImportError:
    print("⚠️ 未安装pyperclip，无法自动复制路径到剪贴板")
except Exception as e:
    print(f"⚠️ 复制路径到剪贴板时出错: {e}")


def main():
    """
    主函数
    """
    try:
        generate_report()
    except Exception as e:
        print(f"\n❌ 发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

