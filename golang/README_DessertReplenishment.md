# 甜品饮料补货算法 (Dessert Drink Replenishment Algorithm)

## 核心特性

- **多阶段优化策略**：七阶段递进式优化，确保解的质量和可行性
- **物理货道管理**：支持复杂的物理货道分配和状态管理
- **强约束保障**：严格保证货道容量、仓库库存等硬约束
- **比例平衡优化**：基于预期比例的目标函数，确保SKU分配比例合理
- **动态调整机制**：支持迭代优化和收敛控制
- **全局货道优化**：智能的空闲货道分配和优化策略

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
    ID               int   // 物理货道ID
    SupportedTypes   []int // 支持的货道类型列表
    CommodityID      int   // 分配的商品ID，0表示未占用
    Quantity         int   // 商品数量，未占用时为0
    ReplenishmentQty int   // 补货量，初始化为0
}
```

#### DessertAllocationResult (分配结果)
```go
type DessertAllocationResult struct {
    SKUID            string         // SKU ID
    AllocatedLanes   int            // 分配的货道数 L_i
    LaneCapacity     int            // 货道容量 C_i = LaneCapacityPerLane * L_i
    ReplenishmentQty int            // 补货量 P_i
    FinalStock       int            // 补货后数量 M_i
    CurrentUsedLanes int            // 当前占用货道数 L_i^current
    CanMeetMinStock  bool           // 是否可满足最小库存
    AssignedLanes    []PhysicalLane // 实际分配的物理货道列表
}
```

### 算法类：DessertReplenishmentAlgorithm

#### 主要属性
- `SKUs`: 所有SKU数据
- `LaneTypes`: 货道类型配置
- `PhysicalLanes`: 物理货道配置（每个货道支持的类型列表）
- `TotalLanes`: 总货道数 K
- `CompatibilityMatrix`: SKU与货道类型兼容性矩阵 A_{i,t}
- `WeightAlpha/Beta/Gamma`: 目标函数权重参数
- `MaxIterations`: 最大迭代次数
- `ConvergenceThres`: 收敛阈值
- `MaxLaneConstraint`: 最大货道约束配置
- `MinLaneConstraint`: 最小货道约束配置
- `skuIndexMap`: SKU ID到索引的映射，用于快速查找
- `isDebug`: 算法实例调试模式

#### 核心方法

##### 1. 构造函数
```go
func NewDessertReplenishmentAlgorithm() *DessertReplenishmentAlgorithm
```
- 创建算法实例并设置默认参数

##### 2. 初始化方法
```go
func (d *DessertReplenishmentAlgorithm) Initialize(skus []DessertSKU, laneTypes []LaneType, physicalLanes []PhysicalLane) error
```
- 初始化算法数据
- 构建兼容性矩阵
- 构建SKU索引映射
- 验证约束可行性

##### 3. 主要执行方法
```go
func (d *DessertReplenishmentAlgorithm) Execute() ([]DessertAllocationResult, error)
```
- 执行完整的七阶段优化流程
- 返回最终的分配结果

##### 4. 调试控制方法
```go
func (d *DessertReplenishmentAlgorithm) SetDebugMode(debug bool)
func (d *DessertReplenishmentAlgorithm) GetDebugMode() bool
```
- 设置和获取调试模式状态

##### 5. 约束配置方法
```go
func (d *DessertReplenishmentAlgorithm) SetMaxLaneConstraint(maxLanes int) error
func (d *DessertReplenishmentAlgorithm) SetMinLaneConstraint(minLanes int) error
```
- 设置最大和最小货道约束

## 七阶段优化策略

### 阶段0：约束验证 (validateConstraints)
- 验证每个SKU至少有一种兼容的货道类型
- 验证预期比例总和是否为1
- 确保输入数据的有效性

### 阶段1：货道兼容性分析 (stage1_LaneCompatibilityAnalysis)
- 计算每个SKU当前占用货道数
- 分析SKU与物理货道的兼容性
- 确定每个SKU的可用货道总数
- 初始化InitialLanes（如果未设置）

### 阶段2：初始货道分配 (stage2_InitialLaneAllocation)
- **物理货道预分配策略**：在逻辑分配阶段就考虑物理货道的实际可用性
- **填满优先 + 高预期比例优先**：优先分配比例高的SKU，尽可能填满货道
- **强约束应用**：确保不超过max(初始货道数, MaxLaneConstraint)，不少于MinLaneConstraint
- **三阶段分配**：最小约束 → 填满优先 → 剩余货道分配

### 阶段2.5：全局货道分配优化 (optimizeGlobalLaneAllocation)
- 查找所有空闲货道
- 为每个空闲货道寻找最优的SKU进行分配
- 智能的货道分配优化策略

### 阶段3：最小库存优先处理 (stage3_MinStockPriorityProcessing)
- 优先满足最小库存需求
- 在满足最小库存前提下，尽量填满货道容量
- 处理无法满足最小库存的SKU
- **物理货道分配**：根据预分配结果，找到对应的真实物理货道并分配给SKU

### 阶段4：比例平衡补货量计算 (stage4_ProportionalReplenishmentCalculation)
- 基于预期比例调整补货量
- 在货道容量和仓库库存约束下优化
- 保持阶段3的填满策略基础

### 阶段5：动态调整优化 (stage5_DynamicOptimization)
- 迭代优化目标函数
- 通过交换调整改善解的质量
- 收敛控制和约束验证

### 阶段6：总容量约束验证和修正 (validateAndFixTotalCapacity)
- 验证总库存是否超过总货道容量
- 从没有分配货道的SKU中减少库存
- 从分配了货道的SKU中减少库存

### 阶段7：货道容量约束验证 (validateCapacityConstraints)
- 验证每个SKU的最终库存是否超过货道容量
- 验证补货量是否超过仓库库存
- 验证最终库存计算是否正确

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
4. **强约束**：`MinLaneConstraint ≤ AllocatedLanes ≤ max(InitialLanes, MaxLaneConstraint)`
5. **物理货道约束**：每个物理货道只能分配给一个SKU
6. **货道类型兼容性约束**：SKU只能使用兼容的货道类型

### 软约束
1. **最小库存约束**：尽量满足 `FinalStock ≥ MinStock`
2. **比例平衡约束**：尽量接近预期比例
3. **货道利用率约束**：尽量提高货道利用率

## 使用方法

### 基本使用流程

```go
// 1. 创建算法实例
algorithm := NewDessertReplenishmentAlgorithm()

