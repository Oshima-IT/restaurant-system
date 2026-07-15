from flask import Flask, render_template, request, redirect, session, jsonify, make_response
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import inspect, text

import os
import base64
import csv
import io
import re
from paddleocr import PaddleOCR

from config import Config
from models.database import db
from models.user import User
from models.product import Product
from models.purchase import Purchase
from models.sale import Sale
from datetime import datetime, date ,timedelta
from models.attendance import Attendance

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)


def ensure_purchase_columns():
    inspector = inspect(db.engine)
    existing_columns = {col["name"] for col in inspector.get_columns("purchases")}

    if "supplier_name" not in existing_columns:
        db.session.execute(text("ALTER TABLE purchases ADD COLUMN supplier_name VARCHAR(100) NOT NULL DEFAULT ''"))

    if "unit_price" not in existing_columns:
        db.session.execute(text("ALTER TABLE purchases ADD COLUMN unit_price FLOAT NOT NULL DEFAULT 0"))

    if "total_amount" not in existing_columns:
        db.session.execute(text("ALTER TABLE purchases ADD COLUMN total_amount FLOAT NOT NULL DEFAULT 0"))

    db.session.commit()


def ensure_user_columns():
    inspector = inspect(db.engine)
    existing_columns = {col["name"] for col in inspector.get_columns("users")}

    if "hourly_wage" not in existing_columns:
        db.session.execute(text("ALTER TABLE users ADD COLUMN hourly_wage INT NOT NULL DEFAULT 1500"))

    db.session.commit()


with app.app_context():
    ensure_purchase_columns()
    ensure_user_columns()


def get_user_context():
    return {
        "user_name": session.get("user_name", ""),
        "user_role": session.get("user_role", "staff")
    }


def is_privileged_user():
    return session.get("user_role") in {"admin", "manager"}


def can_access_route(route_name, role):
    role = role or "staff"
    admin_routes = {"dashboard", "pos", "attendance", "sales", "purchase", "products", "employees"}
    manager_routes = {"dashboard", "pos", "attendance", "sales", "purchase", "products"}
    staff_routes = {"dashboard", "pos", "attendance", "sales", "purchase"}

    if role == "admin":
        return route_name in admin_routes
    if role == "manager":
        return route_name in manager_routes
    return route_name in staff_routes


def require_role(route_name):
    if not can_access_route(route_name, session.get("user_role")):
        return redirect("/dashboard")
    return None


def format_work_duration(clock_in, clock_out):
    if not clock_in or not clock_out:
        return "-"

    seconds = int((clock_out - clock_in).total_seconds())

    if seconds < 0:
        return "-"

    hours, remainder = divmod(seconds, 3600)
    minutes = remainder // 60

    return f"{hours}時間{minutes:02d}分"


def calculate_financial_summary(total_sales=0, sale_count=0):
    labor_rate_per_hour = 1500
    estimated_hours_per_sale = 2.5
    labor_cost = int(sale_count * estimated_hours_per_sale * labor_rate_per_hour)

    cogs_rate = 0.35
    cogs = int(total_sales * cogs_rate)

    gross_profit = total_sales - labor_cost - cogs
    gross_margin_rate = round((gross_profit / total_sales) * 100, 1) if total_sales else 0.0

    return {
        "total_sales": total_sales,
        "sale_count": sale_count,
        "labor_cost": labor_cost,
        "cogs": cogs,
        "gross_profit": gross_profit,
        "gross_margin_rate": gross_margin_rate,
    }


