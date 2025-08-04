package main

import (
	"fmt"
	"math"
	"regexp"
	"sort"
	"strconv"
	"strings"
)

// StringSimilarity 字符串相似度比较器
type StringSimilarity struct{}

// NewStringSimilarity 创建新的字符串相似度比较器
func NewStringSimilarity() *StringSimilarity {
	return &StringSimilarity{}
}

// LevenshteinDistance 计算编辑距离（Levenshtein距离）
func (ss *StringSimilarity) LevenshteinDistance(s1, s2 string) int {
	if len(s1) < len(s2) {
		return ss.LevenshteinDistance(s2, s1)
	}

	if len(s2) == 0 {
		return len(s1)
	}

	previousRow := make([]int, len(s2)+1)
	for i := range previousRow {
		previousRow[i] = i
	}

	for i, c1 := range s1 {
		currentRow := []int{i + 1}
		for j, c2 := range s2 {
			insertions := previousRow[j+1] + 1
			deletions := currentRow[j] + 1
			substitutions := previousRow[j]
			if c1 != c2 {
				substitutions++
			}
			currentRow = append(currentRow, minOfThree(insertions, deletions, substitutions))
		}
		previousRow = currentRow
	}

	return previousRow[len(previousRow)-1]
}

// LevenshteinSimilarity 基于编辑距离计算相似度
func (ss *StringSimilarity) LevenshteinSimilarity(s1, s2 string) float64 {
	maxLen := max(len(s1), len(s2))
	if maxLen == 0 {
		return 1.0
	}

	distance := ss.LevenshteinDistance(s1, s2)
	return 1.0 - float64(distance)/float64(maxLen)
}

// JaccardSimilarity 计算Jaccard相似度（基于字符集合）
func (ss *StringSimilarity) JaccardSimilarity(s1, s2 string) float64 {
	set1 := make(map[rune]bool)
	set2 := make(map[rune]bool)

	for _, char := range s1 {
		set1[char] = true
	}
	for _, char := range s2 {
		set2[char] = true
	}

	intersection := 0
	union := make(map[rune]bool)

	for char := range set1 {
		union[char] = true
		if set2[char] {
			intersection++
		}
	}
	for char := range set2 {
		union[char] = true
	}

	if len(union) == 0 {
		return 1.0
	}

	return float64(intersection) / float64(len(union))
}

// CosineSimilarity 计算余弦相似度（基于字符频率）
func (ss *StringSimilarity) CosineSimilarity(s1, s2 string) float64 {
	counter1 := make(map[rune]int)
	counter2 := make(map[rune]int)

	for _, char := range s1 {
		counter1[char]++
	}
	for _, char := range s2 {
		counter2[char]++
	}

	// 获取所有字符
	allChars := make(map[rune]bool)
	for char := range counter1 {
		allChars[char] = true
	}
	for char := range counter2 {
		allChars[char] = true
	}

	// 计算点积和模长
	dotProduct := 0.0
	norm1 := 0.0
	norm2 := 0.0

	for char := range allChars {
		count1 := float64(counter1[char])
		count2 := float64(counter2[char])

		dotProduct += count1 * count2
		norm1 += count1 * count1
		norm2 += count2 * count2
	}

	norm1 = math.Sqrt(norm1)
	norm2 = math.Sqrt(norm2)

	if norm1 == 0 || norm2 == 0 {
		return 0.0
	}

	return dotProduct / (norm1 * norm2)
}

// SequenceMatcherSimilarity 使用最长公共子序列计算相似度
func (ss *StringSimilarity) SequenceMatcherSimilarity(s1, s2 string) float64 {
	// 简化版的序列匹配器，使用最长公共子序列
	lcs := ss.longestCommonSubsequence(s1, s2)
	maxLen := max(len(s1), len(s2))
	if maxLen == 0 {
		return 1.0
	}
	return float64(lcs) / float64(maxLen)
}

// longestCommonSubsequence 计算最长公共子序列长度
func (ss *StringSimilarity) longestCommonSubsequence(s1, s2 string) int {
	m, n := len(s1), len(s2)
	dp := make([][]int, m+1)
	for i := range dp {
		dp[i] = make([]int, n+1)
	}

	for i := 1; i <= m; i++ {
		for j := 1; j <= n; j++ {
			if s1[i-1] == s2[j-1] {
				dp[i][j] = dp[i-1][j-1] + 1
			} else {
				dp[i][j] = max(dp[i-1][j], dp[i][j-1])
			}
		}
	}

	return dp[m][n]
}

