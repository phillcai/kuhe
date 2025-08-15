package main

import (
	"encoding/json"
	"fmt"
	"strings"
)

func main() {
	fmt.Println("=== 第一条补货案例数据解析 ===\n")

	// 基本参数
	K := 108                 // point_max_stock
	M := 108                 // point_forecast_amount
	pointForecast5day := 201 // point_forecast_5day_cnt

	fmt.Printf("基本参数:\n")
	fmt.Printf("K (点位最大库存): %d\n", K)
	fmt.Printf("M (目标补货后总量): %d\n", M)
	fmt.Printf("点位5天预测数量: %d\n\n", pointForecast5day)

	// 车辆库存数据 (N_i) - 仓库库存
	carSkuJSON := `{"100":{"commodity_id":100,"qty":9},"101":{"commodity_id":101,"qty":18},"102":{"commodity_id":102,"qty":27},"104":{"commodity_id":104,"qty":18},"188":{"commodity_id":188,"qty":36},"189":{"commodity_id":189,"qty":18},"219":{"commodity_id":219,"qty":27},"258":{"commodity_id":258,"qty":27},"268":{"commodity_id":268,"qty":18},"269":{"commodity_id":269,"qty":18},"272":{"commodity_id":272,"qty":7},"292":{"commodity_id":292,"qty":18},"323":{"commodity_id":323,"qty":18},"75":{"commodity_id":75,"qty":18},"82":{"commodity_id":82,"qty":18},"95":{"commodity_id":95,"qty":18},"98":{"commodity_id":98,"qty":9}}`

	// 货架分配数据 (G_i和Score) - 当前库存和评分
	shelfJSON := `[{"CommodityID":258,"TheoreticalAmount":7,"TheoreticalShelfCnt":3,"CurrentShelfCnt":5,"FinalShelfCnt":5,"Score":0.06338959857188996},{"CommodityID":104,"TheoreticalAmount":11,"TheoreticalShelfCnt":4,"CurrentShelfCnt":1,"FinalShelfCnt":4,"Score":0.09398652379517144},{"CommodityID":102,"TheoreticalAmount":10,"TheoreticalShelfCnt":4,"CurrentShelfCnt":0,"FinalShelfCnt":4,"Score":0.0911020438833482},{"CommodityID":219,"TheoreticalAmount":10,"TheoreticalShelfCnt":4,"CurrentShelfCnt":1,"FinalShelfCnt":4,"Score":0.09117824136561556},{"CommodityID":188,"TheoreticalAmount":9,"TheoreticalShelfCnt":3,"CurrentShelfCnt":4,"FinalShelfCnt":4,"Score":0.07776577194933555},{"CommodityID":292,"TheoreticalAmount":9,"TheoreticalShelfCnt":3,"CurrentShelfCnt":0,"FinalShelfCnt":3,"Score":0.0744343113910242},{"CommodityID":100,"TheoreticalAmount":8,"TheoreticalShelfCnt":3,"CurrentShelfCnt":0,"FinalShelfCnt":3,"Score":0.06956727567618168},{"CommodityID":323,"TheoreticalAmount":8,"TheoreticalShelfCnt":3,"CurrentShelfCnt":2,"FinalShelfCnt":3,"Score":0.0684292830337791},{"CommodityID":98,"TheoreticalAmount":7,"TheoreticalShelfCnt":3,"CurrentShelfCnt":0,"FinalShelfCnt":3,"Score":0.05612730865949987},{"CommodityID":95,"TheoreticalAmount":7,"TheoreticalShelfCnt":3,"CurrentShelfCnt":0,"FinalShelfCnt":3,"Score":0.06100394509257649},{"CommodityID":308,"TheoreticalAmount":7,"TheoreticalShelfCnt":3,"CurrentShelfCnt":0,"FinalShelfCnt":3,"Score":0.060480162414911436},{"CommodityID":75,"TheoreticalAmount":6,"TheoreticalShelfCnt":2,"CurrentShelfCnt":0,"FinalShelfCnt":2,"Score":0.046406987009556595},{"CommodityID":101,"TheoreticalAmount":5,"TheoreticalShelfCnt":2,"CurrentShelfCnt":0,"FinalShelfCnt":2,"Score":0.03857721086784076},{"CommodityID":189,"TheoreticalAmount":4,"TheoreticalShelfCnt":2,"CurrentShelfCnt":2,"FinalShelfCnt":2,"Score":0.03413487484298474},{"CommodityID":82,"TheoreticalAmount":4,"TheoreticalShelfCnt":2,"CurrentShelfCnt":0,"FinalShelfCnt":2,"Score":0.030954007971023684},{"CommodityID":269,"TheoreticalAmount":3,"TheoreticalShelfCnt":1,"CurrentShelfCnt":0,"FinalShelfCnt":1,"Score":0.02485503673247119},{"CommodityID":268,"TheoreticalAmount":2,"TheoreticalShelfCnt":1,"CurrentShelfCnt":1,"FinalShelfCnt":1,"Score":0.017607416742789452}]`

	// 补货详细数据 (r_i) - 预期比例
	restockJSON := `[{"commodity_id":104,"restock_amount":10,"restock_type":0,"commodity_ratio":0.0375510565436433,"commodity_total_ratio":0.39953660405059566,"commodity_score":0.09398652379517144,"car_commodity_stock":18,"commodity_stock":1},{"commodity_id":188,"restock_amount":0,"restock_type":0,"commodity_ratio":0.031070272436010595,"commodity_total_ratio":0.39953660405059566,"commodity_score":0.07776577194933555,"car_commodity_stock":36,"commodity_stock":11},{"commodity_id":189,"restock_amount":0,"restock_type":0,"commodity_ratio":0.013638131974458232,"commodity_total_ratio":0.39953660405059566,"commodity_score":0.03413487484298474,"car_commodity_stock":18,"commodity_stock":3},{"commodity_id":219,"restock_amount":8,"restock_type":0,"commodity_ratio":0.036429044918523584,"commodity_total_ratio":0.39953660405059566,"commodity_score":0.09117824136561556,"car_commodity_stock":27,"commodity_stock":2},{"commodity_id":258,"restock_amount":0,"restock_type":0,"commodity_ratio":0.025326464945543404,"commodity_total_ratio":0.39953660405059566,"commodity_score":0.06338959857188996,"car_commodity_stock":27,"commodity_stock":14},{"commodity_id":268,"restock_amount":1,"restock_type":0,"commodity_ratio":0.007034807491517699,"commodity_total_ratio":0.39953660405059566,"commodity_score":0.017607416742789452,"car_commodity_stock":18,"commodity_stock":1},{"commodity_id":323,"restock_amount":1,"restock_type":0,"commodity_ratio":0.027340003360933143,"commodity_total_ratio":0.39953660405059566,"commodity_score":0.0684292830337791,"car_commodity_stock":18,"commodity_stock":2}]`

	// 解析数据
	carSku := parseCarSku(carSkuJSON)
	shelfAlloc := parseShelfAllocation(shelfJSON)
	restockDetail := parseRestockDetail(restockJSON)

	// 整合并显示数据
	products := integrateData(carSku, shelfAlloc, restockDetail, pointForecast5day)
	printDataTable(products, K, M)
}

