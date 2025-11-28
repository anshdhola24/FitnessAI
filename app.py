# app.py
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    send_file,
    jsonify,
)
from flask_bcrypt import Bcrypt
from sqlalchemy.exc import IntegrityError
from database import SessionLocal
from models import User, UserProfile, Plan, Progress, init_db
from ai_engine import build_complete_plan
from functools import wraps
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import mm
import ast

app = Flask(__name__)
app.secret_key = "supersecretkey"  # change in real app
bcrypt = Bcrypt(app)

# Initialize DB
init_db()


# ---------------------------------------------------------
# Helper function: Get currently logged-in user
# ---------------------------------------------------------
def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    db = SessionLocal()
    user = db.query(User).filter_by(id=user_id).first()
    db.close()
    return user


# -------------------------------------------------------------------
# Admin helpers
# -------------------------------------------------------------------
@app.context_processor
def inject_globals():
    user = get_current_user()
    is_admin = bool(user and user.email == "anshdhola05@gmail.com")
    return dict(current_user=user, is_admin=is_admin)


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if not user or user.email != "anshdhola05@gmail.com":
            flash("Admin access only.", "danger")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)

    return wrapper


# ---------------------------------------------------------
# Routes
# ---------------------------------------------------------
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    db = SessionLocal()
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        hashed = bcrypt.generate_password_hash(password).decode("utf-8")

        new_user = User(name=name, email=email, password_hash=hashed)
        db.add(new_user)
        try:
            db.commit()
            flash("Registration successful. Please login.", "success")
            return redirect(url_for("login"))
        except IntegrityError:
            db.rollback()
            flash("Email already exists.", "danger")
        finally:
            db.close()
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    db = SessionLocal()
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = db.query(User).filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            session["user_id"] = user.id
            flash("Logged in successfully.", "success")
            db.close()
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid credentials.", "danger")
    db.close()
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("Logged out.", "info")
    return redirect(url_for("home"))


@app.route("/profile", methods=["GET", "POST"])
def profile():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    db = SessionLocal()
    profile = db.query(UserProfile).filter_by(user_id=user.id).first()

    if request.method == "POST":
        age = int(request.form["age"])
        gender = request.form["gender"]
        height_cm = float(request.form["height"])
        weight_kg = float(request.form["weight"])
        activity_level = request.form["activity"]
        goal = request.form["goal"]
        experience_level = request.form.get("experience_level", "beginner")

        if profile:
            profile.age = age
            profile.gender = gender
            profile.height_cm = height_cm
            profile.weight_kg = weight_kg
            profile.activity_level = activity_level
            profile.goal = goal
            profile.experience_level = experience_level
        else:
            profile = UserProfile(
                user_id=user.id,
                age=age,
                gender=gender,
                height_cm=height_cm,
                weight_kg=weight_kg,
                activity_level=activity_level,
                goal=goal,
                experience_level=experience_level,
            )
            db.add(profile)

        db.commit()
        db.close()
        flash("Profile updated.", "success")
        # after updating profile, generate a fresh plan
        return redirect(url_for("generate_plans"))

    db.close()
    return render_template("profile.html", profile=profile)


@app.route("/admin")
@admin_required
def admin_dashboard():
    db = SessionLocal()
    users = db.query(User).all()

    users_data = []
    for u in users:
        profile = db.query(UserProfile).filter_by(user_id=u.id).first()
        plan_count = db.query(Plan).filter_by(user_id=u.id).count()
        progress_count = db.query(Progress).filter_by(user_id=u.id).count()

        users_data.append(
            {
                "user": u,
                "profile": profile,
                "plan_count": plan_count,
                "progress_count": progress_count,
            }
        )

    db.close()
    return render_template("admin_dashboard.html", users_data=users_data)


@app.route("/dashboard")
def dashboard():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    db = SessionLocal()
    profile = db.query(UserProfile).filter_by(user_id=user.id).first()
    plan = db.query(Plan).filter_by(user_id=user.id).order_by(Plan.id.desc()).first()
    progress_rows = (
        db.query(Progress).filter_by(user_id=user.id).order_by(Progress.day).all()
    )
    db.close()

    labels = [f"Day {p.day}" for p in progress_rows]
    weights = [p.weight_kg for p in progress_rows]

    bmi_status = None
    if plan:
        bmi_val = plan.bmi
        if bmi_val < 18.5:
            bmi_status = "Underweight"
        elif bmi_val < 25:
            bmi_status = "Normal"
        elif bmi_val < 30:
            bmi_status = "Overweight"
        else:
            bmi_status = "Obese"

    return render_template(
        "dashboard.html",
        user=user,
        profile=profile,
        plan=plan,
        progress=progress_rows,
        chart_labels=labels,
        chart_weights=weights,
        bmi_status=bmi_status,
    )


