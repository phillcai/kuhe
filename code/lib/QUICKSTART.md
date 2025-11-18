# 快速开始指南

## 5 分钟快速配置

### 步骤 1：配置数据库凭据

打开 `code/lib/config.py` 文件，找到配置部分（约 30 行左右），**直接修改**：

```python
# 数据库凭据（直接在这里修改）
MYSQL_USER: str = 'cookhere_data'       # 修改为你的用户名
MYSQL_PASSWORD: str = 'AiCooker_2024'   # 修改为你的密码
MYSQL_DATABASE: str = 'smart_cooker_sg' # 修改为你的数据库名
```

> 💡 配置已经设置好了，如果你的凭据相同，可以直接跳到步骤 2 测试！

### 步骤 2：测试连接

运行测试脚本：

```bash
cd /Users/admin/Code/MyCode/kuhe
python code/test_db_connection.py
```

如果看到 ✅，说明配置成功！

### 步骤 3：在你的代码中使用

在任何 Python 文件中使用：

```python
from lib import get_default_connection

# 创建连接
db = get_default_connection()

# 执行查询
results = db.execute_query("SELECT * FROM your_table")
print(results)

# 执行更新
rows = db.execute_update("UPDATE your_table SET field = %s WHERE id = %s", ('value', 1))

# 批量插入
data = [('name1', 'email1'), ('name2', 'email2')]
db.execute_many("INSERT INTO users (name, email) VALUES (%s, %s)", data)
```

## 完整示例

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
my_script.py - 我的数据分析脚本
"""

from lib import get_default_connection

def main():
    # 获取数据库连接
    db = get_default_connection()
    
    # 查询数据
    users = db.execute_query("""
        SELECT id, name, email, created_at
        FROM users
        WHERE status = %s
        ORDER BY created_at DESC
        LIMIT 10
    """, ('active',))
    
    # 处理数据
    for user in users:
        print(f"用户: {user['name']}, 邮箱: {user['email']}")
    
    print(f"\n共找到 {len(users)} 个活跃用户")

if __name__ == '__main__':
    main()
```

就这么简单！🎉

## 常见问题

**Q: 如何在代码中动态修改配置？**

A: 在你的脚本开头设置：

```python
from lib.config import DatabaseConfig

DatabaseConfig.set_credentials(
    user='username',
    password='password',
    database='dbname'
)
```

**Q: 如何临时切换到其他数据库？**

A: 使用 `create_db_connection`：

```python
from lib import create_db_connection

db = create_db_connection(mysql_database='other_database')
```

**Q: 配置文件已设置好，为什么还要修改？**

A: 如果你的数据库凭据与配置文件中的相同，可以直接使用，无需修改！

更多详细文档请查看 [README.md](README.md)

