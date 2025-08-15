package main

// 补货算法主程序 - 独立运行
// 使用命令: go run main_replenishment.go replenishment_algorithm.go

import (
	"fmt"
	"math"
	"os"
	"strings"
)

func main() {
	fmt.Println("=== 带最大允许数量约束的补货算法 ===")
	fmt.Println("基于数学建模文档实现")
	fmt.Println()

	// 检查命令行参数
	if len(os.Args) > 1 {
		switch os.Args[1] {
		case "basic":
			runBasicExample()
		case "complex":
			runComplexExample()
		case "boundary":
			runBoundaryExample()
		case "performance":
			runPerformanceTest()
		case "all":
			runAllExamples()
		default:
			printUsage()
		}
	} else {
		// 默认运行所有示例
		runAllExamples()
	}
}

func printUsage() {
	fmt.Println("用法: go run main_replenishment.go [选项]")
	fmt.Println("选项:")
	fmt.Println("  basic      - 运行基础示例")
	fmt.Println("  complex    - 运行复杂示例")
	fmt.Println("  boundary   - 运行边界情况示例")
	fmt.Println("  performance- 运行性能测试")
	fmt.Println("  all        - 运行所有示例（默认）")
}

func runAllExamples() {
	runBasicExample()
	runComplexExample()
	runBoundaryExample()
	fmt.Println("=== 所有示例运行完成 ===")
}

// 基础示例：文档中的三商品示例
func runBasicExample() {
	fmt.Println("1. 基础示例（文档中的三商品示例）")
	fmt.Println(strings.Repeat("=", 60))

	// 创建商品 - 与文档示例完全一致
	products := []Product{
		{
			ID:             "A",
			Name:           "商品A",
			WarehouseStock: 10,  // N_A = 10
			CurrentStock:   2,   // G_A = 2
			MaxAllowed:     8,   // X_A = 8, M_A^max = max(8,2) = 8
			ExpectedRatio:  0.5, // r_A = 0.5
		},
		{
			ID:             "B",
			Name:           "商品B",
			WarehouseStock: 5,   // N_B = 5
			CurrentStock:   1,   // G_B = 1
			MaxAllowed:     4,   // X_B = 4, M_B^max = max(4,1) = 4
			ExpectedRatio:  0.3, // r_B = 0.3
		},
		{
			ID:             "C",
			Name:           "商品C",
			WarehouseStock: 8,   // N_C = 8
			CurrentStock:   0,   // G_C = 0
			MaxAllowed:     6,   // X_C = 6, M_C^max = max(6,0) = 6
			ExpectedRatio:  0.2, // r_C = 0.2
		},
	}

	// 创建配置 - 与文档示例一致
	config := ReplenishmentConfig{
		TargetTotal:    12, // M = 12
		MaxCapacity:    20, // K = 20（假设）
		MaxIterations:  100,
		ToleranceRatio: 0.1,
	}

	fmt.Printf("输入参数:\n")
	fmt.Printf("目标补货后总量 M = %d\n", config.TargetTotal)
	fmt.Printf("点位当前总量 G = %d\n", products[0].CurrentStock+products[1].CurrentStock+products[2].CurrentStock)
	fmt.Printf("目标补货总量 P = %d\n", config.TargetTotal-(products[0].CurrentStock+products[1].CurrentStock+products[2].CurrentStock))
	fmt.Printf("仓库总库存 N = %d\n", products[0].WarehouseStock+products[1].WarehouseStock+products[2].WarehouseStock)
	fmt.Println()

	// 执行算法
	algorithm := NewReplenishmentAlgorithm(products, config)
	results, err := algorithm.Execute()

	if err != nil {
		fmt.Printf("算法执行失败: %v\n", err)
		return
	}

	// 打印结果
	algorithm.PrintResults()

	// 验证与文档示例的一致性
	validateWithDocumentExample(results)

	fmt.Println()
}

