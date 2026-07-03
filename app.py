# -*- coding: utf-8 -*-
"""
本地办公工作台 - Flask主应用
包含四大核心模块：待办任务、工作备忘录、重点关注看板、部门报告库
"""
import os
import json
import shutil
import zipfile
import tempfile
import hashlib
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, jsonify, render_template, send_file, send_from_directory, session, redirect, url_for
from flask_cors import CORS
from werkzeug.utils import secure_filename
import sqlite3

# 导入配置
from config import *

# 创建Flask应用
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
app.config['SECRET_KEY'] = SECRET_KEY
CORS(app)

# 确保上传目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join(os.path.dirname(__file__), 'data'), exist_ok=True)

# ==================== 数据库工具函数 ====================
def get_db_connection():
    """获取数据库连接"""
    db_path = os.path.join(os.path.dirname(__file__), 'data', 'office.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def row_to_dict(row):
    """将sqlite3.Row对象转换为字典"""
    if row is None:
        return None
    return dict(row)

def rows_to_list(rows):
    """将sqlite3.Row列表转换为字典列表"""
    return [row_to_dict(row) for row in rows]

# ==================== 文件上传工具 ====================
def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file, module_type, record_id):
    """保存上传的文件并记录到数据库"""
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        unique_filename = f"{timestamp}_{filename}"
        
        module_dir = os.path.join(app.config['UPLOAD_FOLDER'], module_type)
        os.makedirs(module_dir, exist_ok=True)
        
        file_path = os.path.join(module_dir, unique_filename)
        file.save(file_path)
        
        file_size = os.path.getsize(file_path)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO attachments (file_name, file_path, file_size, module_type, record_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (filename, file_path, file_size, module_type, record_id))
        conn.commit()
        attachment_id = cursor.lastrowid
        conn.close()
        
        return {
            'id': attachment_id,
            'file_name': filename,
            'file_size': file_size
        }
    return None

# ==================== 密码保护装饰器 ====================
def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('authenticated'):
            return jsonify({'code': 401, 'message': '未授权，请先登录'}), 401
        return f(*args, **kwargs)
    return decorated

def check_password(password):
    """验证密码是否正确"""
    password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM system_security")
    result = cursor.fetchone()
    conn.close()
    return result and result['password_hash'] == password_hash

def update_password(new_password):
    """更新密码"""
    password_hash = hashlib.sha256(new_password.encode('utf-8')).hexdigest()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE system_security SET password_hash = ?, updated_at = CURRENT_TIMESTAMP", (password_hash,))
    conn.commit()
    conn.close()

# ==================== 页面路由 ====================
@app.route('/')
def index():
    """首页 - 展示近3天到期任务"""
    return render_template('index.html')

@app.route('/login')
def login_page():
    """登录页面"""
    return render_template('login.html')

@app.route('/todo')
def todo_page():
    """待办任务页面"""
    return render_template('todo.html')

@app.route('/memo')
def memo_page():
    """工作备忘录页面"""
    return render_template('memo.html')

@app.route('/focus')
def focus_page():
    """重点关注看板页面"""
    return render_template('focus.html')

@app.route('/report')
def report_page():
    """部门报告库页面"""
    return render_template('report.html')

@app.route('/config')
def config_page():
    """系统配置页面"""
    return render_template('config.html')

