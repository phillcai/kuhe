# 货道约束补货算法调整说明

## 概述

本文档说明了对补货算法步骤4（总补货量调整）的调整，以满足新的货道约束条件。

## 约束条件

- **点位最大库存**: K
- **货道数量**: K/3 个货道
- **每个货道容量**: 每个货道只能放 3 个相同的商品
- **商品分配**: 每个商品可以有多个货道
- **货道使用**: 不需要保证每个货道都填满，商品可以部分使用货道

### 货道使用示例
- 商品A分配3个货道，最大库存 = 3 × 3 = 9
- 如果商品A最终库存是7：
  - 货道1：3个商品（满）
  - 货道2：3个商品（满）  
  - 货道3：1个商品（部分使用）
- 这种使用方式是完全合理的

## 核心逻辑

### 1. 货道分配策略

每个商品的最大库存 = 3 × 该商品可用的货道数量

```go
// 计算总货道数
totalLanes := maxCapacity / 3

// 按预期比例分配货道给每个商品
for i, product := range products {
    idealLanes := product.ExpectedRatio * float64(totalLanes)
    laneAllocation[i] = int(math.Round(idealLanes))
}

// 每个商品的最大库存
maxLaneStock := 3 * availableLanes
```

### 2. 算法调整

#### 步骤4: 总补货量调整
在原有的步骤4中增加了货道约束的应用：

```go
func (ra *ReplenishmentAlgorithm) adjustToTargetTotal(tempAmounts []int, idealTargets []int) []int {
    finalAmounts := make([]int, len(tempAmounts))
    copy(finalAmounts, tempAmounts)

    // 应用货道约束：每个商品最大库存 = 3 × 可用货道数量
    finalAmounts = ra.applyLaneConstraints(finalAmounts)
    
    // 继续原有的缺口/超额处理逻辑...
}
```

#### 新增函数: applyLaneConstraints
```go
func (ra *ReplenishmentAlgorithm) applyLaneConstraints(amounts []int) []int {
    // 计算总货道数
    totalLanes := ra.config.MaxCapacity / 3
    
    // 按预期比例分配货道给每个商品
    laneAllocation := ra.allocateLanesByRatio(totalLanes)
    
    for i, product := range ra.products {
        // 该商品可用的货道数
        availableLanes := laneAllocation[i]
        
        // 该商品的最大库存 = 3 × 可用货道数
        maxLaneStock := 3 * availableLanes
        
        // 该商品的最大允许补货量
        maxAllowedByLane := maxLaneStock - product.CurrentStock
        
        if maxAllowedByLane < 0 {
            maxAllowedByLane = 0
        }

        // 取货道约束和原有约束的最小值
        if constrainedAmounts[i] > maxAllowedByLane {
            constrainedAmounts[i] = maxAllowedByLane
        }
    }
    
    return constrainedAmounts
}
```

### 3. 货道分配算法

#### 智能动态分配策略
算法现在支持两种货道分配策略：

##### 3.1 动态分配（优先）
根据实际库存需求动态分配货道，最大化货道使用效率：

```go
func (ra *ReplenishmentAlgorithm) allocateLanesDynamically(totalLanes int, amounts []int) []int {
    // 1. 计算每个商品实际需要的货道数
    for i, product := range ra.products {
        finalStock := product.CurrentStock + amounts[i]
        if finalStock > 0 {
            requiredLanes[i] = (finalStock + 2) / 3 // 向上取整
        }
    }
    
    // 2. 如果总需求 <= 总货道数，直接分配 + 剩余货道优化分配
    // 3. 如果总需求 > 总货道数，按效率优化分配
}
```

**动态分配优势：**
- 根据实际需求分配，避免浪费
- 支持货道部分填充（如7个商品占用3个货道）
- 剩余货道按增长潜力分配
- 超出容量时按效率优先分配

##### 3.2 比例分配（回退）
当动态分配不可行时，回退到传统的按比例分配：

```go
func (ra *ReplenishmentAlgorithm) allocateLanesByRatio(totalLanes int) []int {
    // 按预期比例分配货道
    for i, product := range ra.products {
        idealLanes := product.ExpectedRatio * float64(totalLanes)
        laneAllocation[i] = int(math.Round(idealLanes))
    }
    // 调整取整误差，确保总和等于总货道数
}
```

