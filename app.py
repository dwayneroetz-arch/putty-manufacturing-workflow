#!/usr/bin/env python3
"""
Adhesive Putty Manufacturing Workflow System
- Admin dashboard for stock, orders, recipes
- Packing hall view
- 3 Mixing station screens
"""

import sqlite3
import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify

app = Flask(__name__)
app.secret_key = "putty-workflow-secret-key-change-in-prod"

DATABASE = os.path.join(os.path.dirname(__file__), "putty.db")


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    # Raw materials
    c.execute("""
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            unit TEXT DEFAULT 'kg',
            stock REAL DEFAULT 0,
            min_stock REAL DEFAULT 50,
            cost_per_unit REAL DEFAULT 0
        )
    """)

    # Products / Recipes
    c.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            batch_size_kg REAL DEFAULT 100,
            unit_label TEXT DEFAULT 'kg'
        )
    """)

    # Recipe ingredients (percentage of batch)
    c.execute("""
        CREATE TABLE IF NOT EXISTS recipe_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            material_id INTEGER NOT NULL,
            percentage REAL NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products(id),
            FOREIGN KEY (material_id) REFERENCES materials(id),
            UNIQUE(product_id, material_id)
        )
    """)

    # Orders
    c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number TEXT UNIQUE NOT NULL,
            customer TEXT,
            product_id INTEGER NOT NULL,
            quantity_kg REAL NOT NULL,
            status TEXT DEFAULT 'queued',  -- queued, mixing, mixed, packing, packed, ready, shipped
            mixing_station INTEGER,       -- 1,2,3 or NULL
            created_at TEXT,
            mixed_at TEXT,
            packed_at TEXT,
            notes TEXT,
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)

    # Stock movements log
    c.execute("""
        CREATE TABLE IF NOT EXISTS stock_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_id INTEGER,
            change REAL,
            reason TEXT,
            order_id INTEGER,
            created_at TEXT,
            FOREIGN KEY (material_id) REFERENCES materials(id)
        )
    """)

    conn.commit()

    # Seed data if empty
    if c.execute("SELECT COUNT(*) FROM materials").fetchone()[0] == 0:
        materials = [
            ("White Cement (PO 42.5)", "kg", 2500, 200, 0.45),
            ("Heavy Calcium Carbonate", "kg", 4000, 300, 0.12),
            ("Quartz Powder (160-200 mesh)", "kg", 1800, 150, 0.18),
            ("Redispersible Polymer Powder", "kg", 180, 30, 4.50),
            ("HPMC Cellulose Ether", "kg", 90, 15, 8.20),
            ("Wood Fiber", "kg", 60, 10, 1.80),
            ("Polypropylene Fiber 3mm", "kg", 40, 8, 3.10),
            ("Talc Powder", "kg", 500, 50, 0.35),
            ("Acrylic Binder Emulsion", "kg", 300, 40, 2.80),
            ("Preservative", "kg", 25, 5, 12.00),
        ]
        c.executemany(
            "INSERT INTO materials (name, unit, stock, min_stock, cost_per_unit) VALUES (?,?,?,?,?)",
            materials
        )

        products = [
            ("Standard Interior Wall Putty", "General purpose cement-based putty", 100, "kg"),
            ("Premium Water-Resistant Putty", "Higher polymer content for wet areas", 100, "kg"),
            ("Acrylic Flexible Putty", "High flexibility acrylic system", 80, "kg"),
            ("Exterior Grade Putty", "Weather-resistant exterior formula", 100, "kg"),
        ]
        c.executemany(
            "INSERT INTO products (name, description, batch_size_kg, unit_label) VALUES (?,?,?,?)",
            products
        )

        # Recipes (percentages roughly based on industry examples)
        recipes = [
            # Standard Interior Wall Putty (product_id=1)
            (1, 1, 30.0),   # White Cement
            (1, 2, 45.0),   # Heavy Calcium
            (1, 3, 22.0),   # Quartz
            (1, 4, 1.2),    # Polymer
            (1, 5, 0.45),   # HPMC
            (1, 6, 0.2),    # Wood Fiber
            (1, 7, 0.1),    # PP Fiber
            (1, 10, 0.05),  # Preservative

            # Premium Water-Resistant (product_id=2)
            (2, 1, 28.0),
            (2, 2, 42.0),
            (2, 3, 20.0),
            (2, 4, 2.5),
            (2, 5, 0.5),
            (2, 6, 0.3),
            (2, 7, 0.15),
            (2, 10, 0.05),

            # Acrylic Flexible (product_id=3)
            (3, 9, 20.0),   # Acrylic Binder
            (3, 2, 55.0),   # Heavy Calcium
            (3, 8, 15.0),   # Talc
            (3, 5, 0.6),
            (3, 4, 1.5),
            (3, 10, 0.1),

            # Exterior Grade (product_id=4)
            (4, 1, 32.0),
            (4, 2, 38.0),
            (4, 3, 25.0),
            (4, 4, 2.0),
            (4, 5, 0.5),
            (4, 6, 0.25),
            (4, 7, 0.15),
            (4, 10, 0.1),
        ]
        c.executemany(
            "INSERT INTO recipe_items (product_id, material_id, percentage) VALUES (?,?,?)",
            recipes
        )

        # Sample orders
        now = datetime.now().isoformat(timespec="seconds")
        sample_orders = [
            ("ORD-2026-001", "BuildRight Contractors", 1, 500, "queued", None, now, None, None, ""),
            ("ORD-2026-002", "HomeFix Retail", 2, 300, "queued", None, now, None, None, "Urgent"),
            ("ORD-2026-003", "City Renovations", 1, 800, "mixing", 1, now, None, None, ""),
            ("ORD-2026-004", "ProPaint Supplies", 3, 200, "mixed", None, now, now, None, ""),
            ("ORD-2026-005", "Summit Developers", 4, 450, "packing", None, now, now, None, ""),
            ("ORD-2026-006", "Local Hardware Co", 2, 150, "ready", None, now, now, now, "Ready for collection"),
        ]
        c.executemany(
            """INSERT INTO orders 
               (order_number, customer, product_id, quantity_kg, status, mixing_station, created_at, mixed_at, packed_at, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            sample_orders
        )

        conn.commit()
    conn.close()