def parse_pos_ocr_result(text):
    # OCR誤読補正マップ
    char_map = {
        '呂': '8', 'B': '8', '口': '0', 'ロ': '0', 'O': '0', 'D': '0',
        'I': '1', 'l': '1', '|': '1', 'S': '5', 's': '5', 'g': '9',
        '#': '', 'Y': '', 'V': '', 'f': '', 'そ': '', '知': '', ' ': ''
    }
    
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    
    total_amount = None
    clock_in = None
    clock_out = None

    # 合計金額キーワード
    priority_keywords = ["合計", "合言", "合+", "小計", "計", "言", "Total", "TOTAL", "11計"]
    ignore_keywords = ["電話", "tel", "番号", "店No", "再発行", "預", "釣", "客"]

    potential_totals = []
    for i, line in enumerate(lines):
        norm_line = line
        for k, v in char_map.items():
            norm_line = norm_line.replace(k, v)
        
        is_total_line = any(k in line for k in priority_keywords)
        is_ignore_line = any(k in line for k in ignore_keywords) or "-" in line or "/" in line

        if is_total_line and not is_ignore_line:
            nums = re.findall(r"\d+", norm_line)
            if nums:
                vals = [int(n) for n in nums if 10 <= int(n) <= 200000]
                if vals: potential_totals.append(max(vals))
            elif i + 1 < len(lines):
                next_line_norm = lines[i+1]
                for k, v in char_map.items(): next_line_norm = next_line_norm.replace(k, v)
                next_nums = re.findall(r"\d+", next_line_norm)
                if next_nums: potential_totals.append(int(next_nums[0]))

    if potential_totals:
        total_amount = potential_totals[-1]
    elif not any(ik in text for ik in ignore_keywords):
        # フォールバック
        all_nums = []
        for line in lines:
            if any(c in line for c in ["-", "/", ":"]): continue
            ln = line
            for k,v in char_map.items(): ln = ln.replace(k,v)
            fn = re.findall(r"\d+", ln)
            for n in fn:
                if 100 <= int(n) <= 100000: all_nums.append(int(n))
        if all_nums: total_amount = all_nums[-1]

    # 勤怠時間の抽出 (時刻は置換しすぎると壊れるので慎重に)
    time_pattern = re.compile(r"(\d{1,2}[:時]\d{2})")
    for line in lines:
        if any(k in line for k in ["出勤", "入店", "開始", "clockin"]):
            m = time_pattern.search(line)
            if m: clock_in = m.group(1).replace("時", ":")
        if any(k in line for k in ["退勤", "退店", "終了", "clockout"]):
            m = time_pattern.search(line)
            if m: clock_out = m.group(1).replace("時", ":")

    return {
        "total_amount": total_amount or 0,
        "clock_in": clock_in,
        "clock_out": clock_out,
    }


# OCRリーダー
reader = PaddleOCR(
    lang="japan",
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False
)

# ------------------------------
# ログイン
# ------------------------------
@app.route("/", methods=["GET", "POST"])
def login():

    if "user_id" in session:
        return redirect("/dashboard")

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):

            session["user_id"] = user.id
            session["user_name"] = user.name
            session["user_role"] = user.role

            return redirect("/dashboard")

        return render_template(
            "login.html",
            error="ユーザー名またはパスワードが違います。"
        )

    return render_template("login.html")


# ------------------------------
# ダッシュボード
# ------------------------------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/")

    today = date.today()
    # 今月
    first_day_this_month = today.replace(day=1)
    
    # 統計計算
    start_today = datetime.combine(today, datetime.min.time())
    today_sales_q = Sale.query.filter(Sale.created_at >= start_today).all()
    today_sales = sum(s.total_price for s in today_sales_q)

    month_sales_q = Sale.query.filter(Sale.created_at >= datetime.combine(first_day_this_month, datetime.min.time())).all()
    month_sales = sum(s.total_price for s in month_sales_q)

    # グラフ用データ（直近14日間）
    graph_labels = []
    graph_values = []
    for i in range(13, -1, -1):
        target_date = today - timedelta(days=i)
        graph_labels.append(target_date.strftime("%m/%d"))
        s_dt = datetime.combine(target_date, datetime.min.time())
        e_dt = datetime.combine(target_date, datetime.max.time())
        day_total = db.session.query(db.func.sum(Sale.total_price)).filter(Sale.created_at >= s_dt, Sale.created_at <= e_dt).scalar() or 0
        graph_values.append(int(day_total))

    product_count = Product.query.count()

    return render_template(
        "dashboard.html",
        user_name=session["user_name"],
        today_sales=today_sales,
        month_sales=month_sales,
        product_count=product_count,
        graph_labels=graph_labels,
        graph_values=graph_values
    )