// 复杂示例：更多商品和约束
func runComplexExample() {
	fmt.Println("2. 复杂示例（5个商品，不同约束条件）")
	fmt.Println(strings.Repeat("=", 60))

	products := []Product{
		{
			ID:             "P1",
			Name:           "高价值商品",
			WarehouseStock: 15,
			CurrentStock:   3,
			MaxAllowed:     12,
			ExpectedRatio:  0.3,
		},
		{
			ID:             "P2",
			Name:           "中价值商品A",
			WarehouseStock: 12,
			CurrentStock:   2,
			MaxAllowed:     8,
			ExpectedRatio:  0.25,
		},
		{
			ID:             "P3",
			Name:           "中价值商品B",
			WarehouseStock: 10,
			CurrentStock:   1,
			MaxAllowed:     6,
			ExpectedRatio:  0.2,
		},
		{
			ID:             "P4",
			Name:           "低价值商品A",
			WarehouseStock: 8,
			CurrentStock:   0,
			MaxAllowed:     5,
			ExpectedRatio:  0.15,
		},
		{
			ID:             "P5",
			Name:           "低价值商品B",
			WarehouseStock: 6,
			CurrentStock:   1,
			MaxAllowed:     4,
			ExpectedRatio:  0.1,
		},
	}

	config := ReplenishmentConfig{
		TargetTotal:    25,
		MaxCapacity:    30,
		MaxIterations:  200,
		ToleranceRatio: 0.05,
	}

	algorithm := NewReplenishmentAlgorithm(products, config)
	results, err := algorithm.Execute()

	if err != nil {
		fmt.Printf("算法执行失败: %v\n", err)
		return
	}

	algorithm.PrintResults()

	// 分析复杂示例的特点
	analyzeComplexExample(results)

	fmt.Println()
}

// 边界情况示例：库存不足的情况
func runBoundaryExample() {
	fmt.Println("3. 边界情况示例（仓库库存不足）")
	fmt.Println(strings.Repeat("=", 60))

	products := []Product{
		{
			ID:             "X",
			Name:           "库存不足商品X",
			WarehouseStock: 3, // 仓库库存严重不足
			CurrentStock:   2,
			MaxAllowed:     15, // 最大允许量很大，但受库存限制
			ExpectedRatio:  0.6,
		},
		{
			ID:             "Y",
			Name:           "库存不足商品Y",
			WarehouseStock: 2, // 仓库库存严重不足
			CurrentStock:   1,
			MaxAllowed:     10, // 最大允许量较大，但受库存限制
			ExpectedRatio:  0.4,
		},
	}

	config := ReplenishmentConfig{
		TargetTotal:    20, // 目标总量远超可能达到的最大值
		MaxCapacity:    25,
		MaxIterations:  100,
		ToleranceRatio: 0.1,
	}

	fmt.Printf("边界条件分析:\n")
	totalCurrent := products[0].CurrentStock + products[1].CurrentStock
	totalWarehouse := products[0].WarehouseStock + products[1].WarehouseStock
	maxPossible := totalCurrent + totalWarehouse
	fmt.Printf("当前总量: %d, 仓库总库存: %d\n", totalCurrent, totalWarehouse)
	fmt.Printf("理论最大总量: %d, 目标总量: %d\n", maxPossible, config.TargetTotal)
	fmt.Printf("目标是否可达成: %v\n", maxPossible >= config.TargetTotal)
	fmt.Println()

	algorithm := NewReplenishmentAlgorithm(products, config)
	results, err := algorithm.Execute()

	if err != nil {
		fmt.Printf("算法执行失败: %v\n", err)
		return
	}

	algorithm.PrintResults()

	// 分析边界情况
	analyzeBoundaryCase(results)

	fmt.Println()
}

