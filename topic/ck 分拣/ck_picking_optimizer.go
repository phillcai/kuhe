package main

import (
	"fmt"
	"math"
	"sort"
)

// 常量定义
const (
	// ItemsPerLayer 每层货架最大容量
	ItemsPerLayer = 9
	// FloatEpsilon 浮点数比较误差
	FloatEpsilon = 0.0001
)

// SKUInfo SKU信息结构
type SKUInfo struct {
	ID          int     // SKU标识
	Stock       int     // 仓库库存 N_i
	Ratio       float64 // 仓库比例 r_i
	MaxQuantity int     // 单SKU上限 x_i^{max}
}

// PickingResult 分拣结果
type PickingResult struct {
	SKUID       int     // SKU标识
	Quantity    int     // 分拣数量 x_i
	ShelfLayers int     // 占用层数 L_i
	ActualRatio float64 // 实际比例
}

// OptimizationMetrics 优化指标
type OptimizationMetrics struct {
	TotalQuantity       int     // 实际分拣总量 X
	TargetAchievement   float64 // 目标达成率
	ProportionDeviation float64 // 比例偏差
	ShelfUtilization    float64 // 货架利用率
	EmptyLayers         int     // 空余层数
}

// CKPickingOptimizer CK分拣优化器
type CKPickingOptimizer struct {
	// 输入参数
	TargetTotal     int       // 目标分拣总量 M
	ShelfLayers     int       // 车辆货架层数 n
	MaxCapacity     int       // 车辆最大容量 C_max = 9n
	MaxSKURatio     float64   // 单SKU上限比例 p = 0.2
	MaxTop3SKURatio float64   // Top3 SKU上限比例，默认0.45
	SKUs            []SKUInfo // SKU列表

	// 中间变量
	TotalStock int       // 仓库总库存 N
	SKURatios  []float64 // 仓库SKU比例列表

	// 输出结果
	Results []PickingResult     // 分拣结果
	Metrics OptimizationMetrics // 优化指标

	// 调试模式
	isDebug bool // 是否启用调试模式
}

// NewCKPickingOptimizer 创建新的CK分拣优化器
func NewCKPickingOptimizer(targetTotal int, shelfLayers int, skus []SKUInfo) *CKPickingOptimizer {
	maxCapacity := ItemsPerLayer * shelfLayers
	maxSKURatio := 0.2
	maxTop3SKURatio := 0.5 // 默认45%

	optimizer := &CKPickingOptimizer{
		TargetTotal:     targetTotal,
		ShelfLayers:     shelfLayers,
		MaxCapacity:     maxCapacity,
		MaxSKURatio:     maxSKURatio,
		MaxTop3SKURatio: maxTop3SKURatio,
		SKUs:            skus,
		Results:         make([]PickingResult, 0, len(skus)),
		isDebug:         false, // 默认关闭调试模式
	}

	return optimizer
}

// SetDebugMode 设置算法实例调试模式
func (o *CKPickingOptimizer) SetDebugMode(debug bool) {
	o.isDebug = debug
}

// GetDebugMode 获取算法实例调试模式
func (o *CKPickingOptimizer) GetDebugMode() bool {
	return o.isDebug
}

// debugPrint 算法实例调试打印函数
func (o *CKPickingOptimizer) debugPrint(format string, args ...interface{}) {
	if o.isDebug {
		fmt.Printf(format, args...)
	}
}

// Optimize 执行优化算法
func (o *CKPickingOptimizer) Optimize() error {
	// 步骤1：参数初始化与约束检查
	if err := o.step1Initialize(); err != nil {
		return fmt.Errorf("步骤1初始化失败: %v", err)
	}

	// 步骤2：初始分拣量计算
	quantities := o.step2CalculateInitialQuantities()

	// 步骤3：货架层数分配
	layers := o.step3AllocateShelfLayers(quantities)

	// 步骤4：目标总量调整
	quantities = o.step4AdjustTargetTotal(quantities, layers)
	// 步骤4后：再次检查实际比例约束
	o.adjustForActualRatioConstraint(quantities)
	// 步骤4后：检查top3 SKU约束
	o.adjustForTop3SKUConstraint(quantities)

	// 步骤5：货架利用率优化
	quantities, layers = o.step5OptimizeUtilization(quantities, layers)
	// 步骤5后：再次检查实际比例约束
	o.adjustForActualRatioConstraint(quantities)
	// 步骤5后：检查top3 SKU约束
	o.adjustForTop3SKUConstraint(quantities)

	// 步骤6：最终验证与输出
	o.step6Finalize(quantities, layers)

	return nil
}

