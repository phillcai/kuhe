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

- **弱约束**：
  - M_i 之间的比例接近 r_i 之间的比例（最小化比例偏差）

### 算法步骤
1. **计算理想目标数量**：基于预期比例计算各商品理想补货后数量
2. **施加最大允许数量约束**：限制补货后数量不超过最大允许值
3. **施加仓库库存约束**：限制补货量不超过仓库实际库存
4. **调整总补货量至目标**：通过比例关系偏差优化进行微调
5. **特殊情况处理**：处理目标总量无法达成等边界情况
6. **最终校验**：验证所有约束条件是否满足

## 文件结构

```
golang/
├── replenishment_algorithm.go  # 核心算法实现
├── main_replenishment.go      # 主程序和示例
├── replenishment_example.go   # 示例程序（已整合到主程序）
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
    ReplenishAmount   int     // 补货量 P_i
    FinalStock        int     // 补货后数量 M_i
    ActualRatio       float64 // 实际比例
    ExpectedRatio     float64 // 预期比例
}
```

## 使用方法

### 编译和运行

```bash
# 编译
go build -o replenishment main_replenishment.go replenishment_algorithm.go

# 运行所有示例
./replenishment

# 运行特定示例
./replenishment basic      # 基础示例
./replenishment complex    # 复杂示例
./replenishment boundary   # 边界情况示例
./replenishment performance# 性能测试
```

### 直接运行源码

```bash
# 运行所有示例
go run main_replenishment.go replenishment_algorithm.go

# 运行特定示例
go run main_replenishment.go replenishment_algorithm.go basic
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

### 1. 基础示例
- 使用文档中的三商品示例
- 验证算法与数学建模的一致性
- 展示标准的约束处理流程

### 2. 复杂示例  
- 5个商品，不同的约束条件
- 展示算法在复杂场景下的表现
- 分析比例偏差和约束满足情况

### 3. 边界情况示例
- 仓库库存严重不足的情况
- 目标总量无法达成的处理
- 展示算法的适应性和鲁棒性

### 4. 性能测试
- 大规模商品（50个商品）
- 测试算法的扩展性和精度
- 分析平均偏差和相对精度

## 算法优势

1. **数学严谨性**：基于完整的数学建模，理论基础扎实
2. **约束完整性**：同时处理硬约束和软约束
3. **比例优化**：关注商品间的比例关系而非绝对比例
4. **边界处理**：妥善处理各种边界情况和异常场景
5. **可扩展性**：支持大规模商品的补货计算
6. **实用性**：提供详细的结果分析和验证

## 性能特点

- **时间复杂度**：O(n²·k)，其中 n 为商品数量，k 为最大迭代次数
- **空间复杂度**：O(n)
- **收敛性**：通过最大迭代次数限制确保算法终止
- **精度**：支持到小数点后6位的比例精度

## 扩展建议

1. **并行化**：对于大规模商品，可以考虑并行计算比例偏差
2. **缓存优化**：缓存中间计算结果以提升性能
3. **动态调整**：支持运行时动态调整约束条件
4. **可视化**：添加结果可视化和过程监控
5. **持久化**：支持配置和结果的持久化存储

## 注意事项

1. **输入验证**：确保预期比例总和为1.0
2. **数值精度**：注意浮点数计算的精度问题
3. **约束冲突**：当约束条件过于严格时，算法会优先满足硬约束
4. **迭代控制**：合理设置最大迭代次数以平衡精度和性能
5. **边界处理**：在极端情况下，算法可能无法达到理想的比例关系

## 更新日志

- v1.0.0: 初始版本，实现完整的补货算法
- 支持所有文档中定义的约束条件
- 提供完整的示例和测试用例
- 包含性能测试和边界情况处理