@app.route("/generate-plans")
def generate_plans():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    db = SessionLocal()
    profile = db.query(UserProfile).filter_by(user_id=user.id).first()
    if not profile:
        db.close()
        flash("Please complete your profile first.", "warning")
        return redirect(url_for("profile"))

    diet_pref = request.args.get("diet", "mixed")
    workout_focus = request.args.get("workout", "general")

    profile_dict = {
        "age": profile.age,
        "gender": profile.gender,
        "height_cm": profile.height_cm,
        "weight_kg": profile.weight_kg,
        "activity_level": profile.activity_level,
        "goal": profile.goal,
        "diet_type": diet_pref,
        "workout_focus": workout_focus,
        "experience_level": profile.experience_level or "beginner",
    }

    result = build_complete_plan(profile_dict)

    new_plan = Plan(
        user_id=user.id,
        bmi=result["bmi"],
        bmr=result["bmr"],
        calories_target=result["calories_target"],
        diet_plan=str(result["diet_plan"]),
        workout_plan=str(result["workout_plan"]),
    )
    db.add(new_plan)
    db.commit()
    db.close()

    flash("New AI-based plan generated.", "success")
    return redirect(url_for("plans"))


@app.route("/plans")
def plans():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    db = SessionLocal()
    plan = db.query(Plan).filter_by(user_id=user.id).order_by(Plan.id.desc()).first()
    db.close()

    if not plan:
        flash("No plan found. Generate one first.", "info")
        return redirect(url_for("generate_plans"))

    diet_plan = ast.literal_eval(plan.diet_plan)
    workout_plan = ast.literal_eval(plan.workout_plan)

    return render_template(
        "plans.html",
        plan=plan,
        diet_plan=diet_plan,
        workout_plan=workout_plan,
    )


@app.route("/download-plan")
def download_plan():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    db = SessionLocal()
    plan = (
        db.query(Plan)
        .filter_by(user_id=user.id)
        .order_by(Plan.id.desc())
        .first()
    )
    db.close()

    if not plan:
        flash("No plan found to download.", "info")
        return redirect(url_for("plans"))

    diet_plan = ast.literal_eval(plan.diet_plan)
    workout_plan = ast.literal_eval(plan.workout_plan)

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    margin_x = 25 * mm
    margin_y = 25 * mm
    header_height = 32
    y = height - margin_y

    # HEADER BAR
    c.setFillColorRGB(0.09, 0.20, 0.45)
    c.rect(0, height - header_height - 10, width, header_height + 10, stroke=0, fill=1)
    c.setFillColorRGB(0.15, 0.40, 0.90)
    c.rect(0, height - header_height, width, header_height, stroke=0, fill=1)

    logo_radius = 9
    logo_cx = margin_x
    logo_cy = height - header_height / 2 - 5

    c.setFillColor(colors.white)
    c.circle(logo_cx, logo_cy, logo_radius, stroke=0, fill=1)

    c.setFillColorRGB(0.11, 0.27, 0.65)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(logo_cx, logo_cy - 3, "F")

    text_x = logo_cx + 2 * logo_radius + 6
    text_y = logo_cy + 2

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 15)
    c.drawString(text_x, text_y, "FitAI Planner")

    c.setFont("Helvetica", 8.5)
    c.setFillColorRGB(0.88, 0.94, 1)
    c.drawString(text_x, text_y - 12, "Smart Fitness & Diet Assistant")

    title = "Personalised Fitness & Diet Plan"
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(colors.white)
    c.drawCentredString(width / 2, height - header_height + 4, title)

    y = height - header_height - 20

    # USER SUMMARY
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(colors.black)
    c.drawString(margin_x, y, f"👤  User: {user.name}")
    y -= 16

    c.setFont("Helvetica", 9.5)
    c.drawString(margin_x, y, f"BMI: {plan.bmi}     BMR: {plan.bmr} kcal/day")
    y -= 13
    c.drawString(margin_x, y, f"Target Calories: {plan.calories_target} kcal/day")
    y -= 18

    c.setStrokeColorRGB(0.8, 0.85, 0.9)
    c.line(margin_x, y, width - margin_x, y)
    y -= 18

    # DIET PLAN
    c.setFont("Helvetica-Bold", 11.5)
    c.setFillColorRGB(0.11, 0.27, 0.65)
    c.drawString(margin_x, y, "🍽  Diet Plan")
    y -= 14

    c.setFont("Helvetica", 9)
    c.setFillColor(colors.black)
    focus = diet_plan.get("focus", "")
    c.drawString(margin_x, y, focus[:110])
    y -= 18

    box_height = 72
    c.setStrokeColorRGB(0.82, 0.86, 0.94)
    c.setFillColorRGB(0.97, 0.98, 1)
    c.roundRect(
        margin_x,
        y - box_height,
        width - 2 * margin_x,
        box_height,
        6,
        stroke=1,
        fill=1,
    )

    row_y = y - 12

    def diet_row(label, value):
        nonlocal row_y
        c.setFont("Helvetica-Bold", 9)
        c.setFillColorRGB(0.12, 0.16, 0.26)
        c.drawString(margin_x + 6, row_y, label)
        c.setFont("Helvetica", 9)
        c.setFillColor(colors.black)
        c.drawString(margin_x + 70, row_y, (value or "")[:80])
        row_y -= 14

    diet_row("Breakfast:", diet_plan.get("breakfast", ""))
    diet_row("Lunch:", diet_plan.get("lunch", ""))
    diet_row("Dinner:", diet_plan.get("dinner", ""))
    diet_row("Snacks:", diet_plan.get("snacks", ""))

    y = y - box_height - 26

    # WORKOUT PLAN
    if y < margin_y + 80:
        c.showPage()
        y = height - margin_y

    c.setFont("Helvetica-Bold", 11.5)
    c.setFillColorRGB(0.11, 0.27, 0.65)
    c.drawString(margin_x, y, "🏋️  Workout Plan")
    y -= 14

    c.setFont("Helvetica", 9)
    c.setFillColor(colors.black)
    c.drawString(margin_x, y, workout_plan.get("level", ""))
    y -= 16

    workouts = workout_plan.get("workouts", [])

    for i, w in enumerate(workouts, start=1):
        if y < 40:
            c.showPage()
            y = height - margin_y
            c.setFont("Helvetica-Bold", 10.5)
            c.drawString(margin_x, y, "Workout Plan (continued)")
            y -= 16
            c.setFont("Helvetica", 9)

        c.drawString(margin_x, y, f"Day {i}: {w}")
        y -= 13

    c.setFont("Helvetica-Oblique", 8)
    c.setFillColorRGB(0.45, 0.5, 0.6)
    c.drawString(
        margin_x,
        18,
        "Generated by FitAI Planner • This plan is for educational purposes only.",
    )

    c.showPage()
    c.save()

    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name="fitai_plan.pdf",
        mimetype="application/pdf",
    )


