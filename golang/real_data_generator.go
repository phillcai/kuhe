package main

import (
	"encoding/csv"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"os"
	"sort"
	"strconv"
	"strings"
	"time"
)

// 重新定义必要的类型（避免导入冲突）
type RealVehiclePoint struct {
	ID             string   `json:"id"`
	Longitude      float64  `json:"longitude"`
	Latitude       float64  `json:"latitude"`
	IsShortage     bool     `json:"is_shortage"`
	CompatVehicles []string `json:"compat_vehicles"`
}

type RealVehicle struct {
	ID     string  `json:"id"`
	Ratio  float64 `json:"ratio"`
	Region int     `json:"region"`
}

// 缺货数据结构
type StockOutData struct {
	Code        int   `json:"code"`
	CurrentTime int64 `json:"currentTime"`
	Data        struct {
		List []struct {
			PointID      int    `json:"point_id"`
			StockOutTime string `json:"stock_out_time"`
		} `json:"list"`
	} `json:"data"`
}

// 点位原始数据结构
type RawPointData struct {
	ID           int
	PointName    string
	PointType    string
	MaxStock     int
	Latitude     float64
	Longitude    float64
	Address      string
	CreateTime   string
	DataType     string
	StartTime    string
	EndTime      string
	Remark       string
	Escort       string
	CarTypeLimit int // car_type_limit字段：1表示只能14车访问，其他值表示所有车可访问
}

// 数据处理器
type RealDataProcessor struct {
	PointsData  []RawPointData
	ShortageMap map[int]bool
	TimeMatrix  map[string]map[string]float64
}

// 测试用例数据结构
type RealTestCaseData struct {
	Points     []RealVehiclePoint `json:"points"`
	Vehicles   []RealVehicle      `json:"vehicles"`
	TimeMatrix [][]float64        `json:"time_matrix"`
	PointIDs   []string           `json:"point_ids"`
}

// 构造函数
func NewRealDataProcessor() *RealDataProcessor {
	return &RealDataProcessor{
		ShortageMap: make(map[int]bool),
		TimeMatrix:  make(map[string]map[string]float64),
	}
}

// 步骤1：解析点位数据
func (dp *RealDataProcessor) ParsePointData(filename string) error {
	fmt.Println("🔄 步骤1：解析点位数据...")

	file, err := os.Open(filename)
	if err != nil {
		return fmt.Errorf("打开文件失败: %v", err)
	}
	defer file.Close()

	reader := csv.NewReader(file)
	records, err := reader.ReadAll()
	if err != nil {
		return fmt.Errorf("读取CSV失败: %v", err)
	}

	// 使用map去重
	pointMap := make(map[int]RawPointData)
	duplicateCount := 0

	// 跳过标题行
	for i := 1; i < len(records); i++ {
		record := records[i]
		if len(record) < 14 { // 现在需要至少14列（包含car_type_limit）
			continue
		}

		id, _ := strconv.Atoi(record[0])
		maxStock, _ := strconv.Atoi(record[3])
		lat, _ := strconv.ParseFloat(record[4], 64)
		lon, _ := strconv.ParseFloat(record[5], 64)
		carTypeLimit, _ := strconv.Atoi(record[13]) // car_type_limit字段

		pointData := RawPointData{
			ID:           id,
			PointName:    record[1],
			PointType:    record[2],
			MaxStock:     maxStock,
			Latitude:     lat,
			Longitude:    lon,
			Address:      record[6],
			Remark:       record[11],
			Escort:       record[12],
			CarTypeLimit: carTypeLimit,
		}

		// 检查是否重复
		if _, exists := pointMap[id]; exists {
			duplicateCount++
			// 保留第一个，跳过重复的
			continue
		}

		pointMap[id] = pointData
	}

	// 将去重后的数据转换为切片
	dp.PointsData = make([]RawPointData, 0, len(pointMap))
	for _, pointData := range pointMap {
		dp.PointsData = append(dp.PointsData, pointData)
	}

	fmt.Printf("✅ 成功解析 %d 个点位", len(dp.PointsData))
	if duplicateCount > 0 {
		fmt.Printf("（跳过 %d 个重复点位）", duplicateCount)
	}
	fmt.Println()
	return nil
}

