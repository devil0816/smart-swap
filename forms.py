from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, SelectField, IntegerField, HiddenField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, NumberRange, ValidationError
from models import User, Skill


SKILL_CATEGORIES = [
    ('Programming & Tech', 'Programming & Tech'),
    ('Design & Creative', 'Design & Creative'),
    ('Languages', 'Languages'),
    ('Business & Marketing', 'Business & Marketing'),
    ('Music & Arts', 'Music & Arts'),
    ('Health & Fitness', 'Health & Fitness'),
    ('Academics & Writing', 'Academics & Writing'),
    ('Other', 'Other')
]

AVAILABILITY_CHOICES = [
    ('Flexible', 'Flexible Schedule'),
    ('Weekends Only', 'Weekends Only'),
    ('Weekday Evenings', 'Weekday Evenings'),
    ('Weekday Mornings', 'Weekday Mornings'),
    ('Remote / Online Only', 'Remote / Online Only')
]

PROFICIENCY_CHOICES = [
    ('Beginner', 'Beginner (Basic fundamentals)'),
    ('Intermediate', 'Intermediate (Practical experience)'),
    ('Advanced', 'Advanced (Deep expertise)'),
    ('Expert', 'Expert (Professional / Mastery)')
]


class LoginForm(FlaskForm):
    username_or_email = StringField('Username or Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=30)])
    email = StringField('Email Address', validators=[DataRequired(), Email(), Length(max=120)])
    full_name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6, message='Password must be at least 6 characters')])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password', message='Passwords must match')])
    terms = BooleanField('I agree to the Terms of Service & Knowledge Exchange Ethics', validators=[DataRequired(message='You must agree to continue')])
    submit = SubmitField('Create Account')

    def validate_username(self, username):
        user = User.query.filter(User.username.ilike(username.data)).first()
        if user:
            raise ValidationError('This username is already taken. Please choose another.')

    def validate_email(self, email):
        user = User.query.filter(User.email.ilike(email.data)).first()
        if user:
            raise ValidationError('This email is already registered. Please sign in.')


class ProfileEditForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    headline = StringField('Professional Headline', validators=[Length(max=150)])
    bio = TextAreaField('About You / Bio', validators=[Length(max=1000)])
    location = StringField('Location (City, Country or Remote)', validators=[Length(max=100)])
    availability = SelectField('Preferred Availability', choices=AVAILABILITY_CHOICES)
    avatar = FileField('Profile Picture', validators=[FileAllowed(['jpg', 'png', 'jpeg', 'webp', 'gif'], 'Images only!')])
    submit = SubmitField('Save Profile')


class AddSkillForm(FlaskForm):
    skill_id = SelectField('Select Skill', coerce=int, validators=[DataRequired()])
    skill_type = SelectField('Skill Type', choices=[('teach', 'I want to Teach this skill'), ('learn', 'I want to Learn this skill')], validators=[DataRequired()])
    proficiency_level = SelectField('Proficiency / Target Level', choices=PROFICIENCY_CHOICES, validators=[DataRequired()])
    experience_years = IntegerField('Years of Experience / Study', default=1, validators=[NumberRange(min=0, max=50)])
    notes = TextAreaField('Notes / What you can share or what you want to focus on', validators=[Length(max=300)])
    submit = SubmitField('Add Skill to Profile')


class QuickCreateSkillForm(FlaskForm):
    name = StringField('Skill Name', validators=[DataRequired(), Length(min=2, max=100)])
    category = SelectField('Category', choices=SKILL_CATEGORIES, validators=[DataRequired()])
    description = TextAreaField('Short Description', validators=[Length(max=255)])
    submit = SubmitField('Create New Skill')

    def validate_name(self, name):
        existing = Skill.query.filter(Skill.name.ilike(name.data.strip())).first()
        if existing:
            raise ValidationError('This skill already exists in the platform directory.')


class ExchangeRequestForm(FlaskForm):
    offered_skill_id = SelectField('Skill You Will Teach / Offer', coerce=int, validators=[DataRequired()])
    requested_skill_id = SelectField('Skill You Want Them to Teach You', coerce=int, validators=[DataRequired()])
    message = TextAreaField('Introduction & Exchange Proposal', validators=[DataRequired(), Length(min=10, max=1000)])
    schedule_notes = StringField('Proposed Schedule or Preferred Mode (e.g. Google Meet, Discord, Weekends)', default='Remote / Flexible', validators=[Length(max=255)])
    submit = SubmitField('Send Exchange Request')


class MessageForm(FlaskForm):
    content = TextAreaField('Message', validators=[DataRequired(), Length(min=1, max=2000)])
    submit = SubmitField('Send')


class ReviewForm(FlaskForm):
    rating = SelectField('Rating', choices=[
        ('5', '★★★★★ 5 - Outstanding Mentor!'),
        ('4', '★★★★☆ 4 - Great Knowledge Exchange'),
        ('3', '★★★☆☆ 3 - Good Experience'),
        ('2', '★★☆☆☆ 2 - Below Expectations'),
        ('1', '★☆☆☆☆ 1 - Poor Experience')
    ], validators=[DataRequired()])
    comment = TextAreaField('Your Feedback & Review', validators=[DataRequired(), Length(min=10, max=1000)])
    submit = SubmitField('Submit Review')


class ReportUserForm(FlaskForm):
    reason = SelectField('Reason for Report', choices=[
        ('Inappropriate Behavior', 'Inappropriate or abusive behavior'),
        ('No-show / Spam', 'Repeated no-show or spam requests'),
        ('Commercial Solicitation', 'Demanded money instead of skill exchange'),
        ('Misrepresentation', 'Falsified skills or identity'),
        ('Other', 'Other violation')
    ], validators=[DataRequired()])
    details = TextAreaField('Additional Details / Evidence', validators=[DataRequired(), Length(min=10, max=1000)])
    submit = SubmitField('Submit Report')
