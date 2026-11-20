from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from extensions import db, login_manager


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    headline = db.Column(db.String(150), default='Skill Exchanger')
    bio = db.Column(db.Text, default='Passionate about learning and sharing knowledge.')
    location = db.Column(db.String(100), default='Remote / Global')
    availability = db.Column(db.String(50), default='Flexible')  # Flexible, Weekends, Evenings, Weekdays
    avatar = db.Column(db.String(255), default='default_avatar.png')
    is_admin = db.Column(db.Boolean, default=False)
    is_active_account = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user_skills = db.relationship('UserSkill', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    sent_requests = db.relationship('ExchangeRequest', foreign_keys='ExchangeRequest.sender_id', backref='sender', lazy='dynamic')
    received_requests = db.relationship('ExchangeRequest', foreign_keys='ExchangeRequest.receiver_id', backref='receiver', lazy='dynamic')
    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy='dynamic')
    received_messages = db.relationship('Message', foreign_keys='Message.receiver_id', backref='receiver', lazy='dynamic')
    reviews_given = db.relationship('Review', foreign_keys='Review.reviewer_id', backref='reviewer', lazy='dynamic')
    reviews_received = db.relationship('Review', foreign_keys='Review.reviewee_id', backref='reviewee', lazy='dynamic')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    reports_submitted = db.relationship('Report', foreign_keys='Report.reporter_id', backref='reporter', lazy='dynamic')
    reports_against = db.relationship('Report', foreign_keys='Report.reported_user_id', backref='reported_user', lazy='dynamic')

    def __init__(self, username=None, email=None, full_name=None, headline='Skill Exchanger', bio='Passionate about learning and sharing knowledge.', location='Remote / Global', availability='Flexible', avatar='default_avatar.png', is_admin=False, is_active_account=True, **kwargs):
        super().__init__(**kwargs)
        if username is not None: self.username = username
        if email is not None: self.email = email
        if full_name is not None: self.full_name = full_name
        self.headline = headline
        self.bio = bio
        self.location = location
        self.availability = availability
        self.avatar = avatar
        self.is_admin = is_admin
        self.is_active_account = is_active_account

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def teaching_skills(self):
        return [us for us in self.user_skills if us.skill_type == 'teach']

    def learning_skills(self):
        return [us for us in self.user_skills if us.skill_type == 'learn']

    def teaching_skill_ids(self):
        return [us.skill_id for us in self.user_skills if us.skill_type == 'teach']

    def learning_skill_ids(self):
        return [us.skill_id for us in self.user_skills if us.skill_type == 'learn']

    @property
    def average_rating(self):
        revs = self.reviews_received.all()
        if not revs:
            return 5.0  # Default friendly starter rating
        total = sum(r.rating for r in revs)
        return round(total / len(revs), 1)

    @property
    def rating_count(self):
        return self.reviews_received.count()

    @property
    def completed_exchanges_count(self):
        return ExchangeRequest.query.filter(
            ((ExchangeRequest.sender_id == self.id) | (ExchangeRequest.receiver_id == self.id)),
            ExchangeRequest.status == 'completed'
        ).count()

    @property
    def active_exchanges_count(self):
        return ExchangeRequest.query.filter(
            ((ExchangeRequest.sender_id == self.id) | (ExchangeRequest.receiver_id == self.id)),
            ExchangeRequest.status == 'accepted'
        ).count()

    @property
    def pending_requests_count(self):
        return ExchangeRequest.query.filter(
            ExchangeRequest.receiver_id == self.id,
            ExchangeRequest.status == 'pending'
        ).count()

    @property
    def unread_messages_count(self):
        return Message.query.filter_by(receiver_id=self.id, is_read=False).count()

    @property
    def unread_notifications_count(self):
        return Notification.query.filter_by(user_id=self.id, is_read=False).count()

    @property
    def badges(self):
        badge_list = []
        if self.completed_exchanges_count >= 1:
            badge_list.append({
                'name': 'Pioneer Exchanger',
                'icon': 'bi-award-fill',
                'color': 'primary',
                'desc': 'Completed first verified skill exchange'
            })
        if self.average_rating >= 4.8 and self.rating_count >= 1:
            badge_list.append({
                'name': 'Master Mentor',
                'icon': 'bi-star-fill',
                'color': 'warning',
                'desc': 'Maintained a 4.8★+ rating across peer reviews'
            })
        cats = {us.skill.category for us in self.user_skills if us.skill and us.skill.category}
        if len(cats) >= 2:
            badge_list.append({
                'name': 'Multi-Domain Scholar',
                'icon': 'bi-globe-americas',
                'color': 'info',
                'desc': f'Active in {len(cats)} diverse learning domains'
            })
        if self.is_active_account and self.reports_against.count() == 0 and self.completed_exchanges_count >= 1:
            badge_list.append({
                'name': 'Trusted Partner',
                'icon': 'bi-shield-check',
                'color': 'success',
                'desc': '100% clean community standing with verified reviews'
            })
        if len(self.teaching_skills()) + len(self.learning_skills()) >= 3:
            badge_list.append({
                'name': 'Knowledge Champion',
                'icon': 'bi-lightning-charge-fill',
                'color': 'danger',
                'desc': 'Listed 3+ diverse skills to teach and learn'
            })
        return badge_list

    def get_avatar_url(self):
        if self.avatar and self.avatar != 'default_avatar.png' and not self.avatar.startswith('http'):
            return f'/static/uploads/avatars/{self.avatar}'
        elif self.avatar and self.avatar.startswith('http'):
            return self.avatar
        # Fallback to high quality SVG avatar using dicebear
        return f"https://api.dicebear.com/7.x/bottts/svg?seed={self.username}&backgroundColor=b6e3f4,c0aede,d1d4f9"

    def __repr__(self):
        return f'<User {self.username}>'


