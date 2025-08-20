# 车辆点位分配算法 - Golang 实现

## 概述

本项目实现了基于文档《车辆和点位分配.md》的三阶段约束启发式算法，用于解决无人售货机点位的车辆分配问题。

## 核心特性

### 🚗 多约束优化
- **兼容性约束**: 车辆与点位的服务能力匹配
- **相对地理约束**: 按经度划分区域，保证地理连续性
- **运力平衡约束**: 缺货点位比例均衡分配

### 📊 三阶段算法架构
1. **阶段0**: 约束预处理与区域划分
2. **阶段1**: 多约束下的点位聚类
3. **阶段2**: 缺货点位比例优化调整

### 🎯 优化目标
- **运力平衡优先** (权重 0.75): 防止车辆闲忙不均
- **缺货点位集中性** (权重 0.20): 优化配送路径
- **不缺货点位集中性** (权重 0.05): 次要优化目标

## 文件结构

```
golang/
├── vehicle_allocation.go          # ✅ 纯粹的算法核心类
├── full_real_data_case.go        # ✅ 主函数 + 完整真实数据测试
├── clustering_utils.go           # ✅ 聚类工具类
├── real_data_generator.go        # ✅ 真实数据生成器（重要：用于生成测试数据）
├── run_vehicle_allocation.sh     # ✅ 一键运行脚本（推荐使用）
└── README_VehicleAllocation.md   # 本文档

output/                              # 📁 输出结果目录
├── real_data_test_case.json        # 📊 完整测试数据          
├── allocation_results.csv           # 📋 完整分配结果
└── shortage_points.csv              # ⚠️ 缺货点位分配结果
```

## 核心类说明

### VehicleAllocationAlgorithm
主要的车辆分配算法类，包含：

**核心数据结构:**
```go
type VehiclePoint struct {
    ID            string    // 点位ID
    Longitude     float64   // 经度
    Latitude      float64   // 纬度
    IsShortage    bool      // 是否缺货
    CompatVehicles []string // 兼容车辆列表
}

type Vehicle struct {
    ID     string  // 车辆ID
    Ratio  float64 // 预设缺货点位比例
    Region int     // 所属区域编号
}
```

**主要方法:**
- `Initialize()`: 初始化算法参数和数据
- `Execute()`: 执行三阶段分配算法
- `stage0_RegionPartition()`: 区域划分和约束预处理
- `stage1_PointClustering()`: 多约束点位聚类
- `stage2_ProportionOptimization()`: 比例优化调整

### ClusteringUtils
聚类工具类，提供多种聚类算法：
- **层次聚类** (AgglomerativeClustering): 推荐用于中等规模点位
- **K-means聚类**: 适用于大规模点位
- **加权聚类**: 对缺货点位给予更高聚集权重

## 使用方式

### 🚀 快速运行（推荐）

```bash
# 一键运行：重新生成数据 + 执行算法（推荐）
cd golang
./run_vehicle_allocation.sh
```

### 📋 手动运行

```bash
# 手动运行完整的新加坡真实数据测试
cd golang
go run vehicle_allocation.go full_real_data_case.go clustering_utils.go
```

### 📊 真实数据特性

- **数据来源**：新加坡111个无人售货机点位
- **缺货识别**：基于未来12小时内的缺货预测
- **车辆配置**：3辆车 [2, 14, 15] 从东到西排序
- **兼容性约束**：受限访问点位只能由特定车辆服务
- **地理分布**：完整覆盖新加坡全岛（经度103.62~104.02）

### 🔄 重新生成测试数据（可选）

如果需要基于最新的原始数据重新生成测试用例：

```bash
# 运行数据生成器（需要原始数据文件）
go run real_data_generator.go

# 生成的文件：
# - real_data_test_case.json  (完整的JSON数据)
# - real_data_test.go         (Go代码示例)
```

**注意**：所有生成的文件会自动保存到 `../output/` 目录，保持 `golang` 目录的整洁。

**数据生成器功能**：
- 解析 `../data/point.csv` - 111个点位信息
- 解析 `../data/point_stock_out.txt` - 缺货预测数据
- 解析 `../data/duration_point.csv` - 点位间行驶时间
- 生成符合算法要求的测试数据格式

### 💻 算法调用示例

```go
// 1. 创建算法实例
algorithm := NewVehicleAllocationAlgorithm()

// 2. 从JSON加载真实数据
points, vehicles, timeMatrix, err := loadRealDataFromJSON()
if err != nil {
    log.Fatal(err)
}

// 3. 调整算法参数（可选）
algorithm.WeightAlpha = 0.8   // 运力平衡权重
algorithm.WeightBeta = 0.15   // 缺货点位集中性权重
algorithm.WeightGamma = 0.05  // 不缺货点位集中性权重

// 4. 初始化算法
err = algorithm.Initialize(points, vehicles, timeMatrix)
if err != nil {
    log.Fatal(err)
}

// 5. 执行三阶段算法
results, err := algorithm.Execute()
if err != nil {
    log.Fatal(err)
}

// 6. 查看结果
algorithm.PrintResults(results)
```

## 算法参数配置

### 权重参数设置

#### 核心权重参数
```go
algorithm.WeightAlpha = 0.75  // 运力平衡权重 (推荐 0.6-0.8)
algorithm.WeightBeta = 0.20   // 缺货点位集中性 (推荐 0.15-0.3)  
algorithm.WeightGamma = 0.05  // 不缺货点位集中性 (推荐 0.05-0.1)
```