// NumberPatternSimilarity 基于数字模式的相似度（专门针对类似"27_64_147_95"的格式）
func (ss *StringSimilarity) NumberPatternSimilarity(s1, s2 string) float64 {
	re := regexp.MustCompile(`\d+`)
	nums1Str := re.FindAllString(s1, -1)
	nums2Str := re.FindAllString(s2, -1)

	if len(nums1Str) == 0 || len(nums2Str) == 0 {
		return 0.0
	}

	nums1 := make([]int, len(nums1Str))
	nums2 := make([]int, len(nums2Str))

	for i, numStr := range nums1Str {
		num, err := strconv.Atoi(numStr)
		if err != nil {
			return 0.0
		}
		nums1[i] = num
	}

	for i, numStr := range nums2Str {
		num, err := strconv.Atoi(numStr)
		if err != nil {
			return 0.0
		}
		nums2[i] = num
	}

	maxLen := max(len(nums1), len(nums2))
	minLen := min(len(nums1), len(nums2))

	// 长度相似度
	lengthSimilarity := float64(minLen) / float64(maxLen)

	// 数字匹配度
	matches := 0
	for i := 0; i < minLen; i++ {
		if nums1[i] == nums2[i] {
			matches++
		}
	}
	positionSimilarity := float64(matches) / float64(maxLen)

	// 数字集合相似度
	set1 := make(map[int]bool)
	set2 := make(map[int]bool)
	for _, num := range nums1 {
		set1[num] = true
	}
	for _, num := range nums2 {
		set2[num] = true
	}

	intersection := 0
	union := make(map[int]bool)
	for num := range set1 {
		union[num] = true
		if set2[num] {
			intersection++
		}
	}
	for num := range set2 {
		union[num] = true
	}

	setSimilarity := 0.0
	if len(union) > 0 {
		setSimilarity = float64(intersection) / float64(len(union))
	}

	// 综合相似度
	return 0.4*positionSimilarity + 0.3*lengthSimilarity + 0.3*setSimilarity
}

// PrefixSimilarity 计算前缀相似度（开头部分越接近越好）
func (ss *StringSimilarity) PrefixSimilarity(s1, s2, separator string) float64 {
	parts1 := strings.Split(s1, separator)
	parts2 := strings.Split(s2, separator)

	if len(parts1) == 0 || len(parts2) == 0 {
		return 0.0
	}

	maxLen := max(len(parts1), len(parts2))
	minLen := min(len(parts1), len(parts2))

	// 计算从开头开始连续匹配的部分数量
	consecutiveMatches := 0
	for i := 0; i < minLen; i++ {
		if parts1[i] == parts2[i] {
			consecutiveMatches++
		} else {
			break
		}
	}

	// 前缀匹配得分（连续匹配的权重更高）
	if consecutiveMatches == 0 {
		return 0.0
	}

	// 使用指数权重，开头匹配更重要
	prefixScore := float64(consecutiveMatches) / float64(maxLen)
	// 给连续匹配额外加权
	bonus := math.Pow(float64(consecutiveMatches)/float64(minLen), 0.5)
	prefixScore = math.Min(1.0, prefixScore*(1+bonus))

	return prefixScore
}

// ComprehensiveSimilarity 综合相似度计算（多种算法加权平均，重视前缀匹配）
func (ss *StringSimilarity) ComprehensiveSimilarity(s1, s2 string) float64 {
	levenshteinSim := ss.LevenshteinSimilarity(s1, s2)
	jaccardSim := ss.JaccardSimilarity(s1, s2)
	cosineSim := ss.CosineSimilarity(s1, s2)
	sequenceSim := ss.SequenceMatcherSimilarity(s1, s2)
	numberSim := ss.NumberPatternSimilarity(s1, s2)
	prefixSim := ss.PrefixSimilarity(s1, s2, "_")

	// 调整权重分配，重视前缀匹配
	weights := map[string]float64{
		"prefix":         0.40, // 前缀匹配权重最高
		"levenshtein":    0.20, // 编辑距离
		"sequence":       0.15, // 序列匹配
		"number_pattern": 0.15, // 数字模式
		"jaccard":        0.05, // 字符集合
		"cosine":         0.05, // 字符频率
	}

	comprehensiveSim := weights["prefix"]*prefixSim +
		weights["levenshtein"]*levenshteinSim +
		weights["jaccard"]*jaccardSim +
		weights["cosine"]*cosineSim +
		weights["sequence"]*sequenceSim +
		weights["number_pattern"]*numberSim

	return comprehensiveSim
}

