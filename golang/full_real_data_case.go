package main

import (
	"encoding/csv"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"log"
	"os"
	"strconv"
)

// 从JSON文件加载真实数据的测试用例
func loadRealDataFromJSON() ([]VehiclePoint, []Vehicle, [][]float64, error) {
	// 读取JSON文件
	data, err := ioutil.ReadFile("real_data_test_case.json")
	if err != nil {
		return nil, nil, nil, fmt.Errorf("读取JSON文件失败: %v", err)
	}

	// 定义JSON数据结构
	var jsonData struct {
		Points []struct {
			ID             string   `json:"id"`
			Longitude      float64  `json:"longitude"`
			Latitude       float64  `json:"latitude"`
			IsShortage     bool     `json:"is_shortage"`
			CompatVehicles []string `json:"compat_vehicles"`
		} `json:"points"`
		Vehicles []struct {
			ID     string  `json:"id"`
			Ratio  float64 `json:"ratio"`
			Region int     `json:"region"`
		} `json:"vehicles"`
		TimeMatrix [][]float64 `json:"time_matrix"`
		PointIDs   []string    `json:"point_ids"`
	}

	// 解析JSON
	if err := json.Unmarshal(data, &jsonData); err != nil {
		return nil, nil, nil, fmt.Errorf("解析JSON失败: %v", err)
	}

	// 转换为算法所需的数据结构
	points := make([]VehiclePoint, len(jsonData.Points))
	for i, p := range jsonData.Points {
		points[i] = VehiclePoint{
			ID:             p.ID,
			Longitude:      p.Longitude,
			Latitude:       p.Latitude,
			IsShortage:     p.IsShortage,
			CompatVehicles: p.CompatVehicles,
		}
	}

	vehicles := make([]Vehicle, len(jsonData.Vehicles))
	for i, v := range jsonData.Vehicles {
		vehicles[i] = Vehicle{
			ID:     v.ID,
			Ratio:  v.Ratio,
			Region: v.Region,
		}
	}

	return points, vehicles, jsonData.TimeMatrix, nil
}

// 运行完整的真实数据测试
func runFullRealDataTest() {
	fmt.Println("=== 完整真实数据车辆点位分配测试 ===")
	fmt.Println("数据来源：新加坡111个无人售货机点位")

	// 从JSON文件加载数据
	points, vehicles, timeMatrix, err := loadRealDataFromJSON()
	if err != nil {
		log.Printf("❌ 加载真实数据失败: %v", err)
		fmt.Println("无法加载完整数据，程序退出")
		return
	}

	fmt.Printf("✅ 成功加载真实数据: %d个点位, %d辆车\n", len(points), len(vehicles))

	// 统计缺货点位
	shortageCount := 0
	restrictedCount := 0
	for _, point := range points {
		if point.IsShortage {
			shortageCount++
		}
		if len(point.CompatVehicles) == 1 {
			restrictedCount++
		}
	}

	fmt.Printf("📊 数据概况:\n")
	fmt.Printf("   - 缺货点位: %d个 (%.1f%%)\n", shortageCount, float64(shortageCount)/float64(len(points))*100)
	fmt.Printf("   - 受限点位: %d个 (%.1f%%)\n", restrictedCount, float64(restrictedCount)/float64(len(points))*100)
	fmt.Printf("   - 车辆配置: 车辆2(东区), 车辆14(中区), 车辆15(西区)\n")

	// 创建算法实例
	algorithm := NewVehicleAllocationAlgorithm()

	// 调整算法参数（针对真实数据优化）
	algorithm.WeightAlpha = 0.6       // 提高运力平衡权重
	algorithm.WeightBeta = 0.35       // 缺货点位集中性
	algorithm.WeightGamma = 0.05      // 不缺货点位集中性
	algorithm.MaxIterations = 20      // 增加迭代次数
	algorithm.ConvergenceThres = 0.01 // 提高收敛精度

	fmt.Printf("🔧 算法参数: α=%.2f, β=%.2f, γ=%.2f\n",
		algorithm.WeightAlpha, algorithm.WeightBeta, algorithm.WeightGamma)

	// 初始化算法
	if err := algorithm.Initialize(points, vehicles, timeMatrix); err != nil {
		log.Fatalf("❌ 算法初始化失败: %v", err)
	}

	fmt.Println("\n🚀 开始执行三阶段分配算法...")

	// 执行算法
	results, err := algorithm.Execute()
	if err != nil {
		log.Fatalf("❌ 算法执行失败: %v", err)
	}

	fmt.Println("\n📋 算法执行完成，结果如下：")

	// 打印结果
	algorithm.PrintResults(results)

	// 详细验证结果
	fmt.Println("\n🔍 详细约束验证:")
	validateRealDataResults(results, points, vehicles)

	// 性能分析
	fmt.Println("\n📈 性能分析:")
	analyzePerformance(results, points, vehicles, timeMatrix)

	// 输出CSV格式结果
	fmt.Println("\n📊 生成CSV结果文件...")
	err = outputCSVResults(results, points, vehicles)
	if err != nil {
		log.Printf("⚠️ CSV输出失败: %v", err)
	} else {
		fmt.Println("✅ 结果已保存到: allocation_results.csv")
	}

	// 输出只包含缺货点位的CSV
	err = outputShortageOnlyCSV(results, points, vehicles)
	if err != nil {
		log.Printf("⚠️ 缺货点位CSV输出失败: %v", err)
	} else {
		fmt.Println("✅ 缺货点位已保存到: shortage_points.csv")
	}
}

