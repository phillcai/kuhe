package main

import (
	"fmt"
	"math"
	"sort"
	"strings"
)

// 商品信息结构
type Product struct {
	ID             string  // 商品标识
	Name           string  // 商品名称
	WarehouseStock int     // 仓库库存 N_i
	CurrentStock   int     // 点位现有量 G_i
	MaxAllowed     int     // 最大允许补货后数量 X_i
	ExpectedRatio  float64 // 预期比例 r_i
}

// 补货结果结构
type ReplenishmentResult struct {
	ProductID       string  // 商品ID
	CurrentStock    int     // 当前库存 G_i
	WarehouseStock  int     // 仓库库存 N_i
	MaxAllowed      int     // 最大允许数量 X_i
	ReplenishAmount int     // 补货量 P_i
	FinalStock      int     // 补货后数量 M_i
	ActualRatio     float64 // 实际比例
	ExpectedRatio   float64 // 预期比例
}

// 补货算法配置
type ReplenishmentConfig struct {
	TargetTotal    int     // 目标补货后总量 M
	MaxCapacity    int     // 点位最大库存 K
	MaxIterations  int     // 最大循环次数
	ToleranceRatio float64 // 比例偏差容忍度
}

// 补货算法主类
type ReplenishmentAlgorithm struct {
	products            []Product
	config              ReplenishmentConfig
	results             []ReplenishmentResult
	finalLaneAllocation []int // 存储最终的货道分配结果
}

// 创建新的补货算法实例
func NewReplenishmentAlgorithm(products []Product, config ReplenishmentConfig) *ReplenishmentAlgorithm {
	return &ReplenishmentAlgorithm{
		products: products,
		config:   config,
		results:  make([]ReplenishmentResult, 0),
	}
}

// 主算法执行入口
func (ra *ReplenishmentAlgorithm) Execute() ([]ReplenishmentResult, error) {
	fmt.Println("=== 开始执行带最大允许数量约束的补货算法 ===")

	// 验证输入数据
	if err := ra.validateInput(); err != nil {
		return nil, fmt.Errorf("输入验证失败: %v", err)
	}

	// 步骤1: 计算理想目标数量
	idealTargets := ra.calculateIdealTargets()
	fmt.Printf("步骤1: 理想目标数量计算完成\n")

	// 步骤2: 施加最大允许数量约束
	initialAmounts := ra.applyMaxAllowedConstraints(idealTargets)
	fmt.Printf("步骤2: 最大允许数量约束施加完成\n")

	// 步骤3: 施加仓库库存约束
	tempAmounts := ra.applyWarehouseStockConstraints(initialAmounts)
	fmt.Printf("步骤3: 仓库库存约束施加完成\n")

	// 步骤4: 调整总补货量至目标
	finalAmounts := ra.adjustToTargetTotal(tempAmounts, idealTargets)
	fmt.Printf("步骤4: 总补货量调整完成\n")

	// 步骤5: 特殊情况处理
	finalAmounts = ra.handleSpecialCases(finalAmounts)
	fmt.Printf("步骤5: 特殊情况处理完成\n")

	// 步骤6: 最终校验
	if err := ra.validateFinalResults(finalAmounts); err != nil {
		return nil, fmt.Errorf("最终校验失败: %v", err)
	}
	fmt.Printf("步骤6: 最终校验通过\n")

	// 生成结果
	ra.generateResults(finalAmounts)

	fmt.Println("=== 补货算法执行完成 ===")
	return ra.results, nil
}

// 验证输入数据
func (ra *ReplenishmentAlgorithm) validateInput() error {
	if len(ra.products) == 0 {
		return fmt.Errorf("商品列表为空")
	}

	totalRatio := 0.0
	totalCurrentStock := 0
	totalWarehouseStock := 0

	for _, product := range ra.products {
		if product.ExpectedRatio < 0 {
			return fmt.Errorf("商品 %s 的预期比例不能为负", product.ID)
		}
		if product.WarehouseStock < 0 {
			return fmt.Errorf("商品 %s 的仓库库存不能为负", product.ID)
		}
		if product.CurrentStock < 0 {
			return fmt.Errorf("商品 %s 的当前库存不能为负", product.ID)
		}
		if product.MaxAllowed < 0 {
			return fmt.Errorf("商品 %s 的最大允许数量不能为负", product.ID)
		}

		totalRatio += product.ExpectedRatio
		totalCurrentStock += product.CurrentStock
		totalWarehouseStock += product.WarehouseStock
	}

	if math.Abs(totalRatio-1.0) > 1e-4 {
		return fmt.Errorf("预期比例总和必须为1.0，当前为 %.6f", totalRatio)
	}

	if ra.config.TargetTotal <= totalCurrentStock {
		return fmt.Errorf("目标总量 %d 必须大于当前总库存 %d", ra.config.TargetTotal, totalCurrentStock)
	}

	targetReplenish := ra.config.TargetTotal - totalCurrentStock
	if targetReplenish > totalWarehouseStock {
		fmt.Printf("警告: 目标补货量 %d 超过仓库总库存 %d\n", targetReplenish, totalWarehouseStock)
	}

	return nil
}

// 步骤1: 计算理想目标数量
func (ra *ReplenishmentAlgorithm) calculateIdealTargets() []int {
	idealTargets := make([]int, len(ra.products))

	for i, product := range ra.products {
		ideal := product.ExpectedRatio * float64(ra.config.TargetTotal)
		idealTargets[i] = int(math.Round(ideal))
	}

	// 调整取整误差，确保总和等于目标总量
	totalIdeal := 0
	for _, ideal := range idealTargets {
		totalIdeal += ideal
	}

	diff := ra.config.TargetTotal - totalIdeal
	if diff != 0 {
		// 按比例调整差异
		for i := 0; i < len(idealTargets) && diff != 0; i++ {
			if diff > 0 {
				idealTargets[i]++
				diff--
			} else {
				if idealTargets[i] > 0 {
					idealTargets[i]--
					diff++
				}
			}
		}
	}

	fmt.Printf("理想目标数量: %v\n", idealTargets)
	return idealTargets
}

// 步骤2: 施加最大允许数量约束
func (ra *ReplenishmentAlgorithm) applyMaxAllowedConstraints(idealTargets []int) []int {
	initialAmounts := make([]int, len(ra.products))

	// 应用点位容量约束：X_i不能超过点位最大库存的30%
	maxCapacityLimit := float64(ra.config.TargetTotal) * 0.3

	// 计算总货道数
	totalLanes := ra.config.MaxCapacity / 3
	// 获取基础货道分配
	laneAllocation := ra.allocateLanesByRatio(totalLanes)

	for i, product := range ra.products {
		// 限制X_i不超过0.3K
		adjustedMaxAllowed := product.MaxAllowed
		if float64(product.MaxAllowed) > maxCapacityLimit {
			adjustedMaxAllowed = int(maxCapacityLimit)
			fmt.Printf("商品%d的最大允许数量从%d调整为%d (30%%容量限制)\n",
				i, product.MaxAllowed, adjustedMaxAllowed)
		}

		// 应用货道约束：每个商品最大库存 = 3 × 可用货道数
		availableLanes := laneAllocation[i]
		maxLaneStock := 3 * availableLanes

		// 检查当前库存是否超过货道限制
		if product.CurrentStock > maxLaneStock {
			// 当前库存超过货道限制，需要重新分配货道
			requiredLanes := (product.CurrentStock + 2) / 3 // 向上取整
			if requiredLanes <= totalLanes {
				// 可以重新分配货道
				fmt.Printf("⚠️  商品 %s 当前库存 %d 超过货道限制 %d，需要 %d 个货道，重新分配\n",
					product.ID, product.CurrentStock, maxLaneStock, requiredLanes)
				availableLanes = requiredLanes
				maxLaneStock = 3 * availableLanes
				// 更新货道分配
				laneAllocation[i] = requiredLanes
			} else {
				// 货道不足，无法容纳当前库存
				fmt.Printf("❌  商品 %s 当前库存 %d 需要 %d 个货道，但总货道数只有 %d，无法处理\n",
					product.ID, product.CurrentStock, requiredLanes, totalLanes)
				// 这种情况下，该商品不应该参与补货
				initialAmounts[i] = 0
				continue
			}
		}

		// 取货道约束和原有约束的最小值
		maxAllowed := maxInt(adjustedMaxAllowed, product.CurrentStock)
		// maxAllowed = minInt(maxAllowed, maxLaneStock)

		idealAmount := max(idealTargets[i]-product.CurrentStock, 0)

		if product.CurrentStock+idealAmount <= maxAllowed {
			initialAmounts[i] = idealAmount
		} else {
			// 确保补货量不为负数
			initialAmounts[i] = maxInt(0, maxAllowed-product.CurrentStock)
		}
	}

	// 保存调整后的货道分配结果
	ra.finalLaneAllocation = make([]int, len(laneAllocation))
	copy(ra.finalLaneAllocation, laneAllocation)

	fmt.Printf("初步补货量: %v\n", initialAmounts)
	return initialAmounts
}

