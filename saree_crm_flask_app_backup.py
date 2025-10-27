"""
Saree CRM - Single-file Flask + SQLite app
Run locally for a fast, offline-friendly CRM for an Instagram saree business.

Features implemented:
- Customers, Orders, Follow-ups CRUD (simple add/list/edit/delete)
- Dashboard with KPIs and charts (Monthly Sales, Saree Type distribution, Top Customers)
- SQLite DB (created automatically). Sample data seeded on first run.
- Single-file app (no separate templates) using render_template_string for easy local run.

Requirements:
- Python 3.8+
- pip install flask flask_sqlalchemy

Run:
$ pip install flask flask_sqlalchemy
$ python saree_crm_flask_app.py
Open http://127.0.0.1:5000 in your browser

Note: This is a minimal, production-**lite** app for local/desktop use. If you want an Electron or packaged desktop binary next, I can convert it.
"""
from flask import Flask, request, redirect, url_for, jsonify, render_template_string
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
import os
import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///saree_crm.db'
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
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'name': self.name,
            'insta': self.insta,
            'phone': self.phone,
            'city': self.city,
            'ctype': self.ctype,
            'notes': self.notes
        }

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
        return {
            'id': self.id,
            'order_id': self.order_id,
            'date': self.date.isoformat(),
            'customer_id': self.customer_id,
            'saree_type': self.saree_type,
            'amount': self.amount,
            'payment_status': self.payment_status,
            'delivery_status': self.delivery_status,
            'remarks': self.remarks
        }

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
        return {
            'id': self.id,
            'fu_id': self.fu_id,
            'date': self.date.isoformat() if self.date else None,
            'customer_name': self.customer_name,
            'insta': self.insta,
            'topic': self.topic,
            'next_date': self.next_date.isoformat() if self.next_date else None,
            'status': self.status,
            'remarks': self.remarks
        }

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
    for c in customers:
        db.session.add(c)

    orders = [
        Order(order_id='O001', date=today - datetime.timedelta(days=60), customer_id='C001', saree_type='Soft Silk', amount=2500, payment_status='Paid', delivery_status='Delivered'),
        Order(order_id='O002', date=today - datetime.timedelta(days=45), customer_id='C003', saree_type='Chiffon Floral', amount=1800, payment_status='Paid', delivery_status='Delivered'),
        Order(order_id='O003', date=today - datetime.timedelta(days=30), customer_id='C002', saree_type='Banarasi', amount=3200, payment_status='Paid', delivery_status='Delivered'),
    ]
    for o in orders:
        db.session.add(o)

    fus = [
        FollowUp(fu_id='F001', date=today - datetime.timedelta(days=10), customer_name='Kavya Sharma', insta='@kavya.s', topic='Interested in Banarasi saree', next_date=today + datetime.timedelta(days=2), status='Pending', remarks='Send new arrivals images'),
    ]
    for f in fus:
        db.session.add(f)

    db.session.commit()

# --- Routes: UI and API ----------------------------------------------------
BASE_TEMPLATE = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Saree CRM (Local)</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  </head>
  <body class="bg-light">
  <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
    <div class="container-fluid">
      <a class="navbar-brand" href="/">Saree CRM</a>
      <div class="collapse navbar-collapse">
        <ul class="navbar-nav me-auto mb-2 mb-lg-0">
          <li class="nav-item"><a class="nav-link" href="/customers">Customers</a></li>
          <li class="nav-item"><a class="nav-link" href="/orders">Orders</a></li>
          <li class="nav-item"><a class="nav-link" href="/followups">Follow-ups</a></li>
          <li class="nav-item"><a class="nav-link" href="/dashboard">Dashboard</a></li>
        </ul>
      </div>
    </div>
  </nav>
  <div class="container my-4">
    {% with messages = get_flashed_messages() %}
      {% if messages %}
        <div class="alert alert-info">{{ messages[0] }}</div>
      {% endif %}
    {% endwith %}
    {{ body|safe }}
  </div>
  </body>
