from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from extensions import db
from models import User, Skill, UserSkill, ExchangeRequest, Review, Notification
from matching import get_smart_matches, calculate_compatibility
from forms import SKILL_CATEGORIES, AVAILABILITY_CHOICES, PROFICIENCY_CHOICES

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    # Platform metrics for landing page
    total_users = User.query.filter_by(is_active_account=True).count()
    total_skills = Skill.query.count()
    total_exchanges = ExchangeRequest.query.filter_by(status='completed').count()
    categories = SKILL_CATEGORIES

    featured_skills = Skill.query.order_by(Skill.id.desc()).limit(8).all()
    recent_reviews = Review.query.filter(Review.rating >= 4).order_by(Review.created_at.desc()).limit(3).all()
    top_mentors = User.query.filter(User.is_active_account == True).limit(4).all()

    return render_template('index.html',
                           total_users=total_users,
                           total_skills=total_skills,
                           total_exchanges=total_exchanges,
                           categories=categories,
                           featured_skills=featured_skills,
                           recent_reviews=recent_reviews,
                           top_mentors=top_mentors)


@main_bp.route('/dashboard')
@login_required
def dashboard():
    # User stats
    skills_offered_count = len(current_user.teaching_skills())
    skills_wanted_count = len(current_user.learning_skills())
    pending_count = current_user.pending_requests_count
    active_count = current_user.active_exchanges_count
    completed_count = current_user.completed_exchanges_count

    # Smart Match Recommendations (Top 4)
    smart_matches = get_smart_matches(current_user, limit=4)

    # Active exchanges for quick access
    active_exchanges = ExchangeRequest.query.filter(
        ((ExchangeRequest.sender_id == current_user.id) | (ExchangeRequest.receiver_id == current_user.id)),
        ExchangeRequest.status == 'accepted'
    ).order_by(ExchangeRequest.updated_at.desc()).limit(5).all()

    # Pending incoming requests
    pending_incoming = ExchangeRequest.query.filter_by(
        receiver_id=current_user.id,
        status='pending'
    ).order_by(ExchangeRequest.created_at.desc()).limit(3).all()

    # Recent notifications
    notifications = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(Notification.created_at.desc()).limit(5).all()

    return render_template('dashboard.html',
                           skills_offered_count=skills_offered_count,
                           skills_wanted_count=skills_wanted_count,
                           pending_count=pending_count,
                           active_count=active_count,
                           completed_count=completed_count,
                           smart_matches=smart_matches,
                           active_exchanges=active_exchanges,
                           pending_incoming=pending_incoming,
                           notifications=notifications)


@main_bp.route('/explore')
def explore():
    query_text = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    skill_type = request.args.get('type', 'teach').strip()  # 'teach' or 'learn'
    level = request.args.get('level', '').strip()
    location = request.args.get('location', '').strip()
    availability = request.args.get('availability', '').strip()

    # Base query for user skills
    user_skill_query = UserSkill.query.join(User).join(Skill).filter(
        User.is_active_account == True
    )

    if skill_type in ['teach', 'learn']:
        user_skill_query = user_skill_query.filter(UserSkill.skill_type == skill_type)

    if query_text:
        search_pattern = f"%{query_text}%"
        user_skill_query = user_skill_query.filter(
            (Skill.name.ilike(search_pattern)) |
            (User.full_name.ilike(search_pattern)) |
            (User.username.ilike(search_pattern)) |
            (User.headline.ilike(search_pattern)) |
            (UserSkill.notes.ilike(search_pattern))
        )

    if category:
        user_skill_query = user_skill_query.filter(Skill.category == category)

    if level:
        user_skill_query = user_skill_query.filter(UserSkill.proficiency_level == level)

    if location:
        user_skill_query = user_skill_query.filter(User.location.ilike(f"%{location}%"))

    if availability:
        user_skill_query = user_skill_query.filter(User.availability == availability)

    page = request.args.get('page', 1, type=int)
    results = user_skill_query.order_by(UserSkill.created_at.desc()).paginate(page=page, per_page=12, error_out=False)

    all_categories = SKILL_CATEGORIES
    popular_skills = Skill.query.order_by(Skill.name).all()

    return render_template('skills/explore.html',
                           results=results,
                           query_text=query_text,
                           selected_category=category,
                           selected_type=skill_type,
                           selected_level=level,
                           selected_location=location,
                           selected_availability=availability,
                           categories=all_categories,
                           popular_skills=popular_skills,
                           proficiency_choices=PROFICIENCY_CHOICES,
                           availability_choices=AVAILABILITY_CHOICES)


@main_bp.route('/skills/<int:skill_id>')
def skill_detail(skill_id):
    skill = Skill.query.get_or_404(skill_id)
    teachers = UserSkill.query.filter_by(skill_id=skill.id, skill_type='teach').all()
    learners = UserSkill.query.filter_by(skill_id=skill.id, skill_type='learn').all()

    return render_template('skills/detail.html',
                           skill=skill,
                           teachers=teachers,
                           learners=learners)


@main_bp.route('/smart-matching')
@login_required
def smart_matching():
    min_score = request.args.get('min_score', 20, type=int)
    category = request.args.get('category', '').strip() or None

    matches = get_smart_matches(current_user, limit=50, category=category, min_score=min_score)

    return render_template('matching/index.html',
                           matches=matches,
                           min_score=min_score,
                           selected_category=category or '',
                           categories=SKILL_CATEGORIES)


@main_bp.route('/notifications')
@login_required
def notifications():
    user_notifications = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(Notification.created_at.desc()).all()

    return render_template('notifications.html', notifications=user_notifications)


@main_bp.route('/notifications/read-all', methods=['POST'])
@login_required
def mark_all_notifications_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    flash('All notifications marked as read.', 'info')
    return redirect(url_for('main.notifications'))


@main_bp.route('/architecture')
def architecture():
    return render_template('architecture.html')

