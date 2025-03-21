from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
from flask_cors import CORS

app = Flask(__name__)
app.secret_key = "123"

CORS(app, supports_credentials=True, origins=["http://localhost:5173", "https://localhost:4433"])

PORTAL_LOGIN_URL = "https://ims.ritchennai.edu.in/login"
PORTAL_GRADES_URL = "https://ims.ritchennai.edu.in/admin/grade/student/mark/get_marks"
PORTAL_CSRF_URL = "https://ims.ritchennai.edu.in/admin/grade/student/mark/report"

LOGIN_FAILURE_MSG = "These credentials do not match our records."

credits_mapper = {
    "Engineering Chemistry": 3,
    "Chemistry Laboratory": 1,
    "Problem Solving and C Programming": 3,
    "Heritage of Tamil": 0,
    "Problem Solving and C Programming Laboratory": 1,
    "Engineering Practices Laboratory": 1,
    "Engineering Graphics": 4,
    "Communicative English": 3,
    "Matrices and Calculus": 4,
    "Python for Data science ": 3,
    "Python for Data Science Laboratory ": 1,
    "Basic Electrical and Electronics\nEngineering ": 3,
    "Communication Laboratory /\nForeign Language ": 1,
    "Professional English ": 2,
    "Statistics and Numerical Methods ": 4,
    "Physics for Information Science ": 3,
    "Physics Laboratory ": 1,
    "Fundamentals of Economics and Financial Accounting": 4,
    "Object Oriented Programming": 3,
    "Data Structures and Algorithms": 3,
    "Digital Principles and Computer Organization": 4,
    "Discrete Mathematics": 3,
    "Object Oriented Programming Laboratory": 1,
    "Data Structures and Algorithms\nLaboratory": 1,
    "Design Thinking": 1,
}

letter_mapper = {"O": 10, "A+": 9, "A": 8, "B+": 7, "B": 6, "C": 5, "U": 0}


@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.json
    register_number = data.get("register_number")
    phone_number = data.get("phone_number")

    session = requests.Session()
    
    login_page = session.get(PORTAL_LOGIN_URL)
    login_soup = BeautifulSoup(login_page.content, 'lxml')
    _token = login_soup.find("input", {"name": "_token"})["value"]

    payload = {"_token": _token, "email": register_number, "password": phone_number}
    response = session.post(PORTAL_LOGIN_URL, data=payload)
    
    if LOGIN_FAILURE_MSG in response.text:
        return jsonify({"error": "Invalid credentials"}), 401

    cookies = session.cookies.get_dict()
    resp = jsonify({"message": "Login successful"})
    for key, value in cookies.items():
        resp.set_cookie(key, value, httponly=True, secure=True, samesite="None")

    return resp

@app.route("/api/get_grades", methods=["GET"])
def get_grades():
    cookies = {
        "XSRF-TOKEN": request.cookies.get("XSRF-TOKEN"),
        "laravel_session": request.cookies.get("laravel_session"),
    }

    if not cookies["XSRF-TOKEN"] or not cookies["laravel_session"]:
        return jsonify({"error": "Not logged in"}), 403
    session = requests.Session()
    session.cookies.update(cookies)

    csrf_response = session.get(PORTAL_CSRF_URL)
    csrf_soup = BeautifulSoup(csrf_response.content, "lxml")
    csrf_token = csrf_soup.find("input", {"name": "_token"})["value"]
    
    headers = {
        "User-Agent": "Mozilla/5.0",
        "X-Csrf-Token": csrf_token,
        "X-Requested-With": "XMLHttpRequest",
    }
    
    semesters = [1, 2, 3]
    total_score = 0
    total_credits = 0
    results = {}
    
    for semester in semesters:
        response = session.post(PORTAL_GRADES_URL, data={"semester": semester}, headers=headers)
        data = response.json()
        
        sem_score = 0
        sem_total_credits = 0
        subjects = []
        
        for item in data["data"]:
            subject_name = item["subject_name"]
            grade_letter = item["grade_letter"]
            
            if subject_name in credits_mapper and grade_letter in letter_mapper:
                if grade_letter == "U":
                    continue
                sem_score += letter_mapper[grade_letter] * credits_mapper[subject_name]
                sem_total_credits += credits_mapper[subject_name]
            
            subjects.append({
                "subject_name": subject_name,
                "subject_code": item["subject_code"],
                "grade_letter": grade_letter,
                "result": item["result"],
            })
        
        results[f"Semester {semester}"] = {
            "GPA": round(sem_score / sem_total_credits, 3) if sem_total_credits else 0,
        }
        total_score += sem_score
        total_credits += sem_total_credits
    
    cgpa = round(total_score / total_credits, 3) if total_credits else 0
    return jsonify({"CGPA": cgpa, "grades": results})

if __name__ == "__main__":
    app.run(debug=True)
