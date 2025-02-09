    import requests
from lxml import etree
import datetime
import random
import math
import numpy as np
from geopy.distance import geodesic
from geopy import Point
import matplotlib.pyplot as plt

# Configuration Parameters
AVG_MIN_PER_KM = 4
SECONDS_PER_KM = AVG_MIN_PER_KM * 60
AVG_SPEED = 1000 / SECONDS_PER_KM  # 4.166... m/s
ROUTE_LENGTH = 8000  # e.g., 8000 meters (8 km)

# Define average heart rate and cadence
AVG_BPM = 100  # Average heart rate in bpm
AVG_CADENCE = 80  # Average cadence in rpm

def fetch_round_trip_route(start_coords, api_key, route_length, num_points=5):
    """
    Fetches a round trip route from OpenRouteService API in GPX format.
    
    :param start_coords: Tuple of (longitude, latitude)
    :param api_key: OpenRouteService API key
    :param route_length: Desired length of the route in meters
    :param num_points: Number of via points to use in the route
    :return: GPX data as a string
    """
    url = ''
    # For cycling routes, uncomment the following line and comment out the above line
    # url = 'https://api.openrouteservice.org/v2/directions/cycling-road/gpx?gpxType=track'
    
    headers = {
        'Authorization': api_key,
        'Content-Type': 'application/json'
    }
    payload = {
        'coordinates': [list(start_coords)],
        'options': {
            'round_trip': {
                'length': route_length,
                'points': num_points
            }
        },
        'elevation': True,
        'instructions': False,
        'geometry_simplify': False
    }
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        print('GPX data fetched successfully.')
        return response.text
    else:
        raise Exception(f'Error fetching route: {response.status_code} - {response.text}')

def parse_gpx(gpx_data):
    """
    Parses the GPX data to extract coordinates and elevations.
    
    :param gpx_data: GPX data as a string
    :return: List of dictionaries with 'lat', 'lon', 'ele'
    """
    # Parse the GPX XML
    root = etree.fromstring(gpx_data.encode('utf-8'))
    
    # Find all rtept elements regardless of namespace
    rtepts = root.findall('.//{*}rtept')
    
    points = []
    for pt in rtepts:
        lat = pt.get('lat')
        lon = pt.get('lon')
        ele_elem = pt.find('{*}ele')
        ele_val = ele_elem.text if ele_elem is not None else '0'
        
        # Convert to float
        try:
            lat = float(lat)
            lon = float(lon)
            ele_val = float(ele_val)
        except ValueError:
            print(f"Invalid coordinate or elevation value: lat={lat}, lon={lon}, ele={ele_val}. Skipping point.")
            continue
        
        points.append({'lat': lat, 'lon': lon, 'ele': ele_val})
    
    print(f'Parsed {len(points)} track points from GPX data.')
    return points

def calculate_initial_compass_bearing(pointA, pointB):
    """
    Calculates the bearing between two points.
    
    :param pointA: tuple of (lat, lon)
    :param pointB: tuple of (lat, lon)
    :return: bearing in degrees
    """
    lat1 = math.radians(pointA[0])
    lat2 = math.radians(pointB[0])
    diffLong = math.radians(pointB[1] - pointA[1])

    x = math.sin(diffLong) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - (math.sin(lat1)
            * math.cos(lat2) * math.cos(diffLong))

    initial_bearing = math.atan2(x, y)

    # Convert from radians to degrees and normalize
    initial_bearing = math.degrees(initial_bearing)
    compass_bearing = (initial_bearing + 360) % 360

    return compass_bearing

