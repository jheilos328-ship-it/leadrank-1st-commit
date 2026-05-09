import json
import requests
from flask import Flask, request, render_template
from datetime import datetime
from supabase import create_client
from dotenv import load_dotenv
import os

load_dotenv()

print("URL:", os.environ.get("SUPABASE_URL"))
print("KEY:", os.environ.get("SUPABASE_ANON_KEY"))

app = Flask(__name__)

supabase = create_client(
    os.environ.get("SUPABASE_URL"),
    os.environ.get("SUPABASE_ANON_KEY")
)

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
def index():
    return render_template("index.html")


@app.route("/submit", methods=["POST"])
def submit():
    lead = {
        "id": datetime.now().strftime("%Y%m%d%H%M%S"),
        "name": request.form["name"],
        "email": request.form["email"],
        "phone": request.form["phone"],
        "problem": request.form["problem"],
        "urgency": request.form["urgency"],
        "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    analysis = analyze_lead(lead)
    lead["score"] = analysis["score"]
    lead["summary"] = analysis["summary"]
    lead["recommendation"] = analysis["recommendation"]

    supabase.table("leads").insert(lead).execute()

    return f"""
    <h2>Lead submitted and analyzed.</h2>
    <p><strong>Score:</strong> {lead['score']}/100</p>
    <p><strong>Summary:</strong> {lead['summary']}</p>
    <p><strong>Recommendation:</strong> {lead['recommendation']}</p>
    <br>
    <a href="/">Submit another</a>
    """


@app.route("/dashboard")
def dashboard():
    response = supabase.table("leads").select("*").order("score", desc=True).execute()
    leads = response.data

    return render_template("dashboard.html", leads=leads)


if __name__ == "__main__":
    app.run(debug=True)