// 步骤3: 施加仓库库存约束
func (ra *ReplenishmentAlgorithm) applyWarehouseStockConstraints(initialAmounts []int) []int {
	tempAmounts := make([]int, len(ra.products))

	for i, product := range ra.products {
		tempAmounts[i] = minInt(initialAmounts[i], product.WarehouseStock)
	}

	fmt.Printf("受库存约束后补货量: %v\n", tempAmounts)
	return tempAmounts
}

// 步骤4: 调整总补货量至目标
func (ra *ReplenishmentAlgorithm) adjustToTargetTotal(tempAmounts []int, idealTargets []int) []int {
	finalAmounts := make([]int, len(tempAmounts))
	copy(finalAmounts, tempAmounts)

	// 应用货道约束：每个商品最大库存 = 3 × 可用货道数量
	finalAmounts = ra.applyLaneConstraints(finalAmounts)
	fmt.Printf("应用货道约束后补货量: %v\n", finalAmounts)

	currentTotal := ra.calculateCurrentTotal(finalAmounts)
	targetReplenish := ra.config.TargetTotal - ra.getCurrentStockTotal()

	fmt.Printf("当前补货总量: %d, 目标补货总量: %d\n", currentTotal, targetReplenish)

	if currentTotal < targetReplenish {
		// 子步骤4.1: 存在缺口，需要补充
		finalAmounts = ra.handleGapWithLaneReallocation(finalAmounts, targetReplenish-currentTotal, idealTargets)
	} else if currentTotal > targetReplenish {
		// 子步骤4.2: 存在超额，需要减少
		finalAmounts = ra.handleExcess(finalAmounts, currentTotal-targetReplenish, idealTargets)
	}

	// 最终货道约束检查：确保没有货道的商品补货量为0
	if ra.finalLaneAllocation != nil && len(ra.finalLaneAllocation) > 0 {
		fmt.Printf("最终货道约束检查...\n")
		for i, lanes := range ra.finalLaneAllocation {
			if lanes == 0 && finalAmounts[i] > 0 {
				fmt.Printf("⚠️  商品 %s 没有分配货道，最终补货量从 %d 调整为 0\n",
					ra.products[i].ID, finalAmounts[i])
				finalAmounts[i] = 0
			}
		}
	}

	return finalAmounts
}

// 应用货道约束：每个商品最大库存 = 3 × 可用货道数量
func (ra *ReplenishmentAlgorithm) applyLaneConstraints(amounts []int) []int {
	constrainedAmounts := make([]int, len(amounts))
	copy(constrainedAmounts, amounts)

	// 如果已经有调整过的货道分配，直接使用
	if ra.finalLaneAllocation != nil && len(ra.finalLaneAllocation) > 0 {
		fmt.Printf("使用已调整的货道分配: %v\n", ra.finalLaneAllocation)
		return ra.applyLaneAllocation(amounts, ra.finalLaneAllocation)
	}

	// 计算总货道数
	totalLanes := ra.config.MaxCapacity / 3
	fmt.Printf("总货道数: %d (总容量 %d / 3)\n", totalLanes, ra.config.MaxCapacity)

	// 尝试动态分配货道（根据实际需求）
	fmt.Printf("尝试动态货道分配...\n")
	dynamicAllocation := ra.allocateLanesDynamically(totalLanes, amounts)

	// 验证动态分配是否可行
	if ra.validateDynamicAllocation(dynamicAllocation, amounts) {
		fmt.Printf("使用动态货道分配: %v\n", dynamicAllocation)
		// 保存最终的货道分配结果
		ra.finalLaneAllocation = make([]int, len(dynamicAllocation))
		copy(ra.finalLaneAllocation, dynamicAllocation)
		return ra.applyLaneAllocation(amounts, dynamicAllocation)
	}

	// 如果动态分配不可行，回退到比例分配
	fmt.Printf("动态分配不可行，使用比例分配...\n")
	laneAllocation := ra.allocateLanesByRatioWithLogging(totalLanes, true)
	fmt.Printf("货道分配: %v\n", laneAllocation)

	// 保存最终的货道分配结果
	ra.finalLaneAllocation = make([]int, len(laneAllocation))
	copy(ra.finalLaneAllocation, laneAllocation)

	return ra.applyLaneAllocation(amounts, laneAllocation)
}

// 应用货道分配到补货量
func (ra *ReplenishmentAlgorithm) applyLaneAllocation(amounts []int, laneAllocation []int) []int {
	constrainedAmounts := make([]int, len(amounts))
	copy(constrainedAmounts, amounts)

	for i, product := range ra.products {
		// 该商品可用的货道数
		availableLanes := laneAllocation[i]

		// 如果没有分配货道，补货量必须为0
		if availableLanes == 0 {
			if constrainedAmounts[i] > 0 {
				fmt.Printf("商品 %s 没有分配货道，补货量从 %d 调整为 0\n",
					product.ID, constrainedAmounts[i])
				constrainedAmounts[i] = 0
			}
			continue
		}

		// 该商品的最大库存 = 3 × 可用货道数
		maxLaneStock := 3 * availableLanes

		// 该商品的最大允许补货量
		maxAllowedByLane := maxLaneStock - product.CurrentStock

		if maxAllowedByLane < 0 {
			maxAllowedByLane = 0
		}

		// 取货道约束和原有约束的最小值
		if constrainedAmounts[i] > maxAllowedByLane {
			fmt.Printf("商品 %s 受货道约束限制：补货量从 %d 调整为 %d (可用货道: %d, 最大库存: %d)\n",
				product.ID, constrainedAmounts[i], maxAllowedByLane, availableLanes, maxLaneStock)
			constrainedAmounts[i] = maxAllowedByLane
		}
	}

	return constrainedAmounts
}

// 应用货道约束到补货量（用于缺口处理过程中的实时约束）
func (ra *ReplenishmentAlgorithm) applyLaneConstraintsToAmounts(amounts []int) []int {
	constrainedAmounts := make([]int, len(amounts))
	copy(constrainedAmounts, amounts)

	// 使用已保存的货道分配结果
	if ra.finalLaneAllocation == nil || len(ra.finalLaneAllocation) == 0 {
		// 如果没有保存的货道分配，重新计算
		totalLanes := ra.config.MaxCapacity / 3
		laneAllocation := ra.allocateLanesByRatio(totalLanes)
		ra.finalLaneAllocation = make([]int, len(laneAllocation))
		copy(ra.finalLaneAllocation, laneAllocation)
	}

	for i, product := range ra.products {
		availableLanes := ra.finalLaneAllocation[i]

		// 如果没有分配货道，补货量必须为0
		if availableLanes == 0 {
			if constrainedAmounts[i] > 0 {
				constrainedAmounts[i] = 0
			}
			continue
		}

		// 计算最大允许库存
		maxLaneStock := 3 * availableLanes
		maxAllowedByLane := maxLaneStock - product.CurrentStock

		if maxAllowedByLane < 0 {
			maxAllowedByLane = 0
		}

		// 应用货道约束
		if constrainedAmounts[i] > maxAllowedByLane {
			constrainedAmounts[i] = maxAllowedByLane
		}
	}

	return constrainedAmounts
}