# ==================== 登录认证API ====================
@app.route('/api/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.get_json()
    password = data.get('password', '')
    
    if check_password(password):
        session['authenticated'] = True
        session.permanent = True
        return jsonify({'code': 0, 'message': '登录成功'})
    return jsonify({'code': 1, 'message': '密码错误'})

@app.route('/api/logout', methods=['POST'])
def logout():
    """用户登出"""
    session.pop('authenticated', None)
    return jsonify({'code': 0, 'message': '登出成功'})

@app.route('/api/change_password', methods=['POST'])
@requires_auth
def change_password():
    """修改密码"""
    data = request.get_json()
    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')
    
    if not check_password(old_password):
        return jsonify({'code': 1, 'message': '原密码错误'})
    
    if len(new_password) < 4:
        return jsonify({'code': 1, 'message': '新密码长度至少4位'})
    
    update_password(new_password)
    return jsonify({'code': 0, 'message': '密码修改成功'})

@app.route('/api/check_auth', methods=['GET'])
def check_auth():
    """检查登录状态"""
    if session.get('authenticated'):
        return jsonify({'code': 0, 'authenticated': True})
    return jsonify({'code': 0, 'authenticated': False})

# ==================== 待办任务API ====================
@app.route('/api/tasks', methods=['GET'])
@requires_auth
def get_tasks():
    """获取待办任务列表，支持多条件检索"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 获取查询参数
    keyword = request.args.get('keyword', '')
    tag = request.args.get('tag', '')
    team = request.args.get('team', '')
    person = request.args.get('person', '')
    deadline_start = request.args.get('deadline_start', '')
    deadline_end = request.args.get('deadline_end', '')
    status = request.args.get('status', 'active')  # 默认只显示活跃任务
    sort = request.args.get('sort', 'created_desc')  # 默认创建时间倒序
    
    # 构建SQL查询
    sql = "SELECT * FROM todo_tasks WHERE 1=1"
    params = []
    
    if keyword:
        sql += " AND (summary LIKE ? OR detail_content LIKE ? OR progress_note LIKE ?)"
        keyword_param = f"%{keyword}%"
        params.extend([keyword_param, keyword_param, keyword_param])
    
    if tag:
        sql += " AND tag = ?"
        params.append(tag)
    
    if team:
        sql += " AND assigned_team = ?"
        params.append(team)
    
    if person:
        sql += " AND assigned_person = ?"
        params.append(person)
    
    if deadline_start:
        sql += " AND deadline >= ?"
        params.append(deadline_start)
    
    if deadline_end:
        sql += " AND deadline <= ?"
        params.append(deadline_end)
    
    if status == 'active':
        sql += " AND status = '未完成'"
    elif status == 'completed':
        sql += " AND status = '已完成'"
    
    # 排序
    if sort == 'created_desc':
        sql += " ORDER BY created_at DESC"
    elif sort == 'created_asc':
        sql += " ORDER BY created_at ASC"
    elif sort == 'deadline_asc':
        sql += " ORDER BY deadline ASC"
    elif sort == 'deadline_desc':
        sql += " ORDER BY deadline DESC"
    
    cursor.execute(sql, params)
    tasks = rows_to_list(cursor.fetchall())
    
    # 为每个任务获取附件
    for task in tasks:
        cursor.execute("SELECT * FROM attachments WHERE module_type = 'todo' AND record_id = ?", (task['id'],))
        task['attachments'] = rows_to_list(cursor.fetchall())
    
    conn.close()
    return jsonify({'code': 0, 'data': tasks})

@app.route('/api/tasks/upcoming', methods=['GET'])
@requires_auth
def get_upcoming_tasks():
    """获取近5天内到期的任务（首页提醒用）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    now = datetime.now()
    five_days_later = now + timedelta(days=5)
    
    cursor.execute('''
        SELECT * FROM todo_tasks 
        WHERE status = '未完成' 
        AND deadline IS NOT NULL 
        AND deadline >= ? 
        AND deadline <= ?
        ORDER BY 
            CASE tag WHEN '紧急' THEN 1 WHEN '重要' THEN 2 WHEN '一般' THEN 3 ELSE 4 END,
            deadline ASC
    ''', (now.strftime('%Y-%m-%d %H:%M:%S'), five_days_later.strftime('%Y-%m-%d %H:%M:%S')))
    
    tasks = rows_to_list(cursor.fetchall())
    conn.close()
    return jsonify({'code': 0, 'data': tasks})

@app.route('/api/tasks', methods=['POST'])
@requires_auth
def create_task():
    """创建待办任务"""
    data = request.get_json()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO todo_tasks (summary, detail_content, deadline, assigned_team, assigned_person, progress_note, tag, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data.get('summary'),
        data.get('detail_content'),
        data.get('deadline'),
        data.get('assigned_team'),
        data.get('assigned_person'),
        data.get('progress_note'),
        data.get('tag', '一般'),
        data.get('status', '未完成')
    ))
    conn.commit()
    task_id = cursor.lastrowid
    conn.close()
    
    return jsonify({'code': 0, 'message': '创建成功', 'data': {'id': task_id}})

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
@requires_auth
def update_task(task_id):
    """更新待办任务"""
    data = request.get_json()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 构建更新SQL
    update_fields = []
    params = []
    
    for field in ['summary', 'detail_content', 'deadline', 'assigned_team', 'assigned_person', 'progress_note', 'tag', 'status']:
        if field in data:
            update_fields.append(f"{field} = ?")
            params.append(data[field])
    
    if update_fields:
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        sql = f"UPDATE todo_tasks SET {', '.join(update_fields)} WHERE id = ?"
        params.append(task_id)
        cursor.execute(sql, params)
        conn.commit()
    
    conn.close()
    return jsonify({'code': 0, 'message': '更新成功'})

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
@requires_auth
def delete_task(task_id):
    """删除待办任务"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 删除关联附件
    cursor.execute("SELECT file_path FROM attachments WHERE module_type = 'todo' AND record_id = ?", (task_id,))
    attachments = cursor.fetchall()
    for att in attachments:
        if os.path.exists(att['file_path']):
            os.remove(att['file_path'])
    
    cursor.execute("DELETE FROM attachments WHERE module_type = 'todo' AND record_id = ?", (task_id,))
    cursor.execute("DELETE FROM todo_tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'code': 0, 'message': '删除成功'})

@app.route('/api/tasks/<int:task_id>/complete', methods=['POST'])
@requires_auth
def complete_task(task_id):
    """完成任务"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE todo_tasks SET status = '已完成', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    return jsonify({'code': 0, 'message': '任务已完成'})

