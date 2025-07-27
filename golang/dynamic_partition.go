package main

import (
	"encoding/csv"
	"fmt"
	"log"
	"math"
	"math/rand"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"
)

// ============= 配置管理 =============

// Config 算法配置参数
type Config struct {
	// 基础参数
	NClusters     int     `json:"n_clusters"`     // 聚类组数
	MaxIterations int     `json:"max_iterations"` // 最大迭代次数
	MinInterval   float64 `json:"min_interval"`   // 时间窗口最小间隔（分钟）

	// 距离权重参数
	TimeWeight float64 `json:"time_weight"` // 行驶时长权重
	GeoWeight  float64 `json:"geo_weight"`  // 地理距离权重

	// 优化参数
	StdFactor    float64 `json:"std_factor"`     // 离群点判定标准差倍数
	ThresholdKm  float64 `json:"threshold_km"`   // 孤立点归组阈值（公里）
	MaxOptimIter int     `json:"max_optim_iter"` // 优化最大迭代次数

	// 模拟退火参数
	InitTemp float64 `json:"init_temp"` // 初始温度
	CoolRate float64 `json:"cool_rate"` // 冷却率
	MinTemp  float64 `json:"min_temp"`  // 最小温度

	// 约束参数
	TimeWindowStart float64 `json:"time_window_start"` // 主时间窗开始时间（分钟）
	TimeWindowEnd   float64 `json:"time_window_end"`   // 主时间窗结束时间（分钟）

	// 输出参数
	Verbose    bool   `json:"verbose"`     // 详细输出
	OutputPath string `json:"output_path"` // 输出路径

	// 补货点位优先策略参数
	RecallPointsPriority    bool `json:"recall_points_priority"`    // 启用补货点位优先策略
	StrictRecallConstraints bool `json:"strict_recall_constraints"` // 对补货点位使用更严格的约束
	SkipLoadBalancing       bool `json:"skip_load_balancing"`       // 是否跳过负载均衡

	// 两阶段分配参数
	EnableSecondStage    bool    `json:"enable_second_stage"`    // 启用第二阶段分配
	LoadBalanceTolerance float64 `json:"load_balance_tolerance"` // 负载均衡容忍度（如0.3表示30%）
}

// DefaultConfig 返回默认配置
func DefaultConfig() *Config {
	return &Config{
		NClusters:       3,
		MaxIterations:   100,
		MinInterval:     120.0,
		TimeWeight:      0.7,
		GeoWeight:       0.3,
		StdFactor:       2.0,
		ThresholdKm:     20.0,
		MaxOptimIter:    50,
		InitTemp:        100.0,
		CoolRate:        0.95,
		MinTemp:         0.1,
		TimeWindowStart: 540.0,  // 9:00
		TimeWindowEnd:   1260.0, // 21:00
		Verbose:         true,
		OutputPath:      "../output",

		// 补货点位优先策略默认值
		RecallPointsPriority:    false, // 默认关闭
		StrictRecallConstraints: false, // 默认关闭
		SkipLoadBalancing:       false, // 默认关闭

		// 两阶段分配默认值
		EnableSecondStage:    false, // 默认关闭
		LoadBalanceTolerance: 0.3,   // 30%容忍度
	}
}

// ============= 数据结构定义 =============

// TimeWindow 时间窗口结构
type TimeWindow struct {
	Start string `json:"start"`
	End   string `json:"end"`
}

// Point 点位结构
type Point struct {
	ID          int          `json:"id"`
	Longitude   float64      `json:"longitude"`
	Latitude    float64      `json:"latitude"`
	TimeWindows []TimeWindow `json:"time_windows"`
}

// TravelTimeMatrix 行驶时长矩阵
type TravelTimeMatrix struct {
	Times          [][]float64 `json:"times"`
	Size           int         `json:"size"`
	PointIDToIndex map[int]int `json:"point_id_to_index"`
}

// ConstraintStatus 约束状态
type ConstraintStatus struct {
	TimeWindowViolations int     `json:"time_window_violations"`
	LoadBalanceScore     float64 `json:"load_balance_score"`
	GeographicSpread     float64 `json:"geographic_spread"`
	ConstraintsSatisfied bool    `json:"constraints_satisfied"`
}

// PerformanceMetrics 性能指标
type PerformanceMetrics struct {
	TotalDistance      float64 `json:"total_distance"`
	AverageGroupSize   float64 `json:"average_group_size"`
	LoadBalanceIndex   float64 `json:"load_balance_index"`
	TimeWindowCoverage float64 `json:"time_window_coverage"`
	ExecutionTime      float64 `json:"execution_time"`
	IterationsUsed     int     `json:"iterations_used"`
}