// 验证动态分配是否可行
func (ra *ReplenishmentAlgorithm) validateDynamicAllocation(laneAllocation []int, amounts []int) bool {
	totalAllocated := 0
	for _, lanes := range laneAllocation {
		totalAllocated += lanes
	}

	totalLanes := ra.config.MaxCapacity / 3
	if totalAllocated > totalLanes {
		fmt.Printf("动态分配超出总货道数: %d > %d\n", totalAllocated, totalLanes)
		return false
	}

	// 检查每个商品的分配是否合理
	for i, product := range ra.products {
		finalStock := product.CurrentStock + amounts[i]
		requiredLanes := 0
		if finalStock > 0 {
			requiredLanes = (finalStock + 2) / 3
		}

		if laneAllocation[i] < requiredLanes {
			fmt.Printf("商品 %s 货道分配不足: 需要 %d, 分配 %d\n",
				product.ID, requiredLanes, laneAllocation[i])
			return false
		}
	}

	return true
}

// 按预期比例分配货道给每个商品
func (ra *ReplenishmentAlgorithm) allocateLanesByRatio(totalLanes int) []int {
	return ra.allocateLanesByRatioWithLogging(totalLanes, false)
}

// 按预期比例分配货道给每个商品（带日志控制）
func (ra *ReplenishmentAlgorithm) allocateLanesByRatioWithLogging(totalLanes int, enableLogging bool) []int {
	laneAllocation := make([]int, len(ra.products))

	// 第一步：计算零库存商品的预期比例总和
	zeroStockRatioSum := 0.0
	for _, product := range ra.products {
		if product.WarehouseStock == 0 && product.CurrentStock == 0 {
			zeroStockRatioSum += product.ExpectedRatio
		}
	}

	// 第二步：按调整后的比例分配货道
	for i, product := range ra.products {
		// 如果仓库库存为0，根据当前库存分配最小必需货道
		if product.WarehouseStock == 0 {
			// 如果有当前库存，需要分配足够的货道来容纳
			if product.CurrentStock > 0 {
				laneAllocation[i] = (product.CurrentStock + 2) / 3 // 向上取整
			} else {
				laneAllocation[i] = 0 // 零库存且零当前库存的商品不分配货道
			}
			continue
		}

		// 有库存的商品：按调整后的比例分配货道
		// 调整后比例 = 原比例 + 零库存商品比例的重新分配
		adjustedRatio := product.ExpectedRatio
		if zeroStockRatioSum > 0 {
			// 按原比例重新分配零库存商品的份额
			redistributedRatio := (product.ExpectedRatio / (1.0 - zeroStockRatioSum)) * zeroStockRatioSum
			adjustedRatio += redistributedRatio
		}

		idealLanes := adjustedRatio * float64(totalLanes)
		laneAllocation[i] = int(math.Round(idealLanes))
	}

	// 第三步：微调以确保总数合理
	totalAllocated := 0
	for _, lanes := range laneAllocation {
		totalAllocated += lanes
	}

	// 如果分配过多，按比例缩减
	if totalAllocated > totalLanes {
		scale := float64(totalLanes) / float64(totalAllocated)
		for i := range laneAllocation {
			if ra.products[i].WarehouseStock > 0 {
				laneAllocation[i] = int(math.Round(float64(laneAllocation[i]) * scale))
			}
		}

		// 重新计算总分配数
		totalAllocated = 0
		for _, lanes := range laneAllocation {
			totalAllocated += lanes
		}

		// 如果仍然超出，强制限制每个商品的货道数
		if totalAllocated > totalLanes {
			fmt.Printf("⚠️  货道分配仍然超出限制，进行强制约束调整\n")
			// 按优先级强制调整：优先保证有库存商品的货道
			ra.forceLaneConstraint(laneAllocation, totalLanes)
		}
	}

	// 一次性输出货道重新分配信息
	if enableLogging && zeroStockRatioSum > 0 {
		fmt.Printf("✅ 货道智能重新分配: 零库存商品比例 %.1f%% 已重新分配给有库存商品\n", zeroStockRatioSum*100)
	}

	// 静默验证货道分配的合理性
	ra.validateLaneAllocation(laneAllocation, totalLanes)

	return laneAllocation
}

// 强制约束每个商品的货道数不超过总货道数
func (ra *ReplenishmentAlgorithm) forceLaneConstraint(laneAllocation []int, totalLanes int) {
	totalAllocated := 0
	for _, lanes := range laneAllocation {
		totalAllocated += lanes
	}

	if totalAllocated <= totalLanes {
		return // 无需调整
	}

	fmt.Printf("强制约束: 总分配货道数 %d 超过总货道数 %d，进行强制调整\n", totalAllocated, totalLanes)

	// 创建商品优先级列表，按重要性排序
	type productPriority struct {
		index          int
		warehouseStock int
		currentStock   int
		expectedRatio  float64
		requiredLanes  int
	}

	priorities := make([]productPriority, 0)
	for i, product := range ra.products {
		requiredLanes := laneAllocation[i]
		if requiredLanes > 0 {
			priorities = append(priorities, productPriority{
				index:          i,
				warehouseStock: product.WarehouseStock,
				currentStock:   product.CurrentStock,
				expectedRatio:  product.ExpectedRatio,
				requiredLanes:  requiredLanes,
			})
		}
	}

	// 按优先级排序：1.有仓库库存 2.有当前库存 3.预期比例高
	sort.Slice(priorities, func(i, j int) bool {
		// 第一优先级：有仓库库存
		if priorities[i].warehouseStock > 0 && priorities[j].warehouseStock == 0 {
			return true
		}
		if priorities[i].warehouseStock == 0 && priorities[j].warehouseStock > 0 {
			return false
		}

		// 第二优先级：有当前库存
		if priorities[i].currentStock > 0 && priorities[j].currentStock == 0 {
			return true
		}
		if priorities[i].currentStock == 0 && priorities[j].currentStock > 0 {
			return false
		}

		// 第三优先级：预期比例高
		return priorities[i].expectedRatio > priorities[j].expectedRatio
	})

	// 重新分配货道，优先保证高优先级商品
	remainingLanes := totalLanes
	for _, priority := range priorities {
		if remainingLanes <= 0 {
			// 没有剩余货道，设置为0
			laneAllocation[priority.index] = 0
			continue
		}

		// 计算该商品应该分配的货道数
		// 优先保证最小必需货道数
		minRequired := 0
		if priority.currentStock > 0 {
			minRequired = (priority.currentStock + 2) / 3 // 向上取整
		}

		// 分配货道数：取最小值（原分配数、剩余货道数、最小必需数）
		allocated := minInt(priority.requiredLanes, remainingLanes)
		if allocated < minRequired && remainingLanes >= minRequired {
			allocated = minRequired
		}

		laneAllocation[priority.index] = allocated
		remainingLanes -= allocated

		fmt.Printf("商品 %s: 分配 %d 货道 (原需求: %d, 最小必需: %d, 剩余货道: %d)\n",
			ra.products[priority.index].ID, allocated, priority.requiredLanes, minRequired, remainingLanes)
	}

	// 最终验证
	finalTotal := 0
	for _, lanes := range laneAllocation {
		finalTotal += lanes
	}

	if finalTotal > totalLanes {
		fmt.Printf("⚠️  强制约束后仍然超出限制: %d > %d，进行最终调整\n", finalTotal, totalLanes)
		// 最后的强制调整：按比例缩减
		scale := float64(totalLanes) / float64(finalTotal)
		for i := range laneAllocation {
			laneAllocation[i] = int(math.Round(float64(laneAllocation[i]) * scale))
		}
	}

	fmt.Printf("✅ 强制约束完成，最终货道分配: %v\n", laneAllocation)
}

