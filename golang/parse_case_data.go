package main

import (
	"encoding/json"
	"fmt"
	"strconv"
	"strings"
)

// CSV第一条记录的原始数据
const firstRecord = `21,3ce9aa5dd811d4be,"48,176",24,14,2025-08-16 00:17:09,"40,097",192,1,108,2025-05-18,0,201,0,0,108,35,34,7,117,17,88,17,20,4,"{""100"":{""commodity_id"":100,""qty"":9},""101"":{""commodity_id"":101,""qty"":18},""102"":{""commodity_id"":102,""qty"":27},""104"":{""commodity_id"":104,""qty"":18},""188"":{""commodity_id"":188,""qty"":36},""189"":{""commodity_id"":189,""qty"":18},""219"":{""commodity_id"":219,""qty"":27},""258"":{""commodity_id"":258,""qty"":27},""268"":{""commodity_id"":268,""qty"":18},""269"":{""commodity_id"":269,""qty"":18},""272"":{""commodity_id"":272,""qty"":7},""292"":{""commodity_id"":292,""qty"":18},""323"":{""commodity_id"":323,""qty"":18},""75"":{""commodity_id"":75,""qty"":18},""82"":{""commodity_id"":82,""qty"":18},""95"":{""commodity_id"":95,""qty"":18},""98"":{""commodity_id"":98,""qty"":9}}","[{""CommodityID"":258,""TheoreticalAmount"":7,""TheoreticalShelfCnt"":3,""CurrentShelfCnt"":5,""FinalShelfCnt"":5,""Score"":0.06338959857188996},{""CommodityID"":104,""TheoreticalAmount"":11,""TheoreticalShelfCnt"":4,""CurrentShelfCnt"":1,""FinalShelfCnt"":4,""Score"":0.09398652379517144},{""CommodityID"":102,""TheoreticalAmount"":10,""TheoreticalShelfCnt"":4,""CurrentShelfCnt"":0,""FinalShelfCnt"":4,""Score"":0.0911020438833482},{""CommodityID"":219,""TheoreticalAmount"":10,""TheoreticalShelfCnt"":4,""CurrentShelfCnt"":1,""FinalShelfCnt"":4,""Score"":0.09117824136561556},{""CommodityID"":188,""TheoreticalAmount"":9,""TheoreticalShelfCnt"":3,""CurrentShelfCnt"":4,""FinalShelfCnt"":4,""Score"":0.07776577194933555},{""CommodityID"":292,""TheoreticalAmount"":9,""TheoreticalShelfCnt"":3,""CurrentShelfCnt"":0,""FinalShelfCnt"":3,""Score"":0.0744343113910242},{""CommodityID"":100,""TheoreticalAmount"":8,""TheoreticalShelfCnt"":3,""CurrentShelfCnt"":0,""FinalShelfCnt"":3,""Score"":0.06956727567618168},{""CommodityID"":323,""TheoreticalAmount"":8,""TheoreticalShelfCnt"":3,""CurrentShelfCnt"":2,""FinalShelfCnt"":3,""Score"":0.0684292830337791},{""CommodityID"":98,""TheoreticalAmount"":7,""TheoreticalShelfCnt"":3,""CurrentShelfCnt"":0,""FinalShelfCnt"":3,""Score"":0.05612730865949987},{""CommodityID"":95,""TheoreticalAmount"":7,""TheoreticalShelfCnt"":3,""CurrentShelfCnt"":0,""FinalShelfCnt"":3,""Score"":0.06100394509257649},{""CommodityID"":308,""TheoreticalAmount"":7,""TheoreticalShelfCnt"":3,""CurrentShelfCnt"":0,""FinalShelfCnt"":3,""Score"":0.060480162414911436},{""CommodityID"":75,""TheoreticalAmount"":6,""TheoreticalShelfCnt"":2,""CurrentShelfCnt"":0,""FinalShelfCnt"":2,""Score"":0.046406987009556595},{""CommodityID"":101,""TheoreticalAmount"":5,""TheoreticalShelfCnt"":2,""CurrentShelfCnt"":0,""FinalShelfCnt"":2,""Score"":0.03857721086784076},{""CommodityID"":189,""TheoreticalAmount"":4,""TheoreticalShelfCnt"":2,""CurrentShelfCnt"":2,""FinalShelfCnt"":2,""Score"":0.03413487484298474},{""CommodityID"":82,""TheoreticalAmount"":4,""TheoreticalShelfCnt"":2,""CurrentShelfCnt"":0,""FinalShelfCnt"":2,""Score"":0.030954007971023684},{""CommodityID"":269,""TheoreticalAmount"":3,""TheoreticalShelfCnt"":1,""CurrentShelfCnt"":0,""FinalShelfCnt"":1,""Score"":0.02485503673247119},{""CommodityID"":268,""TheoreticalAmount"":2,""TheoreticalShelfCnt"":1,""CurrentShelfCnt"":1,""FinalShelfCnt"":1,""Score"":0.017607416742789452}]","{""reduce_detail"":{""100"":1,""101"":1,""189"":1,""292"":1,""308"":2,""323"":2,""75"":1,""82"":1,""95"":2,""98"":2},""result"":{""100"":{""CommodityID"":100,""FinalShelfCnt"":2,""RestockAmount"":6},""101"":{""CommodityID"":101,""FinalShelfCnt"":1,""RestockAmount"":3},""102"":{""CommodityID"":102,""FinalShelfCnt"":4,""RestockAmount"":10},""104"":{""CommodityID"":104,""FinalShelfCnt"":4,""RestockAmount"":11},""188"":{""CommodityID"":188,""FinalShelfCnt"":4,""RestockAmount"":9},""189"":{""CommodityID"":189,""FinalShelfCnt"":1,""RestockAmount"":3},""219"":{""CommodityID"":219,""FinalShelfCnt"":4,""RestockAmount"":10},""258"":{""CommodityID"":258,""FinalShelfCnt"":5,""RestockAmount"":7},""268"":{""CommodityID"":268,""FinalShelfCnt"":1,""RestockAmount"":2},""269"":{""CommodityID"":269,""FinalShelfCnt"":1,""RestockAmount"":3},""292"":{""CommodityID"":292,""FinalShelfCnt"":2,""RestockAmount"":6},""308"":{""CommodityID"":308,""FinalShelfCnt"":1,""RestockAmount"":3},""323"":{""CommodityID"":323,""FinalShelfCnt"":1,""RestockAmount"":3},""75"":{""CommodityID"":75,""FinalShelfCnt"":1,""RestockAmount"":3},""82"":{""CommodityID"":82,""FinalShelfCnt"":1,""RestockAmount"":3},""95"":{""CommodityID"":95,""FinalShelfCnt"":1,""RestockAmount"":3},""98"":{""CommodityID"":98,""FinalShelfCnt"":1,""RestockAmount"":3}}}"}`

