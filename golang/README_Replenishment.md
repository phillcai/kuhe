# 带最大允许数量约束的补货算法

## 概述

这是基于数学建模文档实现的带最大允许数量约束的补货算法的 Golang 版本。算法的核心目标是在满足各种约束条件的前提下，使商品之间的比例关系尽可能接近预期比例关系。

## 算法特点

### 核心约束
- **强约束**：
  1. 总补货量不超过仓库总库存
  2. 单商品补货量不超过对应仓库库存  
  3. 补货后数量不超过最大允许值
  4. 不允许负补货
  5. 货道容量约束（每个货道最多3个商品）

- **弱约束**：
  - M_i 之间的比例接近 r_i 之间的比例（最小化比例偏差）

### 新增特性
- **动态货道分配**：智能分配空余货道，采用轮询策略避免重复分配
- **向上取整**：MaxAllowed 计算采用向上取整，提高补货灵活性
- **剩余潜力分析**：计算每个商品的剩余补货潜力

### 算法步骤
1. **计算理想目标数量**：基于预期比例计算各商品理想补货后数量
2. **施加最大允许数量约束**：限制补货后数量不超过最大允许值
3. **施加仓库库存约束**：限制补货量不超过仓库实际库存
4. **调整总补货量至目标**：通过比例关系偏差优化进行微调
5. **动态货道分配**：智能分配空余货道，采用轮询策略优化货道使用
6. **特殊情况处理**：处理目标总量无法达成等边界情况
7. **最终校验**：验证所有约束条件是否满足

## 可配置参数

### 核心算法参数

#### 1. ToleranceRatio（比例偏差容忍度）
- **参数类型**: `float64`
- **取值范围**: `0.01` ~ `0.3`
- **推荐值**: `0.05` ~ `0.15`
- **默认值**: `0.1`
- **作用**: 控制商品比例关系的精确度要求
- **影响**:
  - `≤ 0.05`: 高精度模式，比例关系要求严格，算法收敛较慢
  - `0.05 ~ 0.1`: 平衡模式，精度和效率兼顾（推荐）
  - `0.1 ~ 0.2`: 快速收敛模式，允许较大比例偏差
  - `> 0.2`: 宽松模式，主要用于快速测试和原型验证

#### 2. MaxIterations（最大迭代次数）
- **参数类型**: `int`
- **取值范围**: `50` ~ `1000`
- **推荐值**: `100` ~ `300`
- **默认值**: `200`
- **作用**: 限制算法最大循环次数，防止死循环
- **影响**:
  - `≤ 100`: 快速执行，但可能无法达到最优解
  - `100 ~ 300`: 平衡模式，推荐用于生产环境
  - `300 ~ 500`: 高精度模式，适合复杂场景
  - `> 500`: 极高精度模式，仅用于特殊需求


### 高级调优参数

#### 3. 库存充足度调整因子阈值
- **相似度阈值**: `0.005`（5‰）
- **相对库存阈值**: `0.8` 和 `1.2`
- **调整因子范围**: `-0.02` ~ `+0.1`
- **作用**: 在比例关系优化的基础上，根据库存状况微调优先级
- **调整建议**:
  - 提高相似度阈值（如 `0.01`）: 扩大比较范围，调整更激进
  - 降低相似度阈值（如 `0.001`）: 缩小比较范围，调整更保守
  - 调整相对库存阈值: 改变库存充足度的判断标准



## 参数配置建议

### 生产环境推荐配置
```go
config := ReplenishmentConfig{
    TargetTotal:    业务目标总量,
    MaxCapacity:    业务最大容量,
    MaxIterations:  200,        // 平衡精度和效率
    ToleranceRatio: 0.1,        // 10%容忍度，适合大多数场景
}
```

### 高精度场景配置
```go
config := ReplenishmentConfig{
    TargetTotal:    业务目标总量,
    MaxCapacity:    业务最大容量,
    MaxIterations:  500,        // 高精度模式
    ToleranceRatio: 0.05,       // 5%容忍度，严格要求
}
```

### 快速测试配置
```go
config := ReplenishmentConfig{
    TargetTotal:    业务目标总量,
    MaxCapacity:    业务最大容量,
    MaxIterations:  100,        // 快速执行
    ToleranceRatio: 0.15,       // 15%容忍度，快速收敛
}
```


