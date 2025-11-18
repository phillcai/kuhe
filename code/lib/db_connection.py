#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库连接模块
通过 SSH 隧道连接到 MySQL 数据库，提供便捷的数据库访问接口
"""

from contextlib import contextmanager
from typing import Optional, Dict, Any
import pymysql
from sshtunnel import SSHTunnelForwarder
from pymysql.cursors import DictCursor

from .config import DatabaseConfig


class DatabaseConnection:
    """
    数据库连接类
    管理 SSH 隧道和 MySQL 数据库连接
    """
    
    def __init__(
        self,
        ssh_host: str,
        ssh_port: int = 22,
        ssh_username: str = 'root',
        ssh_pkey: str = '/Users/admin/.ssh/id_ed25519',
        mysql_host: str = 'rm-t4ne4yl5huiod5010.mysql.singapore.rds.aliyuncs.com',
        mysql_port: int = 3306,
        mysql_user: Optional[str] = None,
        mysql_password: Optional[str] = None,
        mysql_database: Optional[str] = None,
        mysql_charset: str = 'utf8mb4',
    ):
        """
        初始化数据库连接配置
        
        Args:
            ssh_host: SSH 服务器地址
            ssh_port: SSH 端口
            ssh_username: SSH 用户名
            ssh_pkey: SSH 私钥路径
            mysql_host: MySQL 服务器地址
            mysql_port: MySQL 端口
            mysql_user: MySQL 用户名
            mysql_password: MySQL 密码
            mysql_database: MySQL 数据库名
            mysql_charset: MySQL 字符集
        """
        self.ssh_config = {
            'host': ssh_host,
            'port': ssh_port,
            'username': ssh_username,
            'pkey': ssh_pkey,
        }
        
        self.mysql_config = {
            'host': mysql_host,
            'port': mysql_port,
            'user': mysql_user,
            'password': mysql_password,
            'database': mysql_database,
            'charset': mysql_charset,
        }
        
        self._tunnel: Optional[SSHTunnelForwarder] = None
        self._connection: Optional[pymysql.Connection] = None
    
    @contextmanager
    def connect(self):
        """
        创建数据库连接的上下文管理器
        
        Yields:
            pymysql.Connection: 数据库连接对象
            
        Example:
            >>> db = DatabaseConnection(
            ...     ssh_host='47.237.30.160',
            ...     mysql_user='user',
            ...     mysql_password='pass',
            ...     mysql_database='dbname'
            ... )
            >>> with db.connect() as conn:
            ...     with conn.cursor() as cursor:
            ...         cursor.execute("SELECT * FROM table")
            ...         result = cursor.fetchall()
        """
        if not self.mysql_config['user']:
            raise ValueError("MySQL 用户名未设置，请设置 mysql_user 参数")
        if not self.mysql_config['password']:
            raise ValueError("MySQL 密码未设置，请设置 mysql_password 参数")
        
        # 创建 SSH 隧道
        tunnel = SSHTunnelForwarder(
            (self.ssh_config['host'], self.ssh_config['port']),
            ssh_username=self.ssh_config['username'],
            ssh_pkey=self.ssh_config['pkey'],
            remote_bind_address=(self.mysql_config['host'], self.mysql_config['port']),
            local_bind_address=('127.0.0.1', 0),  # 0 表示自动分配本地端口
        )
        
        try:
            tunnel.start()
            self._tunnel = tunnel
            
            # 通过 SSH 隧道连接 MySQL
            connection = pymysql.connect(
                host='127.0.0.1',
                port=tunnel.local_bind_port,
                user=self.mysql_config['user'],
                password=self.mysql_config['password'],
                database=self.mysql_config['database'],
                charset=self.mysql_config['charset'],
                cursorclass=DictCursor,
            )
            
            self._connection = connection
            
            try:
                yield connection
            finally:
                connection.close()
                self._connection = None
        finally:
            if tunnel.is_alive:
                tunnel.stop()
            self._tunnel = None
    
    def execute_query(self, sql: str, params: Optional[tuple] = None) -> list:
        """
        执行查询语句并返回结果
        
        Args:
            sql: SQL 查询语句
            params: SQL 参数（可选）
            
        Returns:
            list: 查询结果列表（字典格式）
            
        Example:
            >>> db = DatabaseConnection(...)
            >>> results = db.execute_query("SELECT * FROM users WHERE id = %s", (1,))
        """
        with self.connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()
    
    def execute_update(self, sql: str, params: Optional[tuple] = None) -> int:
        """
        执行更新语句（INSERT, UPDATE, DELETE）
        
        Args:
            sql: SQL 更新语句
            params: SQL 参数（可选）
            
        Returns:
            int: 受影响的行数
            
        Example:
            >>> db = DatabaseConnection(...)
            >>> rows = db.execute_update("UPDATE users SET name = %s WHERE id = %s", ('John', 1))
        """
        with self.connect() as conn:
            with conn.cursor() as cursor:
                rows = cursor.execute(sql, params)
                conn.commit()
                return rows
    
    def execute_many(self, sql: str, params_list: list) -> int:
        """
        批量执行 SQL 语句
        
        Args:
            sql: SQL 语句
            params_list: 参数列表
            
        Returns:
            int: 受影响的行数
            
        Example:
            >>> db = DatabaseConnection(...)
            >>> rows = db.execute_many(
            ...     "INSERT INTO users (name, email) VALUES (%s, %s)",
            ...     [('John', 'john@example.com'), ('Jane', 'jane@example.com')]
            ... )
        """
        with self.connect() as conn:
            with conn.cursor() as cursor:
                rows = cursor.executemany(sql, params_list)
                conn.commit()
                return rows


def create_db_connection(
    mysql_user: Optional[str] = None,
    mysql_password: Optional[str] = None,
    mysql_database: Optional[str] = None,
    ssh_host: Optional[str] = None,
    ssh_port: Optional[int] = None,
    ssh_username: Optional[str] = None,
    ssh_pkey: Optional[str] = None,
    mysql_host: Optional[str] = None,
    mysql_port: Optional[int] = None,
    use_config: bool = True,
) -> DatabaseConnection:
    """
    快速创建数据库连接对象的便捷函数
    
    Args:
        mysql_user: MySQL 用户名（如果不提供，从配置文件读取）
        mysql_password: MySQL 密码（如果不提供，从配置文件读取）
        mysql_database: MySQL 数据库名（如果不提供，从配置文件读取）
        ssh_host: SSH 服务器地址（如果不提供，从配置文件读取）
        ssh_port: SSH 端口（如果不提供，从配置文件读取）
        ssh_username: SSH 用户名（如果不提供，从配置文件读取）
        ssh_pkey: SSH 私钥路径（如果不提供，从配置文件读取）
        mysql_host: MySQL 服务器地址（如果不提供，从配置文件读取）
        mysql_port: MySQL 端口（如果不提供，从配置文件读取）
        use_config: 是否使用配置文件中的默认值（默认: True）
        
    Returns:
        DatabaseConnection: 数据库连接对象
        
    Example:
        >>> from lib.db_connection import create_db_connection
        >>> 
        >>> # 方法 1: 使用配置文件（推荐）
        >>> db = create_db_connection()
        >>> 
        >>> # 方法 2: 指定部分参数，其他从配置文件读取
        >>> db = create_db_connection(mysql_database='other_db')
        >>> 
        >>> # 方法 3: 完全自定义配置
        >>> db = create_db_connection(
        ...     mysql_user='user',
        ...     mysql_password='pass',
        ...     mysql_database='dbname',
        ...     use_config=False
        ... )
    """
    if use_config:
        # 从配置文件读取默认值
        return DatabaseConnection(
            ssh_host=ssh_host or DatabaseConfig.SSH_HOST,
            ssh_port=ssh_port or DatabaseConfig.SSH_PORT,
            ssh_username=ssh_username or DatabaseConfig.SSH_USERNAME,
            ssh_pkey=ssh_pkey or DatabaseConfig.SSH_PKEY,
            mysql_host=mysql_host or DatabaseConfig.MYSQL_HOST,
            mysql_port=mysql_port or DatabaseConfig.MYSQL_PORT,
            mysql_user=mysql_user or DatabaseConfig.MYSQL_USER,
            mysql_password=mysql_password or DatabaseConfig.MYSQL_PASSWORD,
            mysql_database=mysql_database or DatabaseConfig.MYSQL_DATABASE,
        )
    else:
        # 不使用配置文件，必须提供所有参数
        return DatabaseConnection(
            ssh_host=ssh_host or '47.237.30.160',
            ssh_port=ssh_port or 22,
            ssh_username=ssh_username or 'root',
            ssh_pkey=ssh_pkey or '/Users/admin/.ssh/id_ed25519',
            mysql_host=mysql_host or 'rm-t4ne4yl5huiod5010.mysql.singapore.rds.aliyuncs.com',
            mysql_port=mysql_port or 3306,
            mysql_user=mysql_user,
            mysql_password=mysql_password,
            mysql_database=mysql_database,
        )


def get_default_connection() -> DatabaseConnection:
    """
    获取使用默认配置的数据库连接对象
    
    这是最简单的方式，直接使用 config.py 中配置的所有参数
    
    Returns:
        DatabaseConnection: 数据库连接对象
        
    Example:
        >>> from lib.db_connection import get_default_connection
        >>> db = get_default_connection()
        >>> results = db.execute_query("SELECT * FROM table")
    """
    return create_db_connection()

