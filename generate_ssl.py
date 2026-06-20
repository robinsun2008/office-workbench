# -*- coding: utf-8 -*-
"""
SSL证书生成脚本
生成自签名证书用于本地HTTPS测试
"""
import os
from pathlib import Path

def generate_self_signed_cert():
    """生成自签名SSL证书"""
    try:
        # 尝试使用OpenSSL
        import subprocess
        
        ssl_dir = Path(__file__).parent / 'ssl'
        ssl_dir.mkdir(exist_ok=True)
        
        key_file = ssl_dir / 'server.key'
        cert_file = ssl_dir / 'server.crt'
        
        # 生成私钥和证书
        # Windows路径处理
        key_path = str(key_file).replace('\\', '/')
        cert_path = str(cert_file).replace('\\', '/')
        
        print("正在生成SSL证书...")
        
        # 生成私钥
        subprocess.run([
            'openssl', 'genrsa', '-out', key_path, '2048'
        ], check=True, capture_output=True)
        
        # 生成自签名证书
        subprocess.run([
            'openssl', 'req', '-new', '-x509',
            '-key', key_path,
            '-out', cert_path,
            '-days', '3650',
            '-subj', '/CN=localhost/O=OfficeWorkbench/C=CN'
        ], check=True, capture_output=True)
        
        print("=" * 50)
        print("SSL证书生成成功！")
        print(f"证书文件: {cert_file}")
        print(f"私钥文件: {key_file}")
        print("=" * 50)
        print("现在可以重启应用使用HTTPS访问")
        print("访问地址: https://localhost:5000")
        print("=" * 50)
        return True
        
    except FileNotFoundError:
        print("错误：未找到OpenSSL，请先安装OpenSSL")
        print("或从 https://slproweb.com/products/Win32OpenSSL.html 下载安装")
        return False
    except subprocess.CalledProcessError as e:
        print(f"生成证书时出错: {e}")
        return False
    except Exception as e:
        print(f"未知错误: {e}")
        return False

def generate_cert_with_python():
    """使用Python生成自签名证书（备选方案）"""
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        import datetime
        
        ssl_dir = Path(__file__).parent / 'ssl'
        ssl_dir.mkdir(exist_ok=True)
        
        # 生成私钥
        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        # 生成证书
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "CN"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "OfficeWorkbench"),
            x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.utcnow()
        ).not_valid_after(
            datetime.datetime.utcnow() + datetime.timedelta(days=3650)
        ).sign(key, hashes.SHA256(), default_backend())
        
        # 保存私钥
        key_file = ssl_dir / 'server.key'
        with open(key_file, 'wb') as f:
            f.write(key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        # 保存证书
        cert_file = ssl_dir / 'server.crt'
        with open(cert_file, 'wb') as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        
        print("=" * 50)
        print("SSL证书生成成功！")
        print(f"证书文件: {cert_file}")
        print(f"私钥文件: {key_file}")
        print("=" * 50)
        print("现在可以重启应用使用HTTPS访问")
        print("访问地址: https://localhost:5000")
        print("=" * 50)
        return True
        
    except ImportError:
        print("需要安装 cryptography 库: pip install cryptography")
        return False

if __name__ == '__main__':
    print("=" * 50)
    print("SSL证书生成工具")
    print("=" * 50)
    
    # 先尝试使用OpenSSL
    if not generate_self_signed_cert():
        print("\nOpenSSL不可用，尝试使用Python cryptography库...")
        if not generate_cert_with_python():
            print("\n无法生成证书，请安装OpenSSL或cryptography库")
            print("\nOpenSSL下载地址: https://slproweb.com/products/Win32OpenSSL.html")