## 文件结构

```
golang/
├── replenishment_algorithm.go  # 核心算法实现
├── csv_algorithm_calculator.go # CSV数据解析和算法计算器
├── dynamic_test_runner.go     # 动态测试运行器
└── README_Replenishment.md    # 本文档
```

## 核心数据结构

### Product（商品信息）
```go
type Product struct {
    ID           string  // 商品标识
    Name         string  // 商品名称  
    WarehouseStock int   // 仓库库存 N_i
    CurrentStock   int   // 点位现有量 G_i
    MaxAllowed     int   // 最大允许补货后数量 X_i
    ExpectedRatio  float64 // 预期比例 r_i
}
```

### ReplenishmentConfig（算法配置）
```go
type ReplenishmentConfig struct {
    TargetTotal     int     // 目标补货后总量 M
    MaxCapacity     int     // 点位最大库存 K
    MaxIterations   int     // 最大循环次数
    ToleranceRatio  float64 // 比例偏差容忍度
}
```

**配置参数详细说明**:

| 参数 | 类型 | 取值范围 | 默认值 | 说明 |
|------|------|----------|--------|------|
| `TargetTotal` | `int` | `> 0` | 业务需求 | 目标补货后总量，必须大于0 |
| `MaxCapacity` | `int` | `≥ 3` | 业务需求 | 点位最大库存，影响货道分配 |
| `MaxIterations` | `int` | `50 ~ 1000` | `200` | 最大迭代次数，防止死循环 |
| `ToleranceRatio` | `float64` | `0.01 ~ 0.3` | `0.1` | 比例偏差容忍度，控制精度 |

### ReplenishmentResult（补货结果）
```go
type ReplenishmentResult struct {
    ProductID         string  // 商品ID
    CurrentStock      int     // 当前库存 G_i
    WarehouseStock    int     // 仓库库存 N_i
    MaxAllowed        int     // 最大允许数量 X_i
    ReplenishAmount   int     // 补货量 P_i
    FinalStock        int     // 补货后数量 M_i
    ActualRatio       float64 // 实际比例
    ExpectedRatio     float64 // 预期比例
}
```

## 使用方法


### 直接运行源码

```bash
# 运行CSV计算器
go run csv_algorithm_calculator.go replenishment_algorithm.go

# 运行动态测试
go run dynamic_test_runner.go replenishment_algorithm.go
```

### 编程使用示例

```go
package main

import "fmt"

func main() {
    // 1. 创建商品列表
    products := []Product{
        {
            ID:            "A",
            Name:          "商品A",
            WarehouseStock: 10,  // 仓库库存
            CurrentStock:   2,   // 当前库存
            MaxAllowed:     8,   // 最大允许数量
            ExpectedRatio:  0.5, // 预期比例
        },
        {
            ID:            "B",
            Name:          "商品B", 
            WarehouseStock: 5,
            CurrentStock:   1,
            MaxAllowed:     4,
            ExpectedRatio:  0.3,
        },
        {
            ID:            "C",
            Name:          "商品C",
            WarehouseStock: 8,
            CurrentStock:   0,
            MaxAllowed:     6,
            ExpectedRatio:  0.2,
        },
    }
    
    // 2. 创建算法配置
    config := ReplenishmentConfig{
        TargetTotal:    12,  // 目标补货后总量
        MaxCapacity:    20,  // 点位最大库存
        MaxIterations:  200, // 最大迭代次数
        ToleranceRatio: 0.1, // 比例偏差容忍度
    }
    
    // 3. 创建算法实例并执行
    algorithm := NewReplenishmentAlgorithm(products, config)
    results, err := algorithm.Execute()
    
    if err != nil {
        fmt.Printf("算法执行失败: %v\n", err)
        return
    }
    
    // 4. 打印结果
    algorithm.PrintResults()
    
    // 5. 处理结果
    for _, result := range results {
        fmt.Printf("商品 %s 需要补货 %d 个单位\n", 
            result.ProductID, result.ReplenishAmount)
    }
}
```

## 示例说明