// Result 算法结果
type Result struct {
	Groups      map[int][]int       `json:"groups"`
	Performance *PerformanceMetrics `json:"performance"`
	Constraints *ConstraintStatus   `json:"constraints"`
	Config      *Config             `json:"config"`
	Timestamp   time.Time           `json:"timestamp"`
}

// ============= 核心算法类 =============

// DynamicPartitionAlgorithm 动态分区算法
type DynamicPartitionAlgorithm struct {
	config        *Config
	pointDict     map[int]*Point
	travelMatrix  *TravelTimeMatrix
	recallPoints  map[int]bool
	features      map[int][]float64
	distanceCache map[string]float64
	logger        *log.Logger
}

// NewDynamicPartitionAlgorithm 创建新的算法实例
func NewDynamicPartitionAlgorithm(config *Config) *DynamicPartitionAlgorithm {
	return &DynamicPartitionAlgorithm{
		config:        config,
		pointDict:     make(map[int]*Point),
		recallPoints:  make(map[int]bool),
		features:      make(map[int][]float64),
		distanceCache: make(map[string]float64),
		logger:        log.New(os.Stdout, "[动态分区] ", log.LstdFlags),
	}
}

// GetConfig 获取算法配置
func (alg *DynamicPartitionAlgorithm) GetConfig() *Config {
	return alg.config
}

// GetPointDict 获取点位字典
func (alg *DynamicPartitionAlgorithm) GetPointDict() map[int]*Point {
	return alg.pointDict
}

// GetRecallPoints 获取补货点位映射
func (alg *DynamicPartitionAlgorithm) GetRecallPoints() map[int]bool {
	return alg.recallPoints
}

// ============= 第一阶段：数据预处理与约束分析 =============

// LoadData 加载数据
func (alg *DynamicPartitionAlgorithm) LoadData(pointsPath, travelTimePath, recallPointsPath string) error {
	alg.logInfo("开始数据预处理阶段...")

	// 1.1 加载点位信息
	if err := alg.loadPointsFromCSV(pointsPath); err != nil {
		return fmt.Errorf("加载点位信息失败: %v", err)
	}
	alg.logInfo("成功读取 %d 个点位", len(alg.pointDict))

	// 1.2 加载行驶时长矩阵
	if err := alg.loadTravelTimeMatrix(travelTimePath); err != nil {
		alg.logInfo("警告：无法读取行驶时长文件，将使用地理距离: %v", err)
	} else {
		alg.logInfo("成功读取行驶时长矩阵: %d x %d", alg.travelMatrix.Size, alg.travelMatrix.Size)
	}

	// 1.3 加载补货点位
	if err := alg.loadRecallPoints(recallPointsPath); err != nil {
		alg.logInfo("警告：无法读取补货点位文件: %v", err)
	} else {
		alg.logInfo("成功读取补货点位: %d 个", len(alg.recallPoints))
	}

	// 1.4 构建特征向量
	if err := alg.buildFeatures(); err != nil {
		return fmt.Errorf("构建特征向量失败: %v", err)
	}

	// 1.5 根据配置决定是否启用两阶段分配
	if !alg.config.EnableSecondStage {
		// 单阶段模式：过滤非补货点位，只保留补货点位
		alg.logInfo("单阶段模式：过滤非补货点位，只保留补货点位...")
		filteredPointDict := make(map[int]*Point)
		for pid, point := range alg.pointDict {
			if alg.recallPoints[pid] {
				filteredPointDict[pid] = point
			}
		}
		alg.pointDict = filteredPointDict
		alg.logInfo("过滤完成，保留 %d 个补货点位", len(alg.pointDict))

		// 重新构建行驶时长矩阵（只针对补货点位）
		if alg.travelMatrix != nil {
			if err := alg.rebuildTravelMatrix(); err != nil {
				alg.logInfo("警告：重新构建行驶时长矩阵失败: %v", err)
			}
		}

		// 重新构建特征向量（只针对补货点位）
		if err := alg.buildFeatures(); err != nil {
			return fmt.Errorf("重新构建特征向量失败: %v", err)
		}
	} else {
		// 两阶段模式：保留所有点位，但只为补货点位构建特征向量
		alg.logInfo("两阶段模式：保留所有 %d 个点位，其中 %d 个补货点位", len(alg.pointDict), len(alg.recallPoints))

		// 只为补货点位构建特征向量
		alg.logInfo("为补货点位构建特征向量...")
		alg.features = make(map[int][]float64)
		for pid, point := range alg.pointDict {
			if alg.recallPoints[pid] {
				var feature []float64
				feature = append(feature, point.Longitude, point.Latitude)

				if alg.travelMatrix != nil {
					avgTravelTime := alg.calculateAverageTravelTime(pid)
					feature = append(feature, avgTravelTime)
				}

				mainTimeWindow := alg.calculateMainTimeWindowMean(point.TimeWindows)
				feature = append(feature, mainTimeWindow)

				alg.features[pid] = feature
			}
		}
		alg.logInfo("补货点位特征向量构建完成")
	}

	// 1.7 约束分析
	if err := alg.analyzeConstraints(); err != nil {
		return fmt.Errorf("约束分析失败: %v", err)
	}

	alg.logInfo("数据预处理阶段完成")
	return nil
}