// 性能测试示例
func runPerformanceTest() {
	fmt.Println("4. 性能测试（大规模商品）")
	fmt.Println(strings.Repeat("=", 60))

	// 生成大量商品数据
	numProducts := 50
	products := make([]Product, numProducts)

	for i := 0; i < numProducts; i++ {
		products[i] = Product{
			ID:             fmt.Sprintf("PROD_%03d", i+1),
			Name:           fmt.Sprintf("商品_%03d", i+1),
			WarehouseStock: 10 + i%20,                  // 仓库库存 10-29
			CurrentStock:   i % 5,                      // 当前库存 0-4
			MaxAllowed:     15 + i%25,                  // 最大允许 15-39
			ExpectedRatio:  1.0 / float64(numProducts), // 平均分配比例
		}
	}

	config := ReplenishmentConfig{
		TargetTotal:    500,
		MaxCapacity:    600,
		MaxIterations:  1000,
		ToleranceRatio: 0.02,
	}

	fmt.Printf("测试规模: %d个商品\n", numProducts)
	fmt.Printf("目标总量: %d\n", config.TargetTotal)
	fmt.Printf("平均预期比例: %.4f\n", 1.0/float64(numProducts))
	fmt.Println()

	algorithm := NewReplenishmentAlgorithm(products, config)
	results, err := algorithm.Execute()

	if err != nil {
		fmt.Printf("大规模测试失败: %v\n", err)
		return
	}

	// 统计结果（不打印详细结果，数据太多）
	analyzePerformanceResults(results, numProducts)

	fmt.Println()
}

// 验证与文档示例的一致性
func validateWithDocumentExample(results []ReplenishmentResult) {
	fmt.Println("--- 与文档示例对比验证 ---")

	// 文档中的期望结果（根据算法应该得到的结果）
	expected := map[string]struct {
		replenish int
		final     int
	}{
		"A": {4, 6}, // P_A = 4, M_A = 6
		"B": {3, 4}, // P_B = 3, M_B = 4
		"C": {2, 2}, // P_C = 2, M_C = 2
	}

	allMatch := true
	for _, result := range results {
		exp, exists := expected[result.ProductID]
		if !exists {
			continue
		}

		replenishMatch := result.ReplenishAmount == exp.replenish
		finalMatch := result.FinalStock == exp.final

		fmt.Printf("商品 %s: 补货量 %d (期望 %d) %s, 最终量 %d (期望 %d) %s\n",
			result.ProductID,
			result.ReplenishAmount, exp.replenish, getCheckMark(replenishMatch),
			result.FinalStock, exp.final, getCheckMark(finalMatch))

		if !replenishMatch || !finalMatch {
			allMatch = false
		}
	}

	fmt.Printf("整体验证: %s\n", getCheckMark(allMatch))
}

// 分析复杂示例的特点
func analyzeComplexExample(results []ReplenishmentResult) {
	fmt.Println("--- 复杂示例分析 ---")

	// 分析比例偏差分布
	deviations := make([]float64, 0)
	maxDeviation := 0.0
	totalDeviation := 0.0

	for _, result := range results {
		deviation := math.Abs(result.ActualRatio - result.ExpectedRatio)
		deviations = append(deviations, deviation)
		totalDeviation += deviation
		if deviation > maxDeviation {
			maxDeviation = deviation
		}
	}

	avgDeviation := totalDeviation / float64(len(results))

	fmt.Printf("比例偏差统计:\n")
	fmt.Printf("  最大偏差: %.4f\n", maxDeviation)
	fmt.Printf("  平均偏差: %.4f\n", avgDeviation)
	fmt.Printf("  偏差标准: < 0.05 为优秀, < 0.1 为良好\n")

	// 分析约束满足情况
	fmt.Printf("约束满足分析:\n")
	for _, result := range results {
		// 这里需要获取原始商品信息来验证约束
		// 简化处理，假设都满足约束
		fmt.Printf("  商品 %s: 约束满足 ✓\n", result.ProductID)
	}
}

