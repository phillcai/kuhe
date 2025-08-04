package main

import (
	"encoding/csv"
	"fmt"
	"log"
	"math"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
)

// TimeWindow 表示时间窗口
type TimeWindow struct {
	Start string
	End   string
}

// Point 表示一个点位
type Point struct {
	ID          int
	Longitude   float64
	Latitude    float64
	TimeWindows []TimeWindow
}

// Group 表示一个分组
type Group struct {
	ID     int
	Points []int // 点位ID列表
}

// TravelTimeMatrix 表示行驶时长矩阵
type TravelTimeMatrix struct {
	Times          [][]float64 // Times[i][j] 表示从点位i到点位j的行驶时长（分钟）
	Size           int         // 矩阵大小
	PointIDToIndex map[int]int // 点位ID到矩阵索引的映射
}

// 读取长格式的行驶时长数据并转换为矩阵
func readTravelTimeFromLongFormat(filePath string, pointDict map[int]*Point) (*TravelTimeMatrix, error) {
	file, err := os.Open(filePath)
	if err != nil {
		return nil, fmt.Errorf("无法打开行驶时长文件: %v", err)
	}
	defer file.Close()

	reader := csv.NewReader(file)
	records, err := reader.ReadAll()
	if err != nil {
		return nil, fmt.Errorf("读取CSV文件失败: %v", err)
	}

	if len(records) < 2 {
		return nil, fmt.Errorf("文件数据不足")
	}

	// 获取所有点位ID
	var allPointIDs []int
	for pid := range pointDict {
		allPointIDs = append(allPointIDs, pid)
	}
	sort.Ints(allPointIDs)

	// 创建点位ID到索引的映射
	pointIDToIndex := make(map[int]int)
	for i, pid := range allPointIDs {
		pointIDToIndex[pid] = i
	}

	nPoints := len(allPointIDs)
	matrix := &TravelTimeMatrix{
		Times:          make([][]float64, nPoints),
		Size:           nPoints,
		PointIDToIndex: pointIDToIndex,
	}

	// 初始化矩阵，所有值设为-1（表示无数据）
	for i := range matrix.Times {
		matrix.Times[i] = make([]float64, nPoints)
		for j := range matrix.Times[i] {
			matrix.Times[i][j] = -1
		}
	}

	// 设置对角线为0（同一点位）
	for i := 0; i < nPoints; i++ {
		matrix.Times[i][i] = 0
	}

	// 解析数据（跳过表头）
	for i := 1; i < len(records); i++ {
		record := records[i]
		if len(record) < 3 {
			continue
		}

		// 解析起始点位ID
		fromID, err := strconv.Atoi(strings.TrimSpace(record[0]))
		if err != nil {
			continue
		}

		// 解析目标点位ID
		toID, err := strconv.Atoi(strings.TrimSpace(record[1]))
		if err != nil {
			continue
		}

		// 解析行驶时长
		durationStr := strings.TrimSpace(record[2])
		// 处理带逗号的数字格式
		durationStr = strings.ReplaceAll(durationStr, ",", "")
		duration, err := strconv.ParseFloat(durationStr, 64)
		if err != nil {
			continue
		}

		// 检查点位ID是否在有效范围内
		fromIndex, fromExists := pointIDToIndex[fromID]
		toIndex, toExists := pointIDToIndex[toID]
		if fromExists && toExists {
			matrix.Times[fromIndex][toIndex] = duration
		}
	}

	return matrix, nil
}

// 读取行驶时长数据
func readTravelTimeFromCSV(filePath string) (*TravelTimeMatrix, error) {
	file, err := os.Open(filePath)
	if err != nil {
		return nil, fmt.Errorf("无法打开行驶时长文件: %v", err)
	}
	defer file.Close()

	reader := csv.NewReader(file)
	records, err := reader.ReadAll()
	if err != nil {
		return nil, fmt.Errorf("读取CSV文件失败: %v", err)
	}

	if len(records) < 2 {
		return nil, fmt.Errorf("文件数据不足")
	}

	// 获取点位数量（假设第一行是表头，第一列是点位ID）
	nPoints := len(records) - 1
	matrix := &TravelTimeMatrix{
		Times:          make([][]float64, nPoints),
		Size:           nPoints,
		PointIDToIndex: make(map[int]int),
	}

	// 初始化矩阵
	for i := range matrix.Times {
		matrix.Times[i] = make([]float64, nPoints)
	}

	// 初始化点位ID映射（假设第一列是点位ID）
	for i := 1; i < len(records); i++ {
		record := records[i]
		if len(record) > 0 {
			if pointID, err := strconv.Atoi(strings.TrimSpace(record[0])); err == nil {
				matrix.PointIDToIndex[pointID] = i - 1
			}
		}
	}

	// 解析数据（跳过表头）
	for i := 1; i < len(records); i++ {
		record := records[i]
		if len(record) < nPoints+1 {
			continue
		}

		// 解析当前行点位ID
		_, err = strconv.Atoi(record[0])
		if err != nil {
			continue
		}

		// 解析到各个点位的行驶时长
		for j := 1; j < len(record) && j <= nPoints; j++ {
			timeStr := strings.TrimSpace(record[j])
			if timeStr == "" || timeStr == "-" {
				matrix.Times[i-1][j-1] = -1 // 表示无数据
				continue
			}

			travelTime, err := strconv.ParseFloat(timeStr, 64)
			if err != nil {
				matrix.Times[i-1][j-1] = -1 // 解析失败设为-1
				continue
			}
			matrix.Times[i-1][j-1] = travelTime
		}
	}

	return matrix, nil
}

// 获取两点间的行驶时长
func (tm *TravelTimeMatrix) GetTravelTime(fromID, toID int) float64 {
	fromIndex, fromExists := tm.PointIDToIndex[fromID]
	toIndex, toExists := tm.PointIDToIndex[toID]

	if !fromExists || !toExists || fromIndex < 0 || fromIndex >= tm.Size || toIndex < 0 || toIndex >= tm.Size {
		return -1
	}
	return tm.Times[fromIndex][toIndex]
}

// 标准化行驶时长数据
func normalizeTravelTimes(times []float64) []float64 {
	if len(times) == 0 {
		return times
	}

	// 过滤掉无效数据（-1）
	var validTimes []float64
	for _, t := range times {
		if t >= 0 {
			validTimes = append(validTimes, t)
		}
	}

	if len(validTimes) == 0 {
		return times
	}

	// 计算均值和标准差
	mean := 0.0
	for _, t := range validTimes {
		mean += t
	}
	mean /= float64(len(validTimes))

	variance := 0.0
	for _, t := range validTimes {
		variance += (t - mean) * (t - mean)
	}
	variance /= float64(len(validTimes))
	std := math.Sqrt(variance)

	// 标准化
	normalized := make([]float64, len(times))
	for i, t := range times {
		if t < 0 {
			normalized[i] = 0 // 无效数据设为0
		} else {
			if std > 0 {
				normalized[i] = (t - mean) / std
			} else {
				normalized[i] = 0
			}
		}
	}

	return normalized
}

// 基于行驶时长的距离计算函数
func travelTimeDistance(fromID, toID int, travelMatrix *TravelTimeMatrix) float64 {
	if travelMatrix == nil {
		return 0
	}

	travelTime := travelMatrix.GetTravelTime(fromID, toID)
	if travelTime < 0 {
		// 如果没有行驶时长数据，返回一个较大的默认值
		return 1000.0
	}

	return travelTime
}