type CarSkuDetail struct {
	CommodityID int `json:"commodity_id"`
	Qty         int `json:"qty"`
}

type ShelfAllocation struct {
	CommodityID     int     `json:"CommodityID"`
	CurrentShelfCnt int     `json:"CurrentShelfCnt"`
	Score           float64 `json:"Score"`
}

type RestockDetail struct {
	CommodityID    int     `json:"commodity_id"`
	CommodityScore float64 `json:"commodity_score"`
}

type ProductData struct {
	CommodityID    int     // 商品ID
	Name           string  // 商品名称
	WarehouseStock int     // 仓库库存 N_i
	CurrentStock   int     // 点位现有量 G_i
	MaxAllowed     int     // 最大允许补货后数量 X_i
	ExpectedRatio  float64 // 预期比例 r_i
}

func parseCarSku(jsonStr string) map[int]*CarSkuDetail {
	var carSkuMap map[string]*CarSkuDetail
	json.Unmarshal([]byte(jsonStr), &carSkuMap)

	result := make(map[int]*CarSkuDetail)
	for _, detail := range carSkuMap {
		result[detail.CommodityID] = detail
	}
	return result
}

func parseShelfAllocation(jsonStr string) map[int]*ShelfAllocation {
	var allocations []*ShelfAllocation
	json.Unmarshal([]byte(jsonStr), &allocations)

	result := make(map[int]*ShelfAllocation)
	for _, allocation := range allocations {
		result[allocation.CommodityID] = allocation
	}
	return result
}