### 1. CSV数据测试（csv_algorithm_calculator.go）
- 解析真实CSV数据格式
- 支持车辆库存、货架分配、补货详情等复杂数据结构
- 自动计算MaxAllowed（5天预测量 × 预期比例，向上取整）

### 2. 动态测试（dynamic_test_runner.go）
- 支持按ReqID动态执行测试用例
- 完整的结果分析和对比
- 包含剩余补货潜力分析


## 性能特点

- **时间复杂度**：O(n²·k)，其中 n 为商品数量，k 为最大迭代次数
- **空间复杂度**：O(n)
- **收敛性**：通过最大迭代次数限制确保算法终止
- **精度**：支持到小数点后6位的比例精度
- **货道分配效率**：轮询策略确保公平分配，避免重复选择
- **防死循环**：多层防护机制确保算法安全终止




## 功能详解

### 动态货道分配算法

#### 核心特性
- **轮询分配策略**：确保每个候选商品都有平等的分配机会
- **智能货道利用**：充分利用每个货道的3个商品容量
- **防重复分配**：避免连续分配给同一商品，提高资源均衡性

#### 算法流程
1. **候选商品筛选**：预检查所有可分配货道的商品
2. **轮询选择**：按顺序尝试每个候选商品
3. **容量计算**：计算新货道能增加的库存量
4. **约束检查**：验证仓库库存、MaxAllowed等约束
5. **货道分配**：分配货道并更新相关状态
6. **循环控制**：设置最大迭代次数防止死循环

#### 轮询策略示例
```
候选商品队列: [商品A, 商品B, 商品C]
第1次分配: 商品A ✅
第2次分配: 商品B ✅  
第3次分配: 商品C ✅
第4次分配: 商品A ✅ (回到A)
第5次分配: 商品B ✅ (回到B)
... (循环往复)
```

### CSV数据支持

#### 支持的数据结构
- **车辆库存数据**：`car_sku_detail` 字段
- **货架分配数据**：`shelf_allocation_before` 字段
- **补货详情数据**：`commodity_restock_detail` 字段
- **点位扩展数据**：`point_ext` 字段

#### 数据解析流程
1. **CSV记录解析**：解析标准CSV格式数据
2. **JSON字段解析**：解析嵌套的JSON格式字段
3. **数据整合**：将多个数据源整合为统一的商品结构
4. **约束计算**：自动计算MaxAllowed等约束参数

## 参数调优最佳实践

### 性能调优指南

#### 1. 算法收敛性调优
- **问题**: 算法无法在MaxIterations内收敛
- **解决方案**: 
  - 增加 `MaxIterations` 到 300-500
  - 适当放宽 `ToleranceRatio` 到 0.15-0.2
  - 检查输入数据的合理性

#### 2. 精度与效率平衡
- **高精度需求**: `ToleranceRatio: 0.05`, `MaxIterations: 500`
- **平衡模式**: `ToleranceRatio: 0.1`, `MaxIterations: 200`
- **快速模式**: `ToleranceRatio: 0.15`, `MaxIterations: 100`

#### 3. 内存使用优化
- **商品数量 > 100**: 考虑分批处理
- **复杂约束**: 适当减少 `MaxIterations` 避免过度计算
- **货道分配**: 对于大量货道，考虑优化分配策略



### 故障排除

#### 常见问题及解决方案

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| 算法无法收敛 | `MaxIterations` 过小 | 增加到 300-500 |
| 比例偏差过大 | `ToleranceRatio` 过小 | 适当放宽到 0.15-0.2 |
| 执行时间过长 | 商品数量过多或约束复杂 | 减少 `MaxIterations` 或放宽 `ToleranceRatio` |
| 货道分配失败 | `MaxCapacity` 设置不合理 | 确保 `MaxCapacity ≥ 3` 且为3的倍数 |
| 库存约束冲突 | 输入数据不合理 | 检查仓库库存和最大允许数量设置 |


### 监控指标

#### 关键性能指标
- **收敛时间**: 算法达到收敛的迭代次数
- **比例偏差**: 最终商品比例关系的偏差程度
- **货道利用率**: 货道分配的效率
- **约束满足率**: 各种约束条件的满足程度


