from flask import Flask, render_template, request, redirect, url_for, send_file, make_response
from bson.objectid import ObjectId
from flask_bcrypt import Bcrypt
from pymongo import MongoClient
import gridfs
from dotenv import load_dotenv
import os
import io
import certifi
from  flask_mail import *
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'default_secret_key')

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'didacount1@gmail.com'
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASS')

email = Mail(app)

client = MongoClient(os.getenv('MONGO_CONNECT'),tlsCAFile=certifi.where())
project_db = client['project_db']

#connecting the cloud server
client2 = MongoClient(os.getenv('MONGO_CONNECT'),tlsCAFile=certifi.where())
user_db = client2['myfirstdb']


fs = gridfs.GridFS(project_db)
bcrypt = Bcrypt(app)

@app.route('/')
def home():
    
    return render_template('index.html')

@app.route('/sign-in_for_company', methods=['GET', 'POST'])
def signupforcompany():
    if request.method == 'POST':
        name = request.form.get('username')
        mobile = request.form.get('mobnumber')
        mail = request.form.get('usermail')
        password = request.form.get('userpassword')
        repass = request.form.get('Repassword')

        if user_db.Companys.find_one({'Mail': mail}):
            return render_template('login_for_companys.html', message="Email already registered, please login.")

        if password != repass:
            return render_template('sign-in_for_company.html', message="Passwords do not match.")

        hashed_pass = bcrypt.generate_password_hash(password).decode('utf-8')
        user_db.Companys.insert_one({
            'Name': name,
            'Mobile': mobile,
            'Mail': mail,
            'Password': hashed_pass
        })

        response = make_response(redirect(url_for('upload')))
        response.set_cookie('name', name, max_age=60*60*24*30, path='/')
        response.set_cookie('Mail', mail, max_age=60*60*24*30, path='/')
        msg = Message("Welcome To MooovieRec" , sender='didacount1@gmail.com', recipients=[mail])
        msg.body = "Hello "+ name + " thank you for registering in the MooovieRec\nThank you for using this website. \nYour password is "+password+" \nplease do not share the password with any one"
        email.send(msg)
        return response

    return render_template('sign-in_for_company.html')

@app.route('/login_for_companys', methods=['GET', 'POST'])
def login_for_companys():
    if request.method == 'POST':
        mail = request.form.get('Mail')
        password = request.form.get('Password')

        print(f"Mail entered: {mail}")
        user = user_db.Companys.find_one({'Mail': mail})

        if user:
            print("User Found:", user)
            if bcrypt.check_password_hash(user['Password'], password):
                print("Password match")
                response = make_response(redirect(url_for('upload')))
                response.set_cookie('name', user['Name'], max_age=60*60*24*30, path='/')
                response.set_cookie('Mail', mail, max_age=60*60*24*30, path='/')
                return response
            else:
                print("Password mismatch")
        else:
            print("User not found in DB")

        return render_template('login_for_companys.html', message="Invalid Credentials")

    return render_template('login_for_companys.html')


@app.route('/sign-in_for_students', methods=['GET', 'POST'])
def signupforstudents():
    if request.method == 'POST':
        name = request.form.get('username')
        mobile = request.form.get('mobnumber')
        mail = request.form.get('usermail')
        password = request.form.get('userpassword')
        repass = request.form.get('Repassword')

        if user_db.Students.find_one({'Mail': mail}):
            return render_template('login_for_students.html', message="Email already registered, please login.")

        if password != repass:
            return render_template('sign-in_for_students.html', message="Passwords do not match.")

        hashed_pass = bcrypt.generate_password_hash(password).decode('utf-8')
        user_db.Students.insert_one({
            'Name': name,
            'Mobile': mobile,
            'Mail': mail,
            'Password': hashed_pass
        })

        response =make_response(redirect(url_for('studentdash')))
        response.set_cookie('name', name, max_age=60*60*24*30, path='/')
        response.set_cookie('Mail', mail, max_age=60*60*24*30, path='/')
        msg = Message("Welcome To MooovieRec" , sender='didacount1@gmail.com', recipients=[mail])
        msg.body = "Hello "+ name + " thank you for registering in the MooovieRec\nThank you for using this website. \nYour password is "+password+" \nplease do not share the password with any one"
        email.send(msg)
        return response

    return render_template('sign-in_for_students.html')

@app.route('/login_for_students', methods=['GET', 'POST'])
def loginforstudents():
    if request.method == 'POST':
        mail = request.form.get('Mail')
        password = request.form.get('Password')

        user = user_db.Students.find_one({'Mail': mail})

        if user and bcrypt.check_password_hash(user['Password'], password):
            response = make_response(redirect(url_for('studentdash')))
            response.set_cookie('name', user['Name'], max_age=60*60*24*30, path='/')
            response.set_cookie('Mail', mail, max_age=60*60*24*30, path='/')
            return response

        return render_template('login_for_students.html', message="Invalid Credentials")

    return render_template('login_for_students.html')

@app.route('/company-dashboard.html')
def companydash():
    name = request.cookies.get('name')
    mail = request.cookies.get('Mail')
    uploaded_projects = list(project_db.projects.find({'company': mail}))
    return render_template('company-dashboard.html', name=name, projects=uploaded_projects)

@app.route('/student-dashboard.html')
def studentdash():
    return render_template('student-dashboard.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        company = request.cookies.get('Mail')
        language = request.form.get('language')
        dataset_link = request.form.get('dataset_link')
        pdf = request.files.get('pdf')

        if pdf:
            pdf_id = fs.put(pdf, filename=pdf.filename)
            project_db.projects.insert_one({
                'title': title,
                'description': description,
                'company': company,
                'language': language,
                'dataset_link': dataset_link,
                'pdf_id': pdf_id
            })

        return redirect(url_for('upload'))

    mail = request.cookies.get('Mail')
    uploaded_projects = list(project_db.projects.find({'company': mail}))
    return render_template('upload.html', uploaded_projects=uploaded_projects)

@app.route('/projects/<language>')
def projects(language):
    projects = list(project_db.projects.find({'language': language.capitalize()}))
    return render_template('project-detail.html', projects=projects, language=language)

@app.route('/file/<file_id>')
def get_file(file_id):
    try:
        file = fs.get(ObjectId(file_id))
        return send_file(io.BytesIO(file.read()), download_name=file.filename, as_attachment=True)
    except:
        return "File not found", 404

@app.route('/file_view/<file_id>')
def get_view(file_id):
    try:
        file = fs.get(ObjectId(file_id))
        return send_file(io.BytesIO(file.read()), mimetype='application/pdf', as_attachment=False, download_name=file.filename)
    except:
        return "File not found", 404

if __name__ == '__main__':
    app.run(debug=True)
