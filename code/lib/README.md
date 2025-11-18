# 数据库连接模块

通过 SSH 隧道连接到 MySQL 数据库的便捷工具库。

## 快速开始

### 1. 首次使用：配置数据库凭据

**方法一：直接修改 `config.py` 文件（推荐）**

打开 `code/lib/config.py`，找到配置部分，直接修改：

```python
# 数据库凭据（直接在这里修改）
MYSQL_USER: str = 'cookhere_data'       # 改为你的用户名
MYSQL_PASSWORD: str = 'AiCooker_2024'   # 改为你的密码
MYSQL_DATABASE: str = 'smart_cooker_sg' # 改为你的数据库名
```

**方法二：在你的代码中动态设置**

```python
from lib.config import DatabaseConfig

DatabaseConfig.set_credentials(
    user='your_username',
    password='your_password',
    database='smart_cooker_sg'
)
```

### 2. 基本使用

配置完成后，使用非常简单：

```python
from lib import get_default_connection

# 创建数据库连接
db = get_default_connection()

# 执行查询
results = db.execute_query("SELECT * FROM users WHERE id = %s", (1,))
print(results)

# 执行更新
rows = db.execute_update("UPDATE users SET name = %s WHERE id = %s", ('John', 1))
print(f"更新了 {rows} 行")

# 批量插入
data = [('user1', 'email1@example.com'), ('user2', 'email2@example.com')]
db.execute_many("INSERT INTO users (name, email) VALUES (%s, %s)", data)
```

## 使用方式

### 方式 1：使用便捷方法（最简单）

```python
from lib import get_default_connection

db = get_default_connection()

# 查询
results = db.execute_query("SELECT * FROM table")

# 更新
rows = db.execute_update("UPDATE table SET field = %s WHERE id = %s", ('value', 1))

# 批量操作
db.execute_many("INSERT INTO table (col1, col2) VALUES (%s, %s)", data_list)
```

### 方式 2：使用上下文管理器（适合复杂操作）

```python
from lib import get_default_connection

db = get_default_connection()

with db.connect() as conn:
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM users")
        results = cursor.fetchall()
        for row in results:
            print(row)
```

### 方式 3：临时切换数据库

```python
from lib import create_db_connection

# 使用默认配置，但切换到其他数据库
db = create_db_connection(mysql_database='other_database')
results = db.execute_query("SELECT * FROM table")
```

### 方式 4：完全自定义配置

```python
from lib import create_db_connection

db = create_db_connection(
    mysql_user='custom_user',
    mysql_password='custom_pass',
    mysql_database='custom_db',
    ssh_host='192.168.1.100',
    use_config=False  # 不使用配置文件
)
```

## 在其他文件中使用

### 示例 1：数据分析脚本

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze_user_data.py - 用户数据分析脚本
"""

from lib import get_default_connection
import pandas as pd

def analyze_users():
    """分析用户数据"""
    db = get_default_connection()
    
    # 查询数据
    results = db.execute_query("""
        SELECT 
            date(created_at) as date,
            count(*) as user_count
        FROM users
        WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        GROUP BY date(created_at)
        ORDER BY date
    """)
    
    # 使用 pandas 处理数据
    df = pd.DataFrame(results)
    print(df.describe())
    
    return df

if __name__ == '__main__':
    df = analyze_users()
```

### 示例 2：数据导出脚本

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
export_orders.py - 导出订单数据
"""

from lib import get_default_connection
import csv

def export_orders_to_csv(start_date, end_date, output_file):
    """导出订单数据到 CSV"""
    db = get_default_connection()
    
    orders = db.execute_query("""
        SELECT order_no, customer_name, total_amount, created_at
        FROM orders
        WHERE created_at >= %s AND created_at < %s
        ORDER BY created_at
    """, (start_date, end_date))
    
    # 写入 CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        if orders:
            writer = csv.DictWriter(f, fieldnames=orders[0].keys())
            writer.writeheader()
            writer.writerows(orders)
    
    print(f"已导出 {len(orders)} 条订单到 {output_file}")

if __name__ == '__main__':
    export_orders_to_csv('2025-01-01', '2025-02-01', 'orders.csv')
