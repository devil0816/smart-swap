from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from extensions import db
from models import User, Skill, UserSkill, ExchangeRequest, Review, Report, Notification
from forms import QuickCreateSkillForm, SKILL_CATEGORIES

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Access restricted to platform administrators.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/')
@admin_bp.route('')
@login_required
@admin_required
def dashboard():
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active_account=True).count()
    banned_users = User.query.filter_by(is_active_account=False).count()

    total_skills = Skill.query.count()
    total_user_skills = UserSkill.query.count()
    total_teaching = UserSkill.query.filter_by(skill_type='teach').count()
    total_learning = UserSkill.query.filter_by(skill_type='learn').count()

    total_exchanges = ExchangeRequest.query.count()
    pending_exchanges = ExchangeRequest.query.filter_by(status='pending').count()
    active_exchanges = ExchangeRequest.query.filter_by(status='accepted').count()
    completed_exchanges = ExchangeRequest.query.filter_by(status='completed').count()
    rejected_exchanges = ExchangeRequest.query.filter_by(status='rejected').count()

    completion_rate = round((completed_exchanges / total_exchanges * 100), 1) if total_exchanges > 0 else 0

    pending_reports = Report.query.filter_by(status='pending').count()
    total_reviews = Review.query.count()

    # Category breakdown
    category_counts = {}
    for cat, _ in SKILL_CATEGORIES:
        count = Skill.query.filter_by(category=cat).count()
        category_counts[cat] = count

    recent_users = User.query.order_by(User.created_at.desc()).limit(6).all()
    recent_exchanges = ExchangeRequest.query.order_by(ExchangeRequest.created_at.desc()).limit(6).all()
    recent_reports = Report.query.order_by(Report.created_at.desc()).limit(5).all()

    return render_template('admin/dashboard.html',
                           total_users=total_users,
                           active_users=active_users,
                           banned_users=banned_users,
                           total_skills=total_skills,
                           total_user_skills=total_user_skills,
                           total_teaching=total_teaching,
                           total_learning=total_learning,
                           total_exchanges=total_exchanges,
                           pending_exchanges=pending_exchanges,
                           active_exchanges=active_exchanges,
                           completed_exchanges=completed_exchanges,
                           rejected_exchanges=rejected_exchanges,
                           completion_rate=completion_rate,
                           pending_reports=pending_reports,
                           total_reviews=total_reviews,
                           category_counts=category_counts,
                           recent_users=recent_users,
                           recent_exchanges=recent_exchanges,
                           recent_reports=recent_reports)


@admin_bp.route('/users')
@login_required
@admin_required
def users():
    search = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '').strip()

    query = User.query
    if search:
        query = query.filter(
            (User.username.ilike(f"%{search}%")) |
            (User.email.ilike(f"%{search}%")) |
            (User.full_name.ilike(f"%{search}%"))
        )

    if status_filter == 'active':
        query = query.filter_by(is_active_account=True)
    elif status_filter == 'banned':
        query = query.filter_by(is_active_account=False)
    elif status_filter == 'admin':
        query = query.filter_by(is_admin=True)

    page = request.args.get('page', 1, type=int)
    users_page = query.order_by(User.created_at.desc()).paginate(page=page, per_page=15, error_out=False)

    return render_template('admin/users.html',
                           users_page=users_page,
                           search=search,
                           status_filter=status_filter)


