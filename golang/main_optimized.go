package main

import (
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strings"
	"time"
)

// ============= 主程序入口 =============

func main() {
	fmt.Println("=== 补货点位聚类分组系统 ===")
	fmt.Println("专门针对补货点位的智能分组算法")
	fmt.Println()

	// 记录开始时间
	startTime := time.Now()

	// 运行动态分区算法
	if err := runOptimizedDynamicPartition(); err != nil {
		log.Fatalf("算法执行失败: %v", err)
	}

	// 计算总执行时间
	totalTime := time.Since(startTime)
	fmt.Printf("\n=== 算法执行完成 ===\n")
	fmt.Printf("总执行时间: %.2f 秒\n", totalTime.Seconds())
}

// runOptimizedDynamicPartition 运行优化的动态分区算法
func runOptimizedDynamicPartition() error {
	// 第0步：创建配置
	config := createOptimizedConfig()

	// 第1步：创建算法实例
	alg := NewDynamicPartitionAlgorithm(config)

	// 第2步：定义数据路径
	dataPath := filepath.Join("..", "data")
	pointsPath := filepath.Join(dataPath, "点位信息.csv")
	travelTimePath := filepath.Join(dataPath, "duration_point.csv")
	recallPointsPath := filepath.Join(dataPath, "recall_point.csv")

	fmt.Println("=== 第一阶段：数据预处理与约束分析 ===")

	// 第3步：数据预处理
	if err := alg.LoadData(pointsPath, travelTimePath, recallPointsPath); err != nil {
		return fmt.Errorf("数据加载失败: %v", err)
	}

	fmt.Println("\n=== 第二阶段：补货点位聚类分组 ===")

	// 第4步：补货点位聚类
	groups, err := alg.InitialPartition()
	if err != nil {
		return fmt.Errorf("补货点位聚类失败: %v", err)
	}

	// 打印聚类结果
	printPartitionSummary("补货点位聚类", groups, alg)

	// 调试：检查实际处理的点位数量
	totalPointsInGroups := 0
	for _, pids := range groups {
		totalPointsInGroups += len(pids)
	}
	fmt.Printf("调试信息：分组中总点位数 = %d, pointDict中点位数 = %d\n", totalPointsInGroups, len(alg.GetPointDict()))

	fmt.Println("\n=== 第三阶段：启发式优化与局部搜索 ===")

	// 第5步：启发式优化
	optimizedGroups, err := alg.OptimizePartition(groups)
	if err != nil {
		return fmt.Errorf("分区优化失败: %v", err)
	}

	// 打印优化后分区结果
	printPartitionSummary("优化后分区", optimizedGroups, alg)

	fmt.Println("\n=== 第四阶段：结果验证与输出 ===")

	// 第6步：结果验证与输出
	result, err := alg.ValidateAndOutput(optimizedGroups)
	if err != nil {
		return fmt.Errorf("结果输出失败: %v", err)
	}

	// 第7步：打印最终报告
	printFinalReport(result)

	return nil
}

// createOptimizedConfig 创建优化的配置
func createOptimizedConfig() *Config {
	config := DefaultConfig()

	// 根据实际需求调整参数
	config.NClusters = 3       // 分组数量
	config.MaxIterations = 100 // K-means最大迭代次数
	config.MaxOptimIter = 30   // 优化最大迭代次数
	config.TimeWeight = 0.7    // 行驶时长权重
	config.GeoWeight = 0.3     // 地理距离权重
	config.StdFactor = 2.0     // 离群点判定标准差倍数
	config.ThresholdKm = 15.0  // 孤立点归组阈值
	config.MinInterval = 120.0 // 时间窗口最小间隔

	// 模拟退火参数
	config.InitTemp = 100.0 // 初始温度
	config.CoolRate = 0.95  // 冷却率
	config.MinTemp = 0.1    // 最小温度

	// 时间窗口参数
	config.TimeWindowStart = 540.0 // 9:00
	config.TimeWindowEnd = 1260.0  // 21:00

	// 输出配置
	config.Verbose = true
	config.OutputPath = "../output"

	// 新增：补货点位优先策略开关
	config.RecallPointsPriority = true    // 启用补货点位优先策略（保存第一阶段结果）
	config.StrictRecallConstraints = true // 对补货点位使用更严格的约束
	config.SkipLoadBalancing = false      // 是否跳过负载均衡（可选）

	return config
}

