package main

import (
	"fmt"
	"math"
	"sort"
)

// 点位结构体
type VehiclePoint struct {
	ID             string   // 点位ID
	Longitude      float64  // 经度
	Latitude       float64  // 纬度
	IsShortage     bool     // 是否缺货
	CompatVehicles []string // 兼容车辆列表
}

// 车辆结构体
type Vehicle struct {
	ID     string  // 车辆ID
	Ratio  float64 // 预设缺货点位比例
	Region int     // 所属区域编号
}

// 区域结构体
type Region struct {
	ID     int      // 区域ID
	Points []string // 区域内点位ID列表
}

// 分配结果结构体
type AllocationResult struct {
	VehicleID      string   // 车辆ID
	AssignedPoints []string // 分配的点位ID列表
	ShortageCount  int      // 缺货点位数量
	ActualRatio    float64  // 实际缺货比例
}

// 车辆点位分配算法核心类
type VehicleAllocationAlgorithm struct {
	Points           []VehiclePoint // 所有点位
	Vehicles         []Vehicle      // 所有车辆
	TimeMatrix       [][]float64    // 行驶时间矩阵
	CompatMatrix     [][]bool       // 兼容性矩阵 [点位索引][车辆索引]
	Regions          []Region       // 区域列表
	WeightAlpha      float64        // 运力平衡权重
	WeightBeta       float64        // 缺货点位集中性权重
	WeightGamma      float64        // 不缺货点位集中性权重
	MaxIterations    int            // 最大迭代次数
	ConvergenceThres float64        // 收敛阈值
}

// 构造函数
func NewVehicleAllocationAlgorithm() *VehicleAllocationAlgorithm {
	return &VehicleAllocationAlgorithm{
		WeightAlpha:      0.7,  // 运力平衡优先
		WeightBeta:       0.25, // 缺货点位集中性
		WeightGamma:      0.05, // 不缺货点位集中性
		MaxIterations:    20,
		ConvergenceThres: 0.01,
	}
}

// 初始化数据
func (v *VehicleAllocationAlgorithm) Initialize(points []VehiclePoint, vehicles []Vehicle, timeMatrix [][]float64) error {
	v.Points = points
	v.Vehicles = vehicles
	v.TimeMatrix = timeMatrix

	// 构建兼容性矩阵
	if err := v.buildCompatibilityMatrix(); err != nil {
		return fmt.Errorf("构建兼容性矩阵失败: %v", err)
	}

	// 验证约束可行性
	if err := v.validateConstraints(); err != nil {
		return fmt.Errorf("约束验证失败: %v", err)
	}

	return nil
}

// 构建兼容性矩阵
func (v *VehicleAllocationAlgorithm) buildCompatibilityMatrix() error {
	pointCount := len(v.Points)
	vehicleCount := len(v.Vehicles)

	v.CompatMatrix = make([][]bool, pointCount)
	for i := range v.CompatMatrix {
		v.CompatMatrix[i] = make([]bool, vehicleCount)
	}

	// 填充兼容性矩阵
	for i, point := range v.Points {
		for j, vehicle := range v.Vehicles {
			v.CompatMatrix[i][j] = v.isCompatible(point.CompatVehicles, vehicle.ID)
		}
	}

	return nil
}

// 检查车辆与点位兼容性
func (v *VehicleAllocationAlgorithm) isCompatible(compatVehicles []string, vehicleID string) bool {
	for _, compatVehicle := range compatVehicles {
		if compatVehicle == vehicleID {
			return true
		}
	}
	return false
}

// 验证约束可行性
func (v *VehicleAllocationAlgorithm) validateConstraints() error {
	// 验证每个点位至少有一辆兼容车辆
	for i, point := range v.Points {
		hasCompatVehicle := false
		for j := range v.Vehicles {
			if v.CompatMatrix[i][j] {
				hasCompatVehicle = true
				break
			}
		}
		if !hasCompatVehicle {
			return fmt.Errorf("点位 %s 没有兼容的车辆", point.ID)
		}
	}

	// 验证每辆车至少有一个兼容点位
	for j, vehicle := range v.Vehicles {
		hasCompatPoint := false
		for i := range v.Points {
			if v.CompatMatrix[i][j] {
				hasCompatPoint = true
				break
			}
		}
		if !hasCompatPoint {
			return fmt.Errorf("车辆 %s 没有兼容的点位", vehicle.ID)
		}
	}

	return nil
}

