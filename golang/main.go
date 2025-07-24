package main

import (
	"encoding/csv"
	"fmt"
	"log"
	"math"
	"math/rand"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"
)

// TimeWindow 表示时间窗口
type TimeWindow struct {
	Start string
	End   string
}

// Point 表示一个点位
type Point struct {
	ID          int
	Longitude   float64
	Latitude    float64
	TimeWindows []TimeWindow
}

// Group 表示一个分组
type Group struct {
	ID     int
	Points []int // 点位ID列表
}

// 读取点位信息数据
func readPointsFromCSV(filePath string) (map[int]*Point, error) {
	file, err := os.Open(filePath)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	reader := csv.NewReader(file)
	records, err := reader.ReadAll()
	if err != nil {
		return nil, err
	}

	pointDict := make(map[int]*Point)

	// 跳过表头
	for i := 1; i < len(records); i++ {
		record := records[i]
		if len(record) < 4 {
			continue
		}

		id, err := strconv.Atoi(record[0])
		if err != nil {
			continue
		}

		// 过滤掉pid为998和999的点位
		if id == 998 || id == 999 {
			continue
		}

		longitude, err := strconv.ParseFloat(record[1], 64)
		if err != nil {
			continue
		}

		latitude, err := strconv.ParseFloat(record[2], 64)
		if err != nil {
			continue
		}

		startTime := record[3]
		endTime := record[4]

		if point, exists := pointDict[id]; exists {
			// 如果点位已存在，添加时间窗口
			point.TimeWindows = append(point.TimeWindows, TimeWindow{Start: startTime, End: endTime})
		} else {
			// 创建新点位
			pointDict[id] = &Point{
				ID:          id,
				Longitude:   longitude,
				Latitude:    latitude,
				TimeWindows: []TimeWindow{{Start: startTime, End: endTime}},
			}
		}
	}

	return pointDict, nil
}

// 计算主时间窗均值（分钟）
func mainTimeWindowMean(timeWindows []TimeWindow) float64 {
	if len(timeWindows) == 0 {
		return 0
	}

	var starts []float64
	for _, tw := range timeWindows {
		parts := strings.Split(tw.Start, ":")
		if len(parts) != 2 {
			continue
		}
		h, err1 := strconv.Atoi(parts[0])
		m, err2 := strconv.Atoi(parts[1])
		if err1 != nil || err2 != nil {
			continue
		}
		starts = append(starts, float64(h*60+m))
	}

	if len(starts) == 0 {
		return 0
	}

	sum := 0.0
	for _, s := range starts {
		sum += s
	}
	return sum / float64(len(starts))
}

// 计算欧几里得距离
func euclideanDistance(a, b []float64) float64 {
	if len(a) != len(b) {
		return 0
	}
	sum := 0.0
	for i := range a {
		diff := a[i] - b[i]
		sum += diff * diff
	}
	return math.Sqrt(sum)
}

// K-means聚类算法
func kmeans(features [][]float64, nClusters int, maxIterations int) []int {
	nPoints := len(features)
	if nPoints == 0 {
		return nil
	}

	// 随机初始化聚类中心
	centers := make([][]float64, nClusters)
	rand.Seed(time.Now().UnixNano())
	for i := 0; i < nClusters; i++ {
		idx := rand.Intn(nPoints)
		centers[i] = make([]float64, len(features[idx]))
		copy(centers[i], features[idx])
	}

	labels := make([]int, nPoints)

	for iter := 0; iter < maxIterations; iter++ {
		// 分配点到最近的聚类中心
		changed := false
		for i, feature := range features {
			minDist := math.Inf(1)
			bestCluster := 0
			for j, center := range centers {
				dist := euclideanDistance(feature, center)
				if dist < minDist {
					minDist = dist
					bestCluster = j
				}
			}
			if labels[i] != bestCluster {
				labels[i] = bestCluster
				changed = true
			}
		}

		if !changed {
			break
		}

		// 更新聚类中心
		for i := range centers {
			clusterPoints := make([][]float64, 0)
			for j, label := range labels {
				if label == i {
					clusterPoints = append(clusterPoints, features[j])
				}
			}
			if len(clusterPoints) > 0 {
				newCenter := make([]float64, len(features[0]))
				for _, point := range clusterPoints {
					for k, val := range point {
						newCenter[k] += val
					}
				}
				for k := range newCenter {
					newCenter[k] /= float64(len(clusterPoints))
				}
				centers[i] = newCenter
			}
		}
	}

	return labels
}

