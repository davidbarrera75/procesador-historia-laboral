from flask import Flask, request, jsonify, send_file, render_template_string
from flask_cors import CORS
import pdfplumber
import pandas as pd
import re
import io
import json
from datetime import datetime
import os
import unicodedata

app = Flask(__name__)
CORS(app)

# HTML embebido en el código
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Procesador Historia Laboral</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background-color: #f5f5f7;
            color: #1d1d1f;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .container {
            background-color: white;
            padding: 48px;
            border-radius: 16px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.07);
            max-width: 500px;
            width: 100%;
            margin: 20px;
        }

        h1 {
            font-size: 32px;
            font-weight: 600;
            margin-bottom: 12px;
            color: #1d1d1f;
        }

        .subtitle {
            color: #86868b;
            font-size: 16px;
            margin-bottom: 32px;
        }

        .upload-area {
            border: 2px dashed #d2d2d7;
            border-radius: 12px;
            padding: 40px;
            text-align: center;
            transition: all 0.3s ease;
            cursor: pointer;
            background-color: #fbfbfd;
        }

        .upload-area:hover {
            border-color: #0071e3;
            background-color: #f5f9ff;
        }

        .upload-area.dragover {
            border-color: #0071e3;
            background-color: #e8f2ff;
        }

        .upload-icon {
            width: 64px;
            height: 64px;
            margin: 0 auto 16px;
            fill: #86868b;
        }

        .upload-text {
            font-size: 18px;
            font-weight: 500;
            color: #1d1d1f;
            margin-bottom: 8px;
        }

        .upload-subtext {
            font-size: 14px;
            color: #86868b;
        }

        input[type="file"] {
            display: none;
        }

        .button {
            background-color: #0071e3;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s ease;
            display: inline-block;
            text-decoration: none;
            margin: 4px;
        }

        .button:hover {
            background-color: #0077ed;
            transform: scale(1.02);
        }

        .button:disabled {
            background-color: #d2d2d7;
            cursor: not-allowed;
            transform: scale(1);
        }

        .button.secondary {
            background-color: #5ac8fa;
        }

        .button.secondary:hover {
            background-color: #32ade6;
        }

        .loading {
            display: none;
            text-align: center;
            margin-top: 32px;
        }

        .spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #0071e3;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .message {
            margin-top: 24px;
            padding: 16px;
            border-radius: 8px;
            text-align: center;
            display: none;
        }

        .message.success {
            background-color: #d4f4dd;
            color: #00692b;
        }

        .message.error {
            background-color: #ffd4d4;
            color: #d70015;
        }

        .message.info {
            background-color: #d4e4ff;
            color: #0051d7;
        }

        .download-buttons {
            display: none;
            margin-top: 24px;
            text-align: center;
        }

        .file-info {
            margin-top: 16px;
            padding: 12px;
            background-color: #f5f5f7;
            border-radius: 8px;
            font-size: 14px;
            color: #1d1d1f;
            display: none;
        }

        .debug-info {
            margin-top: 16px;
            padding: 12px;
            background-color: #f0f0f0;
            border-radius: 8px;
            font-size: 12px;
            color: #666;
            max-height: 200px;
            overflow-y: auto;
            display: none;
            white-space: pre-wrap;
            font-family: monospace;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Procesador Historia Laboral</h1>
        <p class="subtitle">Suba su archivo PDF para extraer y exportar datos laborales</p>
        
        <div class="upload-area" id="uploadArea">
            <svg class="upload-icon" viewBox="0 0 24 24">
                <path d="M9 16h6v-6h4l-7-7-7 7h4v6zm-4 2h14v2H5v-2z"/>
            </svg>
            <p class="upload-text">Subir PDF</p>
            <p class="upload-subtext">Haga clic o arrastre su archivo aquí</p>
            <input type="file" id="fileInput" accept=".pdf">
        </div>

        <div class="file-info" id="fileInfo"></div>

        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p style="margin-top: 16px; color: #86868b;">Procesando archivo...</p>
        </div>

        <div class="message" id="message"></div>
        <div class="debug-info" id="debugInfo"></div>

        <div class="download-buttons" id="downloadButtons">
            <button class="button" id="downloadExcel">Exportar Excel</button>
            <button class="button secondary" id="downloadJson">Descargar JSON</button>
        </div>
    </div>

    <script>
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const loading = document.getElementById('loading');
        const message = document.getElementById('message');
        const downloadButtons = document.getElementById('downloadButtons');
        const fileInfo = document.getElementById('fileInfo');
        const debugInfo = document.getElementById('debugInfo');
        const downloadExcel = document.getElementById('downloadExcel');
        const downloadJson = document.getElementById('downloadJson');

        let processedData = null;

        // Click to upload
        uploadArea.addEventListener('click', () => {
            fileInput.click();
        });

        // Drag and drop
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });

        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            
            const files = e.dataTransfer.files;
            if (files.length > 0 && files[0].type === 'application/pdf') {
                handleFile(files[0]);
            } else {
                showMessage('Por favor, seleccione un archivo PDF válido', 'error');
            }
        });

        // File input change
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                handleFile(e.target.files[0]);
            }
        });

        function handleFile(file) {
            if (file.type !== 'application/pdf') {
                showMessage('Por favor, seleccione un archivo PDF válido', 'error');
                return;
            }

            fileInfo.style.display = 'block';
            fileInfo.textContent = `Archivo seleccionado: ${file.name} (${formatFileSize(file.size)})`;

            uploadFile(file);
        }

        function formatFileSize(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }

        async function uploadFile(file) {
            const formData = new FormData();
            formData.append('pdf', file);

            loading.style.display = 'block';
            message.style.display = 'none';
            debugInfo.style.display = 'none';
            downloadButtons.style.display = 'none';

            try {
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();

                if (response.ok && result.success) {
                    processedData = result.data;
                    showMessage(`Archivo procesado exitosamente. Se encontraron ${result.data.length} registros.`, 'success');
                    downloadButtons.style.display = 'block';
                } else {
                    showMessage(result.error || 'Error al procesar el archivo', 'error');
                    if (result.debug_info) {
                        debugInfo.style.display = 'block';
                        debugInfo.textContent = 'Información de debug:\n' + result.debug_info;
                    }
                }
            } catch (error) {
                showMessage('Error de conexión con el servidor', 'error');
                console.error('Error:', error);
            } finally {
                loading.style.display = 'none';
            }
        }

        function showMessage(text, type) {
            message.textContent = text;
            message.className = `message ${type}`;
            message.style.display = 'block';
        }

        // Download handlers
        downloadExcel.addEventListener('click', async () => {
            if (!processedData) return;

            try {
                const response = await fetch('/download/excel', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ data: processedData })
                });

                if (response.ok) {
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'historia_laboral.xlsx';
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                }
            } catch (error) {
                showMessage('Error al descargar el archivo Excel', 'error');
                console.error('Error:', error);
            }
        });

        downloadJson.addEventListener('click', () => {
            if (!processedData) return;

            const jsonStr = JSON.stringify(processedData, null, 2);
            const blob = new Blob([jsonStr], { type: 'application/json' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'historia_laboral.json';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        });
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

def normalize_text(text):
    """
    Normaliza el texto para hacer búsquedas más flexibles
    """
    # Eliminar tildes
    text = ''.join(c for c in unicodedata.normalize('NFD', text)
                   if unicodedata.category(c) != 'Mn')
    # Convertir a minúsculas
    text = text.lower()
    # Eliminar espacios múltiples
    text = ' '.join(text.split())
    return text

def extract_labor_history_data(pdf_path):
    """
    Extrae datos de historia laboral del PDF con búsqueda flexible
    """
    data = []
    debug_info = []
    
    # Palabras clave para buscar (normalizadas)
    keywords = [
        "historia laboral regimen de ahorro individual con solidaridad",
        "historia laboral regimen de ahorro individual",
        "historia laboral",
        "regimen de ahorro individual",
        "ahorro individual con solidaridad"
    ]
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            found_section = False
            
            debug_info.append(f"Total de páginas en el PDF: {len(pdf.pages)}")
            
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text()
                
                if not text:
                    debug_info.append(f"Página {page_num + 1}: Sin texto extraíble")
                    continue
                
                # Normalizar el texto de la página
                normalized_text = normalize_text(text)
                
                # Log primeros 500 caracteres de cada página
                preview = text[:500].replace('\n', ' ')
                debug_info.append(f"\nPágina {page_num + 1} - Vista previa: {preview}...")
                
                # Buscar cualquiera de las palabras clave
                for keyword in keywords:
                    if keyword in normalized_text:
                        found_section = True
                        debug_info.append(f"¡Sección encontrada en página {page_num + 1} con palabra clave: '{keyword}'!")
                        break
                
                if found_section:
                    # Intentar extraer tablas
                    tables = page.extract_tables()
                    
                    if tables:
                        debug_info.append(f"Página {page_num + 1}: {len(tables)} tabla(s) encontrada(s)")
                    
                    for table_idx, table in enumerate(tables):
                        if not table:
                            continue
                        
                        debug_info.append(f"Tabla {table_idx + 1}: {len(table)} filas")
                        
                        header_row = None
                        periodo_idx = None
                        salario_idx = None
                        
                        for i, row in enumerate(table):
                            if row and any(row):
                                # Debug: mostrar primeras filas
                                if i < 3:
                                    debug_info.append(f"  Fila {i}: {row}")
                                
                                for j, cell in enumerate(row):
                                    if cell:
                                        cell_text = str(cell).strip()
                                        cell_normalized = normalize_text(cell_text)
                                        
                                        if "periodo" in cell_normalized:
                                            periodo_idx = j
                                            header_row = i
                                            debug_info.append(f"  Columna 'Periodo' encontrada en posición {j}")
                                        elif any(term in cell_normalized for term in ["salario base", "cotizacion", "salario"]):
                                            salario_idx = j
                                            debug_info.append(f"  Columna 'Salario' encontrada en posición {j}")
                                
                                if periodo_idx is not None and salario_idx is not None and i > header_row:
                                    periodo = row[periodo_idx] if periodo_idx < len(row) else None
                                    salario = row[salario_idx] if salario_idx < len(row) else None
                                    
                                    if periodo and salario:
                                        periodo_clean = re.sub(r'\D', '', str(periodo))
                                        if len(periodo_clean) == 6 and periodo_clean.isdigit():
                                            año = periodo_clean[:4]
                                            mes = periodo_clean[4:6]
                                            
                                            salario_clean = str(salario).replace('$', '').replace(',', '').replace('.', '')
                                            salario_clean = re.sub(r'[^\d]', '', salario_clean)
                                            
                                            if salario_clean.isdigit():
                                                if len(salario_clean) > 2:
                                                    salario_num = int(salario_clean[:-2])
                                                else:
                                                    salario_num = int(salario_clean)
                                                
                                                data.append({
                                                    'año': int(año),
                                                    'mes': int(mes),
                                                    'salario': salario_num
                                                })
                    
                    # Si no encontramos tablas, intentar con expresiones regulares
                    if not tables or not data:
                        debug_info.append(f"Página {page_num + 1}: Intentando extracción con regex")
                        lines = text.split('\n')
                        
                        for line in lines:
                            # Buscar patrón: YYYYMM seguido de un monto
                            matches = re.findall(r'(\d{6})\s+.*?\$?\s*([\d,\.]+)', line)
                            for match in matches:
                                periodo = match[0]
                                salario = match[1]
                                
                                if len(periodo) == 6:
                                    año = periodo[:4]
                                    mes = periodo[4:6]
                                    
                                    salario_clean = salario.replace(',', '').replace('.', '')
                                    if salario_clean.isdigit() and len(salario_clean) > 2:
                                        salario_num = int(salario_clean)
                                        
                                        data.append({
                                            'año': int(año),
                                            'mes': int(mes),
                                            'salario': salario_num
                                        })
                                        debug_info.append(f"  Registro encontrado: {año}/{mes} - ${salario_num}")
        
        debug_text = '\n'.join(debug_info)
        
        if not found_section:
            debug_text += "\n\nNo se encontró ninguna sección relacionada con historia laboral."
            debug_text += "\nPalabras clave buscadas:"
            for kw in keywords:
                debug_text += f"\n  - {kw}"
        
        return data, None, debug_text
    
    except Exception as e:
        error_msg = str(e)
        debug_text = '\n'.join(debug_info) + f"\n\nError: {error_msg}"
        return None, error_msg, debug_text

def create_excel(data):
    """
    Crea un archivo Excel con los datos procesados
    """
    df = pd.DataFrame(data)
    df.columns = ['AÑO', 'MES', 'SALARIO']
    
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Historia Laboral')
        
        worksheet = writer.sheets['Historia Laboral']
        worksheet.column_dimensions['A'].width = 10
        worksheet.column_dimensions['B'].width = 10
        worksheet.column_dimensions['C'].width = 15
        
        for cell in worksheet[1]:
            cell.font = cell.font.copy(bold=True)
    
    output.seek(0)
    return output

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'pdf' not in request.files:
        return jsonify({'success': False, 'error': 'No se encontró el archivo PDF'}), 400
    
    file = request.files['pdf']
    
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No se seleccionó ningún archivo'}), 400
    
    if not file.filename.endswith('.pdf'):
        return jsonify({'success': False, 'error': 'El archivo debe ser un PDF'}), 400
    
    try:
        temp_path = f'temp_{datetime.now().timestamp()}.pdf'
        file.save(temp_path)
        
        data, error, debug_info = extract_labor_history_data(temp_path)
        
        os.remove(temp_path)
        
        if error:
            return jsonify({
                'success': False, 
                'error': f'Error al procesar el PDF: {error}',
                'debug_info': debug_info
            }), 500
        
        if not data:
            return jsonify({
                'success': False, 
                'error': 'No se encontraron datos válidos. Revise la información de debug.',
                'debug_info': debug_info
            }), 404
        
        return jsonify({
            'success': True,
            'data': data,
            'message': f'Se procesaron {len(data)} registros exitosamente',
            'debug_info': debug_info if len(data) < 10 else None  # Solo mostrar debug si hay pocos datos
        })
    
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': str(e),
            'debug_info': 'Error crítico al procesar el archivo'
        }), 500

@app.route('/download/excel', methods=['POST'])
def download_excel():
    try:
        data = request.json.get('data', [])
        
        if not data:
            return jsonify({'error': 'No hay datos para exportar'}), 400
        
        excel_buffer = create_excel(data)
        
        return send_file(
            excel_buffer,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='historia_laboral.xlsx'
        )
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    # Para producción
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