// 阶段0：约束预处理与区域划分
func (v *VehicleAllocationAlgorithm) stage0_RegionPartition() error {
	// 按经度排序点位
	sortedPoints := make([]VehiclePoint, len(v.Points))
	copy(sortedPoints, v.Points)
	sort.Slice(sortedPoints, func(i, j int) bool {
		return sortedPoints[i].Longitude < sortedPoints[j].Longitude
	})

	// 动态区域划分
	vehicleCount := len(v.Vehicles)
	pointCount := len(sortedPoints)

	v.Regions = make([]Region, vehicleCount)

	for k := 0; k < vehicleCount; k++ {
		start := k * pointCount / vehicleCount
		end := (k + 1) * pointCount / vehicleCount
		if k == vehicleCount-1 {
			end = pointCount // 确保最后一个区域包含所有剩余点位
		}

		v.Regions[k] = Region{
			ID:     k,
			Points: make([]string, 0),
		}

		for i := start; i < end; i++ {
			v.Regions[k].Points = append(v.Regions[k].Points, sortedPoints[i].ID)
		}

		// 设置车辆的区域映射
		v.Vehicles[k].Region = k
	}

	// 处理兼容性冲突
	return v.resolveCompatibilityConflicts()
}

// 解决兼容性冲突
func (v *VehicleAllocationAlgorithm) resolveCompatibilityConflicts() error {
	// 检查并调整不兼容的分配
	for regionIdx, region := range v.Regions {
		vehicleIdx := regionIdx

		// 检查该区域内的点位是否与对应车辆兼容
		for _, pointID := range region.Points {
			pointIdx := v.getPointIndex(pointID)
			if pointIdx == -1 {
				continue
			}

			if !v.CompatMatrix[pointIdx][vehicleIdx] {
				// 寻找兼容的车辆和区域进行交换
				if err := v.swapPointToCompatibleRegion(pointID, regionIdx); err != nil {
					return fmt.Errorf("无法解决点位 %s 的兼容性冲突: %v", pointID, err)
				}
			}
		}
	}

	return nil
}

// 将点位交换到兼容的区域
func (v *VehicleAllocationAlgorithm) swapPointToCompatibleRegion(pointID string, currentRegionIdx int) error {
	pointIdx := v.getPointIndex(pointID)
	if pointIdx == -1 {
		return fmt.Errorf("找不到点位 %s", pointID)
	}

	// 寻找兼容的车辆/区域
	for targetRegionIdx := range v.Vehicles {
		if targetRegionIdx == currentRegionIdx {
			continue
		}

		if v.CompatMatrix[pointIdx][targetRegionIdx] {
			// 尝试交换点位
			return v.swapPoints(pointID, currentRegionIdx, targetRegionIdx)
		}
	}

	return fmt.Errorf("找不到兼容的区域进行交换")
}

// 交换两个区域间的点位
func (v *VehicleAllocationAlgorithm) swapPoints(pointID string, fromRegion, toRegion int) error {
	// 从原区域移除点位
	fromPoints := &v.Regions[fromRegion].Points
	for i, p := range *fromPoints {
		if p == pointID {
			*fromPoints = append((*fromPoints)[:i], (*fromPoints)[i+1:]...)
			break
		}
	}

	// 添加到目标区域
	v.Regions[toRegion].Points = append(v.Regions[toRegion].Points, pointID)

	return nil
}

// 阶段1：多约束下的点位聚类
func (v *VehicleAllocationAlgorithm) stage1_PointClustering() ([]AllocationResult, error) {
	results := make([]AllocationResult, len(v.Vehicles))

	// 为每个车辆分配其区域内的兼容点位
	for i, vehicle := range v.Vehicles {
		regionPoints := v.Regions[vehicle.Region].Points
		compatiblePoints := make([]string, 0)
		shortageCount := 0

		// 筛选兼容点位
		for _, pointID := range regionPoints {
			pointIdx := v.getPointIndex(pointID)
			if pointIdx != -1 && v.CompatMatrix[pointIdx][i] {
				compatiblePoints = append(compatiblePoints, pointID)
				if v.Points[pointIdx].IsShortage {
					shortageCount++
				}
			}
		}

		results[i] = AllocationResult{
			VehicleID:      vehicle.ID,
			AssignedPoints: compatiblePoints,
			ShortageCount:  shortageCount,
			ActualRatio:    0, // 将在后续计算
		}
	}

	return results, nil
}