// 商品库存信息（车辆库存）
type CarSkuDetail struct {
	CommodityID int `json:"commodity_id"`
	Qty         int `json:"qty"`
}

// 货架分配信息
type ShelfAllocation struct {
	CommodityID         int     `json:"CommodityID"`
	TheoreticalAmount   int     `json:"TheoreticalAmount"`
	TheoreticalShelfCnt int     `json:"TheoreticalShelfCnt"`
	CurrentShelfCnt     int     `json:"CurrentShelfCnt"`
	FinalShelfCnt       int     `json:"FinalShelfCnt"`
	Score               float64 `json:"Score"`
}

// 补货详细信息
type RestockDetail struct {
	CommodityID         int     `json:"commodity_id"`
	RestockAmount       int     `json:"restock_amount"`
	RestockType         int     `json:"restock_type"`
	CommodityRatio      float64 `json:"commodity_ratio"`
	CommodityTotalRatio float64 `json:"commodity_total_ratio"`
	CommodityScore      float64 `json:"commodity_score"`
	CarCommodityStock   int     `json:"car_commodity_stock"`
	CommodityStock      int     `json:"commodity_stock"`
}

// 解析后的商品数据
type ParsedProductData struct {
	CommodityID    int     // 商品ID
	Name           string  // 商品名称
	WarehouseStock int     // 仓库库存 N_i (来自car_sku_detail)
	CurrentStock   int     // 点位现有量 G_i (来自shelf_allocation_before)
	MaxAllowed     int     // 最大允许补货后数量 X_i (point_forecast_5day_cnt * r_i)
	ExpectedRatio  float64 // 预期比例 r_i (来自commodity_restock_detail的commodity_score)
	Score          float64 // 原始Score (来自shelf_allocation_before)
}

