from flask import Flask, request, redirect, url_for, session, render_template, send_file
import pandas as pd
from werkzeug.utils import secure_filename
from docxtpl import DocxTemplate
from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import os

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

@app.route('/upload_and_submit', methods=['POST'])
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
def generate_docx():
    if 'data' in session and 'additional_data' in session:
        data = session['data']
        additional_data = session['additional_data']
        combined_doc = Document()

        for count in range(len(data['Imię'])):
            # Załaduj szablon dokumentu
            template = DocxTemplate(os.path.join("docx_templates", "templatka.docx"))
            context = {
                'imie': data['Imię'][str(count)],
                'nazwisko': data['Nazwisko'][str(count)],
                'numer_indeksu': data['Numer indeksu'][str(count)],
                'data': additional_data['date'],
                'event': additional_data['project-dropdown']
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

if __name__ == '__main__':
    app.run(debug=True)