def interpolate_points(p1, p2, speed_profile, total_time, current_time):
    """
    Interpolates points between p1 and p2 based on the speed profile.

    :param p1: Dictionary with 'lat', 'lon', 'ele'
    :param p2: Dictionary with 'lat', 'lon', 'ele'
    :param speed_profile: Numpy array of speeds for each second
    :param total_time: Total duration of the run in seconds
    :param current_time: Current timestamp in seconds
    :return: List of interpolated points
    """
    # Calculate the geodesic distance between p1 and p2
    point1 = (p1['lat'], p1['lon'])
    point2 = (p2['lat'], p2['lon'])
    distance = geodesic(point1, point2).meters

    # Determine the duration based on the speed at current_time
    speed = speed_profile[current_time]  # m/s
    duration = distance / speed  # in seconds
    num_seconds = int(duration)

    if num_seconds == 0:
        num_seconds = 1  # Ensure at least one interpolated point

    # Calculate elevation difference
    ele_diff = p2['ele'] - p1['ele']

    interpolated_points = []
    # Calculate initial bearing manually
    bearing = calculate_initial_compass_bearing(point1, point2)
    
    for i in range(1, num_seconds + 1):
        fraction = i / num_seconds
        # Calculate the destination point given the bearing and distance
        interpolated_distance = speed * i  # distance covered after i seconds
        interpolated_point = geodesic(meters=interpolated_distance).destination(Point(p1['lat'], p1['lon']), bearing)
        # Interpolate elevation
        interpolated_ele = p1['ele'] + (ele_diff * fraction)
        interpolated_points.append({
            'lat': interpolated_point.latitude,
            'lon': interpolated_point.longitude,
            'ele': interpolated_ele
        })
    return interpolated_points

def generate_timestamps(num_points, interval_seconds=1, start_time=None):
    """
    Generates a list of timestamps.
    
    :param num_points: Number of timestamps to generate
    :param interval_seconds: Seconds between each timestamp
    :param start_time: Starting datetime object
    :return: List of datetime objects
    """
    if start_time is None:
        start_time = datetime.datetime.utcnow()
    return [start_time + datetime.timedelta(seconds=i*interval_seconds) for i in range(num_points)]

# def create_speed_profile(total_seconds, avg_speed, speed_decrease=0.005):
#     """
#     Creates a smooth speed profile that slightly decreases over time.

#     :param total_seconds: Total duration of the run in seconds
#     :param avg_speed: Average speed in meters per second
#     :param speed_decrease: Total decrease in speed over the run
#     :return: Numpy array of speeds for each second
#     """
#     # Create a linear decrease with slight curvature using a polynomial
#     # Speed(t) = avg_speed - k * t^2, where k is a small coefficient
#     coefficients = np.polyfit([0, total_seconds], [avg_speed, avg_speed - speed_decrease], 2)
#     poly = np.poly1d(coefficients)
#     speed_profile = poly(np.arange(total_seconds))
    
#     # Ensure speed does not drop below 95% of avg_speed
#     min_speed = avg_speed * 0.90
#     speed_profile = np.maximum(speed_profile, min_speed)
    
#     return speed_profile


def create_speed_profile(total_seconds, avg_speed, speed_decrease=0.05):
    """
    Creates a smooth speed profile that slightly decreases over time with polynomial deviations.
    
    :param total_seconds: Total duration of the run in seconds
    :param avg_speed: Average speed in meters per second
    :param speed_decrease: Total decrease in speed over the run
    :return: Numpy array of speeds for each second
    """
    # Time points
    t = np.linspace(0, total_seconds, num=total_seconds)
    
    # Polynomial coefficients: Simulate some fluctuations around the average speed
    # We generate random small fluctuations and fit them into a polynomial of degree 10
    random_fluctuations = np.random.normal(loc=0, scale=1.8, size=total_seconds)
    random_fluctuations[0] = 0.2*avg_speed
    desired_speeds = avg_speed + random_fluctuations
    
    # Fit a polynomial of degree 10
    polynomial_coefficients = np.polyfit(t, desired_speeds, 10)
    polynomial = np.poly1d(polynomial_coefficients)
    
    # Polynomial values
    polynomial_values = polynomial(t)
    
    # Adding a linear decline to the polynomial values
    # Total decrease should be speed_decrease over total_seconds
    linear_decline = np.linspace(0, speed_decrease, total_seconds)
    speed_profile = polynomial_values - linear_decline
    
    # Ensure speed does not drop below 90% of avg_speed
    min_speed = avg_speed * 0.90
    speed_profile = np.maximum(speed_profile, min_speed)
    
     # Plotting the speed profile
    plot = True
    if plot:
        plt.figure(figsize=(10, 5))
        plt.plot(t, speed_profile, label='Speed Profile')
        plt.title('Speed Profile Over Time')
        plt.xlabel('Time (seconds)')
        plt.ylabel('Speed (m/s)')
        plt.grid(True)
        plt.axhline(y=avg_speed, color='r', linestyle='--', label='Average Speed')
        plt.axhline(y=min_speed, color='g', linestyle=':', label='Minimum Speed')
        plt.legend()
        plt.show()
    return speed_profile


