## Context

`central_kitchen_picking_task` 记录每次分拣任务，`frame_inventory_info` 是 JSON 数组，每个元素代表一个货架格，包含 `production_date`（逗号分隔的批次日期，每个值 = 1份）和 `qty`（该格总份数）。CK 在当日 16:00 生产完成当天批次，预期次日 16:00 前完成分拣。

## Goals / Non-Goals

**Goals:**
- 按分拣日期统计时效分类的份数与占比
- 支持默认区间（近7天不含今天）和命令行自定义区间
- 输出控制台报告和 CSV 文件

**Non-Goals:**
- 不分析甜品（commodity_type != 1 的可忽略，按实际数据处理）
- 不做实时监控，只做历史回溯分析
- 不分析具体 SKU 维度（该维度数据量大，按需可扩展）

## Decisions

**时效截止时间计算**
- 截止时间 = `production_date` 解析为日期 + 1天 + 16小时
- 分类：
  - `picking_time ≤ cutoff` → 周期内
  - `cutoff < picking_time ≤ cutoff + 24h` → 晚1天
  - `cutoff + 24h < picking_time ≤ cutoff + 48h` → 晚2天
  - `picking_time > cutoff + 48h` → 更久
  - `production_date` 为空或格式异常 → 批次缺失
- 用任务 `create_time` 作为分拣时间（粒度足够，无更精细时间戳）

**数据过滤**
- `canceled_at IS NULL`：排除已取消任务
- `frame_inventory_info IS NOT NULL AND != ''`：排除无货架数据的任务

**命令行参数**
- 无参数：默认近7天不含今天
- 两个参数 `YYYY-MM-DD YYYY-MM-DD`：左闭右闭区间（按分拣日期 DATE(create_time)）

**数据库连接**
- 复用 `code/lib.create_db_connection`，指定 `mysql_database='smart_cooker_sg'`

## Risks / Trade-offs

- `production_date` 逗号数量应等于 `qty`，若不一致按实际逗号数处理，不报错
- 批次日期历史数据可能出现极旧日期（如库存积压），归入"更久"，无需特殊处理
- 查询区间较长时，`frame_inventory_info` 数据量大，解析耗时可能较长 → 可接受，离线分析场景
