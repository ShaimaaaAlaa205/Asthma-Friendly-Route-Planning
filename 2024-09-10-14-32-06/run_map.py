import os  # لإضافة المكتبة المسؤولة عن التعامل مع الملفات والمجلدات
import traci
import pytz
import datetime
import pandas as pd

def getdatetime():
    utc_now = pytz.utc.localize(datetime.datetime.utcnow())
    currentDT = utc_now.astimezone(pytz.timezone("Australia/Sydney"))
    DATIME = currentDT.strftime("%Y-%m-%d %H:%M:%S")
    return DATIME

def flatten_list(_2d_list):
    flat_list = []
    for element in _2d_list:
        if type(element) is list:
            for item in element:
                flat_list.append(item)
        else:
            flat_list.append(element)
    return flat_list

def get_exit_direction(angle):
    if 45 <= angle < 135:
        return "Right"
    elif 135 <= angle < 225:
        return "U-turn"
    elif 225 <= angle < 315:
        return "Left"
    else:
        return "Straight"
    
# Start SUMO
sumoCmd = ["sumo", "-c", "osm.sumocfg"]
traci.start(sumoCmd)

# Data storage
packBigData = []

# Junction tracking
junction_edges = set()  # Set to store edges associated with junctions
edge_junction_map = {}  # Maps each edge to the corresponding junction it is linked with
packPersonData = []  # Data list to track person activities
personState = {}  # Dictionary to track each person's last known state (on bus, off bus)

# Populate junction_edges and edge_junction_map
for junction_id in traci.junction.getIDList():
    for incoming_edge in traci.junction.getIncomingEdges(junction_id):
        junction_edges.add(incoming_edge)
        edge_junction_map[incoming_edge] = junction_id

# To track which junction the bus has exited and its next direction
bus_junction_track = {}

# Simulation step
while traci.simulation.getMinExpectedNumber() > 0:
    traci.simulationStep()

    vehicles = traci.vehicle.getIDList()
    trafficlights = traci.trafficlight.getIDList()

    for vehid in vehicles:
        x, y = traci.vehicle.getPosition(vehid)
        coord = [x, y]
        lon, lat = traci.simulation.convertGeo(x, y)
        gpscoord = [lon, lat]
        spd = round(traci.vehicle.getSpeed(vehid) * 3.6, 2)
        edge = traci.vehicle.getRoadID(vehid)
        lane = traci.vehicle.getLaneID(vehid)
        displacement = round(traci.vehicle.getDistance(vehid), 2)
        turnAngle = round(traci.vehicle.getAngle(vehid), 2)
        nextTLS = traci.vehicle.getNextTLS(vehid)

        # Initialize variables for junction tracking
        junction_id = ""
        exit_edge = ""
        exit_angle = ""
        exit_direction = ""

        # Check if the vehicle is on a junction edge
        if edge in junction_edges:
            junction_id = edge_junction_map[edge]
            # Track vehicle direction when it exits the junction
            if vehid in bus_junction_track:
                last_junction, last_edge = bus_junction_track[vehid]
                if last_junction == junction_id and last_edge != edge:
                    exit_edge = edge 

                    # Vehicle has exited the junction
                    exit_angle = turnAngle
                    exit_direction = get_exit_direction(exit_angle)
                    print(f"Vehicle {vehid} exited junction {junction_id} to edge {exit_edge} with angle {exit_angle} degrees, direction: {exit_direction}")
                    bus_junction_track[vehid] = (junction_id, edge)
            else:
                bus_junction_track[vehid] = (junction_id, edge)

        # Packing all data for export to CSV, including junction exit info
        vehList = [
            getdatetime(), vehid, coord, gpscoord, spd, edge, lane, 
            displacement, turnAngle, nextTLS, junction_id,exit_edge, exit_angle, exit_direction
        ]

        # Track traffic light data
        tlsList = []
        for k in range(len(trafficlights)):
            if lane in traci.trafficlight.getControlledLanes(trafficlights[k]):
                tflight = trafficlights[k]
                tl_state = traci.trafficlight.getRedYellowGreenState(trafficlights[k])
                tl_phase_duration = traci.trafficlight.getPhaseDuration(trafficlights[k])
                tl_lanes_controlled = traci.trafficlight.getControlledLanes(trafficlights[k])
                tl_program = traci.trafficlight.getCompleteRedYellowGreenDefinition(trafficlights[k])
                tl_next_switch = traci.trafficlight.getNextSwitch(trafficlights[k])

                tlsList = [tflight, tl_state, tl_phase_duration, tl_lanes_controlled, tl_program, tl_next_switch]

        # Pack simulation data
        packBigDataLine = flatten_list([vehList, tlsList])
        packBigData.append(packBigDataLine)
      
    # Track Persons
    persons = traci.person.getIDList()
    for person_id in persons:
        person_pos = traci.person.getPosition(person_id)
        person_edge = traci.person.getRoadID(person_id)
        person_speed = traci.person.getSpeed(person_id)
        person_vehicle = traci.person.getVehicle(person_id)  # Get the vehicle ID if the person is riding a bus

        # Check if the person is boarding a bus
        if person_id not in personState:
            personState[person_id] = {"status": "walking", "vehicle": "", "last_edge": person_edge}

        current_status = personState[person_id]["status"]
        last_vehicle = personState[person_id]["vehicle"]

        # Boarding a bus
        if person_vehicle and current_status == "walking":
            personState[person_id] = {"status": "on_veh", "vehicle": person_vehicle, "last_edge": person_edge}
            packPersonData.append([
                getdatetime(), person_id, person_pos, person_edge, person_speed, person_vehicle, "Boarded Bus"
            ])
            print(f"Person {person_id} boarded {person_vehicle} at {getdatetime()} on edge {person_edge}.")

        # Alighting a bus
        elif not person_vehicle and current_status == "on_veh":
            personState[person_id] = {"status": "walking", "vehicle": "", "last_edge": person_edge}
            packPersonData.append([
                getdatetime(), person_id, person_pos, person_edge, person_speed, last_vehicle, "Alighted Bus"
            ])
            print(f"Person {person_id} alighted {last_vehicle} at {getdatetime()} on edge {person_edge}.")

        # Update status based on speed
        if person_speed == 0:
            # Person is not moving, so they are either waiting or standing still
            if current_status == "walking":
                current_status = "waiting"
        else:
            # Person is moving
            if current_status == "waiting":
                current_status = "walking"

        # Update the person's activity log even if there is no boarding or alighting
        packPersonData.append([
            getdatetime(), person_id, person_pos, person_edge, person_speed, person_vehicle, current_status
        ])


# Close SUMO
traci.close()

# Generate CSV file
vehicle_columns = [
    'dateandtime', 'vehid', 'coord', 'gpscoord', 'spd', 'edge', 'lane', 
    'displacement', 'turnAngle', 'nextTLS', 'junction_id','exit_edge', 'exit_angle', 'exit_direction',
    'tflight', 'tl_state', 'tl_phase_duration', 'tl_lanes_controlled', 
    'tl_program', 'tl_next_switch'
]
person_columns = ['dateandtime', 'person_id', 'position', 'current_edge', 'speed', 'vehicle', 'activity']

directory = 'SumoData'
if not os.path.exists(directory):
    os.makedirs(directory)

# Save Vehicle Data
dataset = pd.DataFrame(packBigData, columns=vehicle_columns)
dataset.to_csv(f'{directory}/vehicle_data.csv', index=False)

# Save Person Data
person_dataset = pd.DataFrame(packPersonData, index=None, columns=person_columns)
person_dataset.to_csv(f'{directory}/person_data.csv', index=False)