**参数说明**：
- **WeightAlpha**: 控制各车辆缺货点位比例均衡程度，权重越高运力分配越均匀
- **WeightBeta**: 控制缺货点位地理聚集程度，权重越高配送路径越短
- **WeightGamma**: 控制不缺货点位聚集程度，次要优化目标

#### 迭代控制参数
```go
algorithm.MaxIterations = 30      // 最大迭代次数 (推荐 15-30)
algorithm.ConvergenceThres = 0.005 // 收敛阈值 (推荐 0.005-0.02)
```

**参数说明**：
- **MaxIterations**: 限制最大迭代次数，防止无限循环
- **ConvergenceThres**: 判断算法收敛的精度阈值，值越小解质量越高

## 真实数据测试结果

### 📊 测试环境
- **数据来源**: 新加坡111个无人售货机真实点位数据
- **缺货点位**: 12个（10.8%，基于未来12小时预测）
- **车辆配置**: 3辆车从东到西分配
- **时间矩阵**: 基于真实行驶时间数据

### 🎯 算法性能表现

```
=== 分配结果统计 ===
车辆 2 (东区): 37个点位, 3个缺货点位 (25.0%)
车辆 14(中区): 37个点位, 3个缺货点位 (25.0%) 
车辆 15(西区): 37个点位, 6个缺货点位 (50.0%)

运力平衡得分: 0.0434 (越小越好)
地理集中性: 平均17-23分钟点位间距离
区域覆盖: 完整覆盖新加坡全岛
```

### 🔧 推荐算法配置

```go
// 针对真实数据优化的参数配置
algorithm.WeightAlpha = 0.8    // 运力平衡权重（提高）
algorithm.WeightBeta = 0.15    // 缺货集中性权重
algorithm.WeightGamma = 0.05   // 不缺货集中性权重
algorithm.MaxIterations = 30   // 增加迭代次数

// 聚类参数建议
clusteringUtils := NewClusteringUtils(timeMatrix, points)
clusters := clusteringUtils.AgglomerativeClustering(
    pointIDs, 
    3,     // 车辆数量
    15.0,  // 15分钟行驶时间阈值
)
```

### 📋 输出文件管理

算法执行完成后会自动生成以下文件，并保存到 `../output/` 目录：

#### allocation_results.csv - 完整分配结果

```csv
point_id,longitude,latitude,car_id
111,103.620000,1.240000,2
112,103.620000,1.270000,2
190,103.630000,1.290000,2
...
```

**字段说明**：
- **point_id**: 点位ID
- **longitude**: 经度（6位小数精度）
- **latitude**: 纬度（6位小数精度）  
- **car_id**: 分配的车辆ID

## 约束验证

算法会自动验证以下约束：

### ✅ 强制约束
- **全点位覆盖**: 每个点位都被分配且仅被分配一次
- **兼容性约束**: 车辆只能服务兼容的点位
- **相对地理约束**: 车辆在指定区域内服务

### ⚠️ 优化目标
- **运力平衡**: 各车辆缺货点位比例接近预设值
- **地理集中性**: 最小化车辆内点位间的平均行驶时间

## 性能指标

### 运力平衡评估
- **最大偏差 < 10%**: ✅ 良好
- **最大偏差 < 20%**: ⚠️ 一般  
- **最大偏差 >= 20%**: ❌ 较差

### 真实数据验证结果
- **全点位覆盖**: ✅ 所有111个点位都被分配
- **兼容性约束**: ✅ 满足车辆-点位兼容性要求
- **运力平衡**: ⚠️ 存在一定偏差，车辆15承担更多缺货点位
- **地理集中性**: ✅ 良好的区域划分和集中性

## 扩展功能

### 聚类算法选择
```go
// 层次聚类 - 推荐用于新加坡场景
clusters := clusteringUtils.AgglomerativeClustering(pointIDs, maxClusters, threshold)

// K-means聚类 - 适用于大规模场景
clusters := clusteringUtils.KMeansClustering(pointIDs, k, maxIterations)

// 加权聚类 - 缺货点位优先聚集
clusters := clusteringUtils.WeightedClustering(pointIDs, k, shortageWeight)
```

### 聚类质量评估
```go
metrics := clusteringUtils.EvaluateClusterQuality(clusters)
fmt.Printf("平均簇内距离: %.2f\n", metrics["avg_intra_distance"])
fmt.Printf("缺货点位集中度: %.2f\n", metrics["shortage_concentration"])
```

## 算法优势

### ✅ 优点
- **数学建模严谨**: 统一的加权目标函数
- **多约束支持**: 兼容性、地理、比例约束并行处理
- **业务适配性强**: 运力平衡优先，符合实际运营需求
- **参数自适应**: 动态调整优化参数
- **收敛性保证**: 明确的终止条件

### ⚠️ 限制
- **多约束冲突**: 强约束下可行解空间可能较小
- **数据依赖性**: 需要精确的时间矩阵和兼容性信息
- **参数敏感性**: 权重参数需要根据场景调优

## 故障排除

### 常见问题
1. **约束不可行**: 检查兼容性矩阵，确保每个点位有兼容车辆
2. **比例严重失衡**: 调整权重参数，增加 `WeightAlpha`
3. **地理分散**: 增加 `WeightBeta`，使用更严格的距离阈值

### 调试建议
- 使用 `PrintResults()` 查看详细分配结果
- 调用 `validateResults()` 验证约束满足情况
- 启用详细日志输出跟踪算法执行过程

## 贡献指南

欢迎提交 Issue 和 Pull Request 来改进算法实现。

### 开发环境
- Go 1.19+
- 推荐使用 VSCode 或 GoLand

### 测试
```bash
go test ./...
```

## 许可证

本项目遵循 MIT 许可证。
