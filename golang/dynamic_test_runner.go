package main

import (
	"encoding/csv"
	"encoding/json"
	"fmt"
	"math"
	"os"
	"strconv"
	"strings"
)

// CSV记录结构
type CSVRecord struct {
	ID                     string
	ReqID                  string
	ReqTaskID              string
	ReqPointID             string
	ReqCarID               string
	CurrentTime            string
	PointDeviceID          string
	PointDeviceContainerID string
	PointType              string
	PointMaxStock          int
	PointOpenDate          string
	PointIsNew             int
	PointForecast5DayCnt   int
	PointHistory5DayAvgCnt int
	PointIsFullRestock     int
	PointForecastAmount    int
	PointValidShelfCnt     int
	PointRemainStock       int
	PointRemainSku         int
	PointAmountTheoretical int
	PointSkuTheoretical    int
	PointAmountReal        int
	PointSkuReal           int
	PointReplenishAmount   int
	PointReplenishSku      int
	CarSkuDetail           string
	ShelfAllocationBefore  string
	ShelfAllocationAfter   string
	NeedShelfCnt           int
	IsReduceShelf          int
	ReduceShelfCnt         int
	CommodityRestockDetail string
	PointRestockType       int
	DebugData              string
	Status                 int
	FailedReason           string
	CreateTime             string
	UpdateTime             string
}

// 车辆库存数据
type CarSkuData struct {
	CommodityID int `json:"commodity_id"`
	Qty         int `json:"qty"`
}

// 货架分配数据
type ShelfAllocation struct {
	CommodityID         int     `json:"CommodityID"`
	TheoreticalAmount   int     `json:"TheoreticalAmount"`
	TheoreticalShelfCnt int     `json:"TheoreticalShelfCnt"`
	CurrentShelfCnt     int     `json:"CurrentShelfCnt"`
	FinalShelfCnt       int     `json:"FinalShelfCnt"`
	Score               float64 `json:"Score"`
}

// 补货详情数据
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

// 动态测试运行器
type DynamicTestRunner struct {
	csvFilePath string
}

// 创建动态测试运行器
func NewDynamicTestRunner(csvFilePath string) *DynamicTestRunner {
	return &DynamicTestRunner{
		csvFilePath: csvFilePath,
	}
}

// 根据req_id执行测试用例
func (dtr *DynamicTestRunner) RunTestCase(reqID string) error {
	fmt.Printf("=== 动态补货算法测试 (Req ID: %s) ===\n\n", reqID)

	// 1. 读取并解析CSV数据
	record, err := dtr.readCSVRecord(reqID)
	if err != nil {
		return fmt.Errorf("读取CSV记录失败: %v", err)
	}

	// 2. 解析并生成商品数据
	products, err := dtr.parseProductsFromRecord(record)
	if err != nil {
		return fmt.Errorf("解析商品数据失败: %v", err)
	}

	// 3. 创建算法配置
	config := ReplenishmentConfig{
		TargetTotal:    record.PointForecastAmount,
		MaxCapacity:    record.PointMaxStock,
		MaxIterations:  200,
		ToleranceRatio: 0.1,
	}

	// 4. 打印输入数据概览
	fmt.Printf("=== 输入数据概览 (Req ID: %s) ===\n", reqID)
	dtr.printInputSummary(products, config, record)

	// 5. 执行补货算法
	fmt.Printf("\n=== 执行补货算法 ===\n")
	algorithm := NewReplenishmentAlgorithm(products, config)
	results, err := algorithm.Execute()

	if err != nil {
		fmt.Printf("❌ 算法执行失败: %v\n", err)
		return err
	}

	// 6. 打印算法结果
	fmt.Printf("\n=== 算法执行结果 ===\n")
	algorithm.PrintResults()

	// 7. 详细分析结果
	fmt.Printf("\n=== 结果分析 ===\n")
	dtr.analyzeResults(results, config.TargetTotal)

	// 8. 与原始期望结果对比
	fmt.Printf("\n=== 与原始期望结果对比 ===\n")
	originalResults, err := dtr.parseOriginalResults(record.CommodityRestockDetail)
	if err != nil {
		fmt.Printf("⚠️  无法解析原始结果: %v\n", err)
	} else {
		dtr.compareWithOriginalResults(results, originalResults)
	}

	// 9. 约束验证
	fmt.Printf("\n=== 约束验证 ===\n")
	dtr.validateConstraints(results, products, config)

	return nil
}

