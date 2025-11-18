#!/bin/bash
# 补货周报生成脚本
# 使用方法: ./run.sh

echo "======================================"
echo "  补货周报生成工具"
echo "======================================"
echo ""

# 切换到项目根目录
cd "$(dirname "$0")/../.." || exit 1

# 运行报告生成脚本
echo "正在生成周报..."
uv run topic/补货周报/generate_report.py

# 检查是否成功
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 周报生成成功!"
    echo ""
    echo "报告位置: topic/补货周报/report.html"
    echo ""
    
    # 询问是否在浏览器中打开
    read -p "是否在浏览器中打开报告? (Y/n): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
        open topic/补货周报/report.html
        echo "已在浏览器中打开报告"
    fi
else
    echo ""
    echo "❌ 周报生成失败,请查看上面的错误信息"
    exit 1
fi

