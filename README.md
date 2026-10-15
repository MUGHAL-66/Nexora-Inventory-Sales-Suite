# Nexora Inventory & Sales Suite

A Python 3.12+ inventory and sales application built with Streamlit and MySQL 8+. The current implementation includes authenticated access, role-checked product/category and customer/supplier directories, audited stock adjustments, dashboard analytics, sales billing, purchase workflows, and invoice PDF generation.

## Current implementation status

Verified in the workspace:

- Streamlit app shell, light maroon-and-rose-gold enterprise theme, and role-aware navigation
- Authentication with bcrypt hashing and active-user revalidation
- Admin, Manager, Sales Staff, and Staff account roles with distinct role labels and centralized permissions; Managers have operational supplier, inventory-history, and purchase workflows, while Sales Staff keeps a focused sales workspace and Staff retains its existing limited access
- Product/category management, customer/supplier management, and audited stock adjustments
- Dashboard KPIs, charts, low-stock alerts, and date-filtered sales metrics
- Sales billing flow, invoice history, and invoice PDF export
- Purchase workflow, supplier cost tracking, and stock increase records
- Inventory ledger and transaction history

Reporting and settings are not registered routes in the current application; this redesign does not add unsupported pages or fabricated data.

## Included foundation

- Streamlit entry point and reusable light workspace, maroon sidebar, rose-gold accent, and two-panel sign-in design system.
- Environment-driven MySQL configuration, validated database identifiers, connection lifecycle management, and safe schema initialization.
- Normalized MySQL schema for users, categories, products, customers, suppliers, sales, sale items, purchases, purchase items, payments, and auditable stock transactions.
- Opt-in, idempotent sample category and products with unmistakable `[DEMO]` labels.
- Bcrypt-based login/logout with database-revalidated sessions and centralized role permissions enforced in service functions. Sessions retain the exact database role so sidebar labels and dashboard profiles remain accurate.
- Admin user management, including self-deactivation and last-active-admin protections.
- Searchable product and contact directories, safe deactivation instead of deletes, product SKU uniqueness, and audited stock adjustment transactions.
- Live dashboard counts, date-filtered totals, Plotly sales and product charts, low-stock alerts, recent activity, and gross profit only when all selected sales have sale-item cost data.
- Input/formatting helpers and a small PDF table document builder for later workflows.
- Non-destructive `database/migrations/001_sales_staff_role.sql` migration, automatically applied by the initializer. The database stores `admin`, `manager`, `sales_staff`, and `staff` as distinct role identifiers.

## Requirements

- Python 3.12 or later
- MySQL Server 8.0 or later
- MySQL account allowed to create the application database during first-time initialization; the runtime account needs normal schema read/write privileges

## Local setup

Run commands from the workspace root.

1. Create and activate a virtual environment:

   ```powershell
   py -3.12 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install dependencies and create local settings:

   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   Copy-Item .env.example .env
   ```

3. Edit `.env` with your local MySQL host and credentials. Do not commit `.env`. The DB account must be able to create the configured database the first time `init_db` is run.

4. Initialize the schema. This uses `CREATE DATABASE IF NOT EXISTS` and `CREATE TABLE IF NOT EXISTS`; it does not drop tables or existing rows:

   ```powershell
   python -m database.init_db
   ```

   Alternatively, an administrator can create the database, apply `database/schema.sql`, and then apply every numbered migration in `database/migrations/` in order with a MySQL client. The schema file intentionally contains table definitions only.

5. Create the first admin. Set `INITIAL_ADMIN_USERNAME`, `INITIAL_ADMIN_EMAIL`, and `INITIAL_ADMIN_FULL_NAME` in `.env`, then run:

   ```powershell
   python -m database.create_admin
   ```

   The command securely prompts for a matching password of at least 12 characters (and no more than bcrypt's 72 UTF-8 byte limit). It does not create a known/default password and does not reset existing accounts.

6. (Optional) Add sample catalog data for a local demo only:

   ```powershell
   python -m database.seed_data --confirm-demo-data
   ```

   Inserts are `INSERT IGNORE`, use `[DEMO]` labels and `DEMO-` SKUs, and do not overwrite existing rows. Do not seed demo records in production.

7. Start the application and sign in with the admin username and password:

   ```powershell
   streamlit run app.py
   ```

## Configuration

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `DB_HOST` | Yes | — | MySQL server hostname |
| `DB_PORT` | No | `3306` | MySQL TCP port |
| `DB_USER` | Yes | — | MySQL application/setup username |
| `DB_PASSWORD` | Yes | — | MySQL password |
| `DB_NAME` | No | `inventory_management` | Database name (letters, digits, underscores) |
| `DB_CONNECTION_TIMEOUT` | No | `5` | Connect timeout in seconds |
| `INITIAL_ADMIN_USERNAME` | For admin setup | — | Initial administrator username |
| `INITIAL_ADMIN_EMAIL` | For admin setup | — | Initial administrator email |
| `INITIAL_ADMIN_FULL_NAME` | For admin setup | — | Initial administrator display name |

The dashboard/login area shows a setup or availability notice rather than sample data when the database is unconfigured or unavailable. Detailed connection errors are logged server-side; credentials and exception details are not shown in the UI.

## Development and tests

```powershell
python -m pytest
python -m compileall -q app.py database pages services utils tests
```

Tests for configuration, authentication, role authorization, validation, and service query behavior use isolated mocks and do not require a running MySQL server. Schema initialization, account creation, and real database-backed pages require a reachable configured MySQL 8+ server.

## Architecture

```text
app.py                  Authenticated Streamlit bootstrap and sanitized DB boundary
pages/                  Login, dashboard, catalog, contact, stock, and admin pages
services/               Auth, DB-backed permissions, catalog, contacts, and dashboard queries
database/                MySQL config, schema, role migration and setup tools
utils/                  Validation, formatting, PDF, and theme components
assets/                 Local brand asset notes
tests/                  Configuration and helper tests
```

Sales billing, purchase creation/receiving, and the inventory transaction history are available in the current workspace. Reporting and settings routes are not included in the current page registry.

## Security notes

- Keep `.env` private. Use a least-privilege database account after initial schema creation.
- Values in CRUD and analytics queries are parameterized. Dynamic schema identifiers are restricted to alphanumeric characters and underscores.
- Passwords are bcrypt-hashed. Admin bootstrap is an explicit, interactive insert; user sessions retain only the user ID and re-check active status and role against MySQL on each rerun.
- Every service operation re-reads the actor's active role from MySQL before enforcing its role rules. Sales Staff, Manager, and Staff cannot call administrator-only services even if they bypass the UI.
- Managers can create purchases using the product's stored catalog cost, but supplier purchase totals, purchase line costs, and gross-profit metrics remain Admin-only. Managers can view inventory history and manage supplier contacts; manual stock adjustments and user administration remain Admin-only.
- Product stock is not editable on catalog forms; only the administrator stock-adjustment service changes it and appends an inventory transaction.
- Use TLS for database connections outside a trusted local development environment. Production deployment additionally needs secret management, authentication/session protections, backups, monitoring, and operational review.