// buildFeatures 构建特征向量
func (alg *DynamicPartitionAlgorithm) buildFeatures() error {
	alg.logInfo("构建点位特征向量...")

	// 清空旧的特征数据
	alg.features = make(map[int][]float64)

	for pid, point := range alg.pointDict {
		var feature []float64

		// 基础特征：经度、纬度
		feature = append(feature, point.Longitude, point.Latitude)

		// 如果有行驶时长数据，添加平均行驶时长特征
		if alg.travelMatrix != nil {
			avgTravelTime := alg.calculateAverageTravelTime(pid)
			feature = append(feature, avgTravelTime)
		}

		// 时间窗口特征
		mainTimeWindow := alg.calculateMainTimeWindowMean(point.TimeWindows)
		feature = append(feature, mainTimeWindow)

		// 补货优先级特征
		if alg.recallPoints[pid] {
			feature = append(feature, 1.0)
		} else {
			feature = append(feature, 0.0)
		}

		alg.features[pid] = feature
	}

	// 特征标准化
	alg.normalizeFeatures()

	return nil
}

// analyzeConstraints 约束分析
func (alg *DynamicPartitionAlgorithm) analyzeConstraints() error {
	alg.logInfo("分析时间窗口约束...")

	conflicts := 0
	for pid1, point1 := range alg.pointDict {
		for pid2, point2 := range alg.pointDict {
			if pid1 >= pid2 {
				continue
			}

			if alg.hasTimeWindowConflict(point1.TimeWindows, point2.TimeWindows) {
				conflicts++
			}
		}
	}

	alg.logInfo("检测到 %d 对点位存在时间窗口冲突", conflicts)
	return nil
}

// ============= 第二阶段：基于地理位置的初始分区 =============

// InitialPartition 补货点位聚类分区
func (alg *DynamicPartitionAlgorithm) InitialPartition() (map[int][]int, error) {
	alg.logInfo("开始补货点位聚类...")

	// 2.1 K-means聚类（只针对补货点位）
	groups, err := alg.kmeansCluster()
	if err != nil {
		return nil, fmt.Errorf("K-means聚类失败: %v", err)
	}

	// 2.2 负载均衡调整
	groups = alg.balanceGroupLoad(groups)

	// 2.3 时间窗口可行性验证
	groups = alg.validateTimeWindowFeasibility(groups)

	// 2.4 保存第一阶段结果（如果启用两阶段分配）
	if alg.config.EnableSecondStage {
		if err := alg.saveFirstStageResult(groups); err != nil {
			alg.logInfo("警告：保存第一阶段结果失败: %v", err)
		} else {
			alg.logInfo("第一阶段结果已保存")
		}
	}

	alg.logInfo("补货点位聚类完成")
	return groups, nil
}

// kmeansCluster K-means聚类
func (alg *DynamicPartitionAlgorithm) kmeansCluster() (map[int][]int, error) {
	alg.logInfo("执行K-means聚类...")

	// 提取特征矩阵和点位ID列表
	var features [][]float64
	var pidList []int

	for pid, feature := range alg.features {
		features = append(features, feature)
		pidList = append(pidList, pid)
	}

	// 执行聚类
	labels := alg.kmeansWithConstraints(features, pidList)

	// 构建分组结果
	groups := make(map[int][]int)
	for i, label := range labels {
		pid := pidList[i]
		groups[label] = append(groups[label], pid)
	}

	return groups, nil
}

