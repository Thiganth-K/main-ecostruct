from flask import Flask, render_template, request, jsonify, send_file
from utils import grade_data, spec_data, resolve_ecf, calculate_transport_factor, calculate_waste_factor
import math
import pdfkit
import tempfile
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/concrete')
def concrete():
    return render_template('concrete.html')

@app.route('/concrete/column')
def column():
    return render_template('column.html')

@app.route('/concrete/calculate', methods=['POST'])
def calculate():
    data = request.get_json()
    results = []
    
    for column in data['columns']:
        length = float(column['length'])
        breadth = float(column['breadth'])
        depth = float(column['depth'])
        num_columns = int(column['numColumns'])
        steel_dia = float(column['steelDiameter'])
        steel_length = float(column['steelLength'])
        num_bars = int(column['numBars'])
        grade = column['grade']
        spec = column['specification']
        
        # Calculate volume
        volume = length * breadth * depth
        
        # Get concrete quantities
        cement_qty = volume * grade_data[grade]['cement']
        fine_qty = volume * grade_data[grade]['fine_agg']
        coarse_qty = volume * grade_data[grade]['coarse_agg']
        concrete_weight = cement_qty + fine_qty + coarse_qty
        
        # Calculate steel
        steel_volume = math.pi * (steel_dia / 1000) ** 2 / 4 * steel_length
        steel_mass = steel_volume * 7860 * num_bars
        
        # Total weight and ECF
        total_weight = concrete_weight + steel_mass
        ecf = resolve_ecf(grade, spec)
        embodied_carbon = total_weight * ecf
        
        results.append({
            'volume': round(volume, 2),
            'cement_qty': round(cement_qty, 2),
            'fine_qty': round(fine_qty, 2),
            'coarse_qty': round(coarse_qty, 2),
            'steel_mass': round(steel_mass, 2),
            'total_weight': round(total_weight, 2),
            'ecf': round(ecf, 3),
            'embodied_carbon': round(embodied_carbon, 2)
        })
    
    return jsonify({'results': results})

@app.route('/concrete/results')
def results():
    return render_template('results.html')

@app.route('/concrete/calculate-transport', methods=['POST'])
def calculate_transport():
    data = request.get_json()
    total_weight = float(data['total_weight'])
    distance = float(data['distance'])
    fuel_type = data['fuel_type']
    
    transport_factor = calculate_transport_factor(total_weight, distance, fuel_type)
    
    return jsonify({
        'transport_factor': round(transport_factor, 2),
        'vehicle_type': data['vehicle_type'],
        'distance': distance,
        'fuel_type': fuel_type
    })

@app.route('/concrete/calculate-waste', methods=['POST'])
def calculate_waste():
    data = request.get_json()
    total_weight = float(data['total_weight'])
    grade = data['grade']
    spec = data['specification']
    transport_factor = float(data['transport_factor'])
    
    result = calculate_waste_factor(total_weight, grade, spec, transport_factor)
    
    return jsonify({
        'waste_factor': round(result['waste_factor'], 3),
        'ecf_from_waste': round(result['ecf_from_waste'], 2),
        'total_carbon': round(
            data['embodied_carbon'] + transport_factor + result['ecf_from_waste'],
            2
        )
    })

@app.route('/concrete/compare', methods=['POST'])
def compare_columns():
    data = request.get_json()
    columns = data['columns']
    
    # Calculate efficiency scores
    min_carbon = min(col['total_carbon'] for col in columns)
    for col in columns:
        col['efficiency_score'] = (min_carbon / col['total_carbon']) * 100
    
    # Find most and least efficient
    most_efficient = max(columns, key=lambda x: x['efficiency_score'])
    least_efficient = min(columns, key=lambda x: x['efficiency_score'])
    
    return jsonify({
        'columns': columns,
        'most_efficient_index': columns.index(most_efficient),
        'least_efficient_index': columns.index(least_efficient)
    })

@app.route('/concrete/export-pdf', methods=['POST'])
def export_pdf():
    data = request.get_json()
    
    # Generate HTML content
    html_content = render_template(
        'pdf_template.html',
        columns=data['columns'],
        date=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    
    # Configure PDF options
    options = {
        'page-size': 'A4',
        'margin-top': '0.75in',
        'margin-right': '0.75in',
        'margin-bottom': '0.75in',
        'margin-left': '0.75in',
    }
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
        pdfkit.from_string(html_content, f.name, options=options)
        return send_file(f.name, as_attachment=True, download_name='ecostruct_report.pdf')

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=9000)