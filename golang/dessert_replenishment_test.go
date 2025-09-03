package main

import (
	"encoding/csv"
	"encoding/json"
	"fmt"
	"os"
	"strconv"
	"strings"
	"testing"
)

// 解析CSV中特定req_id的数据结构体
type ReqTestData struct {
	ReqID                       string
	PointID                     string
	CarID                       string
	CommodityType               int
	PointMaxStock               int
	PointRemainStock            int
	PointRemainSKU              int
	PointValidShelfCnt          int
	CarSKUDetail                map[string]CarSKUInfo
	CommodityStockMap           map[string]CommodityStockInfo
	CommodityShelfAllocationMap map[string]CommodityShelfAllocation
}

// 车辆SKU信息
type CarSKUInfo struct {
	CommodityID int `json:"commodity_id"`
	Qty         int `json:"qty"`
}

// 商品库存信息
type CommodityStockInfo struct {
	CommodityID          int           `json:"commodity_id"`
	TotalAmount          int           `json:"total_amount"`
	TotalAvailableAmount int           `json:"total_available_amount"`
	ShelfCnt             int           `json:"shelf_cnt"`
	ShelfDetails         []ShelfDetail `json:"shelf_details"`
}

// 货架详情
type ShelfDetail struct {
	ShelfID         int    `json:"shelf_id"`
	CommodityID     int    `json:"commodity_id"`
	ShelfType       int    `json:"shelf_type"`
	ShelfTypes      string `json:"shelf_types"`
	ShelfMax        int    `json:"shelf_max"`
	Amount          int    `json:"amount"`
	AvailableAmount int    `json:"available_amount"`
}

// 商品货架分配信息
type CommodityShelfAllocation struct {
	CommodityID        int   `json:"commodity_id"`
	CommodityType      int   `json:"commodity_type"`
	CommodityShelfType int   `json:"commodity_shelf_type"`
	AvailableShelves   []int `json:"available_shelves"`
}

