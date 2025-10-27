"""
Saree CRM - Single-file Flask + SQLite app (Improved)
Features added in this version:
- Full CRUD: Add / Edit / Delete for Customers, Orders, Follow-ups via the web UI
- Dashboard improvements: Pending follow-ups KPI, better charts with percentages on pie
- Export endpoints: download CSV for Customers, Orders, Follow-ups
- Shows where data is saved (SQLite file path) in the Dashboard
- Business name set to: Mana Saree Collection (shown in navbar & dashboard)

Run locally:
- pip install flask flask_sqlalchemy
- python3 saree_crm_flask_app.py
- Open http://127.0.0.1:5000

Notes: This is still a lightweight local app intended for small-business use. For multi-user production use, migrate DB to PostgreSQL and add authentication.
"""
from flask import Flask, request, redirect, url_for, jsonify, render_template_string, send_file
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
import os
import datetime
import csv

# ---- Config ----------------------------------------------------------------
BUSINESS_NAME = "Mana Saree Collection"
DB_FILENAME = 'saree_crm.db'
DB_PATH = os.path.join(os.path.dirname(__file__), DB_FILENAME)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Models -----------------------------------------------------------------
class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    insta = db.Column(db.String(80))
    phone = db.Column(db.String(30))
    city = db.Column(db.String(80))
    ctype = db.Column(db.String(20))
    notes = db.Column(db.Text)

    def to_dict(self):
        return {k: getattr(self, k) for k in ['customer_id','name','insta','phone','city','ctype','notes']}

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(20), unique=True, nullable=False)
    date = db.Column(db.Date, default=func.current_date())
    customer_id = db.Column(db.String(20), nullable=False)
    saree_type = db.Column(db.String(120))
    amount = db.Column(db.Integer)
    payment_status = db.Column(db.String(20))
    delivery_status = db.Column(db.String(30))
    remarks = db.Column(db.Text)

    def to_dict(self):
        return {k: getattr(self, k) for k in ['order_id','date','customer_id','saree_type','amount','payment_status','delivery_status','remarks']}

class FollowUp(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fu_id = db.Column(db.String(20), unique=True, nullable=False)
    date = db.Column(db.Date, default=func.current_date())
    customer_name = db.Column(db.String(120))
    insta = db.Column(db.String(80))
    topic = db.Column(db.String(200))
    next_date = db.Column(db.Date)
    status = db.Column(db.String(20))
    remarks = db.Column(db.Text)

    def to_dict(self):
        return {k: getattr(self, k) for k in ['fu_id','date','customer_name','insta','topic','next_date','status','remarks']}

# --- DB seed (if empty) ----------------------------------------------------
def seed_data():
    if Customer.query.first():
        return
    today = datetime.date.today()
    customers = [
        Customer(customer_id='C001', name='Priya Reddy', insta='@priyareddy', phone='9876543210', city='Hyderabad', ctype='Regular', notes='Loves soft silk sarees'),
        Customer(customer_id='C002', name='Kavya Sharma', insta='@kavya.s', phone='9988776655', city='Bengaluru', ctype='New', notes='Asked about Banarasi'),
        Customer(customer_id='C003', name='Meena Patel', insta='@meenap', phone='9123456780', city='Mumbai', ctype='VIP', notes='Prefers pastel colors'),
    ]
    db.session.bulk_save_objects(customers)

    orders = [
        Order(order_id='O001', date=today - datetime.timedelta(days=60), customer_id='C001', saree_type='Soft Silk', amount=2500, payment_status='Paid', delivery_status='Delivered'),
        Order(order_id='O002', date=today - datetime.timedelta(days=45), customer_id='C003', saree_type='Chiffon Floral', amount=1800, payment_status='Paid', delivery_status='Delivered'),
        Order(order_id='O003', date=today - datetime.timedelta(days=30), customer_id='C002', saree_type='Banarasi', amount=3200, payment_status='Paid', delivery_status='Delivered'),
    ]
    db.session.bulk_save_objects(orders)

    fus = [
        FollowUp(fu_id='F001', date=today - datetime.timedelta(days=10), customer_name='Kavya Sharma', insta='@kavya.s', topic='Interested in Banarasi saree', next_date=today + datetime.timedelta(days=2), status='Pending', remarks='Send new arrivals images'),
    ]
    db.session.bulk_save_objects(fus)
    db.session.commit()

# --- Templates --------------------------------------------------------------
BASE_TEMPLATE = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ business }} - Saree CRM</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  </head>
  <body class="bg-light">
  <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
    <div class="container-fluid">
      <a class="navbar-brand" href="/">{{ business }}</a>
      <div class="collapse navbar-collapse">
        <ul class="navbar-nav me-auto mb-2 mb-lg-0">
          <li class="nav-item"><a class="nav-link" href="/customers">Customers</a></li>
          <li class="nav-item"><a class="nav-link" href="/orders">Orders</a></li>
          <li class="nav-item"><a class="nav-link" href="/followups">Follow-ups</a></li>
          <li class="nav-item"><a class="nav-link" href="/dashboard">Dashboard</a></li>
        </ul>
        <div class="d-flex">
          <a class="btn btn-outline-light btn-sm me-2" href="/export/all">Export CSVs</a>
          <span class="navbar-text text-light">DB: {{ dbfile }}</span>
        </div>
      </div>
    </div>
  </nav>
  <div class="container my-4">
    {{ body|safe }}
  </div>
  </body>