// 计算基于行驶时长的聚类特征
func calculateTravelTimeFeatures(pointDict map[int]*Point, travelMatrix *TravelTimeMatrix) (map[int][]float64, error) {
	features := make(map[int][]float64)

	// 为每个点位计算特征向量
	for pid := range pointDict {
		// 特征向量包含：经度、纬度、平均行驶时长
		point := pointDict[pid]

		// 计算到所有其他点位的平均行驶时长
		totalTime := 0.0
		validCount := 0

		for otherPid := range pointDict {
			if otherPid == pid {
				continue
			}

			travelTime := travelMatrix.GetTravelTime(pid, otherPid)
			if travelTime >= 0 {
				totalTime += travelTime
				validCount++
			}
		}

		avgTravelTime := 0.0
		if validCount > 0 {
			avgTravelTime = totalTime / float64(validCount)
		}

		// 特征向量：[经度, 纬度, 平均行驶时长]
		features[pid] = []float64{
			point.Longitude,
			point.Latitude,
			avgTravelTime,
		}
	}

	return features, nil
}

// 读取需要补货的点位列表
func readRecallPoints(filePath string) (map[int]bool, error) {
	file, err := os.Open(filePath)
	if err != nil {
		return nil, fmt.Errorf("无法打开补货点位文件: %v", err)
	}
	defer file.Close()

	reader := csv.NewReader(file)
	records, err := reader.ReadAll()
	if err != nil {
		return nil, fmt.Errorf("读取CSV文件失败: %v", err)
	}

	recallPoints := make(map[int]bool)

	// 跳过表头
	for i := 1; i < len(records); i++ {
		record := records[i]
		if len(record) < 1 {
			continue
		}

		// 解析点位ID
		id, err := strconv.Atoi(strings.TrimSpace(record[0]))
		if err != nil {
			continue
		}

		recallPoints[id] = true
	}

	return recallPoints, nil
}

// 考虑补货点位优先级的K-means聚类（基于行驶时长）
func kmeansWithTravelTimeAndRecallPriority(features [][]float64, pidList []int, nClusters int, maxIterations int, travelMatrix *TravelTimeMatrix, recallPoints map[int]bool) []int {
	if len(features) == 0 || nClusters <= 0 {
		return []int{}
	}

	// 初始化聚类中心
	centers := make([][]float64, nClusters)
	for i := 0; i < nClusters; i++ {
		centers[i] = make([]float64, len(features[0]))
		copy(centers[i], features[i%len(features)])
	}

	labels := make([]int, len(features))
	prevLabels := make([]int, len(features))

	// 优先分配补货点位到最近的聚类中心
	fmt.Println("优先分配补货点位...")
	for i, pid := range pidList {
		if recallPoints[pid] {
			minDist := math.Inf(1)
			bestCluster := 0
			for j := 0; j < nClusters; j++ {
				dist := travelTimeBasedDistance(features[i], centers[j], pid, pidList[0], travelMatrix)
				if dist < minDist {
					minDist = dist
					bestCluster = j
				}
			}
			labels[i] = bestCluster
			prevLabels[i] = bestCluster
		}
	}

	// 迭代优化
	for iter := 0; iter < maxIterations; iter++ {
		// 分配非补货点位到最近的聚类中心
		for i, pid := range pidList {
			if !recallPoints[pid] {
				minDist := math.Inf(1)
				bestCluster := 0
				for j := 0; j < nClusters; j++ {
					dist := travelTimeBasedDistance(features[i], centers[j], pid, pidList[0], travelMatrix)
					if dist < minDist {
						minDist = dist
						bestCluster = j
					}
				}
				labels[i] = bestCluster
			}
		}

		// 检查收敛
		converged := true
		for i := range labels {
			if labels[i] != prevLabels[i] {
				converged = false
				break
			}
		}
		if converged {
			break
		}

		// 更新聚类中心
		for i := range centers {
			for j := range centers[i] {
				centers[i][j] = 0
			}
		}
		counts := make([]int, nClusters)

		for i, label := range labels {
			for j, val := range features[i] {
				centers[label][j] += val
			}
			counts[label]++
		}

		for i := range centers {
			if counts[i] > 0 {
				for j := range centers[i] {
					centers[i][j] /= float64(counts[i])
				}
			}
		}

		copy(prevLabels, labels)
	}

	return labels
}

// 考虑补货点位优先级的传统K-means聚类
func kmeansWithRecallPriority(features [][]float64, pidList []int, nClusters int, maxIterations int, recallPoints map[int]bool) []int {
	if len(features) == 0 || nClusters <= 0 {
		return []int{}
	}

	// 初始化聚类中心
	centers := make([][]float64, nClusters)
	for i := 0; i < nClusters; i++ {
		centers[i] = make([]float64, len(features[0]))
		copy(centers[i], features[i%len(features)])
	}

	labels := make([]int, len(features))
	prevLabels := make([]int, len(features))

	// 优先分配补货点位到最近的聚类中心
	fmt.Println("优先分配补货点位...")
	for i, pid := range pidList {
		if recallPoints[pid] {
			minDist := math.Inf(1)
			bestCluster := 0
			for j := 0; j < nClusters; j++ {
				dist := euclideanDistance(features[i], centers[j])
				if dist < minDist {
					minDist = dist
					bestCluster = j
				}
			}
			labels[i] = bestCluster
			prevLabels[i] = bestCluster
		}
	}

	// 迭代优化
	for iter := 0; iter < maxIterations; iter++ {
		// 分配非补货点位到最近的聚类中心
		for i, pid := range pidList {
			if !recallPoints[pid] {
				minDist := math.Inf(1)
				bestCluster := 0
				for j := 0; j < nClusters; j++ {
					dist := euclideanDistance(features[i], centers[j])
					if dist < minDist {
						minDist = dist
						bestCluster = j
					}
				}
				labels[i] = bestCluster
			}
		}

		// 检查收敛
		converged := true
		for i := range labels {
			if labels[i] != prevLabels[i] {
				converged = false
				break
			}
		}
		if converged {
			break
		}

		// 更新聚类中心
		for i := range centers {
			for j := range centers[i] {
				centers[i][j] = 0
			}
		}
		counts := make([]int, nClusters)

		for i, label := range labels {
			for j, val := range features[i] {
				centers[label][j] += val
			}
			counts[label]++
		}

		for i := range centers {
			if counts[i] > 0 {
				for j := range centers[i] {
					centers[i][j] /= float64(counts[i])
				}
			}
		}

		copy(prevLabels, labels)
	}

	return labels
}

// 数量均衡调整
func balanceGroupSize(groups map[int][]int, features map[int][]float64, targetSize int) map[int][]int {
	changed := true
	for changed {
		changed = false

		// 找出最大和最小的组
		var maxG, minG int
		maxSize := -1
		minSize := math.MaxInt32
		for g, pids := range groups {
			size := len(pids)
			if size > maxSize {
				maxSize = size
				maxG = g
			}
			if size < minSize {
				minSize = size
				minG = g
			}
		}

		if maxSize-minSize <= 1 {
			break
		}

		// 计算最大组质心
		var maxCenter []float64
		if len(groups[maxG]) > 0 {
			maxCenter = make([]float64, len(features[groups[maxG][0]]))
			for _, pid := range groups[maxG] {
				feature := features[pid]
				for i, val := range feature {
					maxCenter[i] += val
				}
			}
			for i := range maxCenter {
				maxCenter[i] /= float64(len(groups[maxG]))
			}
		}

		// 找最大组中距离质心最远的点
		var movePid int
		maxDist := -1.0
		for _, pid := range groups[maxG] {
			dist := euclideanDistance(features[pid], maxCenter)
			if dist > maxDist {
				maxDist = dist
				movePid = pid
			}
		}

		// 移动点到最小组
		for i, pid := range groups[maxG] {
			if pid == movePid {
				groups[maxG] = append(groups[maxG][:i], groups[maxG][i+1:]...)
				break
			}
		}
		groups[minG] = append(groups[minG], movePid)
		changed = true
	}

	return groups
}

