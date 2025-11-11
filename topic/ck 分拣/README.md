# CK分拣优化算法 - Golang实现

## 概述

本实现基于 `ck 分拣数学建模.md` 文档，提供了完整的CK分拣优化算法Golang实现。

## 文件结构

```
topic/ck 分拣/
├── ck 分拣数学建模.md      # 数学建模文档
├── ck 库存.csv              # 真实库存数据（CSV格式）
├── ck_picking_optimizer.go  # 核心算法实现
├── main.go                  # 示例程序
├── ck_picking_test.go       # 单元测试
├── test_with_real_data.go   # 真实数据测试脚本
├── run_test.sh              # 测试运行脚本
└── README.md                # 本文档
```

## 核心类说明

### CKPickingOptimizer

CK分拣优化器，实现了完整的6步优化算法。

#### 主要方法

- `NewCKPickingOptimizer(targetTotal, shelfLayers int, skus []SKUInfo) *CKPickingOptimizer`
  - 创建新的优化器实例
  
- `Optimize() error`
  - 执行完整的优化算法，返回错误（如果有）

- `PrintResults()`
  - 打印优化结果和指标

#### 数据结构

**SKUInfo** - SKU信息
```go
type SKUInfo struct {
    ID          int     // SKU标识
    Stock       int     // 仓库库存 N_i
    Ratio       float64 // 仓库比例 r_i（自动计算）
    MaxQuantity int     // 单SKU上限 x_i^{max}（自动计算）
}
```

**PickingResult** - 分拣结果
```go
type PickingResult struct {
    SKUID       int     // SKU标识
    Quantity    int     // 分拣数量 x_i
    ShelfLayers int     // 占用层数 L_i
    ActualRatio float64 // 实际比例
}
```

**OptimizationMetrics** - 优化指标
```go
type OptimizationMetrics struct {
    TotalQuantity      int     // 实际分拣总量 X
    TargetAchievement  float64 // 目标达成率
    ProportionDeviation float64 // 比例偏差
    ShelfUtilization   float64 // 货架利用率
    EmptyLayers        int     // 空余层数
}
```

## 使用示例

### 基本使用

```go
package main

import "fmt"

func main() {
    // 1. 定义输入参数
    targetTotal := 100  // 目标分拣总量 M
    shelfLayers := 15    // 车辆货架层数 n
    
    // 2. 定义SKU列表
    skus := []SKUInfo{
        {ID: 1, Stock: 50},
        {ID: 2, Stock: 30},
        {ID: 3, Stock: 25},
        {ID: 4, Stock: 15},
        {ID: 5, Stock: 5},
    }
    
    // 3. 创建优化器
    optimizer := NewCKPickingOptimizer(targetTotal, shelfLayers, skus)
    
    // 4. 执行优化
    if err := optimizer.Optimize(); err != nil {
        fmt.Printf("优化失败: %v\n", err)
        return
    }
    
    // 5. 查看结果
    optimizer.PrintResults()
    
    // 6. 访问详细结果
    for _, result := range optimizer.Results {
        fmt.Printf("SKU %d: 分拣 %d 个, 占用 %d 层\n",
            result.SKUID, result.Quantity, result.ShelfLayers)
    }
    
    // 7. 查看优化指标
    metrics := optimizer.Metrics
    fmt.Printf("目标达成率: %.2f%%\n", metrics.TargetAchievement)
    fmt.Printf("比例偏差: %.4f\n", metrics.ProportionDeviation)
    fmt.Printf("货架利用率: %.2f%%\n", metrics.ShelfUtilization)
}
```

## 算法步骤

算法按照文档中的6个步骤执行：

1. **参数初始化与约束检查**
   - 计算仓库总库存和SKU比例
   - 检查可行性（库存、容量、全SKU包含）
   - 计算单SKU上限

2. **初始分拣量计算**
   - 基于比例计算理想分拣量
   - 应用单SKU上限约束
   - 应用仓库库存约束
   - 应用全SKU包含约束（确保每个SKU至少1个）

3. **货架层数分配**
   - 计算所需层数：$L_i = \lceil x_i / 9 \rceil$
   - 检查总层数约束
   - 如果超限，按比例偏差调整

4. **目标总量调整**
   - 如果存在缺口，增加分拣量
   - 如果存在超额，减少分拣量
   - 使用改善得分机制选择最优调整

5. **货架利用率优化**
   - 识别空余层数
   - 按比例平衡优先级分配空余层数

6. **最终验证与输出**
   - 验证所有强约束
   - 计算优化指标
   - 构建结果输出

## 约束条件

算法自动满足以下强约束：

1. ✅ **车辆容量约束**: $X \leq 9n$
2. ✅ **仓库库存约束**: $x_i \leq N_i$
3. ✅ **单SKU上限约束**: $x_i \leq 0.2M$
4. ✅ **全SKU包含约束**: $x_i \geq 1, \forall i$
5. ✅ **总层数约束**: $\sum L_i \leq n$
6. ✅ **每层单一SKU约束**: $x_i \leq 9 \times L_i$

## 运行测试

```bash
# 运行单元测试
go test -v

# 运行特定测试
go test -v -run TestCKPickingOptimizer

# 运行示例程序
go run main.go

# 使用真实库存数据运行测试
go run test_with_real_data.go ck_picking_optimizer.go

# 或使用测试脚本
./run_test.sh
```

### 真实数据测试

项目包含一个基于真实库存数据的测试脚本 `test_with_real_data.go`，它会：

1. 从 `ck 库存.csv` 文件加载SKU库存信息
2. 运行多个测试场景：
   - 场景1: 目标分拣总量 = 总库存的80%
   - 场景2: 目标分拣总量 = 总库存的50%
   - 场景3: 目标分拣总量 = 总库存的30%
   - 场景4: 固定目标分拣总量 = 200
   - 场景5: 小容量车辆测试
3. 显示详细的优化结果和统计信息

CSV文件格式：
```csv
commodity_id,qty
82,142
95,202
...
```

## 算法特点

1. **多约束平衡**: 同时考虑车辆容量、仓库库存、单SKU上限、货架层数等多重约束
2. **比例平衡优化**: 通过改善得分机制，优先调整能最大程度改善比例偏差的SKU
3. **分层优化策略**: 先满足目标总量，再优化比例平衡，最后提高利用率
4. **货架资源管理**: 智能分配货架层数，最大化空间利用
5. **全SKU包含**: 确保每次分拣都包含所有SKU

## 注意事项

1. **最小分拣总量**: 由于全SKU包含约束，最小分拣总量为SKU种类数 $I$
2. **单SKU上限**: 当 $p \times M$ 较小时，可能无法达到目标总量
3. **整数约束**: 分拣数量必须为整数，可能导致无法完全达到理想比例
4. **计算复杂度**: 当SKU种类较多时，优化计算量较大

## 扩展建议

1. **动态调整单SKU上限**: 根据仓库SKU比例动态调整
2. **多车辆协同**: 当单辆车无法满足目标总量时，考虑多辆车协同
3. **分拣成本考虑**: 在优化目标中加入分拣成本因素

## 参考文档

详细数学建模请参考 `ck 分拣数学建模.md`

