from functools import wraps
from pathlib import Path
from datetime import datetime, date
import json
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from sqlalchemy import or_, cast, String
from config import Config
from urllib.parse import quote
from models import db, Admin, User, Record, Notice, WalletTransaction, Market, GameRate,UserGameHistory,GameResult

app = Flask(__name__)
app.config.from_object(Config)
Path(app.instance_path).mkdir(parents=True, exist_ok=True)
db.init_app(app)

# Sidebar hierarchy follows the supplied reference screenshots.
MENU_GROUPS = [
    {"label": "Dashboard", "icon": "▰", "single": "dashboard"},
    {"label": "All Users", "icon": "👥", "single": "users"},
    {"label": "System Reports", "icon": "▤", "items": [
        ("Deposit Summary", "deposit-summary"),
        ("Withdraw Summary", "withdraw-summary"),
        ("Market Win/Bid", "market-win-bid"),
        ("Deposit Transactions", "deposit-transactions"),
        ("Withdraw Transactions", "withdraw-transactions"),
    ]},
    {"label": "Game Management", "icon": "🎮", "items": [
        ("Game Providers", "game-providers"),
        ("Game Rates", "game-rates"),
        ("Game Result", "game-result"),
        ("Generate Result", "/generate-result"),
        ("Bid Revert", "bid-revert"),
    ]},
    {"label": "Bookie Corner", "icon": "▣", "items": [
        ("Cutting List", "cutting-list"),
        ("OC Cutting Group", "oc-cutting-group"),
        ("Loss Cutting", "loss-cutting"),
    ]},
    {"label": "Report Management", "icon": "▤", "items": [
        ("Winner prediction", "winner-prediction"),
        ("Bid History", "bid-history"),
        ("Winning History", "winning-history"),
        ("Customer Sell Report", "customer-sell-report"),
    ]},
    {"label": "Wallet Management", "icon": "▣", "items": [
        ("Fund Report", "fund-report"),
        ("Deposit Requests", "deposit-requests"),
        ("Withdraw Points Request", "withdraw-points-request"),
    ]},
    {"label": "Settings", "icon": "⚙", "items": [
        ("General Settings", "settings"),
    ]},
    {"label": "Notice Management", "icon": "▤", "items": [
        ("Bell Notifications", "bell-notifications"),
        ("Send Notification", "send-notification"),
        ("Manage Contents", "manage-contents"),
    ]},
    {"label": "Personal Games", "icon": "●", "single": "personal-games"},
    {"label": "Main Starline", "icon": "⠿", "items": [
        ("Game Provider", "starline-game-provider"),
        ("Game Rates", "starline-game-rates"),
        ("Bid History", "starline-bid-history"),
        ("Game Result", "starline-game-result"),
        ("Result History", "starline-result-history"),
        ("Sell Report", "starline-sell-report"),
        ("Winning Report", "starline-winning-report"),
    ]},
    {"label": "Main Jackpot", "icon": "⠿", "items": [
        ("Game Provider", "jackpot-game-provider"),
        ("Game Rates", "jackpot-game-rates"),
        ("Bid History", "jackpot-bid-history"),
        ("Game Result", "jackpot-game-result"),
        ("Result History", "jackpot-result-history"),
        ("Sell Report", "jackpot-sell-report"),
        ("Winning Report", "jackpot-winning-report"),
    ]},
]

MODULE_TITLES = {}
for group in MENU_GROUPS:
    if group.get("single") and group["single"] not in ("dashboard", "users", "settings"):
        MODULE_TITLES[group["single"]] = group["label"]
    for label, slug in group.get("items", []):
        if slug != "settings":
            MODULE_TITLES[slug] = label

@app.context_processor
def inject_menu():
    return {"menu_groups": MENU_GROUPS, "current_admin": session.get("admin_username")}

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "admin_id" not in session:
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped

