# -*- coding: utf-8 -*-
"""
输入：一批点位id（逗号分割）
输出：json格式，包含点位id、name、地址、当天剩余可补货分钟数
过滤：首尾点位不做过滤，中间点位若当前不在补货窗口则剔除
"""
import pandas as pd
import sys
import json
import datetime
import pyperclip
import re

# 读取点位信息
info_path = 'data/点位信息.csv'
df = pd.read_csv(info_path)

# 中文注释：获取命令行参数，支持指定当前日期和时间
if len(sys.argv) < 2:
    # 未传入参数时使用默认点位id
    str_ids = '999,27,124,123,147,30,155,81,998'
    # 中文注释：支持逗号和下划线作为分隔符
    point_ids = re.split(r'[,_]', str_ids)
    point_ids = [pid.strip() for pid in point_ids if pid.strip()]
    print(f"未指定点位id，使用默认值: {str_ids}")
    custom_datetime = '2025-07-09 10:30'
elif len(sys.argv) == 2:
    # 中文注释：只传入点位id，支持逗号和下划线作为分隔符
    point_ids = re.split(r'[,_]', sys.argv[1])
    point_ids = [pid.strip() for pid in point_ids if pid.strip()]
    custom_datetime = '2025-07-09 10:30'
else:
    # 中文注释：传入点位id和当前日期时间，支持逗号和下划线作为分隔符
    point_ids = re.split(r'[,_]', sys.argv[1])
    point_ids = [pid.strip() for pid in point_ids if pid.strip()]
    custom_datetime = sys.argv[2].strip()
    # 校验日期时间格式
    try:
        dt = datetime.datetime.strptime(custom_datetime, '%Y-%m-%d %H:%M')
    except Exception:
        print(f"指定的当前日期时间格式不正确，应为YYYY-MM-DD HH:MM，如2024-06-01 08:30，实际为：{custom_datetime}")
        sys.exit(1)

# 检查point_ids是否为空
if not point_ids:
    print("未提供有效的点位id列表！")
    sys.exit(1)

# 检查df中是否有'id'列
if 'id' not in df.columns:
    print("点位信息表缺少'id'列")
    sys.exit(1)

# 只保留相关点位
# 统一id为字符串进行比对
ids_str = df['id'].astype(str)
df = df[ids_str.isin(point_ids)].copy()

# 检查过滤后df是否为空
if df.empty:
    print("没有匹配的点位id，请检查输入或点位信息表")
    sys.exit(1)

# 获取当前星期和时间
if 'custom_datetime' in locals() and custom_datetime:
    # 中文注释：如果指定了当前日期时间参数，则使用该时间
    now = datetime.datetime.strptime(custom_datetime, '%Y-%m-%d %H:%M')
else:
    now = datetime.datetime.now()
weekday = now.isoweekday()  # 1=周一
current_time = now.strftime('%H:%M')

# 中文注释：计算当天剩余可补货分钟数的函数
def get_remain_minutes(row):
    """
    计算当天剩余可补货分钟数
    :param row: 行数据
    :return: 剩余分钟数（int），若不在补货窗口则为0
    """
    try:
        allowed_days = eval(row['data_type']) if not pd.isnull(row['data_type']) else []
    except Exception:
        allowed_days = []
    # 已去除调试和警告输出
    if weekday not in allowed_days:
        return 0
    # 补货时间窗口
    start = row['start_time']
    end = row['end_time']
    # 当前时间早于窗口
    if current_time < start:
        start_dt = datetime.datetime.strptime(start, '%H:%M')
        end_dt = datetime.datetime.strptime(end, '%H:%M')
        return int((end_dt - start_dt).total_seconds() // 60)
    # 当前时间在窗口内
    elif start <= current_time <= end:
        now_dt = datetime.datetime.strptime(current_time, '%H:%M')
        end_dt = datetime.datetime.strptime(end, '%H:%M')
        return max(0, int((end_dt - now_dt).total_seconds() // 60))
    # 当前时间晚于窗口
    else:
        return 0

# 中文注释：构建结果
result = []
for idx, pid in enumerate(point_ids):
    row = df[df['id'].astype(str) == pid]
    if row.empty:
        print(f"点位 {pid} 不存在于点位信息表，已跳过。")
        continue
    row = row.iloc[0]
    # 首尾点位不过滤
    if idx == 0 or idx == len(point_ids) - 1:
        remain_min = get_remain_minutes(row)  # 也可不算，但这里保留
        result.append({
            'id': int(row['id']),
            'name': row['point_name'],
            'address': row['point_address'],
            'remain_minutes': int(remain_min)
        })
    else:
        remain_min = get_remain_minutes(row)
        if remain_min > 0:
            result.append({
                'id': int(row['id']),
                'name': row['point_name'],
                'address': row['point_address'],
                'remain_minutes': int(remain_min)
            })
        else:
            print(f"点位 {pid} 当前不在补货窗口，已跳过。")

# 输出json
# 中文注释：将结果JSON复制到剪切板
# 中文注释：在结果外层增加一个字段，记录最开始输入的时间或默认时间
output = {
    "input_time": current_time,  # 记录输入时间
    "points": result
}

json_str = json.dumps(output, ensure_ascii=False, indent=2)
pyperclip.copy(json_str)
print(json_str)