// kmeansWithConstraints 带约束的K-means聚类
func (alg *DynamicPartitionAlgorithm) kmeansWithConstraints(features [][]float64, pidList []int) []int {
	if len(features) == 0 {
		return []int{}
	}

	nClusters := alg.config.NClusters
	maxIter := alg.config.MaxIterations

	// 初始化聚类中心
	centers := alg.initializeCenters(features, nClusters)
	labels := make([]int, len(features))

	// 使用均衡初始化策略，确保每个组都有相近数量的点位
	alg.balancedInitialAssignment(features, pidList, labels, nClusters)

	// 迭代优化
	for iter := 0; iter < maxIter; iter++ {
		changed := false

		// 分配非补货点位
		for i, pid := range pidList {
			if alg.recallPoints[pid] {
				continue // 跳过已分配的补货点位
			}

			bestCluster := alg.findBestCluster(features[i], pid, centers)
			if labels[i] != bestCluster {
				labels[i] = bestCluster
				changed = true
			}
		}

		if !changed {
			break
		}

		// 更新聚类中心
		alg.updateCenters(features, labels, centers)
	}

	return labels
}

// ============= 第三阶段：启发式优化与局部搜索 =============

// OptimizePartition 优化分区
func (alg *DynamicPartitionAlgorithm) OptimizePartition(groups map[int][]int) (map[int][]int, error) {
	alg.logInfo("开始启发式优化阶段...")

	// 3.1 局部搜索优化
	groups = alg.localSearchOptimization(groups)

	// 3.2 模拟退火全局优化
	groups = alg.simulatedAnnealingOptimization(groups)

	// 3.3 约束满足性维护
	groups = alg.maintainConstraintSatisfaction(groups)

	alg.logInfo("启发式优化阶段完成")
	return groups, nil
}

// localSearchOptimization 局部搜索优化
func (alg *DynamicPartitionAlgorithm) localSearchOptimization(groups map[int][]int) map[int][]int {
	alg.logInfo("执行局部搜索优化...")

	improved := true
	iteration := 0

	for improved && iteration < alg.config.MaxOptimIter {
		improved = false
		iteration++

		// 在相邻分组间交换边界点位
		for g1 := 0; g1 < alg.config.NClusters; g1++ {
			for g2 := g1 + 1; g2 < alg.config.NClusters; g2++ {
				if alg.trySwapBoundaryPoints(groups, g1, g2) {
					improved = true
				}
			}
		}

		// 移动离群点
		if alg.moveOutliers(groups) {
			improved = true
		}
	}

	alg.logInfo("局部搜索完成，迭代 %d 次", iteration)
	return groups
}

// simulatedAnnealingOptimization 模拟退火优化
func (alg *DynamicPartitionAlgorithm) simulatedAnnealingOptimization(groups map[int][]int) map[int][]int {
	alg.logInfo("执行模拟退火全局优化...")

	currentGroups := alg.copyGroups(groups)
	bestGroups := alg.copyGroups(groups)

	currentCost := alg.calculateObjectiveFunction(currentGroups)
	bestCost := currentCost

	temp := alg.config.InitTemp

	for temp > alg.config.MinTemp {
		// 生成邻域解
		newGroups := alg.generateNeighborSolution(currentGroups)
		newCost := alg.calculateObjectiveFunction(newGroups)

		// 接受准则
		if alg.acceptSolution(currentCost, newCost, temp) {
			currentGroups = newGroups
			currentCost = newCost

			if newCost < bestCost {
				bestGroups = alg.copyGroups(newGroups)
				bestCost = newCost
			}
		}

		// 降温
		temp *= alg.config.CoolRate
	}

	alg.logInfo("模拟退火优化完成，最优成本: %.2f", bestCost)
	return bestGroups
}

// ============= 第四阶段：结果验证与输出 =============

// ValidateAndOutput 验证并输出结果
func (alg *DynamicPartitionAlgorithm) ValidateAndOutput(groups map[int][]int) (*Result, error) {
	alg.logInfo("开始结果验证与输出阶段...")

	// 4.1 性能指标计算
	performance := alg.calculatePerformanceMetrics(groups)

	// 4.2 约束满足性检查
	constraints := alg.checkConstraintSatisfaction(groups)

	// 4.3 构建结果
	result := &Result{
		Groups:      groups,
		Performance: performance,
		Constraints: constraints,
		Config:      alg.config,
		Timestamp:   time.Now(),
	}

	// 4.4 输出结果
	if err := alg.outputResults(result); err != nil {
		return nil, fmt.Errorf("输出结果失败: %v", err)
	}

	alg.logInfo("结果验证与输出阶段完成")
	return result, nil
}

// ============= 辅助函数实现 =============

