import os
import uuid
from urllib.parse import urlsplit
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from extensions import db
from models import User, Skill, UserSkill, Review, ExchangeRequest
from forms import LoginForm, RegistrationForm, ProfileEditForm, AddSkillForm, QuickCreateSkillForm
from matching import calculate_compatibility

auth_bp = Blueprint('auth', __name__)


def is_safe_url(target):
    if not target:
        return False
    ref_url = urlsplit(request.host_url)
    test_url = urlsplit(target)
    return (test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc) or (not test_url.netloc and target.startswith('/'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data.strip().lower(),
            email=form.email.data.strip().lower(),
            full_name=form.full_name.data.strip()
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash(f'Welcome to Smart Swap, {user.full_name}! Let’s add the skills you can teach and want to learn.', 'success')
        return redirect(url_for('auth.manage_skills'))

    return render_template('auth/register.html', form=form)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        login_input = form.username_or_email.data.strip().lower()
        user = User.query.filter(
            (User.username == login_input) | (User.email == login_input)
        ).first()

        if user and user.check_password(form.password.data):
            if not user.is_active_account:
                flash('This account has been suspended. Please contact the administrator.', 'danger')
                return render_template('auth/login.html', form=form)

            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            if next_page and not is_safe_url(next_page):
                next_page = None
            flash(f'Welcome back, {user.full_name}!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('main.dashboard'))
        else:
            flash('Invalid username/email or password.', 'danger')

    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('main.index'))


@auth_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = ProfileEditForm(obj=current_user)

    if form.validate_on_submit():
        current_user.full_name = form.full_name.data.strip()
        current_user.headline = form.headline.data.strip() if form.headline.data else ''
        current_user.bio = form.bio.data.strip() if form.bio.data else ''
        current_user.location = form.location.data.strip() if form.location.data else 'Remote'
        current_user.availability = form.availability.data

        # Handle avatar file upload
        if form.avatar.data:
            file = form.avatar.data
            ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
            if ext in current_app.config['ALLOWED_EXTENSIONS']:
                filename = f"avatar_{current_user.id}_{uuid.uuid4().hex[:8]}.{ext}"
                os.makedirs(current_app.config['AVATAR_FOLDER'], exist_ok=True)
                file_path = os.path.join(current_app.config['AVATAR_FOLDER'], filename)
                file.save(file_path)
                current_user.avatar = filename

        db.session.commit()
        flash('Your profile has been updated successfully!', 'success')
        return redirect(url_for('auth.user_profile', username=current_user.username))

    return render_template('profile/edit.html', form=form)


@auth_bp.route('/profile/skills', methods=['GET', 'POST'])
@login_required
def manage_skills():
    add_form = AddSkillForm()
    quick_skill_form = QuickCreateSkillForm()

    # Populate skill choices
    skills = Skill.query.order_by(Skill.category, Skill.name).all()
    add_form.skill_id.choices = [(s.id, f"{s.name} ({s.category})") for s in skills]

    # Handle adding existing skill to user profile
    if 'submit_add_skill' in request.form and add_form.validate_on_submit():
        skill_id = add_form.skill_id.data
        skill_type = add_form.skill_type.data

        existing = UserSkill.query.filter_by(
            user_id=current_user.id,
            skill_id=skill_id,
            skill_type=skill_type
        ).first()

        if existing:
            flash('You have already added this skill to your profile!', 'warning')
        else:
            user_skill = UserSkill(
                user_id=current_user.id,
                skill_id=skill_id,
                skill_type=skill_type,
                proficiency_level=add_form.proficiency_level.data,
                experience_years=add_form.experience_years.data or 1,
                notes=add_form.notes.data or ''
            )
            db.session.add(user_skill)
            db.session.commit()
            action_verb = "teach" if skill_type == 'teach' else "learn"
            flash(f'Skill added to your list of skills to {action_verb}!', 'success')
            return redirect(url_for('auth.manage_skills'))

    # Handle creating a new skill catalog entry if user skill doesn't exist
    if 'submit_quick_skill' in request.form and quick_skill_form.validate_on_submit():
        new_skill = Skill(
            name=quick_skill_form.name.data.strip(),
            category=quick_skill_form.category.data,
            description=quick_skill_form.description.data.strip() if quick_skill_form.description.data else ''
        )
        db.session.add(new_skill)
        db.session.commit()
        flash(f'New skill "{new_skill.name}" registered in the directory! You can now add it to your profile.', 'success')
        return redirect(url_for('auth.manage_skills'))

    teaching_skills = current_user.teaching_skills()
    learning_skills = current_user.learning_skills()

    return render_template('profile/manage_skills.html',
                           add_form=add_form,
                           quick_skill_form=quick_skill_form,
                           teaching_skills=teaching_skills,
                           learning_skills=learning_skills)


@auth_bp.route('/profile/skills/delete/<int:user_skill_id>', methods=['POST'])
@login_required
def delete_user_skill(user_skill_id):
    user_skill = UserSkill.query.get_or_404(user_skill_id)
    if user_skill.user_id != current_user.id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('auth.manage_skills'))

    db.session.delete(user_skill)
    db.session.commit()
    flash('Skill removed from your profile.', 'info')
    return redirect(url_for('auth.manage_skills'))


@auth_bp.route('/u/<username>')
def user_profile(username):
    user = User.query.filter(User.username.ilike(username)).first_or_404()
    
    # Calculate smart compatibility if logged in and not viewing self
    compatibility = None
    if current_user.is_authenticated and current_user.id != user.id:
        compatibility = calculate_compatibility(current_user, user)

    # Get recent reviews
    reviews = Review.query.filter_by(reviewee_id=user.id).order_by(Review.created_at.desc()).limit(10).all()
    
    # Check if there is an active exchange with this user
    existing_exchange = None
    if current_user.is_authenticated and current_user.id != user.id:
        existing_exchange = ExchangeRequest.query.filter(
            ((ExchangeRequest.sender_id == current_user.id) & (ExchangeRequest.receiver_id == user.id)) |
            ((ExchangeRequest.sender_id == user.id) & (ExchangeRequest.receiver_id == current_user.id)),
            ExchangeRequest.status.in_(['pending', 'accepted'])
        ).first()

    return render_template('profile/view.html',
                           user=user,
                           compatibility=compatibility,
                           reviews=reviews,
                           existing_exchange=existing_exchange)


@auth_bp.route('/u/<username>/portfolio')
def user_portfolio(username):
    user = User.query.filter(User.username.ilike(username)).first_or_404()
    completed_exchanges = ExchangeRequest.query.filter(
        ((ExchangeRequest.sender_id == user.id) | (ExchangeRequest.receiver_id == user.id)),
        ExchangeRequest.status == 'completed'
    ).order_by(ExchangeRequest.completed_at.desc()).all()

    reviews = Review.query.filter_by(reviewee_id=user.id).order_by(Review.rating.desc(), Review.created_at.desc()).all()

    return render_template('profile/portfolio.html',
                           user=user,
                           completed_exchanges=completed_exchanges,
                           reviews=reviews)

