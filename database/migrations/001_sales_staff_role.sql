-- Safe, repeatable role migration. Existing manager/staff values are retained;
-- application authorization maps both legacy values to the least-privilege role.
ALTER TABLE users
    MODIFY COLUMN role ENUM('admin', 'sales_staff', 'manager', 'staff')
    NOT NULL DEFAULT 'sales_staff';
