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

// CSV记录结构（简化版）
type CSVRecordSimple struct {
	ReqID                  string
	PointMaxStock          int
	PointForecast5DayCnt   int
	PointForecastAmount    int
	CarSkuDetail           string
	ShelfAllocationBefore  string
	CommodityRestockDetail string
	PointExt               string
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
func (cac *CSVAlgorithmCalculator) parseProductsFromRecord(record *CSVRecordSimple) ([]Product, error) {
	// 解析车辆库存数据 (N_i)
	var carSkuData map[string]CarSkuData
	if err := json.Unmarshal([]byte(record.CarSkuDetail), &carSkuData); err != nil {
		return nil, fmt.Errorf("解析车辆库存数据失败: %v", err)
	}

	// 解析货架分配数据 (获取r_i比例和理论货道数)
	var shelfAllocations []ShelfAllocation
	if err := json.Unmarshal([]byte(record.ShelfAllocationBefore), &shelfAllocations); err != nil {
		return nil, fmt.Errorf("解析货架分配数据失败: %v", err)
	}

	// 解析point_ext字段获取当前库存
	var pointExtData map[string]int
	if record.PointExt == "" {
		return nil, fmt.Errorf("point_ext字段为空，无法获取当前库存数据")
	}

	// 尝试解析point_ext字段 - 新格式：{"商品ID": 库存数量}
	if err := json.Unmarshal([]byte(record.PointExt), &pointExtData); err != nil {
		return nil, fmt.Errorf("解析point_ext字段失败: %v", err)
	}

	// 添加调试信息
	fmt.Printf("🔍 调试信息 - point_ext解析结果: %+v\n", pointExtData)
	fmt.Printf("🔍 调试信息 - shelf_allocation商品数量: %d\n", len(shelfAllocations))

	// 创建商品映射
	productMap := make(map[int]*Product)

	// 从货架分配数据中创建所有商品信息
	for _, shelf := range shelfAllocations {
		// 检查point_ext中是否有该商品的库存数据
		currentStock, exists := pointExtData[strconv.Itoa(shelf.CommodityID)]
		if !exists {
			// 如果point_ext中没有该商品，库存设置为0
			fmt.Printf("⚠️  商品 %d 在point_ext中不存在，库存设置为0\n", shelf.CommodityID)
			currentStock = 0
		}

		productMap[shelf.CommodityID] = &Product{
			ID:             strconv.Itoa(shelf.CommodityID),
			Name:           fmt.Sprintf("商品_%d", shelf.CommodityID),
			WarehouseStock: 0,                                                                        // 稍后从车辆库存中填充
			CurrentStock:   currentStock,                                                             // 使用point_ext的库存数据，不存在则为0
			MaxAllowed:     int(math.Ceil(float64(record.PointForecast5DayCnt) * shelf.Score * 1.2)), // X_i = 5天预测量 * 比例，向上取整
			ExpectedRatio:  shelf.Score,                                                              // 保持原始比例
		}
	}

	fmt.Printf("🔍 调试信息 - 成功创建商品数量: %d\n", len(productMap))

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
func (cac *CSVAlgorithmCalculator) runReplenishmentAlgorithm(record *CSVRecordSimple) (totalAmount int, skuCount int, finalTotalStock int, finalSkuCount int, err error) {
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
func (cac *CSVAlgorithmCalculator) parseCSVRecord(record []string) (*CSVRecordSimple, error) {
	if len(record) < 40 {
		return nil, fmt.Errorf("CSV记录字段不足，需要至少40个字段，当前只有%d个", len(record))
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

	// 重新构建完整的point_ext字段
	pointExt := cac.reconstructPointExt(record)

	return &CSVRecordSimple{
		ReqID:                  record[1],
		PointMaxStock:          parseInt(record[9]),
		PointForecast5DayCnt:   parseInt(record[12]),
		PointForecastAmount:    parseInt(record[15]),
		CarSkuDetail:           record[25],
		ShelfAllocationBefore:  record[26],
		CommodityRestockDetail: record[31],
		PointExt:               pointExt, // 使用重新构建的point_ext字段
	}, nil
}

// 重新构建完整的point_ext字段
func (cac *CSVAlgorithmCalculator) reconstructPointExt(record []string) string {
	// 检查第39列（索引38）是否包含完整的point_ext JSON
	if len(record) > 38 && record[38] != "" {
		field := record[38]
		// 检查是否是有效的JSON格式
		if strings.HasPrefix(field, "{") && strings.HasSuffix(field, "}") {
			fmt.Printf("🔍 调试信息 - 找到完整的point_ext JSON: %s\n", field)
			return field
		}
	}

	// 如果没有找到完整的JSON，尝试重建（保留原有逻辑作为备用）
	fmt.Printf("🔍 调试信息 - 第39列没有完整JSON，尝试重建...\n")

	// 从第35列开始，搜索所有包含JSON片段的列
	var jsonParts []string

	// 从第35列开始查找JSON片段，搜索范围扩大到更多列
	for i := 34; i < len(record) && i < 70; i++ { // 扩大搜索范围
		field := record[i]
		if field != "" {
			// 检查是否包含JSON片段的关键特征
			if strings.Contains(field, "commodity_id") ||
				strings.Contains(field, "qty") ||
				strings.Contains(field, "\"") {
				jsonParts = append(jsonParts, field)
				fmt.Printf("🔍 调试信息 - 找到JSON片段[%d]: %s\n", i, field)
			}
		}
	}

	if len(jsonParts) == 0 {
		fmt.Printf("🔍 调试信息 - 没有找到任何JSON片段\n")
		return "{}" // 返回空JSON对象
	}

	fmt.Printf("🔍 调试信息 - 总共找到 %d 个JSON片段\n", len(jsonParts))

	// 改进的JSON重建逻辑
	// 分析JSON片段，寻找商品ID和数量的配对
	var commodityData []string
	var currentCommodityID string
	var currentQty string

	// 遍历所有JSON片段
	for i := 0; i < len(jsonParts); i++ {
		part := jsonParts[i]
		fmt.Printf("🔍 调试信息 - 处理片段[%d]: %s\n", i, part)

		// 如果这个片段包含商品ID
		if strings.Contains(part, "commodity_id") {
			// 提取商品ID
			commodityID := ""
			if strings.Contains(part, "\"") {
				// 提取引号中的数字
				parts := strings.Split(part, "\"")
				for _, p := range parts {
					if p != "" && p != "commodity_id" && p != ":" && p != "{" && p != "}" {
						// 检查是否是数字
						if _, err := strconv.Atoi(p); err == nil {
							commodityID = p
							break
						}
					}
				}
			}

			if commodityID != "" {
				currentCommodityID = commodityID
				fmt.Printf("🔍 调试信息 - 找到商品ID: %s\n", commodityID)
			}
		}

		// 如果这个片段包含数量
		if strings.Contains(part, "qty") {
			// 提取数量
			qty := ""
			if strings.Contains(part, "\"") {
				parts := strings.Split(part, "\"")
				for _, p := range parts {
					if p != "" && p != "qty" && p != ":" && p != "}" {
						// 检查是否是数字
						if _, err := strconv.Atoi(p); err == nil {
							qty = p
							break
						}
					}
				}
			}

			if qty != "" {
				currentQty = qty
				fmt.Printf("🔍 调试信息 - 找到数量: %s\n", qty)
			}
		}

		// 如果找到了商品ID和数量，构建完整的商品数据
		if currentCommodityID != "" && currentQty != "" {
			commodityData = append(commodityData, fmt.Sprintf("\"%s\":{\"commodity_id\":%s,\"qty\":%s}",
				currentCommodityID, currentCommodityID, currentQty))
			fmt.Printf("🔍 调试信息 - 构建商品数据: %s\n", commodityData[len(commodityData)-1])
			// 重置当前值，准备下一个商品
			currentCommodityID = ""
			currentQty = ""
		}
	}

	// 组合所有商品数据
	reconstructed := "{"
	for i, data := range commodityData {
		if i > 0 {
			reconstructed += ","
		}
		reconstructed += data
	}
	reconstructed += "}"

	// 添加调试信息
	fmt.Printf("🔍 调试信息 - 重建的point_ext: %s\n", reconstructed)
	fmt.Printf("🔍 调试信息 - 找到的商品数量: %d\n", len(commodityData))

	return reconstructed
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
