from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from extensions import db
from models import User, Skill, UserSkill, ExchangeRequest, Review, Notification, Message, Report
from forms import ExchangeRequestForm, ReviewForm, ReportUserForm

exchanges_bp = Blueprint('exchanges', __name__)


@exchanges_bp.route('/exchanges')
@login_required
def index():
    active_tab = request.args.get('tab', 'active')

    # Pending requests received by current user
    pending_received = ExchangeRequest.query.filter_by(
        receiver_id=current_user.id,
        status='pending'
    ).order_by(ExchangeRequest.created_at.desc()).all()

    # Pending requests sent by current user
    pending_sent = ExchangeRequest.query.filter_by(
        sender_id=current_user.id,
        status='pending'
    ).order_by(ExchangeRequest.created_at.desc()).all()

    # Active exchanges
    active_exchanges = ExchangeRequest.query.filter(
        ((ExchangeRequest.sender_id == current_user.id) | (ExchangeRequest.receiver_id == current_user.id)),
        ExchangeRequest.status == 'accepted'
    ).order_by(ExchangeRequest.updated_at.desc()).all()

    # Completed exchanges
    completed_exchanges = ExchangeRequest.query.filter(
        ((ExchangeRequest.sender_id == current_user.id) | (ExchangeRequest.receiver_id == current_user.id)),
        ExchangeRequest.status == 'completed'
    ).order_by(ExchangeRequest.completed_at.desc()).all()

    # Cancelled / Rejected
    archived_exchanges = ExchangeRequest.query.filter(
        ((ExchangeRequest.sender_id == current_user.id) | (ExchangeRequest.receiver_id == current_user.id)),
        ExchangeRequest.status.in_(['rejected', 'cancelled'])
    ).order_by(ExchangeRequest.updated_at.desc()).all()

    return render_template('exchanges/manage.html',
                           active_tab=active_tab,
                           pending_received=pending_received,
                           pending_sent=pending_sent,
                           active_exchanges=active_exchanges,
                           completed_exchanges=completed_exchanges,
                           archived_exchanges=archived_exchanges)


@exchanges_bp.route('/exchanges/request/<int:receiver_id>', methods=['GET', 'POST'])
@login_required
def request_exchange(receiver_id):
    if receiver_id == current_user.id:
        flash('You cannot request an exchange with yourself!', 'warning')
        return redirect(url_for('main.dashboard'))

    receiver = User.query.get_or_404(receiver_id)

    # Check if user has teaching skills
    my_teach_skills = current_user.teaching_skills()
    if not my_teach_skills:
        flash('You must add at least one skill you can teach before requesting an exchange.', 'warning')
        return redirect(url_for('auth.manage_skills'))

    # Check if receiver has teaching skills
    receiver_teach_skills = receiver.teaching_skills()
    if not receiver_teach_skills:
        flash(f'{receiver.full_name} has not listed any skills to teach yet.', 'info')
        return redirect(url_for('auth.user_profile', username=receiver.username))

    # Check for existing active or pending exchange
    existing = ExchangeRequest.query.filter(
        ((ExchangeRequest.sender_id == current_user.id) & (ExchangeRequest.receiver_id == receiver.id)) |
        ((ExchangeRequest.sender_id == receiver.id) & (ExchangeRequest.receiver_id == current_user.id)),
        ExchangeRequest.status.in_(['pending', 'accepted'])
    ).first()

    if existing:
        flash('You already have an active or pending exchange with this user.', 'info')
        return redirect(url_for('exchanges.exchange_detail', exchange_id=existing.id))

    form = ExchangeRequestForm()
    form.offered_skill_id.choices = [(us.skill.id, f"{us.skill.name} ({us.proficiency_level})") for us in my_teach_skills]
    form.requested_skill_id.choices = [(us.skill.id, f"{us.skill.name} ({us.proficiency_level})") for us in receiver_teach_skills]

    # Pre-select matching skills if available
    preselected_requested = request.args.get('requested_skill_id', type=int)
    if preselected_requested and any(choice[0] == preselected_requested for choice in form.requested_skill_id.choices):
        form.requested_skill_id.data = preselected_requested

    if form.validate_on_submit():
        exchange = ExchangeRequest(
            sender_id=current_user.id,
            receiver_id=receiver.id,
            offered_skill_id=form.offered_skill_id.data,
            requested_skill_id=form.requested_skill_id.data,
            message=form.message.data.strip(),
            schedule_notes=form.schedule_notes.data.strip() if form.schedule_notes.data else 'Flexible',
            status='pending'
        )
        db.session.add(exchange)
        db.session.flush()

        # Send initial message to conversation thread
        init_message = Message(
            sender_id=current_user.id,
            receiver_id=receiver.id,
            exchange_id=exchange.id,
            content=f"🤝 Exchange Proposal:\n{form.message.data.strip()}\n\nPreferred Availability: {exchange.schedule_notes}"
        )
        db.session.add(init_message)

        # Notify receiver
        notification = Notification(
            user_id=receiver.id,
            title='New Skill Exchange Request',
            message=f'{current_user.full_name} wants to swap knowledge with you!',
            link=url_for('exchanges.exchange_detail', exchange_id=exchange.id),
            icon='bi-arrow-left-right'
        )
        db.session.add(notification)
        db.session.commit()

        flash(f'Your exchange request has been sent to {receiver.full_name}!', 'success')
        return redirect(url_for('exchanges.exchange_detail', exchange_id=exchange.id))

    return render_template('exchanges/request.html', form=form, receiver=receiver)