</html>
"""

# -- Customers list & add
@app.route('/')
def home():
    return redirect(url_for('dashboard'))

@app.route('/customers', methods=['GET','POST'])
def customers():
    if request.method == 'POST':
        cid = request.form.get('customer_id') or f"C{1000 + (Customer.query.count()+1)}"
        c = Customer(customer_id=cid, name=request.form['name'], insta=request.form.get('insta'), phone=request.form.get('phone'), city=request.form.get('city'), ctype=request.form.get('ctype'), notes=request.form.get('notes'))
        db.session.add(c)
        db.session.commit()
        return redirect(url_for('customers'))
    rows = Customer.query.order_by(Customer.id.desc()).all()
    body = render_template_string('''
      <div class="d-flex justify-content-between align-items-center mb-3">
        <h3>Customers</h3>
        <a class="btn btn-sm btn-success" href="#add" onclick="document.getElementById('add-form').scrollIntoView();">+ Add Customer</a>
      </div>
      <div class="card p-3 mb-3" id="add-form">
        <form method="post">
          <div class="row g-2">
            <div class="col-md-3"><input class="form-control" name="customer_id" placeholder="Customer ID (optional)"/></div>
            <div class="col-md-3"><input required class="form-control" name="name" placeholder="Name"/></div>
            <div class="col-md-2"><input class="form-control" name="insta" placeholder="Instagram"/></div>
            <div class="col-md-2"><input class="form-control" name="phone" placeholder="Phone"/></div>
            <div class="col-md-2"><input class="form-control" name="city" placeholder="City"/></div>
          </div>
          <div class="row g-2 mt-2">
            <div class="col-md-3">
              <select name="ctype" class="form-select"><option>New</option><option>Regular</option><option>VIP</option></select>
            </div>
            <div class="col-md-7"><input class="form-control" name="notes" placeholder="Notes"/></div>
            <div class="col-md-2"><button class="btn btn-primary w-100">Save</button></div>
          </div>
        </form>
      </div>
      <table class="table table-striped">
        <thead><tr><th>ID</th><th>Name</th><th>Insta</th><th>Phone</th><th>City</th><th>Type</th></tr></thead>
        <tbody>
          {% for r in rows %}
            <tr><td>{{ r.customer_id }}</td><td>{{ r.name }}</td><td>{{ r.insta }}</td><td>{{ r.phone }}</td><td>{{ r.city }}</td><td>{{ r.ctype }}</td></tr>
          {% endfor %}
        </tbody>
      </table>
    ''', rows=rows)
    return render_template_string(BASE_TEMPLATE, body=body)

# -- Orders list & add
@app.route('/orders', methods=['GET','POST'])
def orders():
    if request.method == 'POST':
        oid = request.form.get('order_id') or f"O{1000 + (Order.query.count()+1)}"
        date = request.form.get('date') or datetime.date.today().isoformat()
        o = Order(order_id=oid, date=datetime.datetime.fromisoformat(date).date(), customer_id=request.form['customer_id'], saree_type=request.form.get('saree_type'), amount=int(request.form.get('amount') or 0), payment_status=request.form.get('payment_status'), delivery_status=request.form.get('delivery_status'), remarks=request.form.get('remarks'))
        db.session.add(o)
        db.session.commit()
        return redirect(url_for('orders'))
    rows = Order.query.order_by(Order.date.desc()).all()
    customers = Customer.query.all()
    body = render_template_string('''
      <div class="d-flex justify-content-between align-items-center mb-3"><h3>Orders</h3></div>
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
        <thead><tr><th>Order ID</th><th>Date</th><th>Customer</th><th>Saree</th><th>Amt</th><th>Payment</th><th>Delivery</th></tr></thead>
        <tbody>
          {% for r in rows %}
            <tr><td>{{ r.order_id }}</td><td>{{ r.date }}</td><td>{{ r.customer_id }}</td><td>{{ r.saree_type }}</td><td>{{ r.amount }}</td><td>{{ r.payment_status }}</td><td>{{ r.delivery_status }}</td></tr>
          {% endfor %}
        </tbody>
      </table>
    ''', rows=rows, customers=customers)
    return render_template_string(BASE_TEMPLATE, body=body)

# -- Follow-ups
@app.route('/followups', methods=['GET','POST'])
def followups():
    if request.method == 'POST':
        fid = request.form.get('fu_id') or f"F{1000 + (FollowUp.query.count()+1)}"
        next_date = request.form.get('next_date') or None
        nd = datetime.datetime.fromisoformat(next_date).date() if next_date else None
        f = FollowUp(fu_id=fid, date=datetime.datetime.fromisoformat(request.form.get('date')).date() if request.form.get('date') else datetime.date.today(), customer_name=request.form.get('customer_name'), insta=request.form.get('insta'), topic=request.form.get('topic'), next_date=nd, status=request.form.get('status'), remarks=request.form.get('remarks'))
        db.session.add(f)
        db.session.commit()
        return redirect(url_for('followups'))
    rows = FollowUp.query.order_by(FollowUp.next_date.asc().nulls_last()).all()
    body = render_template_string('''
      <div class="d-flex justify-content-between align-items-center mb-3"><h3>Follow-ups</h3></div>
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
            <div class="col-md-3"><input class="form-control" type="date" name="next_date"/></div>
            <div class="col-md-2"><select name="status" class="form-select"><option>Pending</option><option>Done</option></select></div>
            <div class="col-md-5"><input class="form-control" name="remarks" placeholder="Remarks"/></div>
            <div class="col-md-2"><button class="btn btn-primary w-100">Add Follow-up</button></div>
          </div>
        </form>
      </div>
      <table class="table table-sm">
        <thead><tr><th>FU ID</th><th>Next Date</th><th>Customer</th><th>Topic</th><th>Status</th></tr></thead>
        <tbody>
          {% for r in rows %}
            <tr><td>{{ r.fu_id }}</td><td>{{ r.next_date }}</td><td>{{ r.customer_name }}</td><td>{{ r.topic }}</td><td>{{ r.status }}</td></tr>
          {% endfor %}
        </tbody>
      </table>
    ''', rows=rows)
    return render_template_string(BASE_TEMPLATE, body=body)

# -- Dashboard
@app.route('/dashboard')
def dashboard():
    # KPI values via SQL queries
    total_customers = Customer.query.count()
    total_orders = Order.query.count()
    total_sales = db.session.query(func.coalesce(func.sum(Order.amount),0)).scalar() or 0
    avg_order = int(total_sales/total_orders) if total_orders else 0
    pending_payments = Order.query.filter_by(payment_status='Pending').count()
    pending_delivery = Order.query.filter_by(delivery_status='Pending').count()

    # Data for charts
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

        // Saree pie
        new Chart(document.getElementById('sareeChart'), {
          type: 'pie',
          data: { labels: saree.map(x=>x.type), datasets: [{ data: saree.map(x=>x.count) }] },
          options: { responsive:true }
        });

        // Top customers
        new Chart(document.getElementById('topCust'), {
          type: 'bar',
          data: { labels: topc.map(x=>x.name), datasets: [{ label:'Amount (₹)', data: topc.map(x=>x.amount) }] },
          options: { responsive:true }
        });
      </script>
    ''', total_customers=total_customers, total_orders=total_orders, total_sales=total_sales, avg_order=avg_order, pending_payments=pending_payments, pending_delivery=pending_delivery, monthly=monthly, saree_dist=saree_dist, topc=topc)

    return render_template_string(BASE_TEMPLATE, body=body)

# API endpoints (JSON) for integrations / export
@app.route('/api/customers')
def api_customers():
    return jsonify([c.to_dict() for c in Customer.query.all()])

@app.route('/api/orders')
def api_orders():
    return jsonify([o.to_dict() for o in Order.query.order_by(Order.date.desc()).all()])

@app.route('/api/followups')
def api_followups():
    return jsonify([f.to_dict() for f in FollowUp.query.all()])
if __name__ == '__main__':
    # Ensure DB is created and seed data runs inside app context
    with app.app_context():
        db.create_all()
        seed_data()
    print('Starting Saree CRM app... Visit http://0.0.0.0:5000')
    # bind to 0.0.0.0 so EC2 public IP can reach it
    app.run(host='0.0.0.0', port=5000, debug=False)
