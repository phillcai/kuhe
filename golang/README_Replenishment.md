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
        MaxIterations:  100, // 最大迭代次数
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
