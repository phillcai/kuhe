package main

import (
	"math"
	"sort"
)

// 聚类工具类 - 实现层次聚类算法
type ClusteringUtils struct {
	TimeMatrix [][]float64    // 行驶时间矩阵
	Points     []VehiclePoint // 点位信息
}

// 聚类结果
type Cluster struct {
	Points        []string // 聚类中的点位ID
	Center        string   // 聚类中心点位ID
	AvgTime       float64  // 聚类内平均行驶时间
	ShortageCount int      // 缺货点位数量
}

// 距离度量结构
type DistancePair struct {
	Point1   string
	Point2   string
	Distance float64
}

// 构造函数
func NewClusteringUtils(timeMatrix [][]float64, points []VehiclePoint) *ClusteringUtils {
	return &ClusteringUtils{
		TimeMatrix: timeMatrix,
		Points:     points,
	}
}

// 层次聚类算法（凝聚聚类）
func (c *ClusteringUtils) AgglomerativeClustering(pointIDs []string, maxClusters int, distanceThreshold float64) []Cluster {
	if len(pointIDs) <= maxClusters {
		// 如果点位数量不多，直接每个点位一个聚类
		return c.createIndividualClusters(pointIDs)
	}

	// 初始化：每个点位作为一个聚类
	clusters := make([][]string, len(pointIDs))
	for i, pointID := range pointIDs {
		clusters[i] = []string{pointID}
	}

	// 计算所有点位对的距离
	distances := c.calculateAllDistances(pointIDs)

	// 排序距离
	sort.Slice(distances, func(i, j int) bool {
		return distances[i].Distance < distances[j].Distance
	})

	// 执行凝聚聚类
	for len(clusters) > maxClusters && len(distances) > 0 {
		// 找到最小距离的两个聚类
		minDistance := distances[0]

		// 检查距离阈值
		if minDistance.Distance > distanceThreshold {
			break
		}

		// 找到对应的聚类索引
		cluster1Idx := c.findClusterIndex(clusters, minDistance.Point1)
		cluster2Idx := c.findClusterIndex(clusters, minDistance.Point2)

		if cluster1Idx != -1 && cluster2Idx != -1 && cluster1Idx != cluster2Idx {
			// 合并聚类
			mergedCluster := append(clusters[cluster1Idx], clusters[cluster2Idx]...)

			// 移除原聚类，添加合并后的聚类
			newClusters := make([][]string, 0)
			for i, cluster := range clusters {
				if i != cluster1Idx && i != cluster2Idx {
					newClusters = append(newClusters, cluster)
				}
			}
			newClusters = append(newClusters, mergedCluster)
			clusters = newClusters

			// 重新计算距离矩阵（简化实现）
			allPoints := make([]string, 0)
			for _, cluster := range clusters {
				allPoints = append(allPoints, cluster...)
			}
			distances = c.calculateAllDistances(allPoints)
			sort.Slice(distances, func(i, j int) bool {
				return distances[i].Distance < distances[j].Distance
			})
		} else {
			// 移除无效的距离对
			distances = distances[1:]
		}
	}

	// 转换为Cluster结构
	return c.convertToClusters(clusters)
}

// K-means聚类算法（基于时间距离）
func (c *ClusteringUtils) KMeansClustering(pointIDs []string, k int, maxIterations int) []Cluster {
	if len(pointIDs) <= k {
		return c.createIndividualClusters(pointIDs)
	}

	// 初始化聚类中心（随机选择k个点）
	centers := make([]string, k)
	for i := 0; i < k; i++ {
		centers[i] = pointIDs[i*len(pointIDs)/k]
	}

	clusters := make([][]string, k)

	for iter := 0; iter < maxIterations; iter++ {
		// 清空聚类
		for i := range clusters {
			clusters[i] = make([]string, 0)
		}

		// 将每个点分配到最近的聚类中心
		for _, pointID := range pointIDs {
			minDistance := math.MaxFloat64
			bestCluster := 0

			for i, center := range centers {
				distance := c.getDistance(pointID, center)
				if distance < minDistance {
					minDistance = distance
					bestCluster = i
				}
			}

			clusters[bestCluster] = append(clusters[bestCluster], pointID)
		}

		// 更新聚类中心
		converged := true
		for i, cluster := range clusters {
			if len(cluster) > 0 {
				newCenter := c.findClusterCenter(cluster)
				if newCenter != centers[i] {
					centers[i] = newCenter
					converged = false
				}
			}
		}

		if converged {
			break
		}
	}

	return c.convertToClusters(clusters)
}

