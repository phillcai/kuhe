package main

import (
	"fmt"
	"math"
	"sort"
)

// 调试控制变量
var isDebug bool = true

// 调试打印函数
func debugPrint(format string, args ...interface{}) {
	if isDebug {
		fmt.Printf(format, args...)
	}
}

// 设置调试模式
func SetDebugMode(debug bool) {
	isDebug = debug
}

// 获取当前调试模式
func GetDebugMode() bool {
	return isDebug
}

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
	DefaultMinLaneConstraint = 2    // 默认最小货道约束

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
	ID             int   // 物理货道ID
	SupportedTypes []int // 支持的货道类型列表
}

// 甜品分拣分配结果结构体
type DessertAllocationResult struct {
	SKUID            string // SKU ID
	AllocatedLanes   int    // 分配的货道数 L_i
	LaneCapacity     int    // 货道容量 C_i = LaneCapacityPerLane * L_i
	ReplenishmentQty int    // 补货量 P_i
	FinalStock       int    // 补货后数量 M_i
	CurrentUsedLanes int    // 当前占用货道数 L_i^current
	CanMeetMinStock  bool   // 是否可满足最小库存
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
	MinLaneConstraint   int            // 最小货道约束配置：每个SKU最大允许货道数 = max(初始货道数, MinLaneConstraint)
}

// 构造函数
func NewDessertReplenishmentAlgorithm() *DessertReplenishmentAlgorithm {
	return &DessertReplenishmentAlgorithm{
		WeightAlpha:       DefaultWeightAlpha, // 比例平衡权重
		WeightBeta:        DefaultWeightBeta,  // 货道利用率权重
		WeightGamma:       DefaultWeightGamma, // 安全库存惩罚权重
		MaxIterations:     DefaultMaxIterations,
		ConvergenceThres:  DefaultConvergenceThres,
		MinLaneConstraint: DefaultMinLaneConstraint, // 默认最小货道约束
	}
}

// 初始化算法数据
func (d *DessertReplenishmentAlgorithm) Initialize(skus []DessertSKU, laneTypes []LaneType, physicalLanes map[int][]int) error {
	d.SKUs = skus
	d.LaneTypes = laneTypes

	// 设置物理货道配置
	if physicalLanes != nil && len(physicalLanes) > 0 {
		d.PhysicalLanes = make([]PhysicalLane, 0, len(physicalLanes))
		for shelfID, supportedTypes := range physicalLanes {
			d.PhysicalLanes = append(d.PhysicalLanes, PhysicalLane{
				ID:             shelfID,
				SupportedTypes: supportedTypes,
			})
		}
		// 使用物理货道数量
		d.TotalLanes = len(d.PhysicalLanes)
	}

	// 构建兼容性矩阵
	if err := d.buildCompatibilityMatrix(); err != nil {
		return err
	}
	// 中文注释：打印laneTypes信息，便于调试和确认货道类型配置
	debugPrint("初始化时打印laneTypes信息：\n")
	for i, laneType := range d.LaneTypes {
		debugPrint("  laneTypes[%d]: ID=%d, count=%d\n", i, laneType.ID, laneType.TotalLanes)
	}

	return nil
}