// printPartitionSummary 打印分区摘要
func printPartitionSummary(title string, groups map[int][]int, alg *DynamicPartitionAlgorithm) {
	fmt.Printf("\n--- %s结果摘要 ---\n", title)

	totalPoints := 0

	for groupID, pids := range groups {
		totalPoints += len(pids)
		fmt.Printf("分组%d: %d个补货点位\n", groupID+1, len(pids))
	}

	fmt.Printf("总计: %d个补货点位\n", totalPoints)

	// 计算负载均衡指数
	if len(groups) > 0 {
		avgSize := float64(totalPoints) / float64(len(groups))
		variance := 0.0
		for _, pids := range groups {
			diff := float64(len(pids)) - avgSize
			variance += diff * diff
		}
		variance /= float64(len(groups))
		balanceIndex := 1.0 / (1.0 + variance/avgSize)

		fmt.Printf("平均组大小: %.1f, 负载均衡指数: %.3f\n", avgSize, balanceIndex)
	}
}

// printFinalReport 打印最终报告
func printFinalReport(result *Result) {
	fmt.Printf("\n=== 最终执行报告 ===\n")
	fmt.Printf("算法配置:\n")
	fmt.Printf("  - 分组数量: %d\n", result.Config.NClusters)
	fmt.Printf("  - 时间权重: %.2f, 地理权重: %.2f\n",
		result.Config.TimeWeight, result.Config.GeoWeight)
	fmt.Printf("  - 最大迭代次数: %d\n", result.Config.MaxIterations)

	fmt.Printf("\n性能指标:\n")
	fmt.Printf("  - 总距离成本: %.2f\n", result.Performance.TotalDistance)
	fmt.Printf("  - 平均组大小: %.1f\n", result.Performance.AverageGroupSize)
	fmt.Printf("  - 负载均衡指数: %.3f\n", result.Performance.LoadBalanceIndex)
	fmt.Printf("  - 时间窗口覆盖率: %.1f%%\n", result.Performance.TimeWindowCoverage*100)

	fmt.Printf("\n约束满足状态:\n")
	fmt.Printf("  - 时间窗口违反数: %d\n", result.Constraints.TimeWindowViolations)
	fmt.Printf("  - 负载均衡得分: %.3f\n", result.Constraints.LoadBalanceScore)
	fmt.Printf("  - 地理分散度: %.2f km\n", result.Constraints.GeographicSpread)
	fmt.Printf("  - 约束满足状态: %v\n", result.Constraints.ConstraintsSatisfied)

	fmt.Printf("\n分组详情:\n")
	for groupID, pids := range result.Groups {
		recallCount := 0
		for _, pid := range pids {
			// 这里需要访问算法实例来检查补货点位，暂时简化
			_ = pid
		}
		fmt.Printf("  分组%d: %d个点位 (补货点位: %d个)\n",
			groupID+1, len(pids), recallCount)
	}

	fmt.Printf("\n输出文件:\n")
	fmt.Printf("  - CSV结果: %s/dynamic_partition_result.csv\n", result.Config.OutputPath)
	fmt.Printf("  - 详细报告: %s/partition_report.txt\n", result.Config.OutputPath)

	// 算法质量评估
	fmt.Printf("\n算法质量评估:\n")
	if result.Performance.LoadBalanceIndex >= 0.9 {
		fmt.Printf("  ✓ 负载均衡: 优秀 (%.3f)\n", result.Performance.LoadBalanceIndex)
	} else if result.Performance.LoadBalanceIndex >= 0.8 {
		fmt.Printf("  ✓ 负载均衡: 良好 (%.3f)\n", result.Performance.LoadBalanceIndex)
	} else {
		fmt.Printf("  ⚠ 负载均衡: 需要改进 (%.3f)\n", result.Performance.LoadBalanceIndex)
	}

	if result.Performance.TimeWindowCoverage >= 0.9 {
		fmt.Printf("  ✓ 时间窗口覆盖: 优秀 (%.1f%%)\n", result.Performance.TimeWindowCoverage*100)
	} else if result.Performance.TimeWindowCoverage >= 0.8 {
		fmt.Printf("  ✓ 时间窗口覆盖: 良好 (%.1f%%)\n", result.Performance.TimeWindowCoverage*100)
	} else {
		fmt.Printf("  ⚠ 时间窗口覆盖: 需要改进 (%.1f%%)\n", result.Performance.TimeWindowCoverage*100)
	}

	if result.Constraints.TimeWindowViolations == 0 {
		fmt.Printf("  ✓ 约束满足: 完全满足\n")
	} else {
		fmt.Printf("  ⚠ 约束满足: %d个违反\n", result.Constraints.TimeWindowViolations)
	}

	fmt.Printf("\n=== 算法执行成功 ===\n")
}

