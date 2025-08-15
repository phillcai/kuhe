package main

import (
	"fmt"
	"math"
	"strings"
)

func main() {
	fmt.Println("=== 基于第一条补货案例的算法测试 ===\n")

	// 创建第一条案例的商品数据
	products := createCaseOneProducts()

	// 创建算法配置
	config := ReplenishmentConfig{
		TargetTotal:    108, // M = 108
		MaxCapacity:    108, // K = 108
		MaxIterations:  200, // 最大迭代次数
		ToleranceRatio: 0.1, // 比例偏差容忍度
	}

	fmt.Printf("=== 输入数据概览 ===\n")
	printInputSummary(products, config)

	// 执行补货算法
	fmt.Printf("\n=== 执行补货算法 ===\n")
	algorithm := NewReplenishmentAlgorithm(products, config)
	results, err := algorithm.Execute()

	if err != nil {
		fmt.Printf("❌ 算法执行失败: %v\n", err)
		return
	}

	// 打印算法结果
	fmt.Printf("\n=== 算法执行结果 ===\n")
	algorithm.PrintResults()

	// 详细分析结果
	fmt.Printf("\n=== 结果分析 ===\n")
	analyzeResults(results, config.TargetTotal)

	// 与原始期望结果对比
	fmt.Printf("\n=== 与原始期望结果对比 ===\n")
	compareWithOriginalResults(results)

	// 约束验证
	fmt.Printf("\n=== 约束验证 ===\n")
	validateConstraints(results, products, config)
}

// 创建第一条案例的商品数据
func createCaseOneProducts() []Product {
	return []Product{
		{
			ID:             "75",
			Name:           "商品_75",
			WarehouseStock: 18,       // N_i
			CurrentStock:   0,        // G_i
			MaxAllowed:     9,        // X_i = 201 * 0.046407 ≈ 9
			ExpectedRatio:  0.046407, // r_i
		},
		{
			ID:             "82",
			Name:           "商品_82",
			WarehouseStock: 18,
			CurrentStock:   0,
			MaxAllowed:     6, // X_i = 201 * 0.030954 ≈ 6
			ExpectedRatio:  0.030954,
		},
		{
			ID:             "95",
			Name:           "商品_95",
			WarehouseStock: 18,
			CurrentStock:   0,
			MaxAllowed:     12, // X_i = 201 * 0.061004 ≈ 12
			ExpectedRatio:  0.061004,
		},
		{
			ID:             "98",
			Name:           "商品_98",
			WarehouseStock: 9,
			CurrentStock:   0,
			MaxAllowed:     11, // X_i = 201 * 0.056127 ≈ 11
			ExpectedRatio:  0.056127,
		},
		{
			ID:             "100",
			Name:           "商品_100",
			WarehouseStock: 9,
			CurrentStock:   0,
			MaxAllowed:     13, // X_i = 201 * 0.069567 ≈ 13
			ExpectedRatio:  0.069567,
		},
		{
			ID:             "101",
			Name:           "商品_101",
			WarehouseStock: 18,
			CurrentStock:   0,
			MaxAllowed:     7, // X_i = 201 * 0.038577 ≈ 7
			ExpectedRatio:  0.038577,
		},
		{
			ID:             "102",
			Name:           "商品_102",
			WarehouseStock: 27,
			CurrentStock:   0,
			MaxAllowed:     18, // X_i = 201 * 0.091102 ≈ 18
			ExpectedRatio:  0.091102,
		},
		{
			ID:             "104",
			Name:           "商品_104",
			WarehouseStock: 18,
			CurrentStock:   1,
			MaxAllowed:     18, // X_i = 201 * 0.093987 ≈ 18
			ExpectedRatio:  0.093987,
		},
		{
			ID:             "188",
			Name:           "商品_188",
			WarehouseStock: 36,
			CurrentStock:   4,
			MaxAllowed:     15, // X_i = 201 * 0.077766 ≈ 15
			ExpectedRatio:  0.077766,
		},
		{
			ID:             "189",
			Name:           "商品_189",
			WarehouseStock: 18,
			CurrentStock:   2,
			MaxAllowed:     6, // X_i = 201 * 0.034135 ≈ 6
			ExpectedRatio:  0.034135,
		},
		{
			ID:             "219",
			Name:           "商品_219",
			WarehouseStock: 27,
			CurrentStock:   1,
			MaxAllowed:     18, // X_i = 201 * 0.091178 ≈ 18
			ExpectedRatio:  0.091178,
		},
		{
			ID:             "258",
			Name:           "商品_258",
			WarehouseStock: 27,
			CurrentStock:   5,
			MaxAllowed:     12, // X_i = 201 * 0.063390 ≈ 12
			ExpectedRatio:  0.063390,
		},
		{
			ID:             "268",
			Name:           "商品_268",
			WarehouseStock: 18,
			CurrentStock:   1,
			MaxAllowed:     3, // X_i = 201 * 0.017607 ≈ 3
			ExpectedRatio:  0.017607,
		},
		{
			ID:             "269",
			Name:           "商品_269",
			WarehouseStock: 18,
			CurrentStock:   0,
			MaxAllowed:     4, // X_i = 201 * 0.024855 ≈ 4
			ExpectedRatio:  0.024855,
		},
		{
			ID:             "292",
			Name:           "商品_292",
			WarehouseStock: 18,
			CurrentStock:   0,
			MaxAllowed:     14, // X_i = 201 * 0.074434 ≈ 14
			ExpectedRatio:  0.074434,
		},
		{
			ID:             "308",
			Name:           "商品_308",
			WarehouseStock: 0, // 注意：仓库库存为0
			CurrentStock:   0,
			MaxAllowed:     12, // X_i = 201 * 0.060480 ≈ 12
			ExpectedRatio:  0.060480,
		},
		{
			ID:             "323",
			Name:           "商品_323",
			WarehouseStock: 18,
			CurrentStock:   2,
			MaxAllowed:     13, // X_i = 201 * 0.068429 ≈ 13
			ExpectedRatio:  0.068429,
		},
	}
}