// 加权聚类（对缺货点位给予更高权重）
func (c *ClusteringUtils) WeightedClustering(pointIDs []string, k int, shortageWeight float64) []Cluster {
	// 计算加权距离矩阵
	weightedMatrix := c.calculateWeightedDistanceMatrix(pointIDs, shortageWeight)

	// 使用加权距离进行K-means聚类
	return c.kMeansWithWeightedMatrix(pointIDs, k, weightedMatrix, 100)
}

// 辅助函数

// 计算所有点位对的距离
func (c *ClusteringUtils) calculateAllDistances(pointIDs []string) []DistancePair {
	distances := make([]DistancePair, 0)

	for i := 0; i < len(pointIDs); i++ {
		for j := i + 1; j < len(pointIDs); j++ {
			distance := c.getDistance(pointIDs[i], pointIDs[j])
			distances = append(distances, DistancePair{
				Point1:   pointIDs[i],
				Point2:   pointIDs[j],
				Distance: distance,
			})
		}
	}

	return distances
}

// 获取两个点位间的距离
func (c *ClusteringUtils) getDistance(point1ID, point2ID string) float64 {
	idx1 := c.getPointIndex(point1ID)
	idx2 := c.getPointIndex(point2ID)

	if idx1 == -1 || idx2 == -1 {
		return math.MaxFloat64
	}

	return c.TimeMatrix[idx1][idx2]
}

// 获取点位索引
func (c *ClusteringUtils) getPointIndex(pointID string) int {
	for i, point := range c.Points {
		if point.ID == pointID {
			return i
		}
	}
	return -1
}

// 找到包含指定点位的聚类索引
func (c *ClusteringUtils) findClusterIndex(clusters [][]string, pointID string) int {
	for i, cluster := range clusters {
		for _, p := range cluster {
			if p == pointID {
				return i
			}
		}
	}
	return -1
}

// 找到聚类的中心点（距离其他点总距离最小的点）
func (c *ClusteringUtils) findClusterCenter(cluster []string) string {
	if len(cluster) == 0 {
		return ""
	}

	if len(cluster) == 1 {
		return cluster[0]
	}

	minTotalDistance := math.MaxFloat64
	centerPoint := cluster[0]

	for _, candidateCenter := range cluster {
		totalDistance := 0.0
		for _, point := range cluster {
			if point != candidateCenter {
				totalDistance += c.getDistance(candidateCenter, point)
			}
		}

		if totalDistance < minTotalDistance {
			minTotalDistance = totalDistance
			centerPoint = candidateCenter
		}
	}

	return centerPoint
}

// 创建独立聚类（每个点位一个聚类）
func (c *ClusteringUtils) createIndividualClusters(pointIDs []string) []Cluster {
	clusters := make([]Cluster, len(pointIDs))

	for i, pointID := range pointIDs {
		shortageCount := 0
		if c.isShortagePoint(pointID) {
			shortageCount = 1
		}

		clusters[i] = Cluster{
			Points:        []string{pointID},
			Center:        pointID,
			AvgTime:       0,
			ShortageCount: shortageCount,
		}
	}

	return clusters
}

// 检查是否为缺货点位
func (c *ClusteringUtils) isShortagePoint(pointID string) bool {
	for _, point := range c.Points {
		if point.ID == pointID {
			return point.IsShortage
		}
	}
	return false
}

// 转换为Cluster结构
func (c *ClusteringUtils) convertToClusters(clusters [][]string) []Cluster {
	result := make([]Cluster, len(clusters))

	for i, cluster := range clusters {
		if len(cluster) == 0 {
			continue
		}

		center := c.findClusterCenter(cluster)
		avgTime := c.calculateClusterAvgTime(cluster)
		shortageCount := c.countShortagePoints(cluster)

		result[i] = Cluster{
			Points:        cluster,
			Center:        center,
			AvgTime:       avgTime,
			ShortageCount: shortageCount,
		}
	}

	return result
}

// 计算聚类内平均行驶时间
func (c *ClusteringUtils) calculateClusterAvgTime(cluster []string) float64 {
	if len(cluster) <= 1 {
		return 0
	}

	totalTime := 0.0
	count := 0

	for i := 0; i < len(cluster); i++ {
		for j := i + 1; j < len(cluster); j++ {
			totalTime += c.getDistance(cluster[i], cluster[j])
			count++
		}
	}

	if count == 0 {
		return 0
	}

	return totalTime / float64(count)
}

// 统计聚类中缺货点位数量
func (c *ClusteringUtils) countShortagePoints(cluster []string) int {
	count := 0
	for _, pointID := range cluster {
		if c.isShortagePoint(pointID) {
			count++
		}
	}
	return count
}