@app.route("/save-custom-workout", methods=["POST"])
def save_custom_workout():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    db = SessionLocal()
    plan = db.query(Plan).filter_by(user_id=user.id).order_by(Plan.id.desc()).first()
    if not plan:
        db.close()
        flash("No plan found to update.", "warning")
        return redirect(url_for("plans"))

    try:
        existing = ast.literal_eval(plan.workout_plan)
    except Exception:
        existing = {}

    activity_base = existing.get("activity_base", "")

    workouts = [
        request.form.get("day1", "").strip(),
        request.form.get("day2", "").strip(),
        request.form.get("day3", "").strip(),
        request.form.get("day4", "").strip(),
        request.form.get("day5", "").strip(),
    ]

    workout_plan = {
        "level": "Custom Plan (User-Defined)",
        "activity_base": activity_base,
        "focus": "custom",
        "workouts": workouts,
    }

    plan.workout_plan = str(workout_plan)
    db.commit()
    db.close()

    flash("Your custom workout plan has been saved.", "success")
    return redirect(url_for("plans"))


@app.route("/add-progress", methods=["POST"])
def add_progress():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    day = int(request.form["day"])
    weight = float(request.form["weight"])

    db = SessionLocal()
    existing = db.query(Progress).filter_by(user_id=user.id, day=day).first()
    if existing:
        existing.weight_kg = weight
    else:
        rec = Progress(user_id=user.id, day=day, weight_kg=weight)
        db.add(rec)

    db.commit()
    db.close()
    flash("Progress updated.", "success")
    return redirect(url_for("dashboard"))


@app.route("/reset-progress", methods=["POST"])
def reset_progress():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    db = SessionLocal()
    db.query(Progress).filter_by(user_id=user.id).delete()
    db.commit()
    db.close()

    flash("All progress entries have been cleared.", "info")
    return redirect(url_for("dashboard"))



@app.route("/trainer", methods=["GET", "POST"])
def trainer():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    db = SessionLocal()
    profile = db.query(UserProfile).filter_by(user_id=user.id).first()
    plan = db.query(Plan).filter_by(user_id=user.id).order_by(Plan.id.desc()).first()

    diet_plan = workout_plan = None
    if plan:
        diet_plan = ast.literal_eval(plan.diet_plan)
        workout_plan = ast.literal_eval(plan.workout_plan)

    if request.method == "GET":
        db.close()
        return render_template("trainer.html", profile=profile, plan=plan)

    # POST: chat message
    data = request.get_json(silent=True) or {}
    message = data.get("message", "")

    reply = generate_coach_reply(user, profile, plan, diet_plan, workout_plan, message)
    db.close()
    return jsonify({"reply": reply})


if __name__ == "__main__":
    app.run(debug=True)
