import axios from 'axios';

export const generateSingleRoute = async (lat: number, lng: number, length: number) => {
  const response = await axios.post('http://localhost:8080/generate-single', {
    startCoords: { lat, lon: lng },
    routeLength: length,
    routeType: "foot-walking"
  });
  return response.data;
};

export const generateRoute = async (markers: { lat: number; lon: number; }[], length: number) => {
  const response = await axios.post('http://localhost:8080/generate', {
    markers,
    length,
    route_type: "foot-walking"
  });
  return response.data;
};
