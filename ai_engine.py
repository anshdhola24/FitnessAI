# ai_engine.py
"""
Simple rule-based engine for FitAI Planner.

Input: profile dict with keys:
  age, gender, height_cm, weight_kg, activity_level, goal,
  diet_type ("veg" / "nonveg" / "mixed"),
  workout_focus (string),
  experience_level ("beginner" / "intermediate" / "advanced")

Output: dict with:
  bmi, bmr, calories_target,
  diet_plan (dict),
  workout_plan (dict)
"""

def _calc_bmi(weight, height_cm):
    h_m = height_cm / 100.0
    if h_m <= 0:
        return 0
    return round(weight / (h_m * h_m), 1)


def _calc_bmr(age, gender, height_cm, weight):
    # Mifflin–St Jeor
    if gender.lower() == "female":
        bmr = 10 * weight + 6.25 * height_cm - 5 * age - 161
    else:
        bmr = 10 * weight + 6.25 * height_cm - 5 * age + 5
    return int(round(bmr))


def _activity_factor(level):
    return {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "very_active": 1.725,
        "athlete": 1.9,
    }.get(level, 1.4)


def _adjust_for_goal(calories, goal):
    goal = (goal or "").lower()
    if goal == "lose":
        return int(round(calories - 400))
    if goal == "gain":
        return int(round(calories + 300))
    return int(round(calories))


def _build_diet_plan(profile, calories_target):
    diet_type = (profile.get("diet_type") or "mixed").lower()
    goal = (profile.get("goal") or "").lower()

    if goal == "lose":
        focus = "Calorie‑controlled meals with high protein and fibre to support fat loss."
    elif goal == "gain":
        focus = "Higher‑calorie, protein‑focused meals to support muscle gain."
    else:
        focus = "Balanced meals to maintain weight and energy."

    if diet_type == "veg":
        breakfast = "Oats with milk + nuts + fruit"
        lunch = "Brown rice / roti with dal, veg sabzi and salad"
        dinner = "Paneer / tofu curry with roti and mixed salad"
        snacks = "Fruits, roasted chana, curd or buttermilk"
    elif diet_type == "nonveg":
        breakfast = "Eggs + whole‑wheat toast + fruit"
        lunch = "Rice / roti with chicken curry and salad"
        dinner = "Grilled fish / chicken with veggies"
        snacks = "Boiled eggs, yogurt, nuts"
    else:  # mixed
        breakfast = "Oats or eggs with fruit"
        lunch = "Rice / roti with dal or chicken and salad"
        dinner = "Paneer / egg / chicken with veggies"
        snacks = "Fruits, nuts, yogurt"

    return {
        "focus": focus,
        "diet_type": diet_type,
        "calories_target": calories_target,
        "breakfast": breakfast,
        "lunch": lunch,
        "dinner": dinner,
        "snacks": snacks,
    }


def _sets_reps_for_level(level):
    level = (level or "beginner").lower()
    if level == "advanced":
        return "4–5 sets × 6–10 reps (heavier weight)"
    if level == "intermediate":
        return "3–4 sets × 8–12 reps"
    return "2–3 sets × 10–15 reps"


def _build_strength_split(level_desc):
    sr = level_desc
    return [
        f"Chest + Triceps – presses, push‑ups, dips ({sr})",
        f"Back + Biceps – rows, pulldowns, curls ({sr})",
        f"Legs – squats, lunges, hip hinge work ({sr})",
        f"Shoulders – overhead press, lateral raises ({sr})",
        f"Full‑body / weak‑point focus – mix of compounds and isolation ({sr})",
    ]


def _build_calisthenics_split(level_desc):
    sr = level_desc
    return [
        f"Push day – push‑ups, dips, pike push‑ups ({sr})",
        f"Pull day – inverted rows, bodyweight rows ({sr})",
        f"Legs + core – squats, lunges, planks ({sr})",
        f"Upper body skills – harder push / pull progressions ({sr})",
        f"Full‑body circuit – 6–8 exercises done in a circuit ({sr})",
    ]


def _build_cardio_split(level):
    if level == "advanced":
        base = "30–45 min moderate run + intervals at the end"
    elif level == "intermediate":
        base = "25–35 min steady jog / brisk walk"
    else:
        base = "20–30 min brisk walk or easy cycling"

    return [
        f"Low‑intensity cardio – {base}",
        f"Interval cardio – short bursts + easy recovery",
        "Mixed cardio (bike / walk / jog) – easy to moderate",
        "Uphill or stair cardio – controlled pace",
        "Favourite cardio modality – repeat best session of the week",
    ]


def _build_generic_split(level_desc):
    sr = level_desc
    return [
        f"Full body A – squat / push / pull ({sr})",
        f"Full body B – hinge / horizontal push / row ({sr})",
        f"Lower focus – quads + hamstrings + calves ({sr})",
        f"Upper focus – chest, back, shoulders, arms ({sr})",
        f"Conditioning – lighter full‑body circuit ({sr})",
    ]


def _build_workout_plan(profile):
    focus = (profile.get("workout_focus") or "general").lower()
    level = (profile.get("experience_level") or "beginner").lower()

    level_desc = _sets_reps_for_level(level)

    if focus in ("strength", "power", "functional"):
        days_1_to_5 = _build_strength_split(level_desc)
        base_label = "Strength / Functional Split"
    elif focus in ("calisthenics",):
        days_1_to_5 = _build_calisthenics_split(level_desc)
        base_label = "Calisthenics Split"
    elif focus in ("cardio", "endurance"):
        days_1_to_5 = _build_cardio_split(level)
        base_label = "Cardio / Endurance Plan"
    elif focus in ("mobility",):
        days_1_to_5 = [
            "Full‑body mobility: hips, shoulders, thoracic spine",
            "Lower‑body stretching + ankle mobility",
            "Upper‑body stretching + band work",
            "Yoga‑style flow (20–30 min)",
            "Mixed light mobility and core stability",
        ]
        base_label = "Mobility & Flexibility Plan"
    else:
        days_1_to_5 = _build_generic_split(level_desc)
        base_label = "General Fitness Plan"

    # Always include Day 6 + Day 7
    day6 = "Active recovery – light walk, stretching, very easy mobility (15–30 min)."
    day7 = "Full rest – no hard training. Focus on sleep, hydration and good food."

    workouts = days_1_to_5 + [day6, day7]

    level_name = level.capitalize()
    return {
        "level": f"{level_name} • {base_label}",
        "focus": focus,
        "activity_base": profile.get("activity_level", ""),
        "workouts": workouts,
    }


def build_complete_plan(profile: dict) -> dict:
    age = profile["age"]
    gender = profile["gender"]
    height_cm = profile["height_cm"]
    weight_kg = profile["weight_kg"]
    activity_level = profile["activity_level"]
    goal = profile["goal"]

    bmi = _calc_bmi(weight_kg, height_cm)
    bmr = _calc_bmr(age, gender, height_cm, weight_kg)
    tdee = bmr * _activity_factor(activity_level)
    calories_target = _adjust_for_goal(tdee, goal)

    diet_plan = _build_diet_plan(profile, calories_target)
    workout_plan = _build_workout_plan(profile)

    return {
        "bmi": bmi,
        "bmr": bmr,
        "calories_target": calories_target,
        "diet_plan": diet_plan,
        "workout_plan": workout_plan,
    }