// 设置最小货道约束配置
func (d *DessertReplenishmentAlgorithm) SetMinLaneConstraint(minLanes int) error {
	if minLanes < 1 {
		return fmt.Errorf("最小货道约束不能小于1，当前值: %d", minLanes)
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
		availableLanes[i] = 0

		// 统计支持该SKU类型的物理货道数量
		for _, physicalLane := range d.PhysicalLanes {
			// 检查物理货道是否支持该SKU的兼容货道类型
			for _, supportedType := range physicalLane.SupportedTypes {
				for _, compatibleType := range d.SKUs[i].CompatibleLanes {
					if supportedType == compatibleType {
						availableLanes[i]++
						break // 找到一个匹配的类型就足够了
					}
				}
				// 如果已经找到匹配，不需要继续检查其他支持类型,后续 sku有多个 type 再优化
				if availableLanes[i] > 0 {
					break
				}
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
	// 计算每个SKU的理想货道需求
	demandLanes := make([]int, len(d.SKUs))
	totalDemand := 0
	totalCapacity := d.getTotalMaxCapacity() // 货道总容量
	for i, sku := range d.SKUs {
		// 计算需求货道数：基于货道总容量和预期比例
		idealStock := sku.ExpectedRatio * float64(totalCapacity)
		neededStock := math.Max(float64(sku.MinStock), idealStock)
		neededStock = math.Max(neededStock, float64(sku.CurrentStock))
		demand := int(math.Ceil(neededStock / float64(LaneCapacityPerLane)))

		// 确保不少于当前占用货道数
		demand = int(math.Max(float64(demand), float64(currentUsedLanes[i])))

		// 应用强约束：不超过max(初始货道数, 2)
		maxAllowed := d.calculateMaxAllowedLanes(sku)
		demand = int(math.Min(float64(demand), float64(maxAllowed)))

		demandLanes[i] = demand
		totalDemand += demand
	}

	// 检查是否需要缩放以满足总货道约束
	if totalDemand <= d.TotalLanes {
		// 需求在容量范围内，直接分配
		for i := range allocatedLanes {
			// 确保不超过支持该SKU类型的货道数量
			maxAllowed := d.calculateMaxAllowedLanes(d.SKUs[i])
			allocatedLanes[i] = int(math.Min(float64(demandLanes[i]), float64(maxAllowed)))
		}
		return true
	} else {
		// 需求超过容量，按预期比例优先级进行分配
		return d.allocateWithPriority(demandLanes, allocatedLanes, availableLanes)
	}
}

// 按优先级分配货道（优先满足最小库存，然后给没有货道的SKU分配）
func (d *DessertReplenishmentAlgorithm) allocateWithPriority(demandLanes, allocatedLanes, availableLanes []int) bool {
	debugPrint("🔄 开始优先级分配策略补货\n")
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
			if skuAvailableLanes > 0 && remainingLanes > 0 {
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
					additionalCapacity = int(math.Min(float64(additionalCapacity), float64(skuAvailableLanes)))

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
	debugPrint("🔄 开始按比例分配策略补货\n")
	allocatedLanes := make([]int, len(d.SKUs))

	// 预先分配现有货道
	reservedLanes := 0
	for i := range d.SKUs {
		// 只有当SKU有库存需求时才分配货道
		if d.SKUs[i].CurrentStock+d.SKUs[i].WarehouseStock > 0 {
			// 确保当前占用的货道数不超过支持该SKU类型的货道数量
			maxAllowed := d.calculateMaxAllowedLanes(d.SKUs[i])
			// 中文注释：分配货道数为当前占用货道数和最大允许货道数、1三者的最小值
			allocatedLanes[i] = int(math.Max(float64(currentUsedLanes[i]), math.Min(1, float64(maxAllowed))))
		} else {
			// 没有库存需求，不分配货道
			allocatedLanes[i] = 0
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
			CurrentUsedLanes: currentUsedLanes[i], // 使用之前计算的实际占用货道数
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
				debugPrint("SKU %s 可用货道数: %d (货道类型 %d)\n", sku.ID, laneType.TotalLanes, laneType.ID)
				return laneType.TotalLanes
			}
		}
	}

	// 如果找不到兼容的货道类型，返回总货道数作为备选
	debugPrint("SKU %s 可用货道数: %d (备选)\n", sku.ID, 0)
	return 0
}

// 计算SKU的最大允许货道数（强约束）
// 不超过初始货道数和MinLaneConstraint之间的最大值，同时不超过支持该SKU类型的货道总数量
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

	// 计算支持该SKU类型的货道总数量
	// 找到该SKU在SKUs数组中的索引
	skuIndex := -1
	for i, s := range d.SKUs {
		if s.ID == sku.ID {
			skuIndex = i
			break
		}
	}

	var availableLanes int
	if skuIndex >= 0 {
		availableLanes = d.getAvailableLanesForSKU(skuIndex)
		debugPrint("🔍 SKU %s: 初始货道=%d, 可用货道=%d, MinLaneConstraint=%d\n",
			sku.ID, initialLanes, availableLanes, d.MinLaneConstraint)
	} else {
		// 如果找不到SKU索引，使用总货道数作为备选
		availableLanes = d.TotalLanes
	}

	// 返回初始货道数、配置的最小货道约束和支持的货道数量之间的最小值
	maxByConstraint := int(math.Max(float64(initialLanes), float64(d.MinLaneConstraint)))

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

	return finalResults, nil
}

// 打印分配结果
func (d *DessertReplenishmentAlgorithm) PrintResults(results []DessertAllocationResult) {
	debugPrint("\n=== 甜品分拣补货分配结果 ===\n")

	totalAllocatedLanes := 0
	totalReplenishment := 0
	totalFinalStock := 0

	for i, result := range results {
		sku := d.SKUs[i]

		maxAllowedLanes := d.calculateMaxAllowedLanes(sku)

		debugPrint("\nSKU %s (预期比例: %.2f):\n", result.SKUID, sku.ExpectedRatio)
		debugPrint("  当前库存: %d\n", sku.CurrentStock)
		debugPrint("  仓库库存: %d\n", sku.WarehouseStock)
		debugPrint("  最小库存: %d\n", sku.MinStock)
		debugPrint("  初始货道数: %d\n", sku.InitialLanes)
		debugPrint("  最大允许货道数: %d (强约束: max(%d, %d))\n",
			maxAllowedLanes, sku.InitialLanes, d.MinLaneConstraint)
		debugPrint("  当前占用货道: %d\n", result.CurrentUsedLanes)
		debugPrint("  分配货道数: %d\n", result.AllocatedLanes)
		debugPrint("  货道容量: %d\n", result.LaneCapacity)
		debugPrint("  补货量: %d\n", result.ReplenishmentQty)
		debugPrint("  补货后库存: %d\n", result.FinalStock)
		debugPrint("  可满足最小库存: %t\n", result.CanMeetMinStock)

		totalAllocatedLanes += result.AllocatedLanes
		totalReplenishment += result.ReplenishmentQty
		totalFinalStock += result.FinalStock
	}

	// 计算总体指标
	laneUtilization := float64(totalAllocatedLanes) / float64(d.TotalLanes)
	proportionDeviation := d.calculateProportionDeviation(results, totalFinalStock)
	objectiveValue := d.calculateObjective(results)

	debugPrint("\n=== 总体指标 ===\n")
	debugPrint("总货道数: %d\n", d.TotalLanes)
	debugPrint("分配货道数: %d\n", totalAllocatedLanes)
	debugPrint("货道利用率: %.2f%%\n", laneUtilization*100)
	debugPrint("总补货量: %d\n", totalReplenishment)
	debugPrint("补货后总库存: %d\n", totalFinalStock)
	debugPrint("理论最大容量: %d (货道数 × %d)\n", d.getTotalMaxCapacity(), LaneCapacityPerLane)
	debugPrint("容量利用率: %.2f%%\n", float64(totalFinalStock)/float64(d.getTotalMaxCapacity())*100)
	debugPrint("比例偏差: %.4f\n", proportionDeviation)
	debugPrint("目标函数值: %.4f\n", objectiveValue)
	debugPrint("当前最小货道约束配置: %d\n", d.MinLaneConstraint)
}
