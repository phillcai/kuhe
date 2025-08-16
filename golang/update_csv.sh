#!/bin/bash

# CSV更新脚本
# 用法: ./update_csv.sh [输入文件] [输出文件]
# 默认: ./update_csv.sh ../data/分拣case.csv ../data/分拣case_updated.csv

# 设置默认值
INPUT_FILE="../data/分拣 case.csv"
OUTPUT_FILE="../data/分拣 case_with_algorithm_extended.csv"
UPDATER_FILE="csv_algorithm_calculator.go"

# 如果提供了参数，使用参数值
if [ $# -ge 1 ]; then
    INPUT_FILE=$1
fi

if [ $# -ge 2 ]; then
    OUTPUT_FILE=$2
fi

echo "🚀 启动CSV更新程序..."
echo "📁 输入文件: $INPUT_FILE"
echo "📁 输出文件: $OUTPUT_FILE"
echo ""

# 检查文件是否存在
if [ ! -f "$INPUT_FILE" ]; then
    echo "❌ 错误: 输入文件不存在: $INPUT_FILE"
    exit 1
fi

if [ ! -f "$UPDATER_FILE" ]; then
    echo "❌ 错误: 更新程序不存在: $UPDATER_FILE"
    exit 1
fi

# 运行更新程序（需要同时编译算法文件）
go run "$UPDATER_FILE" replenishment_algorithm.go "$INPUT_FILE" "$OUTPUT_FILE"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ CSV更新完成！"
    echo ""
    echo "📊 新增列说明:"
echo "  - 算法总补货量: 算法计算的总补货量"
echo "  - 算法补货商品数: 算法计算的补货商品种类数"
echo "  - 算法补货后总库存: 算法计算的补货后总库存"
echo "  - 算法补货后商品数: 算法计算的补货后商品种类数"
    echo ""
    echo "📄 可以查看输出文件: $OUTPUT_FILE"
else
    echo ""
    echo "❌ CSV更新失败！"
    exit 1
fi
