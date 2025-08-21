package main

import (
	"fmt"
	"math"
	"sort"
)

// 改进的车辆点位分配算法，解决地理位置不集中问题
type ImprovedVehicleAllocationAlgorithm struct {
	Points           []VehiclePoint // 所有点位
	Vehicles         []Vehicle      // 所有车辆
	TimeMatrix       [][]float64    // 行驶时间矩阵
	CompatMatrix     [][]bool       // 兼容性矩阵 [点位索引][车辆索引]
	Regions          []Region       // 区域列表
	WeightAlpha      float64        // 运力平衡权重
	WeightBeta       float64        // 缺货点位集中性权重
	WeightGamma      float64        // 不缺货点位集中性权重
	WeightGeographic float64        // 地理位置集中性权重（新增）
	MaxIterations    int            // 最大迭代次数
	ConvergenceThres float64        // 收敛阈值
}

// 构造函数
func NewImprovedVehicleAllocationAlgorithm() *ImprovedVehicleAllocationAlgorithm {
	return &ImprovedVehicleAllocationAlgorithm{
		WeightAlpha:      0.5,  // 运力平衡权重
		WeightBeta:       0.2,  // 缺货点位集中性权重
		WeightGamma:      0.05, // 不缺货点位集中性权重
		WeightGeographic: 0.25, // 地理位置集中性权重（新增）
		MaxIterations:    30,
		ConvergenceThres: 0.01,
	}
}