// 2. 准备输入数据
skus := []DessertSKU{...}
laneTypes := []LaneType{...}
physicalLanes := []PhysicalLane{...}

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
algorithm.MinLaneConstraint = 1   // 最小货道约束
algorithm.MaxLaneConstraint = 2   // 最大货道约束

// 设置调试模式
algorithm.SetDebugMode(true)  // 开启调试输出
```

## 业务常量

算法使用以下业务常量：

```go
const (
    // 货道相关常量
    LaneCapacityPerLane = 5 // 每个货道的容量（盒数）

    // 算法权重常量
    DefaultWeightAlpha = 0.5 // 默认比例平衡权重
    DefaultWeightBeta  = 0.2 // 默认货道利用率权重
    DefaultWeightGamma = 0.3 // 默认安全库存惩罚权重

    // 算法参数常量
    DefaultMaxIterations     = 100  // 默认最大迭代次数
    DefaultConvergenceThres  = 0.01 // 默认收敛阈值
    DefaultMaxLaneConstraint = 2    // 默认最大货道约束
    DefaultMinLaneConstraint = 1    // 默认最小货道约束

    // 计算参数常量
    RatioToleranceThreshold  = 0.01 // 比例容差阈值
    WarehouseUtilizationRate = 0.8  // 仓库库存利用率（80%）
)
```

## 核心算法特性

### 物理货道管理
- **货道状态跟踪**：实时跟踪每个物理货道的占用状态
- **兼容性检查**：确保SKU只能使用兼容的货道类型
- **智能分配策略**：优先选择支持更多SKU类型的货道（提高灵活性）

### 全局优化策略
- **空闲货道优化**：自动发现并分配空闲货道给最优SKU
- **货道利用率最大化**：通过智能分配提高整体货道利用率
- **约束平衡**：在满足硬约束的前提下优化软约束

### 调试和监控
- **详细日志输出**：支持调试模式，输出详细的算法执行过程
- **物理货道状态显示**：实时显示所有物理货道的分配状态
- **性能指标统计**：提供货道利用率、比例偏差等关键指标