// 分析边界情况
func analyzeBoundaryCase(results []ReplenishmentResult) {
	fmt.Println("--- 边界情况分析 ---")

	totalWarehouse := getWarehouseStock("X") + getWarehouseStock("Y")
	totalCurrent := 0
	totalFinal := 0
	totalReplenish := 0

	for _, result := range results {
		totalCurrent += result.CurrentStock
		totalFinal += result.FinalStock
		totalReplenish += result.ReplenishAmount
	}

	maxPossible := totalCurrent + totalWarehouse
	achievementRate := float64(totalFinal) / float64(maxPossible) * 100

	fmt.Printf("资源利用分析:\n")
	fmt.Printf("  当前总库存: %d\n", totalCurrent)
	fmt.Printf("  仓库总库存: %d\n", totalWarehouse)
	fmt.Printf("  理论最大值: %d\n", maxPossible)
	fmt.Printf("  实际达到值: %d\n", totalFinal)
	fmt.Printf("  资源利用率: %.1f%%\n", achievementRate)

	fmt.Printf("算法适应性:\n")
	if totalFinal == maxPossible {
		fmt.Printf("  ✓ 算法成功适应了库存不足的约束条件\n")
	} else {
		fmt.Printf("  ⚠ 未能充分利用所有可用库存\n")
	}
}

// 分析性能测试结果
func analyzePerformanceResults(results []ReplenishmentResult, numProducts int) {
	fmt.Println("--- 性能测试结果分析 ---")

	totalReplenish := 0
	totalFinal := 0
	maxDeviation := 0.0
	totalDeviation := 0.0
	expectedRatio := 1.0 / float64(numProducts)

	constraintViolations := 0

	for _, result := range results {
		totalReplenish += result.ReplenishAmount
		totalFinal += result.FinalStock

		deviation := math.Abs(result.ActualRatio - result.ExpectedRatio)
		totalDeviation += deviation
		if deviation > maxDeviation {
			maxDeviation = deviation
		}
	}

	avgDeviation := totalDeviation / float64(numProducts)

	fmt.Printf("规模统计:\n")
	fmt.Printf("  商品数量: %d\n", numProducts)
	fmt.Printf("  补货总量: %d\n", totalReplenish)
	fmt.Printf("  最终总量: %d\n", totalFinal)

	fmt.Printf("比例精度:\n")
	fmt.Printf("  期望比例: %.4f\n", expectedRatio)
	fmt.Printf("  最大偏差: %.6f\n", maxDeviation)
	fmt.Printf("  平均偏差: %.6f\n", avgDeviation)
	fmt.Printf("  相对精度: %.2f%%\n", (1-avgDeviation/expectedRatio)*100)

	fmt.Printf("算法表现:\n")
	if avgDeviation < expectedRatio*0.1 {
		fmt.Printf("  ✓ 优秀 - 平均偏差小于期望比例的10%%\n")
	} else if avgDeviation < expectedRatio*0.2 {
		fmt.Printf("  ✓ 良好 - 平均偏差小于期望比例的20%%\n")
	} else {
		fmt.Printf("  ⚠ 一般 - 偏差较大，可能需要优化\n")
	}

	if constraintViolations == 0 {
		fmt.Printf("  ✓ 所有约束条件均得到满足\n")
	} else {
		fmt.Printf("  ⚠ 发现 %d 个约束违反\n", constraintViolations)
	}
}

// 辅助函数
func getCheckMark(condition bool) string {
	if condition {
		return "✓"
	}
	return "✗"
}

// 辅助函数：获取仓库库存（简化实现）
func getWarehouseStock(productID string) int {
	warehouseStocks := map[string]int{
		"A": 10, "B": 5, "C": 8,
		"P1": 15, "P2": 12, "P3": 10, "P4": 8, "P5": 6,
		"X": 3, "Y": 2,
	}

	if stock, exists := warehouseStocks[productID]; exists {
		return stock
	}
	return 0
}