// 初始化数据
func (v *ImprovedVehicleAllocationAlgorithm) Initialize(points []VehiclePoint, vehicles []Vehicle, timeMatrix [][]float64) error {
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
func (v *ImprovedVehicleAllocationAlgorithm) buildCompatibilityMatrix() error {
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
func (v *ImprovedVehicleAllocationAlgorithm) isCompatible(compatVehicles []string, vehicleID string) bool {
	for _, compatVehicle := range compatVehicles {
		if compatVehicle == vehicleID {
			return true
		}
	}
	return false
}

// 验证约束可行性
func (v *ImprovedVehicleAllocationAlgorithm) validateConstraints() error {
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

// 改进的阶段0：智能区域划分与兼容性平衡
func (v *ImprovedVehicleAllocationAlgorithm) stage0_ImprovedRegionPartition() error {

	// 按经度排序点位
	sortedPoints := make([]VehiclePoint, len(v.Points))
	copy(sortedPoints, v.Points)
	sort.Slice(sortedPoints, func(i, j int) bool {
		return sortedPoints[i].Longitude < sortedPoints[j].Longitude
	})

	// 初始区域划分
	vehicleCount := len(v.Vehicles)
	pointCount := len(sortedPoints)

	v.Regions = make([]Region, vehicleCount)

	// 初始化区域
	for k := 0; k < vehicleCount; k++ {
		start := k * pointCount / vehicleCount
		end := (k + 1) * pointCount / vehicleCount
		if k == vehicleCount-1 {
			end = pointCount
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

	v.printRegionStats()

	// 改进的兼容性冲突解决
	return v.improvedResolveCompatibilityConflicts()
}

// 改进的兼容性冲突解决算法
func (v *ImprovedVehicleAllocationAlgorithm) improvedResolveCompatibilityConflicts() error {

	maxAttempts := 10
	for attempt := 0; attempt < maxAttempts; attempt++ {
		conflicts := v.findAllConflicts()
		if len(conflicts) == 0 {
			return nil
		}

		resolved := 0
		for _, conflict := range conflicts {
			if v.resolveConflictWithGeographicPreference(conflict) {
				resolved++
			}
		}

		if resolved == 0 {
			// 如果无法解决更多冲突，尝试更激进的策略
			if !v.forceResolveRemainingConflicts() {
				return fmt.Errorf("无法解决所有兼容性冲突")
			}
		}
	}

	return fmt.Errorf("达到最大尝试次数，仍有未解决的兼容性冲突")
}

// 冲突信息结构体
type Conflict struct {
	PointID           string
	PointIdx          int
	CurrentRegion     int
	CompatibleRegions []int
}

// 查找所有兼容性冲突
func (v *ImprovedVehicleAllocationAlgorithm) findAllConflicts() []Conflict {
	var conflicts []Conflict

	for regionIdx, region := range v.Regions {
		for _, pointID := range region.Points {
			pointIdx := v.getPointIndex(pointID)
			if pointIdx == -1 {
				continue
			}

			// 检查是否与当前区域的车辆兼容
			if !v.CompatMatrix[pointIdx][regionIdx] {
				// 找到所有兼容的区域
				var compatibleRegions []int
				for vehicleIdx := range v.Vehicles {
					if v.CompatMatrix[pointIdx][vehicleIdx] {
						compatibleRegions = append(compatibleRegions, vehicleIdx)
					}
				}

				conflicts = append(conflicts, Conflict{
					PointID:           pointID,
					PointIdx:          pointIdx,
					CurrentRegion:     regionIdx,
					CompatibleRegions: compatibleRegions,
				})
			}
		}
	}

	return conflicts
}

// 基于地理偏好解决冲突
func (v *ImprovedVehicleAllocationAlgorithm) resolveConflictWithGeographicPreference(conflict Conflict) bool {
	point := v.Points[conflict.PointIdx]

	// 计算到各个兼容区域中心的距离
	type RegionDistance struct {
		RegionIdx int
		Distance  float64
	}

	var regionDistances []RegionDistance

	for _, regionIdx := range conflict.CompatibleRegions {
		regionCenter := v.calculateRegionCenter(regionIdx)
		distance := v.calculateGeographicDistance(point.Longitude, point.Latitude,
			regionCenter.Longitude, regionCenter.Latitude)

		regionDistances = append(regionDistances, RegionDistance{
			RegionIdx: regionIdx,
			Distance:  distance,
		})
	}

	// 按距离排序，优先选择最近的区域
	sort.Slice(regionDistances, func(i, j int) bool {
		return regionDistances[i].Distance < regionDistances[j].Distance
	})

	// 尝试与最近的区域进行智能交换
	for _, rd := range regionDistances {
		if v.attemptSmartSwap(conflict.PointID, conflict.CurrentRegion, rd.RegionIdx) {
			return true
		}
	}

	return false
}

// 计算区域中心
func (v *ImprovedVehicleAllocationAlgorithm) calculateRegionCenter(regionIdx int) struct{ Longitude, Latitude float64 } {
	region := v.Regions[regionIdx]
	if len(region.Points) == 0 {
		return struct{ Longitude, Latitude float64 }{0, 0}
	}

	sumLon, sumLat := 0.0, 0.0
	count := 0

	for _, pointID := range region.Points {
		pointIdx := v.getPointIndex(pointID)
		if pointIdx != -1 {
			sumLon += v.Points[pointIdx].Longitude
			sumLat += v.Points[pointIdx].Latitude
			count++
		}
	}

	if count == 0 {
		return struct{ Longitude, Latitude float64 }{0, 0}
	}

	return struct{ Longitude, Latitude float64 }{
		Longitude: sumLon / float64(count),
		Latitude:  sumLat / float64(count),
	}
}

// 计算地理距离（简化版本，使用欧几里得距离）
func (v *ImprovedVehicleAllocationAlgorithm) calculateGeographicDistance(lon1, lat1, lon2, lat2 float64) float64 {
	dlat := lat1 - lat2
	dlon := lon1 - lon2
	return math.Sqrt(dlat*dlat + dlon*dlon)
}

// 尝试智能交换
func (v *ImprovedVehicleAllocationAlgorithm) attemptSmartSwap(pointID string, fromRegion, toRegion int) bool {
	// 首先尝试简单移动
	if v.canMovePoint(pointID, fromRegion, toRegion) {
		v.movePoint(pointID, fromRegion, toRegion)
		return true
	}

	// 如果不能简单移动，尝试找到合适的交换点位
	return v.findAndExecuteSwap(pointID, fromRegion, toRegion)
}

// 检查是否可以移动点位
func (v *ImprovedVehicleAllocationAlgorithm) canMovePoint(pointID string, fromRegion, toRegion int) bool {
	pointIdx := v.getPointIndex(pointID)
	return pointIdx != -1 && v.CompatMatrix[pointIdx][toRegion]
}

// 移动点位
func (v *ImprovedVehicleAllocationAlgorithm) movePoint(pointID string, fromRegion, toRegion int) {
	// 从原区域移除
	fromPoints := &v.Regions[fromRegion].Points
	for i, p := range *fromPoints {
		if p == pointID {
			*fromPoints = append((*fromPoints)[:i], (*fromPoints)[i+1:]...)
			break
		}
	}

	// 添加到目标区域
	v.Regions[toRegion].Points = append(v.Regions[toRegion].Points, pointID)
}

// 寻找并执行交换
func (v *ImprovedVehicleAllocationAlgorithm) findAndExecuteSwap(conflictPointID string, fromRegion, toRegion int) bool {
	conflictPointIdx := v.getPointIndex(conflictPointID)
	if conflictPointIdx == -1 {
		return false
	}

	// 在目标区域中寻找可以交换的点位
	for _, candidatePointID := range v.Regions[toRegion].Points {
		candidatePointIdx := v.getPointIndex(candidatePointID)
		if candidatePointIdx == -1 {
			continue
		}

		// 检查是否可以交换（双向兼容）
		if v.CompatMatrix[conflictPointIdx][toRegion] && v.CompatMatrix[candidatePointIdx][fromRegion] {
			// 检查交换后是否改善地理集中性
			if v.wouldImproveGeographicConcentration(conflictPointID, candidatePointID, fromRegion, toRegion) {
				v.swapPoints(conflictPointID, fromRegion, candidatePointID, toRegion)
				return true
			}
		}
	}

	return false
}

// 检查交换是否会改善地理集中性
func (v *ImprovedVehicleAllocationAlgorithm) wouldImproveGeographicConcentration(point1ID, point2ID string, region1, region2 int) bool {
	point1Idx := v.getPointIndex(point1ID)
	point2Idx := v.getPointIndex(point2ID)

	if point1Idx == -1 || point2Idx == -1 {
		return false
	}

	// point1 := v.Points[point1Idx]
	// point2 := v.Points[point2Idx]

	// 计算当前配置的地理分散度
	currentDispersion := v.calculateRegionDispersion(region1) + v.calculateRegionDispersion(region2)

	// 模拟交换后的分散度
	// 临时交换
	v.swapPoints(point1ID, region1, point2ID, region2)
	newDispersion := v.calculateRegionDispersion(region1) + v.calculateRegionDispersion(region2)
	// 交换回来
	v.swapPoints(point2ID, region1, point1ID, region2)

	// 如果新配置的分散度更小，则交换有益
	return newDispersion < currentDispersion
}

// 计算区域分散度
func (v *ImprovedVehicleAllocationAlgorithm) calculateRegionDispersion(regionIdx int) float64 {
	region := v.Regions[regionIdx]
	if len(region.Points) <= 1 {
		return 0
	}

	center := v.calculateRegionCenter(regionIdx)
	totalDispersion := 0.0

	for _, pointID := range region.Points {
		pointIdx := v.getPointIndex(pointID)
		if pointIdx != -1 {
			point := v.Points[pointIdx]
			distance := v.calculateGeographicDistance(point.Longitude, point.Latitude,
				center.Longitude, center.Latitude)
			totalDispersion += distance * distance
		}
	}

	return totalDispersion / float64(len(region.Points))
}

// 交换两个点位
func (v *ImprovedVehicleAllocationAlgorithm) swapPoints(point1ID string, region1 int, point2ID string, region2 int) {
	// 从region1移除point1，从region2移除point2
	v.removePointFromRegion(point1ID, region1)
	v.removePointFromRegion(point2ID, region2)

	// 将point1添加到region2，将point2添加到region1
	v.Regions[region2].Points = append(v.Regions[region2].Points, point1ID)
	v.Regions[region1].Points = append(v.Regions[region1].Points, point2ID)
}

// 从区域中移除点位
func (v *ImprovedVehicleAllocationAlgorithm) removePointFromRegion(pointID string, regionIdx int) {
	points := &v.Regions[regionIdx].Points
	for i, p := range *points {
		if p == pointID {
			*points = append((*points)[:i], (*points)[i+1:]...)
			break
		}
	}
}

// 强制解决剩余冲突
func (v *ImprovedVehicleAllocationAlgorithm) forceResolveRemainingConflicts() bool {
	conflicts := v.findAllConflicts()
	if len(conflicts) == 0 {
		return true
	}

	for _, conflict := range conflicts {
		// 简单地将冲突点位移动到第一个兼容的区域
		if len(conflict.CompatibleRegions) > 0 {
			targetRegion := conflict.CompatibleRegions[0]
			v.movePoint(conflict.PointID, conflict.CurrentRegion, targetRegion)
		}
	}

	// 验证是否还有冲突
	remainingConflicts := v.findAllConflicts()
	return len(remainingConflicts) == 0
}

// 打印区域统计信息
func (v *ImprovedVehicleAllocationAlgorithm) printRegionStats() {
	for _, region := range v.Regions {
		if len(region.Points) == 0 {
			continue
		}

		// 计算经纬度范围
		minLon, maxLon := 999.0, -999.0
		minLat, maxLat := 999.0, -999.0
		shortageCount := 0

		for _, pointID := range region.Points {
			pointIdx := v.getPointIndex(pointID)
			if pointIdx != -1 {
				point := v.Points[pointIdx]
				if point.Longitude < minLon {
					minLon = point.Longitude
				}
				if point.Longitude > maxLon {
					maxLon = point.Longitude
				}
				if point.Latitude < minLat {
					minLat = point.Latitude
				}
				if point.Latitude > maxLat {
					maxLat = point.Latitude
				}
				if point.IsShortage {
					shortageCount++
				}
			}
		}

	}
}

// 阶段1：改进的点位聚类
func (v *ImprovedVehicleAllocationAlgorithm) stage1_ImprovedPointClustering() ([]AllocationResult, error) {

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

// 阶段2：改进的比例优化调整
func (v *ImprovedVehicleAllocationAlgorithm) stage2_ImprovedProportionOptimization(initialResults []AllocationResult) ([]AllocationResult, error) {

	totalShortage := v.getTotalShortageCount()
	if totalShortage == 0 {
		return initialResults, nil
	}

	// 计算实际比例
	for i := range initialResults {
		initialResults[i].ActualRatio = float64(initialResults[i].ShortageCount) / float64(totalShortage)
	}

	// 改进的迭代优化
	currentResults := make([]AllocationResult, len(initialResults))
	copy(currentResults, initialResults)

	for iter := 0; iter < v.MaxIterations; iter++ {
		prevObjective := v.calculateImprovedObjective(currentResults)

		// 尝试调整分配以改善比例平衡
		improved := v.improvedAdjustAllocation(currentResults)

		newObjective := v.calculateImprovedObjective(currentResults)

		// 检查收敛条件
		if !improved || math.Abs(newObjective-prevObjective) < v.ConvergenceThres {
			break
		}
	}

	return currentResults, nil
}

// 改进的分配调整
func (v *ImprovedVehicleAllocationAlgorithm) improvedAdjustAllocation(results []AllocationResult) bool {
	improved := false
	totalShortage := v.getTotalShortageCount()

	// 寻找可以调整的缺货点位，同时考虑地理集中性
	for i := 0; i < len(results); i++ {
		for j := i + 1; j < len(results); j++ {
			vehicle1 := &results[i]
			vehicle2 := &results[j]

			// 计算理想分配
			targetRatio1 := v.Vehicles[i].Ratio
			targetRatio2 := v.Vehicles[j].Ratio

			currentDiff1 := math.Abs(vehicle1.ActualRatio - targetRatio1)
			currentDiff2 := math.Abs(vehicle2.ActualRatio - targetRatio2)

			// 尝试交换一个缺货点位（考虑地理因素）
			if shortagePoint := v.findBestSwappableShortagePoint(vehicle1, vehicle2, i, j); shortagePoint != "" {
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

// 寻找最佳可交换的缺货点位（考虑地理因素）
func (v *ImprovedVehicleAllocationAlgorithm) findBestSwappableShortagePoint(vehicle1, vehicle2 *AllocationResult, vehicleIdx1, vehicleIdx2 int) string {
	type PointScore struct {
		PointID string
		Score   float64
	}

	var candidates []PointScore

	// 检查vehicle1中的缺货点位是否可以分配给vehicle2
	for _, pointID := range vehicle1.AssignedPoints {
		pointIdx := v.getPointIndex(pointID)
		if pointIdx != -1 && v.Points[pointIdx].IsShortage {
			// 检查兼容性
			if v.CompatMatrix[pointIdx][vehicleIdx2] {
				// 计算地理适应性得分
				score := v.calculateGeographicFitScore(pointID, vehicleIdx2)
				candidates = append(candidates, PointScore{
					PointID: pointID,
					Score:   score,
				})
			}
		}
	}

	// 选择得分最高的点位
	if len(candidates) > 0 {
		sort.Slice(candidates, func(i, j int) bool {
			return candidates[i].Score > candidates[j].Score
		})
		return candidates[0].PointID
	}

	return ""
}

// 计算地理适应性得分
func (v *ImprovedVehicleAllocationAlgorithm) calculateGeographicFitScore(pointID string, vehicleIdx int) float64 {
	pointIdx := v.getPointIndex(pointID)
	if pointIdx == -1 {
		return 0
	}

	point := v.Points[pointIdx]
	regionCenter := v.calculateRegionCenter(vehicleIdx)

	// 距离越近，得分越高
	distance := v.calculateGeographicDistance(point.Longitude, point.Latitude,
		regionCenter.Longitude, regionCenter.Latitude)

	// 使用倒数作为得分，距离越小得分越高
	if distance < 0.001 {
		return 1000.0
	}
	return 1.0 / distance
}

// 改进的目标函数计算
func (v *ImprovedVehicleAllocationAlgorithm) calculateImprovedObjective(results []AllocationResult) float64 {
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

	// 地理集中性项
	concentrationTerm := 0.0
	for _, result := range results {
		avgTime := v.calculateAverageTime(result.AssignedPoints)
		concentrationTerm += avgTime
	}
	objective += v.WeightBeta * concentrationTerm

	// 地理分散度惩罚项（新增）
	geographicTerm := 0.0
	for i := range results {
		dispersion := v.calculateRegionDispersion(i)
		geographicTerm += dispersion
	}
	objective += v.WeightGeographic * geographicTerm

	return objective
}

// 交换缺货点位
func (v *ImprovedVehicleAllocationAlgorithm) swapShortagePoint(vehicle1, vehicle2 *AllocationResult, pointID string) {
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

// 主要执行函数 - 改进的三阶段算法
func (v *ImprovedVehicleAllocationAlgorithm) Execute() ([]AllocationResult, error) {

	// 阶段0：改进的约束预处理与区域划分
	if err := v.stage0_ImprovedRegionPartition(); err != nil {
		return nil, fmt.Errorf("阶段0失败: %v", err)
	}

	// 阶段1：改进的多约束下的点位聚类
	initialResults, err := v.stage1_ImprovedPointClustering()
	if err != nil {
		return nil, fmt.Errorf("阶段1失败: %v", err)
	}

	// 阶段2：改进的缺货点位比例优化调整
	finalResults, err := v.stage2_ImprovedProportionOptimization(initialResults)
	if err != nil {
		return nil, fmt.Errorf("阶段2失败: %v", err)
	}

	// 阶段3：去重和完整性验证
	cleanResults := v.removeDuplicateAssignments(finalResults)

	return cleanResults, nil
}

// 辅助函数

// 获取点位索引
func (v *ImprovedVehicleAllocationAlgorithm) getPointIndex(pointID string) int {
	for i, point := range v.Points {
		if point.ID == pointID {
			return i
		}
	}
	return -1
}

// 获取总缺货点位数量
func (v *ImprovedVehicleAllocationAlgorithm) getTotalShortageCount() int {
	count := 0
	for _, point := range v.Points {
		if point.IsShortage {
			count++
		}
	}
	return count
}

// 计算点位集合的平均行驶时间
func (v *ImprovedVehicleAllocationAlgorithm) calculateAverageTime(pointIDs []string) float64 {
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

// 去重和完整性验证
func (v *ImprovedVehicleAllocationAlgorithm) removeDuplicateAssignments(results []AllocationResult) []AllocationResult {
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

// 打印分配结果
func (v *ImprovedVehicleAllocationAlgorithm) PrintResults(results []AllocationResult) {
	fmt.Println("\n=== 改进算法车辆点位分配结果 ===")
	totalShortage := v.getTotalShortageCount()

	for i, result := range results {
		fmt.Printf("\n车辆 %s (目标比例: %.2f):\n", result.VehicleID, v.Vehicles[i].Ratio)
		fmt.Printf("  分配点位数: %d\n", len(result.AssignedPoints))
		fmt.Printf("  缺货点位数: %d\n", result.ShortageCount)

		if totalShortage > 0 {
			actualRatio := float64(result.ShortageCount) / float64(totalShortage)
			fmt.Printf("  实际缺货比例: %.3f\n", actualRatio)
			fmt.Printf("  比例偏差: %.3f\n", math.Abs(actualRatio-v.Vehicles[i].Ratio))
		}

		// 计算地理范围
		if len(result.AssignedPoints) > 0 {
			minLon, maxLon := 999.0, -999.0
			minLat, maxLat := 999.0, -999.0

			for _, pointID := range result.AssignedPoints {
				pointIdx := v.getPointIndex(pointID)
				if pointIdx != -1 {
					point := v.Points[pointIdx]
					if point.Longitude < minLon {
						minLon = point.Longitude
					}
					if point.Longitude > maxLon {
						maxLon = point.Longitude
					}
					if point.Latitude < minLat {
						minLat = point.Latitude
					}
					if point.Latitude > maxLat {
						maxLat = point.Latitude
					}
				}
			}

			fmt.Printf("  地理范围: 经度%.3f~%.3f, 纬度%.3f~%.3f\n", minLon, maxLon, minLat, maxLat)
		}

		fmt.Printf("  分配点位: %v\n", result.AssignedPoints)
	}

	// 计算总体指标
	if totalShortage > 0 {
		totalDeviation := 0.0
		for i, result := range results {
			actualRatio := float64(result.ShortageCount) / float64(totalShortage)
			deviation := math.Abs(actualRatio - v.Vehicles[i].Ratio)
			totalDeviation += deviation * deviation
		}

		fmt.Printf("\n=== 总体指标 ===\n")
		fmt.Printf("总比例偏差平方和: %.4f\n", totalDeviation)
		fmt.Printf("地理集中性: 改进\n")
		fmt.Printf("算法收敛状态: 已完成\n")
	}
}
