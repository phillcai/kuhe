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
	products []Product
	config   ReplenishmentConfig
	results  []ReplenishmentResult
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

	for i, product := range ra.products {
		// 限制X_i不超过0.3K
		adjustedMaxAllowed := product.MaxAllowed
		if float64(product.MaxAllowed) > maxCapacityLimit {
			adjustedMaxAllowed = int(maxCapacityLimit)
			fmt.Printf("商品%d的最大允许数量从%d调整为%d (30%%容量限制)\n",
				i, product.MaxAllowed, adjustedMaxAllowed)
		}

		maxAllowed := maxInt(adjustedMaxAllowed, product.CurrentStock)
		idealAmount := max(idealTargets[i]-product.CurrentStock, 0)

		if product.CurrentStock+idealAmount <= maxAllowed {
			initialAmounts[i] = idealAmount
		} else {
			initialAmounts[i] = maxAllowed - product.CurrentStock
		}
	}

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

	currentTotal := ra.calculateCurrentTotal(finalAmounts)
	targetReplenish := ra.config.TargetTotal - ra.getCurrentStockTotal()

	fmt.Printf("当前补货总量: %d, 目标补货总量: %d\n", currentTotal, targetReplenish)

	if currentTotal < targetReplenish {
		// 子步骤4.1: 存在缺口，需要补充
		finalAmounts = ra.handleGap(finalAmounts, targetReplenish-currentTotal, idealTargets)
	} else if currentTotal > targetReplenish {
		// 子步骤4.2: 存在超额，需要减少
		finalAmounts = ra.handleExcess(finalAmounts, currentTotal-targetReplenish, idealTargets)
	}

	return finalAmounts
}

// 子步骤4.1: 处理缺口
func (ra *ReplenishmentAlgorithm) handleGap(amounts []int, gap int, idealTargets []int) []int {
	fmt.Printf("处理缺口: %d\n", gap)

	for iteration := 0; iteration < ra.config.MaxIterations && gap > 0; iteration++ {
		// 找出可补商品
		candidates := ra.findSupplementableCandidates(amounts)
		if len(candidates) == 0 {
			fmt.Printf("没有可补商品，停止补充\n")
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
		} else {
			break
		}
	}

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

		// 检查是否达到最大允许数量
		maxAllowed := maxInt(product.MaxAllowed, product.CurrentStock)
		if product.CurrentStock+amounts[i] >= maxAllowed {
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

	// 检查最大允许数量（应用30%容量限制）
	maxCapacityLimit := float64(ra.config.TargetTotal) * 0.3
	adjustedMaxAllowed := product.MaxAllowed
	if float64(product.MaxAllowed) > maxCapacityLimit {
		adjustedMaxAllowed = int(maxCapacityLimit)
	}

	maxAllowed := max(adjustedMaxAllowed, product.CurrentStock)
	if product.CurrentStock+amounts[productIndex] >= maxAllowed {
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
	// 检查目标总量是否可达成
	totalWarehouse := 0
	totalCurrent := 0

	for _, product := range ra.products {
		totalWarehouse += product.WarehouseStock
		totalCurrent += product.CurrentStock
	}

	if totalCurrent+totalWarehouse < ra.config.TargetTotal {
		fmt.Printf("警告: 目标总量 %d 无法达成，最大可能总量为 %d\n",
			ra.config.TargetTotal, totalCurrent+totalWarehouse)

		// 重新计算目标总量
		newTargetTotal := totalCurrent + totalWarehouse
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

		// 检查最大允许数量约束（应用30%容量限制）
		finalAmount := product.CurrentStock + amounts[idx]
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
			ReplenishAmount: amounts[i],
			FinalStock:      finalStock,
			ActualRatio:     actualRatio,
			ExpectedRatio:   product.ExpectedRatio,
		}
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
	fmt.Printf("%-10s %-10s %-10s %-10s %-12s %-12s %-10s\n",
		"商品ID", "当前库存", "补货量", "补货后", "实际比例", "预期比例", "比例偏差")
	fmt.Println(strings.Repeat("-", 80))

	totalReplenish := 0
	totalFinal := 0

	for _, result := range ra.results {
		deviation := math.Abs(result.ActualRatio - result.ExpectedRatio)
		fmt.Printf("%-10s %-10d %-10d %-10d %-12.3f %-12.3f %-10.4f\n",
			result.ProductID,
			result.CurrentStock,
			result.ReplenishAmount,
			result.FinalStock,
			result.ActualRatio,
			result.ExpectedRatio,
			deviation)

		totalReplenish += result.ReplenishAmount
		totalFinal += result.FinalStock
	}

	fmt.Println(strings.Repeat("-", 80))
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