// 距离计算相关
func (alg *DynamicPartitionAlgorithm) calculateDistance(pid1, pid2 int) float64 {
	cacheKey := fmt.Sprintf("%d-%d", pid1, pid2)
	if dist, exists := alg.distanceCache[cacheKey]; exists {
		return dist
	}

	var dist float64
	if alg.travelMatrix != nil {
		// 使用行驶时长矩阵
		travelTime := alg.travelMatrix.GetTravelTime(pid1, pid2)
		if travelTime >= 0 {
			geoDistance := alg.calculateGeographicDistance(pid1, pid2)
			dist = alg.config.TimeWeight*travelTime + alg.config.GeoWeight*geoDistance
		} else {
			dist = alg.calculateGeographicDistance(pid1, pid2)
		}
	} else {
		// 使用地理距离
		dist = alg.calculateGeographicDistance(pid1, pid2)
	}

	alg.distanceCache[cacheKey] = dist
	return dist
}

func (alg *DynamicPartitionAlgorithm) calculateGeographicDistance(pid1, pid2 int) float64 {
	point1, exists1 := alg.pointDict[pid1]
	point2, exists2 := alg.pointDict[pid2]

	if !exists1 || !exists2 {
		return -1.0 // 返回无效距离
	}

	return alg.haversineDistance(point1.Longitude, point1.Latitude, point2.Longitude, point2.Latitude)
}

func (alg *DynamicPartitionAlgorithm) haversineDistance(lon1, lat1, lon2, lat2 float64) float64 {
	const R = 6371.0 // 地球半径（公里）

	dLat := (lat2 - lat1) * math.Pi / 180
	dLon := (lon2 - lon1) * math.Pi / 180

	lat1Rad := lat1 * math.Pi / 180
	lat2Rad := lat2 * math.Pi / 180

	a := math.Sin(dLat/2)*math.Sin(dLat/2) +
		math.Cos(lat1Rad)*math.Cos(lat2Rad)*math.Sin(dLon/2)*math.Sin(dLon/2)
	c := 2 * math.Atan2(math.Sqrt(a), math.Sqrt(1-a))

	return R * c
}

// 时间窗口相关
func (alg *DynamicPartitionAlgorithm) calculateMainTimeWindowMean(timeWindows []TimeWindow) float64 {
	if len(timeWindows) == 0 {
		return 0
	}

	total := 0.0
	count := 0

	for _, tw := range timeWindows {
		startMinutes := alg.timeStringToMinutes(tw.Start)
		if startMinutes >= 0 {
			total += startMinutes
			count++
		}
	}

	if count == 0 {
		return 0
	}

	return total / float64(count)
}

func (alg *DynamicPartitionAlgorithm) timeStringToMinutes(timeStr string) float64 {
	parts := strings.Split(strings.TrimSpace(timeStr), ":")
	if len(parts) != 2 {
		return -1
	}

	hour, err1 := strconv.Atoi(parts[0])
	minute, err2 := strconv.Atoi(parts[1])

	if err1 != nil || err2 != nil || hour < 0 || hour > 23 || minute < 0 || minute > 59 {
		return -1
	}

	return float64(hour*60 + minute)
}

func (alg *DynamicPartitionAlgorithm) hasTimeWindowConflict(tw1, tw2 []TimeWindow) bool {
	// 简化的时间窗口冲突检测
	// 实际应用中可能需要更复杂的逻辑
	return false
}

// 特征处理相关
func (alg *DynamicPartitionAlgorithm) normalizeFeatures() {
	if len(alg.features) == 0 {
		return
	}

	// 获取特征维度
	featureDim := len(alg.features[alg.getFirstPointID()])

	// 计算每个维度的均值和标准差
	means := make([]float64, featureDim)
	stds := make([]float64, featureDim)

	// 计算均值
	for _, feature := range alg.features {
		for i, val := range feature {
			means[i] += val
		}
	}

	n := float64(len(alg.features))
	for i := range means {
		means[i] /= n
	}

	// 计算标准差
	for _, feature := range alg.features {
		for i, val := range feature {
			diff := val - means[i]
			stds[i] += diff * diff
		}
	}

	for i := range stds {
		stds[i] = math.Sqrt(stds[i] / n)
		if stds[i] == 0 {
			stds[i] = 1 // 避免除零
		}
	}

	// 标准化
	for pid, feature := range alg.features {
		normalized := make([]float64, len(feature))
		for i, val := range feature {
			normalized[i] = (val - means[i]) / stds[i]
		}
		alg.features[pid] = normalized
	}
}

