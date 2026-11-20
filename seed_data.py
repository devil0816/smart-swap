import os
from datetime import datetime, timedelta
from app import create_app
from extensions import db
from models import User, Skill, UserSkill, ExchangeRequest, Message, Review, Notification, Report

app = create_app()

SKILLS_CATALOG = [
    # Programming & Tech
    ('Python Programming', 'Programming & Tech', 'Learn core Python, data structures, automation, and backend development.', 'bi-code-slash'),
    ('Web Development (Flask/Django)', 'Programming & Tech', 'Build dynamic web applications and REST APIs using Python frameworks.', 'bi-globe'),
    ('React & Modern Frontend', 'Programming & Tech', 'Component-driven frontend development with modern React and JavaScript.', 'bi-layers'),
    ('Machine Learning & AI', 'Programming & Tech', 'Supervised learning, deep learning, PyTorch, Scikit-Learn and LLM fundamentals.', 'bi-cpu'),
    ('Flutter App Development', 'Programming & Tech', 'Cross-platform iOS and Android mobile app development with Dart.', 'bi-phone'),
    ('SQL & Database Design', 'Programming & Tech', 'Relational database schema modeling, queries, optimization, and indexing.', 'bi-database'),
    
    # Design & Creative
    ('UI/UX Design (Figma)', 'Design & Creative', 'User experience research, wireframing, high-fidelity prototypes and design systems.', 'bi-palette'),
    ('Graphic Design & Branding', 'Design & Creative', 'Logo design, brand identity, color theory, typography and vector graphics.', 'bi-brush'),
    ('Video Editing (Premiere/DaVinci)', 'Design & Creative', 'Video pacing, color grading, sound design and storytelling.', 'bi-film'),
    ('3D Modeling (Blender)', 'Design & Creative', 'Polygon modeling, materials, lighting and 3D rendering.', 'bi-box'),
    ('Photography & Light Room', 'Design & Creative', 'Composition, manual camera control, RAW image editing and color correction.', 'bi-camera'),

    # Languages
    ('Spanish (Conversational)', 'Languages', 'Everyday dialogue, grammar essentials, vocabulary and natural pronunciation.', 'bi-chat-left-quote'),
    ('French (Beginner to Intermediate)', 'Languages', 'French grammar, oral fluency, reading and cultural immersion.', 'bi-translate'),
    ('Italian (Conversational)', 'Languages', 'Italian phrases, idioms, expressive spoken conversation and grammar.', 'bi-chat-heart'),
    ('Japanese (JLPT N5-N3)', 'Languages', 'Hiragana, Katakana, Kanji, essential grammar structures and listening comprehension.', 'bi-flag'),
    ('German (Professional & Daily)', 'Languages', 'Business German, precise grammar, everyday conversation and cultural etiquette.', 'bi-globe2'),

    # Business & Marketing
    ('Digital Marketing & SEO', 'Business & Marketing', 'Search engine optimization, Google Ads, content funneling and analytics.', 'bi-graph-up-arrow'),
    ('Content Writing & Copywriting', 'Business & Marketing', 'High-converting sales copy, blog storytelling, editorial strategy and tone of voice.', 'bi-pencil-square'),
    ('Financial Modeling & Excel', 'Business & Marketing', 'DCF valuation, startup pro-forma financial models, PivotTables and formulas.', 'bi-calculator'),
    ('Public Speaking & Presentations', 'Business & Marketing', 'Stage presence, pitching ideas, overcoming stage fright and vocal projection.', 'bi-mic'),

    # Music & Arts
    ('Acoustic Guitar', 'Music & Arts', 'Chords, fingerpicking, strumming patterns, music theory and song performance.', 'bi-music-note-beamed'),
    ('Classical Piano', 'Music & Arts', 'Sheet music reading, finger technique, scales, and classical/contemporary repertoire.', 'bi-soundwave'),
    ('Music Production (Ableton/Logic)', 'Music & Arts', 'Beat making, synthesizers, mixing, mastering and digital audio workstations.', 'bi-sliders'),
    ('Drawing & Sketching', 'Music & Arts', 'Perspective, shading, anatomy, pencil rendering and gesture drawing.', 'bi-pen'),

    # Health & Fitness
    ('Yoga & Mindfulness', 'Health & Fitness', 'Hatha/Vinyasa flow, breathwork, posture alignment and meditation techniques.', 'bi-heart-pulse'),
    ('Nutrition & Meal Planning', 'Health & Fitness', 'Macronutrients, healthy meal prep, energy optimization and dietary habits.', 'bi-egg-fried')
]