// printFirstStageRecallSummary 打印第一阶段补货点位聚类结果摘要
func printFirstStageRecallSummary(alg *DynamicPartitionAlgorithm) {
	fmt.Printf("\n--- 第一阶段结果摘要（仅补货点位聚类）---\n")

	// 读取第一阶段保存的报告文件
	reportPath := filepath.Join(alg.GetConfig().OutputPath, "first_stage_report.txt")
	content, err := os.ReadFile(reportPath)
	if err != nil {
		fmt.Printf("无法读取第一阶段报告: %v\n", err)
		return
	}

	// 解析报告内容，提取关键信息
	lines := strings.Split(string(content), "\n")
	totalRecallPoints := 0
	groupCounts := make(map[int]int)

	for _, line := range lines {
		line = strings.TrimSpace(line)

		// 解析分组信息
		if strings.HasPrefix(line, "分组") && strings.Contains(line, "个补货点位") {
			var groupID, count int
			if n, _ := fmt.Sscanf(line, "分组%d: %d个补货点位", &groupID, &count); n == 2 {
				groupCounts[groupID] = count
				totalRecallPoints += count
			}
		}
	}

	// 显示分组结果（确保显示所有分组，包括空分组）
	config := alg.GetConfig()
	for i := 1; i <= config.NClusters; i++ {
		if count, exists := groupCounts[i]; exists {
			fmt.Printf("分组%d: %d个补货点位\n", i, count)
		} else {
			fmt.Printf("分组%d: 0个补货点位\n", i)
		}
	}

	fmt.Printf("总计: %d个补货点位\n", totalRecallPoints)

	// 计算并显示负载均衡指数
	if len(groupCounts) > 0 {
		avgSize := float64(totalRecallPoints) / float64(len(groupCounts))
		variance := 0.0
		for _, count := range groupCounts {
			diff := float64(count) - avgSize
			variance += diff * diff
		}
		variance /= float64(len(groupCounts))
		balanceIndex := 1.0 / (1.0 + variance/avgSize)

		fmt.Printf("平均组大小: %.1f, 负载均衡指数: %.3f\n", avgSize, balanceIndex)
	}
}

// ============= 工具函数 =============

// printAlgorithmInfo 打印算法信息
func printAlgorithmInfo() {
	fmt.Println("算法特性:")
	fmt.Println("  - 多阶段设计: 数据预处理 → 初始分区 → 启发式优化 → 结果验证")
	fmt.Println("  - 约束处理: 时间窗口约束、负载均衡约束、地理集中性约束")
	fmt.Println("  - 优化策略: K-means聚类 + 局部搜索 + 模拟退火")
	fmt.Println("  - 多目标优化: 运力均衡 + 总行驶距离 + 时间窗口满足")
	fmt.Println("  - 补货点位优先级: 优先分配补货点位到最优分组")
	fmt.Println("  - 实时监控: 详细的性能指标和约束状态监控")
	fmt.Println()
}

