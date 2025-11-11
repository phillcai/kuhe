#!/bin/bash

# CK分拣优化算法测试脚本
# 使用真实库存数据运行测试

echo "=========================================="
echo "CK分拣优化算法 - 真实数据测试"
echo "=========================================="
echo ""

# 检查CSV文件是否存在
if [ ! -f "ck 库存.csv" ]; then
    echo "错误: 找不到 ck 库存.csv 文件"
    exit 1
fi

# 运行测试
echo "正在运行测试..."
echo ""

go run test_with_real_data.go ck_picking_optimizer.go

echo ""
echo "=========================================="
echo "测试完成"
echo "=========================================="

