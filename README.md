# 本地办公工作台

一个轻量级的本地办公Web应用，支持HTTPS加密传输。

## 功能模块

- **待办任务管理** - 多条件检索、附件上传、进度跟踪、首页到期提醒
- **工作备忘录** - 万字级长文本存储、自定义标签、附件支持
- **重点关注看板** - 可视化展示关注领域及事项状态
- **部门报告库** - 存储各类部门文档、全文检索

## 技术栈

- 前端：原生 HTML + JavaScript
- 后端：Python Flask
- 数据库：SQLite（本地存储）
- 安全：HTTPS加密传输

## 快速启动

```bash
# 安装依赖
pip install -r requirements.txt

# 初始化数据库
python init_db.py

# 生成SSL证书（可选，用于HTTPS）
python generate_ssl.py

# 启动应用
python app.py

# 访问地址
# HTTP: http://localhost:5000
# HTTPS: https://localhost:5000
```

## 数据导入导出

- 支持全量数据导出（ZIP格式）
- 支持一键导入恢复
- 附件批量导出，带标识可溯源

## 项目结构

```
├── app.py              # Flask主应用
├── config.py           # 配置文件
├── init_db.py          # 数据库初始化
├── generate_ssl.py     # SSL证书生成
├── requirements.txt    # Python依赖
├── static/             # 静态资源
├── templates/          # HTML模板
├── data/               # 数据库目录
├── uploads/            # 附件存储
└── ssl/                # SSL证书
```

## 许可证

MIT License