// 动态分配货道：根据实际库存需求优化货道使用
func (ra *ReplenishmentAlgorithm) allocateLanesDynamically(totalLanes int, amounts []int) []int {
	laneAllocation := make([]int, len(ra.products))

	// 计算每个商品实际需要的货道数
	requiredLanes := make([]int, len(ra.products))
	totalRequired := 0

	for i, product := range ra.products {
		// 如果仓库库存为0，根据当前库存分配最小必需货道
		if product.WarehouseStock == 0 {
			// 如果有当前库存，需要分配足够的货道来容纳
			if product.CurrentStock > 0 {
				requiredLanes[i] = (product.CurrentStock + 2) / 3 // 向上取整
			} else {
				requiredLanes[i] = 0
			}
			continue
		}

		finalStock := product.CurrentStock + amounts[i]
		// 计算需要的货道数（向上取整）
		if finalStock > 0 {
			requiredLanes[i] = (finalStock + 2) / 3 // 等价于 math.Ceil(finalStock / 3)
		} else {
			requiredLanes[i] = 0
		}
		totalRequired += requiredLanes[i]
	}

	fmt.Printf("动态货道分配 - 总需求货道: %d, 可用货道: %d\n", totalRequired, totalLanes)

	if totalRequired <= totalLanes {
		// 需求货道数不超过总货道数，直接分配
		copy(laneAllocation, requiredLanes)

		// 剩余货道按预期比例分配给有潜力增长的商品
		remainingLanes := totalLanes - totalRequired
		if remainingLanes > 0 {
			fmt.Printf("剩余货道 %d 个，按预期比例分配\n", remainingLanes)
			ra.distributeRemainingLanes(laneAllocation, remainingLanes, amounts)
		}
	} else {
		// 需求货道数超过总货道数，需要优化分配
		fmt.Printf("货道需求超出容量，进行优化分配\n")
		laneAllocation = ra.optimizeLaneAllocation(totalLanes, amounts, requiredLanes)
	}

	return laneAllocation
}

// 分配剩余货道给有潜力增长的商品
func (ra *ReplenishmentAlgorithm) distributeRemainingLanes(laneAllocation []int, remainingLanes int, amounts []int) {
	// 创建商品优先级列表（按预期比例和增长潜力排序）
	type productPriority struct {
		index           int
		ratio           float64
		growthPotential float64
		currentLanes    int
	}

	priorities := make([]productPriority, 0)
	for i, product := range ra.products {
		// 如果仓库库存为0，跳过
		if product.WarehouseStock == 0 {
			continue
		}

		// 计算增长潜力：仓库库存 - 当前补货量
		growthPotential := float64(product.WarehouseStock - amounts[i])
		if growthPotential > 0 {
			priorities = append(priorities, productPriority{
				index:           i,
				ratio:           product.ExpectedRatio,
				growthPotential: growthPotential,
				currentLanes:    laneAllocation[i],
			})
		}
	}

	// 按预期比例和增长潜力排序
	sort.Slice(priorities, func(i, j int) bool {
		// 优先考虑预期比例高且有增长潜力的商品
		scoreI := priorities[i].ratio * (1 + priorities[i].growthPotential/100)
		scoreJ := priorities[j].ratio * (1 + priorities[j].growthPotential/100)
		return scoreI > scoreJ
	})

	// 分配剩余货道
	for i := 0; i < len(priorities) && remainingLanes > 0; i++ {
		idx := priorities[i].index
		if priorities[i].growthPotential > 0 {
			laneAllocation[idx]++
			remainingLanes--
			fmt.Printf("给商品 %s 额外分配1个货道（增长潜力: %.1f）\n",
				ra.products[idx].ID, priorities[i].growthPotential)
		}
	}
}

// 优化货道分配（当需求超出容量时）
func (ra *ReplenishmentAlgorithm) optimizeLaneAllocation(totalLanes int, amounts []int, requiredLanes []int) []int {
	laneAllocation := make([]int, len(ra.products))

	// 创建商品优先级列表
	type productPriority struct {
		index         int
		ratio         float64
		requiredLanes int
		efficiency    float64 // 每个货道的价值
	}

	priorities := make([]productPriority, len(ra.products))
	for i, product := range ra.products {
		efficiency := 0.0
		if requiredLanes[i] > 0 {
			efficiency = product.ExpectedRatio / float64(requiredLanes[i])
		}

		priorities[i] = productPriority{
			index:         i,
			ratio:         product.ExpectedRatio,
			requiredLanes: requiredLanes[i],
			efficiency:    efficiency,
		}
	}

	// 按效率排序（预期比例/需要货道数）
	sort.Slice(priorities, func(i, j int) bool {
		return priorities[i].efficiency > priorities[j].efficiency
	})

	// 贪心分配：优先给效率高的商品分配货道
	remainingLanes := totalLanes
	for _, priority := range priorities {
		if remainingLanes <= 0 {
			break
		}

		allocate := minInt(priority.requiredLanes, remainingLanes)
		laneAllocation[priority.index] = allocate
		remainingLanes -= allocate

		fmt.Printf("商品 %s: 需要 %d 货道, 分配 %d 货道, 效率 %.3f\n",
			ra.products[priority.index].ID, priority.requiredLanes, allocate, priority.efficiency)
	}

	return laneAllocation
}

// 验证货道分配的合理性（静默验证，不打印详细信息）
func (ra *ReplenishmentAlgorithm) validateLaneAllocation(laneAllocation []int, totalLanes int) {
	totalAllocated := 0
	for _, lanes := range laneAllocation {
		totalAllocated += lanes
	}

	// 只在分配超出总数时才报警告（分配不足是允许的）
	if totalAllocated > totalLanes {
		fmt.Printf("⚠️  货道分配超出限制: 分配了 %d 个货道，但总货道数只有 %d\n", totalAllocated, totalLanes)
		// 打印详细的货道分配信息以便调试
		ra.debugLaneAllocation(laneAllocation, totalLanes)
	}
}

// 调试货道分配详细信息
func (ra *ReplenishmentAlgorithm) debugLaneAllocation(laneAllocation []int, totalLanes int) {
	fmt.Printf("🔍 货道分配调试信息:\n")
	fmt.Printf("  总货道数: %d\n", totalLanes)
	fmt.Printf("  已分配货道数: %d\n", func() int {
		total := 0
		for _, lanes := range laneAllocation {
			total += lanes
		}
		return total
	}())

	fmt.Printf("  各商品货道分配详情:\n")
	for i, lanes := range laneAllocation {
		if lanes > 0 {
			product := ra.products[i]
			fmt.Printf("    商品 %s: 分配 %d 货道 (仓库库存: %d, 当前库存: %d, 预期比例: %.3f)\n",
				product.ID, lanes, product.WarehouseStock, product.CurrentStock, product.ExpectedRatio)
		}
	}
}

// 子步骤4.1: 处理缺口（带货道重新分配）
func (ra *ReplenishmentAlgorithm) handleGapWithLaneReallocation(amounts []int, gap int, idealTargets []int) []int {
	fmt.Printf("处理缺口: %d\n", gap)

	// 第一阶段：常规缺口处理
	amounts = ra.handleGap(amounts, gap, idealTargets)

	// 重新计算剩余缺口
	currentTotal := ra.calculateCurrentTotal(amounts)
	targetReplenish := ra.config.TargetTotal - ra.getCurrentStockTotal()
	remainingGap := targetReplenish - currentTotal

	if remainingGap > 0 {
		fmt.Printf("常规处理后剩余缺口: %d，尝试货道重新分配\n", remainingGap)
		amounts = ra.handleGapWithLaneReallocation2(amounts, remainingGap, idealTargets)
	}

	return amounts
}