// 时间窗分散优化
func balanceTimeWindow(groups map[int][]int, pointDict map[int]*Point, features map[int][]float64, minInterval float64) map[int][]int {
	for g, pids := range groups {
		// 只筛选主时间窗均值在 9:00~21:00 的点位
		var filteredPids []int
		var filteredTimeMeans []float64
		for _, pid := range pids {
			meanTime := mainTimeWindowMean(pointDict[pid].TimeWindows)
			if meanTime >= 540 && meanTime <= 1260 {
				filteredPids = append(filteredPids, pid)
				filteredTimeMeans = append(filteredTimeMeans, meanTime)
			}
		}

		if len(filteredTimeMeans) == 0 {
			continue
		}

		sort.Float64s(filteredTimeMeans)
		interval := filteredTimeMeans[len(filteredTimeMeans)-1] - filteredTimeMeans[0]

		if interval < minInterval {
			// 找边界点
			var center []float64
			if len(filteredPids) > 0 {
				center = make([]float64, len(features[filteredPids[0]]))
				for _, pid := range filteredPids {
					feature := features[pid]
					for i, val := range feature {
						center[i] += val
					}
				}
				for i := range center {
					center[i] /= float64(len(filteredPids))
				}
			}

			// 按距离排序
			type distPoint struct {
				dist float64
				pid  int
			}
			var dists []distPoint
			for _, pid := range filteredPids {
				dist := euclideanDistance(features[pid], center)
				dists = append(dists, distPoint{dist: dist, pid: pid})
			}
			sort.Slice(dists, func(i, j int) bool {
				return dists[i].dist > dists[j].dist
			})

			// 尝试与最近组交换
			for _, dp := range dists {
				movePid := dp.pid
				moveTime := mainTimeWindowMean(pointDict[movePid].TimeWindows)

				// 找邻近组
				var neighborG int
				minDist := math.Inf(1)
				for h, hpids := range groups {
					if h == g {
						continue
					}
					if len(hpids) == 0 {
						continue
					}
					hCenter := make([]float64, len(features[hpids[0]]))
					for _, hpid := range hpids {
						feature := features[hpid]
						for i, val := range feature {
							hCenter[i] += val
						}
					}
					for i := range hCenter {
						hCenter[i] /= float64(len(hpids))
					}
					dist := euclideanDistance(features[movePid], hCenter)
					if dist < minDist {
						minDist = dist
						neighborG = h
					}
				}

				// 只考虑邻近组中主时间窗均值在 9:00~21:00 的点位
				var neighborTimes []float64
				for _, pid := range groups[neighborG] {
					meanTime := mainTimeWindowMean(pointDict[pid].TimeWindows)
					if meanTime >= 540 && meanTime <= 1260 {
						neighborTimes = append(neighborTimes, meanTime)
					}
				}

				if len(neighborTimes) == 0 {
					continue
				}

				sort.Float64s(neighborTimes)

				// 如果交换后能提升两组的时间窗分散度，则交换
				neighborMean := 0.0
				for _, t := range neighborTimes {
					neighborMean += t
				}
				neighborMean /= float64(len(neighborTimes))

				filteredMean := 0.0
				for _, t := range filteredTimeMeans {
					filteredMean += t
				}
				filteredMean /= float64(len(filteredTimeMeans))

				if math.Abs(moveTime-neighborMean) > math.Abs(moveTime-filteredMean) {
					// 从原组移除
					for i, pid := range groups[g] {
						if pid == movePid {
							groups[g] = append(groups[g][:i], groups[g][i+1:]...)
							break
						}
					}
					// 添加到邻近组
					groups[neighborG] = append(groups[neighborG], movePid)
					break
				}
			}
		}
	}

	return groups
}

// 均衡每组主时间窗点位的数量
func balanceTimeWindowCount(groups map[int][]int, pointDict map[int]*Point, features map[int][]float64, minTime, maxTime float64) map[int][]int {
	// 统计每组主时间窗点位
	groupTwPids := make(map[int][]int)
	for g, pids := range groups {
		for _, pid := range pids {
			meanTime := mainTimeWindowMean(pointDict[pid].TimeWindows)
			if meanTime >= minTime && meanTime <= maxTime {
				groupTwPids[g] = append(groupTwPids[g], pid)
			}
		}
	}

	// 计算总数和目标均衡数
	total := 0
	for _, pids := range groupTwPids {
		total += len(pids)
	}
	nGroup := len(groups)
	if nGroup == 0 {
		return groups // 如果没有分组，直接返回
	}
	target := total / nGroup

	// 按需调剂
	changed := true
	for changed {
		changed = false

		// 找出最多和最少的组
		var maxG, minG int
		maxSize := -1
		minSize := math.MaxInt32
		for g, pids := range groupTwPids {
			size := len(pids)
			if size > maxSize {
				maxSize = size
				maxG = g
			}
			if size < minSize {
				minSize = size
				minG = g
			}
		}

		if maxSize-minSize <= 1 {
			break
		}
		if minSize >= target || maxSize <= target {
			break
		}

		// 从maxG移一个点到minG
		if len(groupTwPids[maxG]) == 0 {
			break
		}

		// 选择距离minG质心最近的点
		if len(groupTwPids[minG]) == 0 || len(groups[minG]) == 0 {
			break
		}

		minCenter := make([]float64, len(features[groupTwPids[minG][0]]))
		for _, pid := range groups[minG] {
			feature := features[pid]
			for i, val := range feature {
				minCenter[i] += val
			}
		}
		for i := range minCenter {
			minCenter[i] /= float64(len(groups[minG]))
		}

		var movePid int
		minDist := math.Inf(1)
		for _, pid := range groupTwPids[maxG] {
			dist := euclideanDistance(features[pid], minCenter)
			if dist < minDist {
				minDist = dist
				movePid = pid
			}
		}

		// 移动点
		for i, pid := range groups[maxG] {
			if pid == movePid {
				groups[maxG] = append(groups[maxG][:i], groups[maxG][i+1:]...)
				break
			}
		}
		groups[minG] = append(groups[minG], movePid)

		// 更新groupTwPids
		for i, pid := range groupTwPids[maxG] {
			if pid == movePid {
				groupTwPids[maxG] = append(groupTwPids[maxG][:i], groupTwPids[maxG][i+1:]...)
				break
			}
		}
		groupTwPids[minG] = append(groupTwPids[minG], movePid)

		changed = true
	}

	return groups
}

