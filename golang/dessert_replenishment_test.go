package main

import (
	"encoding/csv"
	"encoding/json"
	"fmt"
	"math"
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
	ShelfList                   []ShelfDetail // 添加ShelfList字段，包含初始货道占用信息
	DebugData                   *DebugDataInfo
}

// Debug数据结构体
type DebugDataInfo struct {
	Products []DebugProduct `json:"products"`
}

// Debug数据中的商品信息
type DebugProduct struct {
	ID                string  `json:"ID"`
	Name              string  `json:"Name"`
	WarehouseStock    int     `json:"WarehouseStock"`
	CurrentStock      int     `json:"CurrentStock"`
	MaxAllowed        int     `json:"MaxAllowed"`
	ExpectedRatio     float64 `json:"ExpectedRatio"`
	PointForecastSale int     `json:"PointForecastSale"` // 点位预测销售量
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

				// 解析ShelfList
				if shelfList, ok := shelfAllocation["ShelfList"].([]interface{}); ok {
					for _, shelfItem := range shelfList {
						if shelf, ok := shelfItem.(map[string]interface{}); ok {
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
							reqData.ShelfList = append(reqData.ShelfList, detail)
						}
					}
				}
			}

			// 解析debug_data (第27列，索引26)
			if len(record) > 26 && record[26] != "" {
				// 获取point_forecast_sale值 (第13列，索引12)
				pointForecastSale := 0
				if len(record) > 12 && record[12] != "" {
					if val, err := strconv.Atoi(record[12]); err == nil {
						pointForecastSale = val
					}
				}

				// 解析debug_data JSON
				var debugDataRaw map[string]interface{}
				if err := json.Unmarshal([]byte(record[26]), &debugDataRaw); err != nil {
					fmt.Printf("解析debug_data失败: %v\n", err)
				} else {
					// 从 isNeedReplenishment 中获取 pointForecastSale
					if isNeedReplenishment, exists := debugDataRaw["isNeedReplenishment"]; exists {
						if replenishmentMap, ok := isNeedReplenishment.(map[string]interface{}); ok {
							if pfs, exists := replenishmentMap["pointForecastSale"]; exists {
								if pfsFloat, ok := pfs.(float64); ok {
									pointForecastSale = int(pfsFloat)
								}
							}
						}
					}

					// 解析 products 数组
					var debugData DebugDataInfo
					if productsData, exists := debugDataRaw["products"]; exists {
						if productsBytes, err := json.Marshal(productsData); err == nil {
							if err := json.Unmarshal(productsBytes, &debugData.Products); err == nil {
								// 为每个产品添加PointForecastSale字段
								for i := range debugData.Products {
									debugData.Products[i].PointForecastSale = pointForecastSale
								}
							}
						}
					}

					reqData.DebugData = &debugData
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
func convertToAlgorithmData(reqData *ReqTestData) ([]DessertSKU, []LaneType, []PhysicalLane) {
	var skus []DessertSKU
	laneTypeMap := make(map[int]int)              // 货道类型ID -> 使用次数
	physicalLanes := make(map[int][]int)          // 物理货道ID -> 支持的类型列表
	laneTypeShelves := make(map[int]map[int]bool) // 货道类型ID -> 支持该类型的货道ID集合

	// 创建ExpectedRatio映射表，从debug_data直接获取（无需归一化）
	expectedRatioMap := make(map[string]float64)

	if reqData.DebugData != nil && len(reqData.DebugData.Products) > 0 {
		// 直接使用debug_data中的ExpectedRatio值，无需归一化
		for _, product := range reqData.DebugData.Products {
			expectedRatioMap[product.ID] = product.ExpectedRatio
		}
	}

	// 从CommodityShelfAllocationMap构建SKU数据，确保覆盖所有应分拣的SKU
	for skuID, allocation := range reqData.CommodityShelfAllocationMap {
		var warehouseStock int
		var expectedRatio float64

		// 从CarSKUDetail获取车上库存量，如果不存在则为0
		if carSKU, exists := reqData.CarSKUDetail[skuID]; exists {
			warehouseStock = carSKU.Qty
		} else {
			// 车上没有该SKU的库存，设置为0
			warehouseStock = 0
		}

		// 从debug_data获取归一化后的ExpectedRatio和点位预测销售量
		var pointForecastSale int
		if ratio, exists := expectedRatioMap[skuID]; exists {
			expectedRatio = ratio
		} else {
			// 如果debug_data中没有该SKU的比例信息，设置为0
			expectedRatio = 0.0
		}

		// 从debug_data获取点位预测销售量
		if reqData.DebugData != nil {
			for _, product := range reqData.DebugData.Products {
				if product.ID == skuID {
					pointForecastSale = product.PointForecastSale
					break
				}
			}
		}

		// 计算最小库存：point_forecast_sale * sku的预期比例向上取整，然后和车上库存+点位库存取小值
		var minStock int
		if pointForecastSale > 0 && expectedRatio > 0 {
			// 计算基于预测销售量和预期比例的最小库存
			forecastBasedMinStock := int(math.Ceil(float64(pointForecastSale) * expectedRatio))

			// 获取当前点位库存
			currentStock := 0
			if stockInfo, exists := reqData.CommodityStockMap[skuID]; exists {
				currentStock = stockInfo.TotalAvailableAmount
			}

			// 和车上库存+点位库存取小值
			totalAvailableStock := warehouseStock + currentStock
			minStock = min(forecastBasedMinStock, totalAvailableStock)

			// 日志记录：使用新的最小库存计算方式
			// fmt.Printf("🔄 SKU %s 新最小库存计算: 预测销售=%d, 预期比例=%.3f, 基于预测最小库存=%d, 可用库存=%d, 最终最小库存=%d\n",
			//	skuID, pointForecastSale, expectedRatio, forecastBasedMinStock, totalAvailableStock, minStock)
		} else {

			minStock = 0 // 车上没有库存的SKU，最小库存设为0

			// 日志记录：使用传统最小库存计算方式
			fmt.Printf("🔄 SKU %s 使用传统最小库存计算: 车上库存=%d, 最终最小库存=%d (预测销售=%d, 预期比例=%.3f)\n",
				skuID, warehouseStock, minStock, pointForecastSale, expectedRatio)
		}

		sku := DessertSKU{
			ID:             skuID,
			WarehouseStock: warehouseStock,
			MinStock:       minStock,
			ExpectedRatio:  expectedRatio, // 基于补货量的预期比例
			Importance:     1.0,           // 默认重要性权重
			InitialLanes:   0,             // 初始为0，稍后从实际占用货道数计算
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
			sku.InitialLanes = actualUsedLanes // 设置初始货道数等于当前实际占用的货道数
			// 设置实际占用货道数

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

		// 直接使用循环中的allocation获取兼容货道类型
		shelfType := allocation.CommodityShelfType
		sku.CompatibleLanes = []int{shelfType}
		laneTypeMap[shelfType]++

		// 为该货道类型记录可用的物理货道
		if laneTypeShelves[shelfType] == nil {
			laneTypeShelves[shelfType] = make(map[int]bool)
		}
		for _, shelfID := range allocation.AvailableShelves {
			laneTypeShelves[shelfType][shelfID] = true

			// 确保所有可用货架都在physicalLanes中
			if _, exists := physicalLanes[shelfID]; !exists {
				physicalLanes[shelfID] = []int{shelfType}
			} else {
				// 检查是否已包含此货道类型
				found := false
				for _, existingType := range physicalLanes[shelfID] {
					if existingType == shelfType {
						found = true
						break
					}
				}
				if !found {
					physicalLanes[shelfID] = append(physicalLanes[shelfID], shelfType)
				}
			}
		}
		// 确保physicalLanes包含所有可用货架

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

	// 将map[int][]int转换为[]PhysicalLane，并处理初始化时被占用的货道
	var physicalLanesList []PhysicalLane
	for shelfID, supportedTypes := range physicalLanes {
		physicalLanesList = append(physicalLanesList, PhysicalLane{
			ID:               shelfID,
			SupportedTypes:   supportedTypes,
			CommodityID:      0, // 初始未占用
			Quantity:         0, // 初始数量为0
			ReplenishmentQty: 0, // 初始补货量为0
		})
	}

	// 处理初始化时被占用的货道
	// 使用CSV中shelf_allocation_before字段的ShelfList数据
	for _, shelfDetail := range reqData.ShelfList {
		if shelfDetail.Amount > 0 { // amount > 0 表示货道被占用
			// 在physicalLanesList中找到对应的货道并设置占用信息
			for i := range physicalLanesList {
				if physicalLanesList[i].ID == shelfDetail.ShelfID {
					physicalLanesList[i].CommodityID = shelfDetail.CommodityID
					physicalLanesList[i].Quantity = shelfDetail.Amount
					physicalLanesList[i].ReplenishmentQty = 0 // 初始补货量为0
					break
				}
			}
		}
	}

	return skus, laneTypes, physicalLanesList
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
	fmt.Printf("%-15s %-12s %-10s %-10s %-10s %-10s %-12s %-15s\n",
		"SKU_ID", "仓库库存", "当前库存", "最小库存", "初始货道", "预期比例", "重要性", "兼容货道")
	fmt.Printf("%s\n", strings.Repeat("-", 100))

	for _, sku := range skus {
		compatibleLanesStr := ""
		for i, lane := range sku.CompatibleLanes {
			if i > 0 {
				compatibleLanesStr += ","
			}
			compatibleLanesStr += fmt.Sprintf("%d", lane)
		}

		fmt.Printf("%-15s %-12d %-10d %-10d %-10d %-10.6f %-12.2f %-15s\n",
			sku.ID,
			sku.WarehouseStock,
			sku.CurrentStock,
			sku.MinStock,
			sku.InitialLanes,
			sku.ExpectedRatio,
			sku.Importance,
			compatibleLanesStr)
	}
	fmt.Printf("%s\n", strings.Repeat("-", 100))
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
	} else {
		fmt.Printf("⚠️  货道利用率有待提升 (%.1f%%)\n", float64(totalAllocatedLanes)/float64(totalLanes)*100)
	}

	// 打印详细的货道利用率分析
	printDetailedLaneUtilizationAnalysis(results, totalLanes)
}

// 打印详细的货道利用率分析
func printDetailedLaneUtilizationAnalysis(results []DessertAllocationResult, totalLanes int) {
	fmt.Printf("\n=== 详细货道利用率分析 ===\n")

	// 计算已分配货道数
	allocatedLanes := 0
	for _, result := range results {
		allocatedLanes += result.AllocatedLanes
	}

	// 计算利用率
	utilizationRate := 0.0
	if totalLanes > 0 {
		utilizationRate = float64(allocatedLanes) / float64(totalLanes) * 100
	}

	fmt.Printf("总货道数: %d\n", totalLanes)
	fmt.Printf("已分配货道数: %d\n", allocatedLanes)
	fmt.Printf("空闲货道数: %d\n", totalLanes-allocatedLanes)
	fmt.Printf("货道利用率: %.2f%%\n", utilizationRate)

	// 分析每个SKU的货道分配情况
	fmt.Printf("\n=== SKU货道分配详情 ===\n")
	fmt.Printf("%-15s %-10s %-15s %-15s\n", "SKU_ID", "分配货道数", "货道利用率", "补货量")
	fmt.Printf("%s\n", strings.Repeat("-", 55))

	for _, result := range results {
		skuUtilization := 0.0
		if totalLanes > 0 {
			skuUtilization = float64(result.AllocatedLanes) / float64(totalLanes) * 100
		}
		fmt.Printf("%-15s %-10d %-15.2f%% %-15d\n",
			result.SKUID, result.AllocatedLanes, skuUtilization, result.ReplenishmentQty)
	}

	// 优化建议
	fmt.Printf("\n=== 优化建议 ===\n")
	if utilizationRate < 80.0 {
		fmt.Printf("⚠️  货道利用率较低 (%.1f%%)，建议：\n", utilizationRate)
		fmt.Printf("   1. 检查是否有SKU可以分配到更多货道\n")
		fmt.Printf("   2. 优化SKU的货道类型兼容性\n")
		fmt.Printf("   3. 调整SKU的预期比例和重要性权重\n")
	} else {
		fmt.Printf("✅ 货道利用率良好 (%.1f%%)\n", utilizationRate)
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
	skus, laneTypes, physicalLanes := convertToAlgorithmData(reqData)

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
	err = algorithm.Initialize(skus, laneTypes, physicalLanes)
	if err != nil {
		fmt.Printf("❌ req_id %s 算法初始化失败: %v\n", reqID, err)
		t.Errorf("req_id %s 算法初始化失败: %v", reqID, err)
		return
	}
	// 根据商品类型和最大库存设置MaxLaneConstraint和MinLaneConstraint
	// CommodityType=6（甜品）：MaxLaneConstraint=2, MinLaneConstraint=0
	// CommodityType=5（饮料）且最大库存≤50：MaxLaneConstraint=1, MinLaneConstraint=0
	// CommodityType=5（饮料）且最大库存>50：MaxLaneConstraint=4, MinLaneConstraint=2
	if reqData.CommodityType == 6 {
		algorithm.SetMaxLaneConstraint(2)
		algorithm.SetMinLaneConstraint(0)
	} else if reqData.CommodityType == 5 {
		// 使用CSV中的point_max_stock字段
		if reqData.PointMaxStock <= 50 {
			algorithm.SetMaxLaneConstraint(1)
			algorithm.SetMinLaneConstraint(0)
		} else {
			algorithm.SetMaxLaneConstraint(4)
			algorithm.SetMinLaneConstraint(2)
		}
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
	skus, laneTypes, physicalLanes := convertToAlgorithmData(reqData)

	if len(skus) == 0 {
		t.Fatalf("无法提取到有效的SKU数据")
	}

	// 打印详细输入数据概览
	printDessertInputSummary(reqData, skus, laneTypes)

	// 创建和初始化算法实例
	fmt.Printf("\n=== 执行补货算法 ===\n")
	algorithm := NewDessertReplenishmentAlgorithm()

	err = algorithm.Initialize(skus, laneTypes, physicalLanes)
	if err != nil {
		t.Fatalf("算法初始化失败: %v", err)
	}
	// 根据商品类型和最大库存设置MaxLaneConstraint和MinLaneConstraint
	// CommodityType=6（甜品）：MaxLaneConstraint=2, MinLaneConstraint=0
	// CommodityType=5（饮料）且最大库存≤50：MaxLaneConstraint=1, MinLaneConstraint=0
	// CommodityType=5（饮料）且最大库存>50：MaxLaneConstraint=4, MinLaneConstraint=2
	if reqData.CommodityType == 6 {
		algorithm.SetMaxLaneConstraint(2)
		algorithm.SetMinLaneConstraint(0)
	} else if reqData.CommodityType == 5 {
		// 使用CSV中的point_max_stock字段
		if reqData.PointMaxStock <= 50 {
			algorithm.SetMaxLaneConstraint(1)
			algorithm.SetMinLaneConstraint(0)
		} else {
			algorithm.SetMaxLaneConstraint(4)
			algorithm.SetMinLaneConstraint(2)
		}
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
	skus, laneTypes, physicalLanes := convertToAlgorithmData(reqData)

	if len(skus) == 0 {
		t.Fatalf("无法提取到有效的SKU数据")
	}

	// 打印详细输入数据概览
	printDessertInputSummary(reqData, skus, laneTypes)

	// 创建和初始化算法实例
	fmt.Printf("\n=== 执行补货算法 ===\n")
	algorithm := NewDessertReplenishmentAlgorithm()

	err = algorithm.Initialize(skus, laneTypes, physicalLanes)
	if err != nil {
		t.Fatalf("算法初始化失败: %v", err)
	}
	// 根据商品类型和最大库存设置MaxLaneConstraint和MinLaneConstraint
	// CommodityType=6（甜品）：MaxLaneConstraint=2, MinLaneConstraint=0
	// CommodityType=5（饮料）且最大库存≤50：MaxLaneConstraint=1, MinLaneConstraint=0
	// CommodityType=5（饮料）且最大库存>50：MaxLaneConstraint=4, MinLaneConstraint=2
	if reqData.CommodityType == 6 {
		algorithm.SetMaxLaneConstraint(2)
		algorithm.SetMinLaneConstraint(0)
	} else if reqData.CommodityType == 5 {
		// 使用CSV中的point_max_stock字段
		if reqData.PointMaxStock <= 50 {
			algorithm.SetMaxLaneConstraint(1)
			algorithm.SetMinLaneConstraint(0)
		} else {
			algorithm.SetMaxLaneConstraint(4)
			algorithm.SetMinLaneConstraint(2)
		}
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

// 批量测试结果结构体
type BatchTestResult struct {
	ReqID             string
	CommodityType     int
	TotalReplenish    int
	ReplenishSKUCount int
	FinalTotalStock   int
	FinalSKUCount     int
	Success           bool
	ErrorMessage      string
}

// 批量测试函数：遍历CSV中所有的req_id并计算相关指标
func TestBatchAllReqIDs(t *testing.T) {
	fmt.Printf("🚀 开始批量测试所有req_id...\n")

	// 读取CSV文件获取所有req_id
	reqIDs, err := getAllReqIDsFromCSV()
	if err != nil {
		t.Fatalf("读取CSV文件失败: %v", err)
	}

	fmt.Printf("📊 发现 %d 个req_id，开始批量测试...\n", len(reqIDs))

	var results []BatchTestResult
	successCount := 0
	errorCount := 0

	// 遍历每个req_id
	for i, reqID := range reqIDs {
		fmt.Printf("\n[%d/%d] 🔄 测试 req_id: %s\n", i+1, len(reqIDs), reqID)

		// 测试甜品类型(6)和饮料类型(5)
		for _, commodityType := range []int{5, 6} {
			result := BatchTestResult{
				ReqID:         reqID,
				CommodityType: commodityType,
			}

			// 解析CSV数据
			reqData, err := parseReqTestData(reqID, commodityType)
			if err != nil {
				result.Success = false
				result.ErrorMessage = fmt.Sprintf("解析失败: %v", err)
				results = append(results, result)
				errorCount++
				continue
			}

			// 转换为算法数据
			skus, laneTypes, physicalLanes := convertToAlgorithmData(reqData)
			if len(skus) == 0 {
				result.Success = false
				result.ErrorMessage = "没有SKU数据"
				results = append(results, result)
				errorCount++
				continue
			}

			// 创建和初始化算法实例
			algorithm := NewDessertReplenishmentAlgorithm()
			algorithm.SetDebugMode(false)
			err = algorithm.Initialize(skus, laneTypes, physicalLanes)
			if err != nil {
				result.Success = false
				result.ErrorMessage = fmt.Sprintf("算法初始化失败: %v", err)
				results = append(results, result)
				errorCount++
				continue
			}

			// 根据商品类型和最大库存设置约束
			if reqData.CommodityType == 6 {
				algorithm.SetMaxLaneConstraint(2)
				algorithm.SetMinLaneConstraint(0)
			} else if reqData.CommodityType == 5 {
				if reqData.PointMaxStock <= 50 {
					algorithm.SetMaxLaneConstraint(1)
					algorithm.SetMinLaneConstraint(0)
				} else {
					algorithm.SetMaxLaneConstraint(4)
					algorithm.SetMinLaneConstraint(2)
				}
			}

			// 执行算法
			algorithmResults, err := algorithm.Execute()
			if err != nil {
				result.Success = false
				result.ErrorMessage = fmt.Sprintf("算法执行失败: %v", err)
				results = append(results, result)
				errorCount++
				continue
			}

			// 计算统计指标
			totalReplenish := 0
			replenishSKUCount := 0
			finalTotalStock := 0
			finalSKUCount := 0

			for _, res := range algorithmResults {
				totalReplenish += res.ReplenishmentQty
				finalTotalStock += res.FinalStock
				if res.ReplenishmentQty > 0 {
					replenishSKUCount++
				}
				if res.FinalStock > 0 {
					finalSKUCount++
				}
			}

			result.TotalReplenish = totalReplenish
			result.ReplenishSKUCount = replenishSKUCount
			result.FinalTotalStock = finalTotalStock
			result.FinalSKUCount = finalSKUCount
			result.Success = true
			result.ErrorMessage = ""

			results = append(results, result)
			successCount++

			fmt.Printf("  ✅ 类型%d: 总补货量=%d, 补货SKU数=%d, 最终总库存=%d, 最终SKU数=%d\n",
				commodityType, totalReplenish, replenishSKUCount, finalTotalStock, finalSKUCount)
		}
	}

	// 输出批量测试结果
	fmt.Printf("\n🎉 批量测试完成！\n")
	fmt.Printf("📊 测试统计:\n")
	fmt.Printf("  总测试数: %d\n", len(results))
	fmt.Printf("  成功数: %d\n", successCount)
	fmt.Printf("  失败数: %d\n", errorCount)
	fmt.Printf("  成功率: %.2f%%\n", float64(successCount)/float64(len(results))*100)

	// 将结果写入CSV文件
	err = writeBatchResultsToCSV(results)
	if err != nil {
		t.Errorf("写入结果到CSV失败: %v", err)
	} else {
		fmt.Printf("✅ 结果已写入CSV文件\n")
	}

	// 打印详细结果
	printBatchTestSummary(results)
}

// 从CSV文件中获取所有唯一的req_id
func getAllReqIDsFromCSV() ([]string, error) {
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

	// 使用map去重
	reqIDMap := make(map[string]bool)
	for _, record := range records[1:] {
		if len(record) > 1 && record[1] != "" {
			reqIDMap[record[1]] = true
		}
	}

	// 转换为slice
	var reqIDs []string
	for reqID := range reqIDMap {
		reqIDs = append(reqIDs, reqID)
	}

	return reqIDs, nil
}

// 将批量测试结果写入CSV文件
func writeBatchResultsToCSV(results []BatchTestResult) error {
	// 读取原始CSV文件
	file, err := os.Open("../data/分拣饮料甜品 case.csv")
	if err != nil {
		return fmt.Errorf("无法打开原始CSV文件: %v", err)
	}
	defer file.Close()

	reader := csv.NewReader(file)
	reader.LazyQuotes = true

	records, err := reader.ReadAll()
	if err != nil {
		return fmt.Errorf("读取原始CSV文件失败: %v", err)
	}

	// 创建结果映射
	resultMap := make(map[string]map[int]BatchTestResult)
	for _, result := range results {
		if resultMap[result.ReqID] == nil {
			resultMap[result.ReqID] = make(map[int]BatchTestResult)
		}
		resultMap[result.ReqID][result.CommodityType] = result
	}

	// 创建新文件
	outputFile, err := os.Create("../data/分拣饮料甜品 case_with_batch_results.csv")
	if err != nil {
		return fmt.Errorf("无法创建输出文件: %v", err)
	}
	defer outputFile.Close()

	writer := csv.NewWriter(outputFile)
	defer writer.Flush()

	// 写入标题行（添加新列）
	newHeader := append(records[0],
		"新总补货量",
		"新补货SKU数",
		"新最终总库存",
		"新最终SKU数",
		"新成功状态",
		"新错误信息")

	if err := writer.Write(newHeader); err != nil {
		return fmt.Errorf("写入标题行失败: %v", err)
	}

	// 写入数据行
	for i := 1; i < len(records); i++ {
		record := records[i]
		if len(record) < 2 {
			continue
		}

		reqID := record[1]
		commodityTypeStr := record[6]
		commodityType, _ := strconv.Atoi(commodityTypeStr)

		// 创建新记录
		newRecord := make([]string, len(newHeader))
		copy(newRecord, record)

		// 填充不足的字段
		for j := len(record); j < len(records[0]); j++ {
			newRecord[j] = ""
		}

		// 添加批量测试结果
		if result, exists := resultMap[reqID][commodityType]; exists {
			newRecord[len(records[0])] = strconv.Itoa(result.TotalReplenish)
			newRecord[len(records[0])+1] = strconv.Itoa(result.ReplenishSKUCount)
			newRecord[len(records[0])+2] = strconv.Itoa(result.FinalTotalStock)
			newRecord[len(records[0])+3] = strconv.Itoa(result.FinalSKUCount)
			if result.Success {
				newRecord[len(records[0])+4] = "成功"
			} else {
				newRecord[len(records[0])+4] = "失败"
			}
			newRecord[len(records[0])+5] = result.ErrorMessage
		} else {
			// 没有测试结果，填充空值
			for j := len(records[0]); j < len(newHeader); j++ {
				newRecord[j] = ""
			}
		}

		if err := writer.Write(newRecord); err != nil {
			return fmt.Errorf("写入记录失败: %v", err)
		}
	}

	return nil
}

// 打印批量测试结果摘要
func printBatchTestSummary(results []BatchTestResult) {
	fmt.Printf("\n=== 批量测试结果摘要 ===\n")

	// 按商品类型分组统计
	typeStats := make(map[int]struct {
		Count           int
		TotalReplenish  int
		TotalSKUCount   int
		TotalFinalStock int
		SuccessCount    int
	})

	for _, result := range results {
		stats := typeStats[result.CommodityType]
		stats.Count++
		stats.TotalReplenish += result.TotalReplenish
		stats.TotalSKUCount += result.ReplenishSKUCount
		stats.TotalFinalStock += result.FinalTotalStock
		if result.Success {
			stats.SuccessCount++
		}
		typeStats[result.CommodityType] = stats
	}

	// 打印各类型统计
	for commodityType, stats := range typeStats {
		typeName := "未知"
		if commodityType == 5 {
			typeName = "饮料"
		} else if commodityType == 6 {
			typeName = "甜品"
		}

		fmt.Printf("\n📊 %s (类型%d) 统计:\n", typeName, commodityType)
		fmt.Printf("  测试数量: %d\n", stats.Count)
		fmt.Printf("  成功数量: %d\n", stats.SuccessCount)
		fmt.Printf("  成功率: %.2f%%\n", float64(stats.SuccessCount)/float64(stats.Count)*100)
		fmt.Printf("  总补货量: %d\n", stats.TotalReplenish)
		fmt.Printf("  总补货SKU数: %d\n", stats.TotalSKUCount)
		fmt.Printf("  总最终库存: %d\n", stats.TotalFinalStock)
		if stats.Count > 0 {
			fmt.Printf("  平均补货量: %.2f\n", float64(stats.TotalReplenish)/float64(stats.Count))
			fmt.Printf("  平均补货SKU数: %.2f\n", float64(stats.TotalSKUCount)/float64(stats.Count))
			fmt.Printf("  平均最终库存: %.2f\n", float64(stats.TotalFinalStock)/float64(stats.Count))
		}
	}

	// 打印失败案例
	fmt.Printf("\n❌ 失败案例:\n")
	failureCount := 0
	for _, result := range results {
		if !result.Success {
			failureCount++
			fmt.Printf("  req_id=%s, 类型=%d: %s\n", result.ReqID, result.CommodityType, result.ErrorMessage)
		}
	}

	if failureCount == 0 {
		fmt.Printf("  🎉 所有测试都成功！\n")
	}
}

// 批量测试函数：一次性测试多个req_id和commodity_type组合
