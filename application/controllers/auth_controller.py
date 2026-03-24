# application/controllers/auth_controller.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import re
from datetime import datetime

from application.models.user import User
from application.services.database_service import DatabaseService
from application.utils.validators import validate_email, validate_password, validate_username
from application.extensions import csrf

auth_bp = Blueprint('auth', __name__)
db = DatabaseService()


@auth_bp.route('/login', methods=['GET', 'POST'])
@csrf.exempt
def login():
    """Trang đăng nhập"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'GET':
        return render_template('auth/login.html')
    
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    remember = request.form.get('remember', False)
    
    if not username or not password:
        flash('Vui lòng nhập đầy đủ thông tin', 'danger')
        return render_template('auth/login.html')
    
    # Tìm user theo username hoặc email
    query = "SELECT * FROM users WHERE (username = %s OR email = %s) AND is_active = TRUE"
    user_data, error = db.execute_query(query, (username, username), fetch_one=True)
    
    if error or not user_data:
        flash('Tên đăng nhập hoặc mật khẩu không đúng', 'danger')
        return render_template('auth/login.html')
    
    # Kiểm tra mật khẩu
    if not check_password_hash(user_data['password_hash'], password):
        flash('Tên đăng nhập hoặc mật khẩu không đúng', 'danger')
        return render_template('auth/login.html')
    
    # Tạo user object và đăng nhập
    user = User(user_data)
    login_user(user, remember=remember)
    
    # Cập nhật last_login
    db.execute_query("UPDATE users SET last_login = NOW() WHERE id = %s", (user.id,))
    
    flash(f'Chào mừng {user.full_name or user.username} đã quay trở lại!', 'success')
    
    next_page = request.args.get('next')
    if next_page:
        return redirect(next_page)
    return redirect(url_for('main.index'))


@auth_bp.route('/register', methods=['GET', 'POST'])
@csrf.exempt
def register():
    """Trang đăng ký"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'GET':
        return render_template('auth/register.html')
    
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')
    confirm_password = request.form.get('confirm_password', '')
    full_name = request.form.get('full_name', '').strip()
    
    # Validation
    errors = []
    
    valid, msg = validate_username(username)
    if not valid:
        errors.append(msg)
    
    if not email:
        errors.append('Vui lòng nhập email')
    elif not validate_email(email):
        errors.append('Email không hợp lệ')
    
    valid, msg = validate_password(password)
    if not valid:
        errors.append(msg)
    
    if password != confirm_password:
        errors.append('Mật khẩu xác nhận không khớp')
    
    if errors:
        for error in errors:
            flash(error, 'danger')
        return render_template('auth/register.html', form_data=request.form)
    
    # Kiểm tra username/email đã tồn tại
    check_query = "SELECT id FROM users WHERE username = %s OR email = %s"
    existing, _ = db.execute_query(check_query, (username, email))
    
    if existing:
        if existing[0]['username'] == username:
            flash('Tên đăng nhập đã tồn tại', 'danger')
        else:
            flash('Email đã được đăng ký', 'danger')
        return render_template('auth/register.html')
    
    # Tạo user mới
    password_hash = generate_password_hash(password)
    query = """
        INSERT INTO users (username, email, password_hash, full_name, role_id)
        VALUES (%s, %s, %s, %s, 2)
    """
    _, error = db.execute_query(query, (username, email, password_hash, full_name))
    
    if error:
        flash('Có lỗi xảy ra, vui lòng thử lại', 'danger')
        return render_template('auth/register.html')
    
    flash('Đăng ký thành công! Vui lòng đăng nhập', 'success')
    return redirect(url_for('auth.login'))


@auth_bp.route('/logout')
@login_required
def logout():
    """Đăng xuất"""
    logout_user()
    session.clear()
    flash('Đã đăng xuất thành công', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/profile')
@login_required
def profile():
    """Trang cá nhân"""
    return render_template('auth/profile.html', user=current_user)


@auth_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Chỉnh sửa thông tin cá nhân"""
    if request.method == 'GET':
        return render_template('auth/profile_edit.html', user=current_user)
    
    full_name = request.form.get('full_name', '').strip()
    email = request.form.get('email', '').strip()
    
    if not email:
        flash('Vui lòng nhập email', 'danger')
        return render_template('auth/profile_edit.html', user=current_user)
    
    if not validate_email(email):
        flash('Email không hợp lệ', 'danger')
        return render_template('auth/profile_edit.html', user=current_user)
    
    # Kiểm tra email trùng
    check_query = "SELECT id FROM users WHERE email = %s AND id != %s"
    existing, _ = db.execute_query(check_query, (email, current_user.id))
    
    if existing:
        flash('Email đã được sử dụng bởi tài khoản khác', 'danger')
        return render_template('auth/profile_edit.html', user=current_user)
    
    query = "UPDATE users SET full_name = %s, email = %s WHERE id = %s"
    _, error = db.execute_query(query, (full_name, email, current_user.id))
    
    if error:
        flash('Có lỗi xảy ra, vui lòng thử lại', 'danger')
    else:
        flash('Cập nhật thông tin thành công!', 'success')
    
    return redirect(url_for('auth.profile'))


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Đổi mật khẩu"""
    if request.method == 'GET':
        return render_template('auth/change_password.html')
    
    current_password = request.form.get('current_password', '')
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')
    
    # Lấy mật khẩu hiện tại
    query = "SELECT password_hash FROM users WHERE id = %s"
    user_data, _ = db.execute_query(query, (current_user.id,), fetch_one=True)
    
    if not user_data or not check_password_hash(user_data['password_hash'], current_password):
        flash('Mật khẩu hiện tại không đúng', 'danger')
        return render_template('auth/change_password.html')
    
    valid, msg = validate_password(new_password)
    if not valid:
        flash(msg, 'danger')
        return render_template('auth/change_password.html')
    
    if new_password != confirm_password:
        flash('Mật khẩu xác nhận không khớp', 'danger')
        return render_template('auth/change_password.html')
    
    new_password_hash = generate_password_hash(new_password)
    update_query = "UPDATE users SET password_hash = %s WHERE id = %s"
    _, error = db.execute_query(update_query, (new_password_hash, current_user.id))
    
    if error:
        flash('Có lỗi xảy ra, vui lòng thử lại', 'danger')
    else:
        flash('Đổi mật khẩu thành công!', 'success')
    
    return redirect(url_for('auth.profile'))