func main() {
	fmt.Println("=== 解析第一条补货案例数据 ===\n")

	// 解析CSV记录
	fields := parseCSVRecord(firstRecord)

	// 提取基本参数
	K := 108                                         // point_max_stock
	M, _ := strconv.Atoi(fields[15])                 // point_forecast_amount
	pointForecast5day, _ := strconv.Atoi(fields[12]) // point_forecast_5day_cnt

	fmt.Printf("基本参数:\n")
	fmt.Printf("K (点位最大库存): %d\n", K)
	fmt.Printf("M (目标补货后总量): %d\n", M)
	fmt.Printf("点位5天预测数量: %d\n", pointForecast5day)
	fmt.Println()

	// 解析车辆库存数据 (N_i)
	carSkuDetailStr := fields[25]
	carSkuDetail := parseCarSkuDetail(carSkuDetailStr)

	// 解析货架分配数据 (G_i和Score)
	shelfAllocationStr := fields[26]
	shelfAllocations := parseShelfAllocation(shelfAllocationStr)

	// 解析补货详细数据 (r_i)
	restockDetailStr := fields[30]
	restockDetails := parseRestockDetail(restockDetailStr)

	// 整合数据
	productData := integrateProductData(carSkuDetail, shelfAllocations, restockDetails, pointForecast5day)

	// 打印整理后的数据供确认
	printProductDataTable(productData, K, M)

	// 验证数据完整性
	validateData(productData)
}

// 解析CSV记录
func parseCSVRecord(record string) []string {
	// 简单的CSV解析，处理引号内的逗号
	fields := make([]string, 0)
	inQuotes := false
	currentField := ""

	for i, char := range record {
		if char == '"' {
			inQuotes = !inQuotes
		} else if char == ',' && !inQuotes {
			fields = append(fields, currentField)
			currentField = ""
		} else {
			currentField += string(char)
		}

		// 最后一个字段
		if i == len(record)-1 {
			fields = append(fields, currentField)
		}
	}

	return fields
}

// 解析车辆库存详细信息
func parseCarSkuDetail(jsonStr string) map[int]*CarSkuDetail {
	// 清理JSON字符串中的转义字符
	cleanedJSON := strings.ReplaceAll(jsonStr, `""`, `"`)

	var carSkuMap map[string]*CarSkuDetail
	if err := json.Unmarshal([]byte(cleanedJSON), &carSkuMap); err != nil {
		fmt.Printf("解析车辆库存数据失败: %v\n", err)
		return nil
	}

	result := make(map[int]*CarSkuDetail)
	for _, detail := range carSkuMap {
		result[detail.CommodityID] = detail
	}

	return result
}

// 解析货架分配信息
func parseShelfAllocation(jsonStr string) map[int]*ShelfAllocation {
	// 清理JSON字符串
	cleanedJSON := strings.ReplaceAll(jsonStr, `""`, `"`)

	var allocations []*ShelfAllocation
	if err := json.Unmarshal([]byte(cleanedJSON), &allocations); err != nil {
		fmt.Printf("解析货架分配数据失败: %v\n", err)
		return nil
	}

	result := make(map[int]*ShelfAllocation)
	for _, allocation := range allocations {
		result[allocation.CommodityID] = allocation
	}

	return result
}

// 解析补货详细信息
func parseRestockDetail(jsonStr string) map[int]*RestockDetail {
	// 清理JSON字符串
	cleanedJSON := strings.ReplaceAll(jsonStr, `""`, `"`)

	var details []*RestockDetail
	if err := json.Unmarshal([]byte(cleanedJSON), &details); err != nil {
		fmt.Printf("解析补货详细数据失败: %v\n", err)
		return nil
	}

	result := make(map[int]*RestockDetail)
	for _, detail := range details {
		result[detail.CommodityID] = detail
	}

	return result
}

