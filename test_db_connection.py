"""
Database Connection & Schema Test Script
Tests whether your application connects to Supabase (PostgreSQL) or local SQLite,
and verifies schema connectivity.
"""
import sys
from app import create_app
from extensions import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    db_uri = app.config['SQLALCHEMY_DATABASE_URI']
    # Mask password for secure display
    masked_uri = db_uri
    if '@' in db_uri and '://' in db_uri:
        protocol, rest = db_uri.split('://', 1)
        user_pass, host_db = rest.split('@', 1)
        if ':' in user_pass:
            user = user_pass.split(':', 1)[0]
            masked_uri = f"{protocol}://{user}:****@{host_db}"
    
    print("\n" + "=" * 60)
    print(" Smart Swap - Database Connection Diagnostic")
    print("=" * 60)
    print(f"Target Database URI: {masked_uri}")
    
    is_supabase = "supabase" in db_uri.lower() or "postgres" in db_uri.lower()
    if is_supabase:
        print("Engine Type: ⚡ Supabase (PostgreSQL)")
    else:
        print("Engine Type: 📁 Local SQLite (fallback)")

    print("\nTesting connection...")
    try:
        with db.engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
            print("✅ Connection test SUCCESSFUL! (SELECT 1 returned: %s)" % result)
            
            # If PostgreSQL / Supabase, check PostgreSQL version
            if is_supabase:
                version = conn.execute(text("SELECT version()")).scalar()
                print(f"PostgreSQL Version: {version}")

        print("\nChecking database tables...")
        from models import User, Skill, UserSkill, ExchangeRequest
        user_count = User.query.count()
        skill_count = Skill.query.count()
        print(f"Existing Users: {user_count}")
        print(f"Existing Skills in Catalog: {skill_count}")
        
        if skill_count == 0:
            print("\n💡 Tip: Your database is empty. Run this command to populate initial skills and demo users:")
            print("    .\\venv\\Scripts\\python seed_data.py")
        else:
            print("\n🎉 Database is ready and fully populated!")

    except Exception as e:
        print("\n❌ Connection FAILED:")
        print(f"Error details: {e}")
        if is_supabase:
            print("\nTroubleshooting Supabase connection:")
            print("1. Double check the database password in your .env file.")
            print("2. Ensure you selected 'Session' or 'Transaction' mode pooler (IPv4 compatible).")
            print("3. Check Supabase Dashboard > Database > Connection string.")
        sys.exit(1)

    print("=" * 60 + "\n")