// 从CSV文件中解析特定req_id和commodity_type的数据
func parseReqTestData(reqID string, commodityType int) (*ReqTestData, error) {
	file, err := os.Open("../data/分拣饮料甜品 case.csv")
	if err != nil {
		return nil, fmt.Errorf("无法打开CSV文件: %v", err)
	}
	defer file.Close()

	reader := csv.NewReader(file)
	reader.LazyQuotes = true

	records, err := reader.ReadAll()
	if err != nil {
		return nil, fmt.Errorf("读取CSV文件失败: %v", err)
	}

	if len(records) < 2 {
		return nil, fmt.Errorf("CSV文件数据不足")
	}

	// 跳过标题行，查找指定的req_id和commodity_type
	var reqData *ReqTestData

	for _, record := range records[1:] {
		if len(record) < 26 {
			continue
		}

		// 同时匹配req_id和commodity_type
		recordCommodityType, _ := strconv.Atoi(record[6])
		if record[1] == reqID && recordCommodityType == commodityType { // req_id在第2列(索引1)，commodity_type在第7列(索引6)
			reqData = &ReqTestData{
				ReqID:   record[1],
				PointID: record[4],
				CarID:   record[5],
			}

			// 解析基本数据
			reqData.CommodityType, _ = strconv.Atoi(record[6])
			reqData.PointMaxStock, _ = strconv.Atoi(record[11])
			reqData.PointRemainStock, _ = strconv.Atoi(record[16])
			reqData.PointRemainSKU, _ = strconv.Atoi(record[17])
			reqData.PointValidShelfCnt, _ = strconv.Atoi(record[15])

			// 解析车辆SKU详情
			if err := json.Unmarshal([]byte(record[23]), &reqData.CarSKUDetail); err != nil {
				fmt.Printf("解析车辆SKU详情失败: %v\n", err)
			}

			// 解析货架分配信息
			var shelfAllocation map[string]interface{}
			if err := json.Unmarshal([]byte(record[24]), &shelfAllocation); err != nil {
				fmt.Printf("解析货架分配信息失败: %v\n", err)
			} else {
				if commodityStockMap, ok := shelfAllocation["CommodityStockMap"].(map[string]interface{}); ok {
					reqData.CommodityStockMap = make(map[string]CommodityStockInfo)
					for skuID, stockInfo := range commodityStockMap {
						if stockMap, ok := stockInfo.(map[string]interface{}); ok {
							var commodityInfo CommodityStockInfo
							if id, ok := stockMap["commodity_id"].(float64); ok {
								commodityInfo.CommodityID = int(id)
							}
							if amount, ok := stockMap["total_amount"].(float64); ok {
								commodityInfo.TotalAmount = int(amount)
							}
							if availAmount, ok := stockMap["total_available_amount"].(float64); ok {
								commodityInfo.TotalAvailableAmount = int(availAmount)
							}
							if shelfCnt, ok := stockMap["shelf_cnt"].(float64); ok {
								commodityInfo.ShelfCnt = int(shelfCnt)
							}

							// 解析货架详情
							if shelfDetails, ok := stockMap["shelf_details"].([]interface{}); ok {
								for _, shelfDetail := range shelfDetails {
									if shelf, ok := shelfDetail.(map[string]interface{}); ok {
										var detail ShelfDetail
										if shelfID, ok := shelf["shelf_id"].(float64); ok {
											detail.ShelfID = int(shelfID)
										}
										if commodityID, ok := shelf["commodity_id"].(float64); ok {
											detail.CommodityID = int(commodityID)
										}
										if shelfType, ok := shelf["shelf_type"].(float64); ok {
											detail.ShelfType = int(shelfType)
										}
										if shelfTypes, ok := shelf["shelf_types"].(string); ok {
											detail.ShelfTypes = shelfTypes
										}
										if shelfMax, ok := shelf["shelf_max"].(float64); ok {
											detail.ShelfMax = int(shelfMax)
										}
										if amount, ok := shelf["amount"].(float64); ok {
											detail.Amount = int(amount)
										}
										if availAmount, ok := shelf["available_amount"].(float64); ok {
											detail.AvailableAmount = int(availAmount)
										}
										commodityInfo.ShelfDetails = append(commodityInfo.ShelfDetails, detail)
									}
								}
							}
							reqData.CommodityStockMap[skuID] = commodityInfo
						}
					}
				}

				// 解析商品货架分配映射
				if commodityShelfAllocationMap, ok := shelfAllocation["CommodityShelfAllocationMap"].(map[string]interface{}); ok {
					reqData.CommodityShelfAllocationMap = make(map[string]CommodityShelfAllocation)
					for skuID, allocationInfo := range commodityShelfAllocationMap {
						if allocationMap, ok := allocationInfo.(map[string]interface{}); ok {
							var allocation CommodityShelfAllocation
							if id, ok := allocationMap["commodity_id"].(float64); ok {
								allocation.CommodityID = int(id)
							}
							if commodityType, ok := allocationMap["commodity_type"].(float64); ok {
								allocation.CommodityType = int(commodityType)
							}
							if shelfType, ok := allocationMap["commodity_shelf_type"].(float64); ok {
								allocation.CommodityShelfType = int(shelfType)
							}
							if shelves, ok := allocationMap["available_shelves"].([]interface{}); ok {
								for _, shelf := range shelves {
									if shelfID, ok := shelf.(float64); ok {
										allocation.AvailableShelves = append(allocation.AvailableShelves, int(shelfID))
									}
								}
							}
							reqData.CommodityShelfAllocationMap[skuID] = allocation
						}
					}
				}
			}
			break
		}
	}

	if reqData == nil {
		return nil, fmt.Errorf("未找到req_id为 %s 且commodity_type为 %d 的数据", reqID, commodityType)
	}

	return reqData, nil
}