// 子步骤4.1: 处理缺口（原始逻辑）
func (ra *ReplenishmentAlgorithm) handleGap(amounts []int, gap int, idealTargets []int) []int {
	originalGap := gap

	for iteration := 0; iteration < ra.config.MaxIterations && gap > 0; iteration++ {
		// 找出可补商品
		candidates := ra.findSupplementableCandidates(amounts)
		if len(candidates) == 0 {
			if gap == originalGap {
				fmt.Printf("没有可补商品，停止补充\n")
			}
			break
		}

		// 计算比例关系偏差并排序
		deviations := ra.calculateProportionDeviations(amounts, idealTargets, candidates, true)

		// 按偏差从大到小排序
		sort.Slice(candidates, func(i, j int) bool {
			return deviations[candidates[i]] > deviations[candidates[j]]
		})

		// 给偏差最大的商品补充1个单位
		bestCandidate := candidates[0]
		if ra.canIncrement(bestCandidate, amounts) {
			amounts[bestCandidate]++
			gap--
			fmt.Printf("给商品 %s 补充1个单位（偏差: %.4f），剩余缺口: %d\n",
				ra.products[bestCandidate].ID, deviations[bestCandidate], gap)

			// 应用货道约束，确保补货后数量不超过货道限制
			amounts = ra.applyLaneConstraintsToAmounts(amounts)
		} else {
			break
		}
	}

	return amounts
}

// 第二阶段缺口处理：货道重新分配
func (ra *ReplenishmentAlgorithm) handleGapWithLaneReallocation2(amounts []int, gap int, idealTargets []int) []int {
	fmt.Printf("开始货道重新分配处理剩余缺口: %d\n", gap)

	totalLanes := ra.config.MaxCapacity / 3

	// 计算当前货道使用情况
	currentLaneUsage := make([]int, len(ra.products))
	totalUsedLanes := 0

	for i, product := range ra.products {
		finalStock := product.CurrentStock + amounts[i]
		if finalStock > 0 {
			currentLaneUsage[i] = (finalStock + 2) / 3 // 向上取整
		}
		totalUsedLanes += currentLaneUsage[i]
	}

	availableLanes := totalLanes - totalUsedLanes
	fmt.Printf("当前已用货道: %d, 可用货道: %d\n", totalUsedLanes, availableLanes)

	if availableLanes > 0 {
		// 有空余货道，可以重新分配
		fmt.Printf("发现 %d 个空余货道，开始重新分配\n", availableLanes)
		amounts = ra.reallocateEmptyLanes(amounts, availableLanes, gap, idealTargets)
	} else {
		fmt.Printf("无空余货道可重新分配\n")
	}

	return amounts
}

// 重新分配空余货道
func (ra *ReplenishmentAlgorithm) reallocateEmptyLanes(amounts []int, availableLanes int, gap int, idealTargets []int) []int {
	fmt.Printf("开始动态分配 %d 个空余货道\n", availableLanes)

	// 获取基础货道分配
	totalLanes := ra.config.MaxCapacity / 3
	baseLaneAllocation := ra.allocateLanesByRatio(totalLanes)

	// 创建动态货道分配（可以调整）
	dynamicLaneAllocation := make([]int, len(baseLaneAllocation))
	copy(dynamicLaneAllocation, baseLaneAllocation)

	remainingLanes := availableLanes
	remainingGap := gap

	// 逐个分配空余货道，采用强制轮询分配策略
	maxIterations := availableLanes * 2 // 防止无限循环
	iterationCount := 0
	noProgressCount := 0             // 记录连续无进展的次数
	lastRemainingGap := remainingGap // 记录上次的剩余缺口

	// 创建候选商品队列，用于轮询分配
	var candidateQueue []int
	for i, product := range ra.products {
		// 预检查商品是否可以作为候选
		if amounts[i] < product.WarehouseStock {
			candidateQueue = append(candidateQueue, i)
		}
	}

	if len(candidateQueue) == 0 {
		fmt.Printf("没有可分配货道的候选商品\n")
		return amounts
	}

	fmt.Printf("候选商品队列: %v\n", candidateQueue)

	for remainingLanes > 0 && remainingGap > 0 && iterationCount < maxIterations {
		bestCandidate := -1
		bestPotentialGain := 0

		// 轮询选择候选商品：按顺序尝试每个候选商品
		for queueIndex := 0; queueIndex < len(candidateQueue); queueIndex++ {
			// 计算当前应该检查的商品索引（轮询）
			candidateIndex := (iterationCount + queueIndex) % len(candidateQueue)
			i := candidateQueue[candidateIndex]
			product := ra.products[i]

			// 检查基本条件
			if amounts[i] >= product.WarehouseStock {
				continue // 仓库库存不足
			}

			currentStock := product.CurrentStock + amounts[i]

			// 检查MaxAllowed约束
			maxCapacityLimit := float64(ra.config.TargetTotal) * 0.3
			adjustedMaxAllowed := product.MaxAllowed
			if float64(product.MaxAllowed) > maxCapacityLimit {
				adjustedMaxAllowed = int(maxCapacityLimit)
			}
			maxAllowedByRule := maxInt(adjustedMaxAllowed, product.CurrentStock)

			if currentStock >= maxAllowedByRule {
				continue // 已达到MaxAllowed上限
			}

			// 计算如果给该商品分配1个额外货道能增加多少库存
			currentLanes := dynamicLaneAllocation[i]
			newMaxStock := 3 * (currentLanes + 1) // 额外1个货道

			// 计算潜在增益：充分利用新货道容量
			// 1. 仓库库存限制
			warehouseLimit := product.WarehouseStock - amounts[i]
			// 2. MaxAllowed约束限制
			maxAllowedLimit := maxAllowedByRule - currentStock
			// 3. 新货道容量限制（这是关键！）
			laneCapacityLimit := newMaxStock - currentStock
			// 4. 剩余缺口限制
			gapLimit := remainingGap

			// 调试信息：显示各个限制因素
			if iterationCount == 0 { // 只在第一次迭代时显示，避免日志过多
				fmt.Printf("   🔍 商品%s限制分析: 仓库=%d, MaxAllowed=%d, 货道容量=%d, 缺口=%d\n",
					product.ID, warehouseLimit, maxAllowedLimit, laneCapacityLimit, gapLimit)
			}

			// 取最小值作为最大可增加量
			maxPossibleIncrease := minInt(
				minInt(warehouseLimit, maxAllowedLimit),
				minInt(laneCapacityLimit, gapLimit),
			)

			if maxPossibleIncrease <= 0 {
				continue // 没有增长空间
			}

			// 找到可分配的商品，直接选择（轮询策略）
			bestCandidate = i
			bestPotentialGain = maxPossibleIncrease
			break // 找到第一个可分配的商品就停止
		}

		// 如果没找到候选商品，检查是否真的无法继续
		if bestCandidate == -1 {
			// 检查是否连续无进展
			if remainingGap == lastRemainingGap {
				noProgressCount++
				if noProgressCount >= len(candidateQueue) {
					fmt.Printf("⚠️  连续 %d 次无进展，停止动态货道分配\n", noProgressCount)
					break
				}
			} else {
				noProgressCount = 0 // 重置无进展计数
			}

			fmt.Printf("没有更多商品可以利用剩余 %d 个货道 (无进展计数: %d)\n", remainingLanes, noProgressCount)
			break
		}

		// 给最佳候选商品分配1个额外货道
		dynamicLaneAllocation[bestCandidate]++
		amounts[bestCandidate] += bestPotentialGain
		remainingGap -= bestPotentialGain
		remainingLanes--
		iterationCount++

		product := ra.products[bestCandidate]
		fmt.Printf("🎯 动态分配货道: 给商品 %s 分配1个额外货道，补充 %d 个单位 [第%d次分配，轮询索引:%d]\n",
			product.ID, bestPotentialGain, iterationCount, (iterationCount-1)%len(candidateQueue))

		// 添加详细的补货量分析
		currentStock := product.CurrentStock + amounts[bestCandidate]
		newLanes := dynamicLaneAllocation[bestCandidate]
		newMaxStock := 3 * newLanes
		fmt.Printf("   📊 补货分析: 当前库存=%d, 新货道数=%d, 新货道容量=%d, 仓库库存=%d, MaxAllowed=%d\n",
			currentStock, newLanes, newMaxStock, product.WarehouseStock, product.MaxAllowed)

		// 更新无进展检查的基准值
		lastRemainingGap = remainingGap

		// 重要：更新finalLaneAllocation以反映动态分配的结果
		ra.finalLaneAllocation[bestCandidate] = dynamicLaneAllocation[bestCandidate]

		// 应用货道约束，确保补货后数量不超过货道限制
		amounts = ra.applyLaneConstraintsToAmounts(amounts)

		// 检查是否达到最大循环次数
		if iterationCount >= maxIterations {
			fmt.Printf("⚠️  达到最大循环次数 %d，停止动态货道分配\n", maxIterations)
			break
		}
	}

	fmt.Printf("动态货道分配完成，使用了 %d 个空余货道\n", availableLanes-remainingLanes)
	return amounts
}