// 步骤2：解析缺货数据
func (dp *RealDataProcessor) ParseShortageData(filename string) error {
	fmt.Println("🔄 步骤2：解析缺货数据...")

	content, err := ioutil.ReadFile(filename)
	if err != nil {
		return fmt.Errorf("读取文件失败: %v", err)
	}

	var stockOutData StockOutData
	if err := json.Unmarshal(content, &stockOutData); err != nil {
		return fmt.Errorf("解析JSON失败: %v", err)
	}

	// 计算12小时后的时间
	now := time.Now()
	future12Hours := now.Add(24 * time.Hour)

	shortageCount := 0
	for _, item := range stockOutData.Data.List {
		// 解析时间字符串
		stockOutTime, err := time.Parse("2006-01-02 15:04:05", item.StockOutTime)
		if err != nil {
			continue
		}

		// 如果缺货时间在未来12小时内，标记为缺货
		if stockOutTime.After(now) && stockOutTime.Before(future12Hours) {
			dp.ShortageMap[item.PointID] = true
			shortageCount++
		}
	}

	fmt.Printf("✅ 识别出 %d 个缺货点位（未来12小时内）\n", shortageCount)
	return nil
}

// 步骤3：解析时间矩阵数据
func (dp *RealDataProcessor) ParseTimeMatrix(filename string) error {
	fmt.Println("🔄 步骤3：解析时间矩阵数据...")

	file, err := os.Open(filename)
	if err != nil {
		return fmt.Errorf("打开文件失败: %v", err)
	}
	defer file.Close()

	reader := csv.NewReader(file)
	records, err := reader.ReadAll()
	if err != nil {
		return fmt.Errorf("读取CSV失败: %v", err)
	}

	// 初始化时间矩阵
	for _, pointData := range dp.PointsData {
		pointID := strconv.Itoa(pointData.ID)
		if dp.TimeMatrix[pointID] == nil {
			dp.TimeMatrix[pointID] = make(map[string]float64)
		}
	}

	// 解析时间数据（跳过标题行）
	timeCount := 0
	for i := 1; i < len(records); i++ {
		record := records[i]
		if len(record) < 3 {
			continue
		}

		fromPointID := record[0]
		toPointID := record[1]

		// 处理duration字符串，移除逗号
		durationStr := strings.ReplaceAll(record[2], ",", "")
		duration, err := strconv.ParseFloat(durationStr, 64)
		if err != nil {
			continue
		}

		// 转换为分钟（原数据是秒）
		durationMinutes := duration / 60.0

		// 跳过起点为-2的数据（仓库到点位的数据）
		if fromPointID == "-2" {
			continue
		}

		// 存储时间数据
		if dp.TimeMatrix[fromPointID] == nil {
			dp.TimeMatrix[fromPointID] = make(map[string]float64)
		}
		dp.TimeMatrix[fromPointID][toPointID] = durationMinutes
		timeCount++
	}

	fmt.Printf("✅ 成功解析 %d 条时间矩阵数据\n", timeCount)
	return nil
}

// 步骤4：生成测试用例数据
func (dp *RealDataProcessor) GenerateTestCase() (*RealTestCaseData, error) {
	fmt.Println("🔄 步骤4：生成测试用例数据...")

	// 按经度排序点位（从东到西）
	sort.Slice(dp.PointsData, func(i, j int) bool {
		return dp.PointsData[i].Longitude < dp.PointsData[j].Longitude
	})

	// 生成点位数据
	points := make([]RealVehiclePoint, 0)
	pointIDs := make([]string, 0)

	for _, pointData := range dp.PointsData {
		pointID := strconv.Itoa(pointData.ID)
		pointIDs = append(pointIDs, pointID)

		// 确定兼容车辆
		compatVehicles := []string{"2", "14", "15"} // 默认所有车辆都兼容

		// 检查car_type_limit字段：1表示只能14车访问
		if pointData.CarTypeLimit == 1 {
			compatVehicles = []string{"14"} // 只有14车能访问受限点位
		}

		// 检查是否缺货
		isShortage := dp.ShortageMap[pointData.ID]

		point := RealVehiclePoint{
			ID:             pointID,
			Longitude:      pointData.Longitude,
			Latitude:       pointData.Latitude,
			IsShortage:     isShortage,
			CompatVehicles: compatVehicles,
		}

		points = append(points, point)
	}

	// 生成车辆数据（从东到西排序）
	vehicles := []RealVehicle{
		{ID: "15", Ratio: 0.26, Region: 2}, // 最西边
		{ID: "14", Ratio: 0.37, Region: 1}, // 中间
		{ID: "2", Ratio: 0.37, Region: 0},  // 最东边
	}

	// 构建时间矩阵
	timeMatrix := dp.buildTimeMatrix(pointIDs)

	// 创建测试用例数据
	testCaseData := &RealTestCaseData{
		Points:     points,
		Vehicles:   vehicles,
		TimeMatrix: timeMatrix,
		PointIDs:   pointIDs,
	}

	// 统计信息
	shortageCount := 0
	restrictedCount := 0
	for _, point := range points {
		if point.IsShortage {
			shortageCount++
		}
		if len(point.CompatVehicles) == 1 {
			restrictedCount++
		}
	}

	fmt.Printf("✅ 生成测试用例完成:\n")
	fmt.Printf("   - 总点位数: %d\n", len(points))
	fmt.Printf("   - 缺货点位: %d\n", shortageCount)
	fmt.Printf("   - 受限点位: %d (只能14车访问)\n", restrictedCount)
	fmt.Printf("   - 车辆数: %d\n", len(vehicles))

	return testCaseData, nil
}

