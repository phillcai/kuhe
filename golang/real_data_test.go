package main

import (
	"fmt"
	"log"
)

// 基于真实数据生成的测试用例
func generateRealDataTestCase() ([]VehiclePoint, []Vehicle, [][]float64) {
	// 点位数据 (按经度从东到西排序) - 显示前10个
	points := []VehiclePoint{
		{ID: "111", Longitude: 103.620000, Latitude: 1.240000, IsShortage: false, CompatVehicles: []string{"2", "14", "15"}},
		{ID: "112", Longitude: 103.620000, Latitude: 1.270000, IsShortage: false, CompatVehicles: []string{"2", "14", "15"}},
		{ID: "190", Longitude: 103.630000, Latitude: 1.290000, IsShortage: false, CompatVehicles: []string{"2", "14", "15"}},
		{ID: "53", Longitude: 103.640000, Latitude: 1.350000, IsShortage: false, CompatVehicles: []string{"2", "14", "15"}},
		{ID: "150", Longitude: 103.640000, Latitude: 1.350000, IsShortage: true, CompatVehicles: []string{"2", "14", "15"}},
		{ID: "168", Longitude: 103.650000, Latitude: 1.340000, IsShortage: false, CompatVehicles: []string{"2", "14", "15"}},
		{ID: "67", Longitude: 103.660000, Latitude: 1.300000, IsShortage: false, CompatVehicles: []string{"2", "14", "15"}},
		{ID: "181", Longitude: 103.670000, Latitude: 1.270000, IsShortage: true, CompatVehicles: []string{"2", "14", "15"}},
		{ID: "175", Longitude: 103.680000, Latitude: 1.350000, IsShortage: false, CompatVehicles: []string{"2", "14", "15"}},
		{ID: "174", Longitude: 103.680000, Latitude: 1.350000, IsShortage: false, CompatVehicles: []string{"2", "14", "15"}},
		// ... 更多点位数据 ...
	}

	// 实际数据包含 107 个点位，其中 29 个缺货点位
	// 如需完整数据，请从JSON文件加载

	// 车辆数据 (从东到西排序: 2, 14, 15)
	vehicles := []Vehicle{
		{ID: "15", Ratio: 0.26, Region: 2},
		{ID: "14", Ratio: 0.37, Region: 1},
		{ID: "2", Ratio: 0.37, Region: 0},
	}

	// 时间矩阵 (分钟) - 简化显示前10x10
	timeMatrix := [][]float64{
		{0.0, 7.1, 10.0, 22.4, 19.8, 21.1, 25.9, 44.5, 5.0, 5.0},
		{6.7, 0.0, 6.7, 19.0, 16.2, 17.6, 22.1, 40.8, 5.0, 5.0},
		{11.7, 8.1, 0.0, 17.8, 15.7, 15.0, 21.6, 39.9, 5.0, 5.0},
		{48.2, 44.0, 41.0, 0.0, 35.2, 34.6, 41.6, 54.5, 5.0, 5.0},
		{47.2, 42.4, 39.8, 33.8, 0.0, 33.8, 40.5, 53.6, 5.0, 5.0},
		{17.6, 14.2, 11.5, 5.6, 5.0, 0.0, 14.6, 26.7, 5.0, 5.0},
		{25.5, 22.3, 17.8, 16.6, 16.5, 13.4, 0.0, 30.6, 5.0, 5.0},
		{40.2, 36.0, 35.3, 28.1, 27.7, 23.8, 29.7, 0.0, 5.0, 5.0},
		{5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 0.0, 5.0},
		{5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 0.0},
		// ... 更多矩阵数据 ...
	}

	return points, vehicles, timeMatrix
}

// 运行真实数据测试
func runRealDataTest() {
	fmt.Println("=== 基于真实数据的车辆点位分配测试 ===")
	fmt.Println("注意：此为简化数据，完整测试请使用JSON文件")
	
	// 创建算法实例
	algorithm := NewVehicleAllocationAlgorithm()
	
	// 获取测试数据
	points, vehicles, timeMatrix := generateRealDataTestCase()
	
	// 初始化算法
	if err := algorithm.Initialize(points, vehicles, timeMatrix); err != nil {
		log.Fatalf("算法初始化失败: %v", err)
	}
	
	// 执行算法
	results, err := algorithm.Execute()
	if err != nil {
		log.Fatalf("算法执行失败: %v", err)
	}
	
	// 打印结果
	algorithm.PrintResults(results)
	
	// 验证结果
	validateResults(results, points, vehicles)
}