def create_bpm_profile(total_seconds, avg_bpm, speed_profile, elevation_changes):
    """
    Creates a smooth BPM profile based on speed and elevation changes.

    :param total_seconds: Total duration of the run in seconds
    :param avg_bpm: Average heart rate in bpm
    :param speed_profile: Numpy array of speeds for each second
    :param elevation_changes: List of elevation changes per second
    :return: Numpy array of BPM values for each second
    """
    # Initialize BPM array
    bpm = np.zeros(total_seconds)
    
    # Start 20 BPM below average
    bpm[0] = avg_bpm - 20
    
    for t in range(1, total_seconds):
        # Smoothly increase BPM initially, then taper off
        # Using a sigmoid function for smooth increase
        progress = t / total_seconds
        sigmoid = 1 / (1 + np.exp(-12 * (progress - 0.2)))  # Shift sigmoid to start increasing at 20%
        
        # Base BPM increases from -20 to +0 relative to avg_bpm
        base_bpm = -20 + 20 * sigmoid
        
        # Adjust BPM based on speed
        speed_deviation = speed_profile[t] - AVG_SPEED
        bpm_speed = speed_deviation * 10  # Proportional to speed deviation
        
        # Adjust BPM based on elevation changes
        elevation_change = elevation_changes[t] if t < len(elevation_changes) else 0
        bpm_elevation = elevation_change * 8  # Proportional to elevation change
        
        # Total BPM with some randomness
        bpm_total = avg_bpm + base_bpm + bpm_speed + bpm_elevation + random.randint(-1, 1)
        
        # Clamp BPM to realistic values
        bpm_total = max(60, min(bpm_total, 200))
        
        bpm[t] = bpm_total
    
    return bpm

def create_cadence_profile(total_seconds, avg_cadence, speed_profile, elevation_changes):
    """
    Creates a smooth cadence profile based on speed and elevation changes.

    :param total_seconds: Total duration of the run in seconds
    :param avg_cadence: Average cadence in rpm
    :param speed_profile: Numpy array of speeds for each second
    :param elevation_changes: List of elevation changes per second
    :return: Numpy array of cadence values for each second
    """
    # Initialize Cadence array
    cad = np.zeros(total_seconds)
    
    # Start at average cadence with slight random fluctuation
    cad[0] = avg_cadence + random.randint(-1, 1)
    
    for t in range(1, total_seconds):
        # Base Cadence
        base_cad = 0  # Starts at average
        
        # Adjust Cadence based on speed
        speed_deviation = speed_profile[t] - AVG_SPEED
        cad_speed = speed_deviation * 3  # Proportional to speed deviation
        
        # Adjust Cadence based on elevation changes
        elevation_change = elevation_changes[t] if t < len(elevation_changes) else 0
        cad_elevation = elevation_change * 2  # Proportional to elevation change
        
        # Total Cadence with slight randomness
        cad_total = avg_cadence + base_cad + cad_speed + cad_elevation + random.randint(-1, 1)
        
        # Clamp Cadence to realistic values
        cad_total = max(30, min(cad_total, 150))
        
        cad[t] = cad_total
    
    return cad

