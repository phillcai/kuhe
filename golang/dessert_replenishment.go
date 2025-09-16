package main

import (
	"fmt"
	"math"
	"sort"
	"strconv"
)

// 业务常量定义
const (
	// 货道相关常量
	LaneCapacityPerLane = 5 // 每个货道的容量（盒数）

	// 算法权重常量
	DefaultWeightAlpha = 0.5 // 默认比例平衡权重
	DefaultWeightBeta  = 0.2 // 默认货道利用率权重
	DefaultWeightGamma = 0.3 // 默认安全库存惩罚权重

	// 算法参数常量
	DefaultMaxIterations     = 100  // 默认最大迭代次数
	DefaultConvergenceThres  = 0.01 // 默认收敛阈值
	DefaultMaxLaneConstraint = 2    // 默认最大货道约束
	DefaultMinLaneConstraint = 1    // 默认最小货道约束

	// 计算参数常量
	RatioToleranceThreshold  = 0.01 // 比例容差阈值
	WarehouseUtilizationRate = 0.8  // 仓库库存利用率（80%）
)

// 甜品SKU结构体
type DessertSKU struct {
	ID              string  // SKU标识
	CurrentStock    int     // 点位当前剩余数量 G_i
	WarehouseStock  int     // 仓库库存 N_i
	MinStock        int     // 最小库存（安全库存）S_i
	ExpectedRatio   float64 // 预期比例 r_i
	CompatibleLanes []int   // 兼容的货道类型
	Importance      float64 // 重要性权重 w_i
	ActualUsedLanes int     // 实际占用的货道数（从数据中统计）
	InitialLanes    int     // 未分配前的初始货道数（用于强约束计算）
}

// 货道类型结构体
type LaneType struct {
	ID         int // 货道类型ID
	TotalLanes int // 该类型的总货道数 L_t^total
}

// 物理货道结构体 - 新增
type PhysicalLane struct {
	ID               int   // 物理货道ID
	SupportedTypes   []int // 支持的货道类型列表
	CommodityID      int   // 分配的商品ID，0表示未占用
	Quantity         int   // 商品数量，未占用时为0
	ReplenishmentQty int   // 补货量，初始化为0
}

// 检查物理货道是否支持指定的货道类型
func (pl *PhysicalLane) SupportsLaneType(laneTypeID int) bool {
	for _, supportedType := range pl.SupportedTypes {
		if supportedType == laneTypeID {
			return true
		}
	}
	return false
}

// 检查物理货道是否被占用
func (pl *PhysicalLane) IsOccupied() bool {
	return pl.CommodityID != 0
}

// 分配物理货道给指定商品
func (pl *PhysicalLane) AssignToCommodity(commodityID int, quantity int, replenishmentQty int) {
	pl.CommodityID = commodityID
	pl.Quantity = quantity
	pl.ReplenishmentQty = replenishmentQty
}

// 释放物理货道
func (pl *PhysicalLane) Release() {
	pl.CommodityID = 0
	pl.Quantity = 0
	pl.ReplenishmentQty = 0
}

// 甜品分拣分配结果结构体
type DessertAllocationResult struct {
	SKUID            string         // SKU ID
	AllocatedLanes   int            // 分配的货道数 L_i
	LaneCapacity     int            // 货道容量 C_i = LaneCapacityPerLane * L_i
	ReplenishmentQty int            // 补货量 P_i
	FinalStock       int            // 补货后数量 M_i
	CurrentUsedLanes int            // 当前占用货道数 L_i^current
	CanMeetMinStock  bool           // 是否可满足最小库存
	AssignedLanes    []PhysicalLane // 实际分配的物理货道列表
}

// 甜品分拣补货算法类
type DessertReplenishmentAlgorithm struct {
	SKUs                []DessertSKU   // 所有SKU
	LaneTypes           []LaneType     // 货道类型配置
	PhysicalLanes       []PhysicalLane // 物理货道配置（每个货道支持的类型列表）
	TotalLanes          int            // 总货道数 K
	CompatibilityMatrix [][]bool       // 兼容性矩阵 A_{i,t}
	WeightAlpha         float64        // 比例平衡权重
	WeightBeta          float64        // 货道利用率权重
	WeightGamma         float64        // 安全库存惩罚权重
	MaxIterations       int            // 最大迭代次数
	ConvergenceThres    float64        // 收敛阈值
	MaxLaneConstraint   int            // 最大货道约束配置：每个SKU最大允许货道数 = max(初始货道数, MaxLaneConstraint)
	MinLaneConstraint   int            // 最小货道约束配置：每个SKU最小保证货道数
	skuIndexMap         map[string]int // SKU ID到索引的映射，用于快速查找
	isDebug             bool           // 算法实例调试模式
}

// 构造函数
func NewDessertReplenishmentAlgorithm() *DessertReplenishmentAlgorithm {
	return &DessertReplenishmentAlgorithm{
		WeightAlpha:       DefaultWeightAlpha, // 比例平衡权重
		WeightBeta:        DefaultWeightBeta,  // 货道利用率权重
		WeightGamma:       DefaultWeightGamma, // 安全库存惩罚权重
		MaxIterations:     DefaultMaxIterations,
		ConvergenceThres:  DefaultConvergenceThres,
		MaxLaneConstraint: DefaultMaxLaneConstraint, // 默认最大货道约束
		MinLaneConstraint: DefaultMinLaneConstraint, // 默认最小货道约束
		isDebug:           false,                    // 默认关闭调试模式
	}
}

// 设置算法实例调试模式
func (d *DessertReplenishmentAlgorithm) SetDebugMode(debug bool) {
	d.isDebug = debug
}

// 获取算法实例调试模式
func (d *DessertReplenishmentAlgorithm) GetDebugMode() bool {
	return d.isDebug
}

// 算法实例调试打印函数
func (d *DessertReplenishmentAlgorithm) debugPrint(format string, args ...interface{}) {
	if d.isDebug {
		fmt.Printf(format, args...)
	}
}

// 初始化算法数据
func (d *DessertReplenishmentAlgorithm) Initialize(skus []DessertSKU, laneTypes []LaneType, physicalLanes []PhysicalLane) error {
	d.SKUs = skus
	d.LaneTypes = laneTypes
	d.PhysicalLanes = physicalLanes
	d.TotalLanes = len(d.PhysicalLanes)

	// 构建SKU索引映射，用于快速查找
	d.skuIndexMap = make(map[string]int)
	for i, sku := range skus {
		d.skuIndexMap[sku.ID] = i
	}

	// 构建兼容性矩阵
	if err := d.buildCompatibilityMatrix(); err != nil {
		return err
	}
	d.debugPrint("\n=== 所有物理货道状态-Initialize ===\n")
	d.printAllPhysicalLanesStatus()
	return nil
}

// 快速查找SKU索引
func (d *DessertReplenishmentAlgorithm) getSKUIndex(skuID string) int {
	if index, exists := d.skuIndexMap[skuID]; exists {
		return index
	}
	return -1
}

// 设置最小货道约束配置
func (d *DessertReplenishmentAlgorithm) SetMaxLaneConstraint(maxLanes int) error {
	if maxLanes < 1 {
		return fmt.Errorf("最大货道约束不能小于1，当前值: %d", maxLanes)
	}
	d.MaxLaneConstraint = maxLanes
	return nil
}

// 获取当前最大货道约束配置
func (d *DessertReplenishmentAlgorithm) GetMaxLaneConstraint() int {
	return d.MaxLaneConstraint
}

// 设置最小货道约束配置
func (d *DessertReplenishmentAlgorithm) SetMinLaneConstraint(minLanes int) error {
	if minLanes < 0 {
		return fmt.Errorf("最小货道约束不能小于0，当前值: %d", minLanes)
	}
	d.MinLaneConstraint = minLanes
	return nil
}

// 获取当前最小货道约束配置
func (d *DessertReplenishmentAlgorithm) GetMinLaneConstraint() int {
	return d.MinLaneConstraint
}

// 构建兼容性矩阵
func (d *DessertReplenishmentAlgorithm) buildCompatibilityMatrix() error {
	skuCount := len(d.SKUs)
	laneTypeCount := len(d.LaneTypes)

	d.CompatibilityMatrix = make([][]bool, skuCount)
	for i := range d.CompatibilityMatrix {
		d.CompatibilityMatrix[i] = make([]bool, laneTypeCount)
	}

	// 填充兼容性矩阵
	for i, sku := range d.SKUs {
		for j, laneType := range d.LaneTypes {
			d.CompatibilityMatrix[i][j] = d.isCompatible(sku.CompatibleLanes, laneType.ID)
		}
	}

	return nil
}

// 检查SKU与货道类型兼容性
func (d *DessertReplenishmentAlgorithm) isCompatible(compatibleLanes []int, laneTypeID int) bool {
	for _, laneID := range compatibleLanes {
		if laneID == laneTypeID {
			return true
		}
	}
	return false
}

// 获取可用的物理货道（支持指定货道类型且未被占用）
func (d *DessertReplenishmentAlgorithm) getAvailablePhysicalLanes(laneTypeID int) []*PhysicalLane {
	var availableLanes []*PhysicalLane
	for i := range d.PhysicalLanes {
		if !d.PhysicalLanes[i].IsOccupied() && d.PhysicalLanes[i].SupportsLaneType(laneTypeID) {
			availableLanes = append(availableLanes, &d.PhysicalLanes[i])
		}
	}
	return availableLanes
}

// 获取SKU当前占用的物理货道
func (d *DessertReplenishmentAlgorithm) getSKUOccupiedLanes(skuID string, laneTypeID int) []PhysicalLane {
	var occupiedLanes []PhysicalLane
	commodityID, _ := strconv.Atoi(skuID)

	for i := range d.PhysicalLanes {
		if d.PhysicalLanes[i].CommodityID == commodityID &&
			d.PhysicalLanes[i].SupportsLaneType(laneTypeID) {
			occupiedLanes = append(occupiedLanes, d.PhysicalLanes[i])
		}
	}
	return occupiedLanes
}

