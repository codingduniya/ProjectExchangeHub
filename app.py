from flask import Flask, render_template, request, redirect, url_for, make_response, session
from flask_bcrypt import Bcrypt
from pymongo import MongoClient
import gridfs
from dotenv import load_dotenv
import os
import certifi
from flask_mail import Mail, Message
import pyotp

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

client = MongoClient(os.getenv('MONGO_CONNECT'), tlsCAFile=certifi.where())
project_db = client['project_db']
user_db = client['myfirstdb']

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

        # Store temporary data in session
        session['temp_user'] = {
            'role': 'company',
            'name': name,
            'mobile': mobile,
            'mail': mail,
            'password': hashed_pass
        }

        # Generate OTP
        otp_secret = pyotp.random_base32()
        session['otp_secret'] = otp_secret
        totp = pyotp.TOTP(otp_secret, interval=300)  # 5 minutes
        otp = totp.now()

        # Send OTP Email
        msg = Message("Your OTP for MooovieRec", sender='didacount1@gmail.com', recipients=[mail])
        msg.body = f"Hello {name},\n\nYour OTP is {otp}. Please enter this to verify your account.\n\nThank you for using MooovieRec."
        email.send(msg)

        return redirect(url_for('verify_otp'))

    return render_template('sign-in_for_company.html')


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

        # Store temporary data in session
        session['temp_user'] = {
            'role': 'student',
            'name': name,
            'mobile': mobile,
            'mail': mail,
            'password': hashed_pass
        }

        # Generate OTP
        otp_secret = pyotp.random_base32()
        session['otp_secret'] = otp_secret
        totp = pyotp.TOTP(otp_secret, interval=300)  # 5 minutes
        otp = totp.now()

        # Send OTP Email
        msg = Message("Your OTP for MooovieRec", sender='didacount1@gmail.com', recipients=[mail])
        msg.body = f"Hello {name},\n\nYour OTP is {otp}. Please enter this to verify your account.\n\nThank you for using MooovieRec."
        email.send(msg)

        return redirect(url_for('verify_otp'))

    return render_template('sign-in_for_students.html')


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

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if request.method == 'POST':
        user_otp = request.form.get('otp')
        otp_secret = session.get('otp_secret')
        temp_user = session.get('temp_user')

        if not temp_user or not otp_secret:
            return redirect(url_for('home'))

        totp = pyotp.TOTP(otp_secret, interval=300)
        if totp.verify(user_otp):
            # Save to DB
            if temp_user['role'] == 'company':
                user_db.Companys.insert_one({
                    'Name': temp_user['name'],
                    'Mobile': temp_user['mobile'],
                    'Mail': temp_user['mail'],
                    'Password': temp_user['password']
                })
                response =  make_response(redirect(url_for('upload')))
            else:
                user_db.Students.insert_one({
                    'Name': temp_user['name'],
                    'Mobile': temp_user['mobile'],
                    'Mail': temp_user['mail'],
                    'Password': temp_user['password']
                })
                response = make_response(redirect(url_for('studentdash')))

            # Set Cookies
            response.set_cookie('name', temp_user['name'], max_age=60*60*24*30, path='/')
            response.set_cookie('Mail', temp_user['mail'], max_age=60*60*24*30, path='/')

            # Clear session
            session.pop('temp_user', None)
            session.pop('otp_secret', None)
            return response
        else:
            return render_template('verify_otp.html', message="Invalid OTP. Please try again.")

    return render_template('verify_otp.html')




if __name__ == '__main__':
    app.run(debug=True)
