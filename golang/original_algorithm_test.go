package main

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"log"
)

// 测试原始算法的主函数
func main() {
	fmt.Println("\n=== 原始算法车辆点位分配测试 ===")
	fmt.Println("数据来源：新加坡111个无人售货机点位")

	// 加载真实数据
	points, vehicles, timeMatrix, err := loadRealDataFromJSONOriginal()
	if err != nil {
		log.Fatalf("❌ 加载真实数据失败: %v", err)
	}

	fmt.Printf("✅ 成功加载真实数据: %d个点位, %d辆车\n", len(points), len(vehicles))

	// 统计数据概况
	shortageCount := 0
	restrictedCount := 0
	for _, point := range points {
		if point.IsShortage {
			shortageCount++
		}
		if len(point.CompatVehicles) < len(vehicles) {
			restrictedCount++
		}
	}

	fmt.Printf("📊 数据概况:\n")
	fmt.Printf("   - 缺货点位: %d个 (%.1f%%)\n", shortageCount, float64(shortageCount)/float64(len(points))*100)
	fmt.Printf("   - 受限点位: %d个 (%.1f%%)\n", restrictedCount, float64(restrictedCount)/float64(len(points))*100)
	fmt.Printf("   - 车辆配置: 车辆2(东区), 车辆14(中区), 车辆15(西区)\n")

	// 创建原始算法实例
	algorithm := NewVehicleAllocationAlgorithm()

	// 设置算法参数
	algorithm.WeightAlpha = 0.75       // 运力平衡权重
	algorithm.WeightBeta = 0.20        // 缺货点位集中性权重
	algorithm.WeightGamma = 0.05       // 不缺货点位集中性权重
	algorithm.MaxIterations = 20       // 最大迭代次数
	algorithm.ConvergenceThres = 0.005 // 收敛阈值

	fmt.Printf("🔧 原始算法参数: α=%.2f, β=%.2f, γ=%.2f\n",
		algorithm.WeightAlpha, algorithm.WeightBeta, algorithm.WeightGamma)

	// 初始化算法
	err = algorithm.Initialize(points, vehicles, timeMatrix)
	if err != nil {
		log.Fatalf("❌ 算法初始化失败: %v", err)
	}

	fmt.Println("\n🚀 开始执行原始三阶段分配算法...")

	// 执行算法
	results, err := algorithm.Execute()
	if err != nil {
		log.Fatalf("❌ 算法执行失败: %v", err)
	}

	fmt.Println("\n📋 原始算法执行完成，结果如下：")

	// 打印结果
	algorithm.PrintResults(results)

	// 验证结果
	validateOriginalResults(results, points)

	// 输出CSV文件
	err = outputOriginalCSVResults(results, points, "original_allocation_results.csv")
	if err != nil {
		log.Printf("⚠️  输出CSV失败: %v", err)
	} else {
		fmt.Printf("✅ 结果已保存到: original_allocation_results.csv\n")
	}

	err = outputOriginalShortageOnlyCSV(results, points, "original_shortage_points.csv")
	if err != nil {
		log.Printf("⚠️  输出缺货点位CSV失败: %v", err)
	} else {
		fmt.Printf("✅ 缺货点位已保存到: original_shortage_points.csv\n")
	}
}

// 加载真实数据的JSON文件（原始算法版本）
func loadRealDataFromJSONOriginal() ([]VehiclePoint, []Vehicle, [][]float64, error) {
	// 读取JSON文件
	data, err := ioutil.ReadFile("../output/real_data_test_case.json")
	if err != nil {
		return nil, nil, nil, fmt.Errorf("读取JSON文件失败: %v", err)
	}

	// 解析JSON数据
	var testCase struct {
		Points     []VehiclePoint `json:"points"`
		Vehicles   []Vehicle      `json:"vehicles"`
		TimeMatrix [][]float64    `json:"time_matrix"`
	}

	err = json.Unmarshal(data, &testCase)
	if err != nil {
		return nil, nil, nil, fmt.Errorf("解析JSON失败: %v", err)
	}

	return testCase.Points, testCase.Vehicles, testCase.TimeMatrix, nil
}

// 验证原始算法结果
func validateOriginalResults(results []AllocationResult, points []VehiclePoint) {
	fmt.Println("\n🔍 详细约束验证:")

	totalAssigned := 0
	totalShortage := 0

	for _, result := range results {
		fmt.Printf("\n车辆 %s 分配详情:\n", result.VehicleID)
		fmt.Printf("  - 分配点位数: %d\n", len(result.AssignedPoints))
		fmt.Printf("  - 缺货点位数: %d\n", result.ShortageCount)

		totalAssigned += len(result.AssignedPoints)
		totalShortage += result.ShortageCount
	}

	// 统计分析
	fmt.Printf("\n📊 分配统计:\n")
	fmt.Printf("  - 总点位数: %d\n", len(points))
	fmt.Printf("  - 已分配点位: %d\n", totalAssigned)

	// 检查覆盖率
	if totalAssigned == len(points) {
		fmt.Printf("✅ 全点位覆盖约束: 完美满足\n")
	} else {
		fmt.Printf("❌ 全点位覆盖约束: 缺失 %d 个点位\n", len(points)-totalAssigned)
	}
}

// 输出原始算法CSV结果
func outputOriginalCSVResults(results []AllocationResult, points []VehiclePoint, filename string) error {
	content := "point_id,longitude,latitude,car_id\n"

	// 创建点位映射
	pointMap := make(map[string]VehiclePoint)
	for _, point := range points {
		pointMap[point.ID] = point
	}

	for _, result := range results {
		for _, pointID := range result.AssignedPoints {
			if point, exists := pointMap[pointID]; exists {
				content += fmt.Sprintf("%s,%.6f,%.6f,%s\n",
					pointID, point.Longitude, point.Latitude, result.VehicleID)
			}
		}
	}

	return ioutil.WriteFile(filename, []byte(content), 0644)
}

// 输出原始算法缺货点位CSV
func outputOriginalShortageOnlyCSV(results []AllocationResult, points []VehiclePoint, filename string) error {
	content := "point_id,longitude,latitude,car_id,is_shortage\n"

	// 创建点位映射
	pointMap := make(map[string]VehiclePoint)
	for _, point := range points {
		pointMap[point.ID] = point
	}

	for _, result := range results {
		for _, pointID := range result.AssignedPoints {
			if point, exists := pointMap[pointID]; exists && point.IsShortage {
				content += fmt.Sprintf("%s,%.6f,%.6f,%s,true\n",
					pointID, point.Longitude, point.Latitude, result.VehicleID)
			}
		}
	}

	return ioutil.WriteFile(filename, []byte(content), 0644)
}