class Skill(db.Model):
    __tablename__ = 'skills'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    category = db.Column(db.String(50), nullable=False, index=True)
    description = db.Column(db.Text, default='')
    icon = db.Column(db.String(50), default='bi-mortarboard')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user_skills = db.relationship('UserSkill', backref='skill', lazy='dynamic', cascade='all, delete-orphan')

    def __init__(self, name=None, category=None, description='', icon='bi-mortarboard', **kwargs):
        super().__init__(**kwargs)
        if name is not None: self.name = name
        if category is not None: self.category = category
        self.description = description
        self.icon = icon

    @property
    def teachers_count(self):
        return UserSkill.query.filter_by(skill_id=self.id, skill_type='teach').count()

    @property
    def learners_count(self):
        return UserSkill.query.filter_by(skill_id=self.id, skill_type='learn').count()

    def __repr__(self):
        return f'<Skill {self.name}>'


class UserSkill(db.Model):
    __tablename__ = 'user_skills'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    skill_id = db.Column(db.Integer, db.ForeignKey('skills.id', ondelete='CASCADE'), nullable=False)
    skill_type = db.Column(db.String(10), nullable=False)  # 'teach' or 'learn'
    proficiency_level = db.Column(db.String(20), default='Intermediate')  # Beginner, Intermediate, Advanced, Expert
    experience_years = db.Column(db.Integer, default=1)
    notes = db.Column(db.Text, default='')
    description = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, user_id=None, skill_id=None, skill_type=None, proficiency_level='Intermediate', experience_years=1, notes='', description='', **kwargs):
        super().__init__(**kwargs)
        if user_id is not None: self.user_id = user_id
        if skill_id is not None: self.skill_id = skill_id
        if skill_type is not None: self.skill_type = skill_type
        self.proficiency_level = proficiency_level
        self.experience_years = experience_years
        self.notes = notes
        self.description = description

    __table_args__ = (
        db.UniqueConstraint('user_id', 'skill_id', 'skill_type', name='uq_user_skill_type'),
    )

    def __repr__(self):
        return f'<UserSkill {self.user_id} - {self.skill_id} ({self.skill_type})>'