// 读取CSV记录
func (dtr *DynamicTestRunner) readCSVRecord(reqID string) (*CSVRecord, error) {
	file, err := os.Open(dtr.csvFilePath)
	if err != nil {
		return nil, fmt.Errorf("无法打开CSV文件: %v", err)
	}
	defer file.Close()

	reader := csv.NewReader(file)
	records, err := reader.ReadAll()
	if err != nil {
		return nil, fmt.Errorf("读取CSV文件失败: %v", err)
	}

	if len(records) < 2 {
		return nil, fmt.Errorf("CSV文件格式不正确")
	}

	// 查找匹配的req_id记录
	for i := 1; i < len(records); i++ { // 跳过标题行
		if len(records[i]) < 38 {
			continue
		}

		if records[i][1] == reqID { // req_id在第2列（索引1）
			return dtr.parseCSVRecord(records[i])
		}
	}

	return nil, fmt.Errorf("未找到req_id为 %s 的记录", reqID)
}

// 解析CSV记录
func (dtr *DynamicTestRunner) parseCSVRecord(record []string) (*CSVRecord, error) {
	if len(record) < 38 {
		return nil, fmt.Errorf("CSV记录字段不足")
	}

	// 解析整数字段的辅助函数
	parseInt := func(s string) int {
		if s == "" {
			return 0
		}
		val, err := strconv.Atoi(s)
		if err != nil {
			return 0
		}
		return val
	}

	return &CSVRecord{
		ID:                     record[0],
		ReqID:                  record[1],
		ReqTaskID:              record[2],
		ReqPointID:             record[3],
		ReqCarID:               record[4],
		CurrentTime:            record[5],
		PointDeviceID:          record[6],
		PointDeviceContainerID: record[7],
		PointType:              record[8],
		PointMaxStock:          parseInt(record[9]),
		PointOpenDate:          record[10],
		PointIsNew:             parseInt(record[11]),
		PointForecast5DayCnt:   parseInt(record[12]),
		PointHistory5DayAvgCnt: parseInt(record[13]),
		PointIsFullRestock:     parseInt(record[14]),
		PointForecastAmount:    parseInt(record[15]),
		PointValidShelfCnt:     parseInt(record[16]),
		PointRemainStock:       parseInt(record[17]),
		PointRemainSku:         parseInt(record[18]),
		PointAmountTheoretical: parseInt(record[19]),
		PointSkuTheoretical:    parseInt(record[20]),
		PointAmountReal:        parseInt(record[21]),
		PointSkuReal:           parseInt(record[22]),
		PointReplenishAmount:   parseInt(record[23]),
		PointReplenishSku:      parseInt(record[24]),
		CarSkuDetail:           record[25],
		ShelfAllocationBefore:  record[26],
		ShelfAllocationAfter:   record[27],
		NeedShelfCnt:           parseInt(record[28]),
		IsReduceShelf:          parseInt(record[29]),
		ReduceShelfCnt:         parseInt(record[30]),
		CommodityRestockDetail: record[31],
		PointRestockType:       parseInt(record[32]),
		DebugData:              record[33],
		Status:                 parseInt(record[34]),
		FailedReason:           record[35],
		CreateTime:             record[36],
		UpdateTime:             record[37],
	}, nil
}

