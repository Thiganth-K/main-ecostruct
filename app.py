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

def calculate_costs(cement_qty, fine_qty, coarse_qty, steel_mass, spec, grade):
    cement_cost = 0
    if spec == "15% Fly Ash":
        cement_cost = (0.85 * cement_qty) * 8 + (0.15 * cement_qty) * 2.9
    elif spec == "30% Fly Ash":
        cement_cost = (0.70 * cement_qty) * 8 + (0.30 * cement_qty) * 2.9
    elif spec == "40% Fly Ash":
        cement_cost = (0.60 * cement_qty) * 8 + (0.40 * cement_qty) * 2.9
    elif spec == "Portland Limestone – 14%":
        cement_cost = (0.86 * cement_qty) * 8 + (0.14 * cement_qty) * 6
    elif spec == "35% Natural Pozzolanic Ash":
        cement_cost = (0.65 * cement_qty) * 8 + (0.35 * cement_qty) * 5.4
    elif spec == "25% Blast Furnace Slag":
        cement_cost = (0.75 * cement_qty) * 8 + (0.25 * cement_qty) * 4
    elif spec == "50% Blast Furnace Slag":
        cement_cost = (0.50 * cement_qty) * 8 + (0.50 * cement_qty) * 4
    elif spec == "70% Blast Furnace Slag":
        cement_cost = (0.70 * cement_qty) * 8 + (0.30 * cement_qty) * 4
    elif spec == "Other":
        cement_cost = cement_qty * 8
    else:
        cement_cost = cement_qty * 8  # Default

    fine_agg_cost = fine_qty * 1.4
    coarse_agg_cost = coarse_qty * 1.4
    steel_cost = steel_mass * 66
    total_cost = cement_cost + fine_agg_cost + coarse_agg_cost + steel_cost

    return {
        "cement_cost": round(cement_cost, 2),
        "fine_agg_cost": round(fine_agg_cost, 2),
        "coarse_agg_cost": round(coarse_agg_cost, 2),
        "steel_cost": round(steel_cost, 2),
        "total_cost": round(total_cost, 2)
    }

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

        # Cost calculation
        costs = calculate_costs(cement_qty, fine_qty, coarse_qty, steel_mass, spec, grade)
        
        results.append({
            'volume': round(volume, 2),
            'cement_qty': round(cement_qty, 2),
            'fine_qty': round(fine_qty, 2),
            'coarse_qty': round(coarse_qty, 2),
            'steel_mass': round(steel_mass, 2),
            'total_weight': round(total_weight, 2),
            'ecf': round(ecf, 3),
            'embodied_carbon': round(embodied_carbon, 2),
            'grade': grade,
            'specification': spec,
            # Add cost fields
            'cement_cost': costs['cement_cost'],
            'fine_agg_cost': costs['fine_agg_cost'],
            'coarse_agg_cost': costs['coarse_agg_cost'],
            'steel_cost': costs['steel_cost'],
            'total_cost': costs['total_cost']
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
    columns = data['columns']

    # Calculate total cost on the backend to ensure accuracy
    total_cost = sum(col.get('total_cost', 0) for col in columns)

    # Generate HTML content
    html_content = render_template(
        'pdf_template.html',
        columns=columns,
        total_cost=total_cost,
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