// 🔧 新增：获取SKU可用的物理货道数量（考虑当前占用情况）
func (d *DessertReplenishmentAlgorithm) getPhysicalAvailableLanesForSKU(skuIndex int) int {
	sku := d.SKUs[skuIndex]
	availableCount := 0

	// 遍历所有物理货道，统计支持该SKU类型且未被占用的货道
	for i := range d.PhysicalLanes {
		physicalLane := &d.PhysicalLanes[i]

		// 检查是否支持该SKU的货道类型
		supportsSKU := false
		for _, compatibleType := range sku.CompatibleLanes {
			if physicalLane.SupportsLaneType(compatibleType) {
				supportsSKU = true
				break
			}
		}

		// 如果支持该SKU且未被占用，则计入可用货道
		if supportsSKU && !physicalLane.IsOccupied() {
			availableCount++
		}
	}

	// 🔧 考虑SKU的初始占用情况：如果SKU已经有初始货道，需要加上这些货道
	// 因为初始货道是强约束，不能被其他SKU占用
	initialOccupiedLanes := sku.InitialLanes
	if initialOccupiedLanes <= 0 && sku.ActualUsedLanes > 0 {
		initialOccupiedLanes = sku.ActualUsedLanes
	}

	totalAvailableLanes := availableCount + initialOccupiedLanes

	d.debugPrint("SKU %s 可用物理货道数: 空闲=%d, 初始占用=%d, 总计=%d\n",
		sku.ID, availableCount, initialOccupiedLanes, totalAvailableLanes)
	return totalAvailableLanes
}

// 分配物理货道给SKU
func (d *DessertReplenishmentAlgorithm) allocatePhysicalLanesToSKU(skuIndex int, laneTypeID int, requiredLanes int) ([]PhysicalLane, error) {
	var assignedLanes []PhysicalLane
	sku := d.SKUs[skuIndex]

	// 首先获取SKU当前占用的货道
	occupiedLanes := d.getSKUOccupiedLanes(sku.ID, laneTypeID)
	assignedLanes = append(assignedLanes, occupiedLanes...)

	// 计算还需要分配的货道数
	additionalLanesNeeded := requiredLanes - len(occupiedLanes)

	if additionalLanesNeeded > 0 {
		// 使用优化的货道选择算法
		selectedLanes, err := d.selectOptimalPhysicalLanes(skuIndex, laneTypeID, additionalLanesNeeded)
		if err != nil {
			return nil, err
		}

		// 分配选中的货道
		for _, lane := range selectedLanes {
			assignedLanes = append(assignedLanes, *lane)
			// 🔧 立即更新物理货道状态，避免后续SKU重复分配
			lane.AssignToCommodity(0, 0, 0) // 先标记为占用，具体数量稍后更新
		}
	}

	return assignedLanes, nil
}

// 优化的物理货道选择算法
func (d *DessertReplenishmentAlgorithm) selectOptimalPhysicalLanes(skuIndex int, laneTypeID int, requiredLanes int) ([]*PhysicalLane, error) {
	sku := d.SKUs[skuIndex]

	// 获取所有可用的物理货道
	availableLanes := d.getAvailablePhysicalLanes(laneTypeID)

	if len(availableLanes) < requiredLanes {
		return nil, fmt.Errorf("SKU %s 需要额外 %d 个货道，但只有 %d 个可用物理货道", sku.ID, requiredLanes, len(availableLanes))
	}

	// 如果可用货道数正好等于需要的货道数，直接返回所有可用货道
	if len(availableLanes) == requiredLanes {
		return availableLanes, nil
	}

	// 使用优化策略选择货道
	selectedLanes := d.optimizeLaneSelection(sku, availableLanes, requiredLanes)

	return selectedLanes, nil
}

// 货道选择优化策略
func (d *DessertReplenishmentAlgorithm) optimizeLaneSelection(sku DessertSKU, availableLanes []*PhysicalLane, requiredLanes int) []*PhysicalLane {
	// 策略1：优先选择支持更多SKU类型的货道（提高灵活性）
	// 策略2：优先选择货道ID较小的货道（保持一致性）
	// 策略3：考虑SKU的重要性权重

	// 为每个可用货道计算优先级分数
	type LaneScore struct {
		lane  *PhysicalLane
		score float64
	}

	var laneScores []LaneScore

	for _, lane := range availableLanes {
		score := d.calculateLaneScore(sku, lane)
		laneScores = append(laneScores, LaneScore{lane: lane, score: score})
	}

	// 按分数降序排序（分数高的优先）
	for i := 0; i < len(laneScores)-1; i++ {
		for j := i + 1; j < len(laneScores); j++ {
			if laneScores[i].score < laneScores[j].score {
				laneScores[i], laneScores[j] = laneScores[j], laneScores[i]
			}
		}
	}

	// 选择前requiredLanes个货道
	var selectedLanes []*PhysicalLane
	for i := 0; i < requiredLanes && i < len(laneScores); i++ {
		selectedLanes = append(selectedLanes, laneScores[i].lane)
	}

	return selectedLanes
}

// 计算货道优先级分数
func (d *DessertReplenishmentAlgorithm) calculateLaneScore(sku DessertSKU, lane *PhysicalLane) float64 {
	score := 0.0

	// 分数1：货道支持的类型数量（支持更多类型 = 更高灵活性）
	typeSupportScore := float64(len(lane.SupportedTypes)) * 10.0
	score += typeSupportScore

	// 分数2：SKU重要性权重
	importanceScore := sku.Importance * 100.0
	score += importanceScore

	// 分数3：货道ID（较小的ID优先，保持一致性）
	laneIDScore := float64(1000 - lane.ID) // 货道ID越小，分数越高
	score += laneIDScore

	// 分数4：货道类型兼容性（如果SKU的兼容类型包含当前货道类型，加分）
	if d.isCompatible(sku.CompatibleLanes, lane.SupportedTypes[0]) {
		compatibilityScore := 50.0
		score += compatibilityScore
	}

	return score
}

// SKU分配信息结构体
type SKUAllocationInfo struct {
	skuIndex      int
	laneTypeID    int
	requiredLanes int
	priority      float64
}

// 全局货道分配优化算法
func (d *DessertReplenishmentAlgorithm) optimizeGlobalLaneAllocation() error {
	// 检查是否有空闲货道可以优化分配
	emptyLanes := d.findEmptyLanes()
	if len(emptyLanes) == 0 {
		d.debugPrint("没有空闲货道，无需优化\n")
		return nil
	}

	d.debugPrint("发现 %d 个空闲货道，开始优化分配\n", len(emptyLanes))

	// 为每个空闲货道寻找最优的SKU进行分配
	allocatedCount := 0
	for _, emptyLane := range emptyLanes {
		bestSKU := d.findBestSKUForLane(emptyLane)
		if bestSKU != nil {
			// 分配货道给最优SKU
			commodityID, err := strconv.Atoi(bestSKU.ID)
			if err != nil {
				d.debugPrint("警告：SKU ID转换失败 %s: %v\n", bestSKU.ID, err)
				continue
			}

			emptyLane.AssignToCommodity(commodityID, 0, 0)
			allocatedCount++
			d.debugPrint("将空闲货道 %d 分配给SKU %s\n", emptyLane.ID, bestSKU.ID)
		}
	}

	d.debugPrint("成功分配了 %d 个空闲货道\n", allocatedCount)
	return nil
}

// 查找所有空闲货道
func (d *DessertReplenishmentAlgorithm) findEmptyLanes() []*PhysicalLane {
	var emptyLanes []*PhysicalLane
	for i := range d.PhysicalLanes {
		if !d.PhysicalLanes[i].IsOccupied() {
			emptyLanes = append(emptyLanes, &d.PhysicalLanes[i])
		}
	}
	return emptyLanes
}

// 为指定货道寻找最优的SKU
func (d *DessertReplenishmentAlgorithm) findBestSKUForLane(lane *PhysicalLane) *DessertSKU {
	var bestSKU *DessertSKU
	bestScore := -1.0

	for i := range d.SKUs {
		sku := &d.SKUs[i]

		// 检查SKU是否与货道兼容
		if !d.isSKUCompatibleWithLane(sku, lane) {
			continue
		}

		// 检查SKU是否还需要更多货道
		if !d.skuNeedsMoreLanes(sku) {
			continue
		}

		// 计算分配分数
		score := d.calculateSKULaneScore(sku, lane)
		if score > bestScore {
			bestScore = score
			bestSKU = sku
		}
	}

	return bestSKU
}

// 检查SKU是否与货道兼容
func (d *DessertReplenishmentAlgorithm) isSKUCompatibleWithLane(sku *DessertSKU, lane *PhysicalLane) bool {
	for _, compatibleType := range sku.CompatibleLanes {
		if lane.SupportsLaneType(compatibleType) {
			return true
		}
	}
	return false
}

// 检查SKU是否还需要更多货道
func (d *DessertReplenishmentAlgorithm) skuNeedsMoreLanes(sku *DessertSKU) bool {
	// 计算SKU当前占用的货道数
	currentLanes := 0
	commodityID, _ := strconv.Atoi(sku.ID)
	for i := range d.PhysicalLanes {
		if d.PhysicalLanes[i].CommodityID == commodityID {
			currentLanes++
		}
	}

	// 计算SKU的最大允许货道数
	maxAllowedLanes := d.calculateMaxAllowedLanes(*sku)

	// 检查是否已经达到最大约束
	if currentLanes >= maxAllowedLanes {
		return false
	}

	// 计算SKU需要的货道数
	requiredLanes := d.calculateRequiredLanesForSKU(*sku)

	return currentLanes < requiredLanes
}

