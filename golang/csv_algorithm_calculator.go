package main

import (
	"encoding/csv"
	"encoding/json"
	"fmt"
	"os"
	"strconv"
)

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

// CSV记录结构（简化版）
type CSVRecord struct {
	ReqID                  string
	PointMaxStock          int
	PointForecast5DayCnt   int
	PointForecastAmount    int
	CarSkuDetail           string
	ShelfAllocationBefore  string
	CommodityRestockDetail string
}

// CSV算法计算器
type CSVAlgorithmCalculator struct {
	inputFile  string
	outputFile string
}

// 创建CSV算法计算器
func NewCSVAlgorithmCalculator(inputFile, outputFile string) *CSVAlgorithmCalculator {
	return &CSVAlgorithmCalculator{
		inputFile:  inputFile,
		outputFile: outputFile,
	}
}

// 从CSV记录解析商品数据
func (cac *CSVAlgorithmCalculator) parseProductsFromRecord(record *CSVRecord) ([]Product, error) {
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

// 运行补货算法计算结果
func (cac *CSVAlgorithmCalculator) runReplenishmentAlgorithm(record *CSVRecord) (totalAmount int, skuCount int, finalTotalStock int, finalSkuCount int, err error) {
	// 解析商品数据
	products, err := cac.parseProductsFromRecord(record)
	if err != nil {
		return 0, 0, 0, 0, fmt.Errorf("解析商品数据失败: %v", err)
	}

	// 创建算法配置
	config := ReplenishmentConfig{
		TargetTotal:    record.PointForecastAmount,
		MaxCapacity:    record.PointMaxStock,
		MaxIterations:  200,
		ToleranceRatio: 0.1,
	}

	// 执行补货算法
	algorithm := NewReplenishmentAlgorithm(products, config)
	results, err := algorithm.Execute()
	if err != nil {
		return 0, 0, 0, 0, fmt.Errorf("算法执行失败: %v", err)
	}

	// 计算补货量统计
	totalAmount = 0
	skuCount = 0
	finalTotalStock = 0
	finalSkuCount = 0

	for _, result := range results {
		// 补货量统计
		totalAmount += result.ReplenishAmount
		if result.ReplenishAmount > 0 {
			skuCount++
		}

		// 补货后总库存统计
		finalTotalStock += result.FinalStock
		if result.FinalStock > 0 {
			finalSkuCount++
		}
	}

	return totalAmount, skuCount, finalTotalStock, finalSkuCount, nil
}

// 解析CSV记录
func (cac *CSVAlgorithmCalculator) parseCSVRecord(record []string) (*CSVRecord, error) {
	if len(record) < 32 {
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
		ReqID:                  record[1],
		PointMaxStock:          parseInt(record[9]),
		PointForecast5DayCnt:   parseInt(record[12]),
		PointForecastAmount:    parseInt(record[15]),
		CarSkuDetail:           record[25],
		ShelfAllocationBefore:  record[26],
		CommodityRestockDetail: record[31],
	}, nil
}

// 添加新列到CSV文件
func (cac *CSVAlgorithmCalculator) AddColumns() error {
	fmt.Printf("📖 读取CSV文件: %s\n", cac.inputFile)

	// 读取原始CSV文件
	inputFile, err := os.Open(cac.inputFile)
	if err != nil {
		return fmt.Errorf("无法打开输入文件: %v", err)
	}
	defer inputFile.Close()

	reader := csv.NewReader(inputFile)
	records, err := reader.ReadAll()
	if err != nil {
		return fmt.Errorf("读取CSV文件失败: %v", err)
	}

	if len(records) < 2 {
		return fmt.Errorf("CSV文件格式不正确，至少需要标题行和一行数据")
	}

	fmt.Printf("✅ 成功读取 %d 行记录（包含标题行）\n", len(records))

	// 创建输出CSV文件
	fmt.Printf("📝 创建输出文件: %s\n", cac.outputFile)
	outputFile, err := os.Create(cac.outputFile)
	if err != nil {
		return fmt.Errorf("无法创建输出文件: %v", err)
	}
	defer outputFile.Close()

	writer := csv.NewWriter(outputFile)
	defer writer.Flush()

	// 处理标题行 - 添加新的列
	header := records[0]
	newHeader := make([]string, len(header)+4)
	copy(newHeader, header)
	newHeader[len(header)] = "算法总补货量"     // 算法计算总补货量
	newHeader[len(header)+1] = "算法补货商品数"  // 算法计算补货商品种类数
	newHeader[len(header)+2] = "算法补货后总库存" // 算法计算补货后总库存
	newHeader[len(header)+3] = "算法补货后商品数" // 算法计算补货后商品种类数

	if err := writer.Write(newHeader); err != nil {
		return fmt.Errorf("写入标题行失败: %v", err)
	}

	fmt.Printf("✅ 新增列: 算法总补货量, 算法补货商品数, 算法补货后总库存, 算法补货后商品数\n")
	fmt.Printf("\n🔄 开始运行补货算法计算数据...\n")

	// 处理数据行
	successCount := 0
	errorCount := 0

	for i := 1; i < len(records); i++ {
		record := records[i]

		// 解析CSV记录
		csvRecord, err := cac.parseCSVRecord(record)
		if err != nil {
			fmt.Printf("⚠️  解析第%d行失败: %v，使用默认值\n", i+1, err)
			// 使用默认值
			newRecord := make([]string, len(newHeader))
			copy(newRecord, record)
			// 填充不足的字段
			for j := len(record); j < len(newHeader); j++ {
				newRecord[j] = "0"
			}
			if err := writer.Write(newRecord); err != nil {
				return fmt.Errorf("写入记录失败: %v", err)
			}
			errorCount++
			continue
		}

		// 运行补货算法计算结果
		var totalAmount, skuCount, finalTotalStock, finalSkuCount int
		if csvRecord.CarSkuDetail != "" && csvRecord.ShelfAllocationBefore != "" {
			fmt.Printf("🔄 计算 req_id=%s...", csvRecord.ReqID)
			totalAmount, skuCount, finalTotalStock, finalSkuCount, err = cac.runReplenishmentAlgorithm(csvRecord)
			if err != nil {
				fmt.Printf("失败: %v，使用默认值\n", err)
				totalAmount = 0
				skuCount = 0
				finalTotalStock = 0
				finalSkuCount = 0
				errorCount++
			} else {
				fmt.Printf("成功: 总补货量=%d, 补货商品数=%d, 补货后总库存=%d, 补货后商品数=%d\n",
					totalAmount, skuCount, finalTotalStock, finalSkuCount)
				successCount++
			}
		} else {
			fmt.Printf("⚠️  第%d行缺少必要数据，使用默认值\n", i+1)
			totalAmount = 0
			skuCount = 0
			finalTotalStock = 0
			finalSkuCount = 0
			errorCount++
		}

		// 创建新记录
		newRecord := make([]string, len(newHeader))
		copy(newRecord, record)
		// 填充不足的字段
		for j := len(record); j < len(header); j++ {
			newRecord[j] = ""
		}
		newRecord[len(header)] = strconv.Itoa(totalAmount)
		newRecord[len(header)+1] = strconv.Itoa(skuCount)
		newRecord[len(header)+2] = strconv.Itoa(finalTotalStock)
		newRecord[len(header)+3] = strconv.Itoa(finalSkuCount)

		if err := writer.Write(newRecord); err != nil {
			return fmt.Errorf("写入记录失败: %v", err)
		}
	}

	fmt.Printf("\n📊 处理完成统计:\n")
	fmt.Printf("  ✅ 算法计算成功: %d 行\n", successCount)
	fmt.Printf("  ⚠️  使用默认值: %d 行\n", errorCount)
	fmt.Printf("  📄 总计: %d 行数据\n", len(records)-1)

	return nil
}

func main() {
	if len(os.Args) != 3 {
		fmt.Printf("用法: %s <输入CSV文件> <输出CSV文件>\n", os.Args[0])
		fmt.Printf("示例: %s \"../data/分拣 case.csv\" \"../data/分拣 case_with_algorithm.csv\"\n", os.Args[0])
		fmt.Printf("\n说明:\n")
		fmt.Printf("  此程序会运行补货算法并在CSV文件中新增四列:\n")
		fmt.Printf("  - 算法总补货量: 补货算法计算的总补货量\n")
		fmt.Printf("  - 算法补货商品数: 补货算法计算的补货商品种类数\n")
		fmt.Printf("  - 算法补货后总库存: 补货算法计算的补货后总库存\n")
		fmt.Printf("  - 算法补货后商品数: 补货算法计算的补货后商品种类数\n")
		os.Exit(1)
	}

	inputFile := os.Args[1]
	outputFile := os.Args[2]

	fmt.Printf("🚀 CSV补货算法计算器启动\n")
	fmt.Printf("📁 输入文件: %s\n", inputFile)
	fmt.Printf("📁 输出文件: %s\n", outputFile)
	fmt.Printf("\n")

	// 检查输入文件是否存在
	if _, err := os.Stat(inputFile); os.IsNotExist(err) {
		fmt.Printf("❌ 错误: 输入文件不存在: %s\n", inputFile)
		os.Exit(1)
	}

	// 创建CSV算法计算器
	calculator := NewCSVAlgorithmCalculator(inputFile, outputFile)

	// 执行计算和添加列操作
	if err := calculator.AddColumns(); err != nil {
		fmt.Printf("❌ 操作失败: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("\n🎉 CSV文件更新完成！\n")
	fmt.Printf("✨ 新增的列（基于补货算法计算）:\n")
	fmt.Printf("   - 算法总补货量: 补货算法计算的总补货量\n")
	fmt.Printf("   - 算法补货商品数: 补货算法计算的补货商品种类数\n")
	fmt.Printf("   - 算法补货后总库存: 补货算法计算的补货后总库存\n")
	fmt.Printf("   - 算法补货后商品数: 补货算法计算的补货后商品种类数\n")
	fmt.Printf("📄 输出文件: %s\n", outputFile)
}