def create_gpx(points, timestamps, gpx_filename='route_strava.gpx', route_length=8000, avg_speed=4.166, avg_bpm=100, avg_cadence=80, bpm_profile=None, cadence_profile=None):
    """
    Creates a GPX file with the given points and timestamps, including heart rate and cadence.
    
    :param points: List of dictionaries with 'lat', 'lon', 'ele'
    :param timestamps: List of datetime objects
    :param gpx_filename: Output GPX file name
    :param route_length: Total length of the route in meters
    :param avg_speed: Average speed in meters per second
    :param avg_bpm: Average heart rate in bpm
    :param avg_cadence: Average cadence in rpm
    :param bpm_profile: Numpy array of BPM values
    :param cadence_profile: Numpy array of cadence values
    """
    NSMAP = {
        None: "http://www.topografix.com/GPX/1/1",
        'ns3': "http://www.garmin.com/xmlschemas/TrackPointExtension/v1",
        'ns2': "http://www.garmin.com/xmlschemas/GpxExtensions/v3",
        'xsi': "http://www.w3.org/2001/XMLSchema-instance"
    }
    
    # Create root element
    gpx = etree.Element('gpx', nsmap=NSMAP, version="1.1", creator="Garmin Connect")
    gpx.set("{http://www.w3.org/2001/XMLSchema-instance}schemaLocation",
            "http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd "
            "http://www.garmin.com/xmlschemas/GpxExtensions/v3 http://www.garmin.com/xmlschemas/GpxExtensionsv3.xsd "
            "http://www.garmin.com/xmlschemas/TrackPointExtension/v1 http://www.garmin.com/xmlschemas/TrackPointExtensionv1.xsd")
    
    # Add metadata
    metadata = etree.SubElement(gpx, 'metadata')
    link = etree.SubElement(metadata, 'link', href="connect.garmin.com")
    text = etree.SubElement(link, 'text')
    text.text = "Garmin Connect"
    time_elem = etree.SubElement(metadata, 'time')
    time_elem.text = timestamps[0].isoformat() + 'Z'
    
    # Create track
    trk = etree.SubElement(gpx, 'trk')
    name = etree.SubElement(trk, 'name')
    name.text = "Generated Route"
    trk_type = etree.SubElement(trk, 'type')
    trk_type.text = "foot_walking"
    # For cycling routes, uncomment the following line
    # trk_type.text = "cycling-road"
    
    # Create track segment
    trkseg = etree.SubElement(trk, 'trkseg')
    
    total_seconds = len(points)
    
    for idx, (point, ts) in enumerate(zip(points, timestamps)):
        trkpt = etree.SubElement(trkseg, 'trkpt', lat=f"{point['lat']}", lon=f"{point['lon']}")
        
        # Elevation
        ele = etree.SubElement(trkpt, 'ele')
        ele.text = f"{point['ele']:.1f}"
        
        # Time
        time_point = etree.SubElement(trkpt, 'time')
        time_point.text = ts.isoformat() + 'Z'
        
        # Extensions
        extensions = etree.SubElement(trkpt, 'extensions')
        tpe = etree.SubElement(extensions, '{http://www.garmin.com/xmlschemas/TrackPointExtension/v1}TrackPointExtension')
        
        # Heart Rate
        hr_elem = etree.SubElement(tpe, '{http://www.garmin.com/xmlschemas/TrackPointExtension/v1}hr')
        hr_elem.text = str(int(bpm_profile[idx-2]))
        
        # # Cadence
        # cad_elem = etree.SubElement(tpe, '{http://www.garmin.com/xmlschemas/TrackPointExtension/v1}cad')
        # cad_elem.text = str(int(cadence_profile[idx]))
    
    # Create ElementTree and write to file
    tree = etree.ElementTree(gpx)
    tree.write(gpx_filename, pretty_print=True, xml_declaration=True, encoding='UTF-8')
    print(f'GPX file has been saved as {gpx_filename}')

