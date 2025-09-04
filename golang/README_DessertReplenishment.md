# 甜品补货算法 (Dessert Replenishment Algorithm)

## 概述

甜品补货算法是一个基于多目标优化的智能分拣系统，用于解决共享货道环境下的甜品SKU补货分配问题。该算法通过五阶段优化策略，在满足多种业务约束的前提下，最大化货道利用率和比例平衡精度。

## 核心特性

- **多阶段优化策略**：五阶段递进式优化，确保解的质量和可行性
- **共享货道支持**：支持多种SKU类型共享物理货道的复杂场景
- **强约束保障**：严格保证货道容量、仓库库存等硬约束
- **比例平衡优化**：基于预期比例的目标函数，确保SKU分配比例合理
- **动态调整机制**：支持迭代优化和收敛控制

## 算法架构

### 核心数据结构

#### DessertSKU (甜品SKU)
```go
type DessertSKU struct {
    ID              string  // SKU标识
    CurrentStock    int     // 点位当前剩余数量 G_i
    WarehouseStock  int     // 仓库库存 N_i
    MinStock        int     // 最小库存（安全库存）S_i
    ExpectedRatio   float64 // 预期比例 r_i
    CompatibleLanes []int   // 兼容的货道类型
    Importance      float64 // 重要性权重 w_i
    ActualUsedLanes int     // 实际占用的货道数
    InitialLanes    int     // 初始货道数（强约束）
}
```

#### LaneType (货道类型)
```go
type LaneType struct {
    ID         int // 货道类型ID
    TotalLanes int // 该类型的总货道数 L_t^total
}
```

#### PhysicalLane (物理货道)
```go
type PhysicalLane struct {
    ID             int   // 物理货道ID
    SupportedTypes []int // 支持的货道类型列表
}
```

### 算法类：DessertReplenishmentAlgorithm

#### 主要属性
- `SKUs`: 所有SKU数据
- `LaneTypes`: 货道类型配置
- `PhysicalLanes`: 物理货道配置
- `CompatibilityMatrix`: SKU与货道类型兼容性矩阵
- `WeightAlpha/Beta/Gamma`: 目标函数权重参数

#### 核心方法

##### 1. 初始化方法
```go
func (d *DessertReplenishmentAlgorithm) Initialize(skus []DessertSKU, laneTypes []LaneType, physicalLanes map[int][]int) error
```
- 初始化算法数据
- 构建兼容性矩阵
- 验证约束可行性

##### 2. 主要执行方法
```go
func (d *DessertReplenishmentAlgorithm) Execute() ([]DessertAllocationResult, error)
```
- 执行完整的五阶段优化流程
- 返回最终的分配结果

## 五阶段优化策略

### 阶段1：货道兼容性分析 (stage1_LaneCompatibilityAnalysis)
- 计算每个SKU当前占用货道数
- 分析SKU与物理货道的兼容性
- 确定每个SKU的可用货道总数

### 阶段2：初始货道分配 (stage2_InitialLaneAllocation)
- **需求驱动分配**：基于SKU需求进行智能分配
- **比例分配回退**：当需求超过容量时的备选策略
- **强约束应用**：确保不超过max(初始货道数, MinLaneConstraint)

### 阶段3：最小库存优先处理 (stage3_MinStockPriorityProcessing)
- 优先满足最小库存需求
- 在满足最小库存前提下，尽量填满货道容量
- 处理无法满足最小库存的SKU

### 阶段4：比例平衡补货量计算 (stage4_ProportionalReplenishmentCalculation)
- 基于预期比例调整补货量
- 在货道容量和仓库库存约束下优化
- 保持阶段3的填满策略基础

### 阶段5：动态调整优化 (stage5_DynamicOptimization)
- 迭代优化目标函数
- 通过交换调整改善解的质量
- 收敛控制和约束验证

## 目标函数

算法优化的目标函数包含三个组成部分：

```
Objective = α × ProportionTerm - β × UtilizationTerm + γ × SafetyPenalty
```

- **比例平衡项 (ProportionTerm)**：最小化实际比例与预期比例的偏差
- **货道利用率项 (UtilizationTerm)**：最大化货道利用率
- **安全库存惩罚项 (SafetyPenalty)**：惩罚不满足最小库存的SKU

## 约束条件

### 硬约束
1. **货道容量约束**：`FinalStock ≤ LaneCapacity`
2. **仓库库存约束**：`ReplenishmentQty ≤ WarehouseStock`
3. **总货道数约束**：`∑AllocatedLanes ≤ TotalLanes`
4. **强约束**：`AllocatedLanes ≤ max(InitialLanes, MinLaneConstraint)`

### 软约束
1. **最小库存约束**：尽量满足 `FinalStock ≥ MinStock`
2. **比例平衡约束**：尽量接近预期比例

## 使用方法

### 基本使用流程

