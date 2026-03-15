## Why

目前无工具可分析 CK 分拣任务的批次时效性。需要了解每天分拣的餐食中，有多少是在预期窗口（批次日次日 16:00）前完成的，以及有多少是超期的、超期几天，以评估分拣及时率。

## What Changes

- 新增 Python 分析脚本，保存至 `topic/分拣批次时效分析/` 目录
- 脚本从数据库查询 `central_kitchen_picking_task` 表，解析 `frame_inventory_info` JSON 字段
- 支持默认分析近7天（不含今天），也支持命令行指定日期区间（`YYYY-MM-DD YYYY-MM-DD`）
- 过滤已取消的任务（`canceled_at IS NULL`）
- 按分拣日期输出时效分布：份数（绝对值）+ 占比（百分比）
- 输出 CSV：明细表 + 按日汇总表

## Capabilities

### New Capabilities

- `picking-timeliness`: 按分拣日期统计各批次时效分类（周期内 / 晚1天 / 晚2天 / 更久 / 批次缺失）的份数与占比

### Modified Capabilities

（无）

## Impact

- 新增文件：`topic/分拣批次时效分析/analyze_picking_timeliness.py`
- 新增输出：`topic/分拣批次时效分析/分拣时效明细.csv`、`topic/分拣批次时效分析/按日时效汇总.csv`
- 依赖：`code/lib`（SSH 隧道 + MySQL 连接）、`pandas`、标准库 `json` / `datetime` / `argparse`
- 数据库：`smart_cooker_sg.central_kitchen_picking_task`