@exchanges_bp.route('/exchanges/<int:exchange_id>')
@login_required
def exchange_detail(exchange_id):
    exchange = ExchangeRequest.query.get_or_404(exchange_id)

    # Security check: must be sender, receiver, or admin
    if current_user.id not in [exchange.sender_id, exchange.receiver_id] and not current_user.is_admin:
        flash('You do not have permission to view this exchange.', 'danger')
        return redirect(url_for('exchanges.index'))

    partner = exchange.receiver if exchange.sender_id == current_user.id else exchange.sender
    my_review = Review.query.filter_by(exchange_id=exchange.id, reviewer_id=current_user.id).first()
    partner_review = Review.query.filter_by(exchange_id=exchange.id, reviewer_id=partner.id).first()

    return render_template('exchanges/detail.html',
                           exchange=exchange,
                           partner=partner,
                           my_review=my_review,
                           partner_review=partner_review)


@exchanges_bp.route('/exchanges/<int:exchange_id>/accept', methods=['POST'])
@login_required
def accept_exchange(exchange_id):
    exchange = ExchangeRequest.query.get_or_404(exchange_id)

    if exchange.receiver_id != current_user.id:
        flash('Only the recipient can accept this exchange request.', 'danger')
        return redirect(url_for('exchanges.index'))

    exchange.status = 'accepted'
    exchange.updated_at = datetime.utcnow()

    # Notify sender
    notification = Notification(
        user_id=exchange.sender_id,
        title='Exchange Accepted! 🎉',
        message=f'{current_user.full_name} accepted your skill exchange proposal!',
        link=url_for('exchanges.exchange_detail', exchange_id=exchange.id),
        icon='bi-check-circle-fill'
    )
    db.session.add(notification)

    # Post system message in thread
    sys_msg = Message(
        sender_id=current_user.id,
        receiver_id=exchange.sender_id,
        exchange_id=exchange.id,
        content="🎉 I've accepted your exchange request! Let's arrange our first learning session."
    )
    db.session.add(sys_msg)
    db.session.commit()

    flash(f'You accepted the exchange with {exchange.sender.full_name}! You can now coordinate sessions via messaging.', 'success')
    return redirect(url_for('exchanges.exchange_detail', exchange_id=exchange.id))


@exchanges_bp.route('/exchanges/<int:exchange_id>/reject', methods=['POST'])
@login_required
def reject_exchange(exchange_id):
    exchange = ExchangeRequest.query.get_or_404(exchange_id)

    if exchange.receiver_id != current_user.id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('exchanges.index'))

    exchange.status = 'rejected'
    exchange.updated_at = datetime.utcnow()

    # Notify sender
    notification = Notification(
        user_id=exchange.sender_id,
        title='Exchange Request Declined',
        message=f'{current_user.full_name} was unable to accept your exchange request at this time.',
        link=url_for('exchanges.exchange_detail', exchange_id=exchange.id),
        icon='bi-x-circle'
    )
    db.session.add(notification)
    db.session.commit()

    flash('You declined the exchange request.', 'info')
    return redirect(url_for('exchanges.index'))


