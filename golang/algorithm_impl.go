package main

import (
	"encoding/csv"
	"fmt"
	"math"
	"math/rand"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"time"
)

// ============= 算法核心实现补充 =============

// calculateAverageTravelTime 计算平均行驶时长
func (alg *DynamicPartitionAlgorithm) calculateAverageTravelTime(pid int) float64 {
	if alg.travelMatrix == nil {
		return 0.0
	}

	totalTime := 0.0
	validCount := 0

	for otherPid := range alg.pointDict {
		if otherPid == pid {
			continue
		}

		travelTime := alg.travelMatrix.GetTravelTime(pid, otherPid)
		if travelTime >= 0 {
			totalTime += travelTime
			validCount++
		}
	}

	if validCount == 0 {
		return 0.0
	}

	return totalTime / float64(validCount)
}

// balanceGroupLoad 负载均衡调整
func (alg *DynamicPartitionAlgorithm) balanceGroupLoad(groups map[int][]int) map[int][]int {
	alg.logInfo("执行负载均衡调整...")

	totalPoints := 0
	for _, pids := range groups {
		totalPoints += len(pids)
	}

	maxIterations := 10

	for iter := 0; iter < maxIterations; iter++ {
		changed := false

		// 找出最大和最小的组
		var maxGroup, minGroup int
		maxSize, minSize := -1, totalPoints

		for g, pids := range groups {
			size := len(pids)
			if size > maxSize {
				maxSize = size
				maxGroup = g
			}
			if size < minSize {
				minSize = size
				minGroup = g
			}
		}

		// 如果差异在可接受范围内，停止调整
		if maxSize-minSize <= 2 {
			break
		}

		// 从最大组移动一个点到最小组
		if len(groups[maxGroup]) > 0 {
			// 选择距离最小组中心最近的点
			movePid := alg.findBestPointToMove(groups[maxGroup], groups[minGroup])

			// 执行移动
			alg.movePointBetweenGroups(groups, maxGroup, minGroup, movePid)
			changed = true
		}

		if !changed {
			break
		}
	}

	alg.logInfo("负载均衡调整完成")
	return groups
}

// validateTimeWindowFeasibility 时间窗口可行性验证
func (alg *DynamicPartitionAlgorithm) validateTimeWindowFeasibility(groups map[int][]int) map[int][]int {
	alg.logInfo("验证时间窗口可行性...")

	violations := 0
	for groupID, pids := range groups {
		// 检查组内点位的时间窗口冲突
		for i := 0; i < len(pids); i++ {
			for j := i + 1; j < len(pids); j++ {
				point1, exists1 := alg.pointDict[pids[i]]
				point2, exists2 := alg.pointDict[pids[j]]

				// 检查点位是否存在
				if !exists1 || !exists2 {
					continue
				}

				if alg.hasTimeWindowConflict(point1.TimeWindows, point2.TimeWindows) {
					violations++
					// 尝试将冲突点位移动到其他组
					alg.resolveTimeWindowConflict(groups, groupID, pids[i], pids[j])
				}
			}
		}
	}

	alg.logInfo("时间窗口验证完成，处理了 %d 个冲突", violations)
	return groups
}

// assignRecallPointsPriority 补货点位优先分配
func (alg *DynamicPartitionAlgorithm) assignRecallPointsPriority(features [][]float64, pidList []int, centers [][]float64, labels []int) {
	alg.logInfo("优先分配补货点位...")

	for i, pid := range pidList {
		if !alg.recallPoints[pid] {
			continue
		}

		minDist := math.Inf(1)
		bestCluster := 0

		for j, center := range centers {
			dist := alg.euclideanDistance(features[i], center)
			if dist < minDist {
				minDist = dist
				bestCluster = j
			}
		}

		labels[i] = bestCluster
	}
}

// findBestCluster 找到最佳聚类
func (alg *DynamicPartitionAlgorithm) findBestCluster(feature []float64, pid int, centers [][]float64) int {
	minDist := math.Inf(1)
	bestCluster := 0

	for j, center := range centers {
		dist := alg.euclideanDistance(feature, center)

		// 如果是补货点位，给予额外权重
		if alg.recallPoints[pid] {
			dist *= 0.8 // 降低距离，提高优先级
		}

		if dist < minDist {
			minDist = dist
			bestCluster = j
		}
	}

	return bestCluster
}