// SimilarityResult 相似度结果结构体
type SimilarityResult struct {
	Candidate  string
	Similarity float64
}

// RankSimilarities 对候选字符串按相似度排序
func (ss *StringSimilarity) RankSimilarities(target string, candidates []string, method string) []SimilarityResult {
	results := make([]SimilarityResult, 0, len(candidates))

	for _, candidate := range candidates {
		var sim float64
		switch method {
		case "comprehensive":
			sim = ss.ComprehensiveSimilarity(target, candidate)
		case "prefix":
			sim = ss.PrefixSimilarity(target, candidate, "_")
		case "levenshtein":
			sim = ss.LevenshteinSimilarity(target, candidate)
		case "jaccard":
			sim = ss.JaccardSimilarity(target, candidate)
		case "cosine":
			sim = ss.CosineSimilarity(target, candidate)
		case "sequence_matcher":
			sim = ss.SequenceMatcherSimilarity(target, candidate)
		case "number_pattern":
			sim = ss.NumberPatternSimilarity(target, candidate)
		default:
			sim = ss.ComprehensiveSimilarity(target, candidate)
		}

		results = append(results, SimilarityResult{
			Candidate:  candidate,
			Similarity: sim,
		})
	}

	// 按相似度降序排序
	sort.Slice(results, func(i, j int) bool {
		return results[i].Similarity > results[j].Similarity
	})

	return results
}

// AllSimilarities 所有相似度类型的结果
type AllSimilarities struct {
	Prefix          float64
	Levenshtein     float64
	Jaccard         float64
	Cosine          float64
	SequenceMatcher float64
	NumberPattern   float64
	Comprehensive   float64
}

// CalculateAllSimilarities 计算所有类型的相似度
func (ss *StringSimilarity) CalculateAllSimilarities(s1, s2 string) AllSimilarities {
	return AllSimilarities{
		Prefix:          ss.PrefixSimilarity(s1, s2, "_"),
		Levenshtein:     ss.LevenshteinSimilarity(s1, s2),
		Jaccard:         ss.JaccardSimilarity(s1, s2),
		Cosine:          ss.CosineSimilarity(s1, s2),
		SequenceMatcher: ss.SequenceMatcherSimilarity(s1, s2),
		NumberPattern:   ss.NumberPatternSimilarity(s1, s2),
		Comprehensive:   ss.ComprehensiveSimilarity(s1, s2),
	}
}

// 辅助函数
func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

func minOfThree(a, b, c int) int {
	if a <= b && a <= c {
		return a
	}
	if b <= c {
		return b
	}
	return c
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}

// removeDuplicates 去重字符串切片
func removeDuplicates(slice []string) []string {
	keys := make(map[string]bool)
	result := []string{}

	for _, item := range slice {
		if !keys[item] {
			keys[item] = true
			result = append(result, item)
		}
	}

	return result
}