@app.route('/api/tasks/<int:task_id>/attachments', methods=['POST'])
@requires_auth
def upload_task_attachment(task_id):
    """上传任务附件"""
    if 'file' not in request.files:
        return jsonify({'code': 1, 'message': '没有上传文件'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'code': 1, 'message': '没有选择文件'})
    
    result = save_uploaded_file(file, 'todo', task_id)
    if result:
        return jsonify({'code': 0, 'message': '上传成功', 'data': result})
    return jsonify({'code': 1, 'message': '文件类型不支持'})

@app.route('/api/tasks/<int:task_id>/attachments', methods=['GET'])
@requires_auth
def get_task_attachments(task_id):
    """获取任务附件列表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM attachments WHERE module_type = 'todo' AND record_id = ?", (task_id,))
    attachments = rows_to_list(cursor.fetchall())
    conn.close()
    return jsonify({'code': 0, 'data': attachments})

@app.route('/api/attachments/<int:attachment_id>/download', methods=['GET'])
@requires_auth
def download_attachment(attachment_id):
    """下载附件"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM attachments WHERE id = ?", (attachment_id,))
    attachment = cursor.fetchone()
    conn.close()
    
    if attachment and os.path.exists(attachment['file_path']):
        return send_file(attachment['file_path'], as_attachment=True, download_name=attachment['file_name'])
    return jsonify({'code': 1, 'message': '文件不存在'})

@app.route('/api/attachments/<int:attachment_id>', methods=['DELETE'])
@requires_auth
def delete_attachment(attachment_id):
    """删除附件"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM attachments WHERE id = ?", (attachment_id,))
    attachment = cursor.fetchone()
    
    if attachment:
        if os.path.exists(attachment['file_path']):
            os.remove(attachment['file_path'])
        cursor.execute("DELETE FROM attachments WHERE id = ?", (attachment_id,))
        conn.commit()
    
    conn.close()
    return jsonify({'code': 0, 'message': '删除成功'})

# ==================== 工作备忘录API ====================
@app.route('/api/memos', methods=['GET'])
@requires_auth
def get_memos():
    """获取备忘录列表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    keyword = request.args.get('keyword', '')
    tags = request.args.get('tags', '')
    
    sql = "SELECT * FROM memos WHERE 1=1"
    params = []
    
    if keyword:
        sql += " AND (title LIKE ? OR content LIKE ?)"
        keyword_param = f"%{keyword}%"
        params.extend([keyword_param, keyword_param])
    
    if tags:
        sql += " AND tags LIKE ?"
        params.append(f"%{tags}%")
    
    sql += " ORDER BY created_at DESC"
    
    cursor.execute(sql, params)
    memos = rows_to_list(cursor.fetchall())
    
    # 获取附件
    for memo in memos:
        cursor.execute("SELECT * FROM attachments WHERE module_type = 'memo' AND record_id = ?", (memo['id'],))
        memo['attachments'] = rows_to_list(cursor.fetchall())
    
    conn.close()
    return jsonify({'code': 0, 'data': memos})

