# 补货周报系统

## 概述

这个系统用于生成补货相关的周报数据,整合了三个关键指标:
- **周缺货率统计** - 来自 report.t_commodity_shortage 表
- **周满足率统计** - 来自 point_commodity_fenjian_log 和 sorting_tasks 表
- **周日均补货数统计** - 来自 sorting_tasks 表

## 文件说明

### 数据查询脚本

1. **query_weekly_shortage.py** - 查询周缺货率数据
   - 数据库: `report`
   - 表: `t_commodity_shortage`
   - 输出: 周缺货率(sku权重)、session数

2. **query_weekly_satisfaction.py** - 查询周满足率数据
   - 数据库: `smart_cooker_sg`
   - 表: `point_commodity_fenjian_log`, `sorting_tasks`
   - 输出: 全部满足率、正常车满足率、虚拟车满足率

3. **query_weekly_replenishment.py** - 查询周补货数据
   - 数据库: `smart_cooker_sg`
   - 表: `sorting_tasks`
   - 输出: 补货数、日均补货、日最大补货数、日均点位

### 报告生成脚本

4. **generate_report.py** - 生成HTML周报
   - 整合上述三个脚本的数据
   - 生成美观的HTML报告页面
   - 输出文件: `report.html`

## 使用方法

### 方式一: 生成完整的HTML报告(推荐)

```bash
# 在项目根目录下运行
uv run topic/补货周报/generate_report.py
```

生成的报告会自动保存到 `report.html`,并在浏览器中打开。

### 方式二: 单独运行各个查询脚本

如果只需要查询某一项数据:

```bash
# 查询周缺货率
uv run topic/补货周报/query_weekly_shortage.py

# 查询周满足率
uv run topic/补货周报/query_weekly_satisfaction.py

# 查询周补货数
uv run topic/补货周报/query_weekly_replenishment.py
```

每个脚本都会:
- 在终端输出详细的统计数据
- 导出 Excel 文件到当前目录

## 数据说明

### 周的定义

所有统计都使用**周日到周六**作为一周的周期:
- 周起始日: 周日
- 周结束日: 周六
- 统计区间: 最近90天

### 缺货率计算

```
缺货率(sku权重) = 1 - (在线商品数量 / 最大商品数量)
```

### 满足率计算

```
满足率 = 实际补货数 / (预测需求 - 剩余库存)
```

分类统计:
- **全部**: 所有车辆的平均满足率
- **正常车**: req_car_id 为 2, 14, 15 的车辆
- **虚拟车**: 其他车辆

### 补货数统计

- **周补货数**: 该周总补货盒数
- **日均补货**: 周总补货数 / 6
- **日最大补货数**: 该周内单日最大补货量
- **日均点位**: 该周平均每天服务的点位数

## 输出示例

### HTML报告特点

- 📊 **现代化设计**: 渐变背景、卡片式布局
- 📱 **响应式**: 支持手机、平板、桌面浏览
- 🎨 **美观表格**: 悬停效果、边框美化
- 📈 **数据格式化**: 百分比、千位分隔符
- ⏰ **生成时间**: 显示报告生成时间戳

### Excel导出

单独运行各查询脚本时,会生成带格式的Excel文件:
- 表头加粗、背景色
- 数值格式化(百分比、千位分隔符)
- 列宽自动调整
- 边框美化

## 环境要求

### Python版本
- Python >= 3.12

### 依赖包

项目使用 `uv` 管理依赖,所有依赖已在 `pyproject.toml` 中定义:

```toml
dependencies = [
    "pandas>=2.0.0,<2.3.0",
    "pymysql>=1.1.2",
    "openpyxl>=3.1.5",
    "paramiko>=2.12.0,<3.0.0",
    "sshtunnel>=0.4.0",
]
```

### 数据库配置

需要在 `code/lib/db_connection.py` 中配置数据库连接信息。

## 故障排查

### 问题: ModuleNotFoundError

```bash
# 解决方案: 同步安装依赖
uv sync
```

### 问题: 数据库连接失败

检查以下配置:
1. SSH隧道配置是否正确
2. 数据库地址、端口是否正确
3. 用户名、密码是否正确
4. 网络连接是否正常

### 问题: 查询结果为空

可能原因:
1. 数据库中没有最近90天的数据
2. 表结构发生变化
3. WHERE条件过滤掉了所有数据

## 维护建议

### 定期更新

建议每周运行一次 `generate_report.py` 生成最新周报。

### 数据归档

可以将生成的HTML报告按日期归档:

```bash
# 重命名报告文件
mv report.html report_$(date +%Y%m%d).html
```

### 自动化

可以将报告生成配置为定时任务(crontab):

```bash
# 每周一早上8点生成周报
0 8 * * 1 cd /path/to/kuhe && uv run topic/补货周报/generate_report.py
```

## 技术栈

- **Python 3.12+**: 核心编程语言
- **pandas**: 数据处理和分析
- **pymysql**: MySQL数据库连接
- **openpyxl**: Excel文件读写
- **paramiko**: SSH隧道连接
- **HTML/CSS**: 报告页面展示

## 贡献

如需添加新的统计指标或优化现有功能,请:
1. 在对应的查询脚本中添加SQL查询
2. 更新 `generate_report.py` 中的表格生成逻辑
3. 测试数据输出是否正确
4. 更新本README文档

## 许可证

内部项目使用

