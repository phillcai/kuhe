# Golang 版本使用说明

本项目包含一个 Golang 版本的点位聚类和时间窗口分析程序，位于 `golang/` 目录中。

## 快速开始

### 1. 进入 golang 目录
```bash
cd golang
```

### 2. 编译程序
```bash
go build -o kuhe main.go
```

### 3. 运行程序
```bash
./kuhe
```

## 详细说明

请查看 `golang/README_Go.md` 文件获取完整的使用说明和功能介绍。

## 文件结构

- `golang/main.go` - 主程序文件
- `golang/go.mod` - Go 模块文件
- `golang/README_Go.md` - 详细说明文档
- `golang/kuhe` - 编译后的可执行文件
- `data/点位信息.csv` - 输入数据文件
- `output/output.csv` - 输出结果文件

## 系统要求

- Go 1.21 或更高版本
- 确保 `data/点位信息.csv` 文件存在且格式正确 