// 从记录中解析商品数据
func (dtr *DynamicTestRunner) parseProductsFromRecord(record *CSVRecord) ([]Product, error) {
	// 解析车辆库存数据 (N_i)
	var carSkuData map[string]CarSkuData
	if err := json.Unmarshal([]byte(record.CarSkuDetail), &carSkuData); err != nil {
		return nil, fmt.Errorf("解析车辆库存数据失败: %v", err)
	}

	// 解析货架分配数据 (G_i, r_i)
	var shelfAllocations []ShelfAllocation
	if err := json.Unmarshal([]byte(record.ShelfAllocationBefore), &shelfAllocations); err != nil {
		return nil, fmt.Errorf("解析货架分配数据失败: %v", err)
	}

	// 创建商品映射
	productMap := make(map[int]*Product)

	// 从货架分配数据中创建基础商品信息
	for _, shelf := range shelfAllocations {
		productMap[shelf.CommodityID] = &Product{
			ID:             strconv.Itoa(shelf.CommodityID),
			Name:           fmt.Sprintf("商品_%d", shelf.CommodityID),
			WarehouseStock: 0, // 稍后从车辆库存中填充
			CurrentStock:   shelf.CurrentShelfCnt,
			MaxAllowed:     int(float64(record.PointForecast5DayCnt) * shelf.Score), // X_i = 5天预测量 * 比例
			ExpectedRatio:  shelf.Score,
		}
	}

	// 从车辆库存数据中填充仓库库存
	for _, carData := range carSkuData {
		commodityID := carData.CommodityID
		if product, exists := productMap[commodityID]; exists {
			product.WarehouseStock = carData.Qty
		}
	}

	// 转换为切片并排序
	products := make([]Product, 0, len(productMap))
	for _, product := range productMap {
		products = append(products, *product)
	}

	// 按商品ID排序以保证一致性
	for i := 0; i < len(products)-1; i++ {
		for j := i + 1; j < len(products); j++ {
			idI, _ := strconv.Atoi(products[i].ID)
			idJ, _ := strconv.Atoi(products[j].ID)
			if idI > idJ {
				products[i], products[j] = products[j], products[i]
			}
		}
	}

	return products, nil
}

// 解析原始补货结果
func (dtr *DynamicTestRunner) parseOriginalResults(commodityRestockDetail string) (map[string]int, error) {
	if commodityRestockDetail == "" {
		return make(map[string]int), nil
	}

	var restockDetails []RestockDetail
	if err := json.Unmarshal([]byte(commodityRestockDetail), &restockDetails); err != nil {
		return nil, fmt.Errorf("解析补货详情失败: %v", err)
	}

	originalResults := make(map[string]int)
	for _, detail := range restockDetails {
		originalResults[strconv.Itoa(detail.CommodityID)] = detail.RestockAmount
	}

	return originalResults, nil
}

// 打印输入数据概览
func (dtr *DynamicTestRunner) printInputSummary(products []Product, config ReplenishmentConfig, record *CSVRecord) {
	totalWarehouse := 0
	totalCurrent := 0
	totalExpectedRatio := 0.0
	zeroStockCount := 0

	for _, product := range products {
		totalWarehouse += product.WarehouseStock
		totalCurrent += product.CurrentStock
		totalExpectedRatio += product.ExpectedRatio
		if product.WarehouseStock == 0 {
			zeroStockCount++
		}
	}

	fmt.Printf("基本参数:\n")
	fmt.Printf("  Req ID: %s\n", record.ReqID)
	fmt.Printf("  任务ID: %s\n", record.ReqTaskID)
	fmt.Printf("  点位ID: %s\n", record.ReqPointID)
	fmt.Printf("  车辆ID: %s\n", record.ReqCarID)
	fmt.Printf("  K (点位最大库存): %d\n", config.MaxCapacity)
	fmt.Printf("  M (目标补货后总量): %d\n", config.TargetTotal)
	fmt.Printf("  点位5天预测数量: %d\n", record.PointForecast5DayCnt)
	fmt.Printf("\n商品统计:\n")
	fmt.Printf("  商品总数: %d\n", len(products))
	fmt.Printf("  当前总库存 G: %d\n", totalCurrent)
	fmt.Printf("  仓库总库存 N: %d\n", totalWarehouse)
	fmt.Printf("  目标补货量 P: %d\n", config.TargetTotal-totalCurrent)
	fmt.Printf("  预期比例总和: %.6f\n", totalExpectedRatio)
	fmt.Printf("  零库存商品数: %d\n", zeroStockCount)

	if zeroStockCount > 0 {
		fmt.Printf("⚠️  注意：有 %d 个商品仓库库存为0，无法补货\n", zeroStockCount)
	}

	// 打印详细商品信息
	fmt.Printf("\n=== 商品详细信息 ===\n")
	fmt.Printf("%-8s %-12s %-10s %-10s %-10s %-10s\n",
		"商品ID", "商品名称", "仓库库存", "当前库存", "最大允许", "预期比例")
	fmt.Printf("%s\n", strings.Repeat("-", 70))

	for _, product := range products {
		fmt.Printf("%-8s %-12s %-10d %-10d %-10d %-10.6f\n",
			product.ID,
			product.Name,
			product.WarehouseStock,
			product.CurrentStock,
			product.MaxAllowed,
			product.ExpectedRatio)
	}
	fmt.Printf("%s\n", strings.Repeat("-", 70))
}

