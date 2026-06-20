# -*- coding: utf-8 -*-
"""
应用配置文件
"""
import os

# 基础路径
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# 数据库配置
SQLALCHEMY_DATABASE_URI = os.path.join(BASE_DIR, 'data', 'office.db')
SQLALCHEMY_TRACK_MODIFICATIONS = False

# 附件上传目录
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 'zip', 'rar'}

# 最大文件大小 (50MB)
MAX_CONTENT_LENGTH = 50 * 1024 * 1024

# 密钥
SECRET_KEY = 'office-workbench-secret-key-2024'

# SSL证书配置
# 方式1: 自签名证书（仅限本地测试）
SSL_CERT = os.path.join(BASE_DIR, 'ssl', 'server.crt')
SSL_KEY = os.path.join(BASE_DIR, 'ssl', 'server.key')

# 方式2: Let's Encrypt证书（生产环境推荐）
# SSL_CERT = '/etc/letsencrypt/live/yourdomain.com/fullchain.pem'
# SSL_KEY = '/etc/letsencrypt/live/yourdomain.com/privkey.pem'