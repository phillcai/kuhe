#!/bin/bash

# 车辆点位分配算法完整运行脚本
# 1. 重新生成最新的真实数据
# 2. 运行车辆分配算法

echo "🚀 车辆点位分配算法 - 完整流程"
echo "================================"
echo "数据来源：新加坡111个无人售货机点位"
echo "车辆配置：3辆车 [2, 14, 15] 从东到西排序"
echo ""

# 创建output目录（如果不存在）
mkdir -p ../output

# 检查必要的算法文件是否存在
required_files=("improved_vehicle_allocation.go" "full_real_data_case.go" "clustering_utils.go" "real_data_generator.go" "types.go")
missing_files=()

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        missing_files+=("$file")
    fi
done

if [ ${#missing_files[@]} -ne 0 ]; then
    echo "❌ 缺少必要文件："
    for file in "${missing_files[@]}"; do
        echo "   - $file"
    done
    echo ""
    echo "请确保所有必要文件都在当前目录下。"
    exit 1
fi

# 检查原始数据文件是否存在
data_files=("../data/point.csv" "../data/point_stock_out.txt" "../data/duration_point.csv")
missing_data=()

for file in "${data_files[@]}"; do
    if [ ! -f "$file" ]; then
        missing_data+=("$file")
    fi
done

if [ ${#missing_data[@]} -ne 0 ]; then
    echo "⚠️  缺少原始数据文件："
    for file in "${data_files[@]}"; do
        echo "   - $file"
    done
    echo ""
    echo "将尝试使用现有的 real_data_test_case.json 文件..."
    if [ ! -f "real_data_test_case.json" ]; then
        echo "❌ 也没有找到 real_data_test_case.json 文件"
        echo "请确保原始数据文件存在，或提供现有的测试数据文件。"
        exit 1
    fi
    echo "✅ 找到现有测试数据文件，跳过数据生成步骤"
    skip_generation=false
else
    echo "✅ 原始数据文件检查完成"
    skip_generation=false
fi

echo ""

# 步骤1：重新生成测试数据（如果原始数据存在）
if [ "$skip_generation" = false ]; then
    echo "📊 步骤1：重新生成最新测试数据..."
    echo "命令: go run real_data_generator.go"
    echo ""
    
    go run real_data_generator.go
    
    generation_exit_code=$?
    
    if [ $generation_exit_code -ne 0 ]; then
        echo "❌ 数据生成失败，退出码: $generation_exit_code"
        echo "将尝试使用现有的测试数据文件..."
        if [ ! -f "real_data_test_case.json" ]; then
            echo "❌ 也没有找到现有的测试数据文件"
            exit 1
        fi
        echo "✅ 使用现有测试数据文件继续"
    else
        echo "✅ 测试数据生成完成！"
    fi
    
    echo ""
    echo "================================"
    echo ""
fi

# 步骤2：运行算法
echo "🔄 步骤2：执行车辆点位分配算法..."
echo "命令: go run improve_vehicle_allocation.go full_real_data_case.go clustering_utils.go types.go"
echo ""

go run improved_vehicle_allocation.go full_real_data_case.go clustering_utils.go types.go

algorithm_exit_code=$?

echo ""
echo "================================"
echo ""

if [ $algorithm_exit_code -eq 0 ]; then
    echo "🎉 算法执行完成！"
    echo ""
    echo "📊 结果说明："
    echo "   - 运力平衡得分：越小越好（理想值 < 0.05）"
    echo "   - 地理集中性：平均点位间距离（理想值 < 25分钟）"
    echo "   - 约束验证：检查是否满足所有约束条件"
    echo ""
    echo "🔧 调整建议："
    echo "   - 算法参数：编辑 full_real_data_case.go 中的权重设置"
    echo "   - 重新运行：./run_vehicle_allocation.sh"
    echo "   - 查看文档：cat README_VehicleAllocation.md"
else
    echo "❌ 算法执行失败，退出码: $algorithm_exit_code"
    echo ""
    echo "🔍 故障排除："
    echo "   1. 检查错误信息"
    echo "   2. 确认数据文件完整性"
    echo "   3. 验证Go环境配置"
    echo "   4. 查看文档获取帮助"
fi

echo ""
echo "📁 生成的文件："
if [ -f "real_data_test_case.json" ]; then
    echo "   ✅ real_data_test_case.json - 完整测试数据"
    # 移动到output目录
    mv real_data_test_case.json ../output/
    echo "   📦 已移动到 ../output/real_data_test_case.json"
fi
if [ -f "allocation_results.csv" ]; then
    echo "   ✅ allocation_results.csv - 完整分配结果（point_id,longitude,latitude,car_id）"
    # 移动到output目录
    mv allocation_results.csv ../output/
    echo "   📦 已移动到 ../output/allocation_results.csv"
fi
if [ -f "shortage_points.csv" ]; then
    echo "   ✅ shortage_points.csv - 缺货点位分配结果（point_id,longitude,latitude,car_id）"
    # 移动到output目录
    mv shortage_points.csv ../output/
    echo "   📦 已移动到 ../output/shortage_points.csv"
fi

echo ""
echo "📂 所有输出文件已保存到 ../output/ 目录"
echo "   当前工作目录: $(pwd)"
echo "   输出目录: ../output/"
