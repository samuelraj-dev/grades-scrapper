from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
from flask_cors import CORS

app = Flask(__name__)
app.secret_key = "123"

CORS(app, supports_credentials=True, origins=["http://localhost:5173", "https://localhost:4433", "https://grades-scrapper-fe.vercel.app"])

PORTAL_LOGIN_URL = "https://ims.ritchennai.edu.in/login"
PORTAL_GRADES_URL = "https://ims.ritchennai.edu.in/admin/grade/student/mark/get_marks"
PORTAL_CSRF_URL = "https://ims.ritchennai.edu.in/admin/grade/student/mark/report"

LOGIN_FAILURE_MSG = "These credentials do not match our records."

credits_mapper = {
    # CSBS 2023 - 2027
    "CY23111": 3,
    "CY23121": 1,
    "GE23111": 3,
    "GE23112": 0,
    "GE23121": 1,
    "GE23122": 1,
    "GE23131": 4,
    "HS23111": 3,
    "MA23111": 4,
    "AD23211": 3,
    "AD23221": 1,
    "GE23211": 3,
    "GE23213": 0,
    "GE23221": 1,
    "HS23211": 2,
    "MA23211": 4,
    "PH23211": 3,
    "PH23221": 1,
    "CB23311": 4,
    "CS23312": 3,
    "CS23314": 3,
    "EC23331": 4,
    "MA23311": 3,
    "CS23322": 1,
    "CS23324": 1,
    "CB23IC1": 1,

    # CSBS 2022 - 2026
    "BS3171": 2,
    "CY3151": 3,
    "GE3151": 3,
    "GE3152": 1,
    "GE3171": 2,
    "GE3172": 1,
    "HS3152": 3,
    "MA3151": 4,
    "PH3151": 3,
    "AD3251": 3,
    "AD3271": 2,
    "BE3251": 3,
    "GE3251": 4,
    "GE3252":1,
    "GE3271":2,
    "GE3272":2,
    "HS3252":2,
    "MA3251":4,
    "PH3256":3,
    "AD3351":4,
    "AD3491":3,
    "CS3351":4,
    "CS3381":1.5,
    "CS3391":3,
    "CW3301":3,
    "CW3311":1.5,
    "GE3361":1,
    "MA3354":4,

    "AD3461":2,
    "AL3451":3,
    "AL3452":4,
    "CS3481":1.5,
    "CS3492":3,
    "CW3401":3,
    "CW3411":1.5,
    "GE3451":2,
    "MA3391":4,
    "CCD332":3,
    "CCS346":3,
    "CS3691":4,
    "CW3501":3,
    "CW3551":3,
    "CW3511":2,
    "MX3084": 0,


    # AIML 2023-2027
    "AL23311": 3,
    "CS23411": 3,
    "AL23321": 1,
    "CS23421": 1,
}

letter_mapper = {"O": 10, "A+": 9, "A": 8, "B+": 7, "B": 6, "C": 5, "U": 0}

# get
# post
# put, patch,
# delete
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
    
    semesters = [1, 2, 3, 4, 5]
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
            subject_name = item["subject_name"].strip()
            subject_code = item["subject_code"].strip()
            grade_letter = item["grade_letter"].strip()
            
            if subject_code in credits_mapper and grade_letter in letter_mapper:
                if grade_letter == "U":
                    continue
                sem_score += letter_mapper[grade_letter] * credits_mapper[subject_code]
                sem_total_credits += credits_mapper[subject_code]
            else:
                print(item)
                return jsonify({"error": "Your department isn't supported yet. Please try later."}), 500
            
            subjects.append({
                "subject_name": subject_name,
                "subject_code": subject_code,
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
