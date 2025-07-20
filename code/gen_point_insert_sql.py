# -*- coding: utf-8 -*-
"""
中文注释：
本脚本用于将 data/点位信息.csv 的全部数据，批量生成 kuhe.point 表的 insert 语句，写入 insert_point.sql 文件。
"""
import csv
import os

# 中文注释：生成 point 表 insert 语句的主函数
def generate_point_insert_sql(csv_path, sql_path):
    # 目标表字段顺序
    fields = [
        'id', 'point_name', 'point_type', 'point_max_stock', 'latitude', 'longitude',
        'point_address', 'create_time', 'data_type', 'start_time', 'end_time', 'remark', 'escort'
    ]
    values_list = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            values = []
            for col in fields:
                val = row[col].strip()
                if val == '':
                    values.append('NULL')
                elif col in ['id', 'point_max_stock']:
                    values.append(val)
                elif col in ['latitude', 'longitude']:
                    try:
                        values.append(str(float(val)))
                    except:
                        values.append('NULL')
                else:
                    # 字符串内容，单引号包裹，内部单引号转义
                    val = val.replace("'", "''")
                    values.append(f"'{val}'")
            values_list.append(f"({', '.join(values)})")
    # 生成 insert 语句
    sql = '-- 中文注释：将点位信息批量插入 kuhe.point 表\n'
    sql += 'INSERT INTO kuhe.point\n'
    sql += '(' + ', '.join(fields) + ') VALUES\n'
    sql += ',\n'.join(values_list)
    sql += ';\n'
    # 写入文件
    with open(sql_path, 'w', encoding='utf-8') as f:
        f.write(sql)

# 中文注释：主入口
def main():
    csv_path = os.path.join(os.path.dirname(__file__), '../data/点位信息.csv')
    sql_path = os.path.join(os.path.dirname(__file__), '../insert_point.sql')
    generate_point_insert_sql(csv_path, sql_path)

if __name__ == '__main__':
    main() 