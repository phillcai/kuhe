package main

import (
	"fmt"
	"math"
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
}

// 货道类型结构体
type LaneType struct {
	ID         int // 货道类型ID
	TotalLanes int // 该类型的总货道数 L_t^total
}

// 物理货道结构体 - 新增
type PhysicalLane struct {
	ID             int   // 物理货道ID
	SupportedTypes []int // 支持的货道类型列表
}

// 甜品分拣分配结果结构体
type DessertAllocationResult struct {
	SKUID            string // SKU ID
	AllocatedLanes   int    // 分配的货道数 L_i
	LaneCapacity     int    // 货道容量 C_i = 5 * L_i
	ReplenishmentQty int    // 补货量 P_i
	FinalStock       int    // 补货后数量 M_i
	CurrentUsedLanes int    // 当前占用货道数 L_i^current
	CanMeetMinStock  bool   // 是否可满足最小库存
}

// 甜品分拣补货算法类
type DessertReplenishmentAlgorithm struct {
	SKUs                []DessertSKU // 所有SKU
	LaneTypes           []LaneType   // 货道类型配置
	TotalLanes          int          // 总货道数 K
	CompatibilityMatrix [][]bool     // 兼容性矩阵 A_{i,t}
	WeightAlpha         float64      // 比例平衡权重
	WeightBeta          float64      // 货道利用率权重
	WeightGamma         float64      // 安全库存惩罚权重
	MaxIterations       int          // 最大迭代次数
	ConvergenceThres    float64      // 收敛阈值
}

// 构造函数
func NewDessertReplenishmentAlgorithm() *DessertReplenishmentAlgorithm {
	return &DessertReplenishmentAlgorithm{
		WeightAlpha:      0.5, // 比例平衡权重
		WeightBeta:       0.2, // 货道利用率权重
		WeightGamma:      0.3, // 安全库存惩罚权重
		MaxIterations:    50,
		ConvergenceThres: 0.01,
	}
}

// 初始化数据
func (d *DessertReplenishmentAlgorithm) Initialize(skus []DessertSKU, laneTypes []LaneType) error {
	d.SKUs = skus
	d.LaneTypes = laneTypes

	// 计算总货道数
	// 修复：在共享货道系统中，不能累加各类型的货道数
	// 应该使用实际的物理货道总数
	if len(laneTypes) > 0 {
		// 所有类型共享相同的物理货道，取任意一个类型的数量作为物理货道总数
		d.TotalLanes = laneTypes[0].TotalLanes
	} else {
		d.TotalLanes = 0
	}

	// 构建兼容性矩阵
	if err := d.buildCompatibilityMatrix(); err != nil {
		return fmt.Errorf("构建兼容性矩阵失败: %v", err)
	}

	// 验证约束可行性
	if err := d.validateConstraints(); err != nil {
		return fmt.Errorf("约束验证失败: %v", err)
	}

	return nil
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
	if math.Abs(totalRatio-1.0) > 0.01 {
		return fmt.Errorf("预期比例总和不等于1，当前总和: %.3f", totalRatio)
	}

	return nil
}

