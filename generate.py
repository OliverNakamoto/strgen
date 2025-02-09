import requests

# Replace with your OpenRouteService API key
API_KEY = '' #'YOUR_API_KEY_HERE'

# Start and end coordinates (longitude, latitude)
start_coords = [-73.989308, 40.741895]
end_coords = [-73.98825211353483, 40.723659147272066]

# OpenRouteService API endpoint for directions in GPX format with gpxType=track
url = ''

# Headers including the API key
headers = {
    'Authorization': API_KEY,
    'Content-Type': 'application/json'
}

# Build the request payload
payload = {
    'coordinates': [start_coords, end_coords],
    'elevation': True,
    'instructions': False,
    'geometry_simplify': False
}

# Make the POST request to the API
response = requests.post(url, json=payload, headers=headers)

# Check if the request was successful
if response.status_code == 200:
    # Save the GPX data to a file
    with open('route.gpx', 'w') as file:
        file.write(response.text)
    print('GPX file has been saved as route.gpx')
else:
    print(f'Error: {response.status_code} - {response.text}')