# ------------------------------
# 商品一覧
# ------------------------------
@app.route("/products")
def products():

    if "user_id" not in session:
        return redirect("/")

    if not can_access_route("products", session.get("user_role")):
        return redirect("/dashboard")

    products = Product.query.all()

    return render_template(
        "products.html",
        products=products,
        user_name=session["user_name"]
    )
# ------------------------------
# 商品追加
# ------------------------------
@app.route("/products/add", methods=["GET", "POST"])
def product_add():

    if "user_id" not in session:
        return redirect("/")

    if not can_access_route("products", session.get("user_role")):
        return redirect("/dashboard")

    if request.method == "POST":

        product = Product(
            name=request.form["name"],
            category=request.form["category"],
            price=int(request.form["price"]),
            stock=int(request.form["stock"])
        )

        db.session.add(product)
        db.session.commit()

        return redirect("/products")

    return render_template(
        "product_add.html",
        user_name=session["user_name"]
    )


# ------------------------------
# 商品編集
# ------------------------------
@app.route("/products/edit/<int:id>", methods=["GET", "POST"])
def product_edit(id):

    if "user_id" not in session:
        return redirect("/")

    if not can_access_route("products", session.get("user_role")):
        return redirect("/dashboard")

    product = Product.query.get_or_404(id)

    if request.method == "POST":

        product.name = request.form["name"]
        product.category = request.form["category"]
        product.price = int(request.form["price"])
        product.stock = int(request.form["stock"])

        db.session.commit()

        return redirect("/products")

    return render_template(
        "product_edit.html",
        product=product,
        user_name=session["user_name"]
    )


# ------------------------------
# 商品削除
# ------------------------------
@app.route("/products/delete/<int:id>")
def product_delete(id):

    if "user_id" not in session:
        return redirect("/")

    if not can_access_route("products", session.get("user_role")):
        return redirect("/dashboard")

    product = Product.query.get_or_404(id)

    db.session.delete(product)
    db.session.commit()

    return redirect("/products")
# ------------------------------
# POS
# ------------------------------
@app.route("/pos")
def pos():

    if "user_id" not in session:
        return redirect("/")

    if not can_access_route("pos", session.get("user_role")):
        return redirect("/dashboard")

    return render_template(
        "pos.html",
        user_name=session["user_name"],
        user_role=session.get("user_role")
    )


