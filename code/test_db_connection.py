#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库连接测试脚本
通过 SSH 隧道连接到 MySQL 数据库
"""

import sys
from sshtunnel import SSHTunnelForwarder
import pymysql
from contextlib import contextmanager


# SSH 隧道配置
SSH_CONFIG = {
    'ssh_host': '47.237.30.160',
    'ssh_port': 22,
    'ssh_username': 'root',
    'ssh_pkey': '/Users/admin/.ssh/id_ed25519',  # 私钥路径
    'ssh_timeout': 5,  # 连接超时时间（秒）
}

# MySQL 数据库配置
MYSQL_CONFIG = {
    'host': 'rm-t4ne4yl5huiod5010.mysql.singapore.rds.aliyuncs.com',
    'port': 3306,
    'user': None,  # 需要填写 MySQL 用户名
    'password': None,  # 需要填写 MySQL 密码
    'database': None,  # 需要填写数据库名，例如 'smart_cooker_sg'
    'charset': 'utf8mb4',
}


@contextmanager
def create_ssh_tunnel():
    """
    创建 SSH 隧道上下文管理器
    
    Yields:
        SSHTunnelForwarder: SSH 隧道对象
    """
    tunnel = SSHTunnelForwarder(
        (SSH_CONFIG['ssh_host'], SSH_CONFIG['ssh_port']),
        ssh_username=SSH_CONFIG['ssh_username'],
        ssh_pkey=SSH_CONFIG['ssh_pkey'],
        ssh_timeout=SSH_CONFIG['ssh_timeout'],
        remote_bind_address=(MYSQL_CONFIG['host'], MYSQL_CONFIG['port']),
        local_bind_address=('127.0.0.1', 0),  # 0 表示自动分配本地端口
    )
    
    try:
        print(f"正在建立 SSH 隧道到 {SSH_CONFIG['ssh_host']}...")
        tunnel.start()
        print(f"SSH 隧道已建立，本地端口: {tunnel.local_bind_port}")
        yield tunnel
    finally:
        print("正在关闭 SSH 隧道...")
        tunnel.stop()
        print("SSH 隧道已关闭")


def test_connection():
    """
    测试数据库连接
    """
    # 检查必要的配置
    if not MYSQL_CONFIG['user']:
        print("错误: 请设置 MYSQL_CONFIG['user']")
        sys.exit(1)
    if not MYSQL_CONFIG['password']:
        print("错误: 请设置 MYSQL_CONFIG['password']")
        sys.exit(1)
    
    try:
        with create_ssh_tunnel() as tunnel:
            # 通过 SSH 隧道连接 MySQL
            connection = pymysql.connect(
                host='127.0.0.1',
                port=tunnel.local_bind_port,
                user=MYSQL_CONFIG['user'],
                password=MYSQL_CONFIG['password'],
                database=MYSQL_CONFIG['database'],
                charset=MYSQL_CONFIG['charset'],
                cursorclass=pymysql.cursors.DictCursor,
            )
            
            try:
                print(f"成功连接到数据库: {MYSQL_CONFIG['database']}")
                
                # 执行测试查询
                with connection.cursor() as cursor:
                    # 查询 MySQL 版本
                    cursor.execute("SELECT VERSION() as version")
                    result = cursor.fetchone()
                    print(f"MySQL 版本: {result['version']}")
                    
                    # 查询当前数据库
                    cursor.execute("SELECT DATABASE() as current_db")
                    result = cursor.fetchone()
                    print(f"当前数据库: {result['current_db']}")
                    
                    # 查询数据库列表
                    cursor.execute("SHOW DATABASES")
                    databases = cursor.fetchall()
                    print(f"\n可用数据库列表:")
                    for db in databases:
                        print(f"  - {db['Database']}")
                    
                    # 如果指定了数据库，查询表列表
                    if MYSQL_CONFIG['database']:
                        cursor.execute("SHOW TABLES")
                        tables = cursor.fetchall()
                        if tables:
                            print(f"\n数据库 '{MYSQL_CONFIG['database']}' 中的表:")
                            for table in tables:
                                table_name = list(table.values())[0]
                                print(f"  - {table_name}")
                        else:
                            print(f"\n数据库 '{MYSQL_CONFIG['database']}' 中没有表")
                
                print("\n✅ 数据库连接测试成功！")
                
            finally:
                connection.close()
                print("数据库连接已关闭")
                
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
    print(f"  主机: {SSH_CONFIG['ssh_host']}")
    print(f"  端口: {SSH_CONFIG['ssh_port']}")
    print(f"  用户: {SSH_CONFIG['ssh_username']}")
    print(f"  私钥: {SSH_CONFIG['ssh_pkey']}")
    print(f"\nMySQL 配置:")
    print(f"  目标主机: {MYSQL_CONFIG['host']}")
    print(f"  端口: {MYSQL_CONFIG['port']}")
    print(f"  用户: {MYSQL_CONFIG['user'] or '(未设置)'}")
    print(f"  数据库: {MYSQL_CONFIG['database'] or '(未设置)'}")
    print("=" * 60)
    print()
    
    test_connection()


if __name__ == '__main__':
    main()