// 计算SKU与货道的分配分数
func (d *DessertReplenishmentAlgorithm) calculateSKULaneScore(sku *DessertSKU, lane *PhysicalLane) float64 {
	score := 0.0

	// 分数1：SKU重要性权重
	score += sku.Importance * 100.0

	// 分数2：SKU预期比例
	score += sku.ExpectedRatio * 50.0

	// 分数3：SKU库存需求（库存越多，优先级越高）
	totalStock := sku.CurrentStock + sku.WarehouseStock
	score += float64(totalStock) * 0.1

	// 分数4：货道支持类型数量（支持更多类型 = 更高灵活性）
	score += float64(len(lane.SupportedTypes)) * 10.0

	return score
}

// 计算SKU需要的货道数
func (d *DessertReplenishmentAlgorithm) calculateRequiredLanesForSKU(sku DessertSKU) int {
	// 基于SKU的实际库存需求计算需要的货道数
	totalStock := sku.CurrentStock + sku.WarehouseStock
	if totalStock > 0 {
		// 计算基于库存需求的货道数
		stockBasedLanes := int(math.Ceil(float64(totalStock) / float64(LaneCapacityPerLane)))

		// 考虑最小库存需求
		minStockLanes := 0
		if sku.MinStock > sku.CurrentStock {
			minStockLanes = int(math.Ceil(float64(sku.MinStock-sku.CurrentStock) / float64(LaneCapacityPerLane)))
		}

		// 取两者中的较大值，确保能满足需求
		requiredLanes := int(math.Max(float64(stockBasedLanes), float64(minStockLanes)))

		// 限制在合理范围内
		maxReasonableLanes := int(math.Ceil(float64(totalStock)/float64(LaneCapacityPerLane))) + 1
		if requiredLanes > maxReasonableLanes {
			requiredLanes = maxReasonableLanes
		}

		return requiredLanes
	}

	// 如果没有库存需求，但SKU存在，至少分配1个货道
	if sku.ExpectedRatio > 0 {
		return 1
	}

	return 0
}

// 释放物理货道
func (d *DessertReplenishmentAlgorithm) releasePhysicalLanes(assignedLanes []PhysicalLane) {
	for _, lane := range assignedLanes {
		// 找到对应的物理货道并释放
		for i := range d.PhysicalLanes {
			if d.PhysicalLanes[i].ID == lane.ID {
				d.PhysicalLanes[i].Release()
				break
			}
		}
	}
}

// 更新物理货道分配信息
func (d *DessertReplenishmentAlgorithm) updatePhysicalLaneAssignment(assignedLanes []PhysicalLane, commodityID int, quantity int, replenishmentQty int) {
	for _, lane := range assignedLanes {
		// 找到对应的物理货道并更新
		for i := range d.PhysicalLanes {
			if d.PhysicalLanes[i].ID == lane.ID {
				d.PhysicalLanes[i].AssignToCommodity(commodityID, quantity, replenishmentQty)
				break
			}
		}
	}
}

// 验证约束可行性
func (d *DessertReplenishmentAlgorithm) validateConstraints() error {
	// 验证每个SKU至少有一种兼容的货道类型
	for i, sku := range d.SKUs {
		hasCompatLane := false
		for j := range d.LaneTypes {
			if d.CompatibilityMatrix[i][j] {
				hasCompatLane = true
				break
			}
		}
		if !hasCompatLane {
			return fmt.Errorf("SKU %s 没有兼容的货道类型", sku.ID)
		}
	}

	// 验证预期比例总和是否为1
	totalRatio := 0.0
	for _, sku := range d.SKUs {
		totalRatio += sku.ExpectedRatio
	}
	if math.Abs(totalRatio-1.0) > RatioToleranceThreshold {
		return fmt.Errorf("预期比例总和不等于1，当前总和: %.3f", totalRatio)
	}

	return nil
}

// 验证分配结果的货道容量约束
func (d *DessertReplenishmentAlgorithm) validateCapacityConstraints(results []DessertAllocationResult) error {
	for i, result := range results {
		// 检查最终库存是否超过货道容量
		if result.FinalStock > result.LaneCapacity {
			return fmt.Errorf("SKU %s 最终库存 %d 超过货道容量 %d (分配货道数: %d)",
				result.SKUID, result.FinalStock, result.LaneCapacity, result.AllocatedLanes)
		}

		// 检查补货量是否超过仓库库存
		sku := d.SKUs[i]
		if result.ReplenishmentQty > sku.WarehouseStock {
			return fmt.Errorf("SKU %s 补货量 %d 超过仓库库存 %d",
				result.SKUID, result.ReplenishmentQty, sku.WarehouseStock)
		}

		// 检查最终库存计算是否正确
		// 如果没有分配货道，最终库存应该为0（因为货道容量为0）
		// 如果分配了货道，最终库存应该是当前库存加上补货量
		var expectedFinalStock int
		if result.AllocatedLanes == 0 {
			expectedFinalStock = 0 // 没有货道，不能存储任何商品
		} else {
			expectedFinalStock = sku.CurrentStock + result.ReplenishmentQty
		}
		if result.FinalStock != expectedFinalStock {
			return fmt.Errorf("SKU %s 最终库存计算错误：期望 %d，实际 %d",
				result.SKUID, expectedFinalStock, result.FinalStock)
		}
	}
	return nil
}

// 步骤1：货道兼容性分析
func (d *DessertReplenishmentAlgorithm) stage1_LaneCompatibilityAnalysis() ([]int, []int, error) {
	currentUsedLanes := make([]int, len(d.SKUs))
	availableLanes := make([]int, len(d.SKUs))

	// 计算每个SKU当前占用货道数，并初始化InitialLanes（如果未设置）
	for i, sku := range d.SKUs {
		// 优先使用实际占用货道数，如果没有则使用数学公式计算
		if sku.ActualUsedLanes > 0 {
			currentUsedLanes[i] = sku.ActualUsedLanes
		} else {
			currentUsedLanes[i] = int(math.Ceil(float64(sku.CurrentStock) / float64(LaneCapacityPerLane)))
		}

		// 如果InitialLanes未设置，使用当前占用货道数作为初始值
		if d.SKUs[i].InitialLanes <= 0 {
			d.SKUs[i].InitialLanes = currentUsedLanes[i]
		}
	}

	// 计算每个SKU的可用货道总数
	// 正确逻辑：每个SKU只能访问支持其类型的物理货道
	for i := range d.SKUs {
		availableLanes[i] = d.getAvailableLanesForSKU(i)
	}

	return currentUsedLanes, availableLanes, nil
}

// 步骤2：初始货道分配
func (d *DessertReplenishmentAlgorithm) stage2_InitialLaneAllocation(currentUsedLanes, availableLanes []int) ([]int, error) {
	allocatedLanes := make([]int, len(d.SKUs))

	// 首先应用需求驱动分配策略
	success := d.demandDrivenAllocation(currentUsedLanes, availableLanes, allocatedLanes)

	if !success {
		// 回退到比例分配策略
		return d.proportionalAllocation(currentUsedLanes, availableLanes)
	}

	return allocatedLanes, nil
}

// 需求驱动分配策略
func (d *DessertReplenishmentAlgorithm) demandDrivenAllocation(currentUsedLanes, availableLanes, allocatedLanes []int) bool {
	// 🔧 使用物理货道预分配策略，确保货道分配的可行性
	return d.physicalLanePreAllocation(currentUsedLanes, availableLanes, allocatedLanes)
}