// 数量均衡调整
func balanceGroupSize(groups map[int][]int, features map[int][]float64, targetSize int) map[int][]int {
	changed := true
	for changed {
		changed = false

		// 找出最大和最小的组
		var maxG, minG int
		maxSize := -1
		minSize := math.MaxInt32
		for g, pids := range groups {
			size := len(pids)
			if size > maxSize {
				maxSize = size
				maxG = g
			}
			if size < minSize {
				minSize = size
				minG = g
			}
		}

		if maxSize-minSize <= 1 {
			break
		}

		// 计算最大组质心
		var maxCenter []float64
		if len(groups[maxG]) > 0 {
			maxCenter = make([]float64, len(features[groups[maxG][0]]))
			for _, pid := range groups[maxG] {
				feature := features[pid]
				for i, val := range feature {
					maxCenter[i] += val
				}
			}
			for i := range maxCenter {
				maxCenter[i] /= float64(len(groups[maxG]))
			}
		}

		// 找最大组中距离质心最远的点
		var movePid int
		maxDist := -1.0
		for _, pid := range groups[maxG] {
			dist := euclideanDistance(features[pid], maxCenter)
			if dist > maxDist {
				maxDist = dist
				movePid = pid
			}
		}

		// 移动点到最小组
		for i, pid := range groups[maxG] {
			if pid == movePid {
				groups[maxG] = append(groups[maxG][:i], groups[maxG][i+1:]...)
				break
			}
		}
		groups[minG] = append(groups[minG], movePid)
		changed = true
	}

	return groups
}

// 时间窗分散优化
func balanceTimeWindow(groups map[int][]int, pointDict map[int]*Point, features map[int][]float64, minInterval float64) map[int][]int {
	for g, pids := range groups {
		// 只筛选主时间窗均值在 9:00~21:00 的点位
		var filteredPids []int
		var filteredTimeMeans []float64
		for _, pid := range pids {
			meanTime := mainTimeWindowMean(pointDict[pid].TimeWindows)
			if meanTime >= 540 && meanTime <= 1260 {
				filteredPids = append(filteredPids, pid)
				filteredTimeMeans = append(filteredTimeMeans, meanTime)
			}
		}

		if len(filteredTimeMeans) == 0 {
			continue
		}

		sort.Float64s(filteredTimeMeans)
		interval := filteredTimeMeans[len(filteredTimeMeans)-1] - filteredTimeMeans[0]

		if interval < minInterval {
			// 找边界点
			var center []float64
			if len(filteredPids) > 0 {
				center = make([]float64, len(features[filteredPids[0]]))
				for _, pid := range filteredPids {
					feature := features[pid]
					for i, val := range feature {
						center[i] += val
					}
				}
				for i := range center {
					center[i] /= float64(len(filteredPids))
				}
			}

			// 按距离排序
			type distPoint struct {
				dist float64
				pid  int
			}
			var dists []distPoint
			for _, pid := range filteredPids {
				dist := euclideanDistance(features[pid], center)
				dists = append(dists, distPoint{dist: dist, pid: pid})
			}
			sort.Slice(dists, func(i, j int) bool {
				return dists[i].dist > dists[j].dist
			})

			// 尝试与最近组交换
			for _, dp := range dists {
				movePid := dp.pid
				moveTime := mainTimeWindowMean(pointDict[movePid].TimeWindows)

				// 找邻近组
				var neighborG int
				minDist := math.Inf(1)
				for h, hpids := range groups {
					if h == g {
						continue
					}
					if len(hpids) == 0 {
						continue
					}
					hCenter := make([]float64, len(features[hpids[0]]))
					for _, hpid := range hpids {
						feature := features[hpid]
						for i, val := range feature {
							hCenter[i] += val
						}
					}
					for i := range hCenter {
						hCenter[i] /= float64(len(hpids))
					}
					dist := euclideanDistance(features[movePid], hCenter)
					if dist < minDist {
						minDist = dist
						neighborG = h
					}
				}

				// 只考虑邻近组中主时间窗均值在 9:00~21:00 的点位
				var neighborTimes []float64
				for _, pid := range groups[neighborG] {
					meanTime := mainTimeWindowMean(pointDict[pid].TimeWindows)
					if meanTime >= 540 && meanTime <= 1260 {
						neighborTimes = append(neighborTimes, meanTime)
					}
				}

				if len(neighborTimes) == 0 {
					continue
				}

				sort.Float64s(neighborTimes)

				// 如果交换后能提升两组的时间窗分散度，则交换
				neighborMean := 0.0
				for _, t := range neighborTimes {
					neighborMean += t
				}
				neighborMean /= float64(len(neighborTimes))

				filteredMean := 0.0
				for _, t := range filteredTimeMeans {
					filteredMean += t
				}
				filteredMean /= float64(len(filteredTimeMeans))

				if math.Abs(moveTime-neighborMean) > math.Abs(moveTime-filteredMean) {
					// 从原组移除
					for i, pid := range groups[g] {
						if pid == movePid {
							groups[g] = append(groups[g][:i], groups[g][i+1:]...)
							break
						}
					}
					// 添加到邻近组
					groups[neighborG] = append(groups[neighborG], movePid)
					break
				}
			}
		}
	}

	return groups
}