#### 分配策略选择
```go
func (ra *ReplenishmentAlgorithm) applyLaneConstraints(amounts []int) []int {
    // 1. 尝试动态分配
    dynamicAllocation := ra.allocateLanesDynamically(totalLanes, amounts)
    
    // 2. 验证动态分配可行性
    if ra.validateDynamicAllocation(dynamicAllocation, amounts) {
        return ra.applyLaneAllocation(amounts, dynamicAllocation)
    }
    
    // 3. 回退到比例分配
    laneAllocation := ra.allocateLanesByRatio(totalLanes)
    return ra.applyLaneAllocation(amounts, laneAllocation)
}
```

### 4. 约束检查更新

更新了以下函数以考虑货道约束：

- `canIncrement()`: 检查是否可以增加补货量
- `findSupplementableCandidates()`: 找出可补商品
- `validateFinalResults()`: 最终校验
- `applyMaxAllowedConstraints()`: 施加最大允许数量约束
- `handleSpecialCases()`: 特殊情况处理

### 5. 货道使用情况分析

新增了货道使用情况分析功能：

```go
func (ra *ReplenishmentAlgorithm) printLaneUsage(amounts []int) {
    // 显示每个商品的：
    // - 分配货道数
    // - 当前库存
    // - 补货量
    // - 补货后库存
    // - 货道利用率
}
```

## 主要改进

### 1. 约束层次
原有约束优先级：
1. 仓库库存约束
2. 最大允许数量约束（含30%容量限制）

新增约束优先级：
1. 仓库库存约束
2. **货道约束**（新增）
3. 最大允许数量约束（含30%容量限制）

### 2. 容量计算
- **原有**: 仅考虑点位总容量K
- **新增**: 考虑货道数量限制，每个商品最大库存受货道数量约束

### 3. 分配策略
- **原有**: 按预期比例直接分配库存
- **新增**: 先按预期比例分配货道，再根据货道计算最大库存

## 使用示例

```go
// 创建商品列表
products := []Product{
    {ID: "A", ExpectedRatio: 0.4, CurrentStock: 2, WarehouseStock: 20, MaxAllowed: 15},
    {ID: "B", ExpectedRatio: 0.3, CurrentStock: 1, WarehouseStock: 15, MaxAllowed: 10},
    // ...
}

// 创建配置
config := ReplenishmentConfig{
    TargetTotal:   25,
    MaxCapacity:   30, // 总容量30，意味着有10个货道
    MaxIterations: 100,
}

// 执行算法
algorithm := NewReplenishmentAlgorithm(products, config)
results, err := algorithm.Execute()

// 查看货道使用情况
algorithm.PrintResults()
```

## 验证机制

算法包含多层验证：

1. **货道分配验证**: 确保货道分配总数等于总货道数
2. **约束验证**: 确保每个商品的最终库存不超过货道约束
3. **比例验证**: 分析最终比例与预期比例的偏差
4. **容量验证**: 确保总库存不超过点位容量

## 输出信息

算法执行后会输出：

1. **货道分配验证**: 显示每个商品的预期货道数vs实际分配货道数
2. **货道使用情况分析**: 显示每个商品的货道利用率
3. **补货结果**: 显示最终的补货量和库存分布
4. **约束验证**: 确认所有约束都得到满足

## 注意事项

1. **货道分配**: 货道按预期比例分配，可能存在取整误差，算法会自动调整
2. **约束优先级**: 货道约束优先于原有的最大允许数量约束
3. **特殊情况**: 当目标总量无法达成时，会考虑货道容量限制重新计算目标
4. **性能**: 货道分配计算会在多个地方调用，但计算复杂度较低

## 总结

### 🎯 核心改进

1. **智能货道分配**：
   - 动态分配策略优先，根据实际需求分配货道
   - 比例分配作为回退，确保算法稳定性
   - 支持货道部分填充，提高空间利用率

2. **灵活约束处理**：
   - 每个商品可占用多个货道
   - 不强制填满每个货道
   - 例：7个商品可占用3个货道（3+3+1的分布）

3. **效率优化**：
   - 剩余货道按增长潜力分配
   - 容量不足时按效率优先分配
   - 最大化货道使用价值

### 📊 算法特性

- **约束层次**：货道约束 > 仓库库存约束 > 最大允许数量约束
- **分配策略**：动态分配 → 比例分配（回退）
- **使用方式**：支持部分填充，无需强制填满货道
- **优化目标**：最大化货道使用效率和比例匹配度

### 🔧 实际应用

通过引入货道约束和智能分配策略，补货算法能够：
- 更好地反映实际的物理限制
- 提高货道空间利用率
- 确保补货方案在实际执行中的可行性
- 保持原有的比例优化逻辑

算法现在完全符合您描述的约束条件，既保证了货道容量限制，又允许灵活高效的货道使用方式。