@exchanges_bp.route('/exchanges/<int:exchange_id>/cancel', methods=['POST'])
@login_required
def cancel_exchange(exchange_id):
    exchange = ExchangeRequest.query.get_or_404(exchange_id)

    if current_user.id not in [exchange.sender_id, exchange.receiver_id]:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('exchanges.index'))

    exchange.status = 'cancelled'
    exchange.updated_at = datetime.utcnow()

    other_user_id = exchange.receiver_id if exchange.sender_id == current_user.id else exchange.sender_id
    notification = Notification(
        user_id=other_user_id,
        title='Exchange Request Cancelled',
        message=f'{current_user.full_name} cancelled the exchange request.',
        link=url_for('exchanges.exchange_detail', exchange_id=exchange.id),
        icon='bi-slash-circle'
    )
    db.session.add(notification)
    db.session.commit()

    flash('Exchange cancelled.', 'info')
    return redirect(url_for('exchanges.index'))


@exchanges_bp.route('/exchanges/<int:exchange_id>/complete', methods=['POST'])
@login_required
def complete_exchange(exchange_id):
    exchange = ExchangeRequest.query.get_or_404(exchange_id)

    if current_user.id not in [exchange.sender_id, exchange.receiver_id]:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('exchanges.index'))

    exchange.status = 'completed'
    exchange.completed_at = datetime.utcnow()
    exchange.updated_at = datetime.utcnow()

    other_user_id = exchange.receiver_id if exchange.sender_id == current_user.id else exchange.sender_id
    notification = Notification(
        user_id=other_user_id,
        title='Exchange Completed! 🌟',
        message=f'{current_user.full_name} marked your exchange as completed. Please leave a review!',
        link=url_for('exchanges.leave_review', exchange_id=exchange.id),
        icon='bi-star-fill'
    )
    db.session.add(notification)
    db.session.commit()

    flash('Congratulations on completing your knowledge exchange! Please take a moment to leave feedback.', 'success')
    return redirect(url_for('exchanges.leave_review', exchange_id=exchange.id))


@exchanges_bp.route('/exchanges/<int:exchange_id>/review', methods=['GET', 'POST'])
@login_required
def leave_review(exchange_id):
    exchange = ExchangeRequest.query.get_or_404(exchange_id)

    if current_user.id not in [exchange.sender_id, exchange.receiver_id]:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('exchanges.index'))

    if exchange.status != 'completed':
        flash('Reviews can only be submitted for completed exchanges.', 'warning')
        return redirect(url_for('exchanges.exchange_detail', exchange_id=exchange.id))

    partner = exchange.receiver if exchange.sender_id == current_user.id else exchange.sender

    # Check if already reviewed
    existing_review = Review.query.filter_by(exchange_id=exchange.id, reviewer_id=current_user.id).first()
    if existing_review:
        flash('You have already submitted a review for this exchange.', 'info')
        return redirect(url_for('exchanges.exchange_detail', exchange_id=exchange.id))

    form = ReviewForm()
    if form.validate_on_submit():
        review = Review(
            exchange_id=exchange.id,
            reviewer_id=current_user.id,
            reviewee_id=partner.id,
            rating=int(form.rating.data),
            comment=form.comment.data.strip()
        )
        db.session.add(review)

        # Notify partner
        notification = Notification(
            user_id=partner.id,
            title='New Review Received! ⭐',
            message=f'{current_user.full_name} gave you a {review.rating}-star review!',
            link=url_for('auth.user_profile', username=partner.username),
            icon='bi-star'
        )
        db.session.add(notification)
        db.session.commit()

        flash(f'Thank you! Your feedback for {partner.full_name} has been published.', 'success')
        return redirect(url_for('exchanges.exchange_detail', exchange_id=exchange.id))

    return render_template('exchanges/review.html', form=form, exchange=exchange, partner=partner)


