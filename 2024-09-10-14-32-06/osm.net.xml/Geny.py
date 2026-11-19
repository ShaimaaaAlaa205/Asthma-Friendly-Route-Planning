import xml.etree.ElementTree as ET
import random

# Data Definitions
VehRoutes = {

    "vehRoute1":{
        "stops:" :[],
        "edges": "672905148 169909217#0 1161059821#1 574620587  175777433#0 1007590184#0 " 
    }
}

def create_element(tag, attributes, parent):
    """Create an XML element with given attributes and append it to the parent."""
    element = ET.SubElement(parent, tag)
    for key, value in attributes.items():
        element.set(key, value)
    return element

def create_routes(routes_dict, root):
    for route_id, route_data in routes_dict.items():
        create_element("route", {"id": route_id, "edges": route_data["edges"]}, root)

def generate_random_vehs(num_vehs, route_ids):
    """Generate a sorted list of vehicles with random routes and departure times."""
    vehs = []
    for i in range(num_vehs):
        veh_id = f"veh_{i + 1}"  # Assigning vehicle id as veh_1, veh_2, etc.
        route = random.choice(route_ids)  # Randomly assign one of the available routes
        depart_time = i * 2  # Can be modified for orderly departure times
        vehicle = {"id": veh_id, "route": route, "capacity": random.randint(30, 60), "speed": 60, "depart": depart_time}
        vehs.append(vehicle)
    return vehs

# =======================================================================================
# Create the root element
root = ET.Element("routes")

# Create vType element for cars
create_element("vType", {"id": "car", "accel": "2.6", "decel": "4.5", "sigma": "0.5", "length": "4.5", "minGap": "2.5", "maxSpeed": "80", "color": "blue"}, root)

# Create route elements from VehRoutes
create_routes(VehRoutes, root)

# =======================================================================================

# Generate 300 vehicles with random routes
num_vehicles = 300
veh_route_ids = list(VehRoutes.keys())
generated_vehicles = generate_random_vehs(num_vehicles, veh_route_ids)

# Create vehicle elements for generated vehicles
for vehicle in generated_vehicles:
    vehicle_element = create_element("vehicle", {
        "id": vehicle["id"], 
        "type": "car", 
        "route": vehicle["route"], 
        "depart": str(vehicle["depart"])  # Use the newly added depart time
    }, root)

# =======================================================================================

# Write the data to the file and print the XML
tree = ET.ElementTree(root)
tree.write("osm.passenger.trips.xml")
ET.dump(root)

print("Data written to osm.passenger.trips.xml")