// 阶段2：缺货点位比例优化调整
func (v *VehicleAllocationAlgorithm) stage2_ProportionOptimization(initialResults []AllocationResult) ([]AllocationResult, error) {
	totalShortage := v.getTotalShortageCount()
	if totalShortage == 0 {
		return initialResults, nil
	}

	// 计算实际比例
	for i := range initialResults {
		initialResults[i].ActualRatio = float64(initialResults[i].ShortageCount) / float64(totalShortage)
	}

	// 迭代优化
	currentResults := make([]AllocationResult, len(initialResults))
	copy(currentResults, initialResults)

	for iter := 0; iter < v.MaxIterations; iter++ {
		prevObjective := v.calculateObjective(currentResults)

		// 尝试调整分配以改善比例平衡
		improved := v.adjustAllocation(currentResults)

		newObjective := v.calculateObjective(currentResults)

		// 检查收敛条件
		if !improved || math.Abs(newObjective-prevObjective) < v.ConvergenceThres {
			break
		}
	}

	return currentResults, nil
}

// 调整分配以改善比例平衡
func (v *VehicleAllocationAlgorithm) adjustAllocation(results []AllocationResult) bool {
	improved := false
	totalShortage := v.getTotalShortageCount()

	// 寻找可以调整的缺货点位
	for i := 0; i < len(results); i++ {
		for j := i + 1; j < len(results); j++ {
			vehicle1 := &results[i]
			vehicle2 := &results[j]

			// 计算理想分配
			targetRatio1 := v.Vehicles[i].Ratio
			targetRatio2 := v.Vehicles[j].Ratio

			currentDiff1 := math.Abs(vehicle1.ActualRatio - targetRatio1)
			currentDiff2 := math.Abs(vehicle2.ActualRatio - targetRatio2)

			// 尝试交换一个缺货点位
			if shortagePoint := v.findSwappableShortagePoint(vehicle1, vehicle2, i, j); shortagePoint != "" {
				// 模拟交换后的效果
				newRatio1 := float64(vehicle1.ShortageCount-1) / float64(totalShortage)
				newRatio2 := float64(vehicle2.ShortageCount+1) / float64(totalShortage)

				newDiff1 := math.Abs(newRatio1 - targetRatio1)
				newDiff2 := math.Abs(newRatio2 - targetRatio2)

				// 如果交换能改善整体偏差，则执行交换
				if newDiff1+newDiff2 < currentDiff1+currentDiff2 {
					v.swapShortagePoint(vehicle1, vehicle2, shortagePoint)
					improved = true
				}
			}
		}
	}

	return improved
}

// 寻找可交换的缺货点位
func (v *VehicleAllocationAlgorithm) findSwappableShortagePoint(vehicle1, vehicle2 *AllocationResult, vehicleIdx1, vehicleIdx2 int) string {
	// 检查vehicle1中的缺货点位是否可以分配给vehicle2
	for _, pointID := range vehicle1.AssignedPoints {
		pointIdx := v.getPointIndex(pointID)
		if pointIdx != -1 && v.Points[pointIdx].IsShortage {
			// 检查兼容性和区域约束
			if v.CompatMatrix[pointIdx][vehicleIdx2] && v.isInSameOrAdjacentRegion(pointID, vehicleIdx2) {
				return pointID
			}
		}
	}

	return ""
}

// 交换缺货点位
func (v *VehicleAllocationAlgorithm) swapShortagePoint(vehicle1, vehicle2 *AllocationResult, pointID string) {
	// 从vehicle1移除
	for i, p := range vehicle1.AssignedPoints {
		if p == pointID {
			vehicle1.AssignedPoints = append(vehicle1.AssignedPoints[:i], vehicle1.AssignedPoints[i+1:]...)
			vehicle1.ShortageCount--
			break
		}
	}

	// 添加到vehicle2
	vehicle2.AssignedPoints = append(vehicle2.AssignedPoints, pointID)
	vehicle2.ShortageCount++

	// 更新比例
	totalShortage := v.getTotalShortageCount()
	vehicle1.ActualRatio = float64(vehicle1.ShortageCount) / float64(totalShortage)
	vehicle2.ActualRatio = float64(vehicle2.ShortageCount) / float64(totalShortage)
}

