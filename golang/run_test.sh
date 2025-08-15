#!/bin/bash

# 补货算法动态测试脚本
# 用法: ./run_test.sh <req_id>
# 示例: ./run_test.sh 3ce9aa5dd811d4be

CSV_FILE="../data/分拣 case.csv"
MAIN_FILE="dynamic_test_runner.go"
ALGO_FILE="replenishment_algorithm.go"

if [ $# -eq 0 ]; then
    echo "用法: $0 <req_id>"
    echo ""
    echo "可用的req_id列表："
    echo "  3ce9aa5dd811d4be  - 第一条补货案例"
    echo "  526596340844fb9f  - 第二条补货案例"
    echo "  5a54923cbd2045a7  - 第三条补货案例"
    echo "  5378ca9dbcebb4b9  - 第四条补货案例"
    echo "  565fd9448c731dce  - 第五条补货案例"
    echo "  1907c849ec53aff6  - 第六条补货案例"
    echo ""
    echo "示例: $0 3ce9aa5dd811d4be"
    exit 1
fi

REQ_ID=$1

echo "🚀 启动补货算法测试..."
echo "📁 CSV文件: $CSV_FILE"
echo "🔍 Req ID: $REQ_ID"
echo ""

# 检查文件是否存在
if [ ! -f "$CSV_FILE" ]; then
    echo "❌ 错误: CSV文件不存在: $CSV_FILE"
    exit 1
fi

if [ ! -f "$MAIN_FILE" ]; then
    echo "❌ 错误: 主程序文件不存在: $MAIN_FILE"
    exit 1
fi

if [ ! -f "$ALGO_FILE" ]; then
    echo "❌ 错误: 算法文件不存在: $ALGO_FILE"
    exit 1
fi

# 运行测试
go run "$MAIN_FILE" "$ALGO_FILE" "$CSV_FILE" "$REQ_ID"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 测试完成！"
else
    echo ""
    echo "❌ 测试失败！"
    exit 1
fi