// 打印输入数据概览
func printInputSummary(products []Product, config ReplenishmentConfig) {
	totalWarehouse := 0
	totalCurrent := 0
	totalExpectedRatio := 0.0
	zeroStockCount := 0

	for _, product := range products {
		totalWarehouse += product.WarehouseStock
		totalCurrent += product.CurrentStock
		totalExpectedRatio += product.ExpectedRatio
		if product.WarehouseStock == 0 {
			zeroStockCount++
		}
	}

	fmt.Printf("商品总数: %d\n", len(products))
	fmt.Printf("目标总量 M: %d\n", config.TargetTotal)
	fmt.Printf("当前总库存 G: %d\n", totalCurrent)
	fmt.Printf("仓库总库存 N: %d\n", totalWarehouse)
	fmt.Printf("目标补货量 P: %d\n", config.TargetTotal-totalCurrent)
	fmt.Printf("预期比例总和: %.6f\n", totalExpectedRatio)
	fmt.Printf("零库存商品数: %d\n", zeroStockCount)

	if zeroStockCount > 0 {
		fmt.Printf("⚠️  注意：有 %d 个商品仓库库存为0，无法补货\n", zeroStockCount)
	}
}

// 分析结果
func analyzeResults(results []ReplenishmentResult, targetTotal int) {
	totalReplenish := 0
	totalFinal := 0
	maxDeviation := 0.0
	totalDeviation := 0.0
	zeroReplenishCount := 0

	fmt.Printf("%-8s %-10s %-10s %-10s %-12s %-12s %-10s\n",
		"商品ID", "补货量", "补货后", "实际比例", "预期比例", "比例偏差", "偏差率")
	fmt.Println(strings.Repeat("-", 75))

	for _, result := range results {
		deviation := math.Abs(result.ActualRatio - result.ExpectedRatio)
		deviationRate := deviation / result.ExpectedRatio * 100

		fmt.Printf("%-8s %-10d %-10d %-12.6f %-12.6f %-10.6f %-10.1f%%\n",
			result.ProductID,
			result.ReplenishAmount,
			result.FinalStock,
			result.ActualRatio,
			result.ExpectedRatio,
			deviation,
			deviationRate)

		totalReplenish += result.ReplenishAmount
		totalFinal += result.FinalStock
		totalDeviation += deviation
		if deviation > maxDeviation {
			maxDeviation = deviation
		}
		if result.ReplenishAmount == 0 {
			zeroReplenishCount++
		}
	}

	fmt.Println(strings.Repeat("-", 75))
	avgDeviation := totalDeviation / float64(len(results))

	fmt.Printf("统计指标:\n")
	fmt.Printf("  总补货量: %d\n", totalReplenish)
	fmt.Printf("  最终总量: %d (目标: %d)\n", totalFinal, targetTotal)
	fmt.Printf("  最大比例偏差: %.6f\n", maxDeviation)
	fmt.Printf("  平均比例偏差: %.6f\n", avgDeviation)
	fmt.Printf("  零补货商品数: %d\n", zeroReplenishCount)

	// 评估算法表现
	if totalFinal == targetTotal {
		fmt.Printf("✅ 成功达到目标总量\n")
	} else {
		fmt.Printf("⚠️  未达到目标总量，差异: %d\n", targetTotal-totalFinal)
	}

	if avgDeviation < 0.01 {
		fmt.Printf("✅ 比例精度优秀 (平均偏差 < 1%%)\n")
	} else if avgDeviation < 0.02 {
		fmt.Printf("✅ 比例精度良好 (平均偏差 < 2%%)\n")
	} else {
		fmt.Printf("⚠️  比例精度一般 (平均偏差 %.1f%%)\n", avgDeviation*100)
	}
}

