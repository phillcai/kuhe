# 甜品饮料补货算法 (Dessert Drink Replenishment Algorithm)


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
- **强约束应用**：确保不超过max(初始货道数, MaxLaneConstraint)，不少于MinLaneConstraint

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
4. **强约束**：`MinLaneConstraint ≤ AllocatedLanes ≤ max(InitialLanes, MaxLaneConstraint)`

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
algorithm.MinLaneConstraint = 1   // 最小货道约束
algorithm.MaxLaneConstraint = 2   // 最大货道约束

// 设置调试模式
SetDebugMode(true)  // 开启调试输出
```