// 均衡每组主时间窗点位的数量
func balanceTimeWindowCount(groups map[int][]int, pointDict map[int]*Point, features map[int][]float64, minTime, maxTime float64) map[int][]int {
	// 统计每组主时间窗点位
	groupTwPids := make(map[int][]int)
	for g, pids := range groups {
		for _, pid := range pids {
			meanTime := mainTimeWindowMean(pointDict[pid].TimeWindows)
			if meanTime >= minTime && meanTime <= maxTime {
				groupTwPids[g] = append(groupTwPids[g], pid)
			}
		}
	}

	// 计算总数和目标均衡数
	total := 0
	for _, pids := range groupTwPids {
		total += len(pids)
	}
	nGroup := len(groups)
	target := total / nGroup

	// 按需调剂
	changed := true
	for changed {
		changed = false

		// 找出最多和最少的组
		var maxG, minG int
		maxSize := -1
		minSize := math.MaxInt32
		for g, pids := range groupTwPids {
			size := len(pids)
			if size > maxSize {
				maxSize = size
				maxG = g
			}
			if size < minSize {
				minSize = size
				minG = g
			}
		}

		if maxSize-minSize <= 1 {
			break
		}
		if minSize >= target || maxSize <= target {
			break
		}

		// 从maxG移一个点到minG
		if len(groupTwPids[maxG]) == 0 {
			break
		}

		// 选择距离minG质心最近的点
		minCenter := make([]float64, len(features[groupTwPids[minG][0]]))
		for _, pid := range groups[minG] {
			feature := features[pid]
			for i, val := range feature {
				minCenter[i] += val
			}
		}
		for i := range minCenter {
			minCenter[i] /= float64(len(groups[minG]))
		}

		var movePid int
		minDist := math.Inf(1)
		for _, pid := range groupTwPids[maxG] {
			dist := euclideanDistance(features[pid], minCenter)
			if dist < minDist {
				minDist = dist
				movePid = pid
			}
		}

		// 移动点
		for i, pid := range groups[maxG] {
			if pid == movePid {
				groups[maxG] = append(groups[maxG][:i], groups[maxG][i+1:]...)
				break
			}
		}
		groups[minG] = append(groups[minG], movePid)

		// 更新groupTwPids
		for i, pid := range groupTwPids[maxG] {
			if pid == movePid {
				groupTwPids[maxG] = append(groupTwPids[maxG][:i], groupTwPids[maxG][i+1:]...)
				break
			}
		}
		groupTwPids[minG] = append(groupTwPids[minG], movePid)

		changed = true
	}

	return groups
}

