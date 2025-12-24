#!/usr/bin/env python3
"""
Script to hash plain text passwords in the database.
This fixes users that were created directly in Railway table interface.
"""

import sys
sys.path.append('/Users/fahadalmanee/pythonProject')

from database import SessionLocal
from models.user_db import UserDB
from services.auth_service import hash_password, verify_password
from sqlalchemy import text

def fix_plaintext_passwords():
    """Find and hash all plain text passwords in the database"""
    db = SessionLocal()
    
    try:
        # Get all users
        users = db.query(UserDB).all()
        
        print("🔍 Checking for plain text passwords...")
        print("=" * 60)
        
        fixed_count = 0
        skipped_count = 0
        
        for user in users:
            password_hash = user.password_hash
            
            # Check if password is already hashed (pbkdf2_sha256 format)
            if password_hash and password_hash.startswith("$pbkdf2-sha256$"):
                print(f"✅ User '{user.invoice_no}' - Password already hashed")
                skipped_count += 1
                continue
            
            # If password_hash looks like plain text (no $ prefix), we need to hash it
            if password_hash and not password_hash.startswith("$"):
                print(f"⚠️  User '{user.invoice_no}' - Found plain text password: '{password_hash}'")
                
                # Hash the plain text password
                hashed = hash_password(password_hash)
                
                # Update the user
                user.password_hash = hashed
                db.commit()
                
                # Verify it worked
                if verify_password(password_hash, hashed):
                    print(f"✅ User '{user.invoice_no}' - Password hashed successfully")
                    print(f"   New hash: {hashed[:50]}...")
                    fixed_count += 1
                else:
                    print(f"❌ User '{user.invoice_no}' - Verification failed!")
                    db.rollback()
            else:
                print(f"⚠️  User '{user.invoice_no}' - Empty or invalid password hash")
        
        print("=" * 60)
        print(f"📊 Summary:")
        print(f"   ✅ Fixed: {fixed_count} users")
        print(f"   ⏭️  Skipped (already hashed): {skipped_count} users")
        print(f"   📝 Total checked: {len(users)} users")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("🔐 Password Hashing Fix Script")
    print("=" * 60)
    print()
    
    # Allow non-interactive mode with --yes flag
    if len(sys.argv) > 1 and sys.argv[1] == "--yes":
        print("⚠️  Running in non-interactive mode...")
        print()
        fix_plaintext_passwords()
        print()
        print("✅ Done!")
    else:
        confirmation = input("⚠️  This will hash all plain text passwords. Continue? (yes/no): ").strip().lower()
        
        if confirmation != "yes":
            print("❌ Cancelled.")
            sys.exit(0)
        
        print()
        fix_plaintext_passwords()
        print()
        print("✅ Done!")