@admin_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_user_status(user_id):
    if user_id == current_user.id:
        flash('You cannot suspend your own account.', 'warning')
        return redirect(url_for('admin.users'))

    user = User.query.get_or_404(user_id)
    user.is_active_account = not user.is_active_account
    db.session.commit()

    status_str = "activated" if user.is_active_account else "suspended"
    flash(f'User {user.username} has been {status_str}.', 'info')
    return redirect(request.referrer or url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/toggle-admin', methods=['POST'])
@login_required
@admin_required
def toggle_user_admin(user_id):
    if user_id == current_user.id:
        flash('You cannot modify your own administrative privileges.', 'warning')
        return redirect(url_for('admin.users'))

    user = User.query.get_or_404(user_id)
    user.is_admin = not user.is_admin
    db.session.commit()

    status_str = "promoted to Admin" if user.is_admin else "demoted from Admin"
    flash(f'User {user.username} has been {status_str}.', 'info')
    return redirect(request.referrer or url_for('admin.users'))


@admin_bp.route('/skills', methods=['GET', 'POST'])
@login_required
@admin_required
def skills():
    form = QuickCreateSkillForm()
    if form.validate_on_submit():
        skill = Skill(
            name=form.name.data.strip(),
            category=form.category.data,
            description=form.description.data.strip() if form.description.data else ''
        )
        db.session.add(skill)
        db.session.commit()
        flash(f'Skill "{skill.name}" successfully created.', 'success')
        return redirect(url_for('admin.skills'))

    category_filter = request.args.get('category', '').strip()
    search = request.args.get('q', '').strip()

    query = Skill.query
    if category_filter:
        query = query.filter_by(category=category_filter)
    if search:
        query = query.filter(Skill.name.ilike(f"%{search}%"))

    all_skills = query.order_by(Skill.category, Skill.name).all()

    return render_template('admin/skills.html',
                           skills=all_skills,
                           form=form,
                           categories=SKILL_CATEGORIES,
                           selected_category=category_filter,
                           search=search)


@admin_bp.route('/skills/<int:skill_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_skill(skill_id):
    skill = Skill.query.get_or_404(skill_id)
    name = skill.name
    db.session.delete(skill)
    db.session.commit()
    flash(f'Skill "{name}" removed from the platform.', 'info')
    return redirect(url_for('admin.skills'))


@admin_bp.route('/exchanges')
@login_required
@admin_required
def exchanges():
    status = request.args.get('status', '').strip()
    query = ExchangeRequest.query

    if status:
        query = query.filter_by(status=status)

    page = request.args.get('page', 1, type=int)
    exchanges_page = query.order_by(ExchangeRequest.created_at.desc()).paginate(page=page, per_page=15, error_out=False)

    return render_template('admin/exchanges.html',
                           exchanges_page=exchanges_page,
                           selected_status=status)


@admin_bp.route('/reports')
@login_required
@admin_required
def reports():
    status = request.args.get('status', 'pending').strip()
    query = Report.query

    if status != 'all':
        query = query.filter_by(status=status)

    all_reports = query.order_by(Report.created_at.desc()).all()

    return render_template('admin/reports.html',
                           reports=all_reports,
                           selected_status=status)


@admin_bp.route('/reports/<int:report_id>/update', methods=['POST'])
@login_required
@admin_required
def update_report(report_id):
    report = Report.query.get_or_404(report_id)
    new_status = request.form.get('status')
    if new_status in ['pending', 'resolved', 'dismissed']:
        report.status = new_status
        db.session.commit()
        flash(f'Report #{report.id} marked as {new_status}.', 'info')

    return redirect(url_for('admin.reports'))


@admin_bp.route('/export-csv')
@login_required
@admin_required
def export_csv():
    import csv
    import io
    from flask import Response

    output = io.StringIO()
    writer = csv.writer(output)

    # Write CSV Header
    writer.writerow([
        'User ID', 'Username', 'Email', 'Full Name', 'Location',
        'Availability', 'Role', 'Status', 'Teaching Skills Count',
        'Learning Skills Count', 'Average Rating', 'Rating Count',
        'Completed Exchanges', 'Registered Date'
    ])

    users = User.query.order_by(User.id.asc()).all()
    for u in users:
        writer.writerow([
            u.id,
            u.username,
            u.email,
            u.full_name,
            u.location,
            u.availability,
            'Admin' if u.is_admin else 'Member',
            'Active' if u.is_active_account else 'Suspended',
            len(u.teaching_skills()),
            len(u.learning_skills()),
            u.average_rating,
            u.rating_count,
            u.completed_exchanges_count,
            u.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=smart_swap_platform_audit.csv'}
    )