// 与原始期望结果对比
func compareWithOriginalResults(results []ReplenishmentResult) {
	// 原始系统的期望补货结果（从commodity_restock_detail字段提取）
	originalResults := map[string]int{
		"104": 10, // restock_amount
		"188": 0,  // restock_amount
		"189": 0,  // restock_amount
		"219": 8,  // restock_amount
		"258": 0,  // restock_amount
		"268": 1,  // restock_amount
		"323": 1,  // restock_amount
	}

	fmt.Printf("%-8s %-12s %-12s %-10s %-15s\n",
		"商品ID", "我们的结果", "原始期望", "差异", "匹配状态")
	fmt.Println(strings.Repeat("-", 60))

	totalOurResult := 0
	totalOriginal := 0
	matchCount := 0

	for _, result := range results {
		ourAmount := result.ReplenishAmount
		originalAmount, hasOriginal := originalResults[result.ProductID]

		if !hasOriginal {
			originalAmount = -1 // 表示原始数据中没有此商品
		}

		difference := ourAmount - originalAmount
		matchStatus := "新商品"
		if hasOriginal {
			if difference == 0 {
				matchStatus = "✅ 完全匹配"
				matchCount++
			} else {
				matchStatus = fmt.Sprintf("❌ 差异%+d", difference)
			}
			totalOriginal += originalAmount
		}

		totalOurResult += ourAmount

		originalStr := "-"
		if hasOriginal {
			originalStr = fmt.Sprintf("%d", originalAmount)
		}

		fmt.Printf("%-8s %-12d %-12s %-10d %-15s\n",
			result.ProductID,
			ourAmount,
			originalStr,
			difference,
			matchStatus)
	}

	fmt.Println(strings.Repeat("-", 60))
	fmt.Printf("总计对比:\n")
	fmt.Printf("  我们的总补货量: %d\n", totalOurResult)
	fmt.Printf("  原始期望总量: %d\n", totalOriginal)
	fmt.Printf("  完全匹配商品数: %d / %d\n", matchCount, len(originalResults))

	matchRate := float64(matchCount) / float64(len(originalResults)) * 100
	fmt.Printf("  匹配率: %.1f%%\n", matchRate)
}

// 约束验证
func validateConstraints(results []ReplenishmentResult, products []Product, config ReplenishmentConfig) {
	productMap := make(map[string]Product)
	for _, p := range products {
		productMap[p.ID] = p
	}

	violations := 0
	totalFinal := 0

	fmt.Printf("约束检查:\n")

	for _, result := range results {
		product := productMap[result.ProductID]
		totalFinal += result.FinalStock

		// 检查仓库库存约束
		if result.ReplenishAmount > product.WarehouseStock {
			fmt.Printf("❌ 商品%s: 补货量(%d) > 仓库库存(%d)\n",
				result.ProductID, result.ReplenishAmount, product.WarehouseStock)
			violations++
		}

		// 检查最大允许数量约束
		maxAllowed := maxInt(product.MaxAllowed, product.CurrentStock)
		if result.FinalStock > maxAllowed {
			fmt.Printf("❌ 商品%s: 补货后数量(%d) > 最大允许(%d)\n",
				result.ProductID, result.FinalStock, maxAllowed)
			violations++
		}

		// 检查负补货约束
		if result.ReplenishAmount < 0 {
			fmt.Printf("❌ 商品%s: 补货量为负(%d)\n",
				result.ProductID, result.ReplenishAmount)
			violations++
		}
	}

	// 检查总量约束
	if totalFinal != config.TargetTotal {
		fmt.Printf("⚠️  总量约束: 实际总量(%d) != 目标总量(%d)\n",
			totalFinal, config.TargetTotal)
	}

	if violations == 0 {
		fmt.Printf("✅ 所有强约束均满足\n")
	} else {
		fmt.Printf("❌ 发现 %d 个约束违反\n", violations)
	}

	fmt.Printf("总量验证: %d (目标: %d)\n", totalFinal, config.TargetTotal)
}
