#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析Excel文件中P列（上架时间）的统计信息
计算平均值、标准差、最大值、最小值
"""

import pandas as pd
import numpy as np
import os

def analyze_p_column_stats():
    """
    分析Excel文件中P列（上架时间）的统计信息
    """
    # Excel文件路径
    excel_file = "/Users/admin/Code/MyCode/kuhe/data/点位耗时.xlsx"
    
    try:
        # 读取Excel文件的所有工作表
        print("正在读取Excel文件...")
        
        # 首先检查所有工作表
        excel_file_obj = pd.ExcelFile(excel_file)
        sheet_names = excel_file_obj.sheet_names
        print(f"发现工作表: {sheet_names}")
        
        # 尝试读取每个工作表
        for sheet_name in sheet_names:
            print(f"\n=== 分析工作表: {sheet_name} ===")
            df = pd.read_excel(excel_file, sheet_name=sheet_name)
            
            # 显示文件基本信息
            print(f"数据形状: {df.shape}")
            print(f"列名: {list(df.columns)}")
            
            # 检查P列或上架时间相关列是否存在
            target_column = None
            if 'P' in df.columns:
                target_column = 'P'
            elif '点位上架时长(点位完成上架时间-点位开始上架时间)' in df.columns:
                target_column = '点位上架时长(点位完成上架时间-点位开始上架时间)'
            elif '上架时长' in str(df.columns):
                # 查找包含"上架时长"的列
                for col in df.columns:
                    if '上架时长' in str(col):
                        target_column = col
                        break
            
            if target_column is None:
                print("未找到P列或上架时间相关列")
                print("可用的列名：")
                for i, col in enumerate(df.columns):
                    print(f"  {i}: {col}")
                continue
            
            # 如果找到目标列，进行分析
            analyze_p_column_data(df, sheet_name, target_column)
            
    except Exception as e:
        print(f"读取文件时出错: {e}")

def analyze_p_column_data(df, sheet_name, target_column):
    """
    分析指定DataFrame中目标列的数据
    """
    # 获取目标列数据
    target_data = df[target_column]
    
    # 显示目标列的基本信息
    print(f"{target_column}数据分析：")
    print(f"数据类型: {target_data.dtype}")
    print(f"非空值数量: {target_data.notna().sum()}")
    print(f"空值数量: {target_data.isna().sum()}")
    
    # 移除空值
    data_clean = target_data.dropna()
    
    if len(data_clean) == 0:
        print("错误：目标列中没有有效数据")
        return
    
    # 计算统计信息
    mean_val = data_clean.mean()
    std_val = data_clean.std()
    max_val = data_clean.max()
    min_val = data_clean.min()
    
    # 显示结果
    print(f"\n=== {target_column}统计结果 ===")
    print(f"平均值: {mean_val:.4f}")
    print(f"标准差: {std_val:.4f}")
    print(f"最大值: {max_val}")
    print(f"最小值: {min_val}")
    
    # 显示前几个数据样本
    print(f"\n前10个数据样本:")
    print(data_clean.head(10).tolist())
    
    # 数据类型转换尝试（如果是字符串格式的时间）
    if data_clean.dtype == 'object':
        print(f"\n尝试将字符串转换为数值...")
        try:
            # 尝试转换为数值
            data_numeric = pd.to_numeric(data_clean, errors='coerce')
            data_numeric_clean = data_numeric.dropna()
            
            if len(data_numeric_clean) > 0:
                print(f"数值转换成功！")
                print(f"=== 转换后的{target_column}统计结果 ===")
                print(f"平均值: {data_numeric_clean.mean():.4f}")
                print(f"标准差: {data_numeric_clean.std():.4f}")
                print(f"最大值: {data_numeric_clean.max()}")
                print(f"最小值: {data_numeric_clean.min()}")
            else:
                print("数值转换失败")
        except Exception as e:
            print(f"数值转换出错: {e}")

if __name__ == "__main__":
    analyze_p_column_stats()