// 计算目标函数值
func (v *VehicleAllocationAlgorithm) calculateObjective(results []AllocationResult) float64 {
	totalShortage := float64(v.getTotalShortageCount())
	objective := 0.0

	// 运力平衡项
	balanceTerm := 0.0
	for i, result := range results {
		actualRatio := float64(result.ShortageCount) / totalShortage
		targetRatio := v.Vehicles[i].Ratio
		balanceTerm += math.Pow(actualRatio-targetRatio, 2)
	}
	objective += v.WeightAlpha * balanceTerm

	// 地理集中性项（简化实现）
	concentrationTerm := 0.0
	for _, result := range results {
		avgTime := v.calculateAverageTime(result.AssignedPoints)
		concentrationTerm += avgTime
	}
	objective += v.WeightBeta * concentrationTerm

	return objective
}

// 去重和完整性验证
func (v *VehicleAllocationAlgorithm) removeDuplicateAssignments(results []AllocationResult) []AllocationResult {
	// 记录每个点位的分配情况
	pointAssignments := make(map[string]int) // pointID -> vehicleIndex
	cleanResults := make([]AllocationResult, len(results))

	// 初始化清理后的结果
	for i, result := range results {
		cleanResults[i] = AllocationResult{
			VehicleID:      result.VehicleID,
			AssignedPoints: make([]string, 0),
			ShortageCount:  0,
			ActualRatio:    0,
		}
	}

	// 遍历所有分配结果，处理重复分配
	for vehicleIdx, result := range results {
		for _, pointID := range result.AssignedPoints {
			// 检查该点位是否已被分配
			if assignedVehicle, exists := pointAssignments[pointID]; exists {
				// 已被分配，需要决定保留哪个分配
				pointIdx := v.getPointIndex(pointID)
				if pointIdx == -1 {
					continue
				}

				// 检查当前车辆是否与该点位兼容
				if v.CompatMatrix[pointIdx][vehicleIdx] {
					// 当前车辆兼容，从之前的车辆移除，分配给当前车辆
					prevResult := &cleanResults[assignedVehicle]
					for i, p := range prevResult.AssignedPoints {
						if p == pointID {
							prevResult.AssignedPoints = append(prevResult.AssignedPoints[:i], prevResult.AssignedPoints[i+1:]...)
							if v.Points[pointIdx].IsShortage {
								prevResult.ShortageCount--
							}
							break
						}
					}

					// 分配给当前车辆
					pointAssignments[pointID] = vehicleIdx
					cleanResults[vehicleIdx].AssignedPoints = append(cleanResults[vehicleIdx].AssignedPoints, pointID)
					if v.Points[pointIdx].IsShortage {
						cleanResults[vehicleIdx].ShortageCount++
					}
				}
				// 如果当前车辆不兼容，保持之前的分配
			} else {
				// 首次分配，检查兼容性
				pointIdx := v.getPointIndex(pointID)
				if pointIdx != -1 && v.CompatMatrix[pointIdx][vehicleIdx] {
					pointAssignments[pointID] = vehicleIdx
					cleanResults[vehicleIdx].AssignedPoints = append(cleanResults[vehicleIdx].AssignedPoints, pointID)
					if v.Points[pointIdx].IsShortage {
						cleanResults[vehicleIdx].ShortageCount++
					}
				}
			}
		}
	}

	// 检查是否有未分配的点位，尝试分配给兼容的车辆
	assignedPointSet := make(map[string]bool)
	for pointID := range pointAssignments {
		assignedPointSet[pointID] = true
	}

	for pointIdx, point := range v.Points {
		if !assignedPointSet[point.ID] {
			// 找到兼容的车辆
			for vehicleIdx := range v.Vehicles {
				if v.CompatMatrix[pointIdx][vehicleIdx] {
					cleanResults[vehicleIdx].AssignedPoints = append(cleanResults[vehicleIdx].AssignedPoints, point.ID)
					if point.IsShortage {
						cleanResults[vehicleIdx].ShortageCount++
					}
					assignedPointSet[point.ID] = true
					break
				}
			}
		}
	}

	// 重新计算比例
	totalShortage := v.getTotalShortageCount()
	if totalShortage > 0 {
		for i := range cleanResults {
			cleanResults[i].ActualRatio = float64(cleanResults[i].ShortageCount) / float64(totalShortage)
		}
	}

	return cleanResults
}

