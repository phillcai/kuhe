package main

import (
	"encoding/csv"
	"fmt"
	"os"
	"strconv"
)

// loadSKUFromCSV 从CSV文件加载SKU信息
func loadSKUFromCSV(filename string) ([]SKUInfo, error) {
	file, err := os.Open(filename)
	if err != nil {
		return nil, fmt.Errorf("打开文件失败: %v", err)
	}
	defer file.Close()

	reader := csv.NewReader(file)
	records, err := reader.ReadAll()
	if err != nil {
		return nil, fmt.Errorf("读取CSV失败: %v", err)
	}

	if len(records) < 2 {
		return nil, fmt.Errorf("CSV文件格式错误: 至少需要表头和数据行")
	}

	skus := make([]SKUInfo, 0)

	// 跳过表头，从第二行开始读取
	for i := 1; i < len(records); i++ {
		record := records[i]
		if len(record) < 2 {
			continue // 跳过空行或格式不正确的行
		}

		// 解析commodity_id
		commodityID, err := strconv.Atoi(record[0])
		if err != nil {
			fmt.Printf("警告: 跳过无效的commodity_id: %s\n", record[0])
			continue
		}

		// 解析qty
		qty, err := strconv.Atoi(record[1])
		if err != nil {
			fmt.Printf("警告: 跳过无效的qty: %s\n", record[1])
			continue
		}

		// 只添加库存大于0的SKU
		if qty > 0 {
			skus = append(skus, SKUInfo{
				ID:    commodityID,
				Stock: qty,
			})
		}
	}

	return skus, nil
}

// testWithRealData 使用真实数据测试
func testWithRealData() {
	fmt.Println("=== 使用真实库存数据测试 ===")
	fmt.Println()

	// 加载CSV数据
	skus, err := loadSKUFromCSV("ck 库存.csv")
	if err != nil {
		fmt.Printf("加载CSV数据失败: %v\n", err)
		return
	}

	if len(skus) == 0 {
		fmt.Println("错误: 没有有效的SKU数据")
		return
	}

	fmt.Printf("成功加载 %d 个SKU\n", len(skus))

	// 计算总库存
	totalStock := 0
	for _, sku := range skus {
		totalStock += sku.Stock
	}
	fmt.Printf("仓库总库存: %d\n", totalStock)
	fmt.Println()

	// 计算最小所需层数（每个SKU至少1个，需要1层）
	minLayers := len(skus)

	// 测试场景4: 固定目标分拣总量，使用足够的货架层数
	// targetTotal4 := 12 * 3 * 9
	// shelfLayers4 := 12 * 3 //小车

	targetTotal4 := 13 * 6 * 9
	shelfLayers4 := 13 * 6 //大车

	fmt.Println()
	fmt.Printf("--- 测试场景4: 固定目标分拣总量 = %d ---\n", targetTotal4)
	fmt.Printf("车辆货架层数: %d (最大容量: %d, 最小所需: %d)\n", shelfLayers4, 9*shelfLayers4, minLayers)
	fmt.Println()

	optimizer4 := NewCKPickingOptimizer(targetTotal4, shelfLayers4, skus)
	optimizer4.SetDebugMode(true)

	if err := optimizer4.Optimize(); err != nil {
		fmt.Printf("优化失败: %v\n", err)
	} else {
		optimizer4.PrintResults()
	}

	// 统计信息
	fmt.Println()
	fmt.Println("=== 统计信息 ===")
	fmt.Printf("SKU总数: %d\n", len(skus))
	fmt.Printf("仓库总库存: %d\n", totalStock)
	fmt.Printf("最小所需货架层数: %d (每个SKU至少1个)\n", minLayers)

	// 显示各SKU的库存占比
	fmt.Println("\n各SKU库存占比:")
	for _, sku := range skus {
		ratio := float64(sku.Stock) / float64(totalStock) * 100
		fmt.Printf("  SKU %d: 库存=%d, 占比=%.2f%%\n", sku.ID, sku.Stock, ratio)
	}
}

func main() {
	testWithRealData()
}