// 自动检测并修正所有分组的地理离群点
func balanceOutliers(groups map[int][]int, pointDict map[int]*Point, features map[int][]float64, maxIter int, stdFactor float64) map[int][]int {
	for iter := 0; iter < maxIter; iter++ {
		moved := false
		for g, pids := range groups {
			if len(pids) <= 1 {
				continue
			}

			// 计算本组质心
			center := make([]float64, len(features[pids[0]]))
			for _, pid := range pids {
				feature := features[pid]
				for i, val := range feature {
					center[i] += val
				}
			}
			for i := range center {
				center[i] /= float64(len(pids))
			}

			// 计算每个点到质心的距离
			var dists []float64
			for _, pid := range pids {
				dist := euclideanDistance(features[pid], center)
				dists = append(dists, dist)
			}

			// 计算均值和标准差
			meanDist := 0.0
			for _, d := range dists {
				meanDist += d
			}
			meanDist /= float64(len(dists))

			variance := 0.0
			for _, d := range dists {
				variance += (d - meanDist) * (d - meanDist)
			}
			variance /= float64(len(dists))
			stdDist := math.Sqrt(variance)

			// 判定离群点
			var outlierPids []int
			for i, pid := range pids {
				if dists[i] > meanDist+stdFactor*stdDist {
					outlierPids = append(outlierPids, pid)
				}
			}

			for _, pid := range outlierPids {
				// 找到距离该点最近的其他分组
				minDist := math.Inf(1)
				var bestG int
				for h, hpids := range groups {
					if h == g {
						continue
					}
					if len(hpids) == 0 {
						continue
					}
					hCenter := make([]float64, len(features[hpids[0]]))
					for _, hpid := range hpids {
						feature := features[hpid]
						for i, val := range feature {
							hCenter[i] += val
						}
					}
					for i := range hCenter {
						hCenter[i] /= float64(len(hpids))
					}
					d := euclideanDistance(features[pid], hCenter)
					if d < minDist {
						minDist = d
						bestG = h
					}
				}

				// 移动点
				for i, p := range groups[g] {
					if p == pid {
						groups[g] = append(groups[g][:i], groups[g][i+1:]...)
						break
					}
				}
				groups[bestG] = append(groups[bestG], pid)
				moved = true
			}
		}

		if !moved {
			break
		}
	}

	return groups
}

// 极端孤立点强制归组
func balanceExtremeIsolatedPoints(groups map[int][]int, pointDict map[int]*Point, features map[int][]float64, thresholdKm float64) map[int][]int {
	moved := true
	for moved {
		moved = false
		for g, pids := range groups {
			if len(pids) <= 1 {
				continue
			}

			// 计算本组质心
			center := make([]float64, len(features[pids[0]]))
			for _, pid := range pids {
				feature := features[pid]
				for i, val := range feature {
					center[i] += val
				}
			}
			for i := range center {
				center[i] /= float64(len(pids))
			}

			for _, pid := range pids {
				lng, lat := features[pid][0], features[pid][1]
				distToOwn := haversine(lng, lat, center[0], center[1])

				// 计算到所有组质心的距离
				minDist := distToOwn
				bestG := g
				for h, hpids := range groups {
					if h == g || len(hpids) == 0 {
						continue
					}
					hCenter := make([]float64, len(features[hpids[0]]))
					for _, hpid := range hpids {
						feature := features[hpid]
						for i, val := range feature {
							hCenter[i] += val
						}
					}
					for i := range hCenter {
						hCenter[i] /= float64(len(hpids))
					}
					d := haversine(lng, lat, hCenter[0], hCenter[1])
					if d < minDist {
						minDist = d
						bestG = h
					}
				}

				// 如果到最近组的质心距离比本组小，且本组距离大于阈值，则强制归组
				if bestG != g && distToOwn-minDist > 0 && distToOwn > thresholdKm {
					// 从原组移除
					for i, p := range groups[g] {
						if p == pid {
							groups[g] = append(groups[g][:i], groups[g][i+1:]...)
							break
						}
					}
					// 添加到最近组
					groups[bestG] = append(groups[bestG], pid)
					moved = true
				}
			}
		}
	}

	return groups
}

// 输出分组结果到CSV文件
func writeOutputToCSV(groups map[int][]int, pointDict map[int]*Point, outputPath string) error {
	file, err := os.Create(outputPath)
	if err != nil {
		return err
	}
	defer file.Close()

	writer := csv.NewWriter(file)
	defer writer.Flush()

	// 写入表头
	err = writer.Write([]string{"pid", "longitude", "latitude", "group_id"})
	if err != nil {
		return err
	}

	// 写入数据
	for groupID, pids := range groups {
		for _, pid := range pids {
			point := pointDict[pid]
			row := []string{
				strconv.Itoa(pid),
				fmt.Sprintf("%f", point.Longitude),
				fmt.Sprintf("%f", point.Latitude),
				strconv.Itoa(groupID + 1),
			}
			err = writer.Write(row)
			if err != nil {
				return err
			}
		}
	}

	return nil
}

// 平衡补货点位在各组中的分布（考虑地理位置和总数量均衡）
func balanceRecallPoints(groups map[int][]int, recallPoints map[int]bool, nClusters int, pointDict map[int]*Point, gidFeatures map[int][]float64) map[int][]int {
	// 统计各组中的补货点位数量和总点数
	recallCounts := make([]int, nClusters)
	totalCounts := make([]int, nClusters)
	for g, pids := range groups {
		totalCounts[g] = len(pids)
		for _, pid := range pids {
			if recallPoints[pid] {
				recallCounts[g]++
			}
		}
	}

	// 计算目标分布
	totalRecall := 0
	totalPoints := 0
	for _, count := range recallCounts {
		totalRecall += count
	}
	for _, count := range totalCounts {
		totalPoints += count
	}

	targetTotalPerGroup := totalPoints / nClusters
	extraTotal := totalPoints % nClusters

	// 如果分布已经相对均匀，直接返回
	maxRecall := 0
	minRecall := totalRecall
	maxTotal := 0
	minTotal := totalPoints
	for _, count := range recallCounts {
		if count > maxRecall {
			maxRecall = count
		}
		if count < minRecall {
			minRecall = count
		}
	}
	for _, count := range totalCounts {
		if count > maxTotal {
			maxTotal = count
		}
		if count < minTotal {
			minTotal = count
		}
	}

	// 如果补货点位分布均匀且总点数分布也相对均匀，直接返回
	if maxRecall-minRecall <= 1 && maxTotal-minTotal <= 6 {
		return groups
	}

	// 尝试重新分配补货点位
	fmt.Println("平衡补货点位分布（考虑地理位置和总数量均衡）...")

	// 找出需要调整的组（优先考虑总点数差异）
	overGroups := make([]int, 0)
	underGroups := make([]int, 0)

	for g := 0; g < nClusters; g++ {
		targetTotal := targetTotalPerGroup
		if g < extraTotal {
			targetTotal++
		}
		if totalCounts[g] > targetTotal+6 { // 允许6个点位的误差
			overGroups = append(overGroups, g)
		} else if totalCounts[g] < targetTotal-6 {
			underGroups = append(underGroups, g)
		}
	}

	// 从过多的组向过少的组转移点位（优先转移补货点位）
	for _, overG := range overGroups {
		if len(underGroups) == 0 {
			break
		}

		// 找出当前组中的补货点位
		recallPids := make([]int, 0)
		for _, pid := range groups[overG] {
			if recallPoints[pid] {
				recallPids = append(recallPids, pid)
			}
		}

		// 计算需要转移的数量
		targetTotal := targetTotalPerGroup
		if overG < extraTotal {
			targetTotal++
		}
		needToMove := totalCounts[overG] - targetTotal

		// 转移点位
		moved := 0
		for _, underG := range underGroups {
			if moved >= needToMove {
				break
			}

			targetTotal := targetTotalPerGroup
			if underG < extraTotal {
				targetTotal++
			}
			canAccept := targetTotal - totalCounts[underG]

			// 计算目标组的中心
			targetCenter := make([]float64, len(gidFeatures[groups[underG][0]]))
			for _, pid := range groups[underG] {
				feature := gidFeatures[pid]
				for i, val := range feature {
					targetCenter[i] += val
				}
			}
			for i := range targetCenter {
				targetCenter[i] /= float64(len(groups[underG]))
			}

			// 优先转移补货点位
			for i := 0; i < canAccept && moved < needToMove && len(recallPids) > 0; i++ {
				// 找到距离目标组中心最近的补货点位
				minDist := math.Inf(1)
				bestIndex := 0
				for j, pid := range recallPids {
					dist := euclideanDistance(gidFeatures[pid], targetCenter)
					if dist < minDist {
						minDist = dist
						bestIndex = j
					}
				}

				pid := recallPids[bestIndex]
				// 从recallPids中移除
				recallPids = append(recallPids[:bestIndex], recallPids[bestIndex+1:]...)

				// 从原组移除
				for j, p := range groups[overG] {
					if p == pid {
						groups[overG] = append(groups[overG][:j], groups[overG][j+1:]...)
						break
					}
				}

				// 添加到目标组
				groups[underG] = append(groups[underG], pid)

				// 更新计数
				recallCounts[overG]--
				recallCounts[underG]++
				totalCounts[overG]--
				totalCounts[underG]++
				moved++

				fmt.Printf("补货点位 %d 从分组 %d 转移到分组 %d (距离: %.2f)\n", pid, overG+1, underG+1, minDist)
			}

			// 如果还需要转移更多点位，转移普通点位
			if moved < needToMove && canAccept > 0 {
				// 找出当前组中的普通点位
				normalPids := make([]int, 0)
				for _, pid := range groups[overG] {
					if !recallPoints[pid] {
						normalPids = append(normalPids, pid)
					}
				}

				for i := 0; i < canAccept && moved < needToMove && len(normalPids) > 0; i++ {
					// 找到距离目标组中心最近的普通点位
					minDist := math.Inf(1)
					bestIndex := 0
					for j, pid := range normalPids {
						dist := euclideanDistance(gidFeatures[pid], targetCenter)
						if dist < minDist {
							minDist = dist
							bestIndex = j
						}
					}

					pid := normalPids[bestIndex]
					// 从normalPids中移除
					normalPids = append(normalPids[:bestIndex], normalPids[bestIndex+1:]...)

					// 从原组移除
					for j, p := range groups[overG] {
						if p == pid {
							groups[overG] = append(groups[overG][:j], groups[overG][j+1:]...)
							break
						}
					}

					// 添加到目标组
					groups[underG] = append(groups[underG], pid)

					// 更新计数
					totalCounts[overG]--
					totalCounts[underG]++
					moved++

					fmt.Printf("普通点位 %d 从分组 %d 转移到分组 %d (距离: %.2f)\n", pid, overG+1, underG+1, minDist)
				}
			}
		}
	}

	return groups
}

