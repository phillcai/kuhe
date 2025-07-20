# -*- coding: utf-8 -*-
"""
本脚本用于将点位按地理位置进行动态分区，并统计每组的时间窗口分布，支持数量均衡和时间窗分散优化。
"""

import pandas as pd
import os
import numpy as np
from sklearn.cluster import KMeans
from collections import defaultdict

# 读取点位信息数据
csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', '点位信息.csv')
points_df = pd.read_csv(csv_path)

# 合并同一id的多个时间窗口
point_dict = {}
# 中文注释：过滤掉pid为998和999的点位，不参与后续计算
for _, row in points_df.iterrows():
    pid = row['id']
    if pid in [998, 999]:
        continue  # 跳过pid为998和999的点
    lng = row['longitude']
    lat = row['latitude']
    start = row['start_time']
    end = row['end_time']
    if pid not in point_dict:
        point_dict[pid] = {'lng': lng, 'lat': lat, 'time_windows': []}
    point_dict[pid]['time_windows'].append((start, end))
# 计算主时间窗均值（分钟）
def main_time_window_mean(time_windows):
    starts = []
    for s, _ in time_windows:
        h, m = map(int, str(s).split(':'))
        starts.append(h * 60 + m)
    return np.mean(starts) if starts else 0

# 1. 只用经纬度做K-means聚类
n_clusters = 3  # 可根据实际需求调整
pid_list = list(point_dict.keys())
geo_features = np.array([[point_dict[pid]['lng'], point_dict[pid]['lat']] for pid in pid_list])
kmeans = KMeans(n_clusters=n_clusters, random_state=42)
labels = kmeans.fit_predict(geo_features)

# 初始分组
groups = defaultdict(list)
for i, label in enumerate(labels):
    pid = pid_list[i]
    groups[label].append(pid)

# 2. 数量均衡调整（边界点欧氏距离）
def balance_group_size(groups, features, target_size):
    changed = True
    while changed:
        sizes = {g: len(pids) for g, pids in groups.items()}
        # 用排序取最大最小组
        max_g = sorted(sizes.items(), key=lambda x: x[1], reverse=True)[0][0]
        min_g = sorted(sizes.items(), key=lambda x: x[1])[0][0]
        if sizes[max_g] - sizes[min_g] <= 1:
            break
        # 计算最大组质心
        max_center = np.mean([features[pid] for pid in groups[max_g]], axis=0)
        # 找最大组中距离质心最远的点
        dists = [(np.linalg.norm(features[pid] - max_center), pid) for pid in groups[max_g]]
        dists.sort(reverse=True)
        move_pid = dists[0][1]
        groups[max_g].remove(move_pid)
        groups[min_g].append(move_pid)
    return groups

# 构建pid->geo特征映射
gid_features = {pid: np.array([point_dict[pid]['lng'], point_dict[pid]['lat']]) for pid in pid_list}
target_size = len(pid_list) // n_clusters

# 数量均衡
groups = balance_group_size(groups, gid_features, target_size)

# 3. 时间窗二次均衡（最大最小间隔）
# 中文注释：只对主时间窗均值在 9:00~21:00（540~1260 分钟）的点位进行分散优化，其他点位不参与该步骤

def balance_time_window(groups, point_dict, features, min_interval=120):
    for g, pids in groups.items():
        # 只筛选主时间窗均值在 9:00~21:00 的点位
        filtered_pids = []
        filtered_time_means = []
        for pid in pids:
            mean_time = float(main_time_window_mean(point_dict[pid]['time_windows']))
            if 540 <= mean_time <= 1260:
                filtered_pids.append(pid)
                filtered_time_means.append(mean_time)
        if not filtered_time_means:
            continue
        interval = float(sorted(filtered_time_means)[-1]) - float(sorted(filtered_time_means)[0])
        if interval < min_interval:
            # 找边界点（只在筛选后的点位中找）
            center = np.mean([features[pid] for pid in filtered_pids], axis=0)
            dists = [(np.linalg.norm(features[pid] - center), pid) for pid in filtered_pids]
            dists.sort(reverse=True)
            # 只尝试与最近组交换一次
            for _, move_pid in dists:
                move_time = float(main_time_window_mean(point_dict[move_pid]['time_windows']))
                # 找邻近组
                neighbor_candidates = [(h, np.linalg.norm(features[move_pid] - np.mean([features[pid] for pid in groups[h]], axis=0))) for h in groups if h != g]
                neighbor_g = min(neighbor_candidates)[0]
                # 只考虑邻近组中主时间窗均值在 9:00~21:00 的点位
                neighbor_times = [float(main_time_window_mean(point_dict[pid]['time_windows'])) for pid in groups[neighbor_g] if 540 <= float(main_time_window_mean(point_dict[pid]['time_windows'])) <= 1260]
                if not neighbor_times:
                    continue
                neighbor_interval = float(sorted(neighbor_times)[-1]) - float(sorted(neighbor_times)[0])
                # 如果交换后能提升两组的时间窗分散度，则交换
                if abs(move_time - np.mean(neighbor_times)) > abs(move_time - np.mean(filtered_time_means)):
                    groups[g].remove(move_pid)
                    groups[neighbor_g].append(move_pid)
                    break
    return groups

# 时间窗分散优化
groups = balance_time_window(groups, point_dict, gid_features, min_interval=120)

# 中文注释：均衡每组主时间窗均值在9:00~21:00的点位数量，尽量让每组这类点位数量接近