@app.route('/api/memos', methods=['POST'])
@requires_auth
def create_memo():
    """创建备忘录"""
    data = request.get_json()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO memos (title, content, tags)
        VALUES (?, ?, ?)
    ''', (data.get('title'), data.get('content'), data.get('tags', '')))
    conn.commit()
    memo_id = cursor.lastrowid
    conn.close()
    
    return jsonify({'code': 0, 'message': '创建成功', 'data': {'id': memo_id}})

@app.route('/api/memos/<int:memo_id>', methods=['PUT'])
@requires_auth
def update_memo(memo_id):
    """更新备忘录"""
    data = request.get_json()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    update_fields = []
    params = []
    
    for field in ['title', 'content', 'tags']:
        if field in data:
            update_fields.append(f"{field} = ?")
            params.append(data[field])
    
    if update_fields:
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        sql = f"UPDATE memos SET {', '.join(update_fields)} WHERE id = ?"
        params.append(memo_id)
        cursor.execute(sql, params)
        conn.commit()
    
    conn.close()
    return jsonify({'code': 0, 'message': '更新成功'})

@app.route('/api/memos/<int:memo_id>', methods=['DELETE'])
@requires_auth
def delete_memo(memo_id):
    """删除备忘录"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 删除关联附件
    cursor.execute("SELECT file_path FROM attachments WHERE module_type = 'memo' AND record_id = ?", (memo_id,))
    attachments = cursor.fetchall()
    for att in attachments:
        if os.path.exists(att['file_path']):
            os.remove(att['file_path'])
    
    cursor.execute("DELETE FROM attachments WHERE module_type = 'memo' AND record_id = ?", (memo_id,))
    cursor.execute("DELETE FROM memos WHERE id = ?", (memo_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'code': 0, 'message': '删除成功'})

@app.route('/api/memos/<int:memo_id>/attachments', methods=['POST'])
@requires_auth
def upload_memo_attachment(memo_id):
    """上传备忘录附件"""
    if 'file' not in request.files:
        return jsonify({'code': 1, 'message': '没有上传文件'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'code': 1, 'message': '没有选择文件'})
    
    result = save_uploaded_file(file, 'memo', memo_id)
    if result:
        return jsonify({'code': 0, 'message': '上传成功', 'data': result})
    return jsonify({'code': 1, 'message': '文件类型不支持'})

@app.route('/api/memos/<int:memo_id>/attachments', methods=['GET'])
@requires_auth
def get_memo_attachments(memo_id):
    """获取备忘录附件列表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM attachments WHERE module_type = 'memo' AND record_id = ?", (memo_id,))
    attachments = rows_to_list(cursor.fetchall())
    conn.close()
    return jsonify({'code': 0, 'data': attachments})

# ==================== 重点关注看板API ====================
@app.route('/api/focus/areas', methods=['GET'])
@requires_auth
def get_focus_areas():
    """获取所有关注领域"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM focus_areas ORDER BY created_at DESC")
    areas = rows_to_list(cursor.fetchall())
    conn.close()
    return jsonify({'code': 0, 'data': areas})

@app.route('/api/focus/areas', methods=['POST'])
@requires_auth
def create_focus_area():
    """创建关注领域"""
    data = request.get_json()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO focus_areas (name, description) VALUES (?, ?)", 
                   (data.get('name'), data.get('description', '')))
    conn.commit()
    area_id = cursor.lastrowid
    conn.close()
    
    return jsonify({'code': 0, 'message': '创建成功', 'data': {'id': area_id}})

@app.route('/api/focus/areas/<int:area_id>', methods=['PUT'])
@requires_auth
def update_focus_area(area_id):
    """更新关注领域"""
    data = request.get_json()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE focus_areas SET name = ?, description = ? WHERE id = ?",
                   (data.get('name'), data.get('description', ''), area_id))
    conn.commit()
    conn.close()
    
    return jsonify({'code': 0, 'message': '更新成功'})

@app.route('/api/focus/areas/<int:area_id>', methods=['DELETE'])
@requires_auth
def delete_focus_area(area_id):
    """删除关注领域及其事项"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 删除关联事项
    cursor.execute("DELETE FROM focus_items WHERE area_id = ?", (area_id,))
    cursor.execute("DELETE FROM focus_areas WHERE id = ?", (area_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'code': 0, 'message': '删除成功'})

@app.route('/api/focus/items', methods=['GET'])
@requires_auth
def get_focus_items():
    """获取关注事项列表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    area_id = request.args.get('area_id', '')
    keyword = request.args.get('keyword', '')
    status = request.args.get('status', '')
    
    sql = '''
        SELECT fi.*, fa.name as area_name 
        FROM focus_items fi 
        LEFT JOIN focus_areas fa ON fi.area_id = fa.id 
        WHERE 1=1
    '''
    params = []
    
    if area_id:
        sql += " AND fi.area_id = ?"
        params.append(area_id)
    
    if keyword:
        sql += " AND (fi.title LIKE ? OR fi.note LIKE ?)"
        keyword_param = f"%{keyword}%"
        params.extend([keyword_param, keyword_param])
    
    if status:
        sql += " AND fi.status = ?"
        params.append(status)
    
    # 过滤完成超过1个月的事项
    one_month_ago = datetime.now() - timedelta(days=30)
    sql += " AND (fi.status != '完成' OR fi.completed_at IS NULL OR fi.completed_at >= ?)"
    params.append(one_month_ago.strftime('%Y-%m-%d %H:%M:%S'))
    
    sql += " ORDER BY fi.created_at DESC"
    
    cursor.execute(sql, params)
    items = rows_to_list(cursor.fetchall())
    conn.close()
    
    return jsonify({'code': 0, 'data': items})

@app.route('/api/focus/items', methods=['POST'])
@requires_auth
def create_focus_item():
    """创建关注事项"""
    data = request.get_json()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO focus_items (area_id, title, note, planned_date, status)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        data.get('area_id'),
        data.get('title'),
        data.get('note', ''),
        data.get('planned_date'),
        data.get('status', '未开始')
    ))
    conn.commit()
    item_id = cursor.lastrowid
    conn.close()
    
    return jsonify({'code': 0, 'message': '创建成功', 'data': {'id': item_id}})

@app.route('/api/focus/items/<int:item_id>', methods=['PUT'])
@requires_auth
def update_focus_item(item_id):
    """更新关注事项"""
    data = request.get_json()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    update_fields = []
    params = []
    
    for field in ['area_id', 'title', 'note', 'planned_date', 'status']:
        if field in data:
            update_fields.append(f"{field} = ?")
            params.append(data[field])
    
    # 如果状态改为完成，记录完成时间
    if data.get('status') == '完成':
        update_fields.append("completed_at = CURRENT_TIMESTAMP")
    
    if update_fields:
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        sql = f"UPDATE focus_items SET {', '.join(update_fields)} WHERE id = ?"
        params.append(item_id)
        cursor.execute(sql, params)
        conn.commit()
    
    conn.close()
    return jsonify({'code': 0, 'message': '更新成功'})

@app.route('/api/focus/items/<int:item_id>', methods=['DELETE'])
@requires_auth
def delete_focus_item(item_id):
    """删除关注事项"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM focus_items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'code': 0, 'message': '删除成功'})

@app.route('/api/focus/kanban', methods=['GET'])
@requires_auth
def get_focus_kanban():
    """获取看板数据（按领域分组）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 获取所有领域
    cursor.execute("SELECT * FROM focus_areas ORDER BY created_at DESC")
    areas = rows_to_list(cursor.fetchall())
    
    # 过滤完成超过1个月的事项
    one_month_ago = datetime.now() - timedelta(days=30)
    
    # 为每个领域获取事项
    for area in areas:
        cursor.execute('''
            SELECT * FROM focus_items 
            WHERE area_id = ? 
            AND (status != '完成' OR completed_at IS NULL OR completed_at >= ?)
            ORDER BY created_at DESC
        ''', (area['id'], one_month_ago.strftime('%Y-%m-%d %H:%M:%S')))
        area['items'] = rows_to_list(cursor.fetchall())
    
    conn.close()
    return jsonify({'code': 0, 'data': areas})

# ==================== 部门报告库API ====================
@app.route('/api/reports', methods=['GET'])
@requires_auth
def get_reports():
    """获取报告列表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    keyword = request.args.get('keyword', '')
    category = request.args.get('category', '')
    tags = request.args.get('tags', '')
    
    sql = "SELECT * FROM reports WHERE 1=1"
    params = []
    
    if keyword:
        sql += " AND (title LIKE ? OR content LIKE ?)"
        keyword_param = f"%{keyword}%"
        params.extend([keyword_param, keyword_param])
    
    if category:
        sql += " AND category = ?"
        params.append(category)
    
    if tags:
        sql += " AND tags LIKE ?"
        params.append(f"%{tags}%")
    
    sql += " ORDER BY created_at DESC"
    
    cursor.execute(sql, params)
    reports = rows_to_list(cursor.fetchall())
    conn.close()
    
    return jsonify({'code': 0, 'data': reports})

@app.route('/api/reports', methods=['POST'])
@requires_auth
def create_report():
    """创建报告"""
    data = request.get_json()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO reports (title, content, category, tags)
        VALUES (?, ?, ?, ?)
    ''', (data.get('title'), data.get('content'), data.get('category', ''), data.get('tags', '')))
    conn.commit()
    report_id = cursor.lastrowid
    conn.close()
    
    return jsonify({'code': 0, 'message': '创建成功', 'data': {'id': report_id}})

