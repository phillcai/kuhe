# 字符串相似度比较器 (Golang 版本)

这是一个用 Golang 实现的字符串相似度比较器，使用 **COMPREHENSIVE** 方法进行字符串相似度计算。

## 功能特性

### 相似度算法

1. **编辑距离 (Levenshtein Distance)** - 计算两个字符串之间的最小编辑操作数
2. **Jaccard 相似度** - 基于字符集合的相似度计算
3. **余弦相似度** - 基于字符频率向量的相似度计算
4. **序列匹配器相似度** - 使用最长公共子序列算法
5. **数字模式相似度** - 专门针对数字序列格式（如 "23_67_41_89_15"）
6. **前缀相似度** - 重视开头部分匹配的相似度算法
7. **综合相似度** - 多种算法的加权平均，重视前缀匹配

### 权重配置 (COMPREHENSIVE 方法)

```go
weights := map[string]float64{
    "prefix":         0.40, // 前缀匹配权重最高
    "levenshtein":    0.20, // 编辑距离
    "sequence":       0.15, // 序列匹配
    "number_pattern": 0.15, // 数字模式
    "jaccard":        0.05, // 字符集合
    "cosine":         0.05, // 字符频率
}
```

## 使用方法

### 1. 基本使用

```go
// 创建相似度比较器
similarityCalculator := NewStringSimilarity()

// 计算两个字符串的综合相似度
target := "23_67_41_89_15"
candidate := "23_67_41_15_89"
similarity := similarityCalculator.ComprehensiveSimilarity(target, candidate)
fmt.Printf("相似度: %.4f\n", similarity)
```

### 2. 批量排序

```go
// 对候选字符串按相似度排序
candidates := []string{
    "23_67_41_15_89",
    "23_67_89_41_15",
    "67_23_41_89_15",
    // ... 更多候选字符串
}

results := similarityCalculator.RankSimilarities(target, candidates, "comprehensive")
for i, result := range results {
    fmt.Printf("%d. %s - 相似度: %.4f\n", i+1, result.Candidate, result.Similarity)
}
```

### 3. 计算所有类型的相似度

```go
allSimilarities := similarityCalculator.CalculateAllSimilarities(target, candidate)
fmt.Printf("前缀相似度: %.4f\n", allSimilarities.Prefix)
fmt.Printf("编辑距离相似度: %.4f\n", allSimilarities.Levenshtein)
fmt.Printf("综合相似度: %.4f\n", allSimilarities.Comprehensive)
```

## 运行演示

要运行完整的演示程序，可以在 `string_similarity.go` 文件中调用 `demonstrateStringSimilarity()` 函数：

```go
func main() {
    demonstrateStringSimilarity()
}
```

或者在现有的 main 函数中添加调用：

```go
// 在现有的 main.go 中添加
demonstrateStringSimilarity()
```

## 演示结果

演示程序会输出：

1. **基本信息** - 目标字符串和候选字符串数量
2. **多种方法排序结果** - comprehensive, prefix, levenshtein, sequence_matcher
3. **详细相似度分析** - 最佳匹配的各种相似度分数
4. **前缀匹配专项分析** - 前缀匹配的详细信息
5. **数字组成分析** - 包含相同数字组合的字符串分析

## 适用场景

- 路径序列相似度比较
- 数字编码相似度匹配
- 字符串模糊匹配
- 前缀优先的相似度排序

## 性能特点

- 时间复杂度：O(n*m) 其中 n,m 是字符串长度
- 空间复杂度：O(n*m) 用于动态规划表
- 适合中小规模字符串比较（长度 < 1000） 