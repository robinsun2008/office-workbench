# -*- coding: utf-8 -*-
"""
数据库初始化脚本
创建所有必要的数据表
"""
import sqlite3
import os

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'office.db')

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """初始化数据库，创建所有表"""
    # 确保data目录存在
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # ==================== 1. 待办任务表 ====================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS todo_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            summary TEXT NOT NULL,              -- 任务摘要
            detail_content TEXT,                -- 详细内容
            deadline DATETIME,                  -- 截止完成时间
            assigned_team TEXT,                 -- 指派团队
            assigned_person TEXT,               -- 指派个人
            progress_note TEXT,                 -- 进度备注
            tag TEXT DEFAULT '一般',            -- 标签：紧急/重要/一般
            status TEXT DEFAULT '未完成',       -- 状态：未完成/已完成
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # ==================== 2. 工作备忘录表 ====================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS memos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,               -- 标题摘要
            content TEXT,                      -- 大篇幅正文（支持万字级）
            tags TEXT,                         -- 自定义标签（逗号分隔）
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # ==================== 3. 重点关注领域表 ====================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS focus_areas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,                -- 领域名称
            description TEXT,                 -- 领域描述
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # ==================== 4. 重点关注事项表 ====================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS focus_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            area_id INTEGER,                   -- 所属领域ID
            title TEXT NOT NULL,               -- 事项标题（≤40字）
            note TEXT,                         -- 长文本备注
            planned_date DATE,                 -- 计划完成时间
            status TEXT DEFAULT '未开始',      -- 状态：未开始/进行中/完成/延期
            completed_at DATETIME,             -- 实际完成时间
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (area_id) REFERENCES focus_areas(id)
        )
    ''')
    
    # ==================== 5. 部门报告表 ====================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,               -- 报告标题
            content TEXT,                      -- 报告内容（支持万字级）
            category TEXT,                     -- 分类：自查报告/审计报告/工作周报/工作月报等
            tags TEXT,                         -- 自定义标签
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # ==================== 6. 附件表（通用） ====================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attachments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT NOT NULL,           -- 原始文件名
            file_path TEXT NOT NULL,           -- 存储路径
            file_size INTEGER,                 -- 文件大小（字节）
            module_type TEXT NOT NULL,         -- 模块类型：todo/memo/report
            record_id INTEGER NOT NULL,        -- 关联记录ID
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # ==================== 7. 系统配置表 ====================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_type TEXT NOT NULL,         -- 配置类型：task_tag/team/person/focus_area
            config_value TEXT NOT NULL,        -- 配置值
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # ==================== 插入默认配置数据 ====================
    # 检查是否已有配置数据
    cursor.execute("SELECT COUNT(*) FROM system_config")
    if cursor.fetchone()[0] == 0:
        # 默认任务标签
        default_tags = [('task_tag', '紧急'), ('task_tag', '重要'), ('task_tag', '一般')]
        cursor.executemany("INSERT INTO system_config (config_type, config_value) VALUES (?, ?)", default_tags)
        
        # 默认团队
        default_teams = [('team', '技术部'), ('team', '产品部'), ('team', '运营部'), ('team', '市场部'), ('team', '人事部'), ('team', '财务部')]
        cursor.executemany("INSERT INTO system_config (config_type, config_value) VALUES (?, ?)", default_teams)
        
        # 默认人员
        default_persons = [('person', '张三'), ('person', '李四'), ('person', '王五'), ('person', '赵六')]
        cursor.executemany("INSERT INTO system_config (config_type, config_value) VALUES (?, ?)", default_persons)
        
        # 默认关注领域
        default_areas = [('focus_area', '项目进度'), ('focus_area', '团队建设'), ('focus_area', '业务拓展')]
        cursor.executemany("INSERT INTO system_config (config_type, config_value) VALUES (?, ?)", default_areas)
    
    conn.commit()
    conn.close()
    print("数据库初始化完成！")
    print(f"数据库文件位置: {DB_PATH}")

if __name__ == '__main__':
    init_database()