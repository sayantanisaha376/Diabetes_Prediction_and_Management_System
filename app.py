from flask import Flask, render_template, request, redirect, url_for, send_file, session, flash
import sqlite3
import pickle
import numpy as np
import pandas as pd
from fpdf import FPDF
import os
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import google.generativeai as genai  # Import Google Generative AI
import logging
import json



# Load API key from .env file
load_dotenv()
genai_api_key = os.getenv("GENAI_API_KEY")

if not genai_api_key:
    raise ValueError("Missing Google Generative AI API Key. Add GENAI_API_KEY to .env file.")

# Configure Google Generative AI client
genai.configure(api_key=genai_api_key)

app = Flask(__name__)
app.secret_key = "your_secret_key"

# Load trained model
try:
    with open("diabetes_model.pkl", "rb") as model_file:
        model = pickle.load(model_file)
except FileNotFoundError:
    raise FileNotFoundError("diabetes_model.pkl not found. Please train the model and place it in the directory.")

# Database connection
def create_connection():
    return sqlite3.connect("database.db", check_same_thread=False)

# Create database tables
def init_db():
    conn = create_connection()
    cur = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS diet_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_input TEXT NOT NULL,
            response TEXT NOT NULL
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            age REAL NOT NULL,
            bmi REAL NOT NULL,
            glucose REAL NOT NULL,
            insulin REAL NOT NULL,
            result TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()

init_db()

# Home route
@app.route("/")
def home():
    if "user" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")

# Register route
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])

        conn = create_connection()
        cur = conn.cursor()

        cur.execute("SELECT * FROM users WHERE username = ?", (username,))
        if cur.fetchone():
            flash("Username already exists!", "danger")
            return redirect(url_for("register"))

        cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        conn.close()

        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")

# Login route
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = create_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cur.fetchone()
        conn.close()

        if user and check_password_hash(user[2], password):
            session["user"] = username
            flash("Login successful!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid username or password!", "danger")

    return render_template("login.html")

# Dashboard route
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        flash("Please log in to access the dashboard.", "warning")
        return redirect(url_for("login"))
    return render_template("dashboard.html", username=session["user"])

# AI Diet Recommendation using GenAI
@app.route("/diet", methods=["GET", "POST"])
def diet():
    weekly_diet_plan = None
    if request.method == "POST":
        age = int(request.form["age"])
        lifestyle = request.form["lifestyle"]
        meal_preference = request.form["meal_preference"]
        meals_per_day = int(request.form["meals_per_day"])
        weight = float(request.form["weight"])
        height = float(request.form["height"])

        # Calculate BMI (optional, for reference)
        bmi = round(weight / ((height / 100) ** 2), 2)

        # Calculate water intake (liters/day)
        water_intake = round(weight * 0.033, 2)

        # Macronutrient recommendations per meal
        protein_per_meal = round(0.8 * weight / meals_per_day, 1)  # in grams
        carbs_per_meal = round((weight * 1.2) / meals_per_day, 1)  # in grams
        fats_per_meal = round((weight * 0.4) / meals_per_day, 1)   # in grams

        # Diverse meal suggestions
        meal_suggestions = {
            "veg": [
                "Quinoa salad with roasted vegetables and nuts",
                "Lentil soup with whole-grain bread",
                "Vegetable stir-fry with tofu and rice",
                "Avocado toast with chia seeds and fruit",
                "Spinach and chickpea curry with naan bread",
                "Stuffed bell peppers with black beans and quinoa",
                "Mushroom risotto with asparagus and Parmesan cheese"
            ],
            "nonveg": [
                "Grilled chicken with sweet potatoes and broccoli",
                "Salmon with wild rice and green beans",
                "Turkey wrap with hummus and mixed greens",
                "Egg omelette with whole-grain toast and avocado",
                "Beef stir-fry with rice noodles and vegetables",
                "Shrimp tacos with salsa and a side of coleslaw",
                "Baked cod with quinoa and roasted brussels sprouts"
            ]
        }

        # Generate a 7-day meal plan with varied options
        weekly_diet_plan = {}
        for day, suggestion in zip(
            ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
            meal_suggestions[meal_preference]
        ):
            meals = []
            for meal in range(1, meals_per_day + 1):
                meals.append({
                    "meal_name": f"Meal {meal}",
                    "protein": f"{protein_per_meal}g Protein",
                    "carbs": f"{carbs_per_meal}g Carbs",
                    "fats": f"{fats_per_meal}g Fats",
                    "suggestion": suggestion
                })
            weekly_diet_plan[day] = meals

        return render_template(
            "diet.html",
            weekly_diet_plan=weekly_diet_plan,
            water_intake=water_intake
        )

    return render_template("diet.html")

