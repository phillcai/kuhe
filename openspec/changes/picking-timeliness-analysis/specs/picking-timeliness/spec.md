## ADDED Requirements

### Requirement: 默认分析近7天
脚本在无命令行参数时，SHALL 自动分析近7天（不含运行当天）的分拣任务。

#### Scenario: 无参数运行
- **WHEN** 用户直接运行脚本，不传任何参数
- **THEN** 分析区间为 `today - 7days` 到 `today - 1day`（含两端日期）

### Requirement: 支持命令行指定日期区间
脚本 SHALL 支持通过命令行参数指定任意日期区间，格式为 `YYYY-MM-DD YYYY-MM-DD`（起始日 结束日，左闭右闭）。

#### Scenario: 指定合法区间
- **WHEN** 用户运行 `python script.py 2026-03-01 2026-03-06`
- **THEN** 仅分析 2026-03-01 至 2026-03-06（含）的分拣任务

#### Scenario: 参数格式错误
- **WHEN** 用户传入格式不符合 `YYYY-MM-DD` 的参数
- **THEN** 脚本打印错误信息并退出，提示正确格式

### Requirement: 过滤已取消任务
脚本 SHALL 排除 `canceled_at IS NOT NULL` 的任务。

#### Scenario: 存在已取消任务
- **WHEN** 数据库中存在 `canceled_at` 不为空的分拣任务
- **THEN** 这些任务的份数不计入任何时效分类

### Requirement: 时效分类计算
脚本 SHALL 以批次 `production_date + 1天 + 16小时` 为截止时间，对每份餐食分类：周期内 / 晚1天 / 晚2天 / 更久 / 批次缺失。

#### Scenario: 在截止时间前分拣
- **WHEN** 分拣任务 `create_time ≤ production_date + 1day + 16h`
- **THEN** 该份餐食归为"周期内"

#### Scenario: 超期1天内
- **WHEN** `cutoff < create_time ≤ cutoff + 24h`
- **THEN** 归为"晚1天"

#### Scenario: 超期2天内
- **WHEN** `cutoff + 24h < create_time ≤ cutoff + 48h`
- **THEN** 归为"晚2天"

#### Scenario: 超期超过2天
- **WHEN** `create_time > cutoff + 48h`
- **THEN** 归为"更久"

#### Scenario: 批次日期缺失
- **WHEN** `production_date` 为空字符串或无法解析为日期
- **THEN** 归为"批次缺失"

### Requirement: 按分拣日输出份数与占比
脚本 SHALL 按 `DATE(create_time)` 分组，输出每个时效分类的绝对份数和占该日总份数的百分比。

#### Scenario: 标准输出
- **WHEN** 分析完成
- **THEN** 控制台打印按分拣日期排序的表格，列包含：合计、周期内、晚1天、晚2天、更久、批次缺失（每项含份数和占比%）

#### Scenario: 输出 CSV
- **WHEN** 分析完成
- **THEN** 在脚本所在目录输出 `分拣时效明细.csv`（逐份明细）和 `按日时效汇总.csv`（汇总表）
