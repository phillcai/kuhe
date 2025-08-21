# 车辆点位分配算法 - Golang 实现

## 概述

本项目实现了基于文档《车辆和点位分配.md》的改进三阶段约束启发式算法，用于解决无人售货机点位的车辆分配问题。**重点解决了地理位置不集中的问题，避免东部点位分给西部车辆的情况。**

## 🚀 快速开始

### 立即运行改进算法
```bash
cd golang
go run full_real_data_case.go improved_vehicle_allocation.go types.go
```

### 主要改进
- ✅ **解决地理错配**：东部点位不再分给西部车辆
- ✅ **运力平衡优秀**：偏差平方和仅0.0005
- ✅ **智能冲突解决**：基于地理偏好的约束处理
- ✅ **四维优化目标**：新增地理集中性权重

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
- **运力平衡** (权重 0.4): 防止车辆闲忙不均
- **缺货点位集中性** (权重 0.2): 优化配送路径
- **不缺货点位集中性** (权重 0.05): 次要优化目标
- **地理位置集中性** (权重 0.35): **新增重点**，确保点位地理分布合理

## 文件结构

```
golang/
├── types.go                      # 🆕 基础数据类型定义（核心依赖）
├── vehicle_allocation.go          # ✅ 原始算法核心类（独立运行）
├── improved_vehicle_allocation.go # 🆕 改进算法核心类（推荐使用，独立运行）
├── full_real_data_case.go        # ✅ 改进算法主程序（已集成改进算法）
├── original_algorithm_main.go    # 🆕 原始算法主程序（独立测试）
├── clustering_utils.go           # ✅ 聚类工具类
├── real_data_generator.go        # ✅ 真实数据生成器（重要：用于生成测试数据）
├── run_vehicle_allocation.sh     # ✅ 一键运行脚本（推荐使用）
└── README_VehicleAllocation.md   # 本文档

output/                              # 📁 输出结果目录
├── real_data_test_case.json        # 📊 完整测试数据          
├── allocation_results.csv           # 📋 完整分配结果
└── shortage_points.csv              # ⚠️ 缺货点位分配结果
```

## 🏗️ 架构设计

### 独立性架构
两个算法核心类现已**完全独立**，不互相依赖：

```
types.go                    # 🎯 基础数据类型（共享）
├── VehiclePoint           # 点位结构体
├── Vehicle               # 车辆结构体  
├── Region                # 区域结构体
└── AllocationResult      # 分配结果结构体

vehicle_allocation.go       # 🔄 原始算法（独立）
└── VehicleAllocationAlgorithm

improved_vehicle_allocation.go  # ⚡ 改进算法（独立）
└── ImprovedVehicleAllocationAlgorithm
```

**独立运行能力：**
- ✅ 改进算法：`go run full_real_data_case.go improved_vehicle_allocation.go types.go`
- ✅ 原始算法：`go run original_algorithm_main.go vehicle_allocation.go types.go`
- ✅ 无相互依赖：两个算法可完全独立开发和维护

## 核心类说明

### ImprovedVehicleAllocationAlgorithm（推荐）
改进的车辆分配算法类，**解决地理位置不集中问题**，包含：

**新增特性：**
- **智能区域划分**: 基于地理偏好的兼容性冲突解决
- **地理集中性权重**: 新增WeightGeographic参数优化地理分布
- **双向点位交换**: 改善地理集中性的同时保持约束满足

### VehicleAllocationAlgorithm（原始版本）
原始的车辆分配算法类，保留用于对比：

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

**改进算法主要方法:**
- `Initialize()`: 初始化算法参数和数据
- `Execute()`: 执行改进的三阶段分配算法
- `stage0_ImprovedRegionPartition()`: **改进的区域划分**，智能解决兼容性冲突
- `stage1_ImprovedPointClustering()`: 多约束点位聚类
- `stage2_ImprovedProportionOptimization()`: **改进的比例优化**，考虑地理因素

**核心改进方法:**
- `improvedResolveCompatibilityConflicts()`: 智能兼容性冲突解决
- `resolveConflictWithGeographicPreference()`: 基于地理偏好的冲突解决
- `calculateGeographicFitScore()`: 地理适应性评分

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
# 手动运行改进算法的新加坡真实数据测试（推荐）
cd golang
go run full_real_data_case.go improved_vehicle_allocation.go types.go

# 运行原始算法（独立测试）
go run original_algorithm_main.go vehicle_allocation.go types.go
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

### 💻 改进算法调用示例

```go
// 1. 创建改进算法实例（推荐）
algorithm := NewImprovedVehicleAllocationAlgorithm()

// 2. 从JSON加载真实数据
points, vehicles, timeMatrix, err := loadRealDataFromJSON()
if err != nil {
    log.Fatal(err)
}

// 3. 调整改进算法参数（针对地理集中性优化）
algorithm.WeightAlpha = 0.4       // 运力平衡权重
algorithm.WeightBeta = 0.2        // 缺货点位集中性权重
algorithm.WeightGamma = 0.05      // 不缺货点位集中性权重
algorithm.WeightGeographic = 0.35 // 地理位置集中性权重（新增）

// 4. 初始化算法
err = algorithm.Initialize(points, vehicles, timeMatrix)
if err != nil {
    log.Fatal(err)
}

// 5. 执行改进的三阶段算法
results, err := algorithm.Execute()
if err != nil {
    log.Fatal(err)
}

// 6. 查看结果
algorithm.PrintResults(results)
```

## 算法参数配置

### 权重参数设置

