# -*- coding: utf-8 -*-
import pandas as pd

# 读取csv文件
# 中文注释：使用相对本文件的路径获取csv文件路径
import os
# 中文注释：data 目录和 code 目录是同一级的，拼接 data/sourcecsv.csv 路径
csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'priority.csv')

# 读取数据
df = pd.read_csv(csv_path)


# 先将 task_id 字段去逗号并转为 int 类型
df['task_id'] = df['req_task_id'].astype(str).str.replace(',', '').astype(int)

# 中文注释：用 stock_out_hour 作为缺货风险分，用 sales 作为预计销量分
# 生成 stock_out_score 和 sales_score 两列

df['stock_out_score'] = df['stockout_score']
df['point_stock_score'] = 1 / (df['point_stock']+1)
# df['sales_score'] = df['sales_score'] - df['point_stock']

# =========================
# 计算优先级的主函数
# =========================
def calc_priority(df: pd.DataFrame, w1=0.6, w2=0.25, w3=0.15, w4=0.15) -> pd.DataFrame:
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
    type_score_norm = norm(df['type_score'])
    stock_score_norm = norm(df['point_stock_score'])

    # 中文注释：保存归一化分数到新列
    df.loc[:, 'stock_out_score_norm'] = stockout_score_norm * w1
    df.loc[:, 'sales_score_norm'] = sales_score_norm * w2
    df.loc[:, 'type_score_norm'] = type_score_norm * w3
    df.loc[:, 'stock_score_norm'] = stock_score_norm * w4

    # 用 .loc 赋值，避免 SettingWithCopyWarning
    df.loc[:, 'priority_new'] = (
        w1 * stockout_score_norm +
        w2 * sales_score_norm +
        w3 * type_score_norm +
        w4 * stock_score_norm
    )

    return df

# =========================
# 主流程
# =========================
if __name__ == '__main__':
    # 设置权重，可根据需要调整
    w1 = 0.457  # 缺货风险分权重
    w2 = 0.299  # 预计销量分权重
    w3 = 0.244  # 点位类型分权重
    w4 = 0.00  # 点位类型分权重

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
    assert isinstance(df_task, pd.DataFrame), "df_task 不是 DataFrame"
    if df_task.empty:
        raise ValueError("筛选后没有数据，无法计算优先级")
    df_new = calc_priority(df_task, w1, w2, w3)

    # 按新优先级排序
    df_new = df_new.sort_values(by="priority_new", ascending=False)

    # 中文注释：输出前几行，显示 point_id、原始分、归一化分、priority_new、task_id
    print(df_new[['point_id', 'stock_out_score', 'stock_out_score_norm', 'sales_score', 'sales_score_norm', 'point_stock_score','stock_score_norm', 'type_score', 'type_score_norm', 'priority_new', 'task_id']])

    # 打印所有 point_id，逗号分隔
    point_ids_str = ','.join(str(pid) for pid in df_new['point_id'])
    print("按优先级排序后的 point_id 列表：")
    print(point_ids_str)

    # 如需保存结果
    # df_new.to_csv('data/sourcecsv_with_priority.csv', index=False) 