</html>
"""

# -- Helpers -----------------------------------------------------------------
def next_customer_id():
    # generate Cxxx
    c = Customer.query.order_by(Customer.id.desc()).first()
    if not c:
        return 'C001'
    n = int(c.customer_id.lstrip('C')) + 1
    return f'C{n:03d}'

def next_order_id():
    o = Order.query.order_by(Order.id.desc()).first()
    if not o:
        return 'O001'
    n = int(o.order_id.lstrip('O')) + 1
    return f'O{n:03d}'

def next_fu_id():
    f = FollowUp.query.order_by(FollowUp.id.desc()).first()
    if not f:
        return 'F001'
    n = int(f.fu_id.lstrip('F')) + 1
    return f'F{n:03d}'

# -- Routes: UI and API ----------------------------------------------------
@app.route('/')
def home():
    return redirect(url_for('dashboard'))

# Customers CRUD
@app.route('/customers', methods=['GET','POST'])
def customers():
    if request.method == 'POST':
        cid = request.form.get('customer_id') or next_customer_id()
        # if editing existing
        existing = Customer.query.filter_by(customer_id=cid).first()
        if existing and request.form.get('_method') == 'PUT':
            existing.name = request.form['name']
            existing.insta = request.form.get('insta')
            existing.phone = request.form.get('phone')
            existing.city = request.form.get('city')
            existing.ctype = request.form.get('ctype')
            existing.notes = request.form.get('notes')
            db.session.commit()
            return redirect(url_for('customers'))
        if existing and request.form.get('_method') == 'DELETE':
            db.session.delete(existing)
            db.session.commit()
            return redirect(url_for('customers'))
        if not existing:
            c = Customer(customer_id=cid, name=request.form['name'], insta=request.form.get('insta'), phone=request.form.get('phone'), city=request.form.get('city'), ctype=request.form.get('ctype'), notes=request.form.get('notes'))
            db.session.add(c)
            db.session.commit()
            return redirect(url_for('customers'))
    rows = Customer.query.order_by(Customer.id.desc()).all()
    body = render_template_string('''
      <div class="d-flex justify-content-between align-items-center mb-3">
        <h3>Customers</h3>
        <div>
          <a class="btn btn-sm btn-secondary" href="/export/customers">Export CSV</a>
        </div>
      </div>
      <div class="card p-3 mb-3" id="add-form">
        <form method="post">
          <div class="row g-2">
            <div class="col-md-2"><input class="form-control" name="customer_id" placeholder="Customer ID (optional)"/></div>
            <div class="col-md-3"><input required class="form-control" name="name" placeholder="Name"/></div>
            <div class="col-md-2"><input class="form-control" name="insta" placeholder="Instagram"/></div>
            <div class="col-md-2"><input class="form-control" name="phone" placeholder="Phone"/></div>
            <div class="col-md-2"><input class="form-control" name="city" placeholder="City"/></div>
            <div class="col-md-1"><select name="ctype" class="form-select"><option>New</option><option>Regular</option><option>VIP</option></select></div>
          </div>
          <div class="row g-2 mt-2">
            <div class="col-md-10"><input class="form-control" name="notes" placeholder="Notes"/></div>
            <div class="col-md-2"><button class="btn btn-primary w-100">Save Customer</button></div>
          </div>
        </form>
      </div>
      <table class="table table-striped">
        <thead><tr><th>ID</th><th>Name</th><th>Insta</th><th>Phone</th><th>City</th><th>Type</th><th>Actions</th></tr></thead>
        <tbody>
          {% for r in rows %}
            <tr>
              <td>{{ r.customer_id }}</td>
              <td>{{ r.name }}</td>
              <td>{{ r.insta }}</td>
              <td>{{ r.phone }}</td>
              <td>{{ r.city }}</td>
              <td>{{ r.ctype }}</td>
              <td>
                <a class="btn btn-sm btn-outline-primary" href="/customers/edit/{{ r.customer_id }}">Edit</a>
                <form method="post" action="/customers" style="display:inline-block; margin-left:6px;">
                  <input type="hidden" name="customer_id" value="{{ r.customer_id }}" />
                  <input type="hidden" name="_method" value="DELETE" />
                  <button class="btn btn-sm btn-outline-danger" onclick="return confirm('Delete customer?')">Delete</button>
                </form>
              </td>
            </tr>
          {% endfor %}
        </tbody>
      </table>
    ''', rows=rows)
    return render_template_string(BASE_TEMPLATE, body=body, business=BUSINESS_NAME, dbfile=DB_PATH)

@app.route('/customers/edit/<cid>', methods=['GET'])
def edit_customer(cid):
    c = Customer.query.filter_by(customer_id=cid).first_or_404()
    body = render_template_string('''
      <h3>Edit Customer {{ c.customer_id }}</h3>
      <form method="post" action="/customers">
        <input type="hidden" name="customer_id" value="{{ c.customer_id }}" />
        <input type="hidden" name="_method" value="PUT" />
        <div class="row g-2">
          <div class="col-md-3"><input class="form-control" name="name" value="{{ c.name }}" required/></div>
          <div class="col-md-2"><input class="form-control" name="insta" value="{{ c.insta }}"/></div>
          <div class="col-md-2"><input class="form-control" name="phone" value="{{ c.phone }}"/></div>
          <div class="col-md-2"><input class="form-control" name="city" value="{{ c.city }}"/></div>
          <div class="col-md-1"><select name="ctype" class="form-select"><option {% if c.ctype=='New' %}selected{% endif %}>New</option><option {% if c.ctype=='Regular' %}selected{% endif %}>Regular</option><option {% if c.ctype=='VIP' %}selected{% endif %}>VIP</option></select></div>
        </div>
        <div class="row g-2 mt-2">
          <div class="col-md-9"><input class="form-control" name="notes" value="{{ c.notes }}"/></div>
          <div class="col-md-3"><button class="btn btn-primary">Save</button> <a class="btn btn-secondary" href="/customers">Cancel</a></div>
        </div>
      </form>
    ''', c=c)
    return render_template_string(BASE_TEMPLATE, body=body, business=BUSINESS_NAME, dbfile=DB_PATH)

# Orders CRUD
@app.route('/orders', methods=['GET','POST'])
def orders():
    if request.method == 'POST':
        oid = request.form.get('order_id') or next_order_id()
        existing = Order.query.filter_by(order_id=oid).first()
        date = request.form.get('date') or datetime.date.today().isoformat()
        date_obj = datetime.datetime.fromisoformat(date).date()
        if existing and request.form.get('_method') == 'PUT':
            existing.date = date_obj
            existing.customer_id = request.form.get('customer_id')
            existing.saree_type = request.form.get('saree_type')
            existing.amount = int(request.form.get('amount') or 0)
            existing.payment_status = request.form.get('payment_status')
            existing.delivery_status = request.form.get('delivery_status')
            existing.remarks = request.form.get('remarks')
            db.session.commit()
            return redirect(url_for('orders'))
        if existing and request.form.get('_method') == 'DELETE':
            db.session.delete(existing)
            db.session.commit()
            return redirect(url_for('orders'))
        if not existing:
            o = Order(order_id=oid, date=date_obj, customer_id=request.form.get('customer_id'), saree_type=request.form.get('saree_type'), amount=int(request.form.get('amount') or 0), payment_status=request.form.get('payment_status'), delivery_status=request.form.get('delivery_status'), remarks=request.form.get('remarks'))
            db.session.add(o)
            db.session.commit()
            return redirect(url_for('orders'))
    rows = Order.query.order_by(Order.date.desc()).all()
    customers = Customer.query.all()
    body = render_template_string('''
      <div class="d-flex justify-content-between align-items-center mb-3"><h3>Orders</h3>
        <div><a class="btn btn-sm btn-secondary" href="/export/orders">Export CSV</a></div></div>
      <div class="card p-3 mb-3">
        <form method="post">
          <div class="row g-2">
            <div class="col-md-2"><input class="form-control" name="order_id" placeholder="Order ID (optional)"/></div>
            <div class="col-md-2"><input class="form-control" type="date" name="date"/></div>
            <div class="col-md-3">
              <select name="customer_id" class="form-select" required>
                <option value="">-- Select Customer --</option>
                {% for c in customers %}
                  <option value="{{ c.customer_id }}">{{ c.customer_id }} - {{ c.name }}</option>
                {% endfor %}
              </select>
            </div>
            <div class="col-md-3"><input class="form-control" name="saree_type" placeholder="Saree Type"/></div>
            <div class="col-md-2"><input class="form-control" name="amount" placeholder="Amount"/></div>
          </div>
          <div class="row g-2 mt-2">
            <div class="col-md-3">
              <select name="payment_status" class="form-select"><option>Paid</option><option>Pending</option></select>
            </div>
            <div class="col-md-3">
              <select name="delivery_status" class="form-select"><option>Pending</option><option>Shipped</option><option>Delivered</option></select>
            </div>
            <div class="col-md-4"><input class="form-control" name="remarks" placeholder="Remarks"/></div>
            <div class="col-md-2"><button class="btn btn-primary w-100">Add Order</button></div>
          </div>
        </form>
      </div>
      <table class="table table-hover">
        <thead><tr><th>Order ID</th><th>Date</th><th>Customer</th><th>Saree</th><th>Amt</th><th>Payment</th><th>Delivery</th><th>Actions</th></tr></thead>
        <tbody>
          {% for r in rows %}
            <tr>
              <td>{{ r.order_id }}</td><td>{{ r.date }}</td><td>{{ r.customer_id }}</td><td>{{ r.saree_type }}</td><td>{{ r.amount }}</td><td>{{ r.payment_status }}</td><td>{{ r.delivery_status }}</td>
              <td>
                <a class="btn btn-sm btn-outline-primary" href="/orders/edit/{{ r.order_id }}">Edit</a>
                <form method="post" action="/orders" style="display:inline-block; margin-left:6px;">
                  <input type="hidden" name="order_id" value="{{ r.order_id }}" />
                  <input type="hidden" name="_method" value="DELETE" />
                  <button class="btn btn-sm btn-outline-danger" onclick="return confirm('Delete order?')">Delete</button>
                </form>
              </td>
            </tr>
          {% endfor %}
        </tbody>
      </table>
    ''', rows=rows, customers=customers)
    return render_template_string(BASE_TEMPLATE, body=body, business=BUSINESS_NAME, dbfile=DB_PATH)

@app.route('/orders/edit/<oid>', methods=['GET'])
def edit_order(oid):
    o = Order.query.filter_by(order_id=oid).first_or_404()
    customers = Customer.query.all()
    body = render_template_string('''
      <h3>Edit Order {{ o.order_id }}</h3>
      <form method="post" action="/orders">
        <input type="hidden" name="order_id" value="{{ o.order_id }}" />
        <input type="hidden" name="_method" value="PUT" />
        <div class="row g-2">
          <div class="col-md-2"><input class="form-control" type="date" name="date" value="{{ o.date }}"/></div>
          <div class="col-md-3">
            <select name="customer_id" class="form-select" required>
              {% for c in customers %}
                <option value="{{ c.customer_id }}" {% if c.customer_id==o.customer_id %}selected{% endif %}>{{ c.customer_id }} - {{ c.name }}</option>
              {% endfor %}
            </select>
          </div>
          <div class="col-md-3"><input class="form-control" name="saree_type" value="{{ o.saree_type }}"/></div>
          <div class="col-md-2"><input class="form-control" name="amount" value="{{ o.amount }}"/></div>
          <div class="col-md-2"><select name="payment_status" class="form-select"><option {% if o.payment_status=='Paid' %}selected{% endif %}>Paid</option><option {% if o.payment_status=='Pending' %}selected{% endif %}>Pending</option></select></div>
        </div>
        <div class="row g-2 mt-2">
          <div class="col-md-3"><select name="delivery_status" class="form-select"><option {% if o.delivery_status=='Pending' %}selected{% endif %}>Pending</option><option {% if o.delivery_status=='Shipped' %}selected{% endif %}>Shipped</option><option {% if o.delivery_status=='Delivered' %}selected{% endif %}>Delivered</option></select></div>
          <div class="col-md-6"><input class="form-control" name="remarks" value="{{ o.remarks }}"/></div>
          <div class="col-md-3"><button class="btn btn-primary">Save</button> <a class="btn btn-secondary" href="/orders">Cancel</a></div>
        </div>
      </form>
    ''', o=o, customers=customers)
    return render_template_string(BASE_TEMPLATE, body=body, business=BUSINESS_NAME, dbfile=DB_PATH)

# Follow-ups CRUD
@app.route('/followups', methods=['GET','POST'])
def followups():
    if request.method == 'POST':
        fid = request.form.get('fu_id') or next_fu_id()
        existing = FollowUp.query.filter_by(fu_id=fid).first()
        date = request.form.get('date') or datetime.date.today().isoformat()
        next_date = request.form.get('next_date') or None
        nd = datetime.datetime.fromisoformat(next_date).date() if next_date else None
        if existing and request.form.get('_method') == 'PUT':
            existing.date = datetime.datetime.fromisoformat(date).date()
            existing.customer_name = request.form.get('customer_name')
            existing.insta = request.form.get('insta')
            existing.topic = request.form.get('topic')
            existing.next_date = nd
            existing.status = request.form.get('status')
            existing.remarks = request.form.get('remarks')
            db.session.commit()
            return redirect(url_for('followups'))
        if existing and request.form.get('_method') == 'DELETE':
            db.session.delete(existing)
            db.session.commit()
            return redirect(url_for('followups'))
        if not existing:
            f = FollowUp(fu_id=fid, date=datetime.datetime.fromisoformat(date).date(), customer_name=request.form.get('customer_name'), insta=request.form.get('insta'), topic=request.form.get('topic'), next_date=nd, status=request.form.get('status'), remarks=request.form.get('remarks'))
            db.session.add(f)
            db.session.commit()
            return redirect(url_for('followups'))
    rows = FollowUp.query.order_by(FollowUp.next_date.asc().nulls_last()).all()
    body = render_template_string('''
      <div class="d-flex justify-content-between align-items-center mb-3"><h3>Follow-ups</h3>
        <div><a class="btn btn-sm btn-secondary" href="/export/followups">Export CSV</a></div></div>
      <div class="card p-3 mb-3">
        <form method="post">
          <div class="row g-2">
            <div class="col-md-2"><input class="form-control" name="fu_id" placeholder="FU ID (opt)"/></div>
            <div class="col-md-2"><input class="form-control" type="date" name="date"/></div>
            <div class="col-md-3"><input class="form-control" name="customer_name" placeholder="Customer name"/></div>
            <div class="col-md-2"><input class="form-control" name="insta" placeholder="Instagram"/></div>
            <div class="col-md-3"><input class="form-control" name="topic" placeholder="Topic"/></div>
          </div>
          <div class="row g-2 mt-2">
            <div class="col-md-2"><input class="form-control" type="date" name="next_date"/></div>
            <div class="col-md-2"><select name="status" class="form-select"><option>Pending</option><option>Done</option></select></div>
            <div class="col-md-6"><input class="form-control" name="remarks" placeholder="Remarks"/></div>
            <div class="col-md-2"><button class="btn btn-primary w-100">Add Follow-up</button></div>
          </div>
        </form>
      </div>
      <table class="table table-sm">
        <thead><tr><th>FU ID</th><th>Next Date</th><th>Customer</th><th>Topic</th><th>Status</th><th>Actions</th></tr></thead>
        <tbody>
          {% for r in rows %}
            <tr>
              <td>{{ r.fu_id }}</td><td>{{ r.next_date }}</td><td>{{ r.customer_name }}</td><td>{{ r.topic }}</td><td>{{ r.status }}</td>
              <td>
                <a class="btn btn-sm btn-outline-primary" href="/followups/edit/{{ r.fu_id }}">Edit</a>
                <form method="post" action="/followups" style="display:inline-block; margin-left:6px;">
                  <input type="hidden" name="fu_id" value="{{ r.fu_id }}" />
                  <input type="hidden" name="_method" value="DELETE" />
                  <button class="btn btn-sm btn-outline-danger" onclick="return confirm('Delete follow-up?')">Delete</button>
                </form>
              </td>
            </tr>
          {% endfor %}
        </tbody>
      </table>
    ''', rows=rows)
    return render_template_string(BASE_TEMPLATE, body=body, business=BUSINESS_NAME, dbfile=DB_PATH)

@app.route('/followups/edit/<fid>', methods=['GET'])
def edit_followup(fid):
    f = FollowUp.query.filter_by(fu_id=fid).first_or_404()
    body = render_template_string('''
      <h3>Edit Follow-up {{ f.fu_id }}</h3>
      <form method="post" action="/followups">
        <input type="hidden" name="fu_id" value="{{ f.fu_id }}" />
        <input type="hidden" name="_method" value="PUT" />
        <div class="row g-2">
          <div class="col-md-2"><input class="form-control" type="date" name="date" value="{{ f.date }}"/></div>
          <div class="col-md-3"><input class="form-control" name="customer_name" value="{{ f.customer_name }}"/></div>
          <div class="col-md-2"><input class="form-control" name="insta" value="{{ f.insta }}"/></div>
          <div class="col-md-3"><input class="form-control" name="topic" value="{{ f.topic }}"/></div>
          <div class="col-md-2"><input class="form-control" type="date" name="next_date" value="{{ f.next_date }}"/></div>
        </div>
        <div class="row g-2 mt-2">
          <div class="col-md-2"><select name="status" class="form-select"><option {% if f.status=='Pending' %}selected{% endif %}>Pending</option><option {% if f.status=='Done' %}selected{% endif %}>Done</option></select></div>
          <div class="col-md-8"><input class="form-control" name="remarks" value="{{ f.remarks }}"/></div>
          <div class="col-md-2"><button class="btn btn-primary">Save</button> <a class="btn btn-secondary" href="/followups">Cancel</a></div>
        </div>
      </form>
    ''', f=f)
    return render_template_string(BASE_TEMPLATE, body=body, business=BUSINESS_NAME, dbfile=DB_PATH)

# Dashboard
@app.route('/dashboard')
def dashboard():
    total_customers = Customer.query.count()
    total_orders = Order.query.count()
    total_sales = db.session.query(func.coalesce(func.sum(Order.amount),0)).scalar() or 0
    avg_order = int(total_sales/total_orders) if total_orders else 0
    pending_payments = Order.query.filter_by(payment_status='Pending').count()
    pending_delivery = Order.query.filter_by(delivery_status='Pending').count()
    pending_followups = FollowUp.query.filter_by(status='Pending').count()

    # Monthly sales
    q = db.session.query(func.strftime('%Y-%m', Order.date).label('m'), func.sum(Order.amount).label('sum')).group_by('m').order_by('m')
    monthly = [{'month': r.m, 'amount': r.sum} for r in q]
    # Saree type distribution
    q2 = db.session.query(Order.saree_type, func.count(Order.id)).group_by(Order.saree_type).all()
    saree_dist = [{'type': r[0] or 'Unknown', 'count': r[1]} for r in q2]
    # Top customers
    q3 = db.session.query(Order.customer_id, func.sum(Order.amount).label('sum')).group_by(Order.customer_id).order_by(func.sum(Order.amount).desc()).limit(5).all()
    topc = []
    for r in q3:
        cust = Customer.query.filter_by(customer_id=r[0]).first()
        topc.append({'name': cust.name if cust else r[0], 'amount': r.sum})

    body = render_template_string('''
      <h3>Dashboard</h3>
      <div class="row g-3">
        <div class="col-md-2"><div class="card p-2"><small>Total Customers</small><h4>{{ total_customers }}</h4></div></div>
        <div class="col-md-2"><div class="card p-2"><small>Total Orders</small><h4>{{ total_orders }}</h4></div></div>
        <div class="col-md-2"><div class="card p-2"><small>Total Sales (₹)</small><h4>{{ total_sales }}</h4></div></div>
        <div class="col-md-2"><div class="card p-2"><small>Avg Order (₹)</small><h4>{{ avg_order }}</h4></div></div>
        <div class="col-md-2"><div class="card p-2"><small>Pending Payments</small><h4>{{ pending_payments }}</h4></div></div>
        <div class="col-md-2"><div class="card p-2"><small>Pending Delivery</small><h4>{{ pending_delivery }}</h4></div></div>
      </div>
      <div class="row mt-3">
        <div class="col-md-3"><div class="card p-2"><small>Pending Follow-ups</small><h4>{{ pending_followups }}</h4></div></div>
      </div>
      <hr/>
      <div class="row mt-3">
        <div class="col-md-6"><canvas id="monthlyChart"></canvas></div>
        <div class="col-md-6"><canvas id="sareeChart"></canvas></div>
      </div>
      <div class="row mt-3">
        <div class="col-md-6"><canvas id="topCust"></canvas></div>
      </div>

      <script>
        const monthly = {{ monthly | tojson }};
        const saree = {{ saree_dist | tojson }};
        const topc = {{ topc | tojson }};

        // Monthly chart
        new Chart(document.getElementById('monthlyChart'), {
          type: 'bar',
          data: {
            labels: monthly.map(x => x.month),
            datasets: [{ label: 'Monthly Sales (₹)', data: monthly.map(x=>x.amount) }]
          },
          options: { responsive:true }
        });

        // Saree pie with percent labels (compute percentages in JS)
        const sareeLabels = saree.map(x=>x.type);
        const sareeData = saree.map(x=>x.count);
        const total = sareeData.reduce((a,b)=>a+b,0);
        const sareePercentLabels = sareeData.map((v,i)=> `${sareeLabels[i]} - ${total?((v/total)*100).toFixed(1):0}%`);

        new Chart(document.getElementById('sareeChart'), {
          type: 'pie',
          data: { labels: sareePercentLabels, datasets: [{ data: sareeData }] },
          options: { responsive:true }
        });

        // Top customers
        new Chart(document.getElementById('topCust'), {
          type: 'bar',
          data: { labels: topc.map(x=>x.name), datasets: [{ label:'Amount (₹)', data: topc.map(x=>x.amount) }] },
          options: { responsive:true }
        });
      </script>
    ''', total_customers=total_customers, total_orders=total_orders, total_sales=total_sales, avg_order=avg_order, pending_payments=pending_payments, pending_delivery=pending_delivery, pending_followups=pending_followups, monthly=monthly, saree_dist=saree_dist, topc=topc)

    return render_template_string(BASE_TEMPLATE, body=body, business=BUSINESS_NAME, dbfile=DB_PATH)

# Export CSV endpoints
def rows_to_csv(rows, cols, filename):
    # write to temp file and return path
    tmp = f"/tmp/{filename}"
    with open(tmp, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(cols)
        for r in rows:
            writer.writerow([getattr(r, c) if hasattr(r, c) else '' for c in cols])
    return tmp

@app.route('/export/customers')
def export_customers():
    rows = Customer.query.all()
    cols = ['customer_id','name','insta','phone','city','ctype','notes']
    path = rows_to_csv(rows, cols, 'customers.csv')
    return send_file(path, as_attachment=True, download_name='customers.csv')

@app.route('/export/orders')
def export_orders():
    rows = Order.query.all()
    cols = ['order_id','date','customer_id','saree_type','amount','payment_status','delivery_status','remarks']
    path = rows_to_csv(rows, cols, 'orders.csv')
    return send_file(path, as_attachment=True, download_name='orders.csv')

@app.route('/export/followups')
def export_followups():
    rows = FollowUp.query.all()
    cols = ['fu_id','date','customer_name','insta','topic','next_date','status','remarks']
    path = rows_to_csv(rows, cols, 'followups.csv')
    return send_file(path, as_attachment=True, download_name='followups.csv')

@app.route('/export/all')
def export_all():
    # returns a small HTML page linking to the three CSV exports
    return redirect(url_for('export_customers'))

# API endpoints (JSON)
@app.route('/api/customers')
def api_customers():
    return jsonify([c.to_dict() for c in Customer.query.all()])

@app.route('/api/orders')
def api_orders():
    return jsonify([o.to_dict() for o in Order.query.order_by(Order.date.desc()).all()])

@app.route('/api/followups')
def api_followups():
    return jsonify([f.to_dict() for f in FollowUp.query.all()])

# --- Init & run -------------------------------------------------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_data()
    print(f'Starting {BUSINESS_NAME} Saree CRM app... DB file: {DB_PATH}')
    app.run(host='0.0.0.0', port=5000, debug=False)