@app.route('/api/reports/<int:report_id>', methods=['PUT'])
@requires_auth
def update_report(report_id):
    """更新报告"""
    data = request.get_json()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    update_fields = []
    params = []
    
    for field in ['title', 'content', 'category', 'tags']:
        if field in data:
            update_fields.append(f"{field} = ?")
            params.append(data[field])
    
    if update_fields:
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        sql = f"UPDATE reports SET {', '.join(update_fields)} WHERE id = ?"
        params.append(report_id)
        cursor.execute(sql, params)
        conn.commit()
    
    conn.close()
    return jsonify({'code': 0, 'message': '更新成功'})

@app.route('/api/reports/<int:report_id>', methods=['DELETE'])
@requires_auth
def delete_report(report_id):
    """删除报告"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM reports WHERE id = ?", (report_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'code': 0, 'message': '删除成功'})

# ==================== 系统配置API ====================
@app.route('/api/config', methods=['GET'])
@requires_auth
def get_config():
    """获取系统配置"""
    config_type = request.args.get('type', '')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if config_type:
        cursor.execute("SELECT * FROM system_config WHERE config_type = ? ORDER BY id", (config_type,))
    else:
        cursor.execute("SELECT * FROM system_config ORDER BY config_type, id")
    
    configs = rows_to_list(cursor.fetchall())
    conn.close()
    
    return jsonify({'code': 0, 'data': configs})

@app.route('/api/config', methods=['POST'])
@requires_auth
def add_config():
    """添加配置项"""
    data = request.get_json()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO system_config (config_type, config_value) VALUES (?, ?)",
                   (data.get('config_type'), data.get('config_value')))
    conn.commit()
    config_id = cursor.lastrowid
    conn.close()
    
    return jsonify({'code': 0, 'message': '添加成功', 'data': {'id': config_id}})

@app.route('/api/config/<int:config_id>', methods=['PUT'])
@requires_auth
def update_config(config_id):
    """更新配置项"""
    data = request.get_json()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE system_config SET config_value = ? WHERE id = ?",
                   (data.get('config_value'), config_id))
    conn.commit()
    conn.close()
    
    return jsonify({'code': 0, 'message': '更新成功'})

@app.route('/api/config/<int:config_id>', methods=['DELETE'])
@requires_auth
def delete_config(config_id):
    """删除配置项"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM system_config WHERE id = ?", (config_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'code': 0, 'message': '删除成功'})

