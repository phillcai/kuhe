package main

// 基础数据类型定义
// 用于车辆点位分配算法的核心数据结构

// 点位结构体
type VehiclePoint struct {
	ID             string   `json:"id"`              // 点位ID
	Longitude      float64  `json:"longitude"`       // 经度
	Latitude       float64  `json:"latitude"`        // 纬度
	IsShortage     bool     `json:"is_shortage"`     // 是否缺货
	CompatVehicles []string `json:"compat_vehicles"` // 兼容车辆列表
}

// 车辆结构体
type Vehicle struct {
	ID     string  `json:"id"`     // 车辆ID
	Ratio  float64 `json:"ratio"`  // 预设缺货点位比例
	Region int     `json:"region"` // 所属区域编号
}

// 区域结构体
type Region struct {
	ID     int      // 区域ID
	Points []string // 区域内点位ID列表
}

// 分配结果结构体
type AllocationResult struct {
	VehicleID      string   // 车辆ID
	AssignedPoints []string // 分配的点位ID列表
	ShortageCount  int      // 缺货点位数量
	ActualRatio    float64  // 实际缺货比例
}
