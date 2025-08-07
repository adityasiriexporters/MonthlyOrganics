# Email Column Removal Migration

## Overview
This migration removes the email column from the users table and updates all related code to eliminate email dependencies.

## Database Changes
```sql
-- Remove email column from users table
ALTER TABLE users DROP COLUMN IF EXISTS email;

-- Verify removal
SELECT column_name FROM information_schema.columns 
WHERE table_name = 'users' AND column_name = 'email';
-- Should return no results
```

## Code Changes Required
1. **User Model** (`models.py`):
   - Remove `email = db.Column(...)` field
   - Update `__repr__` method to use custom_id or id instead of email

2. **Service Layer** (`services/database.py`, `services/security.py`):
   - Remove email parameters from user creation methods
   - Update SQL queries to exclude email column

3. **Admin Panel** (`main.py`):
   - Update `get_all_customers_with_stats()` and `get_filtered_customers()`
   - Remove email from SQL SELECT statements and GROUP BY clauses
   - Update search functionality to exclude email searches

4. **Templates** (`templates/admin/`):
   - Update search placeholders from "Name or email" to "Search by name"

5. **CSV Export** (`main.py`):
   - Remove email column from CSV headers and data rows

## Rollback Instructions
If rollback is needed:

```sql
-- Add email column back (nullable to avoid data loss)
ALTER TABLE users ADD COLUMN email VARCHAR(120);

-- Create index
CREATE INDEX idx_users_email ON users(email);
```

## Verification Steps
1. Confirm email column is removed from database schema
2. Test admin panel customer listing and search
3. Verify user creation and lookup still works
4. Test CSV export functionality
5. Confirm phone encryption system remains intact

## Post-Migration Notes
- Users are now identified by phone numbers (encrypted) and custom IDs only
- Search functionality works on names only
- All existing functionality preserved except email-related features
- Phone encryption system maintained and operational

## Applied: August 7, 2025
Migration successfully completed with full verification.

## Automated Migration Script
An automated migration script exists at `utils/remove_email_migration.py` that:
- Safely drops email constraints and indexes
- Removes the email column using IF EXISTS
- Provides proper error handling and logging
- Can be run independently or as part of database initialization

## For Production Deployments
```bash
# Run the migration script manually if needed
python -c "
from utils.remove_email_migration import EmailRemovalMigration
EmailRemovalMigration.run_migration()
"
```