// 整合商品数据
func integrateProductData(carSku map[int]*CarSkuDetail, shelfAlloc map[int]*ShelfAllocation,
	restockDetail map[int]*RestockDetail, pointForecast5day int) []*ParsedProductData {

	productMap := make(map[int]*ParsedProductData)

	// 从货架分配数据开始构建
	for commodityID, allocation := range shelfAlloc {
		product := &ParsedProductData{
			CommodityID:  commodityID,
			Name:         fmt.Sprintf("商品_%d", commodityID),
			CurrentStock: allocation.CurrentShelfCnt,
			Score:        allocation.Score,
		}

		// 从车辆库存获取仓库库存
		if carDetail, exists := carSku[commodityID]; exists {
			product.WarehouseStock = carDetail.Qty
		}

		// 从补货详细信息获取预期比例
		if restockInfo, exists := restockDetail[commodityID]; exists {
			product.ExpectedRatio = restockInfo.CommodityScore
		}

		// 计算最大允许数量: X_i = point_forecast_5day_cnt * r_i
		product.MaxAllowed = int(float64(pointForecast5day) * product.ExpectedRatio)

		productMap[commodityID] = product
	}

	// 转换为切片并排序
	products := make([]*ParsedProductData, 0, len(productMap))
	for _, product := range productMap {
		products = append(products, product)
	}

	// 按商品ID排序
	for i := 0; i < len(products)-1; i++ {
		for j := i + 1; j < len(products); j++ {
			if products[i].CommodityID > products[j].CommodityID {
				products[i], products[j] = products[j], products[i]
			}
		}
	}

	return products
}

// 打印商品数据表格
func printProductDataTable(products []*ParsedProductData, K, M int) {
	fmt.Printf("=== 整理后的商品数据 ===\n")
	fmt.Printf("K (点位最大库存): %d\n", K)
	fmt.Printf("M (目标补货后总量): %d\n", M)
	fmt.Printf("商品总数: %d\n\n", len(products))

	// 打印表头
	fmt.Printf("%-10s %-15s %-10s %-10s %-10s %-15s %-10s\n",
		"商品ID", "商品名称", "仓库库存", "当前库存", "最大允许", "预期比例", "原始Score")
	fmt.Printf("%-10s %-15s %-10s %-10s %-10s %-15s %-10s\n",
		"", "", "N_i", "G_i", "X_i", "r_i", "")
	fmt.Println(strings.Repeat("-", 85))

	totalWarehouse := 0
	totalCurrent := 0
	totalExpectedRatio := 0.0

	for _, product := range products {
		fmt.Printf("%-10d %-15s %-10d %-10d %-10d %-15.6f %-10.6f\n",
			product.CommodityID,
			product.Name,
			product.WarehouseStock,
			product.CurrentStock,
			product.MaxAllowed,
			product.ExpectedRatio,
			product.Score)

		totalWarehouse += product.WarehouseStock
		totalCurrent += product.CurrentStock
		totalExpectedRatio += product.ExpectedRatio
	}

	fmt.Println(strings.Repeat("-", 85))
	fmt.Printf("%-25s %-10d %-10d %-10s %-15.6f\n",
		"合计:", totalWarehouse, totalCurrent, "-", totalExpectedRatio)

	fmt.Printf("\n数据验证:\n")
	fmt.Printf("预期比例总和: %.6f (应该接近1.0)\n", totalExpectedRatio)
	fmt.Printf("当前总库存: %d\n", totalCurrent)
	fmt.Printf("仓库总库存: %d\n", totalWarehouse)
	fmt.Printf("目标补货量: %d (M - 当前总库存)\n", M-totalCurrent)
}

// 验证数据完整性
func validateData(products []*ParsedProductData) {
	fmt.Printf("\n=== 数据完整性验证 ===\n")

	issues := 0

	for _, product := range products {
		if product.WarehouseStock < 0 {
			fmt.Printf("❌ 商品%d: 仓库库存为负 (%d)\n", product.CommodityID, product.WarehouseStock)
			issues++
		}

		if product.CurrentStock < 0 {
			fmt.Printf("❌ 商品%d: 当前库存为负 (%d)\n", product.CommodityID, product.CurrentStock)
			issues++
		}

		if product.ExpectedRatio < 0 {
			fmt.Printf("❌ 商品%d: 预期比例为负 (%.6f)\n", product.CommodityID, product.ExpectedRatio)
			issues++
		}

		if product.MaxAllowed < 0 {
			fmt.Printf("❌ 商品%d: 最大允许数量为负 (%d)\n", product.CommodityID, product.MaxAllowed)
			issues++
		}
	}

	if issues == 0 {
		fmt.Printf("✅ 数据验证通过，未发现问题\n")
	} else {
		fmt.Printf("⚠️  发现 %d 个数据问题\n", issues)
	}
}
