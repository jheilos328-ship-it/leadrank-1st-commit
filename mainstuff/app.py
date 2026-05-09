import json
import requests
from flask import Flask, request, render_template, redirect, url_for, session
from datetime import datetime
from supabase import create_client
from dotenv import load_dotenv
import os
import functools


load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")

supabase = create_client(
    os.environ.get("SUPABASE_URL"),
    os.environ.get("SUPABASE_ANON_KEY")
)

# --- Auth helper ---
def login_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("access_token"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def get_user_org_id(access_token, user_id):
    if not access_token or not user_id:
        return None

    supabase.postgrest.auth(access_token)
    org_response = supabase.table("organizations").select("id").eq(
        "owner_id", user_id
    ).maybe_single().execute()

    if not org_response or not getattr(org_response, "data", None):
        return None

    return org_response.data["id"]


# --- Auth routes ---
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        business_name = request.form["business_name"]

        try:
            # Create user in Supabase auth
            result = supabase.auth.sign_up({
                "email": email,
                "password": password
            })

            if result.session is None:
                return render_template(
                    "signup.html",
                    message="A confirmation email was sent. Please verify your email before logging in."
                )

            user_id = result.user.id
            access_token = result.session.access_token

            # Create their organization
            supabase.postgrest.auth(access_token)
            supabase.table("organizations").insert({
                "name": business_name,
                "owner_id": user_id
            }).execute()

            # Store session
            session["access_token"] = access_token
            session["user_id"] = user_id

            return redirect(url_for("dashboard"))

        except Exception as e:
            return render_template("signup.html", error=str(e))

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        try:
            result = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            session["access_token"] = result.session.access_token
            session["user_id"] = result.user.id

            if not get_user_org_id(session["access_token"], session["user_id"]):
                return redirect(url_for("create_org"))

            return redirect(url_for("dashboard"))

        except Exception as e:
            return render_template("login.html", error="Invalid email or password")

    return render_template("login.html")


@app.route("/logout")
def logout():
    supabase.auth.sign_out()
    session.clear()
    return redirect(url_for("login"))


# --- App routes ---
def analyze_lead(lead):
    prompt = f"""
You are an assistant that helps HVAC business owners prioritize their leads.

Analyze this customer submission and return exactly 3 things:
1. SCORE: A number from 1 to 100 (100 being most urgent and most money)
2. SUMMARY: One sentence explaining the situation
3. RECOMMENDATION: One sentence on what the owner should do and why

Here is the lead:
From: {lead['name']} ({lead['email']})
Phone: {lead['phone']}
Problem: {lead['problem']}
Urgency: {lead['urgency']}

Respond with only a valid JSON object and absolutely nothing else. No extra strings or code.
Example of valid response:
{{"score": 65, "summary": "your summary here", "recommendation": "your recommendation here"}}

Every lead must have a unique score. No two leads can share the same score.
If two leads seem equally urgent, look more closely at financial impact,
safety risk, and how soon the customer needs help to break the tie.
Use this as a guide:
80-100: Emergency. Safety risk, system completely down, needs same day response.
50-79: Urgent. System struggling, customer has a deadline or dependents at home.
20-49: Routine. System working but needs attention within the week.
1-19: Low priority. Maintenance, curiosity, no real urgency.

If the customer explicitly states they are managing fine and there is no immediate safety risk, 
do not score above 50 regardless of symptoms described.
"""

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "llama3.1",
            "prompt": prompt,
            "stream": False
        }
    )

    raw = response.json()["response"]
    parsed = json.loads(raw)
    return parsed


@app.route("/")
@login_required
def index():
    if not get_user_org_id(session.get("access_token"), session.get("user_id")):
        return redirect(url_for("create_org"))
    return render_template("index.html")


@app.route("/create-org", methods=["GET", "POST"])
@login_required
def create_org():
    access_token = session.get("access_token")
    user_id = session.get("user_id")

    if get_user_org_id(access_token, user_id):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        business_name = request.form["business_name"]
        supabase.postgrest.auth(access_token)
        supabase.table("organizations").insert({
            "name": business_name,
            "owner_id": user_id
        }).execute()
        return redirect(url_for("dashboard"))

    return render_template("create_org.html")


@app.route("/submit", methods=["POST"])
@login_required
def submit():
    # Get the org_id for this user
    access_token = session.get("access_token")
    org_id = get_user_org_id(access_token, session["user_id"])

    if not org_id:
        return (
            "<h2>Error: organization not found.</h2>"
            "<p>Your account does not have a linked organization record.</p>"
            "<p>Please confirm your email, log in again, and retry signup if needed.</p>"
            "<p><a href=\"/logout\">Logout</a></p>",
            400,
        )

    lead = {
        "id": datetime.now().strftime("%Y%m%d%H%M%S"),
        "name": request.form["name"],
        "email": request.form["email"],
        "phone": request.form["phone"],
        "problem": request.form["problem"],
        "urgency": request.form["urgency"],
        "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "org_id": org_id
    }

    analysis = analyze_lead(lead)
    lead["score"] = analysis["score"]
    lead["summary"] = analysis["summary"]
    lead["recommendation"] = analysis["recommendation"]

    supabase.table("leads").insert(lead).execute()

    return render_template("lead_result.html", lead=lead)


@app.route("/dashboard")
@login_required
def dashboard():
    access_token = session.get("access_token")
    supabase.postgrest.auth(access_token)

    response = supabase.table("leads").select("*").order("score", desc=True).execute()
    leads = response.data

    return render_template("dashboard.html", leads=leads)


if __name__ == "__main__":
    app.run(debug=True)