// step1Initialize 步骤1：参数初始化与约束检查
func (o *CKPickingOptimizer) step1Initialize() error {
	// 计算仓库总库存
	o.TotalStock = 0
	for i := range o.SKUs {
		o.TotalStock += o.SKUs[i].Stock
	}

	// 检查可行性
	if o.TotalStock < o.TargetTotal {
		o.TargetTotal = o.TotalStock
		o.debugPrint("警告: 仓库总库存不足，调整目标总量为: %d\n", o.TargetTotal)
	}

	if o.MaxCapacity < o.TargetTotal {
		o.TargetTotal = o.MaxCapacity
		o.debugPrint("警告: 车辆容量不足，调整目标总量为: %d\n", o.TargetTotal)
	}

	// 计算仓库SKU比例
	o.SKURatios = make([]float64, len(o.SKUs))
	for i := range o.SKUs {
		if o.TotalStock > 0 {
			o.SKURatios[i] = float64(o.SKUs[i].Stock) / float64(o.TotalStock)
		} else {
			o.SKURatios[i] = 0
		}
		o.SKUs[i].Ratio = o.SKURatios[i]
	}

	// 计算单SKU上限
	for i := range o.SKUs {
		maxByRatio := int(float64(o.TargetTotal) * o.MaxSKURatio)
		o.SKUs[i].MaxQuantity = min(o.SKUs[i].Stock, maxByRatio, o.MaxCapacity)
	}

	// 检查全SKU包含可行性
	for i := range o.SKUs {
		if o.SKUs[i].Stock < 1 {
			return fmt.Errorf("SKU %d 库存为0，无法满足全SKU包含约束", o.SKUs[i].ID)
		}
	}

	minTotal := len(o.SKUs) // 至少需要分拣 I 个
	if o.TargetTotal < minTotal {
		o.TargetTotal = minTotal
		o.debugPrint("警告: 目标总量小于SKU种类数，调整目标总量为: %d\n", o.TargetTotal)
	}

	return nil
}

// step2CalculateInitialQuantities 步骤2：初始分拣量计算（基于比例）
func (o *CKPickingOptimizer) step2CalculateInitialQuantities() []int {
	quantities := make([]int, len(o.SKUs))

	// 1. 计算理想分拣量
	for i := range o.SKUs {
		ideal := float64(o.TargetTotal) * o.SKURatios[i]
		quantities[i] = int(math.Round(ideal))
	}

	// 2. 应用单SKU上限约束
	for i := range o.SKUs {
		quantities[i] = min2(quantities[i], o.SKUs[i].MaxQuantity)
	}

	// 3. 应用仓库库存约束
	for i := range o.SKUs {
		quantities[i] = min2(quantities[i], o.SKUs[i].Stock)
	}

	// 4. 应用全SKU包含约束
	for i := range o.SKUs {
		quantities[i] = max(quantities[i], 1)
	}

	// 5. 应用实际比例约束：确保每个SKU的实际比例不超过20%
	// 由于实际分拣总量可能小于目标总量，需要调整以确保实际比例不超过20%
	o.adjustForActualRatioConstraint(quantities)

	// 6. 应用top3 SKU约束：确保top3 SKU的总和不超过45%
	o.adjustForTop3SKUConstraint(quantities)

	return quantities
}