// 将测试数据转换为算法所需的SKU和货道类型数据
func convertToAlgorithmData(reqData *ReqTestData) ([]DessertSKU, []LaneType) {
	var skus []DessertSKU
	laneTypeMap := make(map[int]int)              // 货道类型ID -> 使用次数
	physicalLanes := make(map[int][]int)          // 物理货道ID -> 支持的类型列表
	laneTypeShelves := make(map[int]map[int]bool) // 货道类型ID -> 支持该类型的货道ID集合

	// 计算总补货量，用于计算预期比例
	totalQty := 0
	for _, carSKU := range reqData.CarSKUDetail {
		totalQty += carSKU.Qty
	}

	// 从车辆SKU详情构建SKU数据
	for skuID, carSKU := range reqData.CarSKUDetail {
		// 根据补货量计算预期比例，确保总和为1
		expectedRatio := float64(carSKU.Qty) / float64(totalQty)

		sku := DessertSKU{
			ID:             skuID,
			WarehouseStock: carSKU.Qty,
			MinStock:       max(1, carSKU.Qty/10), // 设置最小库存为补货量的10%
			ExpectedRatio:  expectedRatio,         // 基于补货量的预期比例
			Importance:     1.0,                   // 默认重要性权重
		}

		// 从CommodityStockMap获取当前库存
		if stockInfo, exists := reqData.CommodityStockMap[skuID]; exists {
			sku.CurrentStock = stockInfo.TotalAvailableAmount

			// 计算实际占用货道数（统计有商品的货道数量）
			actualUsedLanes := 0
			for _, shelfDetail := range stockInfo.ShelfDetails {
				if shelfDetail.AvailableAmount > 0 {
					actualUsedLanes++
				}
			}
			sku.ActualUsedLanes = actualUsedLanes

			// 从货架详情中提取物理货道信息（用于货道类型映射）
			for _, shelfDetail := range stockInfo.ShelfDetails {
				shelfID := shelfDetail.ShelfID
				// 解析货道支持的类型字符串（用于物理货道映射）
				if shelfDetail.ShelfTypes != "" {
					shelfTypes := strings.Split(shelfDetail.ShelfTypes, ",")
					var supportedTypes []int
					for _, typeStr := range shelfTypes {
						if typeInt, err := strconv.Atoi(strings.TrimSpace(typeStr)); err == nil {
							supportedTypes = append(supportedTypes, typeInt)
						}
					}
					physicalLanes[shelfID] = supportedTypes
				}
			}
		} else {
			sku.CurrentStock = 0
		}

		// 从CommodityShelfAllocationMap获取兼容货道类型（权威来源）
		if allocation, exists := reqData.CommodityShelfAllocationMap[skuID]; exists {
			shelfType := allocation.CommodityShelfType
			sku.CompatibleLanes = []int{shelfType}
			laneTypeMap[shelfType]++

			// 为该货道类型记录可用的物理货道
			if laneTypeShelves[shelfType] == nil {
				laneTypeShelves[shelfType] = make(map[int]bool)
			}
			for _, shelfID := range allocation.AvailableShelves {
				laneTypeShelves[shelfType][shelfID] = true
			}
		} else {
			// 如果没有分配信息，设置默认值
			sku.CompatibleLanes = []int{19} // 默认兼容货道类型19
			laneTypeMap[19]++
			if laneTypeShelves[19] == nil {
				laneTypeShelves[19] = make(map[int]bool)
			}
		}

		skus = append(skus, sku)
	}

	// 构建货道类型数据
	// 重要：使用CSV中声明的有效货道数，而不是从实际使用的货道推算
	var laneTypes []LaneType
	totalDeclaredLanes := reqData.PointValidShelfCnt // 使用CSV中声明的有效货道数

	for laneTypeID := range laneTypeMap {
		// 对于共享货道系统，每种类型都可以使用所有声明的货道
		laneTypes = append(laneTypes, LaneType{
			ID:         laneTypeID,
			TotalLanes: totalDeclaredLanes, // 使用CSV声明的有效货道数
		})
	}

	// 如果没有任何货道类型（默认情况），设置默认货道类型
	if len(laneTypes) == 0 {
		laneTypes = append(laneTypes, LaneType{
			ID:         7,
			TotalLanes: max(2, totalDeclaredLanes), // 使用声明的货道数或最小值2
		})
	}

	return skus, laneTypes
}

// 打印甜品补货输入数据概览
func printDessertInputSummary(reqData *ReqTestData, skus []DessertSKU, laneTypes []LaneType) {
	totalWarehouse := 0
	totalCurrent := 0
	totalExpectedRatio := 0.0
	zeroStockCount := 0

	for _, sku := range skus {
		totalWarehouse += sku.WarehouseStock
		totalCurrent += sku.CurrentStock
		totalExpectedRatio += sku.ExpectedRatio
		if sku.WarehouseStock == 0 {
			zeroStockCount++
		}
	}

	fmt.Printf("=== 输入数据概览 (Req ID: %s) ===\n", reqData.ReqID)
	fmt.Printf("基本参数:\n")
	fmt.Printf("  Req ID: %s\n", reqData.ReqID)
	fmt.Printf("  点位ID: %s\n", reqData.PointID)
	fmt.Printf("  车辆ID: %s\n", reqData.CarID)
	fmt.Printf("  商品类型: %d\n", reqData.CommodityType)
	fmt.Printf("  点位最大库存: %d\n", reqData.PointMaxStock)
	fmt.Printf("  点位剩余库存: %d\n", reqData.PointRemainStock)
	fmt.Printf("  点位剩余SKU数: %d\n", reqData.PointRemainSKU)
	fmt.Printf("  有效货道数: %d\n", reqData.PointValidShelfCnt)

	fmt.Printf("\nSKU统计:\n")
	fmt.Printf("  SKU总数: %d\n", len(skus))
	fmt.Printf("  当前总库存: %d\n", totalCurrent)
	fmt.Printf("  仓库总库存: %d\n", totalWarehouse)
	fmt.Printf("  预期比例总和: %.6f\n", totalExpectedRatio)
	fmt.Printf("  零库存SKU数: %d\n", zeroStockCount)

	fmt.Printf("\n货道类型统计:\n")
	fmt.Printf("  货道类型数: %d\n", len(laneTypes))
	// 修复：在共享货道系统中，不应累加各类型货道数
	actualTotalLanes := 0
	if len(laneTypes) > 0 {
		actualTotalLanes = laneTypes[0].TotalLanes // 所有类型共享相同的物理货道
	}
	for _, laneType := range laneTypes {
		fmt.Printf("  类型%d: %d条货道\n", laneType.ID, laneType.TotalLanes)
	}
	fmt.Printf("  总货道数: %d\n", actualTotalLanes)

	if zeroStockCount > 0 {
		fmt.Printf("⚠️  注意：有 %d 个SKU仓库库存为0，无法补货\n", zeroStockCount)
	}

	// 打印详细SKU信息
	fmt.Printf("\n=== SKU详细信息 ===\n")
	fmt.Printf("%-15s %-12s %-10s %-10s %-10s %-12s %-15s\n",
		"SKU_ID", "仓库库存", "当前库存", "最小库存", "预期比例", "重要性", "兼容货道")
	fmt.Printf("%s\n", strings.Repeat("-", 90))

	for _, sku := range skus {
		compatibleLanesStr := ""
		for i, lane := range sku.CompatibleLanes {
			if i > 0 {
				compatibleLanesStr += ","
			}
			compatibleLanesStr += fmt.Sprintf("%d", lane)
		}

		fmt.Printf("%-15s %-12d %-10d %-10d %-10.6f %-12.2f %-15s\n",
			sku.ID,
			sku.WarehouseStock,
			sku.CurrentStock,
			sku.MinStock,
			sku.ExpectedRatio,
			sku.Importance,
			compatibleLanesStr)
	}
	fmt.Printf("%s\n", strings.Repeat("-", 90))
}