// 🔧 物理货道预分配策略：在逻辑分配阶段就考虑物理货道的实际可用性
func (d *DessertReplenishmentAlgorithm) physicalLanePreAllocation(currentUsedLanes, availableLanes, allocatedLanes []int) bool {
	d.debugPrint("🔄 开始物理货道预分配策略（填满优先 + 高预期比例优先）\n")

	// 创建物理货道状态副本，用于预分配
	physicalLanesCopy := make([]PhysicalLane, len(d.PhysicalLanes))
	for i := range d.PhysicalLanes {
		physicalLanesCopy[i] = d.PhysicalLanes[i]
	}

	// 创建SKU到货道的映射，记录每个SKU分配的具体货道
	skuToLanesMap := make(map[string][]int)

	// 第一阶段：满足最小约束
	d.debugPrint("📋 第一阶段：满足最小约束\n")
	for i, sku := range d.SKUs {
		// 应用最小约束：不少于MinLaneConstraint
		minGuaranteed := d.calculateMinGuaranteedLanes(sku)
		allocatedLanes[i] = minGuaranteed

		// 获取SKU当前占用的货道
		occupiedLanes := d.getSKUOccupiedLanesFromCopy(sku.ID, physicalLanesCopy)
		alreadyAllocated := len(occupiedLanes)

		// 计算还需要分配的货道数
		additionalNeeded := minGuaranteed - alreadyAllocated

		if additionalNeeded > 0 {
			// 获取可用的物理货道
			availableLanes := d.getAvailablePhysicalLanesFromCopy(sku.CompatibleLanes[0], physicalLanesCopy)

			if len(availableLanes) < additionalNeeded {
				// 如果可用货道不足，调整分配数量
				additionalNeeded = len(availableLanes)
				allocatedLanes[i] = alreadyAllocated + additionalNeeded
				d.debugPrint("SKU %s 最小约束货道不足: 需求=%d, 可用=%d, 调整后=%d\n",
					sku.ID, minGuaranteed, len(availableLanes), allocatedLanes[i])
			}

			// 预分配货道
			commodityID, _ := strconv.Atoi(sku.ID)
			for j := 0; j < additionalNeeded; j++ {
				laneIndex := availableLanes[j]
				physicalLanesCopy[laneIndex].AssignToCommodity(commodityID, 0, 0) // 标记为占用并设置正确的商品ID
				// 记录SKU分配的货道
				skuToLanesMap[sku.ID] = append(skuToLanesMap[sku.ID], laneIndex)
			}
		}

		d.debugPrint("SKU %s 最小约束分配: %d个货道\n", sku.ID, allocatedLanes[i])
	}

	// 第二阶段：填满优先 + 高预期比例优先 + 物理货道约束
	d.debugPrint("📋 第二阶段：填满优先 + 高预期比例优先 + 物理货道约束\n")

	// 按预期比例排序SKU，优先分配比例高的SKU
	skuIndices := make([]int, len(d.SKUs))
	for i := range skuIndices {
		skuIndices[i] = i
	}
	sort.Slice(skuIndices, func(i, j int) bool {
		return d.SKUs[skuIndices[i]].ExpectedRatio > d.SKUs[skuIndices[j]].ExpectedRatio
	})

	// 计算当前已分配的货道总数
	currentTotalAllocated := 0
	for i := range allocatedLanes {
		currentTotalAllocated += allocatedLanes[i]
	}
	remainingPhysicalLanes := d.TotalLanes - currentTotalAllocated
	d.debugPrint("当前已分配货道: %d, 剩余物理货道: %d\n", currentTotalAllocated, remainingPhysicalLanes)

	// 为每个SKU尽可能多地分配货道（填满优先），但不超过物理货道限制
	for _, i := range skuIndices {
		if remainingPhysicalLanes <= 0 {
			d.debugPrint("物理货道已用完，停止分配\n")
			break
		}

		sku := d.SKUs[i]

		// 计算最大允许的货道数
		maxAllowed := d.calculateMaxAllowedLanes(sku)

		// 获取SKU当前占用的货道
		occupiedLanes := d.getSKUOccupiedLanesFromCopy(sku.ID, physicalLanesCopy)
		alreadyAllocated := len(occupiedLanes)

		// 计算还能分配的货道数
		additionalPossible := maxAllowed - alreadyAllocated

		if additionalPossible > 0 {
			// 获取可用的物理货道
			availableLanes := d.getAvailablePhysicalLanesFromCopy(sku.CompatibleLanes[0], physicalLanesCopy)

			// 🔧 关键约束：确保不超过剩余物理货道数
			maxAdditionalByPhysical := remainingPhysicalLanes
			additionalToAllocate := int(math.Min(float64(additionalPossible),
				math.Min(float64(len(availableLanes)), float64(maxAdditionalByPhysical))))

			if additionalToAllocate > 0 {
				// 预分配货道
				commodityID, _ := strconv.Atoi(sku.ID)
				for j := 0; j < additionalToAllocate; j++ {
					physicalLanesCopy[availableLanes[j]].AssignToCommodity(commodityID, 0, 0) // 标记为占用并设置正确的商品ID
				}

				allocatedLanes[i] = alreadyAllocated + additionalToAllocate
				remainingPhysicalLanes -= additionalToAllocate

				d.debugPrint("SKU %s 填满优先分配: 已分配=%d, 新增=%d, 总计=%d (预期比例=%.3f, 剩余物理货道=%d)\n",
					sku.ID, alreadyAllocated, additionalToAllocate, allocatedLanes[i], sku.ExpectedRatio, remainingPhysicalLanes)
			}
		}
	}

	// 第三阶段：剩余货道分配（如果还有未使用的货道）
	d.debugPrint("📋 第三阶段：剩余货道分配\n")
	d.debugPrint("剩余可分配货道数: %d\n", remainingPhysicalLanes)

	if remainingPhysicalLanes > 0 {
		// 再次按预期比例排序，分配剩余货道
		for _, i := range skuIndices {
			if remainingPhysicalLanes <= 0 {
				break
			}

			sku := d.SKUs[skuIndices[i]]

			// 检查是否还能分配更多货道
			maxAllowed := d.calculateMaxAllowedLanes(sku)
			currentAllocated := allocatedLanes[skuIndices[i]]

			if currentAllocated < maxAllowed {
				// 获取可用的物理货道
				availableLanes := d.getAvailablePhysicalLanesFromCopy(sku.CompatibleLanes[0], physicalLanesCopy)

				if len(availableLanes) > 0 {
					// 🔧 关键约束：确保不超过剩余物理货道数
					additionalToAllocate := int(math.Min(1,
						math.Min(float64(len(availableLanes)), float64(remainingPhysicalLanes))))

					if additionalToAllocate > 0 {
						// 预分配货道
						commodityID, _ := strconv.Atoi(sku.ID)
						for j := 0; j < additionalToAllocate; j++ {
							physicalLanesCopy[availableLanes[j]].AssignToCommodity(commodityID, 0, 0) // 标记为占用并设置正确的商品ID
						}

						allocatedLanes[skuIndices[i]] += additionalToAllocate
						remainingPhysicalLanes -= additionalToAllocate

						d.debugPrint("SKU %s 剩余货道分配: +%d, 总计=%d (预期比例=%.3f, 剩余物理货道=%d)\n",
							sku.ID, additionalToAllocate, allocatedLanes[skuIndices[i]], sku.ExpectedRatio, remainingPhysicalLanes)
					}
				}
			}
		}
	}

	// 统计最终分配情况
	finalTotalAllocated := 0
	for i := range allocatedLanes {
		finalTotalAllocated += allocatedLanes[i]
	}
	d.debugPrint("🎯 最终分配结果: 总货道=%d, 已分配=%d, 利用率=%.2f%%\n",
		d.TotalLanes, finalTotalAllocated, float64(finalTotalAllocated)/float64(d.TotalLanes)*100)

	// 🔧 同步physicalLanesCopy的更改到d.PhysicalLanes
	for i := range physicalLanesCopy {
		d.PhysicalLanes[i] = physicalLanesCopy[i]
	}

	return true
}

// 🔧 从物理货道副本中获取SKU当前占用的货道
func (d *DessertReplenishmentAlgorithm) getSKUOccupiedLanesFromCopy(skuID string, physicalLanesCopy []PhysicalLane) []PhysicalLane {
	var occupiedLanes []PhysicalLane
	commodityID, _ := strconv.Atoi(skuID)

	for i := range physicalLanesCopy {
		if physicalLanesCopy[i].CommodityID == commodityID {
			occupiedLanes = append(occupiedLanes, physicalLanesCopy[i])
		}
	}
	return occupiedLanes
}

// 🔧 从物理货道副本中获取可用的物理货道
func (d *DessertReplenishmentAlgorithm) getAvailablePhysicalLanesFromCopy(laneTypeID int, physicalLanesCopy []PhysicalLane) []int {
	var availableLanes []int
	for i := range physicalLanesCopy {
		if !physicalLanesCopy[i].IsOccupied() && physicalLanesCopy[i].SupportsLaneType(laneTypeID) {
			availableLanes = append(availableLanes, i)
		}
	}
	// 🔧 对货道ID进行排序，确保结果的一致性
	sort.Ints(availableLanes)
	return availableLanes
}

// 获取指定货道类型的可用物理货道索引（优先分配专用货道类型）
func (d *DessertReplenishmentAlgorithm) getAvailablePhysicalLanesForSKUType(laneType int) []int {
	// 分别收集专用货道和通用货道
	dedicatedLanes := make([]int, 0) // 只支持单一类型的货道
	universalLanes := make([]int, 0) // 支持多种类型的货道

	for i, lane := range d.PhysicalLanes {
		// 检查货道是否支持指定类型且未被占用
		if lane.SupportsLaneType(laneType) && !lane.IsOccupied() {
			// 判断是否为专用货道（只支持单一类型）
			if len(lane.SupportedTypes) == 1 && lane.SupportedTypes[0] == laneType {
				dedicatedLanes = append(dedicatedLanes, i)
			} else {
				universalLanes = append(universalLanes, i)
			}
		}
	}

	// 优先返回专用货道，然后是通用货道
	availableLanes := make([]int, 0, len(dedicatedLanes)+len(universalLanes))
	availableLanes = append(availableLanes, dedicatedLanes...)
	availableLanes = append(availableLanes, universalLanes...)

	d.debugPrint("SKU类型%d可用货道: 专用=%d个, 通用=%d个, 总计=%d个\n",
		laneType, len(dedicatedLanes), len(universalLanes), len(availableLanes))

	return availableLanes
}

