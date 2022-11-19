import binascii
import math
import random
import requests as res
import secrets
import time
from base64 import urlsafe_b64encode as b64e, urlsafe_b64decode as b64d
from time import strftime, localtime
import re
import ibm_db
import sendgrid
from clarifai_grpc.channel.clarifai_channel import ClarifaiChannel
from clarifai_grpc.grpc.api import resources_pb2, service_pb2, service_pb2_grpc
from clarifai_grpc.grpc.api.status import status_code_pb2
from cryptography.fernet import InvalidToken
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from flask import Flask, render_template, request, session, redirect
from sendgrid import SendGridAPIClient
from markupsafe import escape
from sendgrid.helpers.mail import Mail, Email, To, Content

# clarifai
YOUR_CLARIFAI_API_KEY = "xxxxxxx"
YOUR_APPLICATION_ID = "Nutrition_assistant1"
channel = ClarifaiChannel.get_json_channel()
stub = service_pb2_grpc.V2Stub(channel)
metadata = (("authorization", f"Key {YOUR_CLARIFAI_API_KEY}"),)

# sendgrid
SENDGRID_API_KEY = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# rapid API
url = "https://spoonacular-recipe-food-nutrition-v1.p.rapidapi.com/recipes/parseIngredients"
querystring = {"includeNutrition": "true"}
headers = {"content-type": "application/x-www-form-urlencoded",
           "X-RapidAPI-Key": "xxxx",
           "X-RapidAPI-Host": "xxxxx"
           }

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'jfif'}

KEY = "24803877913464067088963527689231"

conn = ibm_db.connect("DATABASE=bludb;HOSTNAME=19af6446-6171-4641-8aba-9dcff8e1b6ff.c1ogj3sd0tgtu0lqde00.databases.appdomain.cloud;PORT=30699;SECURITY=SSL;SSLServerCertificate=DigiCertGlobalRootCA.crt;UID=yyx69722;PWD=2YqarEmzriL08SP7",'','')

print(conn)

app = Flask(__name__)

app.secret_key = "\xfd{H\xe5<\x95\xf9\xe3\x96.5\xd1\x01O<!\xd5\xa2\xa0\x9fR"

@app.route('/')
def home():
    return render_template('intro.html')

def send_confirmation_mail(user, email):
    message = email(
        from_email = "nutritionapplication1@gmail.com",
        to_emails = email,
        subject = "Congrats! Your Account was created Successfully",
        html_content = f"<strong>Congrats {user}!</strong><br>Account Created with username {email}"
    )

    SENDGRID_API_KEY='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'
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        print(response.status_code,response.body)
        #print(response.body)
        #print(response.headers)
    except Exception as e:
        print(f"Some error in sendgrid, {e}")

    