def balance_time_window_count(groups, point_dict, features, min_time=540, max_time=1260):
    # 统计每组主时间窗点位
    group_tw_pids = {}
    for g, pids in groups.items():
        group_tw_pids[g] = [pid for pid in pids if min_time <= float(main_time_window_mean(point_dict[pid]['time_windows'])) <= max_time]
    # 计算总数和目标均衡数
    total = sum(len(pids) for pids in group_tw_pids.values())
    n_group = len(groups)
    target = total // n_group
    # 按需调剂
    changed = True
    while changed:
        changed = False
        # 找出最多和最少的组
        sizes = {g: len(pids) for g, pids in group_tw_pids.items()}
        max_g = max(sizes, key=lambda x: sizes[x])
        min_g = min(sizes, key=lambda x: sizes[x])
        if sizes[max_g] - sizes[min_g] <= 1:
            break
        if sizes[min_g] >= target or sizes[max_g] <= target:
            break
        # 从max_g移一个点到min_g
        # 选择距离min_g质心最近的点
        if not group_tw_pids[max_g]:
            break
        min_center = np.mean([features[pid] for pid in groups[min_g]], axis=0)
        dists = [(np.linalg.norm(features[pid] - min_center), pid) for pid in group_tw_pids[max_g]]
        dists.sort()
        move_pid = dists[0][1]
        groups[max_g].remove(move_pid)
        groups[min_g].append(move_pid)
        group_tw_pids[max_g].remove(move_pid)
        group_tw_pids[min_g].append(move_pid)
        changed = True
    return groups

# 新增：主时间窗点位数量均衡
# 中文注释：对主时间窗均值在9:00~21:00的点位数量做均衡调剂
groups = balance_time_window_count(groups, point_dict, gid_features, min_time=540, max_time=1260)

# 新增：自动检测并修正所有分组的地理离群点
# 中文注释：自动检测并修正所有分组的地理离群点，将离群点分配到地理距离最近的其他分组

def balance_outliers(groups, point_dict, features, max_iter=5, std_factor=2):
    for _ in range(max_iter):
        moved = False
        for g, pids in list(groups.items()):
            if len(pids) <= 1:
                continue
            # 计算本组质心
            center = np.mean([features[pid] for pid in pids], axis=0)
            # 计算每个点到质心的距离
            dists = [(pid, np.linalg.norm(features[pid] - center)) for pid in pids]
            dist_vals = [d for _, d in dists]
            mean_dist = np.mean(dist_vals)
            std_dist = np.std(dist_vals)
            # 判定离群点：距离大于均值+std_factor*std
            outlier_pids = [pid for pid, d in dists if d > mean_dist + std_factor * std_dist]
            for pid in outlier_pids:
                # 找到距离该点最近的其他分组
                min_dist = float('inf')
                best_g = None
                for h, hpids in groups.items():
                    if h == g:
                        continue
                    h_center = np.mean([features[ppid] for ppid in hpids], axis=0)
                    d = np.linalg.norm(features[pid] - h_center)
                    if d < min_dist:
                        min_dist = d
                        best_g = h
                if best_g is not None:
                    groups[g].remove(pid)
                    groups[best_g].append(pid)
                    moved = True
        if not moved:
            break
    return groups

# 新增：自动检测并修正所有分组的地理离群点
groups = balance_outliers(groups, point_dict, gid_features, max_iter=5, std_factor=2)

# 中文注释：极端孤立点强制归组，将距离本组质心远且离其他组更近的点强制分配到最近组

def balance_extreme_isolated_points(groups, point_dict, features, threshold_km=2):
    def haversine(lon1, lat1, lon2, lat2):
        # 计算两经纬度点之间的球面距离（单位：公里）
        from math import radians, sin, cos, sqrt, atan2
        R = 6371.0
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        return R * c
    moved = True
    while moved:
        moved = False
        for g, pids in list(groups.items()):
            if len(pids) <= 1:
                continue
            # 计算本组质心
            center = np.mean([features[pid] for pid in pids], axis=0)
            for pid in list(pids):
                lng, lat = features[pid]
                dist_to_own = haversine(lng, lat, center[0], center[1])
                # 计算到所有组质心的距离
                min_dist = dist_to_own
                best_g = g
                for h, hpids in groups.items():
                    if h == g or len(hpids) == 0:
                        continue
                    h_center = np.mean([features[ppid] for ppid in hpids], axis=0)
                    d = haversine(lng, lat, h_center[0], h_center[1])
                    if d < min_dist:
                        min_dist = d
                        best_g = h
                # 如果到最近组的质心距离比本组小，且本组距离大于阈值，则强制归组
                if best_g != g and dist_to_own - min_dist > 0 and dist_to_own > threshold_km:
                    groups[g].remove(pid)
                    groups[best_g].append(pid)
                    moved = True
    return groups

# 新增：极端孤立点强制归组，阈值调整为20公里
groups = balance_extreme_isolated_points(groups, point_dict, gid_features, threshold_km=20)

# 4. 输出每组点位id和所有时间窗
for group_id, pids in groups.items():
    print(f"分组{group_id+1}:")
    for pid in pids:
        print(f"  点位ID: {pid}, 时间窗: {point_dict[pid]['time_windows']}")
    print(f"  本组点位数: {len(pids)}")
    print("---")


for group_id, pids in groups.items():
    # 中文注释：输出每组的点位id，格式为 id,id,id
    print(f"分组{group_id+1}:")
    print(",".join(str(pid) for pid in pids))
    print(f"  本组点位数: {len(pids)}")
    print("---")

# 中文注释：输出分组结果到 output.csv，表头为 pid,longitude,latitude,group_id
import csv
output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output', 'output.csv')
with open(output_path, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['pid', 'longitude', 'latitude', 'group_id'])
    for group_id, pids in groups.items():
        for pid in pids:
            lng = point_dict[pid]['lng']
            lat = point_dict[pid]['lat']
            writer.writerow([pid, lng, lat, group_id+1])