// 按优先级分配货道（优先满足最小库存，然后给没有货道的SKU分配）
func (d *DessertReplenishmentAlgorithm) allocateWithPriority(demandLanes, allocatedLanes, availableLanes []int) bool {
	d.debugPrint("🔄 开始优先级分配策略补货\n")
	// 第一阶段：满足所有SKU的最小库存需求
	remainingLanes := d.TotalLanes
	minStockLanes := make([]int, len(d.SKUs))

	// 创建可变的availableLanes副本，用于跟踪每个SKU类型的剩余货道数
	remainingAvailableLanes := make([]int, len(availableLanes))
	copy(remainingAvailableLanes, availableLanes)

	for i, sku := range d.SKUs {
		minStockLanes[i] = sku.InitialLanes
		allocatedLanes[i] = minStockLanes[i]
		remainingLanes -= minStockLanes[i]
		remainingAvailableLanes[i] -= minStockLanes[i]
	}

	// 如果满足最小库存后还有剩余货道，进行第二阶段分配
	if remainingLanes > 0 {
		// 第二阶段：优先给没有分配货道但有库存需求的SKU分配至少1个货道
		noLaneSKUs := make([]int, 0)
		for i := range d.SKUs {
			if allocatedLanes[i] == 0 && d.SKUs[i].WarehouseStock > 0 {
				// 检查是否可以分配货道（强约束允许且有剩余容量）
				maxAllowed := d.calculateMaxAllowedLanes(d.SKUs[i])
				if maxAllowed > 0 && remainingLanes > 0 {
					noLaneSKUs = append(noLaneSKUs, i)
				}
			}
		}

		// 按预期比例对没有货道的SKU排序（比例高的优先）
		sort.Slice(noLaneSKUs, func(i, j int) bool {
			return d.SKUs[noLaneSKUs[i]].ExpectedRatio > d.SKUs[noLaneSKUs[j]].ExpectedRatio
		})

		// 给没有货道的SKU分配至少1个货道
		for _, i := range noLaneSKUs {
			// 检查该SKU类型的剩余货道数
			skuAvailableLanes := remainingAvailableLanes[i] - allocatedLanes[i]
			// 🔧 新增：同时检查物理货道的实际可用性
			physicalAvailableLanes := d.getPhysicalAvailableLanesForSKU(i)
			actualAvailableLanes := int(math.Min(float64(skuAvailableLanes), float64(physicalAvailableLanes)))

			if actualAvailableLanes > 0 && remainingLanes > 0 {
				// 确保不超过支持该SKU类型的货道数量
				maxAllowed := d.calculateMaxAllowedLanes(d.SKUs[i])
				if maxAllowed >= 1 {
					allocatedLanes[i] = 1
					remainingLanes--
					// 同步扣减该SKU类型的剩余货道数
					remainingAvailableLanes[i] -= 1
				}
			}
		}

		// 第三阶段：将剩余货道按预期比例分配给所有SKU
		if remainingLanes > 0 {
			// 创建所有SKU的索引数组，按预期比例降序排序
			skuIndices := make([]int, len(d.SKUs))
			for i := range skuIndices {
				skuIndices[i] = i
			}

			// 按预期比例从高到低排序
			sort.Slice(skuIndices, func(i, j int) bool {
				return d.SKUs[skuIndices[i]].ExpectedRatio > d.SKUs[skuIndices[j]].ExpectedRatio
			})

			// 分配剩余货道（优先满足需求，但不超过强约束）
			for _, i := range skuIndices {
				if remainingLanes <= 0 {
					break
				}

				// 只给有库存需求的SKU分配额外货道
				if d.SKUs[i].CurrentStock+d.SKUs[i].WarehouseStock > 0 {
					// 计算该SKU还能分配多少货道
					maxAllowed := d.calculateMaxAllowedLanes(d.SKUs[i])
					additionalCapacity := maxAllowed - allocatedLanes[i]
					// 还要考虑该SKU类型的剩余货道数
					skuAvailableLanes := remainingAvailableLanes[i] - allocatedLanes[i]
					// 🔧 新增：同时检查物理货道的实际可用性
					physicalAvailableLanes := d.getPhysicalAvailableLanesForSKU(i)
					actualAvailableLanes := int(math.Min(float64(skuAvailableLanes), float64(physicalAvailableLanes)))
					additionalCapacity = int(math.Min(float64(additionalCapacity), float64(actualAvailableLanes)))

					if additionalCapacity > 0 {
						// 分配额外货道（不超过需求和剩余容量）
						demandGap := demandLanes[i] - allocatedLanes[i]
						additionalAllocation := int(math.Min(float64(demandGap), math.Min(float64(additionalCapacity), float64(remainingLanes))))

						if additionalAllocation > 0 {
							allocatedLanes[i] += additionalAllocation
							remainingLanes -= additionalAllocation
							// 同步扣减该SKU类型的剩余货道数
							remainingAvailableLanes[i] -= additionalAllocation
						}
					}
				}
			}
		}
	}

	return true
}

// 比例分配策略（回退策略）
func (d *DessertReplenishmentAlgorithm) proportionalAllocation(currentUsedLanes, availableLanes []int) ([]int, error) {
	d.debugPrint("🔄 开始按比例分配策略补货\n")
	allocatedLanes := make([]int, len(d.SKUs))

	// 预先分配现有货道
	reservedLanes := 0
	for i := range d.SKUs {
		// 只有当SKU有库存需求时才分配货道
		// 计算最小保证货道数
		minGuaranteed := d.calculateMinGuaranteedLanes(d.SKUs[i])
		if d.SKUs[i].CurrentStock+d.SKUs[i].WarehouseStock > 0 {
			// 计算最大允许货道数
			maxAllowed := d.calculateMaxAllowedLanes(d.SKUs[i])
			// 分配货道数：至少为最小保证数，但不超过最大允许数
			// 分配货道数：取当前占用货道数和min(最大允许货道数, max(最小保证货道数, 1))中的较大值
			allocatedLanes[i] = int(math.Max(
				float64(currentUsedLanes[i]),
				math.Min(float64(maxAllowed), math.Max(float64(minGuaranteed), 1)),
			))
		} else {
			// 没有库存需求，不分配货道
			allocatedLanes[i] = int(math.Max(float64(currentUsedLanes[i]), float64(minGuaranteed)))
		}
		reservedLanes += allocatedLanes[i]
	}

	remainingLanes := d.TotalLanes - reservedLanes
	if remainingLanes < 0 {
		return nil, fmt.Errorf("当前占用货道数超过总货道数")
	}

	// 计算调整后比例（排除无兼容货道的SKU）
	adjustedRatios := make([]float64, len(d.SKUs))
	totalAdjustedRatio := 0.0

	for i, sku := range d.SKUs {
		if availableLanes[i] > currentUsedLanes[i] {
			adjustedRatios[i] = sku.ExpectedRatio
			totalAdjustedRatio += sku.ExpectedRatio
		}
	}

	// 创建所有SKU的索引数组，按预期比例降序排序
	allSkuIndices := make([]int, len(d.SKUs))
	for i := range allSkuIndices {
		allSkuIndices[i] = i
	}

	// 按预期比例从高到低排序
	sort.Slice(allSkuIndices, func(i, j int) bool {
		return d.SKUs[allSkuIndices[i]].ExpectedRatio > d.SKUs[allSkuIndices[j]].ExpectedRatio
	})

	remainingToAllocate := remainingLanes

	// 阶段1：按预期比例优先级保障SKU丰富度 - 每个有库存的SKU至少1个货道
	for _, i := range allSkuIndices {
		if remainingToAllocate <= 0 {
			break
		}

		sku := d.SKUs[i]
		// 只为有库存需求且还没有分配货道的SKU分配
		if sku.CurrentStock+sku.WarehouseStock > 0 && allocatedLanes[i] == 0 {
			// 检查强约束和兼容性
			maxAllowed := d.calculateMaxAllowedLanes(sku)
			if maxAllowed >= 1 && availableLanes[i] > 0 {
				// 至少分配1个货道，但不超过支持该SKU类型的货道数量
				allocatedLanes[i] = int(math.Min(1.0, float64(maxAllowed)))
				remainingToAllocate--
			}
		}
	}

	// 阶段2：继续按优先级分配剩余货道，直到没有可用货道
	for remainingToAllocate > 0 {
		allocated := false

		for _, i := range allSkuIndices {
			if remainingToAllocate <= 0 {
				break
			}

			sku := d.SKUs[i]
			// 检查是否还能分配更多货道（只给有库存需求的SKU）
			if sku.CurrentStock+sku.WarehouseStock > 0 && availableLanes[i] > allocatedLanes[i] {
				maxAllowed := d.calculateMaxAllowedLanes(sku)
				if allocatedLanes[i] < maxAllowed {
					allocatedLanes[i]++
					remainingToAllocate--
					allocated = true
				}
			}
		}

		// 如果这一轮没有分配任何货道，说明所有SKU都达到了约束上限
		if !allocated {
			break
		}
	}

	// SKU丰富度保障已经在上面的阶段1中处理，这里不需要重复逻辑

	// 检查总分配是否超出限制，如果超出则进行调整
	totalAllocatedAfter := 0
	for _, lanes := range allocatedLanes {
		totalAllocatedAfter += lanes
	}

	// 如果超出限制，进行调整
	if totalAllocatedAfter > d.TotalLanes {
		excess := totalAllocatedAfter - d.TotalLanes

		// 从非当前占用的分配中减少，从后往前处理
		for i := len(d.SKUs) - 1; i >= 0 && excess > 0; i-- {
			if allocatedLanes[i] > currentUsedLanes[i] {
				reduction := int(math.Min(float64(excess), float64(allocatedLanes[i]-currentUsedLanes[i])))
				allocatedLanes[i] -= reduction
				excess -= reduction
			}
		}
	}

	return allocatedLanes, nil
}

