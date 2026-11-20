from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from extensions import db
from models import User, Message, ExchangeRequest, Notification
from forms import MessageForm

messages_bp = Blueprint('messages', __name__)


def get_conversation_partners(user_id):
    """
    Returns list of distinct users with whom user_id has conversed,
    along with their most recent message and unread count.
    """
    all_msgs = Message.query.filter(
        (Message.sender_id == user_id) | (Message.receiver_id == user_id)
    ).order_by(Message.created_at.desc()).all()

    seen_partners = {}
    for msg in all_msgs:
        partner_id = msg.receiver_id if msg.sender_id == user_id else msg.sender_id
        if partner_id not in seen_partners:
            partner = User.query.get(partner_id)
            if partner:
                unread_count = Message.query.filter_by(
                    sender_id=partner_id,
                    receiver_id=user_id,
                    is_read=False
                ).count()
                seen_partners[partner_id] = {
                    'partner': partner,
                    'last_message': msg,
                    'unread_count': unread_count
                }

    return list(seen_partners.values())


@messages_bp.route('/messages')
@login_required
def index():
    conversations = get_conversation_partners(current_user.id)
    first_partner_id = request.args.get('user_id', type=int)

    if not first_partner_id and conversations:
        first_partner_id = conversations[0]['partner'].id

    if first_partner_id:
        return redirect(url_for('messages.chat', partner_id=first_partner_id))

    return render_template('messages/chat.html',
                           conversations=[],
                           active_partner=None,
                           messages=[],
                           form=MessageForm())


@messages_bp.route('/messages/<int:partner_id>', methods=['GET', 'POST'])
@login_required
def chat(partner_id):
    if partner_id == current_user.id:
        flash('You cannot message yourself.', 'warning')
        return redirect(url_for('messages.index'))

    partner = User.query.get_or_404(partner_id)
    form = MessageForm()

    # Find associated exchange if any
    exchange = ExchangeRequest.query.filter(
        ((ExchangeRequest.sender_id == current_user.id) & (ExchangeRequest.receiver_id == partner.id)) |
        ((ExchangeRequest.sender_id == partner.id) & (ExchangeRequest.receiver_id == current_user.id)),
        ExchangeRequest.status.in_(['pending', 'accepted', 'completed'])
    ).first()

    # Send message via regular POST
    if form.validate_on_submit():
        new_msg = Message(
            sender_id=current_user.id,
            receiver_id=partner.id,
            exchange_id=exchange.id if exchange else None,
            content=form.content.data.strip()
        )
        db.session.add(new_msg)

        # Create notification for recipient
        notif = Notification(
            user_id=partner.id,
            title='New Message 💬',
            message=f'{current_user.full_name}: {new_msg.content[:50]}...',
            link=url_for('messages.chat', partner_id=current_user.id),
            icon='bi-chat-dots'
        )
        db.session.add(notif)
        db.session.commit()

        return redirect(url_for('messages.chat', partner_id=partner.id))

    # Mark incoming unread messages as read
    Message.query.filter_by(
        sender_id=partner.id,
        receiver_id=current_user.id,
        is_read=False
    ).update({'is_read': True})
    db.session.commit()

    # Load conversation messages
    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == partner.id)) |
        ((Message.sender_id == partner.id) & (Message.receiver_id == current_user.id))
    ).order_by(Message.created_at.asc()).all()

    conversations = get_conversation_partners(current_user.id)
    
    # If this partner is not yet in conversation list (first time message)
    if not any(c['partner'].id == partner.id for c in conversations):
        conversations.insert(0, {
            'partner': partner,
            'last_message': None,
            'unread_count': 0
        })

    return render_template('messages/chat.html',
                           conversations=conversations,
                           active_partner=partner,
                           exchange=exchange,
                           messages=messages,
                           form=form)


@messages_bp.route('/api/messages/<int:partner_id>', methods=['GET', 'POST'])
@login_required
def api_messages(partner_id):
    partner = User.query.get_or_404(partner_id)

    if request.method == 'POST':
        data = request.get_json() or {}
        content = data.get('content', '').strip()
        if not content:
            return jsonify({'success': False, 'error': 'Message content is empty'}), 400

        exchange = ExchangeRequest.query.filter(
            ((ExchangeRequest.sender_id == current_user.id) & (ExchangeRequest.receiver_id == partner.id)) |
            ((ExchangeRequest.sender_id == partner.id) & (ExchangeRequest.receiver_id == current_user.id)),
            ExchangeRequest.status.in_(['pending', 'accepted', 'completed'])
        ).first()

        new_msg = Message(
            sender_id=current_user.id,
            receiver_id=partner.id,
            exchange_id=exchange.id if exchange else None,
            content=content
        )
        db.session.add(new_msg)

        notif = Notification(
            user_id=partner.id,
            title='New Message 💬',
            message=f'{current_user.full_name}: {content[:50]}...',
            link=url_for('messages.chat', partner_id=current_user.id),
            icon='bi-chat-dots'
        )
        db.session.add(notif)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': {
                'id': new_msg.id,
                'sender_id': new_msg.sender_id,
                'content': new_msg.content,
                'created_at': new_msg.created_at.strftime('%b %d, %H:%M'),
                'is_mine': True
            }
        })

    # GET endpoint: Fetch messages, optionally since a given message id
    since_id = request.args.get('since_id', 0, type=int)
    query = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == partner.id)) |
        ((Message.sender_id == partner.id) & (Message.receiver_id == current_user.id))
    )

    if since_id > 0:
        query = query.filter(Message.id > since_id)

    msgs = query.order_by(Message.created_at.asc()).all()

    # Mark as read
    Message.query.filter(
        Message.sender_id == partner.id,
        Message.receiver_id == current_user.id,
        Message.is_read == False
    ).update({'is_read': True})
    db.session.commit()

    return jsonify({
        'success': True,
        'messages': [{
            'id': m.id,
            'sender_id': m.sender_id,
            'sender_name': m.sender.full_name,
            'content': m.content,
            'created_at': m.created_at.strftime('%b %d, %H:%M'),
            'is_mine': (m.sender_id == current_user.id)
        } for m in msgs]
    })


@messages_bp.route('/api/unread-count')
@login_required
def api_unread_count():
    unread_msgs = current_user.unread_messages_count
    unread_notifs = current_user.unread_notifications_count
    return jsonify({
        'unread_messages': unread_msgs,
        'unread_notifications': unread_notifs
    })
