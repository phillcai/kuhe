#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库连接模块使用示例
"""

from lib.db_connection import create_db_connection, get_default_connection
from lib.config import DatabaseConfig


def example_0_configure_first():
    """
    示例 0: 动态修改配置（可选）
    
    如果需要在代码中动态修改配置，可以使用以下方式
    """
    # 方式 1: 使用 set_credentials 方法（推荐）
    DatabaseConfig.set_credentials(
        user='your_username',
        password='your_password',
        database='smart_cooker_sg'
    )
    
    # 方式 2: 单独设置某个配置项
    # DatabaseConfig.MYSQL_USER = 'your_username'
    # DatabaseConfig.MYSQL_PASSWORD = 'your_password'
    # DatabaseConfig.MYSQL_DATABASE = 'smart_cooker_sg'
    
    print("配置已动态设置")


def example_1_simplest_usage():
    """
    示例 1: 最简单的使用方式（推荐）
    
    前提：已经在 config.py 中配置好数据库凭据
    """
    # 直接使用默认配置
    db = get_default_connection()
    
    # 或者使用 create_db_connection()
    # db = create_db_connection()
    
    # 执行查询
    results = db.execute_query("SELECT VERSION() as version")
    print(f"MySQL 版本: {results[0]['version']}")


def example_2_use_context_manager():
    """
    示例 2: 使用上下文管理器（推荐用于复杂查询）
    """
    db = get_default_connection()
    
    with db.connect() as conn:
        with conn.cursor() as cursor:
            # 执行查询
            cursor.execute("SELECT * FROM users WHERE status = %s", ('active',))
            results = cursor.fetchall()
            for row in results:
                print(row)


def example_3_execute_query():
    """
    示例 3: 使用便捷方法执行查询
    """
    db = get_default_connection()
    
    # 执行查询
    results = db.execute_query(
        "SELECT * FROM users WHERE status = %s AND age > %s",
        ('active', 18)
    )
    print(f"找到 {len(results)} 条记录")


def example_4_execute_update():
    """
    示例 4: 执行更新操作
    """
    db = get_default_connection()
    
    # 执行更新
    rows = db.execute_update(
        "UPDATE users SET status = %s WHERE id = %s",
        ('inactive', 1)
    )
    print(f"更新了 {rows} 行")


def example_5_batch_insert():
    """
    示例 5: 批量插入数据
    """
    db = get_default_connection()
    
    # 批量插入
    data = [
        ('user1', 'email1@example.com'),
        ('user2', 'email2@example.com'),
        ('user3', 'email3@example.com'),
    ]
    rows = db.execute_many(
        "INSERT INTO users (name, email) VALUES (%s, %s)",
        data
    )
    print(f"插入了 {rows} 行")


def example_6_override_database():
    """
    示例 6: 临时切换到其他数据库
    """
    # 使用默认配置，但临时切换数据库
    db = create_db_connection(mysql_database='other_database')
    
    results = db.execute_query("SELECT DATABASE() as db")
    print(f"当前数据库: {results[0]['db']}")


def example_7_custom_config():
    """
    示例 7: 完全自定义配置（不使用配置文件）
    """
    db = create_db_connection(
        mysql_user='custom_user',
        mysql_password='custom_pass',
        mysql_database='custom_db',
        ssh_host='192.168.1.100',
        use_config=False  # 不使用配置文件
    )
    
    results = db.execute_query("SELECT * FROM table")
    print(results)


def example_8_transaction():
    """
    示例 8: 使用事务
    """
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
                print("事务提交成功")
        except Exception as e:
            # 回滚事务
            conn.rollback()
            print(f"事务回滚: {e}")


def example_9_real_world():
    """
    示例 9: 真实场景 - 查询和处理数据
    """
    db = get_default_connection()
    
    # 查询某个时间段的订单
    orders = db.execute_query("""
        SELECT id, order_no, total_amount, created_at
        FROM orders
        WHERE created_at >= %s AND created_at < %s
        AND status = %s
        ORDER BY created_at DESC
        LIMIT 100
    """, ('2025-01-01', '2025-02-01', 'completed'))
    
    # 处理查询结果
    total = sum(order['total_amount'] for order in orders)
    print(f"共有 {len(orders)} 个订单，总金额: {total}")
    
    # 将结果写入文件或进行其他处理
    for order in orders:
        print(f"订单号: {order['order_no']}, 金额: {order['total_amount']}")


if __name__ == '__main__':
    print("=" * 60)
    print("数据库连接模块使用示例")
    print("=" * 60)
    print("\n💡 配置文件 (code/lib/config.py) 已包含默认配置")
    print("   如果需要修改，请打开该文件直接修改配置项")
    print("\n" + "=" * 60)
    print("\n可用的示例函数：")
    print("  - example_0_configure_first()     # 动态修改配置（可选）")
    print("  - example_1_simplest_usage()      # 最简单的使用方式 ⭐")
    print("  - example_2_use_context_manager() # 使用上下文管理器")
    print("  - example_3_execute_query()       # 执行查询")
    print("  - example_4_execute_update()      # 执行更新")
    print("  - example_5_batch_insert()        # 批量插入")
    print("  - example_6_override_database()   # 临时切换数据库")
    print("  - example_7_custom_config()       # 自定义配置")
    print("  - example_8_transaction()         # 使用事务")
    print("  - example_9_real_world()          # 真实场景示例 ⭐")