// 计算加权距离矩阵
func (c *ClusteringUtils) calculateWeightedDistanceMatrix(pointIDs []string, shortageWeight float64) [][]float64 {
	n := len(pointIDs)
	weightedMatrix := make([][]float64, n)

	for i := 0; i < n; i++ {
		weightedMatrix[i] = make([]float64, n)
		for j := 0; j < n; j++ {
			if i == j {
				weightedMatrix[i][j] = 0
				continue
			}

			distance := c.getDistance(pointIDs[i], pointIDs[j])

			// 如果两个点都是缺货点位，降低距离（增加聚集倾向）
			if c.isShortagePoint(pointIDs[i]) && c.isShortagePoint(pointIDs[j]) {
				distance /= shortageWeight
			}

			weightedMatrix[i][j] = distance
		}
	}

	return weightedMatrix
}

// 使用加权矩阵进行K-means聚类
func (c *ClusteringUtils) kMeansWithWeightedMatrix(pointIDs []string, k int, weightedMatrix [][]float64, maxIterations int) []Cluster {
	if len(pointIDs) <= k {
		return c.createIndividualClusters(pointIDs)
	}

	// 初始化聚类中心
	centerIndices := make([]int, k)
	for i := 0; i < k; i++ {
		centerIndices[i] = i * len(pointIDs) / k
	}

	clusters := make([][]int, k)

	for iter := 0; iter < maxIterations; iter++ {
		// 清空聚类
		for i := range clusters {
			clusters[i] = make([]int, 0)
		}

		// 分配点位到最近的聚类中心
		for i, _ := range pointIDs {
			minDistance := math.MaxFloat64
			bestCluster := 0

			for j, centerIdx := range centerIndices {
				distance := weightedMatrix[i][centerIdx]
				if distance < minDistance {
					minDistance = distance
					bestCluster = j
				}
			}

			clusters[bestCluster] = append(clusters[bestCluster], i)
		}

		// 更新聚类中心
		converged := true
		for i, cluster := range clusters {
			if len(cluster) > 0 {
				newCenterIdx := c.findWeightedClusterCenter(cluster, weightedMatrix)
				if newCenterIdx != centerIndices[i] {
					centerIndices[i] = newCenterIdx
					converged = false
				}
			}
		}

		if converged {
			break
		}
	}

	// 转换结果
	result := make([]Cluster, k)
	for i, cluster := range clusters {
		pointsInCluster := make([]string, len(cluster))
		shortageCount := 0

		for j, pointIdx := range cluster {
			pointsInCluster[j] = pointIDs[pointIdx]
			if c.isShortagePoint(pointIDs[pointIdx]) {
				shortageCount++
			}
		}

		center := ""
		if len(cluster) > 0 {
			center = pointIDs[centerIndices[i]]
		}

		result[i] = Cluster{
			Points:        pointsInCluster,
			Center:        center,
			AvgTime:       c.calculateClusterAvgTime(pointsInCluster),
			ShortageCount: shortageCount,
		}
	}

	return result
}

// 找到加权聚类中心
func (c *ClusteringUtils) findWeightedClusterCenter(cluster []int, weightedMatrix [][]float64) int {
	if len(cluster) == 0 {
		return 0
	}

	if len(cluster) == 1 {
		return cluster[0]
	}

	minTotalDistance := math.MaxFloat64
	centerIdx := cluster[0]

	for _, candidateIdx := range cluster {
		totalDistance := 0.0
		for _, pointIdx := range cluster {
			if pointIdx != candidateIdx {
				totalDistance += weightedMatrix[candidateIdx][pointIdx]
			}
		}

		if totalDistance < minTotalDistance {
			minTotalDistance = totalDistance
			centerIdx = candidateIdx
		}
	}

	return centerIdx
}

// 评估聚类质量
func (c *ClusteringUtils) EvaluateClusterQuality(clusters []Cluster) map[string]float64 {
	metrics := make(map[string]float64)

	// 计算平均簇内距离
	totalIntraDistance := 0.0
	totalClusters := 0

	for _, cluster := range clusters {
		if len(cluster.Points) > 1 {
			totalIntraDistance += cluster.AvgTime
			totalClusters++
		}
	}

	if totalClusters > 0 {
		metrics["avg_intra_distance"] = totalIntraDistance / float64(totalClusters)
	}

	// 计算轮廓系数（简化版本）
	// 这里可以根据需要实现更复杂的聚类评估指标

	// 计算缺货点位集中度
	totalShortageConcentration := 0.0
	validClusters := 0

	for _, cluster := range clusters {
		if len(cluster.Points) > 0 {
			concentration := float64(cluster.ShortageCount) / float64(len(cluster.Points))
			totalShortageConcentration += concentration
			validClusters++
		}
	}

	if validClusters > 0 {
		metrics["shortage_concentration"] = totalShortageConcentration / float64(validClusters)
	}

	return metrics
}