# ---------- Helpers ----------

def get_recipe_for_order(order_id):
    """Return list of materials needed for an order with calculated quantities."""
    conn = get_db()
    order = conn.execute(
        "SELECT o.*, p.name as product_name, p.batch_size_kg FROM orders o JOIN products p ON o.product_id = p.id WHERE o.id = ?",
        (order_id,)
    ).fetchone()
    if not order:
        conn.close()
        return None, []

    items = conn.execute("""
        SELECT m.id as material_id, m.name, m.unit, m.stock, ri.percentage,
               ROUND(o.quantity_kg * ri.percentage / 100.0, 2) as qty_needed
        FROM recipe_items ri
        JOIN materials m ON ri.material_id = m.id
        JOIN orders o ON o.id = ?
        WHERE ri.product_id = o.product_id
        ORDER BY ri.percentage DESC
    """, (order_id,)).fetchall()
    conn.close()
    return order, items


def deduct_stock_for_order(order_id):
    """Deduct raw materials when mixing is completed."""
    order, items = get_recipe_for_order(order_id)
    if not order:
        return False
    conn = get_db()
    now = datetime.now().isoformat(timespec="seconds")
    for item in items:
        conn.execute(
            "UPDATE materials SET stock = stock - ? WHERE id = ?",
            (item["qty_needed"], item["material_id"])
        )
        conn.execute(
            "INSERT INTO stock_log (material_id, change, reason, order_id, created_at) VALUES (?,?,?,?,?)",
            (item["material_id"], -item["qty_needed"], f"Mixed for {order['order_number']}", order_id, now)
        )
    conn.commit()
    conn.close()
    return True


# ---------- Routes ----------

@app.route("/")
def index():
    conn = get_db()
    materials = conn.execute("SELECT * FROM materials ORDER BY name").fetchall()
    products = conn.execute("SELECT * FROM products ORDER BY name").fetchall()
    orders = conn.execute("""
        SELECT o.*, p.name as product_name 
        FROM orders o 
        JOIN products p ON o.product_id = p.id 
        ORDER BY 
            CASE o.status 
                WHEN 'queued' THEN 1 
                WHEN 'mixing' THEN 2 
                WHEN 'mixed' THEN 3 
                WHEN 'packing' THEN 4 
                WHEN 'packed' THEN 5 
                WHEN 'ready' THEN 6 
                ELSE 7 
            END, o.created_at DESC
    """).fetchall()
    low_stock = [m for m in materials if m["stock"] < m["min_stock"]]
    conn.close()
    return render_template("admin.html", materials=materials, products=products,
                           orders=orders, low_stock=low_stock)


@app.route("/packing")
def packing_hall():
    conn = get_db()
    orders = conn.execute("""
        SELECT o.*, p.name as product_name 
        FROM orders o 
        JOIN products p ON o.product_id = p.id 
        WHERE o.status IN ('mixed', 'packing', 'packed', 'ready')
        ORDER BY 
            CASE o.status 
                WHEN 'mixed' THEN 1 
                WHEN 'packing' THEN 2 
                WHEN 'packed' THEN 3 
                WHEN 'ready' THEN 4 
            END, o.created_at
    """).fetchall()
    conn.close()
    return render_template("packing.html", orders=orders)