class ExchangeRequest(db.Model):
    __tablename__ = 'exchange_requests'

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    offered_skill_id = db.Column(db.Integer, db.ForeignKey('skills.id'), nullable=False)
    requested_skill_id = db.Column(db.Integer, db.ForeignKey('skills.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, completed, rejected, cancelled
    message = db.Column(db.Text, nullable=False)
    schedule_notes = db.Column(db.String(255), default='Flexible / Remote')
    completed_milestones = db.Column(db.Integer, default=0)  # 0 to 3
    shared_notes = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    # Explicit relationships to skills
    offered_skill = db.relationship('Skill', foreign_keys=[offered_skill_id])
    requested_skill = db.relationship('Skill', foreign_keys=[requested_skill_id])

    # Related items
    messages = db.relationship('Message', backref='exchange', lazy='dynamic', cascade='all, delete-orphan')
    reviews = db.relationship('Review', backref='exchange', lazy='dynamic', cascade='all, delete-orphan')

    def __init__(self, sender_id=None, receiver_id=None, offered_skill_id=None, requested_skill_id=None, status='pending', message='', schedule_notes='Flexible / Remote', completed_milestones=0, shared_notes='', created_at=None, completed_at=None, **kwargs):
        super().__init__(**kwargs)
        if sender_id is not None: self.sender_id = sender_id
        if receiver_id is not None: self.receiver_id = receiver_id
        if offered_skill_id is not None: self.offered_skill_id = offered_skill_id
        if requested_skill_id is not None: self.requested_skill_id = requested_skill_id
        self.status = status
        self.message = message
        self.schedule_notes = schedule_notes
        self.completed_milestones = completed_milestones
        self.shared_notes = shared_notes
        if created_at is not None: self.created_at = created_at
        if completed_at is not None: self.completed_at = completed_at

    @property
    def milestone_percentage(self):
        return min(int((self.completed_milestones / 3) * 100), 100)

    def has_reviewed(self, user_id):
        return Review.query.filter_by(exchange_id=self.id, reviewer_id=user_id).first() is not None

    def __repr__(self):
        return f'<ExchangeRequest {self.id} ({self.status}): {self.sender_id}->{self.receiver_id}>'


class Message(db.Model):
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    exchange_id = db.Column(db.Integer, db.ForeignKey('exchange_requests.id'), nullable=True)
    content = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, sender_id=None, receiver_id=None, exchange_id=None, content='', is_read=False, created_at=None, **kwargs):
        super().__init__(**kwargs)
        if sender_id is not None: self.sender_id = sender_id
        if receiver_id is not None: self.receiver_id = receiver_id
        self.exchange_id = exchange_id
        self.content = content
        self.is_read = is_read
        if created_at is not None: self.created_at = created_at

    def to_dict(self):
        return {
            'id': self.id,
            'sender_id': self.sender_id,
            'sender_name': self.sender.full_name,
            'receiver_id': self.receiver_id,
            'content': self.content,
            'is_read': self.is_read,
            'created_at': self.created_at.strftime('%b %d, %H:%M')
        }

    def __repr__(self):
        return f'<Message {self.id}: {self.sender_id}->{self.receiver_id}>'


class Review(db.Model):
    __tablename__ = 'reviews'

    id = db.Column(db.Integer, primary_key=True)
    exchange_id = db.Column(db.Integer, db.ForeignKey('exchange_requests.id'), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reviewee_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1 to 5
    comment = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, exchange_id=None, reviewer_id=None, reviewee_id=None, rating=5, comment='', created_at=None, **kwargs):
        super().__init__(**kwargs)
        if exchange_id is not None: self.exchange_id = exchange_id
        if reviewer_id is not None: self.reviewer_id = reviewer_id
        if reviewee_id is not None: self.reviewee_id = reviewee_id
        self.rating = rating
        self.comment = comment
        if created_at is not None: self.created_at = created_at

    def __repr__(self):
        return f'<Review {self.id}: {self.rating} stars for user {self.reviewee_id}>'


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    link = db.Column(db.String(255), nullable=True)
    icon = db.Column(db.String(50), default='bi-bell')
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, user_id=None, title='', message='', link=None, icon='bi-bell', is_read=False, created_at=None, **kwargs):
        super().__init__(**kwargs)
        if user_id is not None: self.user_id = user_id
        self.title = title
        self.message = message
        self.link = link
        self.icon = icon
        self.is_read = is_read
        if created_at is not None: self.created_at = created_at

    def __repr__(self):
        return f'<Notification {self.id} for user {self.user_id}>'


class Report(db.Model):
    __tablename__ = 'reports'

    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reported_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reason = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='pending')  # pending, resolved, dismissed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, reporter_id=None, reported_user_id=None, reason='', details=None, status='pending', created_at=None, **kwargs):
        super().__init__(**kwargs)
        if reporter_id is not None: self.reporter_id = reporter_id
        if reported_user_id is not None: self.reported_user_id = reported_user_id
        self.reason = reason
        self.details = details
        self.status = status
        if created_at is not None: self.created_at = created_at

    def __repr__(self):
        return f'<Report {self.id}: User {self.reported_user_id}>'