// 构建时间矩阵
func (dp *RealDataProcessor) buildTimeMatrix(pointIDs []string) [][]float64 {
	n := len(pointIDs)
	matrix := make([][]float64, n)
	for i := range matrix {
		matrix[i] = make([]float64, n)
	}

	// 填充时间矩阵
	for i, fromID := range pointIDs {
		for j, toID := range pointIDs {
			if i == j {
				matrix[i][j] = 0
			} else if time, exists := dp.TimeMatrix[fromID][toID]; exists {
				matrix[i][j] = time
			} else {
				// 如果没有直接的时间数据，使用估算值
				matrix[i][j] = dp.estimateTime(fromID, toID)
			}
		}
	}

	return matrix
}

// 估算时间（基于经纬度距离）
func (dp *RealDataProcessor) estimateTime(fromID, toID string) float64 {
	// 找到对应的点位数据
	var fromPoint, toPoint *RawPointData

	for _, point := range dp.PointsData {
		if strconv.Itoa(point.ID) == fromID {
			fromPoint = &point
		}
		if strconv.Itoa(point.ID) == toID {
			toPoint = &point
		}
	}

	if fromPoint == nil || toPoint == nil {
		return 30.0 // 默认30分钟
	}

	// 简单的欧几里得距离估算（新加坡很小，可以近似）
	latDiff := fromPoint.Latitude - toPoint.Latitude
	lonDiff := fromPoint.Longitude - toPoint.Longitude
	distance := (latDiff*latDiff + lonDiff*lonDiff) * 111000 // 转换为米

	// 假设平均速度30km/h，转换为分钟
	timeMinutes := distance / 500 // 简化计算

	if timeMinutes < 5 {
		timeMinutes = 5 // 最小5分钟
	} else if timeMinutes > 60 {
		timeMinutes = 60 // 最大60分钟
	}

	return timeMinutes
}

// 打印统计信息
func (dp *RealDataProcessor) PrintStatistics(testData *RealTestCaseData) {
	fmt.Println("\n📊 数据统计信息:")
	fmt.Printf("总点位数: %d\n", len(testData.Points))

	shortageCount := 0
	restrictedCount := 0
	for _, point := range testData.Points {
		if point.IsShortage {
			shortageCount++
		}
		if len(point.CompatVehicles) == 1 && point.CompatVehicles[0] == "14" {
			restrictedCount++
		}
	}

	fmt.Printf("缺货点位: %d (%.1f%%)\n", shortageCount, float64(shortageCount)/float64(len(testData.Points))*100)
	fmt.Printf("受限点位: %d (%.1f%%) - 只能14车访问\n", restrictedCount, float64(restrictedCount)/float64(len(testData.Points))*100)

	fmt.Println("\n车辆配置:")
	for _, vehicle := range testData.Vehicles {
		fmt.Printf("  车辆%s: 目标比例 %.1f%%, 区域 %d\n", vehicle.ID, vehicle.Ratio*100, vehicle.Region)
	}

	// 地理分布统计
	fmt.Println("\n地理分布:")
	if len(testData.Points) > 0 {
		minLon := testData.Points[0].Longitude
		maxLon := testData.Points[0].Longitude
		minLat := testData.Points[0].Latitude
		maxLat := testData.Points[0].Latitude

		for _, point := range testData.Points {
			if point.Longitude < minLon {
				minLon = point.Longitude
			}
			if point.Longitude > maxLon {
				maxLon = point.Longitude
			}
			if point.Latitude < minLat {
				minLat = point.Latitude
			}
			if point.Latitude > maxLat {
				maxLat = point.Latitude
			}
		}

		fmt.Printf("  经度范围: %.4f ~ %.4f\n", minLon, maxLon)
		fmt.Printf("  纬度范围: %.4f ~ %.4f\n", minLat, maxLat)
	}
}