// 数据加载相关
func (alg *DynamicPartitionAlgorithm) loadPointsFromCSV(filePath string) error {
	file, err := os.Open(filePath)
	if err != nil {
		return err
	}
	defer file.Close()

	reader := csv.NewReader(file)
	reader.LazyQuotes = true
	reader.FieldsPerRecord = -1

	records, err := reader.ReadAll()
	if err != nil {
		return err
	}

	validCount := 0
	for i := 1; i < len(records); i++ {
		record := records[i]
		if len(record) < 11 {
			continue
		}

		// 解析点位ID
		id, err := strconv.Atoi(strings.TrimSpace(record[0]))
		if err != nil || id == 998 || id == 999 {
			continue
		}

		// 解析经纬度
		latitude, err1 := strconv.ParseFloat(strings.TrimSpace(record[4]), 64)
		longitude, err2 := strconv.ParseFloat(strings.TrimSpace(record[5]), 64)
		if err1 != nil || err2 != nil {
			continue
		}

		// 解析时间窗口
		startTime := strings.TrimSpace(record[9])
		endTime := strings.TrimSpace(record[10])
		if !alg.isValidTimeFormat(startTime) || !alg.isValidTimeFormat(endTime) {
			continue
		}

		// 创建或更新点位
		if point, exists := alg.pointDict[id]; exists {
			point.TimeWindows = append(point.TimeWindows, TimeWindow{Start: startTime, End: endTime})
		} else {
			alg.pointDict[id] = &Point{
				ID:          id,
				Longitude:   longitude,
				Latitude:    latitude,
				TimeWindows: []TimeWindow{{Start: startTime, End: endTime}},
			}
		}
		validCount++
	}

	return nil
}

func (alg *DynamicPartitionAlgorithm) loadTravelTimeMatrix(filePath string) error {
	file, err := os.Open(filePath)
	if err != nil {
		return err
	}
	defer file.Close()

	reader := csv.NewReader(file)
	records, err := reader.ReadAll()
	if err != nil {
		return err
	}

	if len(records) < 2 {
		return fmt.Errorf("行驶时长文件数据不足")
	}

	// 获取所有点位ID
	var allPointIDs []int
	for pid := range alg.pointDict {
		allPointIDs = append(allPointIDs, pid)
	}
	sort.Ints(allPointIDs)

	// 创建点位ID到索引的映射
	pointIDToIndex := make(map[int]int)
	for i, pid := range allPointIDs {
		pointIDToIndex[pid] = i
	}

	nPoints := len(allPointIDs)
	matrix := &TravelTimeMatrix{
		Times:          make([][]float64, nPoints),
		Size:           nPoints,
		PointIDToIndex: pointIDToIndex,
	}

	// 初始化矩阵，所有值设为-1（表示无数据）
	for i := range matrix.Times {
		matrix.Times[i] = make([]float64, nPoints)
		for j := range matrix.Times[i] {
			matrix.Times[i][j] = -1
		}
	}

	// 设置对角线为0（同一点位）
	for i := 0; i < nPoints; i++ {
		matrix.Times[i][i] = 0
	}

	// 解析数据（跳过表头）
	validCount := 0
	for i := 1; i < len(records); i++ {
		record := records[i]
		if len(record) < 3 {
			continue
		}

		// 解析起始点位ID
		fromID, err := strconv.Atoi(strings.TrimSpace(record[0]))
		if err != nil {
			continue
		}

		// 解析目标点位ID
		toID, err := strconv.Atoi(strings.TrimSpace(record[1]))
		if err != nil {
			continue
		}

		// 解析行驶时长
		durationStr := strings.TrimSpace(record[2])
		// 处理带逗号的数字格式
		durationStr = strings.ReplaceAll(durationStr, ",", "")
		duration, err := strconv.ParseFloat(durationStr, 64)
		if err != nil {
			continue
		}

		// 检查点位ID是否在有效范围内
		fromIndex, fromExists := pointIDToIndex[fromID]
		toIndex, toExists := pointIDToIndex[toID]
		if fromExists && toExists {
			matrix.Times[fromIndex][toIndex] = duration
			validCount++
		}
	}

	alg.travelMatrix = matrix
	alg.logInfo("成功加载行驶时长矩阵: %d x %d，有效数据: %d条", nPoints, nPoints, validCount)
	return nil
}

func (alg *DynamicPartitionAlgorithm) loadRecallPoints(filePath string) error {
	file, err := os.Open(filePath)
	if err != nil {
		return err
	}
	defer file.Close()

	reader := csv.NewReader(file)
	records, err := reader.ReadAll()
	if err != nil {
		return err
	}

	for i := 1; i < len(records); i++ {
		record := records[i]
		if len(record) < 1 {
			continue
		}

		id, err := strconv.Atoi(strings.TrimSpace(record[0]))
		if err != nil {
			continue
		}

		alg.recallPoints[id] = true
	}

	return nil
}