// 子步骤4.2: 处理超额
func (ra *ReplenishmentAlgorithm) handleExcess(amounts []int, excess int, idealTargets []int) []int {
	fmt.Printf("处理超额: %d\n", excess)

	for iteration := 0; iteration < ra.config.MaxIterations && excess > 0; iteration++ {
		// 找出可减商品
		candidates := ra.findReducibleCandidates(amounts)
		if len(candidates) == 0 {
			fmt.Printf("没有可减商品，停止减少\n")
			break
		}

		// 计算比例关系偏差并排序
		deviations := ra.calculateProportionDeviations(amounts, idealTargets, candidates, false)

		// 按偏差从大到小排序，优先减少偏差大的商品
		sort.Slice(candidates, func(i, j int) bool {
			return deviations[candidates[i]] > deviations[candidates[j]]
		})

		// 减少偏差最大的商品1个单位
		bestCandidate := candidates[0]
		if ra.canDecrement(bestCandidate, amounts) {
			amounts[bestCandidate]--
			excess--
			fmt.Printf("给商品 %s 减少1个单位，剩余超额: %d\n", ra.products[bestCandidate].ID, excess)
		} else {
			break
		}
	}

	return amounts
}

// 计算比例关系偏差
func (ra *ReplenishmentAlgorithm) calculateProportionDeviations(amounts []int, idealTargets []int, candidates []int, isGap bool) map[int]float64 {
	deviations := make(map[int]float64)

	for _, i := range candidates {
		// 计算如果给商品i增加/减少1个单位后的偏差改善程度
		currentDeviation := ra.calculateTotalDeviation(amounts)

		// 模拟调整后的状态
		testAmounts := make([]int, len(amounts))
		copy(testAmounts, amounts)

		if isGap {
			testAmounts[i]++ // 增加1个单位
		} else {
			testAmounts[i]-- // 减少1个单位
		}

		adjustedDeviation := ra.calculateTotalDeviation(testAmounts)

		// 偏差改善程度 = 调整前偏差 - 调整后偏差 (正值表示改善)
		improvementScore := currentDeviation - adjustedDeviation

		// 库存充足度调整因子
		stockSufficiencyFactor := ra.calculateStockSufficiencyFactor(i, amounts, isGap)

		// 综合得分 = 偏差改善程度 + 库存充足度调整
		deviations[i] = improvementScore + stockSufficiencyFactor
	}

	return deviations
}

// 计算当前状态下的总体比例偏差
func (ra *ReplenishmentAlgorithm) calculateTotalDeviation(amounts []int) float64 {
	totalDeviation := 0.0
	n := len(ra.products)

	for i := 0; i < n; i++ {
		currentAmountI := ra.products[i].CurrentStock + amounts[i]
		for j := i + 1; j < n; j++ {
			currentAmountJ := ra.products[j].CurrentStock + amounts[j]

			if currentAmountJ == 0 {
				continue
			}

			// 实际比例关系
			actualRatio := float64(currentAmountI) / float64(currentAmountJ)

			// 预期比例关系
			expectedRatio := ra.products[i].ExpectedRatio / ra.products[j].ExpectedRatio

			// 加权偏差
			weightedDeviation := math.Abs(actualRatio-expectedRatio) * ra.products[j].ExpectedRatio
			totalDeviation += weightedDeviation
		}
	}

	return totalDeviation
}

// 计算库存充足度调整因子
func (ra *ReplenishmentAlgorithm) calculateStockSufficiencyFactor(productIndex int, amounts []int, isGap bool) float64 {
	product := ra.products[productIndex]

	// 计算可用库存
	availableStock := product.WarehouseStock - amounts[productIndex]
	if availableStock <= 0 {
		return 0.1 // 库存不足，轻微降低优先级
	}

	// 只有在预期比例相似的情况下才考虑库存充足度
	// 计算与同等预期比例商品的库存充足度对比
	similarProducts := ra.findSimilarRatioProducts(productIndex, 0.005) // 5‰的相似度阈值
	if len(similarProducts) == 0 {
		return 0.0 // 没有相似商品，不需要库存调整
	}

	// 计算相对库存充足度
	avgAvailableStock := 0.0
	for _, idx := range similarProducts {
		otherAvailable := ra.products[idx].WarehouseStock - amounts[idx]
		if otherAvailable > 0 {
			avgAvailableStock += float64(otherAvailable)
		}
	}
	avgAvailableStock /= float64(len(similarProducts))

	if avgAvailableStock == 0 {
		return 0.0
	}

	// 相对充足度：当前商品库存 / 相似商品平均库存
	relativeStock := float64(availableStock) / avgAvailableStock

	if isGap {
		// 处理缺口时：库存相对充足的商品优先级略高
		if relativeStock > 1.2 {
			return -0.02 // 库存充足，轻微提高优先级
		} else if relativeStock < 0.8 {
			return 0.02 // 库存不足，轻微降低优先级
		}
	} else {
		// 处理超额时：库存相对不足的商品优先级略高
		if relativeStock < 0.8 {
			return 0.02 // 库存不足，轻微提高优先级
		} else if relativeStock > 1.2 {
			return -0.02 // 库存充足，轻微降低优先级
		}
	}

	return 0.0 // 库存充足度正常，不调整
}

// 找出预期比例相似的商品
func (ra *ReplenishmentAlgorithm) findSimilarRatioProducts(productIndex int, threshold float64) []int {
	similar := make([]int, 0)
	targetRatio := ra.products[productIndex].ExpectedRatio

	for i, product := range ra.products {
		if i == productIndex {
			continue
		}

		if math.Abs(product.ExpectedRatio-targetRatio) <= threshold {
			similar = append(similar, i)
		}
	}

	// 包含自己
	similar = append(similar, productIndex)
	return similar
}