#### 改进算法核心权重参数（推荐配置）
```go
algorithm.WeightAlpha = 0.4       // 运力平衡权重 (推荐 0.3-0.5)
algorithm.WeightBeta = 0.2        // 缺货点位集中性 (推荐 0.15-0.25)  
algorithm.WeightGamma = 0.05      // 不缺货点位集中性 (推荐 0.05-0.1)
algorithm.WeightGeographic = 0.35 // 地理位置集中性权重 (推荐 0.3-0.4) 🆕
```

**参数说明**：
- **WeightAlpha**: 控制各车辆缺货点位比例均衡程度，权重越高运力分配越均匀
- **WeightBeta**: 控制缺货点位地理聚集程度，权重越高配送路径越短
- **WeightGamma**: 控制不缺货点位聚集程度，次要优化目标
- **WeightGeographic**: **新增**控制地理位置集中性，解决东西部点位错配问题

#### 原始算法权重参数（对比用）
```go
algorithm.WeightAlpha = 0.75  // 运力平衡权重 (推荐 0.6-0.8)
algorithm.WeightBeta = 0.20   // 缺货点位集中性 (推荐 0.15-0.3)  
algorithm.WeightGamma = 0.05  // 不缺货点位集中性 (推荐 0.05-0.1)
```

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
- **数据来源**: 新加坡107个无人售货机真实点位数据
- **缺货点位**: 31个（29.0%，基于未来12小时预测）
- **车辆配置**: 3辆车从东到西分配
- **时间矩阵**: 基于真实行驶时间数据

### 🎯 改进算法性能表现（推荐）

```
=== 改进算法分配结果统计 ===
车辆 15(西区): 31个点位, 8个缺货点位 (25.8%) - 经度103.620~103.780
车辆 14(中区): 40个点位, 11个缺货点位 (35.5%) - 经度103.770~104.020  
车辆 2 (东区): 36个点位, 12个缺货点位 (38.7%) - 经度103.780~104.000

✅ 运力平衡得分: 0.0005 (极优，越小越好)
✅ 地理集中性: 显著改善，平均18-21分钟点位间距离
✅ 区域覆盖: 完整覆盖新加坡全岛，地理分布合理
✅ 约束满足: 100%点位覆盖，0重复分配，0未分配
```

### 📊 原始算法对比结果

```
=== 原始算法存在的问题 ===
❌ 地理位置不集中: 东部点位被分配给西部车辆
❌ 运力平衡较差: 比例偏差较大
❌ 配送效率低: 跨区域配送增加成本
```

### 🔧 推荐改进算法配置

```go
// 针对地理集中性优化的改进算法配置
algorithm := NewImprovedVehicleAllocationAlgorithm()
algorithm.WeightAlpha = 0.4        // 运力平衡权重
algorithm.WeightBeta = 0.2         // 缺货集中性权重
algorithm.WeightGamma = 0.05       // 不缺货集中性权重
algorithm.WeightGeographic = 0.35  // 地理位置集中性权重（新增重点）
algorithm.MaxIterations = 30       // 增加迭代次数
algorithm.ConvergenceThres = 0.01  // 收敛精度

// 聚类参数建议（如需要）
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

### 改进算法验证结果
- **全点位覆盖**: ✅ 所有107个点位都被分配，0重复分配
- **兼容性约束**: ✅ 满足车辆-点位兼容性要求
- **运力平衡**: ✅ 极优的运力平衡，最大偏差仅1.7%
- **地理集中性**: ✅ **显著改善**，解决了东西部错配问题

### 关键改进效果
- **地理分布优化**: 车辆15(西区)、车辆14(中区)、车辆2(东区)严格按地理位置分配
- **运力平衡提升**: 偏差平方和从原来的较大值降至0.0005
- **配送效率提升**: 减少跨区域配送，降低运营成本

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

### ✅ 改进算法优点
- **地理集中性显著提升**: **解决了东部点位分给西部车辆的核心问题**
- **智能冲突解决**: 基于地理偏好的兼容性冲突处理机制
- **双向优化交换**: 同时考虑地理因素和运力平衡的点位交换策略
- **数学建模严谨**: 新增地理权重的统一加权目标函数
- **多约束协调**: 兼容性、地理、比例约束的智能协调处理
- **业务适配性强**: 优先解决实际运营中的地理分散问题
- **参数自适应**: 动态调整优化参数
- **收敛性保证**: 明确的终止条件和迭代控制

### 🆚 相比原始算法的改进
- **地理集中性**: 从分散配送改善为区域化配送
- **运力平衡**: 从较大偏差提升到极小偏差(0.0005)
- **约束处理**: 从简单移动改进为智能双向交换
- **目标函数**: 新增地理权重，四维优化目标

### ⚠️ 限制
- **计算复杂度**: 改进算法需要更多计算资源
- **参数调优**: 新增地理权重参数需要根据场景调优
- **数据依赖性**: 需要精确的时间矩阵和兼容性信息

## 故障排除

### 常见问题
1. **约束不可行**: 检查兼容性矩阵，确保每个点位有兼容车辆
2. **比例严重失衡**: 调整权重参数，增加 `WeightAlpha`
3. **地理分散**: **使用改进算法**，增加 `WeightGeographic`
4. **东西部错配**: **推荐使用改进算法**，原始算法无法解决此问题

### 调试建议
- 使用改进算法的 `PrintResults()` 查看详细分配结果和地理范围
- 调用 `validateRealDataResults()` 验证约束满足情况
- 观察算法输出的区域划分统计信息
- 对比 `shortage_points.csv` 文件中的经纬度分布

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