@app.route("/mixing/<int:station>")
def mixing_station(station):
    if station not in (1, 2, 3):
        return "Invalid station", 404
    conn = get_db()
    order = conn.execute("""
        SELECT o.*, p.name as product_name, p.description
        FROM orders o 
        JOIN products p ON o.product_id = p.id 
        WHERE o.mixing_station = ? AND o.status = 'mixing'
        ORDER BY o.created_at LIMIT 1
    """, (station,)).fetchone()
    conn.close()

    recipe_items = []
    if order:
        _, recipe_items = get_recipe_for_order(order["id"])
    return render_template("mixing.html", station=station, order=order, recipe_items=recipe_items)


@app.route("/order/new", methods=["POST"])
def new_order():
    order_number = request.form.get("order_number", "").strip()
    customer = request.form.get("customer", "").strip()
    product_id = request.form.get("product_id")
    quantity = float(request.form.get("quantity_kg", 0))
    notes = request.form.get("notes", "")

    if not order_number or not product_id or quantity <= 0:
        flash("Invalid order data", "error")
        return redirect(url_for("index"))

    conn = get_db()
    try:
        conn.execute(
            """INSERT INTO orders (order_number, customer, product_id, quantity_kg, status, created_at, notes)
               VALUES (?,?,?,?, 'queued', ?, ?)""",
            (order_number, customer, product_id, quantity,
             datetime.now().isoformat(timespec="seconds"), notes)
        )
        conn.commit()
        flash(f"Order {order_number} created", "success")
    except sqlite3.IntegrityError:
        flash("Order number already exists", "error")
    finally:
        conn.close()
    return redirect(url_for("index"))


@app.route("/order/<int:order_id>/assign", methods=["POST"])
def assign_mixing(order_id):
    station = int(request.form.get("station", 0))
    if station not in (1, 2, 3):
        flash("Invalid station", "error")
        return redirect(url_for("index"))

    conn = get_db()
    # Check station is free
    busy = conn.execute(
        "SELECT id FROM orders WHERE mixing_station = ? AND status = 'mixing'", (station,)
    ).fetchone()
    if busy:
        flash(f"Station {station} is already busy", "error")
        conn.close()
        return redirect(url_for("index"))

    conn.execute(
        "UPDATE orders SET status = 'mixing', mixing_station = ? WHERE id = ? AND status = 'queued'",
        (station, order_id)
    )
    conn.commit()
    conn.close()
    flash(f"Order assigned to Mixing Station {station}", "success")
    return redirect(url_for("index"))


@app.route("/order/<int:order_id>/status", methods=["POST"])
def update_status(order_id):
    new_status = request.form.get("status")
    valid = {"queued", "mixing", "mixed", "packing", "packed", "ready", "shipped"}
    if new_status not in valid:
        flash("Invalid status", "error")
        return redirect(request.referrer or url_for("index"))

    conn = get_db()
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if not order:
        conn.close()
        flash("Order not found", "error")
        return redirect(url_for("index"))

    now = datetime.now().isoformat(timespec="seconds")
    updates = {"status": new_status}

    if new_status == "mixed" and order["status"] == "mixing":
        # Deduct stock
        deduct_stock_for_order(order_id)
        updates["mixed_at"] = now
        updates["mixing_station"] = None
    elif new_status == "packed":
        updates["packed_at"] = now
    elif new_status == "queued":
        updates["mixing_station"] = None

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [order_id]
    conn.execute(f"UPDATE orders SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()
    flash(f"Order status updated to {new_status}", "success")
    return redirect(request.referrer or url_for("index"))


@app.route("/stock/adjust", methods=["POST"])
def adjust_stock():
    material_id = int(request.form.get("material_id"))
    change = float(request.form.get("change", 0))
    reason = request.form.get("reason", "Manual adjustment")

    conn = get_db()
    conn.execute("UPDATE materials SET stock = stock + ? WHERE id = ?", (change, material_id))
    conn.execute(
        "INSERT INTO stock_log (material_id, change, reason, created_at) VALUES (?,?,?,?)",
        (material_id, change, reason, datetime.now().isoformat(timespec="seconds"))
    )
    conn.commit()
    conn.close()
    flash("Stock updated", "success")
    return redirect(url_for("index"))


@app.route("/api/orders")
def api_orders():
    """Simple JSON API for potential live refresh."""
    conn = get_db()
    orders = conn.execute("""
        SELECT o.id, o.order_number, o.customer, o.quantity_kg, o.status, o.mixing_station,
               p.name as product_name
        FROM orders o JOIN products p ON o.product_id = p.id
        ORDER BY o.created_at DESC
    """).fetchall()
    conn.close()
    return jsonify([dict(o) for o in orders])


if __name__ == "__main__":
    init_db()
    print("Starting Putty Manufacturing Workflow System...")
    print("  Admin:     http://127.0.0.1:5000/")
    print("  Packing:   http://127.0.0.1:5000/packing")
    print("  Mixing 1:  http://127.0.0.1:5000/mixing/1")
    print("  Mixing 2:  http://127.0.0.1:5000/mixing/2")
    print("  Mixing 3:  http://127.0.0.1:5000/mixing/3")
    app.run(host="0.0.0.0", port=5000, debug=True)