# ------------------------------
# 勤怠
# ------------------------------
@app.route("/attendance", methods=["GET", "POST"])
def attendance():

    if "user_id" not in session:
        return redirect("/")

    if request.method == "POST" and request.files.get("attendance_csv"):
        file_storage = request.files["attendance_csv"]
        stream = io.StringIO(file_storage.stream.read().decode("utf-8-sig"))
        reader = csv.DictReader(stream)

        for row in reader:
            username = (row.get("username") or "").strip()
            work_date = (row.get("work_date") or "").strip()
            clock_in = (row.get("clock_in") or "").strip()
            clock_out = (row.get("clock_out") or "").strip()

            if not username or not work_date:
                continue

            user = User.query.filter_by(username=username).first()
            if not user:
                continue

            try:
                work_date_dt = datetime.strptime(work_date, "%Y-%m-%d").date()
            except Exception:
                continue

            attendance_record = Attendance.query.filter_by(user_id=user.id, work_date=work_date_dt).first()
            if attendance_record is None:
                attendance_record = Attendance(user_id=user.id, work_date=work_date_dt)
                db.session.add(attendance_record)

            if clock_in:
                try:
                    attendance_record.clock_in = datetime.strptime(f"{work_date} {clock_in}", "%Y-%m-%d %H:%M")
                except Exception:
                    attendance_record.clock_in = None

            if clock_out:
                try:
                    attendance_record.clock_out = datetime.strptime(f"{work_date} {clock_out}", "%Y-%m-%d %H:%M")
                except Exception:
                    attendance_record.clock_out = None

        db.session.commit()
        return redirect("/attendance")

    today = date.today()
    today_str = today.strftime("%Y-%m-%d")

    attendance = Attendance.query.filter_by(
        user_id=session["user_id"],
        work_date=today
    ).first()

    filter_type = request.args.get("filter_type", "all")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    if filter_type == "today":
        start_date = today_str
        end_date = today_str
    elif filter_type == "month":
        first_day = today.replace(day=1)
        start_date = first_day.strftime("%Y-%m-%d")
        end_date = today_str
    elif filter_type == "all":
        start_date = None
        end_date = None

    attendance_query = db.session.query(
        Attendance,
        User
    ).join(
        User,
        Attendance.user_id == User.id
    )

    # user filter
    selected_user = request.args.get("user_id")

    if selected_user:
        try:
            uid = int(selected_user)
            attendance_query = attendance_query.filter(Attendance.user_id == uid)
        except ValueError:
            pass

    if start_date:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        attendance_query = attendance_query.filter(Attendance.work_date >= start_dt)

    if end_date:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
        attendance_query = attendance_query.filter(Attendance.work_date <= end_dt)

    attendance_list = attendance_query.order_by(
        Attendance.work_date.desc(),
        Attendance.clock_in.desc()
    ).all()

    # load users for filter dropdown and edit pages
    users = User.query.order_by(User.name).all()
    selected_user = selected_user or ""

    if request.method == "POST":

        action = request.form["action"]

        if action == "in":
            if attendance is None:
                attendance = Attendance(
                    user_id=session["user_id"],
                    work_date=today,
                    clock_in=datetime.now()
                )
                db.session.add(attendance)
            elif attendance.clock_in is None:
                attendance.clock_in = datetime.now()

        elif action == "out":
            if attendance and attendance.clock_out is None:
                attendance.clock_out = datetime.now()

        db.session.commit()

        return redirect("/attendance")

    user_context = get_user_context()

    return render_template(
        "attendance.html",
        attendance=attendance,
        attendance_list=attendance_list,
        users=users,
        selected_user=selected_user,
        user_name=user_context["user_name"],
        user_role=user_context["user_role"],
        is_privileged=is_privileged_user(),
        filter_type=filter_type,
        start_date=start_date,
        end_date=end_date,
        format_work_duration=format_work_duration
    )


@app.route("/attendance/export_csv")
def attendance_export_csv():
    if "user_id" not in session:
        return redirect("/")

    records = Attendance.query.order_by(Attendance.work_date.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["username", "work_date", "clock_in", "clock_out"])

    for record in records:
        user = User.query.get(record.user_id)
        username = user.username if user else ""
        writer.writerow([
            username,
            record.work_date.strftime("%Y-%m-%d") if record.work_date else "",
            record.clock_in.strftime("%H:%M") if record.clock_in else "",
            record.clock_out.strftime("%H:%M") if record.clock_out else "",
        ])

    response = make_response(output.getvalue(), 200)
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=attendance.csv"
    return response


@app.route("/sales/export_csv")
def sales_export_csv():
    if "user_id" not in session:
        return redirect("/")

    upload_folder = os.path.join("static", "uploads")
    csv_path = os.path.join(upload_folder, "pos_records.csv")

    if os.path.exists(csv_path):
        # 既存のサーバー保存CSVを返す
        with open(csv_path, "r", encoding="utf-8") as f:
            data = f.read()
        response = make_response(data, 200)
        response.headers["Content-Type"] = "text/csv; charset=utf-8"
        response.headers["Content-Disposition"] = "attachment; filename=pos_records.csv"
        return response

    # ファイルがなければDBから生成して返す（最低限の情報）
    sales = Sale.query.order_by(Sale.created_at.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "created_at", "total_price"])
    for s in sales:
        writer.writerow([s.id, s.created_at.strftime("%Y-%m-%d %H:%M:%S"), s.total_price])

    response = make_response(output.getvalue(), 200)
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=sales.csv"
    return response