// 工具函数
func (alg *DynamicPartitionAlgorithm) isValidTimeFormat(timeStr string) bool {
	parts := strings.Split(strings.TrimSpace(timeStr), ":")
	if len(parts) != 2 {
		return false
	}

	hour, err1 := strconv.Atoi(parts[0])
	minute, err2 := strconv.Atoi(parts[1])

	return err1 == nil && err2 == nil && hour >= 0 && hour <= 23 && minute >= 0 && minute <= 59
}

func (alg *DynamicPartitionAlgorithm) getFirstPointID() int {
	for pid := range alg.features {
		return pid
	}
	return 0
}

func (alg *DynamicPartitionAlgorithm) logInfo(format string, args ...interface{}) {
	if alg.config.Verbose {
		alg.logger.Printf(format, args...)
	}
}

// initializeCenters 聚类中心初始化（保留此函数，因为algorithm_impl.go中没有）
func (alg *DynamicPartitionAlgorithm) initializeCenters(features [][]float64, nClusters int) [][]float64 {
	// 保持随机初始化，允许每次运行产生不同结果
	centers := make([][]float64, nClusters)
	for i := 0; i < nClusters; i++ {
		centers[i] = make([]float64, len(features[0]))
		copy(centers[i], features[rand.Intn(len(features))])
	}
	return centers
}

// balancedInitialAssignment 均衡初始分配策略
// 确保每个聚类组都有相近数量的点位，优先分配补货点位
func (alg *DynamicPartitionAlgorithm) balancedInitialAssignment(features [][]float64, pidList []int, labels []int, nClusters int) {
	if len(features) == 0 || nClusters <= 0 {
		return
	}

	// 分离补货点位和非补货点位
	var recallIndices []int
	var nonRecallIndices []int

	for i, pid := range pidList {
		if alg.recallPoints[pid] {
			recallIndices = append(recallIndices, i)
		} else {
			nonRecallIndices = append(nonRecallIndices, i)
		}
	}

	alg.logInfo("开始均衡初始分配：补货点位 %d 个，非补货点位 %d 个", len(recallIndices), len(nonRecallIndices))

	// 第一步：均衡分配补货点位
	// 计算每个组应该分配的补货点位数量
	recallPerGroup := len(recallIndices) / nClusters
	extraRecall := len(recallIndices) % nClusters

	groupAssignCount := make([]int, nClusters)
	currentGroup := 0

	// 优先分配补货点位，确保均衡分布
	for _, idx := range recallIndices {
		// 计算当前组的目标数量
		targetCount := recallPerGroup
		if currentGroup < extraRecall {
			targetCount++
		}

		// 如果当前组已满，移动到下一组
		if groupAssignCount[currentGroup] >= targetCount {
			currentGroup = (currentGroup + 1) % nClusters
			// 防止无限循环，如果所有组都满了，分配到最后一个组
			attempts := 0
			for groupAssignCount[currentGroup] >= targetCount && attempts < nClusters {
				currentGroup = (currentGroup + 1) % nClusters
				attempts++
			}
		}

		labels[idx] = currentGroup
		groupAssignCount[currentGroup]++

		// 移动到下一组，实现轮询分配
		currentGroup = (currentGroup + 1) % nClusters
	}

	// 第二步：分配非补货点位
	// 计算每个组应该分配的总点位数量
	totalPerGroup := len(pidList) / nClusters
	extraTotal := len(pidList) % nClusters

	// 重置计数器，统计当前每组的总点位数
	for i := range groupAssignCount {
		groupAssignCount[i] = 0
	}
	for _, label := range labels {
		if label >= 0 && label < nClusters {
			groupAssignCount[label]++
		}
	}

	// 分配非补货点位
	currentGroup = 0
	for _, idx := range nonRecallIndices {
		// 计算当前组的目标总数量
		targetCount := totalPerGroup
		if currentGroup < extraTotal {
			targetCount++
		}

		// 找到一个还有空间的组
		attempts := 0
		for groupAssignCount[currentGroup] >= targetCount && attempts < nClusters {
			currentGroup = (currentGroup + 1) % nClusters
			attempts++
		}

		labels[idx] = currentGroup
		groupAssignCount[currentGroup]++

		// 移动到下一组
		currentGroup = (currentGroup + 1) % nClusters
	}

	// 打印分配结果统计
	for i := 0; i < nClusters; i++ {
		recallCount := 0
		totalCount := 0
		for j, label := range labels {
			if label == i {
				totalCount++
				if alg.recallPoints[pidList[j]] {
					recallCount++
				}
			}
		}
		alg.logInfo("分组 %d: 总计 %d 个点位，其中补货点位 %d 个", i+1, totalCount, recallCount)
	}
}