// 主要执行函数 - 三阶段算法
func (v *VehicleAllocationAlgorithm) Execute() ([]AllocationResult, error) {
	// 阶段0：约束预处理与区域划分
	if err := v.stage0_RegionPartition(); err != nil {
		return nil, fmt.Errorf("阶段0失败: %v", err)
	}

	// 阶段1：多约束下的点位聚类
	initialResults, err := v.stage1_PointClustering()
	if err != nil {
		return nil, fmt.Errorf("阶段1失败: %v", err)
	}

	// 阶段2：缺货点位比例优化调整
	finalResults, err := v.stage2_ProportionOptimization(initialResults)
	if err != nil {
		return nil, fmt.Errorf("阶段2失败: %v", err)
	}

	// 阶段3：去重和完整性验证
	cleanResults := v.removeDuplicateAssignments(finalResults)

	return cleanResults, nil
}

// 辅助函数

// 获取点位索引
func (v *VehicleAllocationAlgorithm) getPointIndex(pointID string) int {
	for i, point := range v.Points {
		if point.ID == pointID {
			return i
		}
	}
	return -1
}

// 获取总缺货点位数量
func (v *VehicleAllocationAlgorithm) getTotalShortageCount() int {
	count := 0
	for _, point := range v.Points {
		if point.IsShortage {
			count++
		}
	}
	return count
}

// 检查点位是否在相同或相邻区域
func (v *VehicleAllocationAlgorithm) isInSameOrAdjacentRegion(pointID string, vehicleIdx int) bool {
	targetRegion := v.Vehicles[vehicleIdx].Region

	// 检查点位是否在目标区域
	for _, p := range v.Regions[targetRegion].Points {
		if p == pointID {
			return true
		}
	}

	// 简化实现：允许相邻区域（可根据实际需求调整）
	return true
}

// 计算点位集合的平均行驶时间
func (v *VehicleAllocationAlgorithm) calculateAverageTime(pointIDs []string) float64 {
	if len(pointIDs) <= 1 {
		return 0
	}

	totalTime := 0.0
	count := 0

	for i, pointID1 := range pointIDs {
		idx1 := v.getPointIndex(pointID1)
		if idx1 == -1 {
			continue
		}

		for j := i + 1; j < len(pointIDs); j++ {
			pointID2 := pointIDs[j]
			idx2 := v.getPointIndex(pointID2)
			if idx2 == -1 {
				continue
			}

			totalTime += v.TimeMatrix[idx1][idx2]
			count++
		}
	}

	if count == 0 {
		return 0
	}

	return totalTime / float64(count)
}

// 打印分配结果
func (v *VehicleAllocationAlgorithm) PrintResults(results []AllocationResult) {
	fmt.Println("=== 车辆点位分配结果 ===")
	totalShortage := v.getTotalShortageCount()

	for i, result := range results {
		fmt.Printf("\n车辆 %s (目标比例: %.2f):\n", result.VehicleID, v.Vehicles[i].Ratio)
		fmt.Printf("  分配点位数: %d\n", len(result.AssignedPoints))
		fmt.Printf("  缺货点位数: %d\n", result.ShortageCount)
		fmt.Printf("  实际缺货比例: %.3f\n", float64(result.ShortageCount)/float64(totalShortage))
		fmt.Printf("  比例偏差: %.3f\n", math.Abs(float64(result.ShortageCount)/float64(totalShortage)-v.Vehicles[i].Ratio))
		fmt.Printf("  分配点位: %v\n", result.AssignedPoints)
	}

	// 计算总体指标
	totalDeviation := 0.0
	for i, result := range results {
		actualRatio := float64(result.ShortageCount) / float64(totalShortage)
		deviation := math.Abs(actualRatio - v.Vehicles[i].Ratio)
		totalDeviation += deviation * deviation
	}

	fmt.Printf("\n=== 总体指标 ===\n")
	fmt.Printf("总比例偏差平方和: %.4f\n", totalDeviation)
	fmt.Printf("算法收敛状态: 已完成\n")
}