# ------------------------------
# 勤怠修正
# ------------------------------
@app.route("/attendance/edit/<int:id>", methods=["GET", "POST"])
def attendance_edit(id):

    if not is_privileged_user():
        return redirect("/attendance")

    attendance_record = Attendance.query.get_or_404(id)

    if request.method == "POST":
        clock_in_value = request.form.get("clock_in", "")
        clock_out_value = request.form.get("clock_out", "")

        if clock_in_value:
            attendance_record.clock_in = datetime.strptime(clock_in_value, "%Y-%m-%dT%H:%M")
        else:
            attendance_record.clock_in = None

        if clock_out_value:
            attendance_record.clock_out = datetime.strptime(clock_out_value, "%Y-%m-%dT%H:%M")
        else:
            attendance_record.clock_out = None

        db.session.commit()
        return redirect("/attendance")

    # pass users map for display
    users_by_id = {u.id: u for u in User.query.all()}

    return render_template(
        "attendance_edit.html",
        attendance_record=attendance_record,
        users_by_id=users_by_id,
        user_name=session.get("user_name"),
        user_role=session.get("user_role")
    )


# ------------------------------
# 社員管理
# ------------------------------
@app.route("/employees")
def employees():

    if not is_privileged_user():
        return redirect("/dashboard")

    users = User.query.order_by(User.created_at.desc()).all()

    return render_template(
        "employees.html",
        users=users,
        user_name=session["user_name"],
        user_role=session["user_role"]
    )


@app.route("/employees/add", methods=["GET", "POST"])
def employee_add():

    if not is_privileged_user():
        return redirect("/dashboard")

    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        if User.query.filter_by(username=username).first():
            return redirect("/employees")

        try:
            hourly_wage = int(request.form.get("hourly_wage", 1500) or 1500)
        except ValueError:
            hourly_wage = 1500

        user = User(
            username=username,
            password=generate_password_hash(password),
            name=request.form["name"].strip(),
            role=request.form["role"],
            hourly_wage=hourly_wage
        )

        db.session.add(user)
        db.session.commit()

        return redirect("/employees")

    return render_template(
        "employee_form.html",
        user=None,
        user_name=session["user_name"],
        user_role=session["user_role"]
    )


@app.route("/employees/edit/<int:id>", methods=["GET", "POST"])
def employee_edit(id):

    if not is_privileged_user():
        return redirect("/dashboard")

    user = User.query.get_or_404(id)

    if request.method == "POST":
        user.name = request.form["name"].strip()
        user.role = request.form["role"]

        try:
            user.hourly_wage = int(request.form.get("hourly_wage", user.hourly_wage) or user.hourly_wage)
        except ValueError:
            user.hourly_wage = user.hourly_wage

        if request.form.get("password"):
            user.password = generate_password_hash(request.form["password"])

        db.session.commit()
        return redirect("/employees")

    return render_template(
        "employee_form.html",
        user=user,
        user_name=session["user_name"],
        user_role=session["user_role"]
    )


@app.route("/employees/delete/<int:id>")
def employee_delete(id):

    if not is_privileged_user():
        return redirect("/dashboard")

    user = User.query.get_or_404(id)

    if user.id != session["user_id"]:
        db.session.delete(user)
        db.session.commit()

    return redirect("/employees")