# Download Diet Plan as PDF
@app.route("/download_diet", methods=["POST"])
def download_diet():
    file_name = f"{session['user']}_diet_plan_{uuid.uuid4().hex}.pdf"  # Initialize file_name to avoid UnboundLocalError
    try:
        # Receive and validate the diet plan and water intake from the form
        diet_plan = request.form.get("diet_plan")
        water_intake = request.form.get("water_intake")

        if not diet_plan or not water_intake:
            raise ValueError("Missing diet plan or water intake data.")

        # Parse the JSON data into Python objects
        diet_plan = json.loads(diet_plan)

        # Create a unique file name for the PDF
        file_name = f"diet_plan_{uuid.uuid4().hex}.pdf"

        # Initialize FPDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        # Add title to the PDF
        pdf.set_font("Arial", style="B", size=16)
        pdf.cell(200, 10, txt="Personalized Weekly Diet Plan", ln=True, align="C")
        pdf.ln(10)

        # Add water intake recommendation
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"Recommended Water Intake: {water_intake} liters/day", ln=True)
        pdf.ln(10)

        # Add the weekly diet plan to the PDF
        for day, meals in diet_plan.items():
            pdf.set_font("Arial", style="B", size=14)
            pdf.cell(200, 10, txt=f"{day}:", ln=True)
            pdf.ln(5)
            pdf.set_font("Arial", size=12)
            for meal in meals:
                pdf.cell(200, 8, txt=f"- {meal['meal_name']}: {meal['suggestion']} ({meal['protein']}, {meal['carbs']}, {meal['fats']})", ln=True)
            pdf.ln(5)

        # Save PDF file
        pdf.output(file_name)

        # Return the PDF for download
        return send_file(file_name, as_attachment=True, download_name="Weekly_Diet_Plan.pdf")

    except json.JSONDecodeError:
        logging.error("Failed to decode JSON data.")
        return "Error decoding JSON data. Please check the data being sent.", 400
    except ValueError as ve:
        logging.error(f"Value error: {ve}")
        return f"An error occurred: {ve}", 400
    except Exception as e:
        logging.error(f"Unexpected error in /download_diet: {e}")
        return f"An error occurred: {e}", 500
    finally:
        # Cleanup: Remove the PDF file if it was created
        if file_name and os.path.exists(file_name):
            os.remove(file_name)

# Predict glucose levels
@app.route("/predict", methods=["GET", "POST"])
def predict():
    prediction = None
    if request.method == "POST":
        try:
            features = [
                float(request.form["age"]),
                float(request.form["bmi"]),
                float(request.form["glucose"]),
                float(request.form["insulin"])
            ]

            if any(f < 0 for f in features):
                flash("Invalid input! All values must be non-negative.", "danger")
                return render_template("predict.html", prediction=None)

            prediction = model.predict([np.array(features)])[0]

            conn = create_connection()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO predictions (age, bmi, glucose, insulin, result) VALUES (?, ?, ?, ?, ?)",
                (features[0], features[1], features[2], features[3], prediction)
            )
            conn.commit()
            conn.close()

        except ValueError:
            flash("Please enter valid numerical values.", "danger")
        except Exception as e:
            flash(f"Prediction error: {str(e)}", "danger")

    return render_template("predict.html", prediction=prediction)

# Logout route
@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("Logged out successfully.", "info")
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)