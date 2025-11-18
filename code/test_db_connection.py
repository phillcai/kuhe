#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库连接测试脚本
通过 SSH 隧道连接到 MySQL 数据库

现在使用封装的数据库连接模块（lib/db_connection.py）
"""

import sys
from lib import get_default_connection
from lib.config import DatabaseConfig


def test_connection():
    """
    测试数据库连接
    """
    # 检查必要的配置
    if not DatabaseConfig.MYSQL_USER:
        print("错误: 请先在 lib/config.py 中设置数据库用户名")
        print("或者在代码中调用：")
        print("  DatabaseConfig.set_credentials(user='xxx', password='xxx', database='xxx')")
        sys.exit(1)
    if not DatabaseConfig.MYSQL_PASSWORD:
        print("错误: 请先在 lib/config.py 中设置数据库密码")
        sys.exit(1)
    
    try:
        print("正在建立数据库连接...")
        db = get_default_connection()
        
        print(f"成功连接到数据库: {DatabaseConfig.MYSQL_DATABASE}")
        
        # 查询 MySQL 版本
        result = db.execute_query("SELECT VERSION() as version")
        print(f"MySQL 版本: {result[0]['version']}")
        
        # 查询当前数据库
        result = db.execute_query("SELECT DATABASE() as current_db")
        print(f"当前数据库: {result[0]['current_db']}")
        
        # 查询数据库列表
        databases = db.execute_query("SHOW DATABASES")
        print(f"\n可用数据库列表:")
        for db_info in databases:
            print(f"  - {db_info['Database']}")
        
        # 如果指定了数据库，查询表列表
        if DatabaseConfig.MYSQL_DATABASE:
            tables = db.execute_query("SHOW TABLES")
            if tables:
                print(f"\n数据库 '{DatabaseConfig.MYSQL_DATABASE}' 中的表:")
                for table in tables:
                    table_name = list(table.values())[0]
                    print(f"  - {table_name}")
            else:
                print(f"\n数据库 '{DatabaseConfig.MYSQL_DATABASE}' 中没有表")
        
        print("\n✅ 数据库连接测试成功！")
                
    except Exception as e:
        print(f"\n❌ 连接失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """
    主函数
    """
    print("=" * 60)
    print("数据库连接测试脚本")
    print("=" * 60)
    print(f"\nSSH 配置:")
    print(f"  主机: {DatabaseConfig.SSH_HOST}")
    print(f"  端口: {DatabaseConfig.SSH_PORT}")
    print(f"  用户: {DatabaseConfig.SSH_USERNAME}")
    print(f"  私钥: {DatabaseConfig.SSH_PKEY}")
    print(f"\nMySQL 配置:")
    print(f"  目标主机: {DatabaseConfig.MYSQL_HOST}")
    print(f"  端口: {DatabaseConfig.MYSQL_PORT}")
    print(f"  用户: {DatabaseConfig.MYSQL_USER or '(未设置)'}")
    print(f"  数据库: {DatabaseConfig.MYSQL_DATABASE or '(未设置)'}")
    print("=" * 60)
    print()
    
    test_connection()


if __name__ == '__main__':
    main()