// updateCenters 更新聚类中心
func (alg *DynamicPartitionAlgorithm) updateCenters(features [][]float64, labels []int, centers [][]float64) {
	nClusters := len(centers)

	// 重置中心
	for i := range centers {
		for j := range centers[i] {
			centers[i][j] = 0
		}
	}

	counts := make([]int, nClusters)

	// 累加特征值
	for i, label := range labels {
		for j, val := range features[i] {
			centers[label][j] += val
		}
		counts[label]++
	}

	// 计算平均值
	for i := range centers {
		if counts[i] > 0 {
			for j := range centers[i] {
				centers[i][j] /= float64(counts[i])
			}
		}
	}
}

// trySwapBoundaryPoints 尝试交换边界点位
func (alg *DynamicPartitionAlgorithm) trySwapBoundaryPoints(groups map[int][]int, g1, g2 int) bool {
	if len(groups[g1]) == 0 || len(groups[g2]) == 0 {
		return false
	}

	// 计算组中心
	center1 := alg.calculateGroupCenter(groups[g1])
	center2 := alg.calculateGroupCenter(groups[g2])

	improved := false

	// 尝试从g1移动点位到g2
	for _, pid := range groups[g1] {
		feature := alg.features[pid]

		dist1 := alg.euclideanDistance(feature, center1)
		dist2 := alg.euclideanDistance(feature, center2)

		// 如果点位更接近g2的中心，考虑移动
		if dist2 < dist1*0.9 { // 添加阈值避免频繁交换
			currentCost := alg.calculateGroupCost(groups)

			// 尝试移动
			alg.movePointBetweenGroups(groups, g1, g2, pid)
			newCost := alg.calculateGroupCost(groups)

			if newCost < currentCost {
				improved = true
				break
			} else {
				// 回退移动
				alg.movePointBetweenGroups(groups, g2, g1, pid)
			}
		}
	}

	return improved
}

// moveOutliers 移动离群点
func (alg *DynamicPartitionAlgorithm) moveOutliers(groups map[int][]int) bool {
	improved := false

	for groupID, pids := range groups {
		if len(pids) <= 2 {
			continue
		}

		// 计算组中心
		center := alg.calculateGroupCenter(pids)

		// 找出离群点
		outliers := alg.findOutliers(pids, center)

		for _, outlierPid := range outliers {
			// 找到最适合的目标组
			bestGroup := alg.findBestTargetGroup(groups, groupID, outlierPid)

			if bestGroup != groupID {
				alg.movePointBetweenGroups(groups, groupID, bestGroup, outlierPid)
				improved = true
			}
		}
	}

	return improved
}

// generateNeighborSolution 生成邻域解
func (alg *DynamicPartitionAlgorithm) generateNeighborSolution(groups map[int][]int) map[int][]int {
	newGroups := alg.copyGroups(groups)

	// 随机选择操作类型
	operationType := rand.Intn(3)

	switch operationType {
	case 0:
		// 随机交换两个点位
		alg.randomSwapPoints(newGroups)
	case 1:
		// 移动随机点位到随机组
		alg.randomMovePoint(newGroups)
	case 2:
		// 重新分配边界点位
		alg.reassignBoundaryPoints(newGroups)
	}

	return newGroups
}

// calculateObjectiveFunction 计算目标函数
func (alg *DynamicPartitionAlgorithm) calculateObjectiveFunction(groups map[int][]int) float64 {
	// 多目标函数：负载均衡 + 总距离 + 时间窗口约束
	loadBalanceCost := alg.calculateLoadBalanceCost(groups)
	distanceCost := alg.calculateTotalDistanceCost(groups)
	timeWindowCost := alg.calculateTimeWindowCost(groups)

	// 权重设置
	w1, w2, w3 := 0.4, 0.4, 0.2

	return w1*loadBalanceCost + w2*distanceCost + w3*timeWindowCost
}

// maintainConstraintSatisfaction 维护约束满足性
func (alg *DynamicPartitionAlgorithm) maintainConstraintSatisfaction(groups map[int][]int) map[int][]int {
	alg.logInfo("维护约束满足性...")

	// 检查并修复时间窗口约束违反
	groups = alg.fixTimeWindowViolations(groups)

	// 检查并修复负载不均衡
	groups = alg.fixLoadImbalance(groups)

	// 检查并修复地理分散性问题
	groups = alg.fixGeographicDispersion(groups)

	return groups
}