@app.route("/")
def index():
    return redirect(url_for("dashboard") if "admin_id" in session else url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        admin = Admin.query.filter_by(username=username).first()
        if admin and admin.check_password(password):
            session.clear()
            session["admin_id"] = admin.id
            session["admin_username"] = admin.username
            flash("Welcome back.", "success")
            return redirect(request.args.get("next") or url_for("dashboard"))
        flash("Invalid username or password.", "danger")
    return render_template("login.html")



@app.route("/user-logout")
def user_logout():
    session.pop("user_id", None)
    session.pop("user_username", None)
    flash("User logged out successfully.", "info")
    return redirect(url_for("user_login"))





@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        username = request.form.get("username", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not name or not username or not password:
            flash("Please fill all required fields.", "danger")

        elif len(password) < 8:
            flash("Password must contain at least 8 characters.", "danger")

        elif password != confirm_password:
            flash("Passwords do not match.", "danger")

        elif User.query.filter_by(username=username).first():
            flash("Username already exists.", "danger")

        else:
            user = User(
                name=name,
                username=username,
                phone=phone,
                email=email,
                status="Active",
                points=0
            )

            user.set_password(password)

            db.session.add(user)
            db.session.commit()

            flash("Registration successful!", "success")
            return redirect(url_for("user_login"))

    return render_template("registration.html")



@app.route("/user-login", methods=["GET", "POST"])
def user_login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()

        if not user or not user.check_password(password):
            flash("Invalid username or password.", "danger")
            return redirect(url_for("user_login"))

        if user.status != "Active":
            flash("Your account is inactive. Contact Admin.", "danger")
            return redirect(url_for("user_login"))

        session.clear()
        session["user_id"] = user.id
        session["user_username"] = user.username

        return redirect(url_for("user_dashboard"))

    return render_template("user_login.html")



@app.route("/user-dashboard")
def user_dashboard():
    if "user_id" not in session:
        return redirect(url_for("user_login"))

    user = User.query.get_or_404(session["user_id"])

    history = (
        UserGameHistory.query
        .filter_by(user_id=user.id)
        .order_by(UserGameHistory.created_at.desc())
        .limit(20)
        .all()
    )

    game_rates = GameRate.query.order_by(
        GameRate.id.asc()
    ).all()

    markets = Market.query.order_by(
        Market.name.asc()
    ).all()

    return render_template(
        "user_dashboard.html",
        user=user,
        history=history,
        game_rates=game_rates,
        markets=markets
    )


@app.route("/user-play", methods=["GET", "POST"])
def user_play():
    if "user_id" not in session:
        return redirect(url_for("user_login"))

    user = User.query.get_or_404(session["user_id"])

    markets = Market.query.order_by(Market.name.asc()).all()
    game_rates = GameRate.query.order_by(GameRate.id.asc()).all()

    if request.method == "POST":
        market_id = request.form.get("market_id", type=int)
        game_type = request.form.get("game_type", "").strip()
        session_type = request.form.get("session", "").strip()
        selection = request.form.get("selection", "").strip()
        points_used = request.form.get("points_used", type=float)

        market = db.session.get(Market, market_id)
        game = GameRate.query.filter_by(game_name=game_type).first()

        if not market or not game:
            flash("Please select a valid market and game.", "danger")


        elif session_type not in ["Open", "Close"] or not selection or points_used is None or points_used <= 0:
            flash("Enter valid game selection and demo points.", "danger")

        elif points_used > user.points:
            flash("Insufficient demo points.", "danger")

        else:
            user.points -= points_used

            history = UserGameHistory(
                user_id=user.id,
                game_name=market.name,
                game_type=game.game_name,
                session=session_type,
                selection=selection,
                points_used=points_used,
                result="Pending",
                status="Demo Submitted"
            )

            db.session.add(history)
            db.session.commit()

            flash("Demo game submitted successfully!", "success")
            return redirect(url_for("user_dashboard"))

    return render_template(
        "user_play.html",
        user=user,
        markets=markets,
        game_rates=game_rates
    )




@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    stats = {
        "users": User.query.count(),
        "active_users": User.query.filter_by(status="Active").count(),
        "records": Record.query.count(),
        "pending": WalletTransaction.query.filter_by(status="Pending").count(),
        "wallet": round(sum((u.points or 0) for u in User.query.all()), 2),
        "notices": Notice.query.count(),
    }
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    recent_tx = WalletTransaction.query.order_by(WalletTransaction.created_at.desc()).limit(5).all()
    return render_template("dashboard.html", stats=stats, recent_users=recent_users, recent_tx=recent_tx)

@app.route("/users")
@login_required
def users():
    q = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    query = User.query
    if q:
        query = query.filter(or_(User.name.ilike(f"%{q}%"), User.username.ilike(f"%{q}%"),
                                 User.phone.ilike(f"%{q}%"), User.email.ilike(f"%{q}%")))
    pagination = query.order_by(User.created_at.desc()).paginate(page=page, per_page=12, error_out=False)
    return render_template("users.html", pagination=pagination, q=q)

@app.route("/users/add", methods=["GET", "POST"])
@login_required
def user_add():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        username = request.form.get("username", "").strip()
        if not name or not username:
            flash("Name and username are required.", "danger")
        elif User.query.filter_by(username=username).first():
            flash("Username already exists.", "danger")
        else:
            user = User(name=name, username=username,
                        phone=request.form.get("phone", "").strip(),
                        email=request.form.get("email", "").strip(),
                        points=request.form.get("points", 0, type=float),
                        status=request.form.get("status", "Active"))
            db.session.add(user)
            db.session.commit()
            flash("User added successfully.", "success")
            return redirect(url_for("users"))
    return render_template("user_form.html", user=None)

@app.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
def user_edit(user_id):
    user = User.query.get_or_404(user_id)
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        duplicate = User.query.filter(User.username == username, User.id != user.id).first()
        if not request.form.get("name", "").strip() or not username:
            flash("Name and username are required.", "danger")
        elif duplicate:
            flash("Username already exists.", "danger")
        else:
            user.name = request.form["name"].strip()
            user.username = username
            user.phone = request.form.get("phone", "").strip()
            user.email = request.form.get("email", "").strip()
            user.points = request.form.get("points", 0, type=float)
            user.status = request.form.get("status", "Active")
            db.session.commit()
            flash("User updated.", "success")
            return redirect(url_for("users"))
    return render_template("user_form.html", user=user)

@app.post("/users/<int:user_id>/delete")
@login_required
def user_delete(user_id):
    user = User.query.get_or_404(user_id)
    WalletTransaction.query.filter_by(user_id=user.id).delete()
    db.session.delete(user)
    db.session.commit()
    flash("User deleted.", "success")
    return redirect(url_for("users"))

@app.route("/admin/deposit-summary")
@login_required
def deposit_summary():
    return wallet_summary("Deposit")

@app.route("/admin/withdraw-summary")
@login_required
def withdraw_summary():
    return wallet_summary("Withdraw")

@app.route("/admin/deposit-transactions")
@login_required
def deposit_transactions():
    return wallet_transactions("Deposit")

@app.route("/admin/withdraw-transactions")
@login_required
def withdraw_transactions():
    return wallet_transactions("Withdraw")

def wallet_transactions(kind):
    """Detailed transaction register for deposits or withdrawals."""
    today = date.today()
    start_text = request.args.get("start_date", "").strip()
    end_text = request.args.get("end_date", "").strip()
    query = WalletTransaction.query.filter(
        WalletTransaction.transaction_type.ilike(kind)
    )
    if start_text:
        try:
            start_date = datetime.strptime(start_text, "%Y-%m-%d").date()
            query = query.filter(WalletTransaction.created_at >= datetime.combine(start_date, datetime.min.time()))
        except ValueError:
            start_text = ""
    if end_text:
        try:
            end_date = datetime.strptime(end_text, "%Y-%m-%d").date()
            query = query.filter(WalletTransaction.created_at < datetime.combine(end_date, datetime.max.time()))
        except ValueError:
            end_text = ""

    search = request.args.get("q", "").strip()
    if search:
        query = query.join(User, WalletTransaction.user_id == User.id, isouter=True).filter(
            or_(User.name.ilike(f"%{search}%"), User.username.ilike(f"%{search}%"),
                User.phone.ilike(f"%{search}%"), WalletTransaction.status.ilike(f"%{search}%"),
                WalletTransaction.note.ilike(f"%{search}%"),
                cast(WalletTransaction.id, String).ilike(f"%{search}%"))
        )
    status = request.args.get("status", "").strip()
    if status:
        query = query.filter(WalletTransaction.status.ilike(status))

    all_rows = query.order_by(WalletTransaction.created_at.desc()).all()
    total_amount = sum(float(tx.amount or 0) for tx in all_rows)
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = request.args.get("show", 10, type=int)
    if per_page not in (10, 25, 50, 100):
        per_page = 10
    total_pages = max((len(all_rows) + per_page - 1) // per_page, 1)
    page = min(page, total_pages)
    rows = all_rows[(page - 1) * per_page:page * per_page]
    return render_template(
        "wallet_transactions.html", kind=kind, transactions=rows,
        total_amount=total_amount, total_count=len(all_rows),
        start_date=start_text, end_date=end_text, search=search, status=status,
        page=page, per_page=per_page, total_pages=total_pages
    )

def wallet_summary(kind):
    today = date.today()
    start_text = request.args.get("start_date", today.isoformat())
    end_text = request.args.get("end_date", today.isoformat())
    try:
        start_date = datetime.strptime(start_text, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_text, "%Y-%m-%d").date()
    except ValueError:
        start_date = end_date = today
        start_text = end_text = today.isoformat()
        flash("Invalid date range. Showing today's transactions.", "warning")
    if start_date > end_date:
        start_date, end_date = end_date, start_date
        start_text, end_text = start_date.isoformat(), end_date.isoformat()

    query = WalletTransaction.query.filter(
        WalletTransaction.transaction_type.ilike(kind),
        WalletTransaction.created_at >= datetime.combine(start_date, datetime.min.time()),
        WalletTransaction.created_at < datetime.combine(end_date, datetime.max.time())
    )
    search = request.args.get("q", "").strip()
    if search:
        query = query.join(User, WalletTransaction.user_id == User.id, isouter=True).filter(
            or_(User.name.ilike(f"%{search}%"), User.username.ilike(f"%{search}%"),
                User.phone.ilike(f"%{search}%"), WalletTransaction.status.ilike(f"%{search}%"),
                WalletTransaction.note.ilike(f"%{search}%"),
                cast(WalletTransaction.id, String).ilike(f"%{search}%"))
        )
    transactions = query.order_by(WalletTransaction.created_at.desc()).all()
    total_amount = sum(float(tx.amount or 0) for tx in transactions)
    status_totals = {}
    if kind == "Withdraw":
        status_aliases = {"Successful": {"successful", "success", "completed"},
                          "Pending": {"pending", "processing"},
                          "Cancelled": {"cancelled", "canceled", "rejected"}}
        for status, aliases in status_aliases.items():
            rows = [tx for tx in transactions if (tx.status or "").lower() in aliases]
            status_totals[status] = {"amount": sum(float(tx.amount or 0) for tx in rows), "count": len(rows)}
    else:
        status_totals["Admin"] = {"amount": total_amount, "count": len(transactions)}
    if kind == "Deposit":
        # Deposit summary's secondary card groups amounts by account owner.
        grouped = {}
        for tx in transactions:
            owner = tx.user.name if tx.user else "ADMIN"
            grouped.setdefault(owner, {"amount": 0.0, "count": 0})
            grouped[owner]["amount"] += float(tx.amount or 0)
            grouped[owner]["count"] += 1
        summary_groups = grouped
    else:
        summary_groups = status_totals
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = request.args.get("show", 10, type=int)
    if per_page not in (10, 25, 50, 100): per_page = 10
    total_pages = max((len(transactions) + per_page - 1) // per_page, 1)
    page = min(page, total_pages)
    page_rows = transactions[(page - 1) * per_page: page * per_page]
    return render_template(
        "wallet_summary.html", kind=kind, transactions=page_rows,
        total_amount=total_amount, total_count=len(transactions),
        status_totals=status_totals, summary_groups=summary_groups,
        start_date=start_text, end_date=end_text, search=search,
        page=page, per_page=per_page, total_pages=total_pages
    )

@app.route("/admin/<slug>")
@login_required
def module_page(slug):
    if slug not in MODULE_TITLES:
        abort(404)

    if slug == "game-result":
        return redirect(url_for("generate_result"))
    if slug == "game-providers":
        q = request.args.get("q", "").strip()
        per_page = request.args.get("show", 10, type=int)
        if per_page not in (10, 25, 50, 100):
            per_page = 10
        query = Market.query
        if q:
            query = query.filter(Market.name.ilike(f"%{q}%"))
        pagination = query.order_by(Market.name.asc()).paginate(
            page=request.args.get("page", 1, type=int), per_page=per_page, error_out=False)
        markets = []
        for market in pagination.items:
            try:
                schedule = json.loads(market.schedule_json or "{}")
            except (TypeError, ValueError):
                schedule = {}
            markets.append({"market": market, "schedule": schedule})
        return render_template("game_providers.html", title=MODULE_TITLES[slug],
                               markets=markets, pagination=pagination, q=q, show=per_page)
    if slug == "game-rates":
        rates = GameRate.query.order_by(GameRate.id.asc()).all()
        return render_template("game_rates.html", title=MODULE_TITLES[slug], rates=rates)


    if slug == "cutting-list":
        selected_date = request.args.get("date", "").strip()
        selected_game = request.args.get("game_id", "").strip()
        selected_session = request.args.get("session", "").strip()

        query = UserGameHistory.query.filter_by(is_reverted=False)

        if selected_date:
            try:
                filter_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
                query = query.filter(
                    db.func.date(UserGameHistory.created_at) == filter_date
                )
            except ValueError:
                selected_date = ""

        if selected_game:
            query = query.filter(
                UserGameHistory.game_type == selected_game
            )

        if selected_session in ["Open", "Close"]:
            query = query.filter(
                UserGameHistory.session == selected_session
            )

        bids = query.order_by(UserGameHistory.created_at.desc()).all()

        games = GameRate.query.order_by(GameRate.game_name.asc()).all()

        return render_template(
            "cutting_list.html",
            title="Cutting List",
            bids=bids,
            games=games,
            selected_date=selected_date,
            selected_game=selected_game,
            selected_session=selected_session
        )


    q = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    query = Record.query.filter_by(module=slug)
    if q:
        query = query.filter(or_(Record.title.ilike(f"%{q}%"), Record.details.ilike(f"%{q}%"),
                                 Record.status.ilike(f"%{q}%")))
    pagination = query.order_by(Record.created_at.desc()).paginate(page=page, per_page=12, error_out=False)
    return render_template("module_list.html", slug=slug, title=MODULE_TITLES[slug],
                           pagination=pagination, q=q)

@app.route("/admin/game-providers/market/add", methods=["GET", "POST"])
@login_required
def market_add():
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Market name is required.", "danger")
        elif Market.query.filter_by(name=name).first():
            flash("This market already exists.", "danger")
        else:
            schedule = {}
            for day in days:
                schedule[day] = {
                    "active": request.form.get(f"{day}_active") == "on",
                    "open": request.form.get(f"{day}_open", "09:25 PM"),
                    "close": request.form.get(f"{day}_close", "11:25 PM"),
                }
            db.session.add(Market(name=name, schedule_json=json.dumps(schedule)))
            db.session.commit()
            flash("Market added successfully.", "success")
            return redirect(url_for("module_page", slug="game-providers"))
    return render_template("market_form.html", market=None, days=days, schedule={})

@app.route("/admin/game-providers/market/<int:market_id>/edit", methods=["GET", "POST"])
@login_required
def market_edit(market_id):
    market = Market.query.get_or_404(market_id)
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    try:
        schedule = json.loads(market.schedule_json or "{}")
    except (TypeError, ValueError):
        schedule = {}
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        duplicate = Market.query.filter(Market.name == name, Market.id != market.id).first()
        if not name or duplicate:
            flash("Enter a unique market name.", "danger")
        else:
            market.name = name
            for day in days:
                schedule[day] = {
                    "active": request.form.get(f"{day}_active") == "on",
                    "open": request.form.get(f"{day}_open", "09:25 PM"),
                    "close": request.form.get(f"{day}_close", "11:25 PM"),
                }
            market.schedule_json = json.dumps(schedule)
            db.session.commit()
            flash("Market updated successfully.", "success")
            return redirect(url_for("module_page", slug="game-providers"))
    return render_template("market_form.html", market=market, days=days, schedule=schedule)

@app.post("/admin/game-providers/market/<int:market_id>/delete")
@login_required
def market_delete(market_id):
    market = Market.query.get_or_404(market_id)
    db.session.delete(market)
    db.session.commit()
    flash("Market deleted.", "success")
    return redirect(url_for("module_page", slug="game-providers"))

@app.post("/admin/game-rates/<int:rate_id>/edit")
@login_required
def game_rate_edit(rate_id):
    rate = GameRate.query.get_or_404(rate_id)
    value = request.form.get("rate", type=float)
    if value is None or value < 0:
        flash("Enter a valid rate.", "danger")
    else:
        rate.rate = value
        db.session.commit()
        flash(f"{rate.game_name} rate updated.", "success")
    return redirect(url_for("module_page", slug="game-rates"))

@app.route("/admin/<slug>/add", methods=["GET", "POST"])
@login_required
def module_add(slug):
    if slug not in MODULE_TITLES:
        abort(404)
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title:
            flash("Title is required.", "danger")
        else:
            record = Record(module=slug, title=title,
                            details=request.form.get("details", "").strip(),
                            value=request.form.get("value", 0, type=float),
                            status=request.form.get("status", "Active"))
            db.session.add(record)
            db.session.commit()
            flash(f"{MODULE_TITLES[slug]} record added.", "success")
            return redirect(url_for("module_page", slug=slug))
    return render_template("module_form.html", slug=slug, title=MODULE_TITLES[slug], record=None)

@app.route("/admin/<slug>/<int:record_id>/edit", methods=["GET", "POST"])
@login_required
def module_edit(slug, record_id):
    if slug not in MODULE_TITLES:
        abort(404)
    record = Record.query.filter_by(id=record_id, module=slug).first_or_404()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title:
            flash("Title is required.", "danger")
        else:
            record.title = title
            record.details = request.form.get("details", "").strip()
            record.value = request.form.get("value", 0, type=float)
            record.status = request.form.get("status", "Active")
            db.session.commit()
            flash("Record updated.", "success")
            return redirect(url_for("module_page", slug=slug))
    return render_template("module_form.html", slug=slug, title=MODULE_TITLES[slug], record=record)

@app.post("/admin/<slug>/<int:record_id>/delete")
@login_required
def module_delete(slug, record_id):
    if slug not in MODULE_TITLES:
        abort(404)
    record = Record.query.filter_by(id=record_id, module=slug).first_or_404()
    db.session.delete(record)
    db.session.commit()
    flash("Record deleted.", "success")
    return redirect(url_for("module_page", slug=slug))

@app.route("/admin/bid-revert")
@login_required
def bid_revert():
    selected_date = request.args.get("date", "").strip()
    selected_market = request.args.get("market_id", "all")
    selected_user = request.args.get("user_id", "")

    query = UserGameHistory.query.filter_by(is_reverted=False)

    # Date filter only when date is selected
    if selected_date:
        try:
            filter_date = datetime.strptime(
                selected_date, "%Y-%m-%d"
            ).date()

            query = query.filter(
                db.func.date(UserGameHistory.created_at) == filter_date
            )
        except ValueError:
            selected_date = ""

    if selected_market != "all":
        query = query.filter(UserGameHistory.game_name == selected_market)

    if selected_user:
        query = query.filter_by(user_id=int(selected_user))

    bets = query.order_by(UserGameHistory.created_at.desc()).all()

    users = User.query.order_by(User.name.asc()).all()
    markets = Market.query.order_by(Market.name.asc()).all()

    return render_template(
        "bid_revert.html",
        bets=bets,
        users=users,
        markets=markets,
        selected_date=selected_date,
        selected_market=selected_market,
        selected_user=selected_user
    )


@app.route("/admin/bid-revert/<int:bet_id>", methods=["POST"])
@login_required
def revert_single_bet(bet_id):
    bet = UserGameHistory.query.filter_by(
        id=bet_id,
        is_reverted=False
    ).first_or_404()

    user = User.query.get_or_404(bet.user_id)
    amount = float(bet.points_used or 0)

    if amount <= 0:
        flash("Invalid bet amount. Refund not processed.", "danger")
        return redirect(url_for("bid_revert"))

    try:
        user.points = float(user.points or 0) + amount

        bet.is_reverted = True
        bet.status = "Reverted"

        db.session.add(WalletTransaction(
            user_id=user.id,
            transaction_type="Credit",
            amount=amount,
            status="Completed",
            note=f"Bid Revert Refund - Bet ID #{bet.id}"
        ))

        db.session.commit()
        flash(f"₹{amount:.2f} refunded to {user.name}.", "success")

    except Exception:
        db.session.rollback()
        flash("Refund failed. Please try again.", "danger")

    return redirect(url_for("bid_revert"))

@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    if request.method == "POST":
        new_password = request.form.get("new_password", "")
        confirm = request.form.get("confirm_password", "")
        if new_password:
            if len(new_password) < 8:
                flash("Password must contain at least 8 characters.", "danger")
            elif new_password != confirm:
                flash("Passwords do not match.", "danger")
            else:
                admin = db.session.get(Admin, session["admin_id"])
                admin.set_password(new_password)
                db.session.commit()
                flash("Admin password updated.", "success")
        else:
            flash("Enter a new password.", "danger")
    return render_template("settings.html")

@app.route("/admin/notifications", methods=["GET", "POST"])
@login_required
def notifications():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        body = request.form.get("body", "").strip()
        if title and body:
            db.session.add(Notice(title=title, body=body))
            db.session.commit()
            flash("Notification published.", "success")
            return redirect(url_for("notifications"))
        flash("Title and message are required.", "danger")
    notices = Notice.query.order_by(Notice.created_at.desc()).all()
    return render_template("notices.html", notices=notices)

@app.post("/admin/notifications/<int:notice_id>/delete")
@login_required
def notice_delete(notice_id):
    notice = Notice.query.get_or_404(notice_id)
    db.session.delete(notice)
    db.session.commit()
    flash("Notification deleted.", "success")
    return redirect(url_for("notifications"))

@app.route("/admin/wallet/<int:user_id>/adjust", methods=["POST"])
@login_required
def wallet_adjust(user_id):
    user = User.query.get_or_404(user_id)
    amount = request.form.get("amount", 0, type=float)
    kind = request.form.get("kind", "credit")
    if amount <= 0:
        flash("Amount must be greater than zero.", "danger")
    elif kind == "debit" and user.points < amount:
        flash("Insufficient demo points.", "danger")
    else:
        user.points += amount if kind == "credit" else -amount
        db.session.add(WalletTransaction(user_id=user.id,
                       transaction_type=kind.title(), amount=amount,
                       status="Completed", note="Admin demo adjustment"))
        db.session.commit()
        flash("Demo points updated.", "success")
    return redirect(url_for("users"))


@app.route("/user-deposit", methods=["GET", "POST"])
def user_deposit():
    if "user_id" not in session:
        return redirect(url_for("user_login"))

    user = User.query.get_or_404(session["user_id"])

    if request.method == "POST":
        amount = request.form.get("amount", type=float)

        if amount is None or amount <= 0:
            flash("Enter a valid amount.", "danger")
            return redirect(url_for("user_deposit"))

        db.session.add(WalletTransaction(user_id=user.id, transaction_type="Deposit",
                       amount=amount, status="Pending", note="WhatsApp deposit request"))
        db.session.commit()
        message = (
            "SHREE SHYAM - DEPOSIT REQUEST\n"
            f"User Name: {user.name}\n"
            f"Registered Number: {user.phone}\n"
            f"Amount: Rs. {amount:.2f}\n"
            "Request: Deposit\n"
            "Status: Pending"
        )

        whatsapp_url = (
            "https://wa.me/917028490415?text=" + quote(message)
        )
        return redirect(whatsapp_url)

    return render_template("user_deposit.html", user=user)


@app.route("/user-withdraw", methods=["GET", "POST"])
def user_withdraw():
    if "user_id" not in session:
        return redirect(url_for("user_login"))

    user = User.query.get_or_404(session["user_id"])

    if request.method == "POST":
        amount = request.form.get("amount", type=float)

        if amount is None or amount <= 0:
            flash("Enter a valid amount.", "danger")
            return redirect(url_for("user_withdraw"))

        db.session.add(WalletTransaction(user_id=user.id, transaction_type="Withdraw",
                       amount=amount, status="Pending", note="WhatsApp withdraw request"))
        db.session.commit()
        message = (
            "SHREE SHYAM - WITHDRAW REQUEST\n"
            f"User Name: {user.name}\n"
            f"Registered Number: {user.phone}\n"
            f"Amount: Rs. {amount:.2f}\n"
            "Request: Withdraw\n"
            "Status: Pending"
        )

        whatsapp_url = (
            "https://wa.me/917028490415?text=" + quote(message)
        )
        return redirect(whatsapp_url)

    return render_template("user_withdraw.html", user=user)




@app.route("/generate-result", methods=["GET", "POST"])
@login_required
def generate_result():
    markets = Market.query.order_by(Market.name.asc()).all()

    if request.method == "POST":
        market_id = request.form.get("market_id", type=int)
        result_session = request.form.get("session", "").strip()
        pana = request.form.get("pana", "").strip()
        date_text = request.form.get("result_date", "").strip()

        market = db.session.get(Market, market_id)

        if not market or result_session not in ("Open", "Close"):
            flash("Please select a valid market and session.", "danger")

        elif len(pana) != 3 or not pana.isdigit():
            flash("Please select a valid 3-digit Pana.", "danger")

        else:
            try:
                result_date = (
                    datetime.strptime(date_text, "%Y-%m-%d").date()
                    if date_text else datetime.now().date()
                )

                # Find existing result for this market, date and session
                result = GameResult.query.filter_by(
                    market_name=market.name,
                    game_type=result_session,
                    result_date=result_date
                ).first()

                if result:
                    result.winning_number = pana
                else:
                    result = GameResult(
                        market_name=market.name,
                        game_type=result_session,
                        winning_number=pana,
                        result_date=result_date
                    )
                    db.session.add(result)

                db.session.commit()
                flash(f"{result_session} Result saved successfully!", "success")
                return redirect(url_for("generate_result"))

            except ValueError:
                flash("Invalid result date.", "danger")

    all_results = GameResult.query.filter(
        GameResult.game_type.in_(["Open", "Close"])
    ).order_by(
        GameResult.result_date.desc(),
        GameResult.market_name.asc()
    ).all()

    grouped = {}

    for result in all_results:
        key = (result.market_name, result.result_date)

        if key not in grouped:
            grouped[key] = {
                "market_name": result.market_name,
                "result_date": result.result_date,
                "open_pana": "-",
                "open_digit": "-",
                "close_pana": "-",
                "close_digit": "-"
            }

        digit = str(sum(int(x) for x in result.winning_number) % 10)

        if result.game_type == "Open":
            grouped[key]["open_pana"] = result.winning_number
            grouped[key]["open_digit"] = digit

        elif result.game_type == "Close":
            grouped[key]["close_pana"] = result.winning_number
            grouped[key]["close_digit"] = digit

    results = list(grouped.values())

    return render_template(
        "generate_result.html",
        markets=markets,
        results=results,
        today=datetime.now().strftime("%Y-%m-%d")
    )





@app.errorhandler(404)
def not_found(error):
    return render_template("errors/404.html"), 404

@app.errorhandler(500)
def server_error(error):
    db.session.rollback()
    return render_template("errors/500.html"), 500

def initialize_database():
    with app.app_context():
        db.create_all()
        if not Admin.query.filter_by(username="admin").first():
            admin = Admin(username="admin")
            admin.set_password(os.environ["INITIAL_ADMIN_PASSWORD"])
            db.session.add(admin)
            db.session.commit()
        default_rates = {
            "Single": 10, "Jodi": 100, "Single Pana": 160,
            "Double Pana": 320, "Triple Pana": 1000, "SP": 150,
            "DP": 300, "TP": 1000, "Family Pana": 150,
            "Cycle Pana": 150, "Half Sangam": 1200, "Full Sangam": 12000,
        }
        for game_name, rate_value in default_rates.items():
            if not GameRate.query.filter_by(game_name=game_name).first():
                db.session.add(GameRate(game_name=game_name, rate=rate_value))
        db.session.commit()

initialize_database()

if __name__ == "__main__":
    app.run(debug=True)


@app.context_processor
def inject_clock():
    return {"now_label": datetime.now().strftime("%d %b %Y"), "year": datetime.now().year}
