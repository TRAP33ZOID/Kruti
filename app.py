from flask import Flask, request, jsonify, render_template, flash, redirect, url_for, session
from flask_mysqldb import MySQL
import fitz  # PyMuPDF
import openai
import os
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

import re
# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Waleed@1999'
app.config['MYSQL_DB'] = 'policy'
app.config['MYSQL_HOST'] = 'localhost'

mysql = MySQL()
mysql.init_app(app)

UPLOAD_FOLDER ='uploads'
ALLOWED_EXTENSIONS = {'txt'}  # allowed file types

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload size
app.secret_key = os.getenv('SECRET_KEY')  # Use environment variable for secret key
openai.api_key = os.getenv('OPENAI_API_KEY')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # Get form data
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        # Connect to the database
        cursor = mysql.connection.cursor()
        
        # Execute the query
        cursor.execute('INSERT INTO users (username, email, password) VALUES (%s, %s, %s)', (username, email, password))
        
        # Commit changes and close the connection
        mysql.connection.commit()
        cursor.close()

        # Redirect to the login page
        return redirect(url_for('login'))

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Retrieve form data
        username = request.form['username']
        password = request.form['password']

        # Connect to the database
        cursor = mysql.connection.cursor()
        
        # Execute query to find user by username
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        user = cursor.fetchone()
        
        # Close cursor
        cursor.close()
        print(f"Fetched User: {user}")  # Debug print

        # Check if user exists and password matches
        if user and user[3] == password:  
            # User is authenticated
            print("Login successful")  # Debug print
            session['logged_in'] = True
            session['username'] = user[1]  
            flash('You were successfully logged in', 'success')
            return redirect(url_for('index'))  # Redirect to the index page or dashboard
        else:
            # Invalid credentials
            print("Login failed")  # Debug print
            flash('Wrong login credentials', 'danger')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('index.html')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/summarize', methods=['POST'])
def summarize():
    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized"}), 401

    file = request.files['file']

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        # Check if file exists to avoid overwriting
        counter = 1
        while os.path.exists(save_path):
            name, extension = os.path.splitext(filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{name}_{counter}{extension}")
            counter += 1

        file.save(save_path)

        with open(save_path, 'r', encoding='utf-8') as file:
            extracted_text = file.read()

        summary = summarize_text(extracted_text)# Parse the summary output
        lines = summary.split('\n')
        primary_dwelling = lines[0].strip()
        construction_materials = lines[1].strip()
        physically_separated_structures = lines[2].strip()
        construction_materials_for_structures = lines[3].strip()

        # Insert into the database
        try:
            cursor = mysql.connection.cursor()
            cursor.execute('''
                INSERT INTO summarization_results (user_id, primary_dwelling, construction_materials, 
                                                physically_separated_structures, construction_materials_for_structures) 
                VALUES (%s, %s, %s, %s)
                ''', (primary_dwelling, construction_materials, 
                    physically_separated_structures, construction_materials_for_structures))
            mysql.connection.commit()
        except Exception as e:
            print("Error:", e)
            # Handle the error appropriately
        finally:
            cursor.close()

        # Rest of the existing code
        return jsonify({"summary": summary, "extractedText": extracted_text[:500]})

def summarize_text(text):
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        messages=[
            {"role": "system", "content": "You are a helpful assistant. Here is the document context, only answer from it: " + text},
            {"role": "user", "content": 
            '''
            1)only answer in 'yes' or 'no'. is primary dwelling covered? if the answer is yes don't type yes but only state the address without any filler words?
            2)do not write full sentences, only answer in 'yes' or 'no'. are construction materials covered?
            3)List the covered physically separated structures at the insured address separated by commas. do not write full sentences, only state the structures.
            4)do not write full sentences, only answer in 'yes' or 'no'. are Construction materials for use in physically separated structures covered?

            
            '''
            }
        ]
    )

    print("Total Tokens:", response.usage.total_tokens)
    return response.choices[0].message.content

if __name__ == '__main__':
    app.run(debug=True)