// 优化地理集中性，减少跨区域分布
func optimizeGeographicConcentration(groups map[int][]int, nClusters int, pointDict map[int]*Point, gidFeatures map[int][]float64) map[int][]int {
	fmt.Println("优化地理集中性，减少跨区域分布...")

	// 计算目标数量
	totalPoints := 0
	for _, pids := range groups {
		totalPoints += len(pids)
	}
	targetPerGroup := totalPoints / nClusters
	extraPoints := totalPoints % nClusters

	// 计算每个组的中心
	groupCenters := make(map[int][]float64)
	for g, pids := range groups {
		if len(pids) == 0 {
			continue
		}

		center := make([]float64, len(gidFeatures[pids[0]]))
		for _, pid := range pids {
			feature := gidFeatures[pid]
			for i, val := range feature {
				center[i] += val
			}
		}
		for i := range center {
			center[i] /= float64(len(pids))
		}
		groupCenters[g] = center
	}

	// 找出地理分散的点位并重新分配
	maxIterations := 2 // 减少迭代次数，避免过度调整
	for iter := 0; iter < maxIterations; iter++ {
		changes := 0

		for g, pids := range groups {
			if len(pids) <= 1 {
				continue
			}

			center := groupCenters[g]

			// 找出距离组中心最远的点位
			maxDist := 0.0
			farthestPid := -1
			for _, pid := range pids {
				dist := euclideanDistance(gidFeatures[pid], center)
				if dist > maxDist {
					maxDist = dist
					farthestPid = pid
				}
			}

			// 如果最远距离超过阈值，尝试重新分配
			if maxDist > 0.12 { // 调整阈值，平衡地理集中性和数量均衡
				// 找到距离这个点位最近的其他组
				minDist := math.Inf(1)
				bestGroup := -1
				for otherG, otherCenter := range groupCenters {
					if otherG == g {
						continue
					}

					// 检查目标组的容量限制
					target := targetPerGroup
					if otherG < extraPoints {
						target++
					}
					if len(groups[otherG]) >= target+3 { // 允许3个点位的误差
						continue
					}

					dist := euclideanDistance(gidFeatures[farthestPid], otherCenter)
					if dist < minDist {
						minDist = dist
						bestGroup = otherG
					}
				}

				// 如果找到更合适的组，且距离差异足够大，则转移
				if bestGroup != -1 && minDist < maxDist*0.75 { // 调整转移条件
					// 从原组移除
					for i, pid := range groups[g] {
						if pid == farthestPid {
							groups[g] = append(groups[g][:i], groups[g][i+1:]...)
							break
						}
					}

					// 添加到新组
					groups[bestGroup] = append(groups[bestGroup], farthestPid)

					// 更新组中心
					updateGroupCenter(groupCenters, g, groups[g], gidFeatures)
					updateGroupCenter(groupCenters, bestGroup, groups[bestGroup], gidFeatures)

					changes++
					fmt.Printf("点位 %d 从分组 %d 转移到分组 %d (距离优化: %.2f -> %.2f)\n",
						farthestPid, g+1, bestGroup+1, maxDist, minDist)
				}
			}
		}

		// 如果没有变化，提前结束
		if changes == 0 {
			break
		}
	}

	return groups
}

// 更新组中心
func updateGroupCenter(centers map[int][]float64, groupID int, pids []int, gidFeatures map[int][]float64) {
	if len(pids) == 0 {
		return
	}

	center := make([]float64, len(gidFeatures[pids[0]]))
	for _, pid := range pids {
		feature := gidFeatures[pid]
		for i, val := range feature {
			center[i] += val
		}
	}
	for i := range center {
		center[i] /= float64(len(pids))
	}
	centers[groupID] = center
}

// 最终数量均衡调整（考虑地理集中性）
func finalBalanceGroupSize(groups map[int][]int, features map[int][]float64, targetSize int) map[int][]int {
	fmt.Println("执行最终数量均衡调整（考虑地理集中性）...")

	// 计算每个组的中心
	groupCenters := make(map[int][]float64)
	for g, pids := range groups {
		if len(pids) == 0 {
			continue
		}

		center := make([]float64, len(features[pids[0]]))
		for _, pid := range pids {
			feature := features[pid]
			for i, val := range feature {
				center[i] += val
			}
		}
		for i := range center {
			center[i] /= float64(len(pids))
		}
		groupCenters[g] = center
	}

	// 找出过多和过少的组
	overGroups := make([]int, 0)
	underGroups := make([]int, 0)

	for g, pids := range groups {
		if len(pids) > targetSize+2 {
			overGroups = append(overGroups, g)
		} else if len(pids) < targetSize-2 {
			underGroups = append(underGroups, g)
		}
	}

	// 从过多的组向过少的组转移点位
	for _, overG := range overGroups {
		if len(underGroups) == 0 {
			break
		}

		needToMove := len(groups[overG]) - targetSize
		moved := 0

		for _, underG := range underGroups {
			if moved >= needToMove {
				break
			}

			canAccept := targetSize - len(groups[underG])
			if canAccept <= 0 {
				continue
			}

			// 计算目标组中心
			targetCenter := groupCenters[underG]

			// 找出距离目标组中心最近的点位进行转移
			for i := 0; i < canAccept && moved < needToMove && len(groups[overG]) > 0; i++ {
				minDist := math.Inf(1)
				bestIndex := 0

				for j, pid := range groups[overG] {
					dist := euclideanDistance(features[pid], targetCenter)
					if dist < minDist {
						minDist = dist
						bestIndex = j
					}
				}

				pid := groups[overG][bestIndex]
				// 从原组移除
				groups[overG] = append(groups[overG][:bestIndex], groups[overG][bestIndex+1:]...)

				// 添加到目标组
				groups[underG] = append(groups[underG], pid)

				// 更新组中心
				updateGroupCenter(groupCenters, overG, groups[overG], features)
				updateGroupCenter(groupCenters, underG, groups[underG], features)

				moved++
				fmt.Printf("最终均衡：点位 %d 从分组 %d 转移到分组 %d (距离: %.2f)\n",
					pid, overG+1, underG+1, minDist)
			}
		}
	}

	return groups
}