# ------------------------------
# 売上
# ------------------------------
@app.route("/sales")
def sales():
    if "user_id" not in session: return redirect("/")
    
    today = date.today()
    first_day_this_month = today.replace(day=1)
    
    # 前月
    last_month_end = first_day_this_month - timedelta(days=1)
    first_day_last_month = last_month_end.replace(day=1)

    # 今月の売上
    this_month_sales_q = Sale.query.filter(Sale.created_at >= datetime.combine(first_day_this_month, datetime.min.time())).all()
    this_month_total = sum(s.total_price for s in this_month_sales_q)
    
    # 前月の売上
    last_month_sales_q = Sale.query.filter(
        Sale.created_at >= datetime.combine(first_day_last_month, datetime.min.time()),
        Sale.created_at <= datetime.combine(last_month_end, datetime.max.time())
    ).all()
    last_month_total = sum(s.total_price for s in last_month_sales_q)

    # 比較計算
    diff = this_month_total - last_month_total
    growth_rate = round((diff / last_month_total * 100), 1) if last_month_total > 0 else 0

    # フィルタ処理（既存）
    filter_type = request.args.get("filter_type", "month")
    # ... (既存のフィルタロジックを維持しつつ、分析データを追加)
    query = Sale.query
    if filter_type == "today":
        query = query.filter(Sale.created_at >= datetime.combine(today, datetime.min.time()))
    elif filter_type == "month":
        query = query.filter(Sale.created_at >= datetime.combine(first_day_this_month, datetime.min.time()))
    
    sales_list = query.order_by(Sale.created_at.desc()).all()
    current_total = sum(s.total_price for s in sales_list)
    summary = calculate_financial_summary(total_sales=current_total, sale_count=len(sales_list))

    return render_template(
        "sales.html",
        sales=sales_list,
        total_sales=current_total,
        summary=summary,
        last_month_total=last_month_total,
        growth_rate=growth_rate,
        diff=diff,
        user_name=session["user_name"]
    )


# ------------------------------
# 受発注
# ------------------------------
@app.route("/purchase", methods=["GET", "POST"])
def purchase():

    if "user_id" not in session:
        return redirect("/")

    if not can_access_route("purchase", session.get("user_role")):
        return redirect("/dashboard")

    if request.method == "POST":

        product_name = request.form.get("product_name", "").strip()
        supplier_name = request.form.get("supplier_name", "").strip()

        try:
            quantity = int(request.form.get("quantity", 0) or 0)
        except ValueError:
            quantity = 0

        try:
            unit_price = float(request.form.get("unit_price", 0) or 0)
        except ValueError:
            unit_price = 0

        try:
            total_amount = float(request.form.get("total_amount", 0) or 0)
        except ValueError:
            total_amount = 0

        if total_amount <= 0:
            total_amount = unit_price * quantity

        purchase = Purchase(
            product_name=product_name,
            quantity=quantity,
            supplier_name=supplier_name,
            unit_price=unit_price,
            total_amount=total_amount,
            status="発注中"
        )

        db.session.add(purchase)
        db.session.commit()

        return redirect("/purchase")

    purchases = Purchase.query.order_by(
        Purchase.created_at.desc()
    ).all()

    return render_template(
        "purchase.html",
        purchases=purchases,
        user_name=session["user_name"]
    )


# ------------------------------
# 会計 (POS) 解析プレビュー
# ------------------------------
@app.route("/checkout_preview", methods=["POST"])
def checkout_preview():
    data = request.get_json() or {}
    text = data.get("text", "")
    parsed = parse_pos_ocr_result(text)
    return jsonify(parsed)