# ==================== 数据导入导出API ====================
@app.route('/api/export/all', methods=['GET'])
@requires_auth
def export_all_data():
    """导出所有数据"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    export_data = {
        'export_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'todo_tasks': [],
        'memos': [],
        'focus_areas': [],
        'focus_items': [],
        'reports': [],
        'system_config': []
    }
    
    # 导出各表数据
    cursor.execute("SELECT * FROM todo_tasks")
    export_data['todo_tasks'] = rows_to_list(cursor.fetchall())
    
    cursor.execute("SELECT * FROM memos")
    export_data['memos'] = rows_to_list(cursor.fetchall())
    
    cursor.execute("SELECT * FROM focus_areas")
    export_data['focus_areas'] = rows_to_list(cursor.fetchall())
    
    cursor.execute("SELECT * FROM focus_items")
    export_data['focus_items'] = rows_to_list(cursor.fetchall())
    
    cursor.execute("SELECT * FROM reports")
    export_data['reports'] = rows_to_list(cursor.fetchall())
    
    cursor.execute("SELECT * FROM system_config")
    export_data['system_config'] = rows_to_list(cursor.fetchall())
    
    conn.close()
    
    # 创建临时文件
    temp_dir = tempfile.mkdtemp()
    json_file = os.path.join(temp_dir, 'data_export.json')
    
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)
    
    # 复制附件到导出目录
    attachments_dir = os.path.join(temp_dir, 'attachments')
    os.makedirs(attachments_dir, exist_ok=True)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM attachments")
    attachments = cursor.fetchall()
    conn.close()
    
    attachment_info = []
    for att in attachments:
        att_dict = row_to_dict(att)
        if os.path.exists(att['file_path']):
            # 创建带标识的文件名：模块类型_记录ID_原始文件名
            new_name = f"{att['module_type']}_{att['record_id']}_{att['file_name']}"
            dest_path = os.path.join(attachments_dir, new_name)
            shutil.copy2(att['file_path'], dest_path)
            att_dict['export_file_name'] = new_name
            attachment_info.append(att_dict)
    
    # 保存附件信息
    with open(os.path.join(temp_dir, 'attachments_info.json'), 'w', encoding='utf-8') as f:
        json.dump(attachment_info, f, ensure_ascii=False, indent=2)
    
    # 创建ZIP文件
    zip_path = os.path.join(tempfile.gettempdir(), f'office_export_{datetime.now().strftime("%Y%m%d%H%M%S")}.zip')
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(json_file, 'data_export.json')
        zipf.write(os.path.join(temp_dir, 'attachments_info.json'), 'attachments_info.json')
        for root, dirs, files in os.walk(attachments_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.join('attachments', file)
                zipf.write(file_path, arcname)
    
    # 清理临时目录
    shutil.rmtree(temp_dir)
    
    return send_file(zip_path, as_attachment=True, download_name=f'office_export_{datetime.now().strftime("%Y%m%d%H%M%S")}.zip')

@app.route('/api/import/all', methods=['POST'])
@requires_auth
def import_all_data():
    """导入所有数据"""
    if 'file' not in request.files:
        return jsonify({'code': 1, 'message': '没有上传文件'})
    
    file = request.files['file']
    if not file.filename.endswith('.zip'):
        return jsonify({'code': 1, 'message': '请上传ZIP格式的导出文件'})
    
    # 解压文件
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, 'upload.zip')
    file.save(zip_path)
    
    with zipfile.ZipFile(zip_path, 'r') as zipf:
        zipf.extractall(temp_dir)
    
    # 读取数据文件
    json_file = os.path.join(temp_dir, 'data_export.json')
    if not os.path.exists(json_file):
        shutil.rmtree(temp_dir)
        return jsonify({'code': 1, 'message': '无效的导出文件格式'})
    
    with open(json_file, 'r', encoding='utf-8') as f:
        import_data = json.load(f)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 清空现有数据
        cursor.execute("DELETE FROM todo_tasks")
        cursor.execute("DELETE FROM memos")
        cursor.execute("DELETE FROM focus_areas")
        cursor.execute("DELETE FROM focus_items")
        cursor.execute("DELETE FROM reports")
        cursor.execute("DELETE FROM system_config")
        cursor.execute("DELETE FROM attachments")
        
        # 导入数据
        for task in import_data.get('todo_tasks', []):
            cursor.execute('''
                INSERT INTO todo_tasks (id, summary, detail_content, deadline, assigned_team, assigned_person, progress_note, tag, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (task['id'], task['summary'], task['detail_content'], task['deadline'], task['assigned_team'], 
                  task['assigned_person'], task['progress_note'], task['tag'], task['status'], task['created_at'], task['updated_at']))
        
        for memo in import_data.get('memos', []):
            cursor.execute('''
                INSERT INTO memos (id, title, content, tags, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (memo['id'], memo['title'], memo['content'], memo['tags'], memo['created_at'], memo['updated_at']))
        
        for area in import_data.get('focus_areas', []):
            cursor.execute('''
                INSERT INTO focus_areas (id, name, description, created_at)
                VALUES (?, ?, ?, ?)
            ''', (area['id'], area['name'], area['description'], area['created_at']))
        
        for item in import_data.get('focus_items', []):
            cursor.execute('''
                INSERT INTO focus_items (id, area_id, title, note, planned_date, status, completed_at, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (item['id'], item['area_id'], item['title'], item['note'], item['planned_date'], 
                  item['status'], item['completed_at'], item['created_at'], item['updated_at']))
        
        for report in import_data.get('reports', []):
            cursor.execute('''
                INSERT INTO reports (id, title, content, category, tags, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (report['id'], report['title'], report['content'], report['category'], report['tags'], 
                  report['created_at'], report['updated_at']))
        
        for config in import_data.get('system_config', []):
            cursor.execute('''
                INSERT INTO system_config (id, config_type, config_value, created_at)
                VALUES (?, ?, ?, ?)
            ''', (config['id'], config['config_type'], config['config_value'], config['created_at']))
        
        # 导入附件
        attachments_info_file = os.path.join(temp_dir, 'attachments_info.json')
        if os.path.exists(attachments_info_file):
            with open(attachments_info_file, 'r', encoding='utf-8') as f:
                attachments_info = json.load(f)
            
            for att in attachments_info:
                src_file = os.path.join(temp_dir, 'attachments', att['export_file_name'])
                if os.path.exists(src_file):
                    # 复制到上传目录
                    module_dir = os.path.join(app.config['UPLOAD_FOLDER'], att['module_type'])
                    os.makedirs(module_dir, exist_ok=True)
                    dest_file = os.path.join(module_dir, f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{att['file_name']}")
                    shutil.copy2(src_file, dest_file)
                    
                    cursor.execute('''
                        INSERT INTO attachments (id, file_name, file_path, file_size, module_type, record_id, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (att['id'], att['file_name'], dest_file, att['file_size'], att['module_type'], att['record_id'], att['created_at']))
        
        conn.commit()
        shutil.rmtree(temp_dir)
        return jsonify({'code': 0, 'message': '数据导入成功'})
    
    except Exception as e:
        conn.rollback()
        shutil.rmtree(temp_dir)
        return jsonify({'code': 1, 'message': f'导入失败: {str(e)}'})

@app.route('/api/export/attachments', methods=['GET'])
@requires_auth
def export_attachments():
    """批量导出附件"""
    temp_dir = tempfile.mkdtemp()
    attachments_dir = os.path.join(temp_dir, 'attachments')
    os.makedirs(attachments_dir, exist_ok=True)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM attachments")
    attachments = cursor.fetchall()
    conn.close()
    
    attachment_info = []
    for att in attachments:
        att_dict = row_to_dict(att)
        if os.path.exists(att['file_path']):
            # 创建带标识的文件名
            new_name = f"{att['module_type']}_{att['record_id']}_{att['file_name']}"
            dest_path = os.path.join(attachments_dir, new_name)
            shutil.copy2(att['file_path'], dest_path)
            att_dict['export_file_name'] = new_name
            attachment_info.append(att_dict)
    
    # 保存附件信息
    with open(os.path.join(temp_dir, 'attachments_info.json'), 'w', encoding='utf-8') as f:
        json.dump(attachment_info, f, ensure_ascii=False, indent=2)
    
    # 创建ZIP文件
    zip_path = os.path.join(tempfile.gettempdir(), f'attachments_export_{datetime.now().strftime("%Y%m%d%H%M%S")}.zip')
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(os.path.join(temp_dir, 'attachments_info.json'), 'attachments_info.json')
        for root, dirs, files in os.walk(attachments_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.join('attachments', file)
                zipf.write(file_path, arcname)
    
    shutil.rmtree(temp_dir)
    
    return send_file(zip_path, as_attachment=True, download_name=f'attachments_export_{datetime.now().strftime("%Y%m%d%H%M%S")}.zip')

# ==================== 静态文件服务 ====================
@app.route('/static/<path:filename>')
def serve_static(filename):
    """提供静态文件"""
    return send_from_directory(os.path.join(os.path.dirname(__file__), 'static'), filename)

# ==================== 报告附件API ====================
@app.route('/api/reports/<int:report_id>/attachments', methods=['POST'])
@requires_auth
def upload_report_attachment(report_id):
    """上传报告附件"""
    if 'file' not in request.files:
        return jsonify({'code': 1, 'message': '没有上传文件'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'code': 1, 'message': '没有选择文件'})
    
    result = save_uploaded_file(file, 'report', report_id)
    if result:
        return jsonify({'code': 0, 'message': '上传成功', 'data': result})
    return jsonify({'code': 1, 'message': '文件类型不支持'})

@app.route('/api/reports/<int:report_id>/attachments', methods=['GET'])
@requires_auth
def get_report_attachments(report_id):
    """获取报告附件列表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM attachments WHERE module_type = 'report' AND record_id = ?", (report_id,))
    attachments = rows_to_list(cursor.fetchall())
    conn.close()
    return jsonify({'code': 0, 'data': attachments})