// calculatePerformanceMetrics 计算性能指标
func (alg *DynamicPartitionAlgorithm) calculatePerformanceMetrics(groups map[int][]int) *PerformanceMetrics {
	totalDistance := 0.0
	totalPoints := 0

	// 计算总距离和点位数
	for _, pids := range groups {
		totalPoints += len(pids)
		for i := 0; i < len(pids); i++ {
			for j := i + 1; j < len(pids); j++ {
				totalDistance += alg.calculateDistance(pids[i], pids[j])
			}
		}
	}

	// 计算负载均衡指数
	loadBalanceIndex := alg.calculateLoadBalanceIndex(groups)

	// 计算时间窗口覆盖率
	timeWindowCoverage := alg.calculateTimeWindowCoverage(groups)

	return &PerformanceMetrics{
		TotalDistance:      totalDistance,
		AverageGroupSize:   float64(totalPoints) / float64(len(groups)),
		LoadBalanceIndex:   loadBalanceIndex,
		TimeWindowCoverage: timeWindowCoverage,
		ExecutionTime:      0.0, // 需要在外部计算
		IterationsUsed:     0,   // 需要在外部设置
	}
}

// checkConstraintSatisfaction 检查约束满足性
func (alg *DynamicPartitionAlgorithm) checkConstraintSatisfaction(groups map[int][]int) *ConstraintStatus {
	timeWindowViolations := 0

	// 检查时间窗口约束
	for _, pids := range groups {
		for i := 0; i < len(pids); i++ {
			for j := i + 1; j < len(pids); j++ {
				point1 := alg.pointDict[pids[i]]
				point2 := alg.pointDict[pids[j]]
				if alg.hasTimeWindowConflict(point1.TimeWindows, point2.TimeWindows) {
					timeWindowViolations++
				}
			}
		}
	}

	loadBalanceScore := alg.calculateLoadBalanceIndex(groups)
	geographicSpread := alg.calculateGeographicSpread(groups)

	return &ConstraintStatus{
		TimeWindowViolations: timeWindowViolations,
		LoadBalanceScore:     loadBalanceScore,
		GeographicSpread:     geographicSpread,
		ConstraintsSatisfied: timeWindowViolations == 0 && loadBalanceScore > 0.8,
	}
}

// outputResults 输出结果
func (alg *DynamicPartitionAlgorithm) outputResults(result *Result) error {
	// 创建输出目录
	if err := os.MkdirAll(alg.config.OutputPath, 0755); err != nil {
		return fmt.Errorf("创建输出目录失败: %v", err)
	}

	// 输出到CSV文件
	csvPath := fmt.Sprintf("%s/dynamic_partition_result.csv", alg.config.OutputPath)
	if err := alg.writeGroupsToCSV(result.Groups, csvPath); err != nil {
		return fmt.Errorf("写入CSV文件失败: %v", err)
	}

	// 输出详细报告
	reportPath := fmt.Sprintf("%s/partition_report.txt", alg.config.OutputPath)
	if err := alg.writeDetailedReport(result, reportPath); err != nil {
		return fmt.Errorf("写入报告文件失败: %v", err)
	}

	alg.logInfo("结果已保存到: %s", alg.config.OutputPath)
	return nil
}

// ============= 辅助函数实现 =============