// 生成Go代码测试用例
func (dp *RealDataProcessor) GenerateGoTestCase(testData *RealTestCaseData, filename string) error {
	fmt.Println("🔄 生成Go代码测试用例...")

	var sb strings.Builder

	sb.WriteString("package main\n\n")
	sb.WriteString("import (\n")
	sb.WriteString("\t\"fmt\"\n")
	sb.WriteString("\t\"log\"\n")
	sb.WriteString(")\n\n")

	sb.WriteString("// 基于真实数据生成的测试用例\n")
	sb.WriteString("func generateRealDataTestCase() ([]VehiclePoint, []Vehicle, [][]float64) {\n")

	// 生成点位数据（只显示前10个作为示例）
	sb.WriteString("\t// 点位数据 (按经度从东到西排序) - 显示前10个\n")
	sb.WriteString("\tpoints := []VehiclePoint{\n")

	maxPoints := 10
	if len(testData.Points) < maxPoints {
		maxPoints = len(testData.Points)
	}

	for i := 0; i < maxPoints; i++ {
		point := testData.Points[i]
		compatVehiclesStr := fmt.Sprintf("[]string{\"%s\"}", strings.Join(point.CompatVehicles, "\", \""))
		sb.WriteString(fmt.Sprintf("\t\t{ID: \"%s\", Longitude: %.6f, Latitude: %.6f, IsShortage: %t, CompatVehicles: %s},\n",
			point.ID, point.Longitude, point.Latitude, point.IsShortage, compatVehiclesStr))
	}
	sb.WriteString("\t\t// ... 更多点位数据 ...\n")
	sb.WriteString("\t}\n\n")

	// 添加完整点位数据的注释
	sb.WriteString(fmt.Sprintf("\t// 实际数据包含 %d 个点位，其中 %d 个缺货点位\n",
		len(testData.Points), dp.countShortagePoints(testData.Points)))
	sb.WriteString("\t// 如需完整数据，请从JSON文件加载\n\n")

	// 生成车辆数据
	sb.WriteString("\t// 车辆数据 (从东到西排序: 2, 14, 15)\n")
	sb.WriteString("\tvehicles := []Vehicle{\n")
	for _, vehicle := range testData.Vehicles {
		sb.WriteString(fmt.Sprintf("\t\t{ID: \"%s\", Ratio: %.2f, Region: %d},\n",
			vehicle.ID, vehicle.Ratio, vehicle.Region))
	}
	sb.WriteString("\t}\n\n")

	// 生成时间矩阵（简化版本）
	sb.WriteString("\t// 时间矩阵 (分钟) - 简化显示前10x10\n")
	sb.WriteString("\ttimeMatrix := [][]float64{\n")

	maxRows := 10
	if len(testData.TimeMatrix) < maxRows {
		maxRows = len(testData.TimeMatrix)
	}

	for i := 0; i < maxRows; i++ {
		sb.WriteString("\t\t{")
		maxCols := 10
		if len(testData.TimeMatrix[i]) < maxCols {
			maxCols = len(testData.TimeMatrix[i])
		}
		for j := 0; j < maxCols; j++ {
			if j > 0 {
				sb.WriteString(", ")
			}
			sb.WriteString(fmt.Sprintf("%.1f", testData.TimeMatrix[i][j]))
		}
		sb.WriteString("},\n")
	}
	sb.WriteString("\t\t// ... 更多矩阵数据 ...\n")
	sb.WriteString("\t}\n\n")

	sb.WriteString("\treturn points, vehicles, timeMatrix\n")
	sb.WriteString("}\n\n")

	// 添加运行测试的函数
	sb.WriteString("// 运行真实数据测试\n")
	sb.WriteString("func runRealDataTest() {\n")
	sb.WriteString("\tfmt.Println(\"=== 基于真实数据的车辆点位分配测试 ===\")\n")
	sb.WriteString("\tfmt.Println(\"注意：此为简化数据，完整测试请使用JSON文件\")\n")
	sb.WriteString("\t\n")
	sb.WriteString("\t// 创建算法实例\n")
	sb.WriteString("\talgorithm := NewVehicleAllocationAlgorithm()\n")
	sb.WriteString("\t\n")
	sb.WriteString("\t// 获取测试数据\n")
	sb.WriteString("\tpoints, vehicles, timeMatrix := generateRealDataTestCase()\n")
	sb.WriteString("\t\n")
	sb.WriteString("\t// 初始化算法\n")
	sb.WriteString("\tif err := algorithm.Initialize(points, vehicles, timeMatrix); err != nil {\n")
	sb.WriteString("\t\tlog.Fatalf(\"算法初始化失败: %v\", err)\n")
	sb.WriteString("\t}\n")
	sb.WriteString("\t\n")
	sb.WriteString("\t// 执行算法\n")
	sb.WriteString("\tresults, err := algorithm.Execute()\n")
	sb.WriteString("\tif err != nil {\n")
	sb.WriteString("\t\tlog.Fatalf(\"算法执行失败: %v\", err)\n")
	sb.WriteString("\t}\n")
	sb.WriteString("\t\n")
	sb.WriteString("\t// 打印结果\n")
	sb.WriteString("\talgorithm.PrintResults(results)\n")
	sb.WriteString("\t\n")
	sb.WriteString("\t// 验证结果\n")
	sb.WriteString("\tvalidateResults(results, points, vehicles)\n")
	sb.WriteString("}\n")

	// 写入文件
	if err := ioutil.WriteFile(filename, []byte(sb.String()), 0644); err != nil {
		return fmt.Errorf("写入Go代码文件失败: %v", err)
	}

	fmt.Printf("✅ Go测试用例代码已保存到: %s\n", filename)
	return nil
}