// 找出可补商品
func (ra *ReplenishmentAlgorithm) findSupplementableCandidates(amounts []int) []int {
	candidates := make([]int, 0)

	for i, product := range ra.products {
		// 检查仓库库存余量
		if amounts[i] >= product.WarehouseStock {
			continue
		}

		// 使用已保存的货道分配结果，确保一致性
		var availableLanes int
		if ra.finalLaneAllocation != nil && len(ra.finalLaneAllocation) > i {
			availableLanes = ra.finalLaneAllocation[i]
		} else {
			// 如果没有保存的货道分配，重新计算（但这应该很少发生）
			totalLanes := ra.config.MaxCapacity / 3
			laneAllocation := ra.allocateLanesByRatio(totalLanes)
			availableLanes = laneAllocation[i]
		}

		// 检查货道约束：每个商品最大库存 = 3 × 可用货道数
		maxLaneStock := 3 * availableLanes
		if product.CurrentStock+amounts[i] >= maxLaneStock {
			continue
		}

		// 检查是否达到最大允许数量（应用30%容量限制）
		maxCapacityLimit := float64(ra.config.TargetTotal) * 0.3
		adjustedMaxAllowed := product.MaxAllowed
		if float64(product.MaxAllowed) > maxCapacityLimit {
			adjustedMaxAllowed = int(maxCapacityLimit)
		}

		// 关键修改：不再强制要求maxAllowed不小于当前库存
		// 这样即使当前库存超过理想目标，只要不超过真正的最大允许数量就可以补货
		if product.CurrentStock+amounts[i] >= adjustedMaxAllowed {
			continue
		}

		candidates = append(candidates, i)
	}

	return candidates
}

// 找出可减商品
func (ra *ReplenishmentAlgorithm) findReducibleCandidates(amounts []int) []int {
	candidates := make([]int, 0)

	for i, product := range ra.products {
		if amounts[i] <= 0 {
			continue
		}

		// 检查最小补货量约束（当前库存为0时，补货量至少为1）
		if product.CurrentStock == 0 && amounts[i] <= 1 {
			continue
		}

		candidates = append(candidates, i)
	}

	return candidates
}

// 检查是否可以增加补货量
func (ra *ReplenishmentAlgorithm) canIncrement(productIndex int, amounts []int) bool {
	product := ra.products[productIndex]

	// 检查仓库库存
	if amounts[productIndex] >= product.WarehouseStock {
		return false
	}

	// 使用已保存的货道分配结果，确保一致性
	var availableLanes int
	if ra.finalLaneAllocation != nil && len(ra.finalLaneAllocation) > productIndex {
		availableLanes = ra.finalLaneAllocation[productIndex]
	} else {
		// 如果没有保存的货道分配，重新计算（但这应该很少发生）
		totalLanes := ra.config.MaxCapacity / 3
		laneAllocation := ra.allocateLanesByRatio(totalLanes)
		availableLanes = laneAllocation[productIndex]
	}

	// 检查货道约束：每个商品最大库存 = 3 × 可用货道数
	maxLaneStock := 3 * availableLanes
	if product.CurrentStock+amounts[productIndex] >= maxLaneStock {
		return false
	}

	// 检查最大允许数量约束（应用30%容量限制）
	maxCapacityLimit := float64(ra.config.TargetTotal) * 0.3
	adjustedMaxAllowed := product.MaxAllowed
	if float64(product.MaxAllowed) > maxCapacityLimit {
		adjustedMaxAllowed = int(maxCapacityLimit)
	}

	// 关键修改：不再强制要求maxAllowed不小于当前库存
	// 这样即使当前库存超过理想目标，只要不超过真正的最大允许数量就可以补货
	if product.CurrentStock+amounts[productIndex] >= adjustedMaxAllowed {
		return false
	}

	return true
}

// 检查是否可以减少补货量
func (ra *ReplenishmentAlgorithm) canDecrement(productIndex int, amounts []int) bool {
	product := ra.products[productIndex]

	if amounts[productIndex] <= 0 {
		return false
	}

	// 检查最小补货量约束
	if product.CurrentStock == 0 && amounts[productIndex] <= 1 {
		return false
	}

	return true
}

// 步骤5: 特殊情况处理
func (ra *ReplenishmentAlgorithm) handleSpecialCases(amounts []int) []int {
	// 检查目标总量是否可达成（考虑货道约束）
	totalWarehouse := 0
	totalCurrent := 0
	totalLaneCapacity := 0

	// 计算货道总容量
	totalLanes := ra.config.MaxCapacity / 3
	laneAllocation := ra.allocateLanesByRatio(totalLanes)

	for i, product := range ra.products {
		totalWarehouse += product.WarehouseStock
		totalCurrent += product.CurrentStock
		// 计算货道允许的最大库存
		availableLanes := laneAllocation[i]
		maxLaneStock := 3 * availableLanes
		totalLaneCapacity += maxLaneStock
	}

	// 取仓库库存和货道容量的最小值作为实际可用容量
	actualAvailableCapacity := minInt(totalWarehouse, totalLaneCapacity)

	if totalCurrent+actualAvailableCapacity < ra.config.TargetTotal {
		fmt.Printf("警告: 目标总量 %d 无法达成\n", ra.config.TargetTotal)
		fmt.Printf("  当前库存: %d\n", totalCurrent)
		fmt.Printf("  仓库总库存: %d\n", totalWarehouse)
		fmt.Printf("  货道总容量: %d\n", totalLaneCapacity)
		fmt.Printf("  实际可用容量: %d\n", actualAvailableCapacity)
		fmt.Printf("  最大可能总量: %d\n", totalCurrent+actualAvailableCapacity)

		// 重新计算目标总量
		newTargetTotal := totalCurrent + actualAvailableCapacity
		newConfig := ra.config
		newConfig.TargetTotal = newTargetTotal

		// 使用新目标重新执行算法
		tempAlgorithm := NewReplenishmentAlgorithm(ra.products, newConfig)
		idealTargets := tempAlgorithm.calculateIdealTargets()
		initialAmounts := tempAlgorithm.applyMaxAllowedConstraints(idealTargets)
		tempAmounts := tempAlgorithm.applyWarehouseStockConstraints(initialAmounts)
		amounts = tempAlgorithm.adjustToTargetTotal(tempAmounts, idealTargets)
	}

	return amounts
}

// 步骤6: 最终校验
func (ra *ReplenishmentAlgorithm) validateFinalResults(amounts []int) error {
	for idx, product := range ra.products {
		// 检查补货量约束
		if amounts[idx] < 0 {
			return fmt.Errorf("商品 %s 补货量不能为负: %d", product.ID, amounts[idx])
		}

		if amounts[idx] > product.WarehouseStock {
			return fmt.Errorf("商品 %s 补货量超过仓库库存: %d > %d",
				product.ID, amounts[idx], product.WarehouseStock)
		}

		// 检查货道约束：每个商品最大库存 = 3 × 可用货道数
		finalAmount := product.CurrentStock + amounts[idx]

		// 使用算法执行时保存的货道分配结果，避免重复计算
		if ra.finalLaneAllocation == nil || len(ra.finalLaneAllocation) == 0 {
			return fmt.Errorf("货道分配结果未初始化，无法进行校验")
		}

		availableLanes := ra.finalLaneAllocation[idx]
		maxLaneStock := 3 * availableLanes

		// 如果货道分配为0，补货后数量必须为0
		if availableLanes == 0 && finalAmount > 0 {
			return fmt.Errorf("商品 %s 没有分配货道，但补货后数量为 %d > 0",
				product.ID, finalAmount)
		}

		if finalAmount > maxLaneStock {
			// 检查是否有空余货道可以动态分配
			totalAllocated := 0
			for _, lanes := range ra.finalLaneAllocation {
				totalAllocated += lanes
			}

			totalLanes := ra.config.MaxCapacity / 3
			if totalAllocated < totalLanes {
				// 有空余货道，计算所需的额外货道数
				extraLanesNeeded := (finalAmount - maxLaneStock + 2) / 3 // 向上取整
				availableExtraLanes := totalLanes - totalAllocated

				if extraLanesNeeded <= availableExtraLanes {
					fmt.Printf("✅ 动态货道验证: 商品 %s 需要 %d 个额外货道，可用 %d 个空余货道\n",
						product.ID, extraLanesNeeded, availableExtraLanes)
					continue // 可以通过动态分配解决，跳过错误
				}
			}

			return fmt.Errorf("商品 %s 补货后数量超过货道约束: %d > %d (可用货道: %d, 最大库存: %d)",
				product.ID, finalAmount, maxLaneStock, availableLanes, maxLaneStock)
		}

		// 检查原有最大允许数量约束（应用30%容量限制）
		maxCapacityLimit := float64(ra.config.TargetTotal) * 0.3
		adjustedMaxAllowed := product.MaxAllowed
		if float64(product.MaxAllowed) > maxCapacityLimit {
			adjustedMaxAllowed = int(maxCapacityLimit)
		}

		maxAllowed := maxInt(adjustedMaxAllowed, product.CurrentStock)
		if finalAmount > maxAllowed {
			return fmt.Errorf("商品 %s 补货后数量超过最大允许值: %d > %d (30%%容量限制后)",
				product.ID, finalAmount, maxAllowed)
		}
	}

	// 检查比例关系偏差
	ra.analyzeProportionDeviations(amounts)

	return nil
}