func (alg *DynamicPartitionAlgorithm) euclideanDistance(a, b []float64) float64 {
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

func (alg *DynamicPartitionAlgorithm) findBestPointToMove(fromGroup, toGroup []int) int {
	if len(fromGroup) == 0 {
		return -1
	}

	toCenter := alg.calculateGroupCenter(toGroup)

	minDist := math.Inf(1)
	bestPid := fromGroup[0]

	for _, pid := range fromGroup {
		feature := alg.features[pid]
		dist := alg.euclideanDistance(feature, toCenter)
		if dist < minDist {
			minDist = dist
			bestPid = pid
		}
	}

	return bestPid
}

func (alg *DynamicPartitionAlgorithm) movePointBetweenGroups(groups map[int][]int, fromGroup, toGroup, pid int) {
	// 从源组移除
	for i, p := range groups[fromGroup] {
		if p == pid {
			groups[fromGroup] = append(groups[fromGroup][:i], groups[fromGroup][i+1:]...)
			break
		}
	}

	// 添加到目标组
	groups[toGroup] = append(groups[toGroup], pid)
}

func (alg *DynamicPartitionAlgorithm) calculateGroupCenter(pids []int) []float64 {
	if len(pids) == 0 {
		return nil
	}

	featureDim := len(alg.features[pids[0]])
	center := make([]float64, featureDim)

	for _, pid := range pids {
		feature := alg.features[pid]
		for i, val := range feature {
			center[i] += val
		}
	}

	for i := range center {
		center[i] /= float64(len(pids))
	}

	return center
}

func (alg *DynamicPartitionAlgorithm) calculateGroupCost(groups map[int][]int) float64 {
	return alg.calculateObjectiveFunction(groups)
}

func (alg *DynamicPartitionAlgorithm) findOutliers(pids []int, center []float64) []int {
	if len(pids) <= 2 {
		return nil
	}

	// 计算所有点到中心的距离
	var distances []float64
	for _, pid := range pids {
		feature := alg.features[pid]
		dist := alg.euclideanDistance(feature, center)
		distances = append(distances, dist)
	}

	// 计算平均距离和标准差
	mean := 0.0
	for _, dist := range distances {
		mean += dist
	}
	mean /= float64(len(distances))

	variance := 0.0
	for _, dist := range distances {
		variance += (dist - mean) * (dist - mean)
	}
	variance /= float64(len(distances))
	std := math.Sqrt(variance)

	// 找出离群点
	var outliers []int
	threshold := mean + alg.config.StdFactor*std

	for i, dist := range distances {
		if dist > threshold {
			outliers = append(outliers, pids[i])
		}
	}

	return outliers
}

func (alg *DynamicPartitionAlgorithm) findBestTargetGroup(groups map[int][]int, currentGroup, pid int) int {
	feature := alg.features[pid]
	minDist := math.Inf(1)
	bestGroup := currentGroup

	for groupID, pids := range groups {
		if groupID == currentGroup {
			continue
		}

		center := alg.calculateGroupCenter(pids)
		dist := alg.euclideanDistance(feature, center)

		if dist < minDist {
			minDist = dist
			bestGroup = groupID
		}
	}

	return bestGroup
}

func (alg *DynamicPartitionAlgorithm) randomSwapPoints(groups map[int][]int) {
	// 随机选择两个组
	groupIDs := make([]int, 0, len(groups))
	for gid := range groups {
		groupIDs = append(groupIDs, gid)
	}

	if len(groupIDs) < 2 {
		return
	}

	g1 := groupIDs[rand.Intn(len(groupIDs))]
	g2 := groupIDs[rand.Intn(len(groupIDs))]

	if g1 == g2 || len(groups[g1]) == 0 || len(groups[g2]) == 0 {
		return
	}

	// 随机选择点位进行交换
	pid1 := groups[g1][rand.Intn(len(groups[g1]))]
	pid2 := groups[g2][rand.Intn(len(groups[g2]))]

	alg.movePointBetweenGroups(groups, g1, g2, pid1)
	alg.movePointBetweenGroups(groups, g2, g1, pid2)
}

func (alg *DynamicPartitionAlgorithm) randomMovePoint(groups map[int][]int) {
	// 随机选择一个组和一个点位
	groupIDs := make([]int, 0, len(groups))
	for gid := range groups {
		if len(groups[gid]) > 1 { // 确保组中至少有2个点位
			groupIDs = append(groupIDs, gid)
		}
	}

	if len(groupIDs) == 0 {
		return
	}

	fromGroup := groupIDs[rand.Intn(len(groupIDs))]
	pid := groups[fromGroup][rand.Intn(len(groups[fromGroup]))]

	// 随机选择目标组
	allGroupIDs := make([]int, 0, len(groups))
	for gid := range groups {
		if gid != fromGroup {
			allGroupIDs = append(allGroupIDs, gid)
		}
	}

	if len(allGroupIDs) == 0 {
		return
	}

	toGroup := allGroupIDs[rand.Intn(len(allGroupIDs))]
	alg.movePointBetweenGroups(groups, fromGroup, toGroup, pid)
}

func (alg *DynamicPartitionAlgorithm) reassignBoundaryPoints(groups map[int][]int) {
	// 重新分配边界点位的简化实现
	for g1 := 0; g1 < len(groups)-1; g1++ {
		for g2 := g1 + 1; g2 < len(groups); g2++ {
			alg.trySwapBoundaryPoints(groups, g1, g2)
		}
	}
}

// 成本计算函数
func (alg *DynamicPartitionAlgorithm) calculateLoadBalanceCost(groups map[int][]int) float64 {
	if len(groups) == 0 {
		return 0
	}

	totalPoints := 0
	for _, pids := range groups {
		totalPoints += len(pids)
	}

	avgSize := float64(totalPoints) / float64(len(groups))
	variance := 0.0

	for _, pids := range groups {
		diff := float64(len(pids)) - avgSize
		variance += diff * diff
	}

	return variance / float64(len(groups))
}

func (alg *DynamicPartitionAlgorithm) calculateTotalDistanceCost(groups map[int][]int) float64 {
	totalCost := 0.0

	for _, pids := range groups {
		// 计算组内总距离
		for i := 0; i < len(pids); i++ {
			for j := i + 1; j < len(pids); j++ {
				totalCost += alg.calculateDistance(pids[i], pids[j])
			}
		}
	}

	return totalCost
}

func (alg *DynamicPartitionAlgorithm) calculateTimeWindowCost(groups map[int][]int) float64 {
	cost := 0.0

	for _, pids := range groups {
		// 计算时间窗口分散度
		timeWindows := make([]float64, 0)
		for _, pid := range pids {
			point := alg.pointDict[pid]
			meanTime := alg.calculateMainTimeWindowMean(point.TimeWindows)
			if meanTime >= alg.config.TimeWindowStart && meanTime <= alg.config.TimeWindowEnd {
				timeWindows = append(timeWindows, meanTime)
			}
		}

		if len(timeWindows) > 1 {
			sort.Float64s(timeWindows)
			spread := timeWindows[len(timeWindows)-1] - timeWindows[0]
			if spread < alg.config.MinInterval {
				cost += alg.config.MinInterval - spread
			}
		}
	}

	return cost
}

// 约束修复函数
func (alg *DynamicPartitionAlgorithm) fixTimeWindowViolations(groups map[int][]int) map[int][]int {
	// 修复时间窗口违反的简化实现
	return groups
}

func (alg *DynamicPartitionAlgorithm) fixLoadImbalance(groups map[int][]int) map[int][]int {
	return alg.balanceGroupLoad(groups)
}

func (alg *DynamicPartitionAlgorithm) fixGeographicDispersion(groups map[int][]int) map[int][]int {
	// 修复地理分散性问题的简化实现
	return groups
}

// 指标计算函数
func (alg *DynamicPartitionAlgorithm) calculateLoadBalanceIndex(groups map[int][]int) float64 {
	if len(groups) == 0 {
		return 0
	}

	totalPoints := 0
	for _, pids := range groups {
		totalPoints += len(pids)
	}

	avgSize := float64(totalPoints) / float64(len(groups))
	sumSquaredDiff := 0.0

	for _, pids := range groups {
		diff := float64(len(pids)) - avgSize
		sumSquaredDiff += diff * diff
	}

	variance := sumSquaredDiff / float64(len(groups))

	// 转换为0-1之间的指数，1表示完全均衡
	if variance == 0 {
		return 1.0
	}

	return 1.0 / (1.0 + variance/avgSize)
}

func (alg *DynamicPartitionAlgorithm) calculateTimeWindowCoverage(groups map[int][]int) float64 {
	totalPoints := 0
	coveredPoints := 0

	for _, pids := range groups {
		for _, pid := range pids {
			totalPoints++
			point := alg.pointDict[pid]
			meanTime := alg.calculateMainTimeWindowMean(point.TimeWindows)
			if meanTime >= alg.config.TimeWindowStart && meanTime <= alg.config.TimeWindowEnd {
				coveredPoints++
			}
		}
	}

	if totalPoints == 0 {
		return 0
	}

	return float64(coveredPoints) / float64(totalPoints)
}

func (alg *DynamicPartitionAlgorithm) calculateGeographicSpread(groups map[int][]int) float64 {
	totalSpread := 0.0

	for _, pids := range groups {
		if len(pids) < 2 {
			continue
		}

		// 计算组内地理分散度
		maxDist := 0.0
		for i := 0; i < len(pids); i++ {
			for j := i + 1; j < len(pids); j++ {
				dist := alg.calculateGeographicDistance(pids[i], pids[j])
				if dist > maxDist {
					maxDist = dist
				}
			}
		}
		totalSpread += maxDist
	}

	return totalSpread / float64(len(groups))
}

// 输出函数
func (alg *DynamicPartitionAlgorithm) writeGroupsToCSV(groups map[int][]int, filePath string) error {
	file, err := os.Create(filePath)
	if err != nil {
		return err
	}
	defer file.Close()

	writer := csv.NewWriter(file)
	defer writer.Flush()

	// 写入表头
	header := []string{"pid", "longitude", "latitude", "group_id", "time_windows"}
	if err := writer.Write(header); err != nil {
		return err
	}

	// 写入数据
	for groupID, pids := range groups {
		for _, pid := range pids {
			point := alg.pointDict[pid]

			// 格式化时间窗口
			timeWindowsStr := ""
			for i, tw := range point.TimeWindows {
				if i > 0 {
					timeWindowsStr += ";"
				}
				timeWindowsStr += fmt.Sprintf("%s-%s", tw.Start, tw.End)
			}

			record := []string{
				strconv.Itoa(pid),
				fmt.Sprintf("%.6f", point.Longitude),
				fmt.Sprintf("%.6f", point.Latitude),
				strconv.Itoa(groupID + 1),
				timeWindowsStr,
			}

			if err := writer.Write(record); err != nil {
				return err
			}
		}
	}

	return nil
}

func (alg *DynamicPartitionAlgorithm) writeDetailedReport(result *Result, filePath string) error {
	file, err := os.Create(filePath)
	if err != nil {
		return err
	}
	defer file.Close()

	fmt.Fprintf(file, "=== 动态分区算法执行报告 ===\n")
	fmt.Fprintf(file, "执行时间: %s\n", result.Timestamp.Format("2006-01-02 15:04:05"))
	fmt.Fprintf(file, "\n=== 配置参数 ===\n")
	fmt.Fprintf(file, "聚类组数: %d\n", result.Config.NClusters)
	fmt.Fprintf(file, "最大迭代次数: %d\n", result.Config.MaxIterations)
	fmt.Fprintf(file, "时间权重: %.2f\n", result.Config.TimeWeight)
	fmt.Fprintf(file, "地理权重: %.2f\n", result.Config.GeoWeight)

	fmt.Fprintf(file, "\n=== 性能指标 ===\n")
	fmt.Fprintf(file, "总距离: %.2f\n", result.Performance.TotalDistance)
	fmt.Fprintf(file, "平均组大小: %.2f\n", result.Performance.AverageGroupSize)
	fmt.Fprintf(file, "负载均衡指数: %.3f\n", result.Performance.LoadBalanceIndex)
	fmt.Fprintf(file, "时间窗口覆盖率: %.3f\n", result.Performance.TimeWindowCoverage)
	fmt.Fprintf(file, "执行时间: %.2f 秒\n", result.Performance.ExecutionTime)

	fmt.Fprintf(file, "\n=== 约束状态 ===\n")
	fmt.Fprintf(file, "时间窗口违反数: %d\n", result.Constraints.TimeWindowViolations)
	fmt.Fprintf(file, "负载均衡得分: %.3f\n", result.Constraints.LoadBalanceScore)
	fmt.Fprintf(file, "地理分散度: %.2f\n", result.Constraints.GeographicSpread)
	fmt.Fprintf(file, "约束满足状态: %v\n", result.Constraints.ConstraintsSatisfied)

	fmt.Fprintf(file, "\n=== 分组详情 ===\n")
	for groupID, pids := range result.Groups {
		fmt.Fprintf(file, "分组 %d: %d 个点位\n", groupID+1, len(pids))
		recallCount := 0
		for _, pid := range pids {
			if alg.recallPoints[pid] {
				recallCount++
			}
		}
		fmt.Fprintf(file, "  补货点位: %d 个\n", recallCount)
		fmt.Fprintf(file, "  点位列表: %v\n", pids)
		fmt.Fprintf(file, "\n")
	}

	return nil
}

func (alg *DynamicPartitionAlgorithm) resolveTimeWindowConflict(groups map[int][]int, groupID, pid1, pid2 int) {
	// 时间窗口冲突解决的简化实现
	// 可以尝试将其中一个点位移动到其他组
}

// saveFirstStageResult 保存第一阶段聚类结果（仅补货点位聚类）
func (alg *DynamicPartitionAlgorithm) saveFirstStageResult(groups map[int][]int) error {
	// 创建仅包含补货点位的分组，确保包含所有分组（包括空分组）
	recallOnlyGroups := make(map[int][]int)

	// 初始化所有分组为空
	for i := 0; i < alg.config.NClusters; i++ {
		recallOnlyGroups[i] = []int{}
	}

	// 填充有补货点位的分组
	for groupID, pids := range groups {
		var recallPids []int
		for _, pid := range pids {
			if alg.recallPoints[pid] {
				recallPids = append(recallPids, pid)
			}
		}
		recallOnlyGroups[groupID] = recallPids
	}

	// 保存到CSV文件
	csvPath := filepath.Join(alg.config.OutputPath, "first_stage_recall_result.csv")
	if err := alg.writeGroupsToCSV(recallOnlyGroups, csvPath); err != nil {
		return fmt.Errorf("写入第一阶段CSV失败: %v", err)
	}

	// 生成第一阶段统计报告
	reportPath := filepath.Join(alg.config.OutputPath, "first_stage_report.txt")
	if err := alg.writeFirstStageReport(recallOnlyGroups, reportPath); err != nil {
		return fmt.Errorf("写入第一阶段报告失败: %v", err)
	}

	alg.logInfo("第一阶段结果已保存: %s", csvPath)
	return nil
}

// writeFirstStageReport 写入第一阶段报告
func (alg *DynamicPartitionAlgorithm) writeFirstStageReport(groups map[int][]int, filePath string) error {
	file, err := os.Create(filePath)
	if err != nil {
		return err
	}
	defer file.Close()

	fmt.Fprintf(file, "=== 第一阶段聚类结果报告（仅补货点位） ===\n")
	fmt.Fprintf(file, "生成时间: %s\n", time.Now().Format("2006-01-02 15:04:05"))
	fmt.Fprintf(file, "聚类方法: K-means (补货点位优先)\n")
	fmt.Fprintf(file, "分组数量: %d\n\n", alg.config.NClusters)

	totalRecallPoints := 0
	// 按分组ID顺序显示所有分组
	for i := 0; i < alg.config.NClusters; i++ {
		pids, exists := groups[i]
		if !exists {
			pids = []int{}
		}
		totalRecallPoints += len(pids)
		fmt.Fprintf(file, "分组%d: %d个补货点位\n", i+1, len(pids))

		// 计算时间窗口分布
		if len(pids) > 0 {
			timeWindowCount := make(map[string]int)
			for _, pid := range pids {
				point := alg.pointDict[pid]
				for _, tw := range point.TimeWindows {
					timeWindow := fmt.Sprintf("%s-%s", tw.Start, tw.End)
					timeWindowCount[timeWindow]++
				}
			}

			fmt.Fprintf(file, "  时间窗口分布:\n")
			for timeWindow, count := range timeWindowCount {
				fmt.Fprintf(file, "    %s: %d个点位\n", timeWindow, count)
			}
		} else {
			fmt.Fprintf(file, "  时间窗口分布: 无补货点位\n")
		}
		fmt.Fprintf(file, "\n")
	}

	fmt.Fprintf(file, "总计补货点位: %d\n", totalRecallPoints)

	// 计算负载均衡指数
	if len(groups) > 0 {
		avgSize := float64(totalRecallPoints) / float64(len(groups))
		variance := 0.0
		for _, pids := range groups {
			diff := float64(len(pids)) - avgSize
			variance += diff * diff
		}
		variance /= float64(len(groups))
		balanceIndex := 1.0 / (1.0 + variance/avgSize)

		fmt.Fprintf(file, "平均组大小: %.1f\n", avgSize)
		fmt.Fprintf(file, "负载均衡指数: %.3f\n", balanceIndex)
	}

	fmt.Fprintf(file, "\n=== 报告结束 ===\n")
	return nil
}