// adjustForActualRatioConstraint 调整分拣量以确保实际比例不超过20%
func (o *CKPickingOptimizer) adjustForActualRatioConstraint(quantities []int) {
	maxIterations := 20 // 最大迭代次数，避免无限循环
	for iter := 0; iter < maxIterations; iter++ {
		currentTotal := sum(quantities)
		if currentTotal == 0 {
			return
		}

		// 找出所有超过20%的SKU
		overLimitIndices := make([]int, 0)
		overLimitSum := 0
		for i := range quantities {
			actualRatio := float64(quantities[i]) / float64(currentTotal)
			if actualRatio > o.MaxSKURatio+FloatEpsilon { // 允许小的浮点误差
				overLimitIndices = append(overLimitIndices, i)
				overLimitSum += quantities[i]
			}
		}

		// 如果没有超过限制的SKU，说明已经满足约束
		if len(overLimitIndices) == 0 {
			break
		}

		// 计算调整后的总量
		// 设调整后总量为 X_new，超过限制的k个SKU都调整为 0.2*X_new
		// 其他SKU保持不变，总量为 currentTotal - overLimitSum
		// 所以：X_new = k * 0.2 * X_new + (currentTotal - overLimitSum)
		// 即：X_new = (currentTotal - overLimitSum) / (1 - 0.2*k)
		k := float64(len(overLimitIndices))
		otherTotal := currentTotal - overLimitSum
		newTotal := int(float64(otherTotal) / (1.0 - o.MaxSKURatio*k))

		// 如果计算出的新总量不合理，使用迭代方法
		if newTotal <= 0 || newTotal > currentTotal {
			// 回退到简单的迭代方法
			for _, i := range overLimitIndices {
				maxAllowedByRatio := int(float64(currentTotal) * o.MaxSKURatio)
				maxAllowedByRatio = max(maxAllowedByRatio, 1)
				if quantities[i] > maxAllowedByRatio {
					quantities[i] = maxAllowedByRatio
				}
			}
			continue
		}

		// 计算每个超过限制的SKU应该调整到的数量
		maxAllowedByNewTotal := int(float64(newTotal) * o.MaxSKURatio)
		maxAllowedByNewTotal = max(maxAllowedByNewTotal, 1)

		// 统一调整所有超过限制的SKU
		for _, i := range overLimitIndices {
			quantities[i] = maxAllowedByNewTotal
		}
	}
}

// getTop3SKUIndicesAndSum 获取top3 SKU的索引和总和
func (o *CKPickingOptimizer) getTop3SKUIndicesAndSum(quantities []int) ([]int, int) {
	type skuQuantity struct {
		index    int
		quantity int
	}

	skuQuantities := make([]skuQuantity, len(quantities))
	for i := range quantities {
		skuQuantities[i] = skuQuantity{
			index:    i,
			quantity: quantities[i],
		}
	}

	// 按分拣数量降序排序
	sort.Slice(skuQuantities, func(i, j int) bool {
		return skuQuantities[i].quantity > skuQuantities[j].quantity
	})

	// 计算top3 SKU的总和和索引
	top3Sum := 0
	top3Indices := make([]int, 0, 3)
	for i := 0; i < 3 && i < len(skuQuantities); i++ {
		top3Sum += skuQuantities[i].quantity
		top3Indices = append(top3Indices, skuQuantities[i].index)
	}

	return top3Indices, top3Sum
}