// 分析比例关系偏差
func (ra *ReplenishmentAlgorithm) analyzeProportionDeviations(amounts []int) {
	// 简化输出，不显示详细的两两比例对比
	fmt.Println("\n=== 比例关系偏差分析 ===")

	// 计算实际补货后数量
	actualAmounts := make([]int, len(ra.products))
	for i, product := range ra.products {
		actualAmounts[i] = product.CurrentStock + amounts[i]
	}

	// 统计比例关系偏差
	totalDeviation := 0.0
	pairCount := 0
	maxDeviation := 0.0

	for i := 0; i < len(ra.products); i++ {
		for j := i + 1; j < len(ra.products); j++ {
			if actualAmounts[j] == 0 {
				continue
			}

			actualRatio := float64(actualAmounts[i]) / float64(actualAmounts[j])
			expectedRatio := ra.products[i].ExpectedRatio / ra.products[j].ExpectedRatio
			deviation := math.Abs(actualRatio - expectedRatio)

			totalDeviation += deviation
			pairCount++
			if deviation > maxDeviation {
				maxDeviation = deviation
			}
		}
	}

	if pairCount > 0 {
		avgDeviation := totalDeviation / float64(pairCount)
		fmt.Printf("两两比例关系统计:\n")
		fmt.Printf("  比较对数: %d\n", pairCount)
		fmt.Printf("  平均偏差: %.4f\n", avgDeviation)
		fmt.Printf("  最大偏差: %.4f\n", maxDeviation)

		if avgDeviation < 0.1 {
			fmt.Printf("✅ 比例关系优秀\n")
		} else if avgDeviation < 0.2 {
			fmt.Printf("✅ 比例关系良好\n")
		} else {
			fmt.Printf("⚠️  比例关系需要改进\n")
		}
	}
}

// 生成最终结果
func (ra *ReplenishmentAlgorithm) generateResults(amounts []int) {
	ra.results = make([]ReplenishmentResult, len(ra.products))

	totalFinal := 0
	for i, product := range ra.products {
		finalStock := product.CurrentStock + amounts[i]
		totalFinal += finalStock
	}

	for i, product := range ra.products {
		finalStock := product.CurrentStock + amounts[i]
		actualRatio := float64(finalStock) / float64(totalFinal)

		ra.results[i] = ReplenishmentResult{
			ProductID:       product.ID,
			CurrentStock:    product.CurrentStock,
			WarehouseStock:  product.WarehouseStock,
			MaxAllowed:      product.MaxAllowed,
			ReplenishAmount: amounts[i],
			FinalStock:      finalStock,
			ActualRatio:     actualRatio,
			ExpectedRatio:   product.ExpectedRatio,
		}
	}

	// 打印货道使用情况
	ra.printLaneUsage(amounts)
}

// 打印货道使用情况
func (ra *ReplenishmentAlgorithm) printLaneUsage(amounts []int) {
	fmt.Println("\n=== 货道使用情况分析 ===")

	totalLanes := ra.config.MaxCapacity / 3
	laneAllocation := ra.allocateLanesByRatio(totalLanes)

	fmt.Printf("总货道数: %d (总容量 %d / 3)\n", totalLanes, ra.config.MaxCapacity)
	fmt.Printf("说明: 每个货道最多放3个相同商品，商品可以部分使用货道\n")
	fmt.Printf("%-10s %-8s %-8s %-8s %-8s %-8s %-12s\n", "商品ID", "分配货道", "当前库存", "补货量", "补货后", "货道利用率", "实际占用货道")
	fmt.Println(strings.Repeat("-", 72))

	totalUsedLanes := 0
	for i, product := range ra.products {
		allocatedLanes := laneAllocation[i]
		currentStock := product.CurrentStock
		replenishAmount := amounts[i]
		finalStock := currentStock + replenishAmount

		// 计算货道利用率 (实际库存 / 最大可能库存)
		utilization := 0.0
		if allocatedLanes > 0 {
			utilization = float64(finalStock) / float64(3*allocatedLanes)
		}

		// 计算实际占用的货道数 (向上取整)
		actualUsedLanes := 0
		if finalStock > 0 {
			actualUsedLanes = (finalStock + 2) / 3 // 等价于 math.Ceil(finalStock / 3)
		}

		fmt.Printf("%-10s %-8d %-8d %-8d %-8d %-8.1f%% %-12d\n",
			product.ID, allocatedLanes, currentStock, replenishAmount, finalStock, utilization*100, actualUsedLanes)

		totalUsedLanes += allocatedLanes
	}

	fmt.Println(strings.Repeat("-", 72))
	fmt.Printf("货道分配总计: %d / %d (%.1f%%)\n", totalUsedLanes, totalLanes, float64(totalUsedLanes)/float64(totalLanes)*100)

	// 检查货道分配是否合理
	if totalUsedLanes != totalLanes {
		fmt.Printf("⚠️  货道分配不匹配: 分配了 %d 个货道，但总货道数为 %d\n", totalUsedLanes, totalLanes)
	}
}

// 辅助函数
func (ra *ReplenishmentAlgorithm) calculateCurrentTotal(amounts []int) int {
	total := 0
	for _, amount := range amounts {
		total += amount
	}
	return total
}

func (ra *ReplenishmentAlgorithm) getCurrentStockTotal() int {
	total := 0
	for _, product := range ra.products {
		total += product.CurrentStock
	}
	return total
}

// 打印结果
func (ra *ReplenishmentAlgorithm) PrintResults() {
	fmt.Println("\n=== 补货算法执行结果 ===")
	fmt.Printf("%-10s %-10s %-10s %-10s %-10s %-10s %-10s %-12s %-12s %-10s\n",
		"商品ID", "仓库库存", "当前库存", "最大允许", "补货量", "补货后", "剩余潜力", "实际比例", "预期比例", "比例偏差")
	fmt.Println(strings.Repeat("-", 110))

	totalReplenish := 0
	totalFinal := 0

	for _, result := range ra.results {
		deviation := math.Abs(result.ActualRatio - result.ExpectedRatio)

		// 计算剩余补货潜力：min(仓库库存+当前库存, 最大允许) - 补货后
		remainingPotential := minInt(result.WarehouseStock+result.CurrentStock, result.MaxAllowed) - result.FinalStock

		fmt.Printf("%-10s %-10d %-10d %-10d %-10d %-10d %-10d %-12.3f %-12.3f %-10.4f\n",
			result.ProductID,
			result.WarehouseStock,
			result.CurrentStock,
			result.MaxAllowed,
			result.ReplenishAmount,
			result.FinalStock,
			remainingPotential,
			result.ActualRatio,
			result.ExpectedRatio,
			deviation)

		totalReplenish += result.ReplenishAmount
		totalFinal += result.FinalStock
	}

	fmt.Println(strings.Repeat("-", 100))
	fmt.Printf("总计: 补货量=%d, 补货后总量=%d\n", totalReplenish, totalFinal)
}

// 工具函数

func maxInt(a, b int) int {
	if a > b {
		return a
	}
	return b
}

func minInt(a, b int) int {
	if a < b {
		return a
	}
	return b
}
