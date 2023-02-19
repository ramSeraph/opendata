
known_problem_networks = [{ "technology": "4G", "tsp": "JIO" }]

def is_problem_combo(tsp, technology):
    for prob in known_problem_networks:
        if prob["technology"] == technology and prob["tsp"] == tsp:
            return True
    return False


known_problem_network_expansions = [
    {"operator": "Jio 4G", "network_type": "4G"},
    {"operator": "Jio", "network_type": "4G"},
    {"operator": "Jio 4G", "network_type": "Mobile Data (4G/LTE)"},
    {"operator": "Jio 4G", "network_type": "Not Connected (4G/LTE)"},
    {"operator": "Jio 4G", "network_type": "WIFI (4G/LTE)"},
    {"operator": "Jio", "network_type": "Mobile Data (4G/LTE)"},
    {"operator": "Jio", "network_type": "Not Connected (4G/LTE)"},
    {"operator": "Jio", "network_type": "WIFI (4G/LTE)"},
]

def is_problem_expansion_combo(key):
    for prob in known_problem_network_expansions:
        if prob["operator"].lower() == key[3].lower() and prob["network_type"].lower() == key[4].lower():
            return True
    return False