// adjustForTop3SKUConstraint 调整分拣量以确保top3 SKU的总和不超过45%
func (o *CKPickingOptimizer) adjustForTop3SKUConstraint(quantities []int) {
	maxIterations := 20 // 最大迭代次数，避免无限循环
	for iter := 0; iter < maxIterations; iter++ {
		currentTotal := sum(quantities)
		if currentTotal == 0 {
			return
		}

		// 获取top3 SKU的索引和总和
		top3Indices, top3Sum := o.getTop3SKUIndicesAndSum(quantities)

		// 检查是否超过45%
		top3Ratio := float64(top3Sum) / float64(currentTotal)
		maxTop3Ratio := o.MaxTop3SKURatio

		if top3Ratio <= maxTop3Ratio+FloatEpsilon { // 允许小的浮点误差
			// 已经满足约束
			break
		}

		// 超过45%，需要减少top3 SKU的分拣量
		// 计算最大允许的top3总和：top3Sum_max = 0.45 * X
		// 需要减少的量：reduction = top3Sum - 0.45 * X
		maxAllowedTop3Sum := int(float64(currentTotal) * maxTop3Ratio)
		reduction := top3Sum - maxAllowedTop3Sum

		// 计算每个top3 SKU需要减少的数量（平均分配）
		// 但确保每个SKU至少为1（全SKU包含约束）
		reductionPerSKU := reduction / len(top3Indices)
		remainder := reduction % len(top3Indices)

		adjusted := false
		for i, idx := range top3Indices {
			// 计算该SKU需要减少的数量
			skuReduction := reductionPerSKU
			if i < remainder {
				skuReduction++ // 余数分配给前几个SKU
			}

			// 确保不会减少到小于1
			actualReduction := min2(skuReduction, quantities[idx]-1)
			if actualReduction > 0 {
				quantities[idx] -= actualReduction
				adjusted = true
			}
		}

		// 如果还有剩余需要减少的量（因为某些SKU已达到最小值），继续迭代
		if !adjusted {
			// 无法继续调整（所有top3 SKU都已达到最小值1）
			o.debugPrint("警告: Top3 SKU约束无法完全满足，所有top3 SKU都已达到最小值1\n")
			break
		}
	}
}

// wouldSatisfyTop3Constraint 检查如果增加指定数量的分拣量，是否仍满足top3 SKU约束
func (o *CKPickingOptimizer) wouldSatisfyTop3Constraint(quantities []int, index int, delta int) bool {
	// 创建临时数组模拟增加后的状态
	tempQuantities := make([]int, len(quantities))
	copy(tempQuantities, quantities)
	tempQuantities[index] += delta

	tempTotal := sum(tempQuantities)
	if tempTotal == 0 {
		return true
	}

	// 获取top3 SKU的总和
	_, top3Sum := o.getTop3SKUIndicesAndSum(tempQuantities)

	// 检查是否超过限制
	top3Ratio := float64(top3Sum) / float64(tempTotal)
	return top3Ratio <= o.MaxTop3SKURatio+FloatEpsilon // 允许小的浮点误差
}

// step3AllocateShelfLayers 步骤3：货架层数分配
func (o *CKPickingOptimizer) step3AllocateShelfLayers(quantities []int) []int {
	layers := make([]int, len(quantities))

	// 计算所需层数
	for i := range quantities {
		layers[i] = int(math.Ceil(float64(quantities[i]) / float64(ItemsPerLayer)))
	}

	// 检查总层数约束
	totalLayers := 0
	for i := range layers {
		totalLayers += layers[i]
	}

	// 如果总层数超过限制，需要调整
	if totalLayers > o.ShelfLayers {
		// 计算层数缺口
		deltaLayers := totalLayers - o.ShelfLayers

		// 按比例减少各SKU的层数
		// 优先减少比例偏差小的SKU的层数
		type layerAdjust struct {
			index int
			score float64
		}

		adjusts := make([]layerAdjust, len(layers))
		for i := range layers {
			// 计算比例偏差作为调整优先级
			actualRatio := float64(quantities[i]) / float64(sum(quantities))
			expectedRatio := o.SKURatios[i]
			adjusts[i] = layerAdjust{
				index: i,
				score: math.Abs(actualRatio - expectedRatio),
			}
		}

		// 按偏差从小到大排序（偏差小的优先减少）
		sort.Slice(adjusts, func(i, j int) bool {
			return adjusts[i].score < adjusts[j].score
		})

		// 逐个减少层数
		for deltaLayers > 0 {
			adjusted := false
			for _, adj := range adjusts {
				if layers[adj.index] > 1 && deltaLayers > 0 {
					layers[adj.index]--
					deltaLayers--
					adjusted = true

					// 重新计算分拣量
					quantities[adj.index] = min2(quantities[adj.index], ItemsPerLayer*layers[adj.index])
					// 确保全SKU包含约束
					quantities[adj.index] = max(quantities[adj.index], 1)
				}
			}
			if !adjusted {
				break
			}
		}
	}

	return layers
}