// 分析甜品补货算法结果
func analyzeDessertResults(results []DessertAllocationResult, skus []DessertSKU, laneTypes []LaneType) {
	totalReplenish := 0
	totalFinalStock := 0
	totalAllocatedLanes := 0
	maxRatioDeviation := 0.0
	totalRatioDeviation := 0.0
	zeroReplenishCount := 0

	// 创建SKU映射
	skuMap := make(map[string]DessertSKU)
	for _, sku := range skus {
		skuMap[sku.ID] = sku
	}

	// 计算总货道数（修复：使用共享货道逻辑）
	totalLanes := 0
	if len(laneTypes) > 0 {
		totalLanes = laneTypes[0].TotalLanes // 所有类型共享相同的物理货道
	}

	fmt.Printf("\n=== 算法执行结果分析 ===\n")
	fmt.Printf("%-15s %-10s %-10s %-10s %-10s %-10s %-12s %-12s %-10s %-12s\n",
		"SKU_ID", "仓库库存", "当前库存", "补货量", "最终库存", "分配货道", "实际比例", "预期比例", "比例偏差", "偏差率")
	fmt.Printf("%s\n", strings.Repeat("-", 125))

	// 计算实际比例
	totalFinalForRatio := 0
	for _, result := range results {
		totalFinalForRatio += result.FinalStock
	}

	for _, result := range results {
		sku := skuMap[result.SKUID]
		actualRatio := 0.0
		if totalFinalForRatio > 0 {
			actualRatio = float64(result.FinalStock) / float64(totalFinalForRatio)
		}

		ratioDeviation := 0.0
		deviationRate := 0.0
		if sku.ExpectedRatio > 0 {
			ratioDeviation = actualRatio - sku.ExpectedRatio
			if ratioDeviation < 0 {
				ratioDeviation = -ratioDeviation
			}
			deviationRate = ratioDeviation / sku.ExpectedRatio * 100
		}

		fmt.Printf("%-15s %-10d %-10d %-10d %-10d %-10d %-12.6f %-12.6f %-10.6f %-12.1f%%\n",
			result.SKUID,
			sku.WarehouseStock,
			sku.CurrentStock,
			result.ReplenishmentQty,
			result.FinalStock,
			result.AllocatedLanes,
			actualRatio,
			sku.ExpectedRatio,
			ratioDeviation,
			deviationRate)

		totalReplenish += result.ReplenishmentQty
		totalFinalStock += result.FinalStock
		totalAllocatedLanes += result.AllocatedLanes
		totalRatioDeviation += ratioDeviation
		if ratioDeviation > maxRatioDeviation {
			maxRatioDeviation = ratioDeviation
		}
		if result.ReplenishmentQty == 0 {
			zeroReplenishCount++
		}
	}

	fmt.Printf("%s\n", strings.Repeat("-", 125))
	avgRatioDeviation := totalRatioDeviation / float64(len(results))

	fmt.Printf("\n统计指标:\n")
	fmt.Printf("  总补货量: %d\n", totalReplenish)
	fmt.Printf("  最终总库存: %d\n", totalFinalStock)
	fmt.Printf("  总分配货道数: %d / %d\n", totalAllocatedLanes, totalLanes)
	fmt.Printf("  货道利用率: %.2f%%\n", float64(totalAllocatedLanes)/float64(totalLanes)*100)
	fmt.Printf("  最大比例偏差: %.6f\n", maxRatioDeviation)
	fmt.Printf("  平均比例偏差: %.6f\n", avgRatioDeviation)
	fmt.Printf("  零补货SKU数: %d\n", zeroReplenishCount)

	// 评估算法表现
	if avgRatioDeviation < 0.01 {
		fmt.Printf("✅ 比例精度优秀 (平均偏差 < 1%%)\n")
	} else if avgRatioDeviation < 0.02 {
		fmt.Printf("✅ 比例精度良好 (平均偏差 < 2%%)\n")
	} else {
		fmt.Printf("⚠️  比例精度一般 (平均偏差 %.1f%%)\n", avgRatioDeviation*100)
	}

	if float64(totalAllocatedLanes)/float64(totalLanes) > 0.8 {
		fmt.Printf("✅ 货道利用率良好\n")
	} else if float64(totalAllocatedLanes)/float64(totalLanes) > 0.6 {
		fmt.Printf("⚠️  货道利用率中等\n")
	} else {
		fmt.Printf("❌ 货道利用率偏低\n")
	}
}

