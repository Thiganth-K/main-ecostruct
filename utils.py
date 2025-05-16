grade_data = {
    "M20": {"cement": 403.2, "fine_agg": 672, "coarse_agg": 1260, "ECF": 0.11},
    "M25": {"cement": 360, "fine_agg": 679, "coarse_agg": 1207, "ECF": 0.12},
    "M30": {"cement": 350, "fine_agg": 711, "coarse_agg": 1283, "ECF": 0.13},
    "M35": {"cement": 420, "fine_agg": 750, "coarse_agg": 1200, "ECF": 0.14},
    "M40": {"cement": 400, "fine_agg": 660, "coarse_agg": 1168, "ECF": 0.15},
    "M45": {"cement": 450, "fine_agg": 685, "coarse_agg": 1150, "ECF": 0.16},
    "M50": {"cement": 450, "fine_agg": 750, "coarse_agg": 1200, "ECF": 0.17},
}

spec_data = {
    "Portland Limestone – 14%": {
        "M20": 0.095, "M25": 0.104, "M30": 0.113, "M35": 0.122,
        "M40": 0.131, "M45": 0.140, "M50": 0.149
    },
    "35% Natural Pozzolanic Ash": {
        "M20": 0.081, "M25": 0.089, "M30": 0.098, "M35": 0.107,
        "M40": 0.116, "M45": 0.124, "M50": 0.133
    },
    "15% Fly Ash": {
        "M20": 0.092, "M25": 0.101, "M30": 0.110, "M35": 0.118,
        "M40": 0.127, "M45": 0.136, "M50": 0.145
    },
    "30% Fly Ash": {
        "M20": 0.085, "M25": 0.093, "M30": 0.101, "M35": 0.110,
        "M40": 0.118, "M45": 0.127, "M50": 0.135
    },
    "40% Fly Ash": {
        "M20": 0.079, "M25": 0.087, "M30": 0.095, "M35": 0.103,
        "M40": 0.111, "M45": 0.119, "M50": 0.127
    },
    "25% Blast Furnace Slag": {
        "M20": 0.090, "M25": 0.099, "M30": 0.108, "M35": 0.117,
        "M40": 0.126, "M45": 0.135, "M50": 0.144
    },
    "50% Blast Furnace Slag": {
        "M20": 0.082, "M25": 0.090, "M30": 0.098, "M35": 0.106,
        "M40": 0.114, "M45": 0.122, "M50": 0.130
    },
    "70% Blast Furnace Slag": {
        "M20": 0.073, "M25": 0.080, "M30": 0.087, "M35": 0.094,
        "M40": 0.101, "M45": 0.108, "M50": 0.115
    }
}

def resolve_ecf(grade, spec):
    if spec != "Other":
        return spec_data.get(spec, {}).get(grade, grade_data[grade]["ECF"])
    return grade_data[grade]["ECF"]


def calculate_transport_factor(total_weight, distance, fuel_type):
    # Define transport ECF values (extendable in future)
    transport_ecf_map = {
        "Petrol": 0.615
    }
    ecf = transport_ecf_map.get(fuel_type, 0.615)
    return (total_weight * distance * ecf) / 1000


def calculate_waste_factor(total_weight, grade, spec, transport_factor):
    try:
        ecf_grade = grade_data[grade]["ECF"]
        ecf_spec = spec_data.get(spec, {}).get(grade, ecf_grade) if spec != "Other" else ecf_grade
        
        # Prevent division by zero
        if ecf_spec == 0:
            waste_factor = 0.02  # Default to minimum waste factor
        else:
            waste_factor = 0.05 * (ecf_grade / ecf_spec) + transport_factor + 0.02
            
        ecf_from_waste = total_weight * waste_factor
        return {
            'waste_factor': waste_factor,
            'ecf_from_waste': ecf_from_waste
        }
    except Exception as e:
        # Handle any other potential errors
        return {
            'waste_factor': 0.02,  # Default minimum
            'ecf_from_waste': total_weight * 0.02
        }