// 标准K-means聚类（不考虑补货点位优先级）
func kmeans(features [][]float64, pidList []int, nClusters int, maxIterations int) []int {
	// 随机初始化聚类中心
	centers := make([][]float64, nClusters)
	for i := 0; i < nClusters; i++ {
		centers[i] = make([]float64, len(features[0]))
		for j := range centers[i] {
			centers[i][j] = features[i][j]
		}
	}

	labels := make([]int, len(features))

	for iter := 0; iter < maxIterations; iter++ {
		// 分配点到最近的中心
		changed := false
		for i, feature := range features {
			minDist := math.Inf(1)
			bestLabel := 0

			for j, center := range centers {
				dist := euclideanDistance(feature, center)
				if dist < minDist {
					minDist = dist
					bestLabel = j
				}
			}

			if labels[i] != bestLabel {
				labels[i] = bestLabel
				changed = true
			}
		}

		if !changed {
			break
		}

		// 更新中心
		for i := range centers {
			for j := range centers[i] {
				centers[i][j] = 0
			}
		}

		counts := make([]int, nClusters)
		for i, label := range labels {
			for j := range features[i] {
				centers[label][j] += features[i][j]
			}
			counts[label]++
		}

		for i := range centers {
			if counts[i] > 0 {
				for j := range centers[i] {
					centers[i][j] /= float64(counts[i])
				}
			}
		}
	}

	return labels
}

// 基于行驶时长的K-means聚类（不考虑补货点位优先级）
func kmeansWithTravelTime(features [][]float64, pidList []int, nClusters int, maxIterations int, travelMatrix *TravelTimeMatrix) []int {
	// 随机初始化聚类中心
	centers := make([][]float64, nClusters)
	for i := 0; i < nClusters; i++ {
		centers[i] = make([]float64, len(features[0]))
		for j := range centers[i] {
			centers[i][j] = features[i][j]
		}
	}

	labels := make([]int, len(features))

	for iter := 0; iter < maxIterations; iter++ {
		// 分配点到最近的中心
		changed := false
		for i, feature := range features {
			minDist := math.Inf(1)
			bestLabel := 0

			for j, center := range centers {
				dist := travelTimeBasedDistance(feature, center, pidList[i], 0, travelMatrix)
				if dist < minDist {
					minDist = dist
					bestLabel = j
				}
			}

			if labels[i] != bestLabel {
				labels[i] = bestLabel
				changed = true
			}
		}

		if !changed {
			break
		}

		// 更新中心
		for i := range centers {
			for j := range centers[i] {
				centers[i][j] = 0
			}
		}

		counts := make([]int, nClusters)
		for i, label := range labels {
			for j := range features[i] {
				centers[label][j] += features[i][j]
			}
			counts[label]++
		}

		for i := range centers {
			if counts[i] > 0 {
				for j := range centers[i] {
					centers[i][j] /= float64(counts[i])
				}
			}
		}
	}

	return labels
}

// 仅平衡补货点位分布（不考虑总数量均衡）
func balanceRecallPointsOnly(groups map[int][]int, recallPoints map[int]bool, nClusters int, pointDict map[int]*Point, gidFeatures map[int][]float64) map[int][]int {
	// 统计各组中的补货点位数量
	recallCounts := make([]int, nClusters)
	for g, pids := range groups {
		for _, pid := range pids {
			if recallPoints[pid] {
				recallCounts[g]++
			}
		}
	}

	// 计算目标分布
	totalRecall := 0
	for _, count := range recallCounts {
		totalRecall += count
	}

	targetPerGroup := totalRecall / nClusters
	extraRecall := totalRecall % nClusters

	// 如果分布已经相对均匀，直接返回
	maxCount := 0
	minCount := totalRecall
	for _, count := range recallCounts {
		if count > maxCount {
			maxCount = count
		}
		if count < minCount {
			minCount = count
		}
	}

	if maxCount-minCount <= 1 {
		return groups
	}

	// 尝试重新分配补货点位
	fmt.Println("平衡补货点位分布...")

	// 找出补货点位过多和过少的组
	overGroups := make([]int, 0)
	underGroups := make([]int, 0)

	for g := 0; g < nClusters; g++ {
		target := targetPerGroup
		if g < extraRecall {
			target++
		}
		if recallCounts[g] > target {
			overGroups = append(overGroups, g)
		} else if recallCounts[g] < target {
			underGroups = append(underGroups, g)
		}
	}

	// 从过多的组向过少的组转移补货点位
	for _, overG := range overGroups {
		if len(underGroups) == 0 {
			break
		}

		// 找出当前组中的补货点位
		recallPids := make([]int, 0)
		for _, pid := range groups[overG] {
			if recallPoints[pid] {
				recallPids = append(recallPids, pid)
			}
		}

		// 计算需要转移的数量
		target := targetPerGroup
		if overG < extraRecall {
			target++
		}
		needToMove := recallCounts[overG] - target

		// 转移补货点位
		moved := 0
		for _, underG := range underGroups {
			if moved >= needToMove {
				break
			}

			target := targetPerGroup
			if underG < extraRecall {
				target++
			}
			canAccept := target - recallCounts[underG]

			// 计算目标组的中心
			targetCenter := make([]float64, len(gidFeatures[groups[underG][0]]))
			for _, pid := range groups[underG] {
				feature := gidFeatures[pid]
				for i, val := range feature {
					targetCenter[i] += val
				}
			}
			for i := range targetCenter {
				targetCenter[i] /= float64(len(groups[underG]))
			}

			// 转移补货点位（选择距离目标组中心最近的）
			for i := 0; i < canAccept && moved < needToMove && len(recallPids) > 0; i++ {
				// 找到距离目标组中心最近的补货点位
				minDist := math.Inf(1)
				bestIndex := 0
				for j, pid := range recallPids {
					dist := euclideanDistance(gidFeatures[pid], targetCenter)
					if dist < minDist {
						minDist = dist
						bestIndex = j
					}
				}

				pid := recallPids[bestIndex]
				// 从recallPids中移除
				recallPids = append(recallPids[:bestIndex], recallPids[bestIndex+1:]...)

				// 从原组移除
				for j, p := range groups[overG] {
					if p == pid {
						groups[overG] = append(groups[overG][:j], groups[overG][j+1:]...)
						break
					}
				}

				// 添加到目标组
				groups[underG] = append(groups[underG], pid)

				// 更新计数
				recallCounts[overG]--
				recallCounts[underG]++
				moved++

				fmt.Printf("补货点位 %d 从分组 %d 转移到分组 %d (距离: %.2f)\n", pid, overG+1, underG+1, minDist)
			}
		}
	}

	return groups
}