def seed():
    with app.app_context():
        print("Clearing existing database tables...")
        db.drop_all()
        db.create_all()

        print("Seeding skills catalog...")
        skill_map = {}
        for name, category, desc, icon in SKILLS_CATALOG:
            skill = Skill(name=name, category=category, description=desc, icon=icon)
            db.session.add(skill)
            skill_map[name] = skill
        db.session.flush()

        print("Creating users...")
        # 1. Admin User
        admin = User(
            username='admin',
            email='admin@smartswap.com',
            full_name='Platform Administrator',
            headline='Smart Swap Team & Community Steward',
            bio='Ensuring a safe, equitable, and vibrant peer-to-peer knowledge sharing community.',
            location='Global Operations',
            availability='Flexible',
            is_admin=True
        )
        admin.set_password('admin123')
        db.session.add(admin)

        # 2. Alex Chen
        alex = User(
            username='alex_chen',
            email='alex@example.com',
            full_name='Alex Chen',
            headline='Machine Learning Researcher & Python Developer',
            bio='Software engineer by day, passionate open-source contributor. I love explaining complex algorithms simply and am eager to polish my design skills.',
            location='San Francisco, CA (Remote)',
            availability='Flexible'
        )
        alex.set_password('password123')
        db.session.add(alex)

        # 3. Sarah Jenkins
        sarah = User(
            username='sarah_ux',
            email='sarah@example.com',
            full_name='Sarah Jenkins',
            headline='Senior Product Designer & Design System Specialist',
            bio='7+ years in UI/UX creating software experiences. Wanting to learn Python and backend basics so I can build functional prototypes myself!',
            location='New York, NY (Remote)',
            availability='Flexible'
        )
        sarah.set_password('password123')
        db.session.add(sarah)

        # 4. Marco Rossi
        marco = User(
            username='marco_rossi',
            email='marco@example.com',
            full_name='Marco Rossi',
            headline='Polyglot Linguist & Language Educator',
            bio='Native Italian speaker fluent in Spanish and French. I believe conversation is the true secret to fluency. Looking to pick up acoustic guitar!',
            location='Rome / Remote',
            availability='Weekday Evenings'
        )
        marco.set_password('password123')
        db.session.add(marco)

        # 5. Priya Patel
        priya = User(
            username='priya_patel',
            email='priya@example.com',
            full_name='Priya Patel',
            headline='Frontend Engineer & React Enthusiast',
            bio='React, TypeScript, and CSS animation wizard. Seeking to understand Machine Learning fundamentals and AI integration in modern web apps.',
            location='Bangalore / Remote',
            availability='Flexible'
        )
        priya.set_password('password123')
        db.session.add(priya)

        # 6. Liam Davis
        liam = User(
            username='liam_davis',
            email='liam@example.com',
            full_name='Liam Davis',
            headline='Audio Engineer & Session Guitarist',
            bio='Recorded with indie bands and scored documentaries. Happy to teach guitar from scratch or music production in Ableton. Excited to learn video editing!',
            location='London, UK (Remote)',
            availability='Weekends Only'
        )
        liam.set_password('password123')
        db.session.add(liam)

        # 7. Elena Rostova
        elena = User(
            username='elena_rostova',
            email='elena@example.com',
            full_name='Elena Rostova',
            headline='Growth Marketer & Copywriter',
            bio='Helping startups find product-market fit. I can help you scale user acquisition, improve your pitch copy, and master SEO in exchange for French lessons.',
            location='Berlin / Remote',
            availability='Weekday Mornings'
        )
        elena.set_password('password123')
        db.session.add(elena)

        db.session.flush()

        print("Attaching user skills (teaching & learning)...")
        # Alex's skills
        db.session.add(UserSkill(user_id=alex.id, skill_id=skill_map['Python Programming'].id, skill_type='teach', proficiency_level='Expert', experience_years=6, notes='Data structures, OOP, API development, script automation'))
        db.session.add(UserSkill(user_id=alex.id, skill_id=skill_map['Machine Learning & AI'].id, skill_type='teach', proficiency_level='Advanced', experience_years=4, notes='PyTorch, NLP, practical model fine-tuning'))
        db.session.add(UserSkill(user_id=alex.id, skill_id=skill_map['UI/UX Design (Figma)'].id, skill_type='learn', proficiency_level='Beginner', experience_years=0, notes='Want to learn design fundamentals, Figma auto-layout and wireframing'))
        db.session.add(UserSkill(user_id=alex.id, skill_id=skill_map['Spanish (Conversational)'].id, skill_type='learn', proficiency_level='Beginner', experience_years=1, notes='Travel conversation and everyday fluency'))

        # Sarah's skills (PERFECT MATCH WITH ALEX!)
        db.session.add(UserSkill(user_id=sarah.id, skill_id=skill_map['UI/UX Design (Figma)'].id, skill_type='teach', proficiency_level='Expert', experience_years=7, notes='Design systems, user research, wireframing, prototype testing'))
        db.session.add(UserSkill(user_id=sarah.id, skill_id=skill_map['Graphic Design & Branding'].id, skill_type='teach', proficiency_level='Advanced', experience_years=5, notes='Visual identity, typography, color harmony and vector design'))
        db.session.add(UserSkill(user_id=sarah.id, skill_id=skill_map['Python Programming'].id, skill_type='learn', proficiency_level='Beginner', experience_years=0, notes='Starting from scratch: scripting, variables, web scrapers'))
        db.session.add(UserSkill(user_id=sarah.id, skill_id=skill_map['Web Development (Flask/Django)'].id, skill_type='learn', proficiency_level='Beginner', experience_years=0, notes='Connecting backend routes to my frontend mockups'))

        # Marco's skills
        db.session.add(UserSkill(user_id=marco.id, skill_id=skill_map['Italian (Conversational)'].id, skill_type='teach', proficiency_level='Expert', experience_years=10, notes='Native Italian speaker, grammar, pronunciation, literature'))
        db.session.add(UserSkill(user_id=marco.id, skill_id=skill_map['Spanish (Conversational)'].id, skill_type='teach', proficiency_level='Advanced', experience_years=8, notes='Castilian and Latin American conversational nuances'))
        db.session.add(UserSkill(user_id=marco.id, skill_id=skill_map['Acoustic Guitar'].id, skill_type='learn', proficiency_level='Beginner', experience_years=0, notes='Learn basic chords and folk song fingerpicking'))

        # Priya's skills
        db.session.add(UserSkill(user_id=priya.id, skill_id=skill_map['React & Modern Frontend'].id, skill_type='teach', proficiency_level='Advanced', experience_years=4, notes='Hooks, state management, Tailwind CSS, performance tuning'))
        db.session.add(UserSkill(user_id=priya.id, skill_id=skill_map['Machine Learning & AI'].id, skill_type='learn', proficiency_level='Beginner', experience_years=0, notes='Integrating LLM APIs and understanding vector embeddings'))
        db.session.add(UserSkill(user_id=priya.id, skill_id=skill_map['Yoga & Mindfulness'].id, skill_type='learn', proficiency_level='Intermediate', experience_years=2, notes='Mindful breathing and posture flow for desk workers'))

        # Liam's skills
        db.session.add(UserSkill(user_id=liam.id, skill_id=skill_map['Acoustic Guitar'].id, skill_type='teach', proficiency_level='Expert', experience_years=12, notes='Acoustic/electric, fretboard harmony, ear training, rhythm'))
        db.session.add(UserSkill(user_id=liam.id, skill_id=skill_map['Music Production (Ableton/Logic)'].id, skill_type='teach', proficiency_level='Expert', experience_years=9, notes='Beat construction, EQ/compression, vocal mixing, synthesis'))
        db.session.add(UserSkill(user_id=liam.id, skill_id=skill_map['Spanish (Conversational)'].id, skill_type='learn', proficiency_level='Beginner', experience_years=0, notes='Basic Spanish for international music tours'))
        db.session.add(UserSkill(user_id=liam.id, skill_id=skill_map['Video Editing (Premiere/DaVinci)'].id, skill_type='learn', proficiency_level='Beginner', experience_years=0, notes='Editing YouTube guitar tutorials and music video clips'))

        # Elena's skills
        db.session.add(UserSkill(user_id=elena.id, skill_id=skill_map['Digital Marketing & SEO'].id, skill_type='teach', proficiency_level='Expert', experience_years=8, notes='Organic growth, technical SEO, keyword research, conversion rate optimization'))
        db.session.add(UserSkill(user_id=elena.id, skill_id=skill_map['Content Writing & Copywriting'].id, skill_type='teach', proficiency_level='Advanced', experience_years=6, notes='Landing page copy, email sequences, high-impact storytelling'))
        db.session.add(UserSkill(user_id=elena.id, skill_id=skill_map['Graphic Design & Branding'].id, skill_type='learn', proficiency_level='Intermediate', experience_years=1, notes='Elevating social media visuals and presentation slide decks'))
        db.session.add(UserSkill(user_id=elena.id, skill_id=skill_map['French (Beginner to Intermediate)'].id, skill_type='learn', proficiency_level='Beginner', experience_years=0, notes='Conversational French for relocation and business'))

        db.session.flush()

        print("Seeding sample exchanges...")
        # 1. Completed Exchange between Alex and Sarah
        completed_ex = ExchangeRequest(
            sender_id=alex.id,
            receiver_id=sarah.id,
            offered_skill_id=skill_map['Python Programming'].id,
            requested_skill_id=skill_map['UI/UX Design (Figma)'].id,
            status='completed',
            message="Hi Sarah! I saw you want to learn Python fundamentals. I've been a software engineer for 6 years and would love to exchange 4 hours of Python mentoring for some hands-on Figma and UI/UX guidance for my web app!",
            schedule_notes='Remote via Google Meet on Saturday mornings',
            created_at=datetime.utcnow() - timedelta(days=20),
            completed_at=datetime.utcnow() - timedelta(days=2)
        )
        db.session.add(completed_ex)
        db.session.flush()

        # Messages in Alex & Sarah's exchange
        db.session.add(Message(sender_id=alex.id, receiver_id=sarah.id, exchange_id=completed_ex.id, content="Hi Sarah! Excited to swap skills. I prepared a syllabus for our Python crash course: variables, data structures, and small scripts.", created_at=datetime.utcnow() - timedelta(days=19)))
        db.session.add(Message(sender_id=sarah.id, receiver_id=alex.id, exchange_id=completed_ex.id, content="Sounds incredible Alex! In return, I have our Figma workspace ready with auto-layout templates and component libraries.", created_at=datetime.utcnow() - timedelta(days=18)))
        db.session.add(Message(sender_id=sarah.id, receiver_id=alex.id, exchange_id=completed_ex.id, content="That session on list comprehensions was so enlightening! Thank you!", created_at=datetime.utcnow() - timedelta(days=5)))
        db.session.add(Message(sender_id=alex.id, receiver_id=sarah.id, exchange_id=completed_ex.id, content="And your feedback on my app's navigation wireframes transformed the whole UX. Let's mark this exchange as completed!", created_at=datetime.utcnow() - timedelta(days=3)))

        # Reviews for completed exchange
        db.session.add(Review(
            exchange_id=completed_ex.id,
            reviewer_id=alex.id,
            reviewee_id=sarah.id,
            rating=5,
            comment="Sarah is a world-class designer and a patient, engaging teacher! In just a few sessions she completely demystified Figma components and UX workflows for me. Highly recommended exchange partner!",
            created_at=datetime.utcnow() - timedelta(days=2)
        ))
        db.session.add(Review(
            exchange_id=completed_ex.id,
            reviewer_id=sarah.id,
            reviewee_id=alex.id,
            rating=5,
            comment="Alex broke down Python concepts with crystal clarity and real-world analogies. I went from fearing code to building my own automated CSV parser in two weeks! An absolute 10/10 mentor.",
            created_at=datetime.utcnow() - timedelta(days=2)
        ))

        # 2. Active Exchange between Marco and Liam
        active_ex = ExchangeRequest(
            sender_id=marco.id,
            receiver_id=liam.id,
            offered_skill_id=skill_map['Spanish (Conversational)'].id,
            requested_skill_id=skill_map['Acoustic Guitar'].id,
            status='accepted',
            message="Ciao Liam! I would love to learn acoustic guitar chords, and in exchange I can offer native-level Spanish conversation lessons.",
            schedule_notes='Tuesdays & Thursdays 7 PM GMT',
            created_at=datetime.utcnow() - timedelta(days=6)
        )
        db.session.add(active_ex)
        db.session.flush()

        db.session.add(Message(sender_id=marco.id, receiver_id=liam.id, exchange_id=active_ex.id, content="Hi Liam! Looking forward to our next guitar lesson on barre chords this Thursday.", created_at=datetime.utcnow() - timedelta(days=2)))
        db.session.add(Message(sender_id=liam.id, receiver_id=marco.id, exchange_id=active_ex.id, content="Hey Marco! Practicing the Spanish phrases you sent. Thursday at 7 works great for me!", created_at=datetime.utcnow() - timedelta(days=1)))

        # 3. Pending Incoming Request: Priya -> Alex
        pending_ex = ExchangeRequest(
            sender_id=priya.id,
            receiver_id=alex.id,
            offered_skill_id=skill_map['React & Modern Frontend'].id,
            requested_skill_id=skill_map['Machine Learning & AI'].id,
            status='pending',
            message="Hi Alex! I saw your impressive ML background. I'm building an AI dashboard and need help with model integration. In exchange, I can teach you advanced React, Tailwind, and frontend architectures!",
            schedule_notes='Flexible / Weekend afternoons',
            created_at=datetime.utcnow() - timedelta(hours=4)
        )
        db.session.add(pending_ex)

        # 4. Pending Request: Elena -> Sarah
        pending_ex2 = ExchangeRequest(
            sender_id=elena.id,
            receiver_id=sarah.id,
            offered_skill_id=skill_map['Digital Marketing & SEO'].id,
            requested_skill_id=skill_map['Graphic Design & Branding'].id,
            status='pending',
            message="Hi Sarah! I'd love to swap growth marketing and SEO strategy for some guidance on brand guidelines and color theory for my marketing consultancy.",
            schedule_notes='Remote / Morning sessions',
            created_at=datetime.utcnow() - timedelta(days=1)
        )
        db.session.add(pending_ex2)

        # Notifications
        db.session.add(Notification(
            user_id=alex.id,
            title='New Skill Exchange Request',
            message='Priya Patel wants to swap React Frontend for your Machine Learning expertise!',
            link='/exchanges',
            icon='bi-arrow-left-right',
            is_read=False,
            created_at=datetime.utcnow() - timedelta(hours=4)
        ))
        db.session.add(Notification(
            user_id=alex.id,
            title='Review Received! ⭐',
            message='Sarah Jenkins left you a 5-star review for Python Programming!',
            link=f'/u/{alex.username}',
            icon='bi-star-fill',
            is_read=True,
            created_at=datetime.utcnow() - timedelta(days=2)
        ))

        db.session.commit()
        print("Database successfully seeded with realistic sample data!")


if __name__ == '__main__':
    seed()