func demonstrateStringSimilarity() {
	// 创建相似度比较器
	similarityCalculator := NewStringSimilarity()

	// 目标字符串
	target := "23_67_41_89_15"

	// 候选字符串列表（用户新提供的列表）
	candidates := []string{
		"23_67_41_15_89",
		"23_67_89_41_15",
		"23_67_89_15_41",
		"23_67_15_41_89",
		"23_67_15_89_41",
		"23_41_67_89_15",
		"23_41_67_15_89",
		"23_41_89_67_15",
		"23_41_89_15_67",
		"23_41_15_67_89",
		"23_41_15_89_67",
		"23_89_67_41_15",
		"23_89_67_15_41",
		"23_89_41_67_15",
		"23_89_41_15_67",
		"23_89_15_67_41",
		"23_89_15_41_67",
		"23_15_67_41_89",
		"23_15_67_89_41",
		"23_15_41_67_89",
		"23_15_41_89_67",
		"23_15_89_67_41",
		"23_15_89_41_67",
		"67_23_41_89_15",
		"67_23_41_15_89",
		"67_23_89_41_15",
		"67_23_89_15_41",
		"67_23_15_41_89",
		"67_23_15_89_41",
		"67_41_23_89_15",
		"67_41_23_15_89",
		"67_41_89_23_15",
		"67_41_89_15_23",
		"67_41_15_23_89",
		"67_41_15_89_23",
		"67_89_23_41_15",
		"67_89_23_15_41",
		"67_89_41_23_15",
		"67_89_41_15_23",
		"67_89_15_23_41",
		"67_89_15_41_23",
		"67_15_23_41_89",
		"67_15_23_89_41",
		"67_15_41_23_89",
		"67_15_41_89_23",
		"67_15_89_23_41",
		"67_15_89_41_23",
		"41_23_67_89_15",
		"41_23_67_15_89",
		"41_23_89_67_15",
		"41_23_89_15_67",
		"41_23_15_67_89",
		"41_23_15_89_67",
		"41_67_23_89_15",
		"41_67_23_15_89",
		"41_67_89_23_15",
		"41_67_89_15_23",
		"41_67_15_23_89",
		"41_67_15_89_23",
		"41_89_23_67_15",
		"41_89_23_15_67",
		"41_89_67_23_15",
		"41_89_67_15_23",
		"41_89_15_23_67",
		"41_89_15_67_23",
		"41_15_23_67_89",
		"41_15_23_89_67",
		"41_15_67_23_89",
		"41_15_67_89_23",
		"41_15_89_23_67",
		"41_15_89_67_23",
		"89_23_67_41_15",
		"89_23_67_15_41",
		"89_23_41_67_15",
		"89_23_41_15_67",
		"89_23_15_67_41",
		"89_23_15_41_67",
		"89_67_23_41_15",
		"89_67_23_15_41",
		"89_67_41_23_15",
		"89_67_41_15_23",
		"89_67_15_23_41",
		"89_67_15_41_23",
		"89_41_23_67_15",
		"89_41_23_15_67",
		"89_41_67_23_15",
		"89_41_67_15_23",
		"89_41_15_23_67",
		"89_41_15_67_23",
		"89_15_23_67_41",
		"89_15_23_41_67",
		"89_15_67_23_41",
		"89_15_67_41_23",
		"89_15_41_23_67",
		"89_15_41_67_23",
		"15_23_67_41_89",
		"15_23_67_89_41",
		"15_23_41_67_89",
		"15_23_41_89_67",
		"15_23_89_67_41",
		"15_23_89_41_67",
		"15_67_23_41_89",
		"15_67_23_89_41",
		"15_67_41_23_89",
		"15_67_41_89_23",
		"15_67_89_23_41",
		"15_67_89_41_23",
		"15_41_23_67_89",
		"15_41_23_89_67",
		"15_41_67_23_89",
		"15_41_67_89_23",
		"15_41_89_23_67",
		"15_41_89_67_23",
		"15_89_23_67_41",
		"15_89_23_41_67",
		"15_89_67_23_41",
		"15_89_67_41_23",
		"15_89_41_23_67",
		"15_89_41_67_23",
	}

	fmt.Println("=== 字符串相似度比较 ===")
	fmt.Printf("目标字符串: %s\n", target)
	fmt.Printf("候选字符串数量: %d\n", len(candidates))
	fmt.Println()

	// 去重候选字符串
	uniqueCandidates := removeDuplicates(candidates)
	fmt.Printf("去重后候选字符串数量: %d\n", len(uniqueCandidates))
	fmt.Println("候选字符串列表:")
	for i, candidate := range uniqueCandidates {
		fmt.Printf("  %2d. %s\n", i+1, candidate)
	}
	fmt.Println()

	// 使用不同方法计算相似度并排序
	methods := []string{"comprehensive", "prefix", "levenshtein", "sequence_matcher"}

	for _, method := range methods {
		fmt.Printf("=== %s 方法排序结果 ===\n", strings.ToUpper(method))
		rankedResults := similarityCalculator.RankSimilarities(target, uniqueCandidates, method)

		for i, result := range rankedResults {
			fmt.Printf("%2d. %-20s - 相似度: %.4f\n", i+1, result.Candidate, result.Similarity)
		}
		fmt.Println()
	}

	// 详细分析最相似的字符串
	fmt.Println("=== 详细相似度分析 ===")
	bestMatch := similarityCalculator.RankSimilarities(target, uniqueCandidates, "comprehensive")[0].Candidate
	fmt.Printf("综合评分最高的字符串: %s\n", bestMatch)

	allSimilarities := similarityCalculator.CalculateAllSimilarities(target, bestMatch)
	fmt.Printf("与目标字符串 '%s' 的各种相似度:\n", target)
	fmt.Printf("  %-15s: %.4f\n", "prefix", allSimilarities.Prefix)
	fmt.Printf("  %-15s: %.4f\n", "levenshtein", allSimilarities.Levenshtein)
	fmt.Printf("  %-15s: %.4f\n", "jaccard", allSimilarities.Jaccard)
	fmt.Printf("  %-15s: %.4f\n", "cosine", allSimilarities.Cosine)
	fmt.Printf("  %-15s: %.4f\n", "sequence_matcher", allSimilarities.SequenceMatcher)
	fmt.Printf("  %-15s: %.4f\n", "number_pattern", allSimilarities.NumberPattern)
	fmt.Printf("  %-15s: %.4f\n", "comprehensive", allSimilarities.Comprehensive)

	// 前缀匹配专项分析
	fmt.Println("\n=== 前缀匹配专项分析 ===")
	prefixRanked := similarityCalculator.RankSimilarities(target, uniqueCandidates, "prefix")
	fmt.Printf("前缀匹配最高的字符串: %s (相似度: %.4f)\n", prefixRanked[0].Candidate, prefixRanked[0].Similarity)

	targetParts := strings.Split(target, "_")
	fmt.Printf("目标字符串各部分: %v\n", targetParts)
	fmt.Println("\n前缀匹配详细分析:")

	for _, result := range prefixRanked[:5] { // 显示前5名
		candidateParts := strings.Split(result.Candidate, "_")
		consecutiveMatches := 0
		for j := 0; j < min(len(targetParts), len(candidateParts)); j++ {
			if targetParts[j] == candidateParts[j] {
				consecutiveMatches++
			} else {
				break
			}
		}

		var matchInfo string
		if consecutiveMatches > 0 {
			matchInfo = fmt.Sprintf("前%d段匹配", consecutiveMatches)
		} else {
			matchInfo = "无前缀匹配"
		}
		fmt.Printf("  %-20s - %s - 前缀相似度: %.4f\n", result.Candidate, matchInfo, result.Similarity)
		fmt.Printf("    候选字符串各部分: %v\n", candidateParts)
	}

	// 分析数字组成相同的字符串
	fmt.Println("\n=== 数字组成分析 ===")
	targetNumbers := make(map[string]bool)
	for _, part := range strings.Split(target, "_") {
		targetNumbers[part] = true
	}

	var targetNumbersSlice []string
	for num := range targetNumbers {
		targetNumbersSlice = append(targetNumbersSlice, num)
	}
	sort.Strings(targetNumbersSlice)
	fmt.Printf("目标字符串包含的数字: %v\n", targetNumbersSlice)

	var sameNumbers []string
	for _, candidate := range uniqueCandidates {
		candidateNumbers := make(map[string]bool)
		for _, part := range strings.Split(candidate, "_") {
			candidateNumbers[part] = true
		}

		// 检查数字集合是否相同
		if len(candidateNumbers) == len(targetNumbers) {
			same := true
			for num := range candidateNumbers {
				if !targetNumbers[num] {
					same = false
					break
				}
			}
			if same {
				sameNumbers = append(sameNumbers, candidate)
			}
		}
	}

	if len(sameNumbers) > 0 {
		fmt.Printf("包含相同数字组合的字符串数量: %d\n", len(sameNumbers))
		fmt.Println("按综合相似度排序 (重视前缀匹配):")
		comprehensiveRanked := similarityCalculator.RankSimilarities(target, sameNumbers, "comprehensive")
		for i, result := range comprehensiveRanked {
			prefixSim := similarityCalculator.PrefixSimilarity(target, result.Candidate, "_")
			fmt.Printf("  %2d. %-20s - 综合: %.4f, 前缀: %.4f\n", i+1, result.Candidate, result.Similarity, prefixSim)
		}
	} else {
		fmt.Println("没有找到包含完全相同数字组合的字符串")
	}
}

// 如果直接运行此文件，则执行演示
func init() {
	// 这个文件可以作为库使用，也可以直接运行演示
}

// 为了能够独立编译运行，添加一个main函数
// 当直接运行 go run string_similarity.go 时会执行
func runDemo() {
	demonstrateStringSimilarity()
}

// main 函数，程序入口
func main() {
	demonstrateStringSimilarity()
}