// 甜品补货约束验证
func validateDessertConstraints(results []DessertAllocationResult, skus []DessertSKU, laneTypes []LaneType) {
	skuMap := make(map[string]DessertSKU)
	for _, sku := range skus {
		skuMap[sku.ID] = sku
	}

	// 统计每种货道类型的使用情况
	laneUsage := make(map[int]int)
	for _, laneType := range laneTypes {
		laneUsage[laneType.ID] = 0
	}

	violations := 0
	totalFinal := 0

	fmt.Printf("\n=== 约束验证 ===\n")

	for _, result := range results {
		sku := skuMap[result.SKUID]
		totalFinal += result.FinalStock

		// 检查仓库库存约束
		if result.ReplenishmentQty > sku.WarehouseStock {
			fmt.Printf("❌ SKU %s: 补货量(%d) > 仓库库存(%d)\n",
				result.SKUID, result.ReplenishmentQty, sku.WarehouseStock)
			violations++
		}

		// 检查最小库存约束
		if result.FinalStock < sku.MinStock {
			fmt.Printf("⚠️  SKU %s: 最终库存(%d) < 最小库存(%d)\n",
				result.SKUID, result.FinalStock, sku.MinStock)
		}

		// 检查负补货约束
		if result.ReplenishmentQty < 0 {
			fmt.Printf("❌ SKU %s: 补货量为负(%d)\n",
				result.SKUID, result.ReplenishmentQty)
			violations++
		}

		// 检查分配的货道数为负
		if result.AllocatedLanes < 0 {
			fmt.Printf("❌ SKU %s: 分配货道数为负(%d)\n",
				result.SKUID, result.AllocatedLanes)
			violations++
		}

		// 统计物理货道使用（新的正确逻辑）
		// 不再按货道类型统计，而是按总的物理货道使用量统计
		// 注意：这里不做类型分配统计，因为类型是共享的
	}

	// 检查总物理货道分配约束
	totalAllocatedLanes := 0
	for _, result := range results {
		totalAllocatedLanes += result.AllocatedLanes
	}

	// 计算总的可用物理货道数（避免重复计算共享货道）
	totalAvailablePhysicalLanes := 0
	if len(laneTypes) > 0 {
		// 所有类型共享相同的物理货道，所以取任意一个类型的总数就是物理货道数
		totalAvailablePhysicalLanes = laneTypes[0].TotalLanes
	}

	if totalAllocatedLanes > totalAvailablePhysicalLanes {
		fmt.Printf("❌ 总货道分配: 使用数量(%d) > 可用物理货道数(%d)\n",
			totalAllocatedLanes, totalAvailablePhysicalLanes)
		violations++
	} else {
		fmt.Printf("✅ 货道分配合理: 使用数量(%d) <= 可用物理货道数(%d)\n",
			totalAllocatedLanes, totalAvailablePhysicalLanes)
	}

	if violations == 0 {
		fmt.Printf("✅ 所有强约束均满足\n")
	} else {
		fmt.Printf("❌ 发现 %d 个约束违反\n", violations)
	}

	fmt.Printf("总库存验证: %d\n", totalFinal)
}

