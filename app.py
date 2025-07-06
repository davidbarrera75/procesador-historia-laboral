from flask import Flask, request, jsonify, send_file, render_template_string
from flask_cors import CORS
import pdfplumber
import json
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)

# HTML embebido en el código
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PDF a JSON - Extractor</title>
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
            max-width: 600px;
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

        .button.success {
            background-color: #34c759;
        }

        .button.success:hover {
            background-color: #2eb04f;
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

        .preview {
            margin-top: 20px;
            padding: 16px;
            background-color: #f5f5f7;
            border-radius: 8px;
            display: none;
            max-height: 300px;
            overflow-y: auto;
        }

        .preview h3 {
            font-size: 16px;
            margin-bottom: 10px;
            color: #1d1d1f;
        }

        .preview pre {
            background-color: white;
            padding: 12px;
            border-radius: 6px;
            font-size: 12px;
            overflow-x: auto;
            white-space: pre-wrap;
            word-wrap: break-word;
        }

        .stats {
            display: flex;
            gap: 20px;
            margin-top: 16px;
            flex-wrap: wrap;
        }

        .stat-item {
            background-color: #f0f0f0;
            padding: 12px 20px;
            border-radius: 8px;
            flex: 1;
            min-width: 150px;
            text-align: center;
        }

        .stat-value {
            font-size: 24px;
            font-weight: 600;
            color: #0071e3;
        }

        .stat-label {
            font-size: 14px;
            color: #86868b;
            margin-top: 4px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>PDF a JSON Extractor</h1>
        <p class="subtitle">Convierta cualquier PDF a JSON estructurado para procesar los datos como desee</p>
        
        <div class="upload-area" id="uploadArea">
            <svg class="upload-icon" viewBox="0 0 24 24">
                <path d="M9 16h6v-6h4l-7-7-7 7h4v6zm-4 2h14v2H5v-2z"/>
            </svg>
            <p class="upload-text">Subir PDF</p>
            <p class="upload-subtext">Haga clic o arrastre su archivo PDF aquí</p>
            <input type="file" id="fileInput" accept=".pdf">
        </div>

        <div class="file-info" id="fileInfo"></div>

        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p style="margin-top: 16px; color: #86868b;">Extrayendo contenido del PDF...</p>
        </div>

        <div class="message" id="message"></div>

        <div class="stats" id="stats" style="display: none;">
            <div class="stat-item">
                <div class="stat-value" id="pageCount">0</div>
                <div class="stat-label">Páginas</div>
            </div>
            <div class="stat-item">
                <div class="stat-value" id="tableCount">0</div>
                <div class="stat-label">Tablas</div>
            </div>
            <div class="stat-item">
                <div class="stat-value" id="charCount">0</div>
                <div class="stat-label">Caracteres</div>
            </div>
        </div>

        <div class="preview" id="preview">
            <h3>Vista previa del JSON (primeras páginas)</h3>
            <pre id="previewContent"></pre>
        </div>

        <div class="download-buttons" id="downloadButtons">
            <button class="button success" id="downloadJson">Descargar JSON Completo</button>
            <button class="button secondary" id="downloadCompact">Descargar JSON Compacto</button>
        </div>
    </div>

    <script>
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const loading = document.getElementById('loading');
        const message = document.getElementById('message');
        const downloadButtons = document.getElementById('downloadButtons');
        const fileInfo = document.getElementById('fileInfo');
        const preview = document.getElementById('preview');
        const previewContent = document.getElementById('previewContent');
        const stats = document.getElementById('stats');
        const downloadJson = document.getElementById('downloadJson');
        const downloadCompact = document.getElementById('downloadCompact');

        let extractedData = null;

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
            fileInfo.textContent = 'Archivo seleccionado: ' + file.name + ' (' + formatFileSize(file.size) + ')';

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
            downloadButtons.style.display = 'none';
            preview.style.display = 'none';
            stats.style.display = 'none';

            try {
                const response = await fetch('/extract', {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();

                if (response.ok && result.success) {
                    extractedData = result.data;
                    showMessage('PDF procesado exitosamente', 'success');
                    
                    // Mostrar estadísticas
                    document.getElementById('pageCount').textContent = result.data.total_pages;
                    document.getElementById('tableCount').textContent = result.data.total_tables;
                    document.getElementById('charCount').textContent = result.data.total_characters.toLocaleString();
                    stats.style.display = 'flex';
                    
                    // Mostrar vista previa
                    const previewData = {
                        total_pages: result.data.total_pages,
                        total_tables: result.data.total_tables,
                        first_page: result.data.pages[0]
                    };
                    previewContent.textContent = JSON.stringify(previewData, null, 2);
                    preview.style.display = 'block';
                    
                    downloadButtons.style.display = 'block';
                } else {
                    showMessage(result.error || 'Error al procesar el archivo', 'error');
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
            message.className = 'message ' + type;
            message.style.display = 'block';
        }

        // Download full JSON
        downloadJson.addEventListener('click', () => {
            if (!extractedData) return;

            const jsonStr = JSON.stringify(extractedData, null, 2);
            const blob = new Blob([jsonStr], { type: 'application/json' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'pdf_completo.json';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        });

        // Download compact JSON (sin espacios)
        downloadCompact.addEventListener('click', () => {
            if (!extractedData) return;

            const jsonStr = JSON.stringify(extractedData);
            const blob = new Blob([jsonStr], { type: 'application/json' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'pdf_compacto.json';
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

def extract_pdf_content(pdf_path):
    """
    Extrae TODO el contenido del PDF y lo estructura en JSON
    """
    data = {
        'filename': os.path.basename(pdf_path),
        'extraction_date': datetime.now().isoformat(),
        'total_pages': 0,
        'total_tables': 0,
        'total_characters': 0,
        'pages': []
    }
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            data['total_pages'] = len(pdf.pages)
            
            # Extraer metadatos si están disponibles
            if hasattr(pdf, 'metadata'):
                data['metadata'] = {
                    key: str(value) if value else None 
                    for key, value in (pdf.metadata or {}).items()
                }
            
            # Procesar cada página
            for page_num, page in enumerate(pdf.pages):
                page_data = {
                    'page_number': page_num + 1,
                    'width': page.width,
                    'height': page.height,
                    'text': '',
                    'tables': [],
                    'text_lines': []
                }
                
                # Extraer texto completo
                text = page.extract_text()
                if text:
                    page_data['text'] = text
                    page_data['text_lines'] = text.split('\n')
                    data['total_characters'] += len(text)
                
                # Extraer todas las tablas
                tables = page.extract_tables()
                if tables:
                    for table_idx, table in enumerate(tables):
                        if table and len(table) > 0:
                            # Convertir tabla a estructura más útil
                            table_data = {
                                'table_index': table_idx,
                                'rows': len(table),
                                'columns': len(table[0]) if table[0] else 0,
                                'headers': table[0] if len(table) > 0 else [],
                                'data': table[1:] if len(table) > 1 else [],
                                'raw_data': table
                            }
                            page_data['tables'].append(table_data)
                            data['total_tables'] += 1
                
                # Extraer información adicional si está disponible
                try:
                    # Intentar extraer palabras con sus posiciones
                    words = page.extract_words()
                    if words and len(words) < 1000:  # Limitar para no sobrecargar
                        page_data['words_sample'] = words[:100]  # Primeras 100 palabras
                except:
                    pass
                
                data['pages'].append(page_data)
        
        return data, None
    
    except Exception as e:
        return None, str(e)

@app.route('/extract', methods=['POST'])
def extract_pdf():
    if 'pdf' not in request.files:
        return jsonify({'success': False, 'error': 'No se encontró el archivo PDF'}), 400
    
    file = request.files['pdf']
    
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No se seleccionó ningún archivo'}), 400
    
    if not file.filename.endswith('.pdf'):
        return jsonify({'success': False, 'error': 'El archivo debe ser un PDF'}), 400
    
    try:
        temp_path = 'temp_' + str(datetime.now().timestamp()) + '.pdf'
        file.save(temp_path)
        
        data, error = extract_pdf_content(temp_path)
        
        os.remove(temp_path)
        
        if error:
            return jsonify({'success': False, 'error': 'Error al procesar el PDF: ' + error}), 500
        
        return jsonify({
            'success': True,
            'data': data,
            'message': 'PDF extraído exitosamente'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok', 'message': 'PDF to JSON Extractor is running'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
