#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试CSV读取方法
"""

import pandas as pd
import csv

def method1_native_csv(file_path):
    """方法1：使用原生CSV模块"""
    print("🔍 方法1：使用原生CSV模块")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            data = list(reader)
        
        df = pd.DataFrame(data)
        print(f"✅ 成功！形状: {df.shape}")
        return df
    except Exception as e:
        print(f"❌ 失败: {e}")
        return None

def method2_manual_build(file_path):
    """方法2：手动构建DataFrame"""
    print("\n🔍 方法2：手动构建DataFrame")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)
            rows = list(reader)
        
        # 创建字典数据
        data_dict = {header: [] for header in headers}
        for row in rows:
            for i, header in enumerate(headers):
                value = row[i] if i < len(row) else None
                data_dict[header].append(value)
        
        df = pd.DataFrame(data_dict)
        print(f"✅ 成功！形状: {df.shape}")
        return df
    except Exception as e:
        print(f"❌ 失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def method3_chunked_read(file_path):
    """方法3：分块读取"""
    print("\n🔍 方法3：分块读取（如果有问题行可以识别）")
    try:
        chunks = []
        chunk_size = 100
        for chunk in pd.read_csv(file_path, chunksize=chunk_size):
            chunks.append(chunk)
            print(f"  读取了 {len(chunk)} 行")
        
        df = pd.concat(chunks, ignore_index=True)
        print(f"✅ 成功！形状: {df.shape}")
        return df
    except Exception as e:
        print(f"❌ 失败: {e}")
        return None

if __name__ == "__main__":
    file_path = "data/点位耗时_cleaned.csv"
    
    print("=" * 60)
    print("🧪 测试CSV文件读取")
    print("=" * 60)
    print(f"文件: {file_path}\n")
    
    # 尝试方法1
    df1 = method1_native_csv(file_path)
    
    # 尝试方法2
    df2 = method2_manual_build(file_path)
    
    # 尝试方法3
    # df3 = method3_chunked_read(file_path)
    
    # 如果method1或2成功，显示前几行
    df = df1 if df1 is not None else df2
    if df is not None:
        print("\n" + "=" * 60)
        print("📊 数据预览")
        print("=" * 60)
        print(df.head())
        print("\n📋 列名:")
        print(df.columns.tolist())
        print("\n📈 数据类型:")
        print(df.dtypes)