// 验证真实数据结果
func validateRealDataResults(results []AllocationResult, points []VehiclePoint, vehicles []Vehicle) {
	// 检查全点位覆盖
	assignedPoints := make(map[string]int) // 点位ID -> 分配给的车辆数量
	totalAssigned := 0

	for vehicleIdx, result := range results {
		fmt.Printf("\n车辆 %s 分配详情:\n", vehicles[vehicleIdx].ID)
		fmt.Printf("  - 分配点位数: %d\n", len(result.AssignedPoints))
		fmt.Printf("  - 缺货点位数: %d\n", result.ShortageCount)

		for _, pointID := range result.AssignedPoints {
			assignedPoints[pointID]++
			totalAssigned++
		}
	}

	// 检查重复分配
	duplicates := 0
	for pointID, count := range assignedPoints {
		if count > 1 {
			fmt.Printf("❌ 点位 %s 被分配给 %d 辆车\n", pointID, count)
			duplicates++
		}
	}

	// 检查未分配点位
	unassigned := 0
	for _, point := range points {
		if assignedPoints[point.ID] == 0 {
			fmt.Printf("❌ 点位 %s 未被分配\n", point.ID)
			unassigned++
		}
	}

	fmt.Printf("\n📊 分配统计:\n")
	fmt.Printf("  - 总点位数: %d\n", len(points))
	fmt.Printf("  - 已分配点位: %d\n", len(assignedPoints))
	fmt.Printf("  - 重复分配: %d\n", duplicates)
	fmt.Printf("  - 未分配: %d\n", unassigned)

	if duplicates == 0 && unassigned == 0 {
		fmt.Println("✅ 全点位覆盖约束: 完美满足")
	} else {
		fmt.Println("❌ 全点位覆盖约束: 存在问题")
	}
}

// 性能分析
func analyzePerformance(results []AllocationResult, points []VehiclePoint, vehicles []Vehicle, timeMatrix [][]float64) {
	// 创建点位ID到索引的映射
	pointIDToIndex := make(map[string]int)
	for i, point := range points {
		pointIDToIndex[point.ID] = i
	}

	totalShortage := 0
	for _, point := range points {
		if point.IsShortage {
			totalShortage++
		}
	}

	fmt.Printf("运力平衡分析:\n")
	balanceScore := 0.0
	for i, result := range results {
		if totalShortage > 0 {
			actualRatio := float64(result.ShortageCount) / float64(totalShortage)
			targetRatio := vehicles[i].Ratio
			deviation := actualRatio - targetRatio
			balanceScore += deviation * deviation

			fmt.Printf("  车辆 %s: 目标 %.1f%%, 实际 %.1f%%, 偏差 %+.1f%%\n",
				vehicles[i].ID, targetRatio*100, actualRatio*100, deviation*100)
		}
	}

	if totalShortage > 0 {
		fmt.Printf("  运力平衡得分: %.4f (越小越好)\n", balanceScore)
	} else {
		fmt.Printf("  当前无缺货点位，运力平衡无需评估\n")
	}

	// 地理集中性分析
	fmt.Printf("\n地理集中性分析:\n")
	for i, result := range results {
		if len(result.AssignedPoints) <= 1 {
			continue
		}

		totalTime := 0.0
		pairCount := 0

		for j := 0; j < len(result.AssignedPoints); j++ {
			for k := j + 1; k < len(result.AssignedPoints); k++ {
				idx1 := pointIDToIndex[result.AssignedPoints[j]]
				idx2 := pointIDToIndex[result.AssignedPoints[k]]

				if idx1 < len(timeMatrix) && idx2 < len(timeMatrix[idx1]) {
					totalTime += timeMatrix[idx1][idx2]
					pairCount++
				}
			}
		}

		if pairCount > 0 {
			avgTime := totalTime / float64(pairCount)
			fmt.Printf("  车辆 %s: 平均点位间距离 %.1f分钟\n", vehicles[i].ID, avgTime)
		}
	}

	// 区域分布分析
	fmt.Printf("\n区域分布分析:\n")
	for i, result := range results {
		if len(result.AssignedPoints) == 0 {
			continue
		}

		minLon, maxLon := 999.0, -999.0
		minLat, maxLat := 999.0, -999.0

		for _, pointID := range result.AssignedPoints {
			// 找到对应的点位
			for _, point := range points {
				if point.ID == pointID {
					if point.Longitude < minLon {
						minLon = point.Longitude
					}
					if point.Longitude > maxLon {
						maxLon = point.Longitude
					}
					if point.Latitude < minLat {
						minLat = point.Latitude
					}
					if point.Latitude > maxLat {
						maxLat = point.Latitude
					}
					break
				}
			}
		}

		fmt.Printf("  车辆 %s: 经度范围 %.3f~%.3f, 纬度范围 %.3f~%.3f\n",
			vehicles[i].ID, minLon, maxLon, minLat, maxLat)
	}
}