// 分析结果
func (dtr *DynamicTestRunner) analyzeResults(results []ReplenishmentResult, targetTotal int) {
	totalReplenish := 0
	totalFinal := 0
	maxDeviation := 0.0
	totalDeviation := 0.0
	zeroReplenishCount := 0

	fmt.Printf("%-8s %-10s %-10s %-12s %-12s %-10s %-10s\n",
		"商品ID", "补货量", "补货后", "实际比例", "预期比例", "比例偏差", "偏差率")
	fmt.Println(strings.Repeat("-", 75))

	for _, result := range results {
		deviation := math.Abs(result.ActualRatio - result.ExpectedRatio)
		deviationRate := deviation / result.ExpectedRatio * 100

		fmt.Printf("%-8s %-10d %-10d %-12.6f %-12.6f %-10.6f %-10.1f%%\n",
			result.ProductID,
			result.ReplenishAmount,
			result.FinalStock,
			result.ActualRatio,
			result.ExpectedRatio,
			deviation,
			deviationRate)

		totalReplenish += result.ReplenishAmount
		totalFinal += result.FinalStock
		totalDeviation += deviation
		if deviation > maxDeviation {
			maxDeviation = deviation
		}
		if result.ReplenishAmount == 0 {
			zeroReplenishCount++
		}
	}

	fmt.Println(strings.Repeat("-", 75))
	avgDeviation := totalDeviation / float64(len(results))

	fmt.Printf("统计指标:\n")
	fmt.Printf("  总补货量: %d\n", totalReplenish)
	fmt.Printf("  最终总量: %d (目标: %d)\n", totalFinal, targetTotal)
	fmt.Printf("  最大比例偏差: %.6f\n", maxDeviation)
	fmt.Printf("  平均比例偏差: %.6f\n", avgDeviation)
	fmt.Printf("  零补货商品数: %d\n", zeroReplenishCount)

	// 评估算法表现
	if totalFinal == targetTotal {
		fmt.Printf("✅ 成功达到目标总量\n")
	} else {
		fmt.Printf("⚠️  未达到目标总量，差异: %d\n", targetTotal-totalFinal)
	}

	if avgDeviation < 0.01 {
		fmt.Printf("✅ 比例精度优秀 (平均偏差 < 1%%)\n")
	} else if avgDeviation < 0.02 {
		fmt.Printf("✅ 比例精度良好 (平均偏差 < 2%%)\n")
	} else {
		fmt.Printf("⚠️  比例精度一般 (平均偏差 %.1f%%)\n", avgDeviation*100)
	}
}