// 统计缺货点位数量
func (dp *RealDataProcessor) countShortagePoints(points []RealVehiclePoint) int {
	count := 0
	for _, point := range points {
		if point.IsShortage {
			count++
		}
	}
	return count
}

// 保存测试用例到JSON文件
func (dp *RealDataProcessor) SaveTestCase(testData *RealTestCaseData, filename string) error {
	data, err := json.MarshalIndent(testData, "", "  ")
	if err != nil {
		return fmt.Errorf("序列化数据失败: %v", err)
	}

	if err := ioutil.WriteFile(filename, data, 0644); err != nil {
		return fmt.Errorf("写入文件失败: %v", err)
	}

	fmt.Printf("✅ 测试用例已保存到: %s\n", filename)
	return nil
}

// 主函数：生成基于真实数据的测试用例
func main() {
	fmt.Println("🚀 开始生成车辆点位分配算法测试用例")
	fmt.Println("=====================================")

	// 创建数据处理器
	processor := NewRealDataProcessor()

	// 数据文件路径
	dataDir := "../data"
	pointFile := dataDir + "/point.csv"
	shortageFile := dataDir + "/point_stock_out.txt"
	timeMatrixFile := dataDir + "/duration_point.csv"

	// 检查文件是否存在
	files := []string{pointFile, shortageFile, timeMatrixFile}
	for _, file := range files {
		if _, err := os.Stat(file); os.IsNotExist(err) {
			fmt.Printf("❌ 数据文件不存在: %s\n", file)
			fmt.Println("请确保数据文件存在于 ../data/ 目录下")
			return
		}
	}

	// 步骤1：解析点位数据
	if err := processor.ParsePointData(pointFile); err != nil {
		fmt.Printf("❌ 解析点位数据失败: %v\n", err)
		return
	}

	// 步骤2：解析缺货数据
	if err := processor.ParseShortageData(shortageFile); err != nil {
		fmt.Printf("❌ 解析缺货数据失败: %v\n", err)
		return
	}

	// 步骤3：解析时间矩阵数据
	if err := processor.ParseTimeMatrix(timeMatrixFile); err != nil {
		fmt.Printf("❌ 解析时间矩阵数据失败: %v\n", err)
		return
	}

	// 步骤4：生成测试用例
	testData, err := processor.GenerateTestCase()
	if err != nil {
		fmt.Printf("❌ 生成测试用例失败: %v\n", err)
		return
	}

	// 打印统计信息
	processor.PrintStatistics(testData)

	// 保存测试用例
	jsonFile := "real_data_test_case.json"
	if err := processor.SaveTestCase(testData, jsonFile); err != nil {
		fmt.Printf("❌ 保存JSON测试用例失败: %v\n", err)
		return
	}

	// 生成Go代码测试用例
	goFile := "real_data_test.go"
	if err := processor.GenerateGoTestCase(testData, goFile); err != nil {
		fmt.Printf("❌ 生成Go代码测试用例失败: %v\n", err)
		return
	}

	fmt.Println("\n🎉 测试用例生成完成！")
	fmt.Println("生成的文件:")
	fmt.Printf("  - %s (JSON格式完整测试数据)\n", jsonFile)
	fmt.Printf("  - %s (Go代码简化测试用例)\n", goFile)

	fmt.Println("\n下一步操作:")
	fmt.Println("  1. 查看生成的测试数据")
	fmt.Println("  2. 运行测试: go run vehicle_allocation.go real_data_test.go vehicle_allocation_example.go clustering_utils.go")
	fmt.Println("  3. 根据需要调整算法参数")
}