// 测试特定req_id的甜品补货算法
func TestDessertReplenishmentWithSpecificReqID(t *testing.T) {
	reqID := "132e5889c453b6f4" // 可以修改这个值来测试不同的req_id
	commodityType := 6          // 可以修改这个值来测试不同的商品类型：5=饮料，6=甜品

	fmt.Printf("=== 甜品补货算法测试 (Req ID: %s, Commodity Type: %d) ===\n\n", reqID, commodityType)

	// 1. 解析CSV数据
	reqData, err := parseReqTestData(reqID, commodityType)
	if err != nil {
		t.Fatalf("解析req_id %s 的数据失败: %v", reqID, err)
	}

	// 2. 转换为算法数据
	skus, laneTypes := convertToAlgorithmData(reqData)

	if len(skus) == 0 {
		t.Fatalf("无法提取到有效的SKU数据")
	}

	// 3. 打印输入数据概览
	printDessertInputSummary(reqData, skus, laneTypes)

	// 4. 创建和初始化算法实例
	fmt.Printf("\n=== 执行补货算法 ===\n")
	algorithm := NewDessertReplenishmentAlgorithm()

	err = algorithm.Initialize(skus, laneTypes)
	if err != nil {
		fmt.Printf("❌ 算法初始化失败: %v\n", err)
		t.Fatalf("算法初始化失败: %v", err)
	}

	// 5. 执行算法
	results, err := algorithm.Execute()
	if err != nil {
		fmt.Printf("❌ 算法执行失败: %v\n", err)
		t.Fatalf("算法执行失败: %v", err)
	}

	// 6. 验证结果
	if len(results) == 0 {
		fmt.Printf("⚠️  算法结果为空\n")
		t.Error("算法结果为空")
		return
	}

	fmt.Printf("✅ 算法执行成功，生成了 %d 个SKU的分配结果\n", len(results))

	// 7. 打印算法默认结果
	fmt.Printf("\n=== 算法默认输出 ===\n")
	algorithm.PrintResults(results)

	// 8. 详细分析结果
	analyzeDessertResults(results, skus, laneTypes)

	// 9. 约束验证
	validateDessertConstraints(results, skus, laneTypes)

	// 10. 基本约束检查（用于测试断言）
	totalAllocatedLanes := 0
	totalReplenishment := 0

	for _, result := range results {
		totalAllocatedLanes += result.AllocatedLanes
		totalReplenishment += result.ReplenishmentQty

		if result.FinalStock < 0 {
			t.Errorf("SKU %s 最终库存为负: %d", result.SKUID, result.FinalStock)
		}

		if result.AllocatedLanes < 0 {
			t.Errorf("SKU %s 分配的货道数为负: %d", result.SKUID, result.AllocatedLanes)
		}
	}

	// 计算总货道数（修复：使用共享货道逻辑）
	totalLanes := 0
	if len(laneTypes) > 0 {
		totalLanes = laneTypes[0].TotalLanes // 所有类型共享相同的物理货道
	}

	if totalAllocatedLanes > totalLanes {
		t.Errorf("分配的货道数(%d)超过总货道数(%d)", totalAllocatedLanes, totalLanes)
	}

	fmt.Printf("\n🎉 测试执行完成！\n")
	fmt.Printf("总分配货道数: %d/%d (利用率: %.2f%%)\n",
		totalAllocatedLanes, totalLanes, float64(totalAllocatedLanes)/float64(totalLanes)*100)
	fmt.Printf("总补货量: %d\n", totalReplenishment)
}

// 支持通过参数指定req_id的测试函数
func TestDessertReplenishmentWithReqID(t *testing.T) {
	testCases := []string{
		"132e5889c453b6f4",
		"76c2665c3f25b62a",
		"1891d2d0136aa93b",
		"5994de1da3acd6f3",
	}

	for _, reqID := range testCases {
		t.Run(fmt.Sprintf("ReqID_%s", reqID), func(t *testing.T) {
			testSpecificReqID(t, reqID)
		})
	}
}

// 测试特定req_id的辅助函数
func testSpecificReqID(t *testing.T, reqID string) {
	testSpecificReqIDWithType(t, reqID, 6) // 默认测试甜品类型
}

