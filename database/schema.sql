-- Nexora Inventory & Sales Suite schema for MySQL 8+.
-- All objects are created only when absent; this file never drops or truncates data.

CREATE TABLE IF NOT EXISTS users (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    username VARCHAR(80) NOT NULL,
    email VARCHAR(254) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(160) NOT NULL,
    role ENUM('admin', 'sales_staff', 'manager', 'staff') NOT NULL DEFAULT 'sales_staff',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_users_username (username),
    UNIQUE KEY uq_users_email (email),
    KEY idx_users_role_active (role, is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS categories (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    name VARCHAR(120) NOT NULL,
    description TEXT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_categories_name (name),
    KEY idx_categories_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS customers (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    customer_code VARCHAR(40) NOT NULL,
    name VARCHAR(160) NOT NULL,
    email VARCHAR(254) NULL,
    phone VARCHAR(40) NULL,
    address TEXT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_customers_code (customer_code),
    KEY idx_customers_name (name),
    KEY idx_customers_email (email),
    KEY idx_customers_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS suppliers (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    supplier_code VARCHAR(40) NOT NULL,
    name VARCHAR(160) NOT NULL,
    email VARCHAR(254) NULL,
    phone VARCHAR(40) NULL,
    address TEXT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_suppliers_code (supplier_code),
    KEY idx_suppliers_name (name),
    KEY idx_suppliers_email (email),
    KEY idx_suppliers_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS products (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    sku VARCHAR(64) NOT NULL,
    name VARCHAR(180) NOT NULL,
    category_id BIGINT UNSIGNED NULL,
    description TEXT NULL,
    cost_price DECIMAL(13, 2) NOT NULL DEFAULT 0.00,
    selling_price DECIMAL(13, 2) NOT NULL DEFAULT 0.00,
    current_stock DECIMAL(13, 3) NOT NULL DEFAULT 0.000,
    reorder_level DECIMAL(13, 3) NOT NULL DEFAULT 0.000,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_products_sku (sku),
    KEY idx_products_category_active (category_id, is_active),
    KEY idx_products_stock (current_stock, reorder_level),
    CONSTRAINT fk_products_category FOREIGN KEY (category_id)
        REFERENCES categories (id) ON DELETE SET NULL,
    CONSTRAINT chk_products_cost CHECK (cost_price >= 0),
    CONSTRAINT chk_products_selling CHECK (selling_price >= 0),
    CONSTRAINT chk_products_stock CHECK (current_stock >= 0),
    CONSTRAINT chk_products_reorder CHECK (reorder_level >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS sales (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    invoice_number VARCHAR(48) NOT NULL,
    customer_id BIGINT UNSIGNED NULL,
    staff_user_id BIGINT UNSIGNED NOT NULL,
    subtotal DECIMAL(13, 2) NOT NULL,
    discount DECIMAL(13, 2) NOT NULL DEFAULT 0.00,
    total DECIMAL(13, 2) NOT NULL,
    payment_status ENUM('unpaid', 'partially_paid', 'paid', 'refunded') NOT NULL DEFAULT 'unpaid',
    sale_status ENUM('draft', 'completed', 'voided', 'refunded') NOT NULL DEFAULT 'completed',
    notes TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_sales_invoice (invoice_number),
    KEY idx_sales_customer (customer_id),
    KEY idx_sales_staff (staff_user_id),
    KEY idx_sales_created_status (created_at, sale_status, payment_status),
    CONSTRAINT fk_sales_customer FOREIGN KEY (customer_id)
        REFERENCES customers (id) ON DELETE SET NULL,
    CONSTRAINT fk_sales_staff FOREIGN KEY (staff_user_id)
        REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT chk_sales_amounts CHECK (subtotal >= 0 AND discount >= 0 AND total >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS sale_items (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    sale_id BIGINT UNSIGNED NOT NULL,
    product_id BIGINT UNSIGNED NOT NULL,
    quantity DECIMAL(13, 3) NOT NULL,
    unit_price DECIMAL(13, 2) NOT NULL,
    unit_cost DECIMAL(13, 2) NOT NULL,
    line_discount DECIMAL(13, 2) NOT NULL DEFAULT 0.00,
    line_total DECIMAL(13, 2) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_sale_items_sale_product (sale_id, product_id),
    KEY idx_sale_items_product (product_id),
    CONSTRAINT fk_sale_items_sale FOREIGN KEY (sale_id)
        REFERENCES sales (id) ON DELETE RESTRICT,
    CONSTRAINT fk_sale_items_product FOREIGN KEY (product_id)
        REFERENCES products (id) ON DELETE RESTRICT,
    CONSTRAINT chk_sale_items_values CHECK (
        quantity > 0 AND unit_price >= 0 AND unit_cost >= 0
        AND line_discount >= 0 AND line_total >= 0
    )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS purchases (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    purchase_number VARCHAR(48) NOT NULL,
    supplier_id BIGINT UNSIGNED NOT NULL,
    created_by_user_id BIGINT UNSIGNED NOT NULL,
    subtotal DECIMAL(13, 2) NOT NULL,
    total DECIMAL(13, 2) NOT NULL,
    receiving_status ENUM('ordered', 'partially_received', 'received', 'cancelled') NOT NULL DEFAULT 'ordered',
    payment_status ENUM('unpaid', 'partially_paid', 'paid', 'refunded') NOT NULL DEFAULT 'unpaid',
    notes TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_purchases_number (purchase_number),
    KEY idx_purchases_supplier (supplier_id),
    KEY idx_purchases_created_status (created_at, receiving_status, payment_status),
    CONSTRAINT fk_purchases_supplier FOREIGN KEY (supplier_id)
        REFERENCES suppliers (id) ON DELETE RESTRICT,
    CONSTRAINT fk_purchases_user FOREIGN KEY (created_by_user_id)
        REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT chk_purchases_amounts CHECK (subtotal >= 0 AND total >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS purchase_items (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    purchase_id BIGINT UNSIGNED NOT NULL,
    product_id BIGINT UNSIGNED NOT NULL,
    quantity_ordered DECIMAL(13, 3) NOT NULL,
    quantity_received DECIMAL(13, 3) NOT NULL DEFAULT 0.000,
    unit_cost DECIMAL(13, 2) NOT NULL,
    line_total DECIMAL(13, 2) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_purchase_items_purchase_product (purchase_id, product_id),
    KEY idx_purchase_items_product (product_id),
    CONSTRAINT fk_purchase_items_purchase FOREIGN KEY (purchase_id)
        REFERENCES purchases (id) ON DELETE RESTRICT,
    CONSTRAINT fk_purchase_items_product FOREIGN KEY (product_id)
        REFERENCES products (id) ON DELETE RESTRICT,
    CONSTRAINT chk_purchase_items_values CHECK (
        quantity_ordered > 0 AND quantity_received >= 0
        AND quantity_received <= quantity_ordered AND unit_cost >= 0 AND line_total >= 0
    )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS payments (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    sale_id BIGINT UNSIGNED NULL,
    purchase_id BIGINT UNSIGNED NULL,
    recorded_by_user_id BIGINT UNSIGNED NOT NULL,
    amount DECIMAL(13, 2) NOT NULL,
    payment_method ENUM('cash', 'card', 'bank_transfer', 'mobile_money', 'other') NOT NULL,
    payment_reference VARCHAR(120) NULL,
    payment_status ENUM('completed', 'pending', 'failed', 'refunded') NOT NULL DEFAULT 'completed',
    paid_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_payments_sale (sale_id, payment_status),
    KEY idx_payments_purchase (purchase_id, payment_status),
    KEY idx_payments_paid_at (paid_at),
    CONSTRAINT fk_payments_sale FOREIGN KEY (sale_id)
        REFERENCES sales (id) ON DELETE RESTRICT,
    CONSTRAINT fk_payments_purchase FOREIGN KEY (purchase_id)
        REFERENCES purchases (id) ON DELETE RESTRICT,
    CONSTRAINT fk_payments_user FOREIGN KEY (recorded_by_user_id)
        REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT chk_payments_one_parent CHECK (
        (sale_id IS NOT NULL AND purchase_id IS NULL)
        OR (sale_id IS NULL AND purchase_id IS NOT NULL)
    ),
    CONSTRAINT chk_payments_amount CHECK (amount > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS inventory_transactions (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    product_id BIGINT UNSIGNED NOT NULL,
    performed_by_user_id BIGINT UNSIGNED NULL,
    transaction_type ENUM(
        'opening_stock', 'purchase_received', 'sale', 'sale_return',
        'purchase_return', 'adjustment_in', 'adjustment_out'
    ) NOT NULL,
    quantity_change DECIMAL(13, 3) NOT NULL,
    stock_after DECIMAL(13, 3) NOT NULL,
    reference_type ENUM('sale', 'purchase', 'adjustment', 'opening_stock') NOT NULL,
    reference_id BIGINT UNSIGNED NULL,
    notes VARCHAR(500) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_inventory_product_time (product_id, created_at),
    KEY idx_inventory_reference (reference_type, reference_id),
    KEY idx_inventory_user_time (performed_by_user_id, created_at),
    CONSTRAINT fk_inventory_product FOREIGN KEY (product_id)
        REFERENCES products (id) ON DELETE RESTRICT,
    CONSTRAINT fk_inventory_user FOREIGN KEY (performed_by_user_id)
        REFERENCES users (id) ON DELETE SET NULL,
    CONSTRAINT chk_inventory_quantity CHECK (quantity_change <> 0),
    CONSTRAINT chk_inventory_stock CHECK (stock_after >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