// step4AdjustTargetTotal 步骤4：目标总量调整
func (o *CKPickingOptimizer) step4AdjustTargetTotal(quantities []int, layers []int) []int {
	currentTotal := sum(quantities)

	if currentTotal < o.TargetTotal {
		// 情况1：存在缺口
		gap := o.TargetTotal - currentTotal
		quantities = o.increaseQuantities(quantities, layers, gap)
	} else if currentTotal > o.TargetTotal {
		// 情况2：存在超额
		excess := currentTotal - o.TargetTotal
		quantities = o.decreaseQuantities(quantities, excess)
	}
	// 情况3：正好满足，无需调整

	return quantities
}

// increaseQuantities 增加分拣量以填补缺口
func (o *CKPickingOptimizer) increaseQuantities(quantities []int, layers []int, gap int) []int {
	for gap > 0 {
		bestIndex := -1
		bestScore := math.Inf(-1)
		currentTotal := sum(quantities)

		// 寻找可增加的SKU
		for i := range quantities {
			// 检查是否可以增加
			if quantities[i] < o.SKUs[i].MaxQuantity {
				// 检查层数限制
				maxByLayer := ItemsPerLayer * layers[i]
				if quantities[i] < maxByLayer {
					// 检查实际比例约束：增加后该SKU的实际比例不能超过20%
					newQuantity := quantities[i] + 1
					newTotal := currentTotal + 1
					actualRatio := float64(newQuantity) / float64(newTotal)
					if actualRatio > o.MaxSKURatio {
						// 实际比例超过20%，跳过
						continue
					}

					// 检查top3 SKU约束：增加后top3总和不能超过45%
					if !o.wouldSatisfyTop3Constraint(quantities, i, 1) {
						// 违反top3约束，跳过
						continue
					}

					// 计算改善得分
					score := o.calculateImprovementScore(quantities, i, 1)
					if score > bestScore {
						bestScore = score
						bestIndex = i
					}
				}
			}
		}

		if bestIndex == -1 {
			// 无法继续增加
			break
		}

		// 增加1个单位
		quantities[bestIndex]++
		gap--
	}

	return quantities
}

// decreaseQuantities 减少分拣量以消除超额
func (o *CKPickingOptimizer) decreaseQuantities(quantities []int, excess int) []int {
	for excess > 0 {
		bestIndex := -1
		bestScore := math.Inf(-1)

		// 寻找可减少的SKU（必须大于1，满足全SKU包含约束）
		for i := range quantities {
			if quantities[i] > 1 {
				// 计算改善得分
				score := o.calculateImprovementScore(quantities, i, -1)
				if score > bestScore {
					bestScore = score
					bestIndex = i
				}
			}
		}

		if bestIndex == -1 {
			// 无法继续减少（所有SKU都已达到最小值1）
			break
		}

		// 减少1个单位
		quantities[bestIndex]--
		excess--
	}

	return quantities
}

// calculateImprovementScore 计算调整后的改善得分
func (o *CKPickingOptimizer) calculateImprovementScore(quantities []int, index int, delta int) float64 {
	// 计算当前比例偏差
	currentDeviation := o.calculateProportionDeviation(quantities)

	// 模拟调整
	newQuantities := make([]int, len(quantities))
	copy(newQuantities, quantities)
	newQuantities[index] += delta

	// 确保约束
	if newQuantities[index] < 1 {
		return math.Inf(-1) // 违反全SKU包含约束
	}
	if newQuantities[index] > o.SKUs[index].MaxQuantity {
		return math.Inf(-1) // 违反上限约束
	}

	// 计算调整后比例偏差
	newDeviation := o.calculateProportionDeviation(newQuantities)

	// 改善得分 = 当前偏差 - 调整后偏差
	return currentDeviation - newDeviation
}

// calculateProportionDeviation 计算比例偏差
func (o *CKPickingOptimizer) calculateProportionDeviation(quantities []int) float64 {
	total := sum(quantities)
	if total == 0 {
		return math.Inf(1)
	}

	deviation := 0.0
	for i := range quantities {
		actualRatio := float64(quantities[i]) / float64(total)
		expectedRatio := o.SKURatios[i]
		deviation += math.Abs(actualRatio-expectedRatio) * expectedRatio
	}

	return deviation
}

