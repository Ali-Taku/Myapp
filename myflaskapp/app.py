from flask import Flask, render_template, flash, redirect, url_for, session, request, logging, jsonify, make_response
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps
import csv
import io

app = Flask(__name__)

# Config MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '12345'
app.config['MYSQL_DB'] = 'myflaskapp'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
# init MYSQL
mysql = MySQL(app)


# Index
@app.route('/')
def index():
    return render_template('home.html')


# About
@app.route('/about')
def about():
    return render_template('about.html')


# Students
@app.route('/students')
def students():
    # Create cursor
    cur = mysql.connection.cursor()

    # Get students
    result = cur.execute("SELECT * FROM students")

    students = cur.fetchall()

    if result > 0:
        return render_template('students.html', students=students)
    else:
        msg = 'No Students Found'
        return render_template('students.html', msg=msg)
    # Close connection
    cur.close()


#Single Student
@app.route('/student/<string:id>/')
def student(id):
    # Create cursor
    cur = mysql.connection.cursor()

    # Get Student
    result = cur.execute("SELECT * FROM students WHERE id = %s", [id])

    student = cur.fetchone()

    return render_template('student.html', student=student)


# Register Form Class
class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=50)])
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField('Confirm Password')


# User Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        # Create cursor
        cur = mysql.connection.cursor()

        # Execute query
        cur.execute("INSERT INTO users(name, email, username, password) VALUES(%s, %s, %s, %s)", (name, email, username, password))

        # Commit to DB
        mysql.connection.commit()

        # Close connection
        cur.close()

        flash('You are now registered and can log in', 'success')

        return redirect(url_for('login'))
    return render_template('register.html', form=form)


# User login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get Form Fields
        username = request.form['username']
        password_candidate = request.form['password']

        # Create cursor
        cur = mysql.connection.cursor()

        # Get user by username
        result = cur.execute("SELECT * FROM users WHERE username = %s", [username])

        if result > 0:
            # Get stored hash
            data = cur.fetchone()
            password = data['password']

            # Compare Passwords
            if sha256_crypt.verify(password_candidate, password):
                # Passed
                session['logged_in'] = True
                session['username'] = username

                flash('You are now logged in', 'success')
                return redirect(url_for('dashboard'))
            else:
                error = 'Invalid login'
                return render_template('login.html', error=error)
            # Close connection
            cur.close()
        else:
            error = 'Username not found'
            return render_template('login.html', error=error)

    return render_template('login.html')

# Check if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('login'))
    return wrap

# Logout
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))

# Dashboard
@app.route('/dashboard')
@is_logged_in
def dashboard():
    # Create cursor
    cur = mysql.connection.cursor()

    # Get students
    result = cur.execute("SELECT * FROM students")

    students = cur.fetchall()

    if result > 0:
        return render_template('dashboard.html', students=students)
    else:
        msg = 'No Students Found'
        return render_template('dashboard.html', msg=msg)
    # Close connection
    cur.close()

# Enroll Form Class
class StudentForm(Form):
    studentname = StringField('Name of Student', [validators.Length(min=1, max=200)])
    coursename = StringField('Course', [validators.Length(min=1, max=200)])
    year = StringField('Year', [validators.Length(min=1, max=4)])

# Add Student
@app.route('/add_student', methods=['GET', 'POST'])
@is_logged_in
def add_student():
    form = StudentForm(request.form)
    if request.method == 'POST' and form.validate():
        studentname = form.studentname.data
        coursename = form.coursename.data
        year = form.year.data

        # Create Cursor
        cur = mysql.connection.cursor()

        # Execute
        cur.execute("INSERT INTO students(studentname, coursename, year) VALUES(%s, %s, %s)",(studentname, coursename, year))

        # Commit to DB
        mysql.connection.commit()

        #Close connection
        cur.close()

        flash('Student Enrolled', 'success')

        return redirect(url_for('dashboard'))

    return render_template('add_student.html', form=form)


# Edit Student
@app.route('/edit_student/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_student(id):
    # Create cursor
    cur = mysql.connection.cursor()

    # Get student by id
    result = cur.execute("SELECT * FROM students WHERE id = %s", [id])

    student = cur.fetchone()
    cur.close()
    # Get form
    form = StudentForm(request.form)

    # Populate student form fields
    form.studentname.data = student['studentname']
    form.coursename.data = student['coursename']
    form.year.data = student['year']

    if request.method == 'POST' and form.validate():
        studentname = request.form['studentname']
        coursename = request.form['coursename']
        year = request.form['year']

        # Create Cursor
        cur = mysql.connection.cursor()
        app.logger.info(studentname)
        # Execute
        cur.execute ("UPDATE students SET studentname=%s, coursename=%s, year=%s WHERE id=%s",(studentname, coursename, year, id))
        # Commit to DB
        mysql.connection.commit()

        #Close connection
        cur.close()

        flash('Details Updated', 'success')

        return redirect(url_for('dashboard'))

    return render_template('edit_student.html', form=form)

# Delete Student
@app.route('/delete_student/<string:id>', methods=['POST'])
@is_logged_in
def delete_student(id):
    # Create cursor
    cur = mysql.connection.cursor()

    # Execute
    cur.execute("DELETE FROM students WHERE id = %s", [id])

    # Commit to DB
    mysql.connection.commit()

    #Close connection
    cur.close()

    flash('Student Deleted', 'success')

    return redirect(url_for('dashboard'))


@app.route('/export_file', methods=['GET'])
@is_logged_in
def export_file():
    si = io.StringIO()
    cw = csv.writer(si)
    cur = mysql.connection.cursor()

    # Get students
    result = cur.execute("SELECT * FROM students")

    rows = cur.fetchall()
    cw.writerow([i[0] for i in cur.description])
    cw.writerows(rows)
    response = make_response(si.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=report.csv'
    response.headers["Content-type"] = "text/csv"
    return response

if __name__ == '__main__':
    app.secret_key='secret123'
    app.run(debug=True)
