## 1. 目录与文件初始化

- [x] 1.1 创建 `topic/分拣批次时效分析/` 目录
- [x] 1.2 创建 `topic/分拣批次时效分析/analyze_picking_timeliness.py` 脚本骨架

## 2. 命令行参数解析

- [x] 2.1 用 `argparse` 实现无参数时默认近7天（不含今天）逻辑
- [x] 2.2 支持两个位置参数 `start_date end_date`（`YYYY-MM-DD` 格式），格式错误时报错退出

## 3. 数据查询

- [x] 3.1 通过 `code/lib.create_db_connection` 连接 `smart_cooker_sg`
- [x] 3.2 查询 `central_kitchen_picking_task`，过滤条件：日期区间、`canceled_at IS NULL`、`frame_inventory_info` 非空

## 4. 数据解析与时效计算

- [x] 4.1 解析每条任务的 `frame_inventory_info` JSON，按逗号展开 `production_date` 得到每份餐食记录
- [x] 4.2 实现 `get_timeliness_label(picking_time, production_date_str)` 函数，返回五档分类
- [x] 4.3 构建 DataFrame，字段：`picking_date`、`picking_no`、`commodity_id`、`production_date`、`timeliness`

## 5. 汇总统计与输出

- [x] 5.1 按 `picking_date × timeliness` 分组统计份数，计算各分类占比（保留1位小数）
- [x] 5.2 输出控制台表格（每行：分拣日期 + 各分类份数 + 各分类占比% + 合计）
- [x] 5.3 输出7天整体汇总（各分类份数+占比）
- [x] 5.4 保存 `分拣时效明细.csv` 和 `按日时效汇总.csv` 到脚本所在目录
