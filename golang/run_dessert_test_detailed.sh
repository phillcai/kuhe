#!/bin/bash

# 甜品补货算法详细测试脚本
# 基于改进版的 dessert_replenishment_test.go
# 
# 使用方法:
# ./run_dessert_test_detailed.sh                           # 交互式选择测试类型
# ./run_dessert_test_detailed.sh 132e5889c453b6f4          # 直接测试指定req_id (默认甜品类型6)
# ./run_dessert_test_detailed.sh 132e5889c453b6f4 6        # 测试指定req_id和商品类型 (6=甜品, 5=饮料)
# ./run_dessert_test_detailed.sh 132e5889c453b6f4 5        # 测试指定req_id的饮料类型

echo "🍰 甜品补货算法详细测试脚本"
echo "==============================="
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
fi

# 检查是否直接传入了req_id参数
if [ $# -ge 1 ]; then
    REQ_ID="$1"
    COMMODITY_TYPE="${2:-6}"  # 默认为甜品类型6，如果提供第二个参数则使用它
    
    # 根据商品类型显示友好名称
    case $COMMODITY_TYPE in
        5)
            COMMODITY_NAME="饮料"
            ;;
        6)
            COMMODITY_NAME="甜品"
            ;;
        *)
            COMMODITY_NAME="未知类型"
            ;;
    esac
    
    echo "🎯 直接测试指定的 req_id: $REQ_ID"
    echo "🏷️  商品类型: $COMMODITY_TYPE ($COMMODITY_NAME)"
    echo "使用详细模式运行..."
    echo ""
    
    # 设置环境变量并运行测试
    export TEST_REQ_ID="$REQ_ID"
    export TEST_COMMODITY_TYPE="$COMMODITY_TYPE"
    go test -v -run TestParameterizedReqID dessert_replenishment.go dessert_replenishment_test.go
    
    exit_code=$?
    echo ""
    if [ $exit_code -eq 0 ]; then
        echo "✅ req_id $REQ_ID (类型: $COMMODITY_TYPE) 测试完成！"
    else
        echo "❌ req_id $REQ_ID (类型: $COMMODITY_TYPE) 测试失败！"
    fi
    exit $exit_code
fi

# 如果没有传入参数，显示交互式菜单
echo "📋 可用的测试选项："
echo "1. 自定义测试 (通过环境变量指定req_id和商品类型)"
echo "2. 运行所有甜品补货测试"
echo ""
echo "💡 提示: 也可以直接传入 req_id 和商品类型参数："
echo "   ./run_dessert_test_detailed.sh 132e5889c453b6f4      # 默认甜品类型"
echo "   ./run_dessert_test_detailed.sh 132e5889c453b6f4 6    # 甜品类型"
echo "   ./run_dessert_test_detailed.sh 132e5889c453b6f4 5    # 饮料类型"
echo ""

read -p "请选择测试类型 (1-2): " choice

case $choice in
    1)
        echo "🛠️  运行自定义测试..."
        echo "请输入要测试的 req_id："
        read -p "req_id: " custom_req_id
        
        if [ -z "$custom_req_id" ]; then
            echo "❌ req_id 不能为空"
            exit 1
        fi
        
        echo "请输入商品类型 (5=饮料, 6=甜品, 默认=6)："
        read -p "commodity_type: " custom_commodity_type
        
        # 如果用户没有输入，默认为甜品类型6
        if [ -z "$custom_commodity_type" ]; then
            custom_commodity_type=6
        fi
        
        # 根据商品类型显示友好名称
        case $custom_commodity_type in
            5)
                commodity_name="饮料"
                ;;
            6)
                commodity_name="甜品"
                ;;
            *)
                commodity_name="未知类型"
                ;;
        esac
        
        echo "🎯 测试指定的 req_id: $custom_req_id"
        echo "🏷️  商品类型: $custom_commodity_type ($commodity_name)"
        echo ""
        
        # 设置环境变量并运行测试
        export TEST_REQ_ID="$custom_req_id"
        export TEST_COMMODITY_TYPE="$custom_commodity_type"
        go test -v -run TestParameterizedReqID dessert_replenishment.go dessert_replenishment_test.go
        ;;
    2)
        echo "🔄 运行所有甜品补货测试..."
        echo ""
        go test -v -run TestDessertReplenishment dessert_replenishment.go dessert_replenishment_test.go
        ;;
    *)
        echo "❌ 无效选择，请重新运行脚本"
        exit 1
        ;;
esac

echo ""
echo "✅ 测试完成！"
echo ""
echo "📝 测试结果说明："
echo "- ✅ 表示测试通过"
echo "- ❌ 表示测试失败" 
echo "- ⚠️  表示警告或需要注意的问题"
echo "- ⏭️  表示跳过的测试"
echo ""
echo "📖 更多详细说明请查看："
echo "   README_DessertReplenishmentTestComplete.md"
