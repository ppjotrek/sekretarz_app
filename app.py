from flask import Flask, request, redirect, url_for, session, render_template, send_file
import pandas as pd
from werkzeug.utils import secure_filename
import os
from docx import Document


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.secret_key = 'supersecretkey'  # Ustaw klucz sesji
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    combined_data = {}
    if 'data' in session:
        df = pd.DataFrame.from_dict(session['data'])
        combined_data['data'] = df.to_dict()
    if 'additional_data' in session:
        combined_data['additional_data'] = session['additional_data']
    return render_template('index.html', combined_data=combined_data)

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
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
            return redirect(url_for('index'))
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit_data():
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
def generate_docx():
    if 'data' in session and 'additional_data' in session:
        data = session['data']
        additional_data = session['additional_data']
        document = Document()
        count = 0
        docs_name = additional_data['project-dropdown'] + data['Nazwisko'][str(count)] + '.docx' 
        docx_path = os.path.join(app.config['UPLOAD_FOLDER'], docs_name)
        document.add_heading('Usprawiedliwienie', level=1)
        document.add_heading('Dane', level=2)
        for key, value in data.items():
            document.add_heading(key, level=3)
            for k, v in value.items():
                document.add_paragraph(f'{k}: {v}')
        document.add_heading('Dodatkowe informacje', level=2)
        for key, value in additional_data.items():
            document.add_paragraph(f'{key}: {value}')
        document.save(docx_path)
        return send_file(docx_path, as_attachment=True)
    return 'No data available to generate document'


if __name__ == '__main__':
    app.run(debug=True)