// step5OptimizeUtilization 步骤5：货架利用率优化
func (o *CKPickingOptimizer) step5OptimizeUtilization(quantities []int, layers []int) ([]int, []int) {
	// 计算空余层数
	totalLayers := sum(layers)
	emptyLayers := o.ShelfLayers - totalLayers

	if emptyLayers <= 0 {
		return quantities, layers
	}

	// 寻找可扩展的SKU
	type expandCandidate struct {
		index      int
		priority   float64
		expandable int
	}

	candidates := make([]expandCandidate, 0)
	for i := range quantities {
		if quantities[i] < o.SKUs[i].MaxQuantity {
			maxByLayer := 9 * layers[i]
			if quantities[i] < maxByLayer {
				// 可以扩展
				actualRatio := float64(quantities[i]) / float64(sum(quantities))
				expectedRatio := o.SKURatios[i]
				priority := expectedRatio - actualRatio // 实际比例低于预期比例的优先

				expandable := min(
					o.SKUs[i].MaxQuantity-quantities[i],
					ItemsPerLayer*emptyLayers,
					maxByLayer-quantities[i],
				)

				if expandable > 0 {
					candidates = append(candidates, expandCandidate{
						index:      i,
						priority:   priority,
						expandable: expandable,
					})
				}
			}
		}
	}

	// 按优先级排序
	sort.Slice(candidates, func(i, j int) bool {
		return candidates[i].priority > candidates[j].priority
	})

	// 逐个分配空余层数
	for emptyLayers > 0 && len(candidates) > 0 {
		best := candidates[0]
		candidates = candidates[1:]

		currentTotal := sum(quantities)

		// 分配1层
		layers[best.index]++
		emptyLayers--

		// 计算可以增加的最大数量，确保实际比例不超过20%
		// 如果增加 increase 个单位，需要满足：(x_i + increase) / (X + increase) <= 0.2
		// 即：x_i + increase <= 0.2*(X + increase)
		// 即：increase <= (0.2*X - x_i) / 0.8
		maxIncreaseByRatio := 0
		if currentTotal > 0 {
			maxAllowedByRatio := float64(currentTotal)*o.MaxSKURatio - float64(quantities[best.index])
			if maxAllowedByRatio > 0 {
				maxIncreaseByRatio = int(maxAllowedByRatio / (1.0 - o.MaxSKURatio))
			}
		}

		// 增加分拣量（最多9个，但不超过实际比例约束）
		increase := min2(ItemsPerLayer, best.expandable)
		if maxIncreaseByRatio >= 0 {
			increase = min2(increase, maxIncreaseByRatio) // 确保不超过实际比例约束
		}

		// 检查top3 SKU约束：逐步增加，确保不超过45%
		for increase > 0 {
			if o.wouldSatisfyTop3Constraint(quantities, best.index, 1) {
				quantities[best.index]++
				increase--
			} else {
				// 如果增加1个就违反top3约束，停止增加
				break
			}
		}

		// 更新候选列表
		if quantities[best.index] < o.SKUs[best.index].MaxQuantity {
			maxByLayer := 9 * layers[best.index]
			if quantities[best.index] < maxByLayer {
				actualRatio := float64(quantities[best.index]) / float64(sum(quantities))
				expectedRatio := o.SKURatios[best.index]
				priority := expectedRatio - actualRatio

				expandable := min(
					o.SKUs[best.index].MaxQuantity-quantities[best.index],
					ItemsPerLayer*emptyLayers,
					maxByLayer-quantities[best.index],
				)

				if expandable > 0 {
					candidates = append(candidates, expandCandidate{
						index:      best.index,
						priority:   priority,
						expandable: expandable,
					})
					// 重新排序
					sort.Slice(candidates, func(i, j int) bool {
						return candidates[i].priority > candidates[j].priority
					})
				}
			}
		}
	}

	return quantities, layers
}