// 基于现有分组中心分配点位
func assignToExistingGroups(features [][]float64, pidList []int, existingGroups map[int][]int, pointDict map[int]*Point, travelMatrix *TravelTimeMatrix) []int {
	// 计算现有分组的中心
	groupCenters := make(map[int][]float64)
	for g, pids := range existingGroups {
		if len(pids) == 0 {
			continue
		}

		center := make([]float64, len(features[0]))
		for _, pid := range pids {
			point := pointDict[pid]
			var feature []float64
			if travelMatrix != nil {
				featuresMap, _ := calculateTravelTimeFeatures(map[int]*Point{pid: point}, travelMatrix)
				feature = featuresMap[pid]
			} else {
				feature = []float64{point.Longitude, point.Latitude}
			}

			for i, val := range feature {
				center[i] += val
			}
		}
		for i := range center {
			center[i] /= float64(len(pids))
		}
		groupCenters[g] = center
	}

	// 为每个点位分配最近的分组
	labels := make([]int, len(features))
	for i, feature := range features {
		minDist := math.Inf(1)
		bestGroup := 0

		for g, center := range groupCenters {
			var dist float64
			if travelMatrix != nil {
				dist = travelTimeBasedDistance(feature, center, pidList[i], 0, travelMatrix)
			} else {
				dist = euclideanDistance(feature, center)
			}

			if dist < minDist {
				minDist = dist
				bestGroup = g
			}
		}

		labels[i] = bestGroup
	}

	return labels
}

// 写入Step1结果（仅补货点位）
func writeStep1ToCSV(groups map[int][]int, pointDict map[int]*Point, recallPoints map[int]bool, outputPath string) error {
	file, err := os.Create(outputPath)
	if err != nil {
		return err
	}
	defer file.Close()

	writer := csv.NewWriter(file)
	defer writer.Flush()

	// 写入表头
	header := []string{"pid", "longitude", "latitude", "group_id"}
	err = writer.Write(header)
	if err != nil {
		return err
	}

	// 只写入补货点位
	for groupID, pids := range groups {
		for _, pid := range pids {
			if recallPoints[pid] { // 只输出补货点位
				point := pointDict[pid]
				record := []string{
					strconv.Itoa(pid),
					fmt.Sprintf("%.6f", point.Longitude),
					fmt.Sprintf("%.6f", point.Latitude),
					strconv.Itoa(groupID + 1),
				}
				err = writer.Write(record)
				if err != nil {
					return err
				}
			}
		}
	}

	return nil
}

// 读取点位信息数据
func readPointsFromCSV(filePath string) (map[int]*Point, error) {
	file, err := os.Open(filePath)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	reader := csv.NewReader(file)
	// 设置更宽松的解析选项来处理复杂的CSV格式
	reader.LazyQuotes = true
	reader.FieldsPerRecord = -1 // 允许不同行有不同数量的字段

	records, err := reader.ReadAll()
	if err != nil {
		return nil, err
	}

	pointDict := make(map[int]*Point)

	// 跳过表头
	validCount := 0
	invalidCount := 0
	for i := 1; i < len(records); i++ {
		record := records[i]
		if len(record) < 11 { // 确保有足够的字段（至少11列）
			invalidCount++
			continue
		}

		// 解析点位ID（第1列）
		id, err := strconv.Atoi(strings.TrimSpace(record[0]))
		if err != nil {
			invalidCount++
			continue
		}

		// 过滤掉pid为998和999的点位
		if id == 998 || id == 999 {
			invalidCount++
			continue
		}

		// 解析经纬度（第5、6列，对应latitude和longitude）
		latitude, err := strconv.ParseFloat(strings.TrimSpace(record[4]), 64)
		if err != nil {
			invalidCount++
			continue
		}

		longitude, err := strconv.ParseFloat(strings.TrimSpace(record[5]), 64)
		if err != nil {
			invalidCount++
			continue
		}

		// 解析时间窗口（第9、10列）
		startTime := strings.TrimSpace(record[9])
		endTime := strings.TrimSpace(record[10])

		// 验证时间格式
		if !isValidTimeFormat(startTime) || !isValidTimeFormat(endTime) {
			invalidCount++
			continue
		}

		if point, exists := pointDict[id]; exists {
			// 如果点位已存在，添加时间窗口
			point.TimeWindows = append(point.TimeWindows, TimeWindow{Start: startTime, End: endTime})
			validCount++
		} else {
			// 创建新点位
			pointDict[id] = &Point{
				ID:          id,
				Longitude:   longitude,
				Latitude:    latitude,
				TimeWindows: []TimeWindow{{Start: startTime, End: endTime}},
			}
			validCount++
		}
	}

	// fmt.Printf("解析统计：有效记录 %d 条，无效记录 %d 条\n", validCount, invalidCount)
	return pointDict, nil
}

// 验证时间格式是否为H:MM或HH:MM
func isValidTimeFormat(timeStr string) bool {
	timeStr = strings.TrimSpace(timeStr)

	// 检查是否包含冒号
	colonIndex := strings.Index(timeStr, ":")
	if colonIndex == -1 {
		return false
	}

	// 解析小时和分钟
	hourStr := timeStr[:colonIndex]
	minuteStr := timeStr[colonIndex+1:]

	hour, err1 := strconv.Atoi(hourStr)
	minute, err2 := strconv.Atoi(minuteStr)
	if err1 != nil || err2 != nil {
		return false
	}

	return hour >= 0 && hour <= 23 && minute >= 0 && minute <= 59
}

// 计算主时间窗均值（分钟）
func mainTimeWindowMean(timeWindows []TimeWindow) float64 {
	if len(timeWindows) == 0 {
		return 0
	}

	var starts []float64
	for _, tw := range timeWindows {
		parts := strings.Split(tw.Start, ":")
		if len(parts) != 2 {
			continue
		}
		h, err1 := strconv.Atoi(parts[0])
		m, err2 := strconv.Atoi(parts[1])
		if err1 != nil || err2 != nil {
			continue
		}
		starts = append(starts, float64(h*60+m))
	}

	if len(starts) == 0 {
		return 0
	}

	sum := 0.0
	for _, s := range starts {
		sum += s
	}
	return sum / float64(len(starts))
}

// 计算基于行驶时长的综合距离
func travelTimeBasedDistance(a, b []float64, fromID, toID int, travelMatrix *TravelTimeMatrix) float64 {
	if len(a) != len(b) {
		return 0
	}

	// 如果行驶时长矩阵可用，优先使用行驶时长
	if travelMatrix != nil {
		travelTime := travelMatrix.GetTravelTime(fromID, toID)
		if travelTime >= 0 {
			// 结合地理距离和行驶时长
			geoDist := euclideanDistance(a[:2], b[:2]) // 只使用经纬度部分
			timeWeight := 0.7                          // 行驶时长权重
			geoWeight := 0.3                           // 地理距离权重
			return timeWeight*travelTime + geoWeight*geoDist
		}
	}

	// 如果没有行驶时长数据，回退到欧几里得距离
	return euclideanDistance(a, b)
}

// 计算欧几里得距离（保留作为备用）
func euclideanDistance(a, b []float64) float64 {
	if len(a) != len(b) {
		return 0
	}
	sum := 0.0
	for i := range a {
		diff := a[i] - b[i]
		sum += diff * diff
	}
	return math.Sqrt(sum)
}

