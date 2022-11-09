from turtle import st
from flask import Flask, render_template, request, redirect, url_for, session
from markupsafe import escape
import re
import ibm_db
conn = ibm_db.connect("DATABASE=bludb;HOSTNAME=19af6446-6171-4641-8aba-9dcff8e1b6ff.c1ogj3sd0tgtu0lqde00.databases.appdomain.cloud;PORT=30699;SECURITY=SSL;SSLServerCertificate=DigiCertGlobalRootCA.crt;UID=yyx69722;PWD=2YqarEmzriL08SP7",'','')
app = Flask(__name__)

app.secret_key = 'nut2345'
@app.route('/')
def home():
    return render_template('intro.html')
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
    return redirect(url_for('login'))       
        
         

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True,port=5000)

   
    