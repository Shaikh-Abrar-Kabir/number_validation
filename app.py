import time

from flask import Flask, render_template, request, redirect, url_for, send_file, render_template_string, flash
from datetime import datetime
from flask_socketio import SocketIO
from geopy.geocoders import Nominatim
import folium,pandas as pd, json, requests, os, bcrypt, calendar
import math
app = Flask(__name__)

socketio = SocketIO(app)
CREDENTIALS_FILE = "admin_credentials.json"
API_KEY_FILE = "api_key.json"
# NUMVERIFY_API_KEY = '98d4844e2026941c35f9703cc7590b92'

def verify_number(phone_number,NUMVERIFY_API_KEY):
    params = {'access_key': NUMVERIFY_API_KEY, 'number': phone_number, 'format': 1}
    response = requests.get('http://apilayer.net/api/validate', params=params)
    return response.json()


@app.route('/')

def index():

    return render_template('authenticate.html')


@app.route('/', methods=['POST'])

def authenticate():
    month_dict = {i: calendar.month_name[i] for i in range(1, 13)}
    with open("present.json", "r") as f:
        count_present = json.load(f)
    with open("past.json", "r") as f:
        count_past = json.load(f)
    count_data = {"ps" : f"Last Month ( {month_dict[int(list(count_past.keys())[0])]} ) Verification = {count_past[list(count_past.keys())[0]]}",
                  "pr" : f"This Month ( {month_dict[int(list(count_present.keys())[0])]} ) Verification = {count_present[list(count_present.keys())[0]]}"
                  }
    input_email = request.form.get('email')
    input_password = request.form.get('pass')
    print(input_email,input_password)
    def check_password(password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(password.encode(), hashed_password.encode())

    with open("creds.json", "r") as f:
        stored_passwords = json.load(f)

    if check_password(input_password, stored_passwords["1"]) and check_password(input_email, stored_passwords["2"]):
        return render_template('index.html',count_data = count_data)
    else:
        return "Incorrect password or email"



@app.route('/change', methods=['POST'])

def change_cred():

    old_email = request.form.get('oldemail')
    old_password = request.form.get('oldpass')
    new_email = request.form.get('newemail')
    new_password = request.form.get('newpass')
    print(old_email,old_password)
    def check_password(password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(password.encode(), hashed_password.encode())

    with open("creds.json", "r") as f:
        stored_passwords = json.load(f)

    if check_password(old_password, stored_passwords["1"]) and check_password(old_email, stored_passwords["2"]):
        hashed_password = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        hashed_email = bcrypt.hashpw(new_email.encode(), bcrypt.gensalt()).decode()
        creds = {
            "1": hashed_password,
            "2": hashed_email
        }
        with open("creds.json", "w") as f:
            json.dump(creds, f, indent=4)
        return render_template('authenticate.html')
    else:
        return "Incorrect old password or old email"



@app.route('/validate', methods=['POST'])

def validate():

    phone_number = request.form.get('phone_number')

    NUMVERIFY_API_KEY = request.form.get('api_key')
    params = {'access_key': NUMVERIFY_API_KEY, 'number': phone_number, 'format': 1}

    response = requests.get('http://apilayer.net/api/validate', params=params)

    result = response.json()
    current_month = datetime.now().month
    with open("present.json", "r") as f:
        count_present = json.load(f)

    if current_month == int(list(count_present.keys())[0]):
        count_present[list(count_present.keys())[0]] += 1
        with open("present.json", "w") as f:
            json.dump(count_present, f, indent=4)

    else:
        with open("past.json", "w") as f:
            json.dump(count_present, f, indent=4)
        count_present_2 = {str(current_month): 0}
        count_present_2[str(current_month)] = count_present_2[str(current_month)] + 1
        with open("present.json", "w") as f:
            json.dump(count_present_2, f, indent=4)
    return render_template('result.html', result=result)

@app.route('/bulk_validate', methods=['GET', 'POST'])

def bulk_verify():

    if request.method == 'POST':

        # Handle file upload

        file = request.files['file']

        # Read Excel file using pandas

        if file and (file.filename.endswith('.xls') or file.filename.endswith('.xlsx') or file.filename.endswith('.csv')):
            if file.filename.endswith('.xlsx'):
                df = pd.read_excel(file, engine='openpyxl')  # Use openpyxl for .xlsx files
            elif file.filename.endswith('.xls'):
                df = pd.read_excel(file)  # Default engine for .xls files
            elif file.filename.endswith('.csv'):
                df = pd.read_csv(file)
            # df = pd.read_excel(file, engine='openpyxl')  # Specify the engine for .xlsx files
            current_month = datetime.now().month
            with open("present.json", "r") as f:
                count_present = json.load(f)

            if current_month == int(list(count_present.keys())[0]):
                count_present[list(count_present.keys())[0]] += len(df)
                with open("present.json", "w") as f:
                    json.dump(count_present, f, indent=4)

            else:
                with open("past.json", "w") as f:
                    json.dump(count_present, f, indent=4)
                count_present_2 = {str(current_month): 0}
                count_present_2[str(current_month)] = count_present_2[str(current_month)] + len(df)
                with open("present.json", "w") as f:
                    json.dump(count_present_2, f, indent=4)
            # Perform Numverify validation for each number
            # print(df)
            validation_results = {}
            validation_data = []
            NUMVERIFY_API_KEY = request.form.get('api_key')
            for index, row in df.iterrows():

                # raw_number = str(row['Mobile Number'])
                if math.isnan(row['Mobile Number']):
                    raw_number = ""
                else:
                    raw_number = str(int(row['Mobile Number']))

                # Perform Numverify validation directly on the raw phone number

                result = verify_number(raw_number,NUMVERIFY_API_KEY)
                rk = list(result.keys())
                validation_results[raw_number] = result
                print(list(result.keys())[0])
                validation_data.append([
                    raw_number,
                    "✔️Valid" if result and result[rk[0]] else "❌Invalid" ,
                    result[rk[1]] if result and result[rk[0]] else "N/A",
                    result[rk[2]] if result and result[rk[0]] else "N/A",
                    result[rk[3]] if result and result[rk[0]] else "N/A",
                    result[rk[4]]if result and result[rk[0]] else "N/A",
                    result[rk[5]] if result and result[rk[0]] else "N/A" ,
                    result[rk[6]] if result and result[rk[0]] else "N/A"
                ])
                time.sleep(1)
            result_df = pd.DataFrame(validation_data, columns=[
                "Phone Number", "Validation Result", "Local Format",
                "Intl. Format", "Country", "Location", "Carrier", "Line Type"
            ])
            file_path = "validation_results.xlsx"
            with pd.ExcelWriter(file_path, engine="xlsxwriter") as writer:
                result_df.to_excel(writer, index=False, sheet_name="Validation Results")

            return render_template('bulk.html', results=validation_results)

    return render_template('index.html')

@app.route("/api_key", methods=['GET', 'POST'])
def api_save():
    api_dict = {
        "api_key" : request.form.get('api_key')
    }
    with open("data.json", "w") as file:
        json.dump(api_dict, file, indent=4)
    return render_template('index.html')



@app.route("/download")
def download_file():
    file_path = "validation_results.xlsx"
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return "File not found", 404




@socketio.on('connect')

def handle_connect():

    print('Client connected')

@socketio.on('disconnect')

def handle_disconnect():

    print('Client disconnected')

if __name__ == '__main__':

    socketio.run(app, debug=True)