// step6Finalize 步骤6：最终验证与输出
func (o *CKPickingOptimizer) step6Finalize(quantities []int, layers []int) {
	// 验证所有强约束
	o.validateConstraints(quantities, layers)

	// 构建结果
	o.Results = make([]PickingResult, 0, len(quantities))
	totalQuantity := sum(quantities)

	for i := range quantities {
		actualRatio := 0.0
		if totalQuantity > 0 {
			actualRatio = float64(quantities[i]) / float64(totalQuantity)
		}

		o.Results = append(o.Results, PickingResult{
			SKUID:       o.SKUs[i].ID,
			Quantity:    quantities[i],
			ShelfLayers: layers[i],
			ActualRatio: actualRatio,
		})
	}

	// 计算优化指标
	o.calculateMetrics(totalQuantity, layers)
}

// validateConstraints 验证所有强约束
func (o *CKPickingOptimizer) validateConstraints(quantities []int, layers []int) {
	totalQuantity := sum(quantities)

	// 车辆容量约束
	if totalQuantity > o.MaxCapacity {
		panic(fmt.Sprintf("违反车辆容量约束: %d > %d", totalQuantity, o.MaxCapacity))
	}

	// 仓库库存约束
	for i := range quantities {
		if quantities[i] > o.SKUs[i].Stock {
			panic(fmt.Sprintf("违反仓库库存约束: SKU %d, %d > %d", o.SKUs[i].ID, quantities[i], o.SKUs[i].Stock))
		}
	}

	// 单SKU上限约束（基于目标总量）
	maxAllowedByTarget := int(float64(o.TargetTotal) * o.MaxSKURatio)
	for i := range quantities {
		if quantities[i] > maxAllowedByTarget {
			panic(fmt.Sprintf("违反单SKU上限约束（目标总量）: SKU %d, %d > %d", o.SKUs[i].ID, quantities[i], maxAllowedByTarget))
		}
	}

	// 单SKU上限约束（基于实际分拣总量，确保实际比例不超过20%）
	for i := range quantities {
		actualRatio := float64(quantities[i]) / float64(totalQuantity)
		if actualRatio > o.MaxSKURatio+0.0001 { // 允许小的浮点误差
			panic(fmt.Sprintf("违反单SKU上限约束（实际比例）: SKU %d, 实际比例 %.2f%% > %.1f%%",
				o.SKUs[i].ID, actualRatio*100, o.MaxSKURatio*100))
		}
	}

	// Top3 SKU约束：top3 SKU的总和不超过45%
	_, top3Sum := o.getTop3SKUIndicesAndSum(quantities)
	top3Ratio := float64(top3Sum) / float64(totalQuantity)
	if top3Ratio > o.MaxTop3SKURatio+FloatEpsilon { // 允许小的浮点误差
		panic(fmt.Sprintf("违反Top3 SKU约束: top3总和=%d, 实际比例 %.2f%% > %.1f%%",
			top3Sum, top3Ratio*100, o.MaxTop3SKURatio*100))
	}

	// 全SKU包含约束
	for i := range quantities {
		if quantities[i] < 1 {
			panic(fmt.Sprintf("违反全SKU包含约束: SKU %d, %d < 1", o.SKUs[i].ID, quantities[i]))
		}
	}

	// 总层数约束
	totalLayers := sum(layers)
	if totalLayers > o.ShelfLayers {
		panic(fmt.Sprintf("违反总层数约束: %d > %d", totalLayers, o.ShelfLayers))
	}

	// 每层单一SKU约束
	for i := range quantities {
		maxByLayer := 9 * layers[i]
		if quantities[i] > maxByLayer {
			panic(fmt.Sprintf("违反每层单一SKU约束: SKU %d, %d > %d", o.SKUs[i].ID, quantities[i], maxByLayer))
		}
	}
}

// calculateMetrics 计算优化指标
func (o *CKPickingOptimizer) calculateMetrics(totalQuantity int, layers []int) {
	// 目标达成率
	targetAchievement := 0.0
	if o.TargetTotal > 0 {
		targetAchievement = float64(totalQuantity) / float64(o.TargetTotal) * 100.0
	}

	// 比例偏差
	proportionDeviation := o.calculateProportionDeviationFromResults()

	// 货架利用率
	shelfUtilization := 0.0
	if o.MaxCapacity > 0 {
		shelfUtilization = float64(totalQuantity) / float64(o.MaxCapacity) * 100.0
	}

	// 空余层数
	totalLayers := sum(layers)
	emptyLayers := o.ShelfLayers - totalLayers

	o.Metrics = OptimizationMetrics{
		TotalQuantity:       totalQuantity,
		TargetAchievement:   targetAchievement,
		ProportionDeviation: proportionDeviation,
		ShelfUtilization:    shelfUtilization,
		EmptyLayers:         emptyLayers,
	}
}