@exchanges_bp.route('/users/<int:user_id>/report', methods=['GET', 'POST'])
@login_required
def report_user(user_id):
    if user_id == current_user.id:
        flash('You cannot report yourself.', 'warning')
        return redirect(url_for('main.dashboard'))

    reported_user = User.query.get_or_404(user_id)
    form = ReportUserForm()

    if form.validate_on_submit():
        report = Report(
            reporter_id=current_user.id,
            reported_user_id=reported_user.id,
            reason=form.reason.data,
            details=form.details.data.strip() if form.details.data else ''
        )
        db.session.add(report)
        db.session.commit()

        flash(f'Your report regarding {reported_user.full_name} has been submitted to the moderation team.', 'info')
        return redirect(url_for('auth.user_profile', username=reported_user.username))

    return render_template('report.html', form=form, reported_user=reported_user)


@exchanges_bp.route('/exchanges/<int:exchange_id>/meet')
@login_required
def virtual_classroom(exchange_id):
    exchange = ExchangeRequest.query.get_or_404(exchange_id)

    if current_user.id not in [exchange.sender_id, exchange.receiver_id] and not current_user.is_admin:
        flash('Unauthorized action. You must be a participant to join this virtual classroom.', 'danger')
        return redirect(url_for('exchanges.index'))

    partner = exchange.receiver if exchange.sender_id == current_user.id else exchange.sender
    # Generate unique sanitized room name for Jitsi Meet
    room_name = f"SmartSwap-Exchange-{exchange.id}-Classroom"

    return render_template('exchanges/meet.html',
                           exchange=exchange,
                           partner=partner,
                           room_name=room_name)


@exchanges_bp.route('/exchanges/<int:exchange_id>/certificate')
@login_required
def view_certificate(exchange_id):
    exchange = ExchangeRequest.query.get_or_404(exchange_id)

    if current_user.id not in [exchange.sender_id, exchange.receiver_id] and not current_user.is_admin:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('exchanges.index'))

    if exchange.status != 'completed':
        flash('Certificates of Knowledge Exchange are only issued for successfully completed swaps.', 'warning')
        return redirect(url_for('exchanges.exchange_detail', exchange_id=exchange.id))

    partner = exchange.receiver if exchange.sender_id == current_user.id else exchange.sender
    my_taught_skill = exchange.offered_skill if exchange.sender_id == current_user.id else exchange.requested_skill
    partner_taught_skill = exchange.requested_skill if exchange.sender_id == current_user.id else exchange.offered_skill

    return render_template('exchanges/certificate.html',
                           exchange=exchange,
                           current_user=current_user,
                           partner=partner,
                           my_taught_skill=my_taught_skill,
                           partner_taught_skill=partner_taught_skill)


@exchanges_bp.route('/exchanges/<int:exchange_id>/update-milestone', methods=['POST'])
@login_required
def update_milestone(exchange_id):
    exchange = ExchangeRequest.query.get_or_404(exchange_id)

    if current_user.id not in [exchange.sender_id, exchange.receiver_id] and not current_user.is_admin:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('exchanges.index'))

    milestone_val = request.form.get('milestones', type=int)
    if milestone_val is not None and 0 <= milestone_val <= 3:
        exchange.completed_milestones = milestone_val
        exchange.updated_at = datetime.utcnow()

        # If all 3 sessions done, suggest completing
        if milestone_val == 3 and exchange.status == 'accepted':
            flash('All 3 learning sessions finished! You can now mark the exchange as completed.', 'success')
        else:
            flash(f'Learning roadmap updated: {exchange.milestone_percentage}% complete!', 'info')

        db.session.commit()

    return redirect(url_for('exchanges.exchange_detail', exchange_id=exchange.id))


@exchanges_bp.route('/exchanges/<int:exchange_id>/save-notes', methods=['POST'])
@login_required
def save_shared_notes(exchange_id):
    exchange = ExchangeRequest.query.get_or_404(exchange_id)

    if current_user.id not in [exchange.sender_id, exchange.receiver_id] and not current_user.is_admin:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('exchanges.index'))

    notes_text = request.form.get('shared_notes', '').strip()
    exchange.shared_notes = notes_text
    exchange.updated_at = datetime.utcnow()
    db.session.commit()

    flash('Shared learning resources and links updated successfully!', 'success')
    return redirect(url_for('exchanges.exchange_detail', exchange_id=exchange.id))


