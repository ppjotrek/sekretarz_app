from flask import Flask, request, redirect, url_for, session, render_template, send_file, jsonify, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
from werkzeug.utils import secure_filename
from docxtpl import DocxTemplate
from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import os
import json

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.secret_key = 'supersecretkey'  # Ustaw klucz sesji
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Konfiguracja Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Konfiguracja SQLAlchemy
db = SQLAlchemy(app)

# Model użytkownika
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    phone_number = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
@login_required
def index():
    file_path = os.path.join('docx_templates', 'projects.json')
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            projects = json.load(file)
    else:
        projects = {}

    return render_template('index.html', projects=projects)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        phone = request.form['phone']
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already registered')
            return redirect(url_for('register'))
        hashed_password = generate_password_hash(password)
        new_user = User(name=name, email=email, password=hashed_password, phone_number=phone)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid email or password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/upload_and_submit', methods=['POST'])
@login_required
def upload_and_submit():
    if 'file' not in request.files:
        return 'No file part'
    file = request.files['file']
    if file.filename == '':
        return 'No selected file'
    if file and (file.filename.endswith('.xlsx') or file.filename.endswith('.xls') or file.filename.endswith('.csv')):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        if file.filename.endswith('.xlsx') or file.filename.endswith('.xls'):
            df = pd.read_excel(filepath)
        elif file.filename.endswith('.csv'):
            df = pd.read_csv(filepath)
        session['data'] = df.to_dict()  # Zapisz dane do sesji

    dropdown1 = request.form.get('project-dropdown')
    date_option = request.form.get('date_option')
    if date_option == 'single':
        date = request.form.get('date')
        session['additional_data'] = {
            'project-dropdown': dropdown1,
            'date': date
        }
    elif date_option == 'range':
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        session['additional_data'] = {
            'project-dropdown': dropdown1,
            'start_date': start_date,
            'end_date': end_date
        }
    return redirect(url_for('index'))

@app.route('/generate_docx')
@login_required
def generate_docx():
    if 'data' in session and 'additional_data' in session:
        data = session['data']
        additional_data = session['additional_data']
        combined_doc = Document()

        # Załaduj dane z projects.json
        with open(os.path.join('docx_templates', 'projects.json'), 'r', encoding='utf-8') as file:
            projects = json.load(file)

        project_name = additional_data['project-dropdown']
        project_info = projects.get(project_name, {})
        nazwa_projektu = project_info.get('nazwa', '')
        opis_projektu = project_info.get('opis', '')

        for count in range(len(data['Imię'])):
            # Pobierz dane z sesji
            imie_i_nazwisko = f"{data['Imię'][str(count)]} {data['Nazwisko'][str(count)]}"
            album = data['Numer indeksu'][str(count)]
            studenta_ki = "studenta" if data['Płeć'][str(count)] == 'Mężczyzna' else "studentki" if data['Płeć'][str(count)] == 'Kobieta' else "osoby studiującej na kierunku"
            kierunek = data['Kierunek'][str(count)]
            wydzial = data['Wydział'][str(count)]
            dniu_dniach = "dniu" if additional_data['date'] else "dniach"
            data_wystawienia = additional_data['date']
            daty = additional_data.get('start_date', '') + ' - ' + additional_data.get('end_date', '')
            sekretarz = current_user.name
            tel_sekretarz = current_user.phone_number
            mail_sekretarz = current_user.email

            # Sprawdź, czy wszystkie zmienne są ustawione
            missing_variables = []
            if not imie_i_nazwisko:
                missing_variables.append('imie_i_nazwisko')
            if not album:
                missing_variables.append('album')
            if not studenta_ki:
                missing_variables.append('studenta_ki')
            if not kierunek:
                missing_variables.append('kierunek')
            if not wydzial:
                missing_variables.append('wydzial')
            if not dniu_dniach:
                missing_variables.append('dniu_dniach')
            if not data_wystawienia:
                missing_variables.append('data')
            if not daty:
                missing_variables.append('daty')
            if not nazwa_projektu:
                missing_variables.append('nazwa_projektu')
            if not opis_projektu:
                missing_variables.append('opis_projektu')
            if not sekretarz:
                missing_variables.append('sekretarz')
            if not tel_sekretarz:
                missing_variables.append('tel_sekretarz')
            if not mail_sekretarz:
                missing_variables.append('mail_sekretarz')

            if missing_variables:
                flash(f'Missing variables: {", ".join(missing_variables)}', 'error')
                return redirect(url_for('index'))

            # Załaduj szablon dokumentu
            template = DocxTemplate(os.path.join("docx_templates", "template_v1.docx"))

            context = {
                'data': data_wystawienia,
                'imie_i_nazwisko': imie_i_nazwisko,
                'album': album,
                'studenta_ki': studenta_ki,
                'kierunek': kierunek,
                'wydzial': wydzial,
                'dniu_dniach': dniu_dniach,
                'data': data_wystawienia,
                'daty': daty,
                'nazwa_projektu': nazwa_projektu,
                'opis_projektu': opis_projektu,
                'sekretarz': sekretarz,
                'tel_sekretarz': tel_sekretarz,
                'mail_sekretarz': mail_sekretarz
            }
            template.render(context)
            
            # Zapisz tymczasowy dokument
            temp_doc_path = os.path.join(app.config['UPLOAD_FOLDER'], f'temp_{count}.docx')
            template.save(temp_doc_path)
            
            # Otwórz tymczasowy dokument i dodaj jego zawartość do głównego dokumentu
            temp_doc = Document(temp_doc_path)
            for element in temp_doc.element.body:
                combined_doc.element.body.append(element)
            
            # Dodaj nową sekcję, aby rozpocząć nową stronę
            if count < len(data['Imię']) - 1:
                page_break = OxmlElement('w:br')
                page_break.set(qn('w:type'), 'page')
                combined_doc.element.body.append(page_break)
        
        docs_name = additional_data['project-dropdown'] + '_combined.docx'
        docx_path = os.path.join(app.config['UPLOAD_FOLDER'], docs_name)
        combined_doc.save(docx_path)
        
        # Usuń tymczasowe pliki
        for count in range(len(data['Imię'])):
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], f'temp_{count}.docx'))
        
        return send_file(docx_path, as_attachment=True)
    return 'Arikitarakuma'

@app.route('/add_project', methods=['POST'])
@login_required
def add_project():
    data = request.get_json()
    project_name = data.get('name')
    project_description = data.get('description')

    if project_name and project_description:
        file_path = os.path.join('docx_templates', 'projects.json')
        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                projects = json.load(file)
        else:
            projects = {}

        projects[project_name] = project_description

        with open(file_path, 'w') as file:
            json.dump(projects, file, indent=4)

        return jsonify(success=True)
    else:
        return jsonify(success=False), 400

if __name__ == '__main__':
    app.run(debug=True)