// 测试特定req_id和commodity_type的辅助函数
func testSpecificReqIDWithType(t *testing.T, reqID string, commodityType int) {
	// 解析CSV数据
	reqData, err := parseReqTestData(reqID, commodityType)
	if err != nil {
		t.Skipf("跳过req_id %s: %v", reqID, err)
		return
	}

	// 只测试甜品(6)和饮料(5)
	if reqData.CommodityType != 5 && reqData.CommodityType != 6 {
		t.Skipf("跳过req_id %s: 商品类型不是甜品或饮料 (type=%d)", reqID, reqData.CommodityType)
		return
	}

	fmt.Printf("\n=== 甜品补货算法测试 (Req ID: %s, Commodity Type: %d) ===\n", reqID, commodityType)

	// 转换为算法数据
	skus, laneTypes := convertToAlgorithmData(reqData)

	if len(skus) == 0 {
		t.Skipf("跳过req_id %s: 没有SKU数据", reqID)
		return
	}

	// 打印简化的输入数据概览
	fmt.Printf("基本信息: 点位ID=%s, 车辆ID=%s, 商品类型=%d\n",
		reqData.PointID, reqData.CarID, reqData.CommodityType)
	fmt.Printf("数据概览: %d个SKU, %d种货道类型\n", len(skus), len(laneTypes))

	// 创建算法实例
	algorithm := NewDessertReplenishmentAlgorithm()

	// 初始化算法
	err = algorithm.Initialize(skus, laneTypes)
	if err != nil {
		fmt.Printf("❌ req_id %s 算法初始化失败: %v\n", reqID, err)
		t.Errorf("req_id %s 算法初始化失败: %v", reqID, err)
		return
	}

	// 执行算法
	results, err := algorithm.Execute()
	if err != nil {
		fmt.Printf("❌ req_id %s 算法执行失败: %v\n", reqID, err)
		t.Errorf("req_id %s 算法执行失败: %v", reqID, err)
		return
	}

	// 验证结果
	if len(results) > 0 {
		fmt.Printf("✅ req_id %s 测试通过，生成了 %d 个分配结果\n", reqID, len(results))

		// 计算简要统计
		totalReplenish := 0
		totalAllocatedLanes := 0
		for _, result := range results {
			totalReplenish += result.ReplenishmentQty
			totalAllocatedLanes += result.AllocatedLanes
		}

		// 计算总货道数（修复：使用共享货道逻辑）
		totalLanes := 0
		if len(laneTypes) > 0 {
			totalLanes = laneTypes[0].TotalLanes // 所有类型共享相同的物理货道
		}

		fmt.Printf("   补货量: %d, 分配货道: %d/%d (利用率: %.1f%%)\n",
			totalReplenish, totalAllocatedLanes, totalLanes,
			float64(totalAllocatedLanes)/float64(totalLanes)*100)
	} else {
		fmt.Printf("⚠️  req_id %s 生成结果为空\n", reqID)
	}
}

// 辅助函数（已在其他文件中定义，这里注释掉避免重复声明）
// func max(a, b int) int {
// 	if a > b {
// 		return a
// 	}
// 	return b
// }
//
// func min(a, b int) int {
// 	if a < b {
// 		return a
// 	}
// 	return b
// }

// 便捷函数：测试任意req_id的甜品补货算法
// 使用方法：go test dessert_replenishment.go dessert_replenishment_test.go -v -run TestCustomReqID
// 然后修改下面的reqID和commodityType变量为您想要测试的用例
func TestCustomReqID(t *testing.T) {
	// ⚠️ 修改这里的req_id和commodity_type来测试不同的用例
	reqID := "132e5889c453b6f4"
	commodityType := 6 // 5=饮料，6=甜品

	fmt.Printf("🧪 自定义详细测试 req_id: %s, commodity_type: %d\n", reqID, commodityType)

	// 解析CSV数据
	reqData, err := parseReqTestData(reqID, commodityType)
	if err != nil {
		t.Fatalf("解析req_id %s 的数据失败: %v", reqID, err)
	}

	// 转换为算法数据
	skus, laneTypes := convertToAlgorithmData(reqData)

	if len(skus) == 0 {
		t.Fatalf("无法提取到有效的SKU数据")
	}

	// 打印详细输入数据概览
	printDessertInputSummary(reqData, skus, laneTypes)

	// 创建和初始化算法实例
	fmt.Printf("\n=== 执行补货算法 ===\n")
	algorithm := NewDessertReplenishmentAlgorithm()

	err = algorithm.Initialize(skus, laneTypes)
	if err != nil {
		t.Fatalf("算法初始化失败: %v", err)
	}

	// 执行算法
	results, err := algorithm.Execute()
	if err != nil {
		t.Fatalf("算法执行失败: %v", err)
	}

	// 验证结果
	if len(results) == 0 {
		t.Error("算法结果为空")
		return
	}

	// 打印算法默认结果
	fmt.Printf("\n=== 算法默认输出 ===\n")
	algorithm.PrintResults(results)

	// 详细分析结果
	analyzeDessertResults(results, skus, laneTypes)

	// 约束验证
	validateDessertConstraints(results, skus, laneTypes)

	fmt.Printf("\n🎉 自定义测试完成！\n")
}