// 步骤1：货道兼容性分析
func (d *DessertReplenishmentAlgorithm) stage1_LaneCompatibilityAnalysis() ([]int, []int, error) {
	currentUsedLanes := make([]int, len(d.SKUs))
	availableLanes := make([]int, len(d.SKUs))

	// 计算每个SKU当前占用货道数
	for i, sku := range d.SKUs {
		// 优先使用实际占用货道数，如果没有则使用数学公式计算
		if sku.ActualUsedLanes > 0 {
			currentUsedLanes[i] = sku.ActualUsedLanes
		} else {
			currentUsedLanes[i] = int(math.Ceil(float64(sku.CurrentStock) / 5.0))
		}
	}

	// 计算每个SKU的可用货道总数
	// 修复：在共享货道系统中，不能简单累加兼容类型的货道数
	// 因为不同类型可能指向相同的物理货道
	for i := range d.SKUs {
		availableLanes[i] = 0
		hasCompatibleLane := false

		for j := range d.LaneTypes {
			if d.CompatibilityMatrix[i][j] {
				hasCompatibleLane = true
				break
			}
		}

		if hasCompatibleLane {
			// 在共享货道系统中，有兼容货道类型的SKU都可以访问所有物理货道
			// 设置为总物理货道数（通过任意一个货道类型获取，因为它们共享相同的物理容量）
			if len(d.LaneTypes) > 0 {
				availableLanes[i] = d.LaneTypes[0].TotalLanes
			}
		}
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
	targetReplenishment := d.calculateTargetReplenishment()

	// 计算每个SKU的理想货道需求
	demandLanes := make([]int, len(d.SKUs))
	totalDemand := 0

	for i, sku := range d.SKUs {
		// 计算需求货道数
		idealStock := sku.ExpectedRatio * float64(targetReplenishment)
		neededStock := math.Max(float64(sku.MinStock), float64(sku.CurrentStock)+idealStock)
		demand := int(math.Ceil(neededStock / 5.0))

		// 确保不少于当前占用货道数
		demand = int(math.Max(float64(demand), float64(currentUsedLanes[i])))

		demandLanes[i] = demand
		totalDemand += demand
	}

	// 检查是否需要缩放以满足总货道约束
	if totalDemand <= d.TotalLanes {
		// 需求在容量范围内，直接分配
		for i := range allocatedLanes {
			allocatedLanes[i] = demandLanes[i]
		}
		return true
	} else {
		// 需求超过容量，需要按比例缩减或使用优先级分配
		return false // 回退到比例分配策略
	}
}

// 比例分配策略（回退策略）
func (d *DessertReplenishmentAlgorithm) proportionalAllocation(currentUsedLanes, availableLanes []int) ([]int, error) {
	allocatedLanes := make([]int, len(d.SKUs))

	// 预先分配现有货道
	reservedLanes := 0
	for i := range d.SKUs {
		allocatedLanes[i] = currentUsedLanes[i]
		reservedLanes += currentUsedLanes[i]
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

	// 按调整后比例分配剩余货道
	for i := range d.SKUs {
		if totalAdjustedRatio > 0 && availableLanes[i] > currentUsedLanes[i] {
			additionalLanes := int(math.Round(adjustedRatios[i] / totalAdjustedRatio * float64(remainingLanes)))
			allocatedLanes[i] += additionalLanes

			// 确保不超过可用货道数
			allocatedLanes[i] = int(math.Min(float64(allocatedLanes[i]), float64(availableLanes[i])))
		}
	}

	// 确保所有需要补货的SKU至少分配1个货道
	// 重新计算当前剩余货道数
	currentUsed := 0
	for _, lanes := range allocatedLanes {
		currentUsed += lanes
	}
	currentRemaining := d.TotalLanes - currentUsed

	for i, sku := range d.SKUs {
		// 如果SKU需要补货（仓库有库存且当前库存低于最优水平）但没有分配货道
		if sku.WarehouseStock > 0 && allocatedLanes[i] == 0 && availableLanes[i] > 0 {
			// 尝试分配1个货道
			if currentRemaining > 0 {
				allocatedLanes[i] = 1
				currentRemaining--
			} else {
				// 如果没有剩余货道，从其他SKU中借1个货道
				for j := range d.SKUs {
					if j != i && allocatedLanes[j] > currentUsedLanes[j] {
						allocatedLanes[j]--
						allocatedLanes[i] = 1
						break
					}
				}
			}
		}
	}

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
			LaneCapacity:     allocatedLanes[i] * 5,
			CurrentUsedLanes: currentUsedLanes[i], // 使用之前计算的实际占用货道数
		}

		// 检查是否可满足最小库存
		result.CanMeetMinStock = (sku.WarehouseStock + sku.CurrentStock) >= sku.MinStock

		if result.CanMeetMinStock {
			// 策略：在满足最小库存的前提下，尽量填满货道容量

			// 第一步：计算必须满足的最小库存
			minRequiredStock := int(math.Max(float64(sku.MinStock), float64(sku.CurrentStock)))

			// 第二步：计算尽量填满货道的目标库存
			// 限制条件：不超过货道容量、不超过仓库总库存
			maxFillableStock := int(math.Min(float64(result.LaneCapacity), float64(sku.CurrentStock+sku.WarehouseStock)))

			// 第三步：选择填满策略 - 直接尝试填满货道（受仓库库存限制）
			result.FinalStock = maxFillableStock

			// 确保不低于最小库存要求
			result.FinalStock = int(math.Max(float64(result.FinalStock), float64(minRequiredStock)))
		} else {
			// 无法满足最小库存，尽力而为，填满仓库库存或货道容量
			maxPossible := int(math.Min(float64(result.LaneCapacity), float64(sku.CurrentStock+sku.WarehouseStock)))
			result.FinalStock = maxPossible
		}

		result.ReplenishmentQty = int(math.Max(0, float64(result.FinalStock-sku.CurrentStock)))

		// 确保不超过仓库库存
		result.ReplenishmentQty = int(math.Min(float64(result.ReplenishmentQty), float64(sku.WarehouseStock)))
		result.FinalStock = sku.CurrentStock + result.ReplenishmentQty

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
		idealStock := int(sku.ExpectedRatio * float64(totalTargetStock))

		// 应用约束条件
		maxByCapacity := results[i].LaneCapacity
		maxByWarehouse := sku.CurrentStock + sku.WarehouseStock
		minByMinStock := results[i].FinalStock // 已分配的最小库存（stage3的填满值）

		// 计算最终库存
		finalStock := int(math.Min(float64(idealStock), float64(maxByCapacity)))
		finalStock = int(math.Min(float64(finalStock), float64(maxByWarehouse)))
		finalStock = int(math.Max(float64(finalStock), float64(minByMinStock)))

		results[i].FinalStock = finalStock
		results[i].ReplenishmentQty = finalStock - sku.CurrentStock

		// 确保补货量非负
		if results[i].ReplenishmentQty < 0 {
			results[i].ReplenishmentQty = 0
			results[i].FinalStock = sku.CurrentStock
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

		newObjective := d.calculateObjective(results)

		// 检查收敛条件
		if !improved || math.Abs(newObjective-prevObjective) < d.ConvergenceThres {
			break
		}
	}

	return results, nil
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

	// 只有在不违反填满策略的情况下才允许交换
	if results[i].ReplenishmentQty > 0 &&
		results[j].ReplenishmentQty < d.SKUs[j].WarehouseStock &&
		results[i].FinalStock > minFillStock_i && // 确保不低于填满策略设定的下界
		results[j].FinalStock < maxFillStock_j { // 确保不超过填满策略设定的上界

		results[i].ReplenishmentQty--
		results[i].FinalStock--
		results[j].ReplenishmentQty++
		results[j].FinalStock++
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

// 计算目标总补货量
func (d *DessertReplenishmentAlgorithm) calculateTargetReplenishment() float64 {
	totalWarehouse := 0
	totalCurrent := 0
	for _, sku := range d.SKUs {
		totalWarehouse += sku.WarehouseStock
		totalCurrent += sku.CurrentStock
	}
	return float64(totalWarehouse) * 0.8 // 使用80%的仓库库存作为目标
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

// 主要执行函数
func (d *DessertReplenishmentAlgorithm) Execute() ([]DessertAllocationResult, error) {
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

	// 步骤3：最小库存优先处理
	initialResults, err := d.stage3_MinStockPriorityProcessing(allocatedLanes, currentUsedLanes)
	if err != nil {
		return nil, fmt.Errorf("步骤3失败: %v", err)
	}

	// 步骤4：比例平衡补货量计算（在填满策略基础上进行微调）
	balancedResults, err := d.stage4_ProportionalReplenishmentCalculation(initialResults)
	if err != nil {
		return nil, fmt.Errorf("步骤4失败: %v", err)
	}

	// 步骤5：动态调整优化
	finalResults, err := d.stage5_DynamicOptimization(balancedResults)
	if err != nil {
		return nil, fmt.Errorf("步骤5失败: %v", err)
	}

	return finalResults, nil
}

// 打印分配结果
func (d *DessertReplenishmentAlgorithm) PrintResults(results []DessertAllocationResult) {
	fmt.Println("\n=== 甜品分拣补货分配结果 ===")

	totalAllocatedLanes := 0
	totalReplenishment := 0
	totalFinalStock := 0

	for i, result := range results {
		sku := d.SKUs[i]

		fmt.Printf("\nSKU %s (预期比例: %.2f):\n", result.SKUID, sku.ExpectedRatio)
		fmt.Printf("  当前库存: %d\n", sku.CurrentStock)
		fmt.Printf("  仓库库存: %d\n", sku.WarehouseStock)
		fmt.Printf("  最小库存: %d\n", sku.MinStock)
		fmt.Printf("  当前占用货道: %d\n", result.CurrentUsedLanes)
		fmt.Printf("  分配货道数: %d\n", result.AllocatedLanes)
		fmt.Printf("  货道容量: %d\n", result.LaneCapacity)
		fmt.Printf("  补货量: %d\n", result.ReplenishmentQty)
		fmt.Printf("  补货后库存: %d\n", result.FinalStock)
		fmt.Printf("  可满足最小库存: %t\n", result.CanMeetMinStock)

		totalAllocatedLanes += result.AllocatedLanes
		totalReplenishment += result.ReplenishmentQty
		totalFinalStock += result.FinalStock
	}

	// 计算总体指标
	laneUtilization := float64(totalAllocatedLanes) / float64(d.TotalLanes)
	proportionDeviation := d.calculateProportionDeviation(results, totalFinalStock)
	objectiveValue := d.calculateObjective(results)

	fmt.Printf("\n=== 总体指标 ===\n")
	fmt.Printf("总货道数: %d\n", d.TotalLanes)
	fmt.Printf("分配货道数: %d\n", totalAllocatedLanes)
	fmt.Printf("货道利用率: %.2f%%\n", laneUtilization*100)
	fmt.Printf("总补货量: %d\n", totalReplenishment)
	fmt.Printf("补货后总库存: %d\n", totalFinalStock)
	fmt.Printf("比例偏差: %.4f\n", proportionDeviation)
	fmt.Printf("目标函数值: %.4f\n", objectiveValue)
}
