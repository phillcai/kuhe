#!/bin/bash

# 批量测试脚本 - 遍历CSV中所有的req_id并计算相关指标
# 
# 使用方法:
# ./run_batch_test.sh                    # 运行批量测试
# ./run_batch_test.sh --help             # 显示帮助信息

echo "🚀 批量测试脚本 - 遍历所有req_id"
echo "=================================="
echo ""

# 检查是否有Go环境
if ! command -v go &> /dev/null; then
    echo "❌ 错误：未找到Go环境，请先安装Go"
    exit 1
fi

# 检查数据文件是否存在
DATA_FILE="../data/分拣饮料甜品 case.csv"
if [ ! -f "$DATA_FILE" ]; then
    echo "⚠️  警告：数据文件 $DATA_FILE 不存在"
    echo "请确保数据文件路径正确"
    exit 1
fi

# 检查输出目录
OUTPUT_DIR="../data"
if [ ! -d "$OUTPUT_DIR" ]; then
    echo "❌ 错误：输出目录 $OUTPUT_DIR 不存在"
    exit 1
fi

echo "📊 开始批量测试所有req_id..."
echo "📁 数据文件: $DATA_FILE"
echo "📁 输出文件: $OUTPUT_DIR/分拣饮料甜品 case_with_batch_results.csv"
echo ""

# 显示帮助信息
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "📖 批量测试说明："
    echo ""
    echo "此脚本将："
    echo "1. 读取CSV文件中的所有req_id"
    echo "2. 对每个req_id测试甜品(类型6)和饮料(类型5)两种商品类型"
    echo "3. 计算每个测试的总补货量、补货SKU数、最终总库存、最终SKU数"
    echo "4. 将结果添加到CSV文件的最后几列"
    echo "5. 生成新的CSV文件：分拣饮料甜品 case_with_batch_results.csv"
    echo ""
    echo "新增的列包括："
    echo "- 批量测试_总补货量"
    echo "- 批量测试_补货SKU数" 
    echo "- 批量测试_最终总库存"
    echo "- 批量测试_最终SKU数"
    echo "- 批量测试_成功状态"
    echo "- 批量测试_错误信息"
    echo ""
    echo "⚠️  注意：此测试可能需要较长时间，请耐心等待"
    echo ""
    exit 0
fi

# 确认是否继续
echo "⚠️  此测试将遍历CSV中的所有req_id，可能需要较长时间"
read -p "是否继续？(y/N): " confirm

if [[ ! $confirm =~ ^[Yy]$ ]]; then
    echo "❌ 用户取消测试"
    exit 0
fi

echo ""
echo "🔄 开始执行批量测试..."
echo ""

# 运行批量测试
go test -v -run TestBatchAllReqIDs dessert_replenishment.go dessert_replenishment_test.go

exit_code=$?

echo ""
if [ $exit_code -eq 0 ]; then
    echo "✅ 批量测试完成！"
    echo ""
    echo "📊 结果文件已生成："
    echo "   $OUTPUT_DIR/分拣饮料甜品 case_with_batch_results.csv"
    echo ""
    echo "📈 新增列说明："
    echo "   - 批量测试_总补货量: 该req_id的总补货数量"
    echo "   - 批量测试_补货SKU数: 有补货的SKU数量"
    echo "   - 批量测试_最终总库存: 补货后的总库存量"
    echo "   - 批量测试_最终SKU数: 有库存的SKU数量"
    echo "   - 批量测试_成功状态: 测试是否成功"
    echo "   - 批量测试_错误信息: 失败时的错误信息"
    echo ""
    echo "💡 提示："
    echo "   - 可以用Excel或其他工具打开结果文件进行分析"
    echo "   - 成功状态为'成功'的行表示该req_id测试通过"
    echo "   - 失败的行会显示具体的错误信息"
else
    echo "❌ 批量测试失败！"
    echo ""
    echo "🔍 可能的原因："
    echo "   - CSV文件格式问题"
    echo "   - 算法执行错误"
    echo "   - 内存不足"
    echo ""
    echo "💡 建议："
    echo "   - 检查CSV文件是否完整"
    echo "   - 查看上面的错误信息"
    echo "   - 尝试单独测试某个req_id"
fi

echo ""
echo "📝 测试结果说明："
echo "- ✅ 表示测试通过"
echo "- ❌ 表示测试失败" 
echo "- ⚠️  表示警告或需要注意的问题"
echo "- ⏭️  表示跳过的测试"
echo ""
echo "📖 更多详细说明请查看："
echo "   README_DessertReplenishmentTestComplete.md"