// copyGroups 分组复制（保留此函数，因为algorithm_impl.go中没有）
func (alg *DynamicPartitionAlgorithm) copyGroups(groups map[int][]int) map[int][]int {
	newGroups := make(map[int][]int)
	for k, v := range groups {
		newGroups[k] = make([]int, len(v))
		copy(newGroups[k], v)
	}
	return newGroups
}

func (alg *DynamicPartitionAlgorithm) acceptSolution(currentCost, newCost, temp float64) bool {
	if newCost < currentCost {
		return true
	}

	prob := math.Exp(-(newCost - currentCost) / temp)
	return rand.Float64() < prob
}

// ============= TravelTimeMatrix 方法实现 =============

func (tm *TravelTimeMatrix) GetTravelTime(fromID, toID int) float64 {
	fromIndex, fromExists := tm.PointIDToIndex[fromID]
	toIndex, toExists := tm.PointIDToIndex[toID]

	if !fromExists || !toExists || fromIndex < 0 || fromIndex >= tm.Size || toIndex < 0 || toIndex >= tm.Size {
		return -1
	}
	return tm.Times[fromIndex][toIndex]
}

// rebuildTravelMatrix 重新构建行驶时长矩阵（只针对补货点位）
func (alg *DynamicPartitionAlgorithm) rebuildTravelMatrix() error {
	if alg.travelMatrix == nil {
		return nil
	}

	// 获取当前的补货点位ID列表
	var recallPointIDs []int
	for pid := range alg.pointDict {
		recallPointIDs = append(recallPointIDs, pid)
	}
	sort.Ints(recallPointIDs)

	// 创建新的点位ID到索引的映射
	newPointIDToIndex := make(map[int]int)
	for i, pid := range recallPointIDs {
		newPointIDToIndex[pid] = i
	}

	nPoints := len(recallPointIDs)
	newMatrix := &TravelTimeMatrix{
		Times:          make([][]float64, nPoints),
		Size:           nPoints,
		PointIDToIndex: newPointIDToIndex,
	}

	// 初始化新矩阵
	for i := range newMatrix.Times {
		newMatrix.Times[i] = make([]float64, nPoints)
		for j := range newMatrix.Times[i] {
			newMatrix.Times[i][j] = -1
		}
	}

	// 设置对角线为0
	for i := 0; i < nPoints; i++ {
		newMatrix.Times[i][i] = 0
	}

	// 从原矩阵复制数据
	for i, fromPid := range recallPointIDs {
		for j, toPid := range recallPointIDs {
			if i != j {
				oldTime := alg.travelMatrix.GetTravelTime(fromPid, toPid)
				if oldTime >= 0 {
					newMatrix.Times[i][j] = oldTime
				}
			}
		}
	}

	alg.travelMatrix = newMatrix
	alg.logInfo("重新构建行驶时长矩阵: %d x %d", nPoints, nPoints)
	return nil
}

// ============= 主函数示例 =============

func runDynamicPartition() error {
	// 创建配置
	config := DefaultConfig()

	// 创建算法实例
	alg := NewDynamicPartitionAlgorithm(config)

	// 数据路径
	pointsPath := filepath.Join("..", "data", "点位信息.csv")
	travelTimePath := filepath.Join("..", "data", "duration_path.csv")
	recallPointsPath := filepath.Join("..", "data", "recall_point.csv")

	// 第一阶段：数据预处理
	if err := alg.LoadData(pointsPath, travelTimePath, recallPointsPath); err != nil {
		return fmt.Errorf("数据加载失败: %v", err)
	}

	// 第二阶段：初始分区
	groups, err := alg.InitialPartition()
	if err != nil {
		return fmt.Errorf("初始分区失败: %v", err)
	}

	// 第三阶段：启发式优化
	groups, err = alg.OptimizePartition(groups)
	if err != nil {
		return fmt.Errorf("分区优化失败: %v", err)
	}

	// 第四阶段：结果验证与输出
	result, err := alg.ValidateAndOutput(groups)
	if err != nil {
		return fmt.Errorf("结果输出失败: %v", err)
	}

	// 打印结果摘要
	fmt.Printf("=== 动态分区算法执行完成 ===\n")
	fmt.Printf("分组数量: %d\n", len(result.Groups))
	fmt.Printf("执行时间: %.2f 秒\n", result.Performance.ExecutionTime)
	fmt.Printf("负载均衡指数: %.2f\n", result.Performance.LoadBalanceIndex)
	fmt.Printf("约束满足状态: %v\n", result.Constraints.ConstraintsSatisfied)

	return nil
}