// 步骤3：最小库存优先处理
func (d *DessertReplenishmentAlgorithm) stage3_MinStockPriorityProcessing(allocatedLanes, currentUsedLanes []int) ([]DessertAllocationResult, error) {
	results := make([]DessertAllocationResult, len(d.SKUs))

	for i, sku := range d.SKUs {
		result := DessertAllocationResult{
			SKUID:            sku.ID,
			AllocatedLanes:   allocatedLanes[i],
			LaneCapacity:     allocatedLanes[i] * LaneCapacityPerLane,
			CurrentUsedLanes: currentUsedLanes[i],     // 使用之前计算的实际占用货道数
			AssignedLanes:    make([]PhysicalLane, 0), // 初始化物理货道分配列表
		}

		// 检查是否可满足最小库存
		result.CanMeetMinStock = (sku.WarehouseStock + sku.CurrentStock) >= sku.MinStock

		if allocatedLanes[i] == 0 {
			// 如果没有分配货道，不能补货，最终库存为0
			result.FinalStock = 0
			result.ReplenishmentQty = 0 // 不能补货
		} else if result.CanMeetMinStock {
			// 有货道分配且可满足最小库存：在满足最小库存的前提下，尽量填满货道容量

			// 第一步：计算必须满足的最小库存
			minRequiredStock := int(math.Max(float64(sku.MinStock), float64(sku.CurrentStock)))

			// 第二步：计算尽量填满货道的目标库存
			// 限制条件：不超过货道容量、不超过仓库总库存
			maxByCapacity := result.LaneCapacity
			maxByWarehouse := sku.CurrentStock + sku.WarehouseStock
			maxFillableStock := int(math.Min(float64(maxByCapacity), float64(maxByWarehouse)))

			// 第三步：选择填满策略 - 直接尝试填满货道（受仓库库存限制）
			targetStock := maxFillableStock

			// 确保不低于最小库存要求，但也不能超过货道容量
			targetStock = int(math.Max(float64(targetStock), float64(minRequiredStock)))
			targetStock = int(math.Min(float64(targetStock), float64(maxByCapacity)))

			result.FinalStock = targetStock
		} else {
			// 有货道分配但无法满足最小库存：尽力而为，填满仓库库存或货道容量
			maxByCapacity := result.LaneCapacity
			maxByWarehouse := sku.CurrentStock + sku.WarehouseStock
			result.FinalStock = int(math.Min(float64(maxByCapacity), float64(maxByWarehouse)))
		}

		// 只有在分配了货道的情况下才需要计算补货量
		if allocatedLanes[i] > 0 {
			// 计算补货量
			result.ReplenishmentQty = int(math.Max(0, float64(result.FinalStock-sku.CurrentStock)))

			// 确保不超过仓库库存
			result.ReplenishmentQty = int(math.Min(float64(result.ReplenishmentQty), float64(sku.WarehouseStock)))

			// 重新计算最终库存，确保一致性
			result.FinalStock = sku.CurrentStock + result.ReplenishmentQty

			// 最后的安全检查：确保不超过货道容量
			if result.FinalStock > result.LaneCapacity {
				// 如果超过容量，调整补货量
				result.FinalStock = result.LaneCapacity
				result.ReplenishmentQty = result.FinalStock - sku.CurrentStock
				// 确保补货量不为负
				if result.ReplenishmentQty < 0 {
					result.ReplenishmentQty = 0
					result.FinalStock = sku.CurrentStock
				}
			}

			// 🔧 使用真实的物理货道分配
			// 根据预分配的结果，找到对应的真实物理货道并分配给SKU
			if len(sku.CompatibleLanes) > 0 {
				// 获取该SKU已经占用的物理货道
				commodityID, _ := strconv.Atoi(sku.ID)
				assignedLanes := make([]PhysicalLane, 0)

				// 遍历所有物理货道，找到分配给当前SKU的货道
				for _, lane := range d.PhysicalLanes {
					if lane.IsOccupied() && lane.CommodityID == commodityID {
						assignedLanes = append(assignedLanes, lane)
					}
				}

				// 更新实际分配的货道数（包括全局优化分配的货道）
				actualAllocatedLanes := len(assignedLanes)
				if actualAllocatedLanes > 0 {
					// 只更新result，不更新allocatedLanes数组，避免重复计算
					result.AllocatedLanes = actualAllocatedLanes
				}

				// 如果找到的货道数不足，尝试分配新的货道
				if len(assignedLanes) < allocatedLanes[i] {
					// 获取可用的物理货道
					availableLanes := d.getAvailablePhysicalLanesForSKUType(sku.CompatibleLanes[0])
					needed := allocatedLanes[i] - len(assignedLanes)

					for k := 0; k < needed && k < len(availableLanes); k++ {
						laneIndex := availableLanes[k]
						// 分配物理货道
						d.PhysicalLanes[laneIndex].AssignToCommodity(commodityID, 0, 0) // 先标记为占用
						assignedLanes = append(assignedLanes, d.PhysicalLanes[laneIndex])
					}
				}

				// 重新计算实际分配的货道数
				actualAllocatedLanes = len(assignedLanes)
				if actualAllocatedLanes > 0 {
					result.AllocatedLanes = actualAllocatedLanes
				}

				// 🔧 修复：基于每个货道的当前库存和容量计算补货量
				laneCount := len(assignedLanes)
				if laneCount > 0 {
					// 计算总需要补货的数量
					totalReplenishmentNeeded := result.ReplenishmentQty

					// 为每个货道计算补货量
					for j := 0; j < laneCount; j++ {
						currentLaneStock := assignedLanes[j].Quantity
						maxLaneCapacity := LaneCapacityPerLane

						// 计算该货道可以补货的数量
						availableCapacity := maxLaneCapacity - currentLaneStock

						// 如果货道已满，不能补货
						if availableCapacity <= 0 {
							assignedLanes[j].ReplenishmentQty = 0
							// 保持当前库存不变
							continue
						}

						// 计算该货道应该补货的数量
						// 优先填满容量较小的货道
						laneReplenishment := int(math.Min(float64(availableCapacity), float64(totalReplenishmentNeeded)))

						// 更新货道的库存和补货量
						assignedLanes[j].Quantity = currentLaneStock + laneReplenishment
						assignedLanes[j].ReplenishmentQty = laneReplenishment

						// 减少剩余需要补货的数量
						totalReplenishmentNeeded -= laneReplenishment

						// 如果已经补够了，停止
						if totalReplenishmentNeeded <= 0 {
							break
						}
					}

					// 同步更新物理货道状态
					for j := 0; j < laneCount; j++ {
						for k := range d.PhysicalLanes {
							if d.PhysicalLanes[k].ID == assignedLanes[j].ID {
								d.PhysicalLanes[k].Quantity = assignedLanes[j].Quantity
								d.PhysicalLanes[k].ReplenishmentQty = assignedLanes[j].ReplenishmentQty
								break
							}
						}
					}
				}

				result.AssignedLanes = assignedLanes
				d.debugPrint("SKU %s 最终分配货道数: %d\n", sku.ID, len(assignedLanes))
			}
		}

		results[i] = result
	}

	return results, nil
}

// 步骤4：比例平衡补货量计算
func (d *DessertReplenishmentAlgorithm) stage4_ProportionalReplenishmentCalculation(initialResults []DessertAllocationResult) ([]DessertAllocationResult, error) {
	results := make([]DessertAllocationResult, len(initialResults))
	copy(results, initialResults)

	totalTargetStock := d.calculateTargetTotalStock()

	// 计算理想分配
	for i, sku := range d.SKUs {
		// 如果没有分配货道，保持最终库存为0
		if results[i].AllocatedLanes == 0 {
			results[i].FinalStock = 0
			results[i].ReplenishmentQty = 0
			continue
		}

		idealStock := int(sku.ExpectedRatio * float64(totalTargetStock))

		// 应用约束条件
		maxByCapacity := results[i].LaneCapacity
		maxByWarehouse := sku.CurrentStock + sku.WarehouseStock
		minByMinStock := int(math.Min(float64(results[i].FinalStock), float64(maxByCapacity))) // 已分配的最小库存（stage3的填满值），但不能超过容量

		// 计算最终库存，严格约束在货道容量内
		finalStock := int(math.Min(float64(idealStock), float64(maxByCapacity)))
		finalStock = int(math.Min(float64(finalStock), float64(maxByWarehouse)))
		finalStock = int(math.Max(float64(finalStock), float64(minByMinStock)))

		// 再次确保不超过货道容量（最终的强制约束）
		finalStock = int(math.Min(float64(finalStock), float64(maxByCapacity)))

		results[i].FinalStock = finalStock
		results[i].ReplenishmentQty = finalStock - sku.CurrentStock

		// 确保补货量非负
		if results[i].ReplenishmentQty < 0 {
			results[i].ReplenishmentQty = 0
			results[i].FinalStock = sku.CurrentStock
		}

		// 最后的容量约束检查：确保不超过货道容量
		if results[i].FinalStock > results[i].LaneCapacity {
			results[i].FinalStock = results[i].LaneCapacity
			results[i].ReplenishmentQty = results[i].FinalStock - sku.CurrentStock
			if results[i].ReplenishmentQty < 0 {
				results[i].ReplenishmentQty = 0
				results[i].FinalStock = sku.CurrentStock
			}
		}
	}

	return results, nil
}

// 步骤5：动态调整优化
func (d *DessertReplenishmentAlgorithm) stage5_DynamicOptimization(initialResults []DessertAllocationResult) ([]DessertAllocationResult, error) {
	results := make([]DessertAllocationResult, len(initialResults))
	copy(results, initialResults)

	for iter := 0; iter < d.MaxIterations; iter++ {
		prevObjective := d.calculateObjective(results)

		// 尝试调整分配以改善目标函数
		improved := d.adjustAllocation(results)

		// 在每次调整后强制验证容量约束
		d.enforceCapacityConstraints(results)

		newObjective := d.calculateObjective(results)

		// 检查收敛条件
		if !improved || math.Abs(newObjective-prevObjective) < d.ConvergenceThres {
			break
		}
	}

	return results, nil
}

// 强制执行容量约束
func (d *DessertReplenishmentAlgorithm) enforceCapacityConstraints(results []DessertAllocationResult) {
	for i := range results {
		// 如果没有分配货道，确保最终库存为0
		if results[i].AllocatedLanes == 0 {
			results[i].FinalStock = 0
			results[i].ReplenishmentQty = 0
			continue
		}

		if results[i].FinalStock > results[i].LaneCapacity {
			// 强制调整到货道容量限制
			results[i].FinalStock = results[i].LaneCapacity
			results[i].ReplenishmentQty = results[i].FinalStock - d.SKUs[i].CurrentStock

			// 确保补货量不为负
			if results[i].ReplenishmentQty < 0 {
				results[i].ReplenishmentQty = 0
				results[i].FinalStock = d.SKUs[i].CurrentStock
			}
		}
	}
}

// 调整分配以改善目标函数
func (d *DessertReplenishmentAlgorithm) adjustAllocation(results []DessertAllocationResult) bool {
	improved := false
	totalStock := d.getTotalFinalStock(results)

	// 寻找可以调整的机会
	for i := 0; i < len(results); i++ {
		for j := i + 1; j < len(results); j++ {
			if d.canImproveBySwap(results, i, j, totalStock) {
				d.performSwap(results, i, j)
				improved = true
			}
		}
	}

	return improved
}

