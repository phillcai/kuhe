#!/bin/bash

# 测试数据解析一致性脚本
# 用法: ./test_data_consistency.sh <req_id>
# 示例: ./test_data_consistency.sh 565fd9448c731dce

REQ_ID=${1:-"565fd9448c731dce"}

echo "🧪 测试数据解析一致性"
echo "🔍 Req ID: $REQ_ID"
echo ""

# 1. 运行dynamic_test_runner.go
echo "=== 运行 dynamic_test_runner.go ==="
go run dynamic_test_runner.go replenishment_algorithm.go "../data/分拣 case.csv" "$REQ_ID" > dynamic_output.txt 2>&1

if [ $? -eq 0 ]; then
    echo "✅ dynamic_test_runner.go 执行成功"
else
    echo "❌ dynamic_test_runner.go 执行失败"
fi

echo ""

# 2. 运行csv_algorithm_calculator.go
echo "=== 运行 csv_algorithm_calculator.go ==="
go run csv_algorithm_calculator.go replenishment_algorithm.go "../data/分拣 case.csv" "../data/test_output.csv" > csv_output.txt 2>&1

if [ $? -eq 0 ]; then
    echo "✅ csv_algorithm_calculator.go 执行成功"
else
    echo "❌ csv_algorithm_calculator.go 执行失败"
fi

echo ""

# 3. 对比输出结果
echo "=== 对比输出结果 ==="
echo "dynamic_test_runner.go 输出:"
echo "----------------------------------------"
grep -E "(商品ID|商品_.*|仓库库存|当前库存|最大允许|预期比例)" dynamic_output.txt | head -20

echo ""
echo "csv_algorithm_calculator.go 输出:"
echo "----------------------------------------"
grep -E "(商品ID|商品_.*|仓库库存|当前库存|最大允许|预期比例)" csv_output.txt | head -20

echo ""
echo "=== 检查point_ext解析 ==="
echo "dynamic_test_runner.go point_ext:"
grep -E "point_ext解析结果" dynamic_output.txt

echo ""
echo "csv_algorithm_calculator.go point_ext:"
grep -E "point_ext解析结果" csv_output.txt

echo ""
echo "=== 检查商品数量 ==="
echo "dynamic_test_runner.go 商品数量:"
grep -E "成功创建商品数量" dynamic_output.txt

echo ""
echo "csv_algorithm_calculator.go 商品数量:"
grep -E "成功创建商品数量" csv_output.txt

# 清理临时文件
rm -f dynamic_output.txt csv_output.txt ../data/test_output.csv

echo ""
echo "🎯 测试完成！如果两个脚本的输出一致，说明数据解析问题已修复。"
