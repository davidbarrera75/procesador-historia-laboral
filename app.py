from flask import Flask, request, jsonify, send_file, render_template_string
from flask_cors import CORS
import pdfplumber
import pandas as pd
import json
import re
import io
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
    <title>Extractor Historia Laboral - PDF a Excel</title>
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

        .results {
            margin-top: 20px;
            padding: 16px;
            background-color: #f5f5f7;
            border-radius: 8px;
            display: none;
        }

        .results h3 {
            font-size: 18px;
            margin-bottom: 12px;
            color: #1d1d1f;
        }

        .results-details {
            font-size: 14px;
            line-height: 1.6;
            color: #333;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Extractor Historia Laboral</h1>
        <p class="subtitle">Suba su PDF para extraer datos de historia laboral y exportar a Excel</p>
        
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
            <p style="margin-top: 16px; color: #86868b;">Procesando PDF y extrayendo datos...</p>
        </div>

        <div class="message" id="message"></div>

        <div class="results" id="results">
            <h3>Resultados de la extracción</h3>
            <div class="results-details" id="resultsDetails"></div>
        </div>

        <div class="stats" id="stats" style="display: none;">
            <div class="stat-item">
                <div class="stat-value" id="recordCount">0</div>
                <div class="stat-label">Registros</div>
            </div>
            <div class="stat-item">
                <div class="stat-value" id="yearRange">-</div>
                <div class="stat-label">Período</div>
            </div>
            <div class="stat-item">
                <div class="stat-value" id="avgSalary">$0</div>
                <div class="stat-label">Salario Promedio</div>
            </div>
        </div>

        <div class="download-buttons" id="downloadButtons">
            <button class="button success" id="downloadExcel">Descargar Excel</button>
            <button class="button secondary" id="downloadCsv">Descargar CSV</button>
            <button class="button" id="downloadJson">Descargar JSON</button>
        </div>
    </div>

    <script>
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const loading = document.getElementById('loading');
        const message = document.getElementById('message');
        const downloadButtons = document.getElementById('downloadButtons');
        const fileInfo = document.getElementById('fileInfo');
        const results = document.getElementById('results');
        const resultsDetails = document.getElementById('resultsDetails');
        const stats = document.getElementById('stats');
        const downloadExcel = document.getElementById('downloadExcel');
        const downloadCsv = document.getElementById('downloadCsv');
        const downloadJson = document.getElementById('downloadJson');

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
            results.style.display = 'none';
            stats.style.display = 'none';

            try {
                const response = await fetch('/process', {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();

                if (response.ok && result.success) {
                    extractedData = result.data;
                    showMessage('PDF procesado exitosamente', 'success');
                    
                    // Mostrar estadísticas
                    document.getElementById('recordCount').textContent = result.summary.total_records;
                    document.getElementById('yearRange').textContent = result.summary.year_range;
                    document.getElementById('avgSalary').textContent = '$' + result.summary.avg_salary.toLocaleString();
                    stats.style.display = 'flex';
                    
                    // Mostrar detalles
                    resultsDetails.innerHTML = result.summary.details;
                    results.style.display = 'block';
                    
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

        // Download Excel
        downloadExcel.addEventListener('click', async () => {
            if (!extractedData) return;

            try {
                const response = await fetch('/download/excel', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ data: extractedData })
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

        // Download CSV
        downloadCsv.addEventListener('click', () => {
            if (!extractedData) return;

            // Convertir a CSV
            const headers = ['año', 'mes', 'salario'];
            const csvContent = [
                headers.join(','),
                ...extractedData.map(row => 
                    [row.año, row.mes, row.salario].join(',')
                )
            ].join('\\n');

            const blob = new Blob([csvContent], { type: 'text/csv' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'historia_laboral.csv';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        });

        // Download JSON
        downloadJson.addEventListener('click', () => {
            if (!extractedData) return;

            const jsonStr = JSON.stringify(extractedData, null, 2);
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

def extract_labor_history_data(pdf_path):
    """Extrae todos los datos de historia laboral del PDF"""
    
    all_records = []
    pages_processed = 0
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Procesar cada página
            for page_num, page in enumerate(pdf.pages):
                pages_processed += 1
                
                try:
                    # Buscar en tablas
                    tables = page.extract_tables()
                    if tables:
                        for table in tables:
                            if not table or len(table) == 0:
                                continue
                            
                            # La primera fila generalmente son los headers
                            headers = table[0] if len(table) > 0 else []
                            data_rows = table[1:] if len(table) > 1 else []
                            
                            # Buscar índices de columnas
                            periodo_idx = None
                            salario_idx = None
                            
                            for i, header in enumerate(headers):
                                if header:
                                    header_str = str(header).lower()
                                    if 'periodo' in header_str or 'período' in header_str:
                                        periodo_idx = i
                                    elif 'salario' in header_str or 'cotizaci' in header_str or 'base' in header_str:
                                        salario_idx = i
                            
                            if periodo_idx is not None and salario_idx is not None:
                                # Procesar filas de datos
                                for row in data_rows:
                                    if len(row) > max(periodo_idx, salario_idx):
                                        # Verificar si los datos están en una celda con saltos de línea
                                        periodo_cell = str(row[periodo_idx]) if row[periodo_idx] else ""
                                        salario_cell = str(row[salario_idx]) if row[salario_idx] else ""
                                        
                                        if '\n' in periodo_cell or '\n' in salario_cell:
                                            # Datos con saltos de línea
                                            periodos = periodo_cell.split('\n')
                                            salarios = salario_cell.split('\n')
                                            
                                            for i in range(min(len(periodos), len(salarios))):
                                                record = process_record(periodos[i].strip(), salarios[i].strip())
                                                if record:
                                                    all_records.append(record)
                                        else:
                                            # Una fila por registro
                                            record = process_record(periodo_cell.strip(), salario_cell.strip())
                                            if record:
                                                all_records.append(record)
                    
                    # También buscar en el texto
                    text = page.extract_text()
                    if text:
                        # Buscar patrones de período y salario
                        lines = text.split('\n')
                        for line in lines:
                            match = re.search(r'(\d{6})\s+.*?\$\s*([\d,\.]+)', line)
                            if match:
                                record = process_record(match.group(1), '$' + match.group(2))
                                if record:
                                    all_records.append(record)
                
                except Exception as e:
                    # Continuar con la siguiente página si hay error
                    app.logger.warning(f"Error procesando página {page_num + 1}: {str(e)}")
                    continue
        
        # Eliminar duplicados
        unique_records = []
        seen_periods = set()
        for record in all_records:
            if record['periodo'] not in seen_periods:
                seen_periods.add(record['periodo'])
                unique_records.append(record)
        
        # Ordenar por período
        unique_records.sort(key=lambda x: x['periodo'])
        
        app.logger.info(f"Páginas procesadas: {pages_processed}, Registros encontrados: {len(unique_records)}")
        
        return unique_records, None
    
    except Exception as e:
        app.logger.error(f"Error al procesar PDF: {str(e)}")
        return None, str(e)

def process_record(periodo, salario):
    """Procesa un registro individual"""
    try:
        # Validar período
        if not re.match(r'^\d{6}$', periodo):
            return None
        
        año = int(periodo[:4])
        mes = int(periodo[4:6])
        
        # Validar año y mes
        if año < 1990 or año > 2030 or mes < 1 or mes > 12:
            return None
        
        # Limpiar salario
        salario_limpio = re.sub(r'[^\d]', '', salario)
        if salario_limpio:
            # Asumir que los últimos 2 dígitos son decimales
            if len(salario_limpio) > 2:
                salario_num = int(salario_limpio[:-2])
            else:
                salario_num = int(salario_limpio)
            
            # Validar salario
            if salario_num > 100000 and salario_num < 100000000:
                return {
                    'periodo': periodo,
                    'año': año,
                    'mes': mes,
                    'salario': salario_num
                }
    except:
        pass
    
    return None

def create_excel(data):
    """Crea un archivo Excel con los datos procesados"""
    df = pd.DataFrame(data)
    df = df[['año', 'mes', 'salario']]  # Solo estas columnas
    
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

@app.route('/process', methods=['POST'])
def process_pdf():
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
        
        # Extraer datos
        data, error = extract_labor_history_data(temp_path)
        
        # Limpiar archivo temporal
        try:
            os.remove(temp_path)
        except:
            pass
        
        if error:
            return jsonify({'success': False, 'error': 'Error al procesar el PDF: ' + error}), 500
        
        if not data:
            return jsonify({
                'success': False, 
                'error': 'No se encontraron datos de historia laboral en el PDF. Verifique que el PDF contenga una tabla con columnas "Periodo" y "Salario base de cotización".'
            }), 404
        
        # Calcular resumen
        df = pd.DataFrame(data)
        summary = {
            'total_records': len(data),
            'year_range': f"{data[0]['año']}-{data[-1]['año']}",
            'avg_salary': int(df['salario'].mean()),
            'min_salary': int(df['salario'].min()),
            'max_salary': int(df['salario'].max()),
            'details': f"""
                <strong>Período completo:</strong> {data[0]['periodo']} - {data[-1]['periodo']}<br>
                <strong>Total de meses:</strong> {len(data)}<br>
                <strong>Salario mínimo:</strong> ${df['salario'].min():,}<br>
                <strong>Salario máximo:</strong> ${df['salario'].max():,}<br>
                <strong>Incremento total:</strong> {((df['salario'].iloc[-1] - df['salario'].iloc[0]) / df['salario'].iloc[0] * 100):.1f}%
            """
        }
        
        return jsonify({
            'success': True,
            'data': data,
            'summary': summary,
            'message': 'PDF procesado exitosamente'
        })
    
    except Exception as e:
        app.logger.error(f"Error inesperado: {str(e)}")
        return jsonify({'success': False, 'error': 'Error inesperado al procesar el archivo. Por favor, intente nuevamente.'}), 500

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
    return jsonify({'status': 'ok', 'message': 'Historia Laboral Extractor is running'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