// 输出CSV格式结果
func outputCSVResults(results []AllocationResult, points []VehiclePoint, vehicles []Vehicle) error {
	// 创建CSV文件
	file, err := os.Create("allocation_results.csv")
	if err != nil {
		return fmt.Errorf("创建CSV文件失败: %v", err)
	}
	defer file.Close()

	// 创建CSV写入器
	writer := csv.NewWriter(file)
	defer writer.Flush()

	// 写入表头
	header := []string{"point_id", "longitude", "latitude", "car_id"}
	if err := writer.Write(header); err != nil {
		return fmt.Errorf("写入CSV表头失败: %v", err)
	}

	// 创建点位ID到点位信息的映射
	pointMap := make(map[string]VehiclePoint)
	for _, point := range points {
		pointMap[point.ID] = point
	}

	// 写入分配结果
	for vehicleIdx, result := range results {
		vehicleID := vehicles[vehicleIdx].ID

		for _, pointID := range result.AssignedPoints {
			point, exists := pointMap[pointID]
			if !exists {
				log.Printf("⚠️ 未找到点位信息: %s", pointID)
				continue
			}

			record := []string{
				pointID,
				strconv.FormatFloat(point.Longitude, 'f', 6, 64),
				strconv.FormatFloat(point.Latitude, 'f', 6, 64),
				vehicleID,
			}

			if err := writer.Write(record); err != nil {
				return fmt.Errorf("写入CSV记录失败: %v", err)
			}
		}
	}

	return nil
}

// 输出只包含缺货点位的CSV格式结果
func outputShortageOnlyCSV(results []AllocationResult, points []VehiclePoint, vehicles []Vehicle) error {
	// 创建CSV文件
	file, err := os.Create("shortage_points.csv")
	if err != nil {
		return fmt.Errorf("创建缺货点位CSV文件失败: %v", err)
	}
	defer file.Close()

	// 创建CSV写入器
	writer := csv.NewWriter(file)
	defer writer.Flush()

	// 写入表头
	header := []string{"point_id", "longitude", "latitude", "car_id"}
	if err := writer.Write(header); err != nil {
		return fmt.Errorf("写入缺货点位CSV表头失败: %v", err)
	}

	// 创建点位ID到点位信息的映射
	pointMap := make(map[string]VehiclePoint)
	for _, point := range points {
		pointMap[point.ID] = point
	}

	// 只写入缺货点位的分配结果
	for vehicleIdx, result := range results {
		vehicleID := vehicles[vehicleIdx].ID

		for _, pointID := range result.AssignedPoints {
			point, exists := pointMap[pointID]
			if !exists {
				log.Printf("⚠️ 未找到点位信息: %s", pointID)
				continue
			}

			// 只处理缺货点位
			if !point.IsShortage {
				continue
			}

			record := []string{
				pointID,
				strconv.FormatFloat(point.Longitude, 'f', 6, 64),
				strconv.FormatFloat(point.Latitude, 'f', 6, 64),
				vehicleID,
			}

			if err := writer.Write(record); err != nil {
				return fmt.Errorf("写入缺货点位CSV记录失败: %v", err)
			}
		}
	}

	return nil
}

// 主函数 - 运行完整真实数据测试
func main() {
	runFullRealDataTest()
}
