#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库配置模块
管理数据库连接的配置信息
"""

from typing import Optional


class DatabaseConfig:
    """
    数据库配置类
    集中管理所有数据库连接配置
    """
    
    # SSH 隧道配置
    SSH_HOST: str = '47.237.30.160'
    SSH_PORT: int = 22
    SSH_USERNAME: str = 'root'
    SSH_PKEY: str = '/Users/admin/.ssh/id_ed25519'
    
    # MySQL 数据库配置
    MYSQL_HOST: str = 'rm-t4ne4yl5huiod5010.mysql.singapore.rds.aliyuncs.com'
    MYSQL_PORT: int = 3306
    MYSQL_CHARSET: str = 'utf8mb4'
    
    # 数据库凭据（直接在这里修改）
    MYSQL_USER: str = 'cookhere_data'
    MYSQL_PASSWORD: str = 'AiCooker_2024'
    MYSQL_DATABASE: str = 'smart_cooker_sg'
    
    @classmethod
    def set_credentials(cls, user: str, password: str, database: Optional[str] = None):
        """
        动态设置数据库凭据
        
        Args:
            user: MySQL 用户名
            password: MySQL 密码
            database: MySQL 数据库名（可选）
        """
        cls.MYSQL_USER = user
        cls.MYSQL_PASSWORD = password
        if database:
            cls.MYSQL_DATABASE = database
    
    @classmethod
    def get_config_dict(cls) -> dict:
        """
        获取配置字典
        
        Returns:
            dict: 配置字典
        """
        return {
            'ssh_host': cls.SSH_HOST,
            'ssh_port': cls.SSH_PORT,
            'ssh_username': cls.SSH_USERNAME,
            'ssh_pkey': cls.SSH_PKEY,
            'mysql_host': cls.MYSQL_HOST,
            'mysql_port': cls.MYSQL_PORT,
            'mysql_user': cls.MYSQL_USER,
            'mysql_password': cls.MYSQL_PASSWORD,
            'mysql_database': cls.MYSQL_DATABASE,
            'mysql_charset': cls.MYSQL_CHARSET,
        }