```go
// 1. 创建算法实例
algorithm := NewDessertReplenishmentAlgorithm()

// 2. 准备输入数据
skus := []DessertSKU{...}
laneTypes := []LaneType{...}
physicalLanes := map[int][]int{...}

// 3. 初始化算法
err := algorithm.Initialize(skus, laneTypes, physicalLanes)
if err != nil {
    // 处理错误
}

// 4. 执行算法
results, err := algorithm.Execute()
if err != nil {
    // 处理错误
}

// 5. 处理结果
for _, result := range results {
    fmt.Printf("SKU %s: 分配货道=%d, 补货量=%d, 最终库存=%d\n",
        result.SKUID, result.AllocatedLanes, result.ReplenishmentQty, result.FinalStock)
}
```

### 配置参数

```go
// 设置算法权重
algorithm.WeightAlpha = 0.5  // 比例平衡权重
algorithm.WeightBeta = 0.2    // 货道利用率权重
algorithm.WeightGamma = 0.3  // 安全库存惩罚权重

// 设置算法参数
algorithm.MaxIterations = 100      // 最大迭代次数
algorithm.ConvergenceThres = 0.01 // 收敛阈值
algorithm.MinLaneConstraint = 2    // 最小货道约束

// 设置调试模式
SetDebugMode(true)  // 开启调试输出
```

## 测试框架

### 测试用例结构

测试框架支持从CSV文件解析真实业务数据：

```go
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
    DebugData                   *DebugDataInfo
}
```

### 运行测试

#### 1. 单个测试用例
```bash
go test -v -run TestDessertReplenishmentWithSpecificReqID
```

#### 2. 批量测试
```bash
go test -v -run TestBatchReqIDs
```

#### 3. 自定义测试用例
```bash
# 修改TestCustomReqID中的reqID和commodityType
go test -v -run TestCustomReqID
```

#### 4. 参数化测试
```bash
export TEST_REQ_ID="132e5889c453b6f4"
export TEST_COMMODITY_TYPE="6"
go test -v -run TestParameterizedReqID
```

### 测试数据文件

测试使用 `../data/分拣饮料甜品 case.csv` 文件，包含：
- 真实的业务场景数据
- 多种req_id和commodity_type组合
- 完整的SKU、货道、库存信息

## 性能指标

### 算法评估指标

1. **比例精度**：实际比例与预期比例的偏差
   - 优秀：平均偏差 < 1%
   - 良好：平均偏差 < 2%

2. **货道利用率**：已分配货道数 / 总货道数
   - 良好：利用率 > 80%
   - 中等：利用率 > 60%

3. **约束满足度**：硬约束违反数量
   - 优秀：0个违反
   - 可接受：≤ 2个违反

### 输出示例

```
=== 甜品分拣补货分配结果 ===

SKU SKU001 (预期比例: 0.25):
  当前库存: 10
  仓库库存: 50
  最小库存: 15
  分配货道数: 3
  货道容量: 15
  补货量: 5
  补货后库存: 15
  可满足最小库存: true

=== 总体指标 ===
总货道数: 20
分配货道数: 18
货道利用率: 90.00%
总补货量: 45
补货后总库存: 180
比例偏差: 0.0023
目标函数值: 0.1567
```

## 配置说明

### 业务常量

```go
const (
    LaneCapacityPerLane = 5        // 每个货道的容量（盒数）
    DefaultWeightAlpha = 0.5       // 默认比例平衡权重
    DefaultWeightBeta = 0.2        // 默认货道利用率权重
    DefaultWeightGamma = 0.3       // 默认安全库存惩罚权重
    DefaultMaxIterations = 100     // 默认最大迭代次数
    DefaultConvergenceThres = 0.01 // 默认收敛阈值
    DefaultMinLaneConstraint = 2   // 默认最小货道约束
)
```

### 调试控制

```go
var isDebug bool = true  // 全局调试开关

// 设置调试模式
func SetDebugMode(debug bool)
func GetDebugMode() bool

// 调试打印
func debugPrint(format string, args ...interface{})
```

## 扩展性

### 自定义目标函数

可以通过修改 `calculateObjective` 方法实现自定义的目标函数：

```go
func (d *DessertReplenishmentAlgorithm) calculateObjective(results []DessertAllocationResult) float64 {
    // 实现自定义目标函数逻辑
    return customObjectiveValue
}
```

### 新增约束条件

可以在相应的验证方法中添加新的约束检查：

```go
func (d *DessertReplenishmentAlgorithm) validateCustomConstraints(results []DessertAllocationResult) error {
    // 实现自定义约束验证
    return nil
}
```

## 注意事项

1. **数据一致性**：确保输入数据的完整性和一致性
2. **约束冲突**：当硬约束冲突时，算法会优先满足容量约束
3. **收敛性**：对于复杂场景，可能需要调整迭代参数
4. **性能考虑**：大规模SKU场景下，建议适当调整算法参数

## 版本历史

- **v1.0**: 基础五阶段优化算法实现
- **v1.1**: 增加共享货道支持和强约束机制
- **v1.2**: 优化比例平衡算法和测试框架
- **v1.3**: 完善调试输出和性能指标

## 贡献指南

欢迎提交Issue和Pull Request来改进算法：

1. Fork项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建Pull Request

## 许可证

本项目采用MIT许可证，详见LICENSE文件。