// 检查是否可以通过交换改善目标函数
func (d *DessertReplenishmentAlgorithm) canImproveBySwap(results []DessertAllocationResult, i, j int, totalStock int) bool {
	// 计算当前比例偏差
	currentDeviation := d.calculateProportionDeviation(results, totalStock)

	// 模拟交换1个单位
	if results[i].ReplenishmentQty > 0 && results[j].ReplenishmentQty < d.SKUs[j].WarehouseStock {
		// 模拟调整
		results[i].ReplenishmentQty--
		results[i].FinalStock--
		results[j].ReplenishmentQty++
		results[j].FinalStock++

		newDeviation := d.calculateProportionDeviation(results, totalStock)

		// 恢复原状
		results[i].ReplenishmentQty++
		results[i].FinalStock++
		results[j].ReplenishmentQty--
		results[j].FinalStock--

		return newDeviation < currentDeviation
	}

	return false
}

// 执行交换
func (d *DessertReplenishmentAlgorithm) performSwap(results []DessertAllocationResult, i, j int) {
	// 计算填满策略的最小库存（不低于这个值）
	minFillStock_i := int(math.Min(float64(results[i].LaneCapacity), float64(d.SKUs[i].CurrentStock+d.SKUs[i].WarehouseStock)))
	minFillStock_i = int(math.Max(float64(minFillStock_i), float64(d.SKUs[i].MinStock)))

	maxFillStock_j := int(math.Min(float64(results[j].LaneCapacity), float64(d.SKUs[j].CurrentStock+d.SKUs[j].WarehouseStock)))

	// 只有在不违反填满策略和容量约束的情况下才允许交换
	if results[i].ReplenishmentQty > 0 &&
		results[j].ReplenishmentQty < d.SKUs[j].WarehouseStock &&
		results[i].FinalStock > minFillStock_i && // 确保不低于填满策略设定的下界
		results[j].FinalStock < maxFillStock_j && // 确保不超过填满策略设定的上界
		results[j].FinalStock+1 <= results[j].LaneCapacity { // 确保交换后j不超过货道容量

		results[i].ReplenishmentQty--
		results[i].FinalStock--
		results[j].ReplenishmentQty++
		results[j].FinalStock++

		// 双重检查：如果交换后超过容量，回滚交换
		if results[j].FinalStock > results[j].LaneCapacity {
			results[i].ReplenishmentQty++
			results[i].FinalStock++
			results[j].ReplenishmentQty--
			results[j].FinalStock--
		}
	}
}

// 计算目标函数值
func (d *DessertReplenishmentAlgorithm) calculateObjective(results []DessertAllocationResult) float64 {
	totalStock := d.getTotalFinalStock(results)

	// 比例偏差项
	proportionTerm := d.calculateProportionDeviation(results, totalStock)

	// 货道利用率项
	utilizationTerm := float64(d.getTotalAllocatedLanes(results))

	// 安全库存惩罚项
	safetyPenalty := 0.0
	for i, result := range results {
		if result.FinalStock < d.SKUs[i].MinStock {
			penalty := float64(d.SKUs[i].MinStock-result.FinalStock) * d.SKUs[i].Importance
			safetyPenalty += penalty
		}
	}

	return d.WeightAlpha*proportionTerm - d.WeightBeta*utilizationTerm + d.WeightGamma*safetyPenalty
}

// 计算比例偏差
func (d *DessertReplenishmentAlgorithm) calculateProportionDeviation(results []DessertAllocationResult, totalStock int) float64 {
	if totalStock == 0 {
		return 0
	}

	deviation := 0.0
	for i := range results {
		for j := i + 1; j < len(results); j++ {
			actualRatio1 := float64(results[i].FinalStock) / float64(totalStock)
			actualRatio2 := float64(results[j].FinalStock) / float64(totalStock)
			expectedRatio1 := d.SKUs[i].ExpectedRatio
			expectedRatio2 := d.SKUs[j].ExpectedRatio

			if expectedRatio2 != 0 {
				actualProportion := actualRatio1 / actualRatio2
				expectedProportion := expectedRatio1 / expectedRatio2
				deviation += math.Abs(actualProportion-expectedProportion) * expectedRatio2
			}
		}
	}

	return deviation
}

// 辅助函数

// 计算支持指定SKU类型的货道总数量
func (d *DessertReplenishmentAlgorithm) getAvailableLanesForSKU(skuIndex int) int {
	// 在共享货道系统中，使用货道类型的总数量
	// 因为每个货道类型都可以使用所有声明的货道
	sku := d.SKUs[skuIndex]

	// 找到该SKU兼容的货道类型
	for _, laneType := range d.LaneTypes {
		for _, compatibleType := range sku.CompatibleLanes {
			if laneType.ID == compatibleType {
				// 返回该货道类型的总货道数
				return laneType.TotalLanes
			}
		}
	}

	// 如果找不到兼容的货道类型，返回总货道数作为备选
	d.debugPrint("SKU %s 可用货道数: %d (备选)\n", sku.ID, 0)
	return 0
}

// 计算SKU的最大允许货道数（强约束）
// 计算SKU的最大允许货道数，考虑最小和最大约束
// 约束条件：MinLaneConstraint ≤ AllocatedLanes ≤ max(InitialLanes, MaxLaneConstraint) ≤ AvailableLanes
func (d *DessertReplenishmentAlgorithm) calculateMaxAllowedLanes(sku DessertSKU) int {
	initialLanes := sku.InitialLanes
	if initialLanes <= 0 {
		// 如果没有设置InitialLanes，使用ActualUsedLanes作为备选
		if sku.ActualUsedLanes > 0 {
			initialLanes = sku.ActualUsedLanes
		} else {
			// 最后备选：根据当前库存计算
			initialLanes = int(math.Ceil(float64(sku.CurrentStock) / float64(LaneCapacityPerLane)))
		}
	}

	// 使用快速查找获取SKU索引
	skuIndex := d.getSKUIndex(sku.ID)
	var availableLanes int
	if skuIndex >= 0 {
		availableLanes = d.getAvailableLanesForSKU(skuIndex)
	} else {
		// 如果找不到SKU索引，使用总货道数作为备选
		availableLanes = d.TotalLanes
	}

	// 计算最大约束：max(初始货道数, MaxLaneConstraint)
	maxByConstraint := int(math.Max(float64(initialLanes), float64(d.MaxLaneConstraint)))

	// 初始货道数不应该被减少，这是强约束
	// 如果SKU有初始货道数，至少保持初始货道数
	if initialLanes > 0 {
		// 确保不超过支持该SKU类型的货道数量
		return int(math.Min(float64(maxByConstraint), float64(availableLanes)))
	}

	// 如果没有初始货道数，才考虑库存需求约束
	maxNeededLanes := 0
	if sku.CurrentStock+sku.WarehouseStock > 0 {
		maxNeededLanes = int(math.Ceil(float64(sku.CurrentStock+sku.WarehouseStock) / float64(LaneCapacityPerLane)))
	}

	// 取三个约束的最小值：强约束、可用货道数、库存需求货道数
	return int(math.Min(float64(maxByConstraint), math.Min(float64(availableLanes), float64(maxNeededLanes))))
}

// 计算SKU的最小保证货道数
// 约束条件：MinLaneConstraint ≤ AllocatedLanes
func (d *DessertReplenishmentAlgorithm) calculateMinGuaranteedLanes(sku DessertSKU) int {
	// 最小保证货道数至少为MinLaneConstraint
	minGuaranteed := d.MinLaneConstraint

	// 如果SKU有初始货道数，不能少于初始货道数
	if sku.InitialLanes > 0 {
		minGuaranteed = int(math.Max(float64(minGuaranteed), float64(sku.InitialLanes)))
	}

	// 使用快速查找获取SKU索引
	skuIndex := d.getSKUIndex(sku.ID)
	var availableLanes int
	if skuIndex >= 0 {
		availableLanes = d.getAvailableLanesForSKU(skuIndex)
	} else {
		// 如果找不到SKU索引，使用总货道数作为备选
		availableLanes = d.TotalLanes
	}
	minGuaranteed = int(math.Min(float64(minGuaranteed), float64(availableLanes)))

	return minGuaranteed
}

// 计算目标总补货量
func (d *DessertReplenishmentAlgorithm) calculateTargetReplenishment() float64 {
	// 目标总补货量 = 货道总容量 - 当前总库存
	totalCapacity := d.getTotalMaxCapacity() // 总货道数 * 每个货道容量
	totalCurrent := 0
	for _, sku := range d.SKUs {
		totalCurrent += sku.CurrentStock
	}

	targetReplenishment := float64(totalCapacity - totalCurrent)

	// 确保目标补货量不为负数
	if targetReplenishment < 0 {
		targetReplenishment = 0
	}

	return targetReplenishment
}

// 计算目标总库存
func (d *DessertReplenishmentAlgorithm) calculateTargetTotalStock() int {
	totalCurrent := 0
	for _, sku := range d.SKUs {
		totalCurrent += sku.CurrentStock
	}
	return totalCurrent + int(d.calculateTargetReplenishment())
}

// 获取总最终库存
func (d *DessertReplenishmentAlgorithm) getTotalFinalStock(results []DessertAllocationResult) int {
	total := 0
	for _, result := range results {
		total += result.FinalStock
	}
	return total
}

// 获取总分配货道数
func (d *DessertReplenishmentAlgorithm) getTotalAllocatedLanes(results []DessertAllocationResult) int {
	total := 0
	for _, result := range results {
		total += result.AllocatedLanes
	}
	return total
}

// 计算总的理论最大容量（总货道数 × 每个货道容量）
func (d *DessertReplenishmentAlgorithm) getTotalMaxCapacity() int {
	return d.TotalLanes * LaneCapacityPerLane
}