// 自动检测并修正所有分组的地理离群点
func balanceOutliers(groups map[int][]int, pointDict map[int]*Point, features map[int][]float64, maxIter int, stdFactor float64) map[int][]int {
	for iter := 0; iter < maxIter; iter++ {
		moved := false
		for g, pids := range groups {
			if len(pids) <= 1 {
				continue
			}

			// 计算本组质心
			center := make([]float64, len(features[pids[0]]))
			for _, pid := range pids {
				feature := features[pid]
				for i, val := range feature {
					center[i] += val
				}
			}
			for i := range center {
				center[i] /= float64(len(pids))
			}

			// 计算每个点到质心的距离
			var dists []float64
			for _, pid := range pids {
				dist := euclideanDistance(features[pid], center)
				dists = append(dists, dist)
			}

			// 计算均值和标准差
			meanDist := 0.0
			for _, d := range dists {
				meanDist += d
			}
			meanDist /= float64(len(dists))

			variance := 0.0
			for _, d := range dists {
				variance += (d - meanDist) * (d - meanDist)
			}
			variance /= float64(len(dists))
			stdDist := math.Sqrt(variance)

			// 判定离群点
			var outlierPids []int
			for i, pid := range pids {
				if dists[i] > meanDist+stdFactor*stdDist {
					outlierPids = append(outlierPids, pid)
				}
			}

			for _, pid := range outlierPids {
				// 找到距离该点最近的其他分组
				minDist := math.Inf(1)
				var bestG int
				for h, hpids := range groups {
					if h == g {
						continue
					}
					if len(hpids) == 0 {
						continue
					}
					hCenter := make([]float64, len(features[hpids[0]]))
					for _, hpid := range hpids {
						feature := features[hpid]
						for i, val := range feature {
							hCenter[i] += val
						}
					}
					for i := range hCenter {
						hCenter[i] /= float64(len(hpids))
					}
					d := euclideanDistance(features[pid], hCenter)
					if d < minDist {
						minDist = d
						bestG = h
					}
				}

				// 移动点
				for i, p := range groups[g] {
					if p == pid {
						groups[g] = append(groups[g][:i], groups[g][i+1:]...)
						break
					}
				}
				groups[bestG] = append(groups[bestG], pid)
				moved = true
			}
		}

		if !moved {
			break
		}
	}

	return groups
}

// 计算两经纬度点之间的球面距离（单位：公里）
func haversine(lon1, lat1, lon2, lat2 float64) float64 {
	const R = 6371.0 // 地球半径（公里）

	lon1Rad := lon1 * math.Pi / 180
	lat1Rad := lat1 * math.Pi / 180
	lon2Rad := lon2 * math.Pi / 180
	lat2Rad := lat2 * math.Pi / 180

	dlon := lon2Rad - lon1Rad
	dlat := lat2Rad - lat1Rad

	a := math.Sin(dlat/2)*math.Sin(dlat/2) + math.Cos(lat1Rad)*math.Cos(lat2Rad)*math.Sin(dlon/2)*math.Sin(dlon/2)
	c := 2 * math.Atan2(math.Sqrt(a), math.Sqrt(1-a))

	return R * c
}

// 极端孤立点强制归组
func balanceExtremeIsolatedPoints(groups map[int][]int, pointDict map[int]*Point, features map[int][]float64, thresholdKm float64) map[int][]int {
	moved := true
	for moved {
		moved = false
		for g, pids := range groups {
			if len(pids) <= 1 {
				continue
			}

			// 计算本组质心
			center := make([]float64, len(features[pids[0]]))
			for _, pid := range pids {
				feature := features[pid]
				for i, val := range feature {
					center[i] += val
				}
			}
			for i := range center {
				center[i] /= float64(len(pids))
			}

			for _, pid := range pids {
				lng, lat := features[pid][0], features[pid][1]
				distToOwn := haversine(lng, lat, center[0], center[1])

				// 计算到所有组质心的距离
				minDist := distToOwn
				bestG := g
				for h, hpids := range groups {
					if h == g || len(hpids) == 0 {
						continue
					}
					hCenter := make([]float64, len(features[hpids[0]]))
					for _, hpid := range hpids {
						feature := features[hpid]
						for i, val := range feature {
							hCenter[i] += val
						}
					}
					for i := range hCenter {
						hCenter[i] /= float64(len(hpids))
					}
					d := haversine(lng, lat, hCenter[0], hCenter[1])
					if d < minDist {
						minDist = d
						bestG = h
					}
				}

				// 如果到最近组的质心距离比本组小，且本组距离大于阈值，则强制归组
				if bestG != g && distToOwn-minDist > 0 && distToOwn > thresholdKm {
					// 从原组移除
					for i, p := range groups[g] {
						if p == pid {
							groups[g] = append(groups[g][:i], groups[g][i+1:]...)
							break
						}
					}
					// 添加到最近组
					groups[bestG] = append(groups[bestG], pid)
					moved = true
				}
			}
		}
	}

	return groups
}