// validateEnvironment 验证运行环境
func validateEnvironment() error {
	// 检查数据文件是否存在
	dataPath := filepath.Join("..", "data")
	requiredFiles := []string{
		"点位信息.csv",
		// "duration_path.csv", // 可选文件
		// "recall_point.csv",  // 可选文件
	}

	for _, filename := range requiredFiles {
		filePath := filepath.Join(dataPath, filename)
		if !fileExists(filePath) {
			return fmt.Errorf("必需的数据文件不存在: %s", filePath)
		}
	}

	// 检查输出目录权限
	outputPath := filepath.Join("..", "output")
	if err := ensureDir(outputPath); err != nil {
		return fmt.Errorf("无法创建输出目录: %v", err)
	}

	return nil
}

// fileExists 检查文件是否存在
func fileExists(filePath string) bool {
	_, err := os.Stat(filePath)
	return err == nil
}

// ensureDir 确保目录存在
func ensureDir(dirPath string) error {
	return os.MkdirAll(dirPath, 0755)
}

// ============= 性能测试和基准测试 =============

// runPerformanceTest 运行性能测试
func runPerformanceTest() {
	fmt.Println("=== 性能测试 ===")

	// 测试不同配置下的算法性能
	configs := []*Config{
		{NClusters: 2, MaxIterations: 50, TimeWeight: 0.5, GeoWeight: 0.5},
		{NClusters: 3, MaxIterations: 100, TimeWeight: 0.7, GeoWeight: 0.3},
		{NClusters: 4, MaxIterations: 150, TimeWeight: 0.8, GeoWeight: 0.2},
	}

	for i, config := range configs {
		fmt.Printf("\n--- 配置 %d ---\n", i+1)
		fmt.Printf("分组数: %d, 迭代数: %d, 时间权重: %.1f\n",
			config.NClusters, config.MaxIterations, config.TimeWeight)

		startTime := time.Now()

		// 运行算法（这里需要实际的测试逻辑）
		// result, err := runAlgorithmWithConfig(config)

		duration := time.Since(startTime)
		fmt.Printf("执行时间: %.2f 秒\n", duration.Seconds())

		// 这里可以添加更多的性能指标比较
	}
}

// ============= 算法比较和验证 =============

// compareWithOriginal 与原始算法比较
func compareWithOriginal() {
	fmt.Println("=== 算法比较 ===")
	fmt.Println("优化版本 vs 原始版本:")
	fmt.Println("  + 模块化设计: 更清晰的代码结构")
	fmt.Println("  + 多阶段处理: 更系统的算法流程")
	fmt.Println("  + 约束处理: 更完善的约束满足机制")
	fmt.Println("  + 启发式搜索: 更智能的优化策略")
	fmt.Println("  + 性能监控: 更详细的指标和报告")
	fmt.Println("  + 配置管理: 更灵活的参数调整")
	fmt.Println("  + 错误处理: 更健壮的异常处理")
}

// ============= 帮助和使用说明 =============

// printUsage 打印使用说明
func printUsage() {
	fmt.Println("=== 使用说明 ===")
	fmt.Println("1. 准备数据文件:")
	fmt.Println("   - data/点位信息.csv (必需)")
	fmt.Println("   - data/duration_path.csv (可选，行驶时长数据)")
	fmt.Println("   - data/recall_point.csv (可选，补货点位数据)")
	fmt.Println()
	fmt.Println("2. 运行程序:")
	fmt.Println("   go run main_optimized.go dynamic_partition.go algorithm_impl.go")
	fmt.Println()
	fmt.Println("3. 查看结果:")
	fmt.Println("   - output/dynamic_partition_result.csv")
	fmt.Println("   - output/partition_report.txt")
	fmt.Println()
	fmt.Println("4. 参数调整:")
	fmt.Println("   修改 createOptimizedConfig() 函数中的配置参数")
	fmt.Println()
}