# ==================== 文本汇总导出API ====================
@app.route('/api/export/text_summary', methods=['GET'])
@requires_auth
def export_text_summary():
    """导出文本汇总（待办任务+备忘录+重点关注+报告清单）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    lines = []
    lines.append("=" * 60)
    lines.append("本地办公工作台数据导出")
    lines.append("导出时间: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    lines.append("=" * 60)
    
    # 待办任务
    cursor.execute("SELECT * FROM todo_tasks ORDER BY created_at DESC")
    tasks = rows_to_list(cursor.fetchall())
    lines.append("")
    lines.append("=" * 60)
    lines.append(f"待办任务 (共{len(tasks)}条)")
    lines.append("=" * 60)
    for task in tasks:
        lines.append("")
        lines.append(f"--- 任务ID: {task['id']} ---")
        lines.append(f"摘要: {task['summary'] or ''}")
        lines.append(f"详细内容: {task['detail_content'] or ''}")
        lines.append(f"截止时间: {task['deadline'] or ''}")
        lines.append(f"指派团队: {task['assigned_team'] or ''}")
        lines.append(f"指派个人: {task['assigned_person'] or ''}")
        lines.append(f"进度备注: {task['progress_note'] or ''}")
        lines.append(f"标签: {task['tag'] or ''}")
        lines.append(f"状态: {task['status'] or ''}")
        lines.append(f"创建时间: {task['created_at'] or ''}")
    
    # 工作备忘录
    cursor.execute("SELECT * FROM memos ORDER BY created_at DESC")
    memos = rows_to_list(cursor.fetchall())
    lines.append("")
    lines.append("=" * 60)
    lines.append(f"工作备忘录 (共{len(memos)}条)")
    lines.append("=" * 60)
    for memo in memos:
        lines.append("")
        lines.append(f"--- 备忘录ID: {memo['id']} ---")
        lines.append(f"标题: {memo['title'] or ''}")
        lines.append(f"正文内容: {memo['content'] or ''}")
        lines.append(f"标签: {memo['tags'] or ''}")
        lines.append(f"创建时间: {memo['created_at'] or ''}")
    
    # 重点关注
    cursor.execute('''
        SELECT fi.*, fa.name as area_name 
        FROM focus_items fi 
        LEFT JOIN focus_areas fa ON fi.area_id = fa.id 
        ORDER BY fi.created_at DESC
    ''')
    focus_items = rows_to_list(cursor.fetchall())
    lines.append("")
    lines.append("=" * 60)
    lines.append(f"重点关注 (共{len(focus_items)}条)")
    lines.append("=" * 60)
    for item in focus_items:
        lines.append("")
        lines.append(f"--- 关注ID: {item['id']} ---")
        lines.append(f"标题: {item['title'] or ''}")
        lines.append(f"备注: {item['note'] or ''}")
        lines.append(f"计划完成时间: {item['planned_date'] or ''}")
        lines.append(f"状态: {item['status'] or ''}")
        lines.append(f"所属领域: {item['area_name'] or ''}")
        lines.append(f"创建时间: {item['created_at'] or ''}")
    
    # 部门报告清单（不含正文）
    cursor.execute("SELECT id, title, category, tags, created_at FROM reports ORDER BY created_at DESC")
    reports = rows_to_list(cursor.fetchall())
    lines.append("")
    lines.append("=" * 60)
    lines.append(f"部门报告清单 (共{len(reports)}条)")
    lines.append("=" * 60)
    for report in reports:
        lines.append("")
        lines.append(f"--- 报告ID: {report['id']} ---")
        lines.append(f"标题: {report['title'] or ''}")
        lines.append(f"分类: {report['category'] or ''}")
        lines.append(f"标签: {report['tags'] or ''}")
        lines.append(f"创建时间: {report['created_at'] or ''}")
    
    lines.append("")
    lines.append("=" * 60)
    lines.append("导出结束")
    lines.append("=" * 60)
    
    conn.close()
    
    content = '\n'.join(lines)
    temp_file = os.path.join(tempfile.gettempdir(), f'text_summary_{datetime.now().strftime("%Y%m%d%H%M%S")}.txt')
    with open(temp_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return send_file(temp_file, as_attachment=True, download_name=f'text_summary_{datetime.now().strftime("%Y%m%d%H%M%S")}.txt')

# ==================== 主程序入口 ====================
if __name__ == '__main__':
    # 初始化数据库
    from init_db import init_database
    init_database()
    
    # SSL证书检查
    ssl_context = None
    ssl_mode = "HTTP"
    
    if os.path.exists(SSL_CERT) and os.path.exists(SSL_KEY):
        ssl_context = (SSL_CERT, SSL_KEY)
        ssl_mode = "HTTPS"
        print("=" * 50)
        print("检测到SSL证书，将使用HTTPS加密传输")
        print("=" * 50)
    else:
        print("=" * 50)
        print("警告：未检测到SSL证书，将使用HTTP明文传输")
        print("如需启用HTTPS，请先生成SSL证书")
        print("=" * 50)
    
    # 启动应用
    print("=" * 50)
    print("本地办公工作台启动中...")
    print(f"访问地址: {ssl_mode}://localhost:5000")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True, ssl_context=ssl_context)