@app.route('/login', methods =['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        sql = "SELECT * FROM Database WHERE username =? And password =?"
        stmt = ibm_db.prepare(conn, sql)
        ibm_db.bind_param(stmt,1,username)
        ibm_db.bind_param(stmt,2,password)
        ibm_db.execute(stmt)
        account = ibm_db.fetch_assoc(stmt)
        print(account)
        if account:
            session['loggedin'] = True
            #session['id'] = account['id']
            session['username'] = username
            msg = 'Logged in successfully !'
            return render_template('mainpage.html', msg = msg)
        else:
            msg = 'Incorrect username / password !'
    return render_template('login.html', msg = msg)
        
@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    return render_template('login.html')       
        
         

@app.route('/register', methods =['GET', 'POST'])
def register():
    msg = ''
   
  
    if request.method=='POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        print(username ,password)
        sql = "SELECT * FROM Database WHERE username =? AND password=?"
        stmt = ibm_db.prepare(conn, sql) 
        ibm_db.bind_param(stmt,1,username)
        ibm_db.bind_param(stmt,2,password)
        ibm_db.execute(stmt)
        account = ibm_db.fetch_assoc(stmt)
        print(account)
        
        if account:
            msg = 'Account already exists !'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address !'
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'name must contain only characters and numbers !'
        elif not username or not password or not email:
            msg = 'Please fill out the form !'
        else:
          insert_sql = "INSERT INTO Database VALUES (?,?,?)"
          prep_stmt = ibm_db.prepare(conn, insert_sql)
          ibm_db.bind_param(prep_stmt, 1, username)
          ibm_db.bind_param(prep_stmt, 2, email)
          ibm_db.bind_param(prep_stmt, 3, password)
          ibm_db.execute(prep_stmt)
          msg = 'You have successfully registered !'
    elif request.method == 'POST':
        msg = 'Please fill out the form !'
    return render_template('register.html', msg = msg)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/dashboard', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'logout' in request.form:
            session["loggedIn"] = None
            session['name'] = None
            session['email'] = None
            return render_template('intro.html', error="Successfully created")
        if 'file' not in request.files:
            # flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.

        if file.filename == '':
            return render_template('dashboard.html', msg="File not found", history=history)
        baseimage = file.read()
        if file and allowed_file(file.filename):
            requests = service_pb2.PostModelOutputsRequest(
                # This is the model ID of a publicly available General model. You may use any other public or custom
                # model ID.
                # model_id="general-image-recognition"
                # model_id="food-item-recognition"
                model_id="food-item-recognition",
                user_app_id=resources_pb2.UserAppIDSet(app_id=YOUR_APPLICATION_ID),
                inputs=[
                    resources_pb2.Input(
                        data=resources_pb2.Data(image=resources_pb2.Image(base64=baseimage))
                    )
                ],
            )
            response = stub.PostModelOutputs(requests, metadata=metadata)

            if response.status.code != status_code_pb2.SUCCESS:
                return render_template('dashboard.html', msg=f'Failed {response.status}', history=history)

            calcium = 0
            vitaminb5 = 0
            protein = 0
            vitamind = 0
            vitamina = 0
            vitaminb2 = 0
            carbohydrates = 0
            fiber = 0
            fat = 0
            sodium = 0
            vitaminc = 0
            calories = 0
            vitaminb1 = 0
            folicacid = 0
            sugar = 0
            vitamink = 0
            cholesterol = 0
            potassium = 0
            monounsaturatedfat = 0
            polyunsaturatedfat = 0
            saturatedfat = 0
            totalfat = 0

            calciumu = 'g'
            vitaminb5u = 'g'
            proteinu = 'g'
            vitamindu = 'g'
            vitaminau = 'g'
            vitaminb2u = 'g'
            carbohydratesu = 'g'
            fiberu = 'g'
            fatu = 'g'
            sodiumu = 'g'
            vitamincu = 'g'
            caloriesu = 'cal'
            vitaminb1u = 'g'
            folicacidu = 'g'
            sugaru = 'g'
            vitaminku = 'g'
            cholesterolu = 'g'
            potassiumu = 'g'
            monounsaturatedfatu = 'g'
            polyunsaturatedfatu = 'g'
            saturatedfatu = 'g'
            totalfatu = 'g'

            for concept in response.outputs[0].data.concepts:
                print("%12s: %.2f" % (concept.name, concept.value))
                if concept.value > 0.5:
                    payload = "ingredientList=" + concept.name + "&servings=1"
                    response1 = res.request("POST", url, data=payload, headers=headers, params=querystring)
                    data = response1.json()
                    for i in range(0, 1):
                        nutri_array = data[i]
                        nutri_dic = nutri_array['nutrition']
                        nutri = nutri_dic['nutrients']

                        for z in range(0, len(nutri)):
                            temp = nutri[z]
                            if temp['name'] == 'Calcium':
                                calcium += temp['amount']
                                calciumu = temp['unit']
                            elif temp['name'] == 'Vitamin B5':
                                vitaminb5 += temp['amount']
                                vitaminb5u = temp['unit']
                            elif temp['name'] == 'Protein':
                                protein += temp['amount']
                                proteinu = temp['unit']
                            elif temp['name'] == 'Vitamin D':
                                vitamind += temp['amount']
                                vitamindu = temp['unit']
                            elif temp['name'] == 'Vitamin A':
                                vitamina += temp['amount']
                                vitaminau = temp['unit']
                            elif temp['name'] == 'Vitamin B2':
                                vitaminb2 += temp['amount']
                                vitaminb2u = temp['unit']
                            elif temp['name'] == 'Carbohydrates':
                                carbohydrates += temp['amount']
                                carbohydratesu = temp['unit']
                            elif temp['name'] == 'Fiber':
                                fiber += temp['amount']
                                fiberu = temp['unit']
                            elif temp['name'] == 'Vitamin C':
                                vitaminc += temp['amount']
                                vitamincu = temp['unit']
                            elif temp['name'] == 'Calories':
                                calories += temp['amount']
                                caloriesu = 'cal'
                            elif temp['name'] == 'Vitamin B1':
                                vitaminb1 += temp['amount']
                                vitaminb1u = temp['unit']
                            elif temp['name'] == 'Folic Acid':
                                folicacid += temp['amount']
                                folicacidu = temp['unit']
                            elif temp['name'] == 'Sugar':
                                sugar += temp['amount']
                                sugaru = temp['unit']
                            elif temp['name'] == 'Vitamin K':
                                vitamink += temp['amount']
                                vitaminku = temp['unit']
                            elif temp['name'] == 'Cholesterol':
                                cholesterol += temp['amount']
                                cholesterolu = temp['unit']
                            elif temp['name'] == 'Mono Unsaturated Fat':
                                monounsaturatedfat += temp['amount']
                                monounsaturatedfatu = temp['unit']
                            elif temp['name'] == 'Poly Unsaturated Fat':
                                polyunsaturatedfat += temp['amount']
                                polyunsaturatedfatu = temp['unit']
                            elif temp['name'] == 'Saturated Fat':
                                saturatedfat += temp['amount']
                                saturatedfatu = temp['unit']
                            elif temp['name'] == 'Fat':
                                fat += temp['amount']
                                fatu = temp['unit']
                            elif temp['name'] == 'Sodium':
                                sodium += temp['amount']
                                sodiumu = temp['unit']
                            elif temp['name'] == 'Potassium':
                                potassium += temp['amount']
                                potassiumu = temp['unit']
                            else:
                                pass

            totalfat += saturatedfat + polyunsaturatedfat + monounsaturatedfat
            data = [calories, totalfat, saturatedfat, polyunsaturatedfat, monounsaturatedfat, cholesterol, sodium,
                    potassium, sugar, protein, carbohydrates, vitamina, vitaminc, vitamind, vitaminb5, calcium]
            unit = [caloriesu, "g", saturatedfatu, polyunsaturatedfatu, monounsaturatedfatu, cholesterolu, sodiumu,
                    potassiumu, sugaru, proteinu, carbohydratesu, vitaminau, vitamincu, vitamindu, vitaminb5u, calciumu]

            to_string = "{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{}".format(data[0], data[1], data[2], data[3],
                                                                                 data[4],
                                                                                 data[5], data[6], data[7], data[8],
                                                                                 data[9],
                                                                                 data[10], data[11], data[12], data[13],
                                                                                 data[14], data[15])
            current_time = strftime("%a, %d %b %Y %H:%M:%S", localtime())

            sql = "SELECT * FROM PERSON"
            stmt = ibm_db.prepare(conn, sql)
            # ibm_db.bind_param(stmt, 1, session['email'])
            ibm_db.execute(stmt)
            # account = ibm_db.fetch_assoc(stmt)

            try:
                # insert_sql = "INSERT INTO PERSON VALUES (?,?,?,?)"
                # prep_stmt = ibm_db.prepare(conn, insert_sql)
                # ibm_db.bind_param(prep_stmt, 1, session['username'])
                # # ibm_db.bind_param(prep_stmt, 2, session['email'])
                # ibm_db.bind_param(prep_stmt, 3, to_string)
                # ibm_db.bind_param(prep_stmt, 4, current_time)
                # print(prep_stmt)
                # ibm_db.execute(prep_stmt)
                return render_template('dashboard.html', data=data, unit=unit)
            except ibm_db.stmt_error:
                print(ibm_db.stmt_error())
                return render_template('dashboard.html', msg='Something wnt wrong', user=session['name'],
                                       email=session['email'], data=data, history=history)

        return render_template('dashboard.html', history=history)
    if session['username'] is None:
        return render_template('intro.html')
    return render_template('dashboard.html')


if __name__ == '__main__':
    app.debug = True
    app.run()