```

### 示例 3：数据同步脚本

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync_data.py - 数据同步脚本
"""

from lib import create_db_connection

def sync_data_between_databases():
    """在两个数据库之间同步数据"""
    # 源数据库
    source_db = create_db_connection(mysql_database='source_db')
    
    # 目标数据库
    target_db = create_db_connection(mysql_database='target_db')
    
    # 从源数据库读取
    source_data = source_db.execute_query("SELECT * FROM products WHERE updated_at > %s", ('2025-01-01',))
    
    # 写入目标数据库
    if source_data:
        target_db.execute_many(
            "INSERT INTO products (id, name, price) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE name=%s, price=%s",
            [(row['id'], row['name'], row['price'], row['name'], row['price']) for row in source_data]
        )
    
    print(f"已同步 {len(source_data)} 条数据")

if __name__ == '__main__':
    sync_data_between_databases()
```

## 事务处理

```python
from lib import get_default_connection

db = get_default_connection()

with db.connect() as conn:
    try:
        with conn.cursor() as cursor:
            # 开始事务
            cursor.execute("START TRANSACTION")
            
            # 执行多个操作
            cursor.execute("UPDATE accounts SET balance = balance - 100 WHERE id = 1")
            cursor.execute("UPDATE accounts SET balance = balance + 100 WHERE id = 2")
            
            # 提交事务
            conn.commit()
            print("转账成功")
    except Exception as e:
        # 回滚事务
        conn.rollback()
        print(f"转账失败，已回滚: {e}")
```

## API 文档

### `get_default_connection()`

获取使用默认配置的数据库连接对象（最简单的方式）。

**返回：** `DatabaseConnection` 对象

### `create_db_connection(**kwargs)`

创建数据库连接对象，支持自定义配置。

**参数：**
- `mysql_user`: MySQL 用户名（可选，默认从配置读取）
- `mysql_password`: MySQL 密码（可选，默认从配置读取）
- `mysql_database`: MySQL 数据库名（可选，默认从配置读取）
- `use_config`: 是否使用配置文件（默认 True）

**返回：** `DatabaseConnection` 对象

### `DatabaseConnection` 类方法

#### `execute_query(sql, params=None)`

执行查询语句并返回结果。

**参数：**
- `sql`: SQL 查询语句
- `params`: SQL 参数（可选）

**返回：** 结果列表（字典格式）

#### `execute_update(sql, params=None)`

执行更新语句（INSERT, UPDATE, DELETE）。

**参数：**
- `sql`: SQL 更新语句
- `params`: SQL 参数（可选）

**返回：** 受影响的行数

#### `execute_many(sql, params_list)`

批量执行 SQL 语句。

**参数：**
- `sql`: SQL 语句
- `params_list`: 参数列表

**返回：** 受影响的行数

#### `connect()`

创建数据库连接的上下文管理器。

**返回：** 数据库连接对象

## 配置说明

### 配置项

在 `config.py` 中可以配置以下参数：

**SSH 隧道配置：**
- `SSH_HOST`: SSH 服务器地址
- `SSH_PORT`: SSH 端口（默认 22）
- `SSH_USERNAME`: SSH 用户名
- `SSH_PKEY`: SSH 私钥路径
- `SSH_TIMEOUT`: 连接超时时间（秒）

**MySQL 配置：**
- `MYSQL_HOST`: MySQL 服务器地址
- `MYSQL_PORT`: MySQL 端口（默认 3306）
- `MYSQL_USER`: MySQL 用户名
- `MYSQL_PASSWORD`: MySQL 密码
- `MYSQL_DATABASE`: MySQL 数据库名
- `MYSQL_CHARSET`: 字符集（默认 utf8mb4）

### 修改配置

```python
from lib.config import DatabaseConfig

# 方法 1: 使用 set_credentials
DatabaseConfig.set_credentials(
    user='username',
    password='password',
    database='dbname'
)

# 方法 2: 直接设置
DatabaseConfig.MYSQL_USER = 'username'
DatabaseConfig.MYSQL_PASSWORD = 'password'
DatabaseConfig.MYSQL_DATABASE = 'dbname'
```

## 注意事项

1. **首次使用前必须配置数据库凭据**
2. **不要将 `config.py` 中的密码提交到 git 仓库**
3. 建议在生产环境使用环境变量
4. 所有查询结果都是字典格式（DictCursor）
5. 自动管理连接生命周期，无需手动关闭

## 更多示例

查看 `example_usage.py` 文件获取更多使用示例。