// 与原始期望结果对比
func (dtr *DynamicTestRunner) compareWithOriginalResults(results []ReplenishmentResult, originalResults map[string]int) {
	fmt.Printf("%-8s %-12s %-12s %-10s %-15s\n",
		"商品ID", "我们的结果", "原始期望", "差异", "匹配状态")
	fmt.Println(strings.Repeat("-", 60))

	totalOurResult := 0
	totalOriginal := 0
	matchCount := 0

	for _, result := range results {
		ourAmount := result.ReplenishAmount
		originalAmount, hasOriginal := originalResults[result.ProductID]

		if !hasOriginal {
			originalAmount = -1 // 表示原始数据中没有此商品
		}

		difference := ourAmount - originalAmount
		matchStatus := "新商品"
		if hasOriginal {
			if difference == 0 {
				matchStatus = "✅ 完全匹配"
				matchCount++
			} else {
				matchStatus = fmt.Sprintf("❌ 差异%+d", difference)
			}
			totalOriginal += originalAmount
		}

		totalOurResult += ourAmount

		originalStr := "-"
		if hasOriginal {
			originalStr = fmt.Sprintf("%d", originalAmount)
		}

		fmt.Printf("%-8s %-12d %-12s %-10d %-15s\n",
			result.ProductID,
			ourAmount,
			originalStr,
			difference,
			matchStatus)
	}

	fmt.Println(strings.Repeat("-", 60))
	fmt.Printf("总计对比:\n")
	fmt.Printf("  我们的总补货量: %d\n", totalOurResult)
	fmt.Printf("  原始期望总量: %d\n", totalOriginal)

	if len(originalResults) > 0 {
		fmt.Printf("  完全匹配商品数: %d / %d\n", matchCount, len(originalResults))
		matchRate := float64(matchCount) / float64(len(originalResults)) * 100
		fmt.Printf("  匹配率: %.1f%%\n", matchRate)
	}
}

// 约束验证
func (dtr *DynamicTestRunner) validateConstraints(results []ReplenishmentResult, products []Product, config ReplenishmentConfig) {
	productMap := make(map[string]Product)
	for _, p := range products {
		productMap[p.ID] = p
	}

	violations := 0
	totalFinal := 0

	fmt.Printf("约束检查:\n")

	for _, result := range results {
		product := productMap[result.ProductID]
		totalFinal += result.FinalStock

		// 检查仓库库存约束
		if result.ReplenishAmount > product.WarehouseStock {
			fmt.Printf("❌ 商品%s: 补货量(%d) > 仓库库存(%d)\n",
				result.ProductID, result.ReplenishAmount, product.WarehouseStock)
			violations++
		}

		// 检查最大允许数量约束
		maxAllowed := maxInt(product.MaxAllowed, product.CurrentStock)
		if result.FinalStock > maxAllowed {
			fmt.Printf("❌ 商品%s: 补货后数量(%d) > 最大允许(%d)\n",
				result.ProductID, result.FinalStock, maxAllowed)
			violations++
		}

		// 检查负补货约束
		if result.ReplenishAmount < 0 {
			fmt.Printf("❌ 商品%s: 补货量为负(%d)\n",
				result.ProductID, result.ReplenishAmount)
			violations++
		}
	}

	// 检查总量约束
	if totalFinal != config.TargetTotal {
		fmt.Printf("⚠️  总量约束: 实际总量(%d) != 目标总量(%d)\n",
			totalFinal, config.TargetTotal)
	}

	if violations == 0 {
		fmt.Printf("✅ 所有强约束均满足\n")
	} else {
		fmt.Printf("❌ 发现 %d 个约束违反\n", violations)
	}

	fmt.Printf("总量验证: %d (目标: %d)\n", totalFinal, config.TargetTotal)
}

func main() {
	if len(os.Args) != 3 {
		fmt.Printf("用法: %s <CSV文件路径> <req_id>\n", os.Args[0])
		fmt.Printf("示例: %s ../data/分拣case.csv 3ce9aa5dd811d4be\n", os.Args[0])
		os.Exit(1)
	}

	csvFilePath := os.Args[1]
	reqID := os.Args[2]

	// 创建动态测试运行器
	runner := NewDynamicTestRunner(csvFilePath)

	// 运行测试用例
	if err := runner.RunTestCase(reqID); err != nil {
		fmt.Printf("测试执行失败: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("\n🎉 测试执行完成！\n")
}

// 注意：maxInt和minInt函数已在replenishment_algorithm.go中定义，这里不需要重复定义