func parseRestockDetail(jsonStr string) map[int]*RestockDetail {
	var details []*RestockDetail
	json.Unmarshal([]byte(jsonStr), &details)

	result := make(map[int]*RestockDetail)
	for _, detail := range details {
		result[detail.CommodityID] = detail
	}
	return result
}

func integrateData(carSku map[int]*CarSkuDetail, shelfAlloc map[int]*ShelfAllocation,
	restockDetail map[int]*RestockDetail, pointForecast5day int) []*ProductData {

	productMap := make(map[int]*ProductData)

	// 从货架分配数据开始构建（这里有最完整的商品列表）
	for commodityID, allocation := range shelfAlloc {
		product := &ProductData{
			CommodityID:  commodityID,
			Name:         fmt.Sprintf("商品_%d", commodityID),
			CurrentStock: allocation.CurrentShelfCnt,
		}

		// 从车辆库存获取仓库库存
		if carDetail, exists := carSku[commodityID]; exists {
			product.WarehouseStock = carDetail.Qty
		}

		// 从补货详细信息获取预期比例
		if restockInfo, exists := restockDetail[commodityID]; exists {
			product.ExpectedRatio = restockInfo.CommodityScore
		} else {
			// 如果在补货详细信息中没有找到，使用货架分配中的Score
			product.ExpectedRatio = allocation.Score
		}

		// 计算最大允许数量: X_i = point_forecast_5day_cnt * r_i
		product.MaxAllowed = int(float64(pointForecast5day) * product.ExpectedRatio)

		productMap[commodityID] = product
	}

	// 转换为切片并排序
	products := make([]*ProductData, 0, len(productMap))
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

func printDataTable(products []*ProductData, K, M int) {
	fmt.Printf("=== 整理后的商品数据 ===\n")
	fmt.Printf("K (点位最大库存): %d\n", K)
	fmt.Printf("M (目标补货后总量): %d\n", M)
	fmt.Printf("商品总数: %d\n\n", len(products))

	// 打印表头
	fmt.Printf("%-8s %-12s %-10s %-10s %-10s %-15s\n",
		"商品ID", "商品名称", "仓库库存", "当前库存", "最大允许", "预期比例")
	fmt.Printf("%-8s %-12s %-10s %-10s %-10s %-15s\n",
		"", "", "N_i", "G_i", "X_i", "r_i")
	fmt.Println(strings.Repeat("-", 75))

	totalWarehouse := 0
	totalCurrent := 0
	totalExpectedRatio := 0.0

	for _, product := range products {
		fmt.Printf("%-8d %-12s %-10d %-10d %-10d %-15.6f\n",
			product.CommodityID,
			product.Name,
			product.WarehouseStock,
			product.CurrentStock,
			product.MaxAllowed,
			product.ExpectedRatio)

		totalWarehouse += product.WarehouseStock
		totalCurrent += product.CurrentStock
		totalExpectedRatio += product.ExpectedRatio
	}

	fmt.Println(strings.Repeat("-", 75))
	fmt.Printf("%-20s %-10d %-10d %-10s %-15.6f\n",
		"合计:", totalWarehouse, totalCurrent, "-", totalExpectedRatio)

	fmt.Printf("\n=== 数据验证 ===\n")
	fmt.Printf("预期比例总和: %.6f (注意：这不是标准化的比例，不需要等于1.0)\n", totalExpectedRatio)
	fmt.Printf("当前总库存 G: %d\n", totalCurrent)
	fmt.Printf("仓库总库存 N: %d\n", totalWarehouse)
	fmt.Printf("目标补货量 P: %d (M - G = %d - %d)\n", M-totalCurrent, M, totalCurrent)

	// 检查是否有足够库存
	if totalWarehouse >= (M - totalCurrent) {
		fmt.Printf("✅ 仓库库存充足，可以达到目标补货量\n")
	} else {
		fmt.Printf("⚠️  仓库库存不足，最大可补货量: %d\n", totalWarehouse)
	}

	fmt.Printf("\n=== 关键观察 ===\n")
	fmt.Printf("1. 商品数量: %d个商品\n", len(products))
	fmt.Printf("2. 库存充足度: %.1f%% (仓库库存/目标补货量)\n",
		float64(totalWarehouse)/float64(M-totalCurrent)*100)
	fmt.Printf("3. 当前填充度: %.1f%% (当前库存/目标总量)\n",
		float64(totalCurrent)/float64(M)*100)
}