def main():
    # Replace with your OpenRouteService API key
    API_KEY = ''  # Replace with your actual API key
        
    # Start coordinates (longitude, latitude)
    # Example coordinates in Oslo, Norway
    start_coords = (10.705898, 59.914428)
    
    # Define route length in meters
    route_length = ROUTE_LENGTH  # e.g., 8000 meters (8 km)
    
    # Fetch GPX data for a round trip
    try:
        gpx_data = fetch_round_trip_route(start_coords, API_KEY, route_length)
    except Exception as e:
        print(f'An error occurred while fetching GPX data: {e}')
        return
    
    # Parse GPX data to extract coordinates
    points = parse_gpx(gpx_data)
    
    if not points:
        print('No track points found in the route.')
        return
    
    # Estimate total time based on average speed
    total_time_seconds = int(route_length / AVG_SPEED)
    
    # Create speed profile
    total_time_seconds = int(total_time_seconds * 1.3)
    speed_profile = create_speed_profile(total_time_seconds, AVG_SPEED, speed_decrease=0.2)
    
    # Extract elevation changes per second (approximate)
    elevation_changes = []
    for i in range(len(points) - 1):
        ele_change = points[i + 1]['ele'] - points[i]['ele']
        # Distribute elevation change over the interpolated points
        distance = geodesic((points[i]['lat'], points[i]['lon']), (points[i + 1]['lat'], points[i + 1]['lon'])).meters
        num_seconds = int(distance / AVG_SPEED)
        for _ in range(num_seconds):
            elevation_changes.append(ele_change / num_seconds if num_seconds > 0 else 0)
    # Pad elevation_changes to match total_time_seconds
    if len(elevation_changes) < total_time_seconds:
        elevation_changes += [0] * (total_time_seconds - len(elevation_changes))
    else:
        elevation_changes = elevation_changes[:total_time_seconds]
    
    # Create BPM and Cadence profiles
    total_time_seconds = total_time_seconds - 2
    print(total_time_seconds)
    bpm_profile = create_bpm_profile(total_time_seconds, AVG_BPM, speed_profile, elevation_changes)
    cadence_profile = create_cadence_profile(total_time_seconds, AVG_CADENCE, speed_profile, elevation_changes)
    
    # Generate interpolated points based on speed profile
    interpolated_points = []
    current_time = 0
    for i in range(len(points) - 1):
        p1 = points[i]
        p2 = points[i + 1]
        new_points = interpolate_points(p1, p2, speed_profile, total_time_seconds, current_time)
        interpolated_points.extend(new_points)
        distance = geodesic((p1['lat'], p1['lon']), (p2['lat'], p2['lon'])).meters
        duration = int(distance / speed_profile[current_time] if speed_profile[current_time] > 0 else 1)
        current_time += duration
        if current_time >= total_time_seconds:
            break
    
    # Adjust profiles to match the number of interpolated points
    total_interpolated = len(interpolated_points)
    if total_interpolated > total_time_seconds:
        bpm_profile = bpm_profile[:total_interpolated]
        cadence_profile = cadence_profile[:total_interpolated]
    elif total_interpolated < total_time_seconds:
        # Only pad if total_interpolated is greater than the length of the profiles
        if total_interpolated > len(bpm_profile):
            bpm_profile = np.pad(bpm_profile, (0, total_interpolated - len(bpm_profile)), 'edge')
        if total_interpolated > len(cadence_profile):
            cadence_profile = np.pad(cadence_profile, (0, total_interpolated - len(cadence_profile)), 'edge')

        
        
        # bpm_profile = np.pad(bpm_profile, (0, total_interpolated - len(bpm_profile)), 'edge')
        # cadence_profile = np.pad(cadence_profile, (0, total_interpolated - len(cadence_profile)), 'edge')
    
    # Generate timestamps (one second apart)
    start_time = datetime.datetime(2024, 12, 2, 6, 5, 38)  # Example start time
    timestamps = generate_timestamps(len(interpolated_points), interval_seconds=1, start_time=start_time)
    
    if len(timestamps) != len(interpolated_points):
        print('Mismatch between number of timestamps and interpolated points.')
        return
    
    # Create the GPX file with bpm and cadence
    create_gpx(
        interpolated_points, 
        timestamps, 
        gpx_filename='route_strava.gpx',
        route_length=route_length,
        avg_speed=AVG_SPEED,
        avg_bpm=AVG_BPM,         # Set your desired average BPM
        avg_cadence=AVG_CADENCE, # Set your desired average cadence
        bpm_profile=bpm_profile,
        cadence_profile=cadence_profile
    )

if __name__ == "__main__":
    main()