// 输出分组结果到CSV文件
func writeOutputToCSV(groups map[int][]int, pointDict map[int]*Point, outputPath string) error {
	file, err := os.Create(outputPath)
	if err != nil {
		return err
	}
	defer file.Close()

	writer := csv.NewWriter(file)
	defer writer.Flush()

	// 写入表头
	err = writer.Write([]string{"pid", "longitude", "latitude", "group_id"})
	if err != nil {
		return err
	}

	// 写入数据
	for groupID, pids := range groups {
		for _, pid := range pids {
			point := pointDict[pid]
			row := []string{
				strconv.Itoa(pid),
				fmt.Sprintf("%f", point.Longitude),
				fmt.Sprintf("%f", point.Latitude),
				strconv.Itoa(groupID + 1),
			}
			err = writer.Write(row)
			if err != nil {
				return err
			}
		}
	}

	return nil
}

func main() {
	// 读取点位信息数据
	csvPath := filepath.Join("..", "data", "点位信息.csv")
	pointDict, err := readPointsFromCSV(csvPath)
	if err != nil {
		log.Fatalf("读取CSV文件失败: %v", err)
	}

	// 准备聚类数据
	var pidList []int
	var geoFeatures [][]float64
	for pid, point := range pointDict {
		pidList = append(pidList, pid)
		geoFeatures = append(geoFeatures, []float64{point.Longitude, point.Latitude})
	}

	// 1. 只用经纬度做K-means聚类
	nClusters := 3
	labels := kmeans(geoFeatures, nClusters, 100)

	// 初始分组
	groups := make(map[int][]int)
	for i, label := range labels {
		pid := pidList[i]
		groups[label] = append(groups[label], pid)
	}

	// 构建pid->geo特征映射
	gidFeatures := make(map[int][]float64)
	for _, pid := range pidList {
		point := pointDict[pid]
		gidFeatures[pid] = []float64{point.Longitude, point.Latitude}
	}

	targetSize := len(pidList) / nClusters

	// 2. 数量均衡调整
	groups = balanceGroupSize(groups, gidFeatures, targetSize)

	// 3. 时间窗分散优化
	groups = balanceTimeWindow(groups, pointDict, gidFeatures, 120)

	// 4. 主时间窗点位数量均衡
	groups = balanceTimeWindowCount(groups, pointDict, gidFeatures, 540, 1260)

	// 5. 自动检测并修正所有分组的地理离群点
	groups = balanceOutliers(groups, pointDict, gidFeatures, 5, 2)

	// 6. 极端孤立点强制归组
	groups = balanceExtremeIsolatedPoints(groups, pointDict, gidFeatures, 20)

	// 输出分组结果
	for groupID, pids := range groups {
		fmt.Printf("分组%d:\n", groupID+1)
		for _, pid := range pids {
			point := pointDict[pid]
			fmt.Printf("  点位ID: %d, 时间窗: %v\n", pid, point.TimeWindows)
		}
		fmt.Printf("  本组点位数: %d\n", len(pids))
		fmt.Println("---")
	}

	// 输出简化的分组结果
	for groupID, pids := range groups {
		fmt.Printf("分组%d:\n", groupID+1)
		var pidStrs []string
		for _, pid := range pids {
			pidStrs = append(pidStrs, strconv.Itoa(pid))
		}
		fmt.Println(strings.Join(pidStrs, ","))
		fmt.Printf("  本组点位数: %d\n", len(pids))
		fmt.Println("---")
	}

	// 输出分组结果到CSV文件
	outputPath := filepath.Join("..", "output", "output.csv")
	err = writeOutputToCSV(groups, pointDict, outputPath)
	if err != nil {
		log.Fatalf("写入CSV文件失败: %v", err)
	}

	fmt.Printf("分组结果已保存到: %s\n", outputPath)
}