// 参数化测试：通过环境变量传入req_id和commodity_type
// 使用方法：export TEST_REQ_ID="132e5889c453b6f4" TEST_COMMODITY_TYPE="6" && go test -v -run TestParameterizedReqID
func TestParameterizedReqID(t *testing.T) {
	// 从环境变量中获取req_id
	reqID := os.Getenv("TEST_REQ_ID")
	commodityTypeStr := os.Getenv("TEST_COMMODITY_TYPE")

	if reqID == "" {
		t.Skip("跳过参数化测试：未设置环境变量 TEST_REQ_ID")
		return
	}

	commodityType := 6 // 默认为甜品
	if commodityTypeStr != "" {
		if ct, err := strconv.Atoi(commodityTypeStr); err == nil {
			commodityType = ct
		}
	}

	fmt.Printf("🧪 参数化详细测试 req_id: %s, commodity_type: %d\n", reqID, commodityType)
	fmt.Printf("通过环境变量 TEST_REQ_ID 和 TEST_COMMODITY_TYPE 传入\n")

	// 解析CSV数据
	reqData, err := parseReqTestData(reqID, commodityType)
	if err != nil {
		t.Fatalf("解析req_id %s 的数据失败: %v", reqID, err)
	}

	// 转换为算法数据
	skus, laneTypes := convertToAlgorithmData(reqData)

	if len(skus) == 0 {
		t.Fatalf("无法提取到有效的SKU数据")
	}

	// 打印详细输入数据概览
	printDessertInputSummary(reqData, skus, laneTypes)

	// 创建和初始化算法实例
	fmt.Printf("\n=== 执行补货算法 ===\n")
	algorithm := NewDessertReplenishmentAlgorithm()

	err = algorithm.Initialize(skus, laneTypes)
	if err != nil {
		t.Fatalf("算法初始化失败: %v", err)
	}

	// 执行算法
	results, err := algorithm.Execute()
	if err != nil {
		t.Fatalf("算法执行失败: %v", err)
	}

	// 验证结果
	if len(results) == 0 {
		t.Error("算法结果为空")
		return
	}

	// 打印算法默认结果
	fmt.Printf("\n=== 算法默认输出 ===\n")
	algorithm.PrintResults(results)

	// 详细分析结果
	analyzeDessertResults(results, skus, laneTypes)

	// 约束验证
	validateDessertConstraints(results, skus, laneTypes)

	fmt.Printf("\n🎉 参数化测试完成！\n")
}

// 批量测试函数：一次性测试多个req_id和commodity_type组合
func TestBatchReqIDs(t *testing.T) {
	// 定义测试用例：{req_id, commodity_type, description}
	type TestCase struct {
		ReqID         string
		CommodityType int
		Description   string
	}

	batchTestCases := []TestCase{
		{"132e5889c453b6f4", 6, "甜品"},
		{"132e5889c453b6f4", 5, "饮料"},
		{"76c2665c3f25b62a", 6, "甜品"},
		{"1891d2d0136aa93b", 6, "甜品"},
		{"5994de1da3acd6f3", 6, "甜品"},
		// 添加更多测试用例在这里...
	}

	fmt.Printf("🔄 批量测试开始：测试 %d 个用例\n", len(batchTestCases))
	fmt.Printf("%s\n", strings.Repeat("=", 80))

	successCount := 0
	failCount := 0
	skipCount := 0

	for i, testCase := range batchTestCases {
		fmt.Printf("\n[%d/%d] 测试 req_id: %s, commodity_type: %d (%s)\n",
			i+1, len(batchTestCases), testCase.ReqID, testCase.CommodityType, testCase.Description)

		t.Run(fmt.Sprintf("BatchTest_%s_%d", testCase.ReqID, testCase.CommodityType), func(t *testing.T) {
			initialFailedFlag := t.Failed()

			testSpecificReqIDWithType(t, testCase.ReqID, testCase.CommodityType)

			if t.Skipped() {
				skipCount++
				fmt.Printf("⏭️  跳过: %s_%d\n", testCase.ReqID, testCase.CommodityType)
			} else if t.Failed() && !initialFailedFlag {
				failCount++
				fmt.Printf("❌ 失败: %s_%d\n", testCase.ReqID, testCase.CommodityType)
			} else {
				successCount++
				fmt.Printf("✅ 成功: %s_%d\n", testCase.ReqID, testCase.CommodityType)
			}
		})
	}

	fmt.Printf("\n%s\n", strings.Repeat("=", 80))
	fmt.Printf("🏁 批量测试完成统计:\n")
	fmt.Printf("   总数: %d\n", len(batchTestCases))
	fmt.Printf("   成功: %d (%.1f%%)\n", successCount, float64(successCount)/float64(len(batchTestCases))*100)
	fmt.Printf("   失败: %d (%.1f%%)\n", failCount, float64(failCount)/float64(len(batchTestCases))*100)
	fmt.Printf("   跳过: %d (%.1f%%)\n", skipCount, float64(skipCount)/float64(len(batchTestCases))*100)

	if successCount == len(batchTestCases) {
		fmt.Printf("🎉 所有测试都成功通过！\n")
	} else if successCount > 0 {
		fmt.Printf("⚠️  部分测试通过，请检查失败的测试用例\n")
	} else {
		fmt.Printf("💥 所有测试都失败了，请检查算法实现\n")
	}
}