// 验证并修正总库存容量限制
func (d *DessertReplenishmentAlgorithm) validateAndFixTotalCapacity(results []DessertAllocationResult) error {
	maxCapacity := d.getTotalMaxCapacity()

	for {
		totalFinalStock := d.getTotalFinalStock(results)

		if totalFinalStock <= maxCapacity {
			break // 满足容量限制，退出循环
		}

		// 总库存超限，需要减少补货量
		excess := totalFinalStock - maxCapacity

		// 优先从没有分配货道的SKU中减少库存
		reduced := d.reduceStockFromUnallocatedSKUs(results, excess)
		if reduced >= excess {
			continue // 已解决问题，重新检查
		}

		// 如果还有剩余超量，从分配了货道但当前库存较高的SKU中减少
		remainingExcess := excess - reduced
		d.reduceStockFromAllocatedSKUs(results, remainingExcess)
	}

	return nil
}

// 从没有分配货道的SKU中减少库存
func (d *DessertReplenishmentAlgorithm) reduceStockFromUnallocatedSKUs(results []DessertAllocationResult, targetReduction int) int {
	actualReduction := 0

	for i := range results {
		if targetReduction <= 0 {
			break
		}

		// 只处理没有分配货道的SKU
		if results[i].AllocatedLanes == 0 {
			// 没有分配货道的SKU不应该有库存，直接设置为0
			if results[i].FinalStock > 0 {
				reduction := results[i].FinalStock
				results[i].FinalStock = 0
				results[i].ReplenishmentQty = 0
				actualReduction += reduction
				targetReduction -= reduction
			}
		}
	}

	return actualReduction
}

// 从分配了货道的SKU中减少库存
func (d *DessertReplenishmentAlgorithm) reduceStockFromAllocatedSKUs(results []DessertAllocationResult, targetReduction int) {
	for i := range results {
		if targetReduction <= 0 {
			break
		}

		// 只处理分配了货道的SKU
		if results[i].AllocatedLanes > 0 {
			sku := d.SKUs[i]

			// 计算可以减少的量（保留最小库存）
			minStock := int(math.Max(float64(sku.MinStock), float64(sku.CurrentStock)))
			maxReduction := results[i].FinalStock - minStock

			if maxReduction > 0 {
				reduction := int(math.Min(float64(maxReduction), float64(targetReduction)))
				results[i].FinalStock -= reduction
				results[i].ReplenishmentQty -= reduction

				// 确保补货量不为负
				if results[i].ReplenishmentQty < 0 {
					results[i].ReplenishmentQty = 0
					results[i].FinalStock = sku.CurrentStock
				}

				targetReduction -= reduction
			}
		}
	}
}

// 主要执行函数
func (d *DessertReplenishmentAlgorithm) Execute() ([]DessertAllocationResult, error) {
	// 打印最大和最小货道约束
	d.debugPrint("最大货道总数约束: %d\n", d.TotalLanes)
	d.debugPrint("所有SKU最小货道约束总和: %d\n", d.GetMinLaneConstraint())
	d.debugPrint("所有SKU最大货道约束总和: %d\n", d.GetMaxLaneConstraint())
	// 步骤0：验证约束条件
	err := d.validateConstraints()
	if err != nil {
		return nil, fmt.Errorf("约束验证失败: %v", err)
	}

	// 步骤1：货道兼容性分析
	currentUsedLanes, availableLanes, err := d.stage1_LaneCompatibilityAnalysis()
	if err != nil {
		return nil, fmt.Errorf("步骤1失败: %v", err)
	}

	// 步骤2：初始货道分配
	allocatedLanes, err := d.stage2_InitialLaneAllocation(currentUsedLanes, availableLanes)
	if err != nil {
		return nil, fmt.Errorf("步骤2失败: %v", err)
	}

	// 步骤2.5：全局货道分配优化（新增）
	d.debugPrint("\n=== 执行全局货道分配优化 ===\n")
	err = d.optimizeGlobalLaneAllocation()
	if err != nil {
		d.debugPrint("警告：全局货道分配优化失败: %v\n", err)
		// 记录错误但不中断执行，继续使用原有分配结果
		d.debugPrint("全局优化失败，使用原有分配结果继续执行\n")
	} else {
		d.debugPrint("全局货道分配优化完成\n")
	}

	// 步骤3：最小库存优先处理
	initialResults, err := d.stage3_MinStockPriorityProcessing(allocatedLanes, currentUsedLanes)
	if err != nil {
		return nil, fmt.Errorf("步骤3失败: %v", err)
	}

	// 在步骤3后立即强制执行容量约束
	d.enforceCapacityConstraints(initialResults)

	// 步骤4：比例平衡补货量计算（在填满策略基础上进行微调）
	balancedResults, err := d.stage4_ProportionalReplenishmentCalculation(initialResults)
	if err != nil {
		return nil, fmt.Errorf("步骤4失败: %v", err)
	}

	// 在步骤4后强制执行容量约束
	d.enforceCapacityConstraints(balancedResults)

	// 步骤5：动态调整优化
	finalResults, err := d.stage5_DynamicOptimization(balancedResults)
	if err != nil {
		return nil, fmt.Errorf("步骤5失败: %v", err)
	}

	// 步骤6：验证并修正总容量约束
	err = d.validateAndFixTotalCapacity(finalResults)
	if err != nil {
		return nil, fmt.Errorf("容量修正失败: %v", err)
	}

	// 步骤7：验证货道容量约束
	err = d.validateCapacityConstraints(finalResults)
	if err != nil {
		return nil, fmt.Errorf("货道容量约束验证失败: %v", err)
	}

	// 显示物理货道分配详情
	d.PrintPhysicalLaneAllocation(finalResults)

	return finalResults, nil
}

// 打印分配结果
func (d *DessertReplenishmentAlgorithm) PrintResults(results []DessertAllocationResult) {
	d.debugPrint("\n=== 甜品分拣补货分配结果 ===\n")

	totalAllocatedLanes := 0
	totalReplenishment := 0
	totalFinalStock := 0

	for i, result := range results {
		sku := d.SKUs[i]

		maxAllowedLanes := d.calculateMaxAllowedLanes(sku)
		minGuaranteedLanes := d.calculateMinGuaranteedLanes(sku)

		d.debugPrint("\nSKU %s (预期比例: %.2f):\n", result.SKUID, sku.ExpectedRatio)
		d.debugPrint("  当前库存: %d\n", sku.CurrentStock)
		d.debugPrint("  仓库库存: %d\n", sku.WarehouseStock)
		d.debugPrint("  最小库存: %d\n", sku.MinStock)
		d.debugPrint("  初始货道数: %d\n", sku.InitialLanes)
		d.debugPrint("  最小保证货道数: %d (约束: ≥%d)\n", minGuaranteedLanes, d.MinLaneConstraint)
		d.debugPrint("  最大允许货道数: %d (强约束: max(%d, %d))\n",
			maxAllowedLanes, sku.InitialLanes, d.MaxLaneConstraint)
		d.debugPrint("  当前占用货道: %d\n", result.CurrentUsedLanes)
		d.debugPrint("  分配货道数: %d\n", result.AllocatedLanes)
		d.debugPrint("  货道容量: %d\n", result.LaneCapacity)
		d.debugPrint("  补货量: %d\n", result.ReplenishmentQty)
		d.debugPrint("  补货后库存: %d\n", result.FinalStock)
		d.debugPrint("  可满足最小库存: %t\n", result.CanMeetMinStock)

		totalAllocatedLanes += result.AllocatedLanes
		totalReplenishment += result.ReplenishmentQty
		totalFinalStock += result.FinalStock
	}

	// 计算总体指标
	laneUtilization := float64(totalAllocatedLanes) / float64(d.TotalLanes)
	proportionDeviation := d.calculateProportionDeviation(results, totalFinalStock)
	objectiveValue := d.calculateObjective(results)

	d.debugPrint("\n=== 总体指标 ===\n")
	d.debugPrint("总货道数: %d\n", d.TotalLanes)
	d.debugPrint("分配货道数: %d\n", totalAllocatedLanes)
	d.debugPrint("货道利用率: %.2f%%\n", laneUtilization*100)
	d.debugPrint("总补货量: %d\n", totalReplenishment)
	d.debugPrint("补货后总库存: %d\n", totalFinalStock)
	d.debugPrint("理论最大容量: %d (货道数 × %d)\n", d.getTotalMaxCapacity(), LaneCapacityPerLane)
	d.debugPrint("容量利用率: %.2f%%\n", float64(totalFinalStock)/float64(d.getTotalMaxCapacity())*100)
	d.debugPrint("比例偏差: %.4f\n", proportionDeviation)
	d.debugPrint("目标函数值: %.4f\n", objectiveValue)
	d.debugPrint("当前最小货道约束配置: %d\n", d.MinLaneConstraint)
	d.debugPrint("当前最大货道约束配置: %d\n", d.MaxLaneConstraint)
}

// 显示物理货道分配详情
func (d *DessertReplenishmentAlgorithm) PrintPhysicalLaneAllocation(results []DessertAllocationResult) {
	d.debugPrint("\n=== 物理货道分配详情 ===\n")

	for _, result := range results {
		if len(result.AssignedLanes) > 0 {
			d.debugPrint("\nSKU %s 分配的物理货道:\n", result.SKUID)
			for _, lane := range result.AssignedLanes {
				d.debugPrint("  货道ID: %d, 支持类型: %v, 商品ID: %d, 数量: %d, 补货量: %d\n",
					lane.ID, lane.SupportedTypes, lane.CommodityID, lane.Quantity, lane.ReplenishmentQty)
			}
		}
	}
	d.debugPrint("\n=== 所有物理货道状态 ===\n")
	d.printAllPhysicalLanesStatus()
}

// 打印所有物理货道状态
func (d *DessertReplenishmentAlgorithm) printAllPhysicalLanesStatus() {

	for _, lane := range d.PhysicalLanes {
		status := "未占用"
		if lane.IsOccupied() {
			status = fmt.Sprintf("已占用(商品ID: %d, 数量: %d, 补货量: %d)",
				lane.CommodityID, lane.Quantity, lane.ReplenishmentQty)
		}
		d.debugPrint("货道ID: %d, 支持类型: %v, 状态: %s\n",
			lane.ID, lane.SupportedTypes, status)
	}
}