// 计算两经纬度点之间的球面距离（单位：公里）
func haversine(lon1, lat1, lon2, lat2 float64) float64 {
	const R = 6371.0 // 地球半径（公里）

	lon1Rad := lon1 * math.Pi / 180
	lat1Rad := lat1 * math.Pi / 180
	lon2Rad := lon2 * math.Pi / 180
	lat2Rad := lat2 * math.Pi / 180

	dlon := lon2Rad - lon1Rad
	dlat := lat2Rad - lat1Rad

	a := math.Sin(dlat/2)*math.Sin(dlat/2) + math.Cos(lat1Rad)*math.Cos(lat2Rad)*math.Sin(dlon/2)*math.Sin(dlon/2)
	c := 2 * math.Atan2(math.Sqrt(a), math.Sqrt(1-a))

	return R * c
}

func main() {
	// 读取点位信息数据
	csvPath := filepath.Join("..", "data", "点位信息.csv")
	pointDict, err := readPointsFromCSV(csvPath)
	if err != nil {
		log.Fatalf("读取CSV文件失败: %v", err)
	}

	fmt.Printf("成功读取 %d 个点位\n", len(pointDict))

	// 读取行驶时长数据
	var travelMatrix *TravelTimeMatrix

	// 尝试读取矩阵格式的行驶时长文件
	travelTimePath := filepath.Join("..", "data", "duration_path.csv")
	travelMatrix, err = readTravelTimeFromCSV(travelTimePath)
	if err != nil {
		// 如果矩阵格式失败，尝试读取长格式文件
		travelTimePath = filepath.Join("..", "data", "duration_point.csv")
		travelMatrix, err = readTravelTimeFromLongFormat(travelTimePath, pointDict)
		if err != nil {
			log.Printf("警告：无法读取行驶时长文件，将使用传统聚类方法: %v", err)
			travelMatrix = nil
		} else {
			log.Printf("成功读取长格式行驶时长文件: %s", travelTimePath)
		}
	} else {
		log.Printf("成功读取矩阵格式行驶时长文件: %s", travelTimePath)
	}

	// 读取需要补货的点位列表
	recallPointsPath := filepath.Join("..", "data", "recall_point.csv")
	recallPoints, err := readRecallPoints(recallPointsPath)
	if err != nil {
		log.Printf("警告：无法读取补货点位文件，将不进行补货点位的处理: %v", err)
		recallPoints = make(map[int]bool)
	} else {
		log.Printf("成功读取补货点位文件: %s，共 %d 个补货点位", recallPointsPath, len(recallPoints))
	}

	// ========== Step1: 仅对补货点位进行分组 ==========
	fmt.Println("\n=== Step1: 仅对补货点位进行分组 ===")

	// 提取补货点位的特征
	var recallFeatures [][]float64
	var recallPidList []int

	for _, point := range pointDict {
		if recallPoints[point.ID] {
			recallPidList = append(recallPidList, point.ID)
			if travelMatrix != nil {
				features, _ := calculateTravelTimeFeatures(map[int]*Point{point.ID: point}, travelMatrix)
				recallFeatures = append(recallFeatures, features[point.ID])
			} else {
				recallFeatures = append(recallFeatures, []float64{point.Longitude, point.Latitude})
			}
		}
	}

	// 对补货点位执行K-means聚类
	nClusters := 3
	var recallLabels []int
	if travelMatrix != nil {
		fmt.Println("对补货点位执行基于行驶时长的K-means聚类...")
		recallLabels = kmeansWithTravelTime(recallFeatures, recallPidList, nClusters, 100, travelMatrix)
	} else {
		fmt.Println("对补货点位执行传统K-means聚类...")
		recallLabels = kmeans(recallFeatures, recallPidList, nClusters, 100)
	}

	// 构建补货点位分组
	recallGroups := make(map[int][]int)
	for i, label := range recallLabels {
		pid := recallPidList[i]
		recallGroups[label] = append(recallGroups[label], pid)
	}

	// 构建recallPidList到特征的映射
	recallFeaturesMap := make(map[int][]float64)
	for i, pid := range recallPidList {
		recallFeaturesMap[pid] = recallFeatures[i]
	}

	// 平衡补货点位在各组中的分布
	fmt.Println("平衡补货点位在各组中的分布...")
	recallGroups = balanceRecallPointsOnly(recallGroups, recallPoints, nClusters, pointDict, recallFeaturesMap)

	// 输出Step1结果
	fmt.Println("\n=== Step1分组结果（仅补货点位）===")
	for groupID, pids := range recallGroups {
		fmt.Printf("分组%d:\n", groupID+1)
		// for _, pid := range pids {
		// 	point := pointDict[pid]
		// 	fmt.Printf("  点位ID: %d, 时间窗: %v\n", pid, point.TimeWindows)
		// }
		fmt.Printf("  本组点位数: %d\n", len(pids))
		fmt.Println("---")
	}

	// 输出Step1结果到CSV
	step1Path := filepath.Join("..", "output", "step1.csv")
	err = writeStep1ToCSV(recallGroups, pointDict, recallPoints, step1Path)
	if err != nil {
		log.Fatalf("写入Step1 CSV文件失败: %v", err)
	}
	fmt.Printf("Step1结果（仅补货点位）已保存到: %s\n", step1Path)

	// ========== Step2: 基于Step1结果聚类其他点位 ==========
	fmt.Println("\n=== Step2: 基于Step1结果聚类其他点位 ===")

	// 提取非补货点位的特征
	var normalFeatures [][]float64
	var normalPidList []int

	for _, point := range pointDict {
		if !recallPoints[point.ID] {
			normalPidList = append(normalPidList, point.ID)
			if travelMatrix != nil {
				features, _ := calculateTravelTimeFeatures(map[int]*Point{point.ID: point}, travelMatrix)
				normalFeatures = append(normalFeatures, features[point.ID])
			} else {
				normalFeatures = append(normalFeatures, []float64{point.Longitude, point.Latitude})
			}
		}
	}

	// 基于Step1的分组中心，对非补货点位进行分配
	fmt.Println("基于Step1分组中心分配非补货点位...")
	normalLabels := assignToExistingGroups(normalFeatures, normalPidList, recallGroups, pointDict, travelMatrix)

	// 合并结果
	groups := make(map[int][]int)
	for groupID, pids := range recallGroups {
		groups[groupID] = append(groups[groupID], pids...)
	}
	for i, label := range normalLabels {
		pid := normalPidList[i]
		groups[label] = append(groups[label], pid)
	}

	// 输出最终分组结果
	fmt.Println("\n=== 最终分组结果 ===")
	for groupID, pids := range groups {
		fmt.Printf("分组%d:\n", groupID+1)
		// for _, pid := range pids {
		// 	point := pointDict[pid]
		// 	recallMark := ""
		// 	if recallPoints[pid] {
		// 		recallMark = " [补货]"
		// 	}
		// 	fmt.Printf("  点位ID: %d%s, 时间窗: %v\n", pid, recallMark, point.TimeWindows)
		// }
		fmt.Printf("  本组点位数: %d\n", len(pids))
		fmt.Println("---")
	}

	// 输出聚类方法信息
	if travelMatrix != nil {
		fmt.Println("\n聚类方法: 基于行驶时长的两步聚类")
		fmt.Printf("行驶时长矩阵大小: %d x %d\n", travelMatrix.Size, travelMatrix.Size)
	} else {
		fmt.Println("\n聚类方法: 传统地理距离两步聚类")
	}

	// 输出最终结果到CSV文件
	outputPath := filepath.Join("..", "output", "output.csv")
	err = writeOutputToCSV(groups, pointDict, outputPath)
	if err != nil {
		log.Fatalf("写入CSV文件失败: %v", err)
	}

	fmt.Printf("最终分组结果已保存到: %s\n", outputPath)
}