# ------------------------------
# 会計 (POS)
# ------------------------------
@app.route("/checkout", methods=["POST"])
def checkout():

    if "user_id" not in session:
        return jsonify({"success": False})

    data = request.get_json() or {}
    mode = data.get("mode", "both") # sale, attendance, both
    total = data.get("total")
    clock_in = data.get("clock_in")
    clock_out = data.get("clock_out")
    text = data.get("text", "")

    # 売上の登録
    if mode in ["sale", "both"]:
        try:
            total_amount = int(total)
            sale = Sale(total_price=total_amount)
            db.session.add(sale)
        except Exception:
            pass

    # 勤怠の登録
    if mode in ["attendance", "both"]:
        if clock_in or clock_out:
            today = date.today()
            attendance = Attendance.query.filter_by(user_id=session["user_id"], work_date=today).first()
            if attendance is None:
                attendance = Attendance(user_id=session["user_id"], work_date=today)
                db.session.add(attendance)

            if clock_in:
                try:
                    attendance.clock_in = datetime.strptime(f"{today.strftime('%Y-%m-%d')} {clock_in}", "%Y-%m-%d %H:%M")
                except Exception:
                    pass

            if clock_out:
                try:
                    attendance.clock_out = datetime.strptime(f"{today.strftime('%Y-%m-%d')} {clock_out}", "%Y-%m-%d %H:%M")
                except Exception:
                    pass

    db.session.commit()

    # サーバー側で POS レコードを CSV に保存（追記）
    try:
        upload_folder = os.path.join("static", "uploads")
        os.makedirs(upload_folder, exist_ok=True)
        csv_path = os.path.join(upload_folder, "pos_records.csv")
        write_header = not os.path.exists(csv_path)

        with open(csv_path, "a", encoding="utf-8", newline="") as csvfile:
            writer = csv.writer(csvfile)
            if write_header:
                writer.writerow(["timestamp", "user_id", "username", "total_price", "clock_in", "clock_out", "raw_text"])

            user = User.query.get(session.get("user_id"))
            username = user.username if user else ""
            timestamp = sale.created_at.strftime("%Y-%m-%d %H:%M:%S") if hasattr(sale, 'created_at') else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            writer.writerow([timestamp, session.get("user_id"), username, total_amount, clock_in or "", clock_out or "", text or ""])
    except Exception:
        pass

    return jsonify({
        "success": True,
        "total_amount": total_amount,
        "clock_in": clock_in,
        "clock_out": clock_out,
    })


# ------------------------------
# 納品書画像保存
# ------------------------------
@app.route("/upload_purchase_image", methods=["POST"])
def upload_purchase_image():

    if "user_id" not in session:
        return jsonify({"success": False})

    upload_folder = os.path.join(
        "static",
        "uploads"
    )

    os.makedirs(
        upload_folder,
        exist_ok=True
    )

    filename = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    ) + ".png"

    filepath = os.path.join(
        upload_folder,
        filename
    )

    # ファイルアップロードの場合
    if "file" in request.files:
        file = request.files["file"]
        if file.filename == "":
            return jsonify({"success": False})
        # ファイルを保存
        file.save(filepath)
    # JSON base64の場合
    elif request.json and "image" in request.json:
        data = request.json["image"]
        header, encoded = data.split(",", 1)
        image = base64.b64decode(encoded)
        with open(filepath, "wb") as f:
            f.write(image)
    else:
        return jsonify({"success": False})

    return jsonify({
        "success": True,
        "filename": filename
    })



# ------------------------------
# OCR実行
# ------------------------------
@app.route("/ocr_purchase", methods=["POST"])
def ocr_purchase():

    filename = request.json["filename"]

    filepath = os.path.join(
        "static",
        "uploads",
        filename
    )

    result = reader.ocr(filepath)

    lines = []
    text = ""

    # OCR結果をリスト化
    for page in result:
        if page is None:
            continue
        for item in page:
            line = item[1][0].strip()
            if line:
                lines.append(line)
                text += line + "\n"

    items = []

    i = 0

    while i < len(lines) - 1:

        current = lines[i]
        next_line = lines[i + 1]

        # 現在が文字列、次が数字なら商品名＋数量と判断
        if (not current.isdigit()) and next_line.isdigit():

            items.append({

                "name": current,

                "quantity": int(next_line)

            })

            i += 2

        else:

            i += 1

    return jsonify({

        "success": True,

        "text": text,

        "items": items

    })

# ------------------------------
# OCR一括登録
# ------------------------------
@app.route("/purchase/ocr_register", methods=["POST"])
def purchase_ocr_register():

    if "user_id" not in session:
        return jsonify({"success": False})

    items = request.json["items"]

    for item in items:

        purchase = Purchase(

            product_name=item["name"],

            quantity=item["quantity"],
            supplier_name="",
            unit_price=0,
            total_amount=0,
            status="発注中"

        )

        db.session.add(purchase)

    db.session.commit()

    return jsonify({

        "success": True

    })

# ------------------------------
# ログアウト
# ------------------------------
@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )