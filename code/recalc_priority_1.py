# -*- coding: utf-8 -*-
import pandas as pd

# 读取csv文件
# 中文注释：使用相对本文件的路径获取csv文件路径
import os
# 中文注释：data 目录和 code 目录是同一级的，拼接 data/sourcecsv.csv 路径
csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'sourcecsv.csv')

# 读取数据
df = pd.read_csv(csv_path)

# 过滤掉 is_skip=1 的点位
# 只保留 is_skip 不为 1 的数据
df = df[df['is_skip'] != 1]

# 先将 task_id 字段去逗号并转为 int 类型
df['task_id'] = df['task_id'].astype(str).str.replace(',', '').astype(int)

# =========================
# 计算优先级的主函数
# =========================
def calc_priority(df: pd.DataFrame, w1=0.6, w2=0.25, w3=0.15) -> pd.DataFrame:
    """
    # 重新计算优先级
    :param df: pandas DataFrame，包含点位数据
    :param w1: 缺货风险分权重
    :param w2: 预计销量分权重
    :param w3: 点位类型分权重
    :return: 新增 priority 列的 DataFrame
    """
    # 归一化处理
    def norm(series: pd.Series) -> pd.Series:
        min_v = series.min()
        max_v = series.max()
        if max_v - min_v == 0:
            return pd.Series([0.5] * len(series), index=series.index)
        return (series - min_v) / (max_v - min_v)

    # 计算标准分
    stockout_score_norm = norm(df['stock_out_score'])
    sales_score_norm = norm(df['sales_score'])
    type_score_norm = norm(df['type_score']) if 'type_score' in df.columns else 0

    # 用 .loc 赋值，避免 SettingWithCopyWarning
    df.loc[:, 'priority_new'] = (
        w1 * stockout_score_norm +
        w2 * sales_score_norm +
        w3 * type_score_norm
    )

    return df

# =========================
# 主流程
# =========================
if __name__ == '__main__':
    # 设置权重，可根据需要调整
    w1 = 0.6  # 缺货风险分权重
    w2 = 0.2 # 预计销量分权重
    w3 = 0 # 点位类型分权重

    # 选择分组 task_id
    import sys
    if len(sys.argv) > 1:
        # 如果命令行指定了 task_id
        task_id = int(str(sys.argv[1]).replace(',', ''))
        print(f"使用指定 task_id: {task_id}")
    else:
        # 没有指定则自动选择最大 task_id
        task_id = df['task_id'].max()
        print(f"未指定 task_id，自动选择最大 task_id: {task_id}")

    # 只保留当前 task_id 的数据
    df_task = df[df['task_id'] == task_id].copy()  # 显式复制

    # 重新计算优先级
    df_new = calc_priority(df_task, w1, w2, w3)

    # 按新优先级排序
    df_new = df_new.sort_values(by="priority_new", ascending=False)

    # 输出前几行查看，并显示 task_id
    print(df_new[['id', 'point_id', 'priority_new', 'task_id']])
    # 打印所有 point_id，逗号分隔
    point_ids_str = ','.join(str(pid) for pid in df_new['point_id'])
    print("按优先级排序后的 point_id 列表：")
    print(point_ids_str)

    # 如需保存结果
    # df_new.to_csv('data/sourcecsv_with_priority.csv', index=False) 