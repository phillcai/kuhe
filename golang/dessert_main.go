package main

import (
	"fmt"
	"log"
)

// 甜品分拣补货算法测试函数
func TestDessertReplenishment() {
	fmt.Println("甜品分拣补货算法演示")

	// 创建算法实例
	algorithm := NewDessertReplenishmentAlgorithm()

	// 定义测试数据
	skus := []DessertSKU{
		{
			ID:              "A",
			CurrentStock:    2,
			WarehouseStock:  15,
			MinStock:        3,
			ExpectedRatio:   0.3,
			CompatibleLanes: []int{1, 2},
			Importance:      1.0,
		},
		{
			ID:              "B",
			CurrentStock:    1,
			WarehouseStock:  12,
			MinStock:        2,
			ExpectedRatio:   0.25,
			CompatibleLanes: []int{1},
			Importance:      1.0,
		},
		{
			ID:              "C",
			CurrentStock:    0,
			WarehouseStock:  10,
			MinStock:        1,
			ExpectedRatio:   0.2,
			CompatibleLanes: []int{2, 3},
			Importance:      1.0,
		},
		{
			ID:              "D",
			CurrentStock:    3,
			WarehouseStock:  8,
			MinStock:        2,
			ExpectedRatio:   0.15,
			CompatibleLanes: []int{3},
			Importance:      1.0,
		},
		{
			ID:              "E",
			CurrentStock:    1,
			WarehouseStock:  5,
			MinStock:        1,
			ExpectedRatio:   0.1,
			CompatibleLanes: []int{1, 2, 3},
			Importance:      1.0,
		},
	}

	laneTypes := []LaneType{
		{ID: 1, TotalLanes: 8},
		{ID: 2, TotalLanes: 6},
		{ID: 3, TotalLanes: 4},
	}

	// 初始化算法
	err := algorithm.Initialize(skus, laneTypes)
	if err != nil {
		log.Fatalf("算法初始化失败: %v", err)
	}

	fmt.Printf("总货道数: %d\n", algorithm.TotalLanes)
	fmt.Println("货道类型配置:")
	for _, laneType := range laneTypes {
		fmt.Printf("  类型%d: %d个货道\n", laneType.ID, laneType.TotalLanes)
	}

	fmt.Println("\nSKU配置:")
	for _, sku := range skus {
		fmt.Printf("  SKU %s: 当前库存%d, 仓库库存%d, 最小库存%d, 预期比例%.2f, 兼容货道%v\n",
			sku.ID, sku.CurrentStock, sku.WarehouseStock, sku.MinStock, sku.ExpectedRatio, sku.CompatibleLanes)
	}

	// 执行算法
	fmt.Println("\n开始执行甜品分拣补货算法...")
	results, err := algorithm.Execute()
	if err != nil {
		log.Fatalf("算法执行失败: %v", err)
	}

	// 打印结果
	algorithm.PrintResults(results)

	fmt.Println("\n算法执行完成!")
}