// calculateProportionDeviationFromResults 从结果计算比例偏差
func (o *CKPickingOptimizer) calculateProportionDeviationFromResults() float64 {
	totalQuantity := 0
	for _, result := range o.Results {
		totalQuantity += result.Quantity
	}

	if totalQuantity == 0 {
		return math.Inf(1)
	}

	deviation := 0.0
	// 通过SKU ID匹配，而不是索引
	skuRatioMap := make(map[int]float64)
	for i := range o.SKUs {
		skuRatioMap[o.SKUs[i].ID] = o.SKURatios[i]
	}

	for _, result := range o.Results {
		actualRatio := result.ActualRatio
		expectedRatio := skuRatioMap[result.SKUID]
		deviation += math.Abs(actualRatio-expectedRatio) * expectedRatio
	}

	return deviation
}

// PrintResults 打印结果
func (o *CKPickingOptimizer) PrintResults() {
	fmt.Println("=== CK分拣优化结果 ===")
	fmt.Printf("\n输入参数:\n")
	fmt.Printf("  目标分拣总量 M: %d\n", o.TargetTotal)
	fmt.Printf("  车辆货架层数 n: %d\n", o.ShelfLayers)
	fmt.Printf("  车辆最大容量: %d\n", o.MaxCapacity)
	fmt.Printf("  单SKU上限比例: %.1f%%\n", o.MaxSKURatio*100)
	fmt.Printf("  仓库总库存: %d\n", o.TotalStock)

	fmt.Printf("\n分拣结果:\n")
	fmt.Printf("%-8s %-12s %-12s %-12s %-12s %-12s\n", "SKU ID", "分拣数量", "占用层数", "实际比例", "预期比例", "比例偏差")
	fmt.Println("--------------------------------------------------------------------------------")

	// 创建SKU比例映射
	skuRatioMap := make(map[int]float64)
	for i := range o.SKUs {
		skuRatioMap[o.SKUs[i].ID] = o.SKURatios[i]
	}

	// 按 SKU ID 升序排序打印结果
	results := make([]PickingResult, len(o.Results))
	copy(results, o.Results)
	// 排序
	sort.Slice(results, func(i, j int) bool {
		return results[i].SKUID < results[j].SKUID
	})

	for _, result := range results {
		expectedRatio := skuRatioMap[result.SKUID] * 100
		deviation := math.Abs(result.ActualRatio-skuRatioMap[result.SKUID]) * 100
		fmt.Printf("%-8d %-12d %-12d %-11.2f%% %-11.2f%% %-11.2f%%\n",
			result.SKUID, result.Quantity, result.ShelfLayers,
			result.ActualRatio*100, expectedRatio, deviation)
	}

	fmt.Printf("\n优化指标:\n")
	fmt.Printf("  实际分拣总量: %d\n", o.Metrics.TotalQuantity)
	fmt.Printf("  目标达成率: %.2f%%\n", o.Metrics.TargetAchievement)
	fmt.Printf("  比例偏差: %.4f\n", o.Metrics.ProportionDeviation)
	fmt.Printf("  货架利用率: %.2f%%\n", o.Metrics.ShelfUtilization)
	fmt.Printf("  空余层数: %d\n", o.Metrics.EmptyLayers)
	fmt.Println()
}

// 辅助函数
func min(a, b, c int) int {
	if a < b {
		if a < c {
			return a
		}
		return c
	}
	if b < c {
		return b
	}
	return c
}

func min2(a, b int) int {
	if a < b {
		return a
	}
	return b
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}

func sum(arr []int) int {
	sum := 0
	for _, v := range arr {
		sum += v
	}
	return sum
}
