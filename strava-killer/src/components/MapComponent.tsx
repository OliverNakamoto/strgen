import React, { useRef, useEffect, useState } from 'react';
import Map from 'ol/Map';
import View from 'ol/View';
import { fromLonLat, toLonLat } from 'ol/proj';
import TileLayer from 'ol/layer/Tile';
import OSM from 'ol/source/OSM';
import Feature from 'ol/Feature';
import { Point, LineString } from 'ol/geom';
import VectorLayer from 'ol/layer/Vector';
import VectorSource from 'ol/source/Vector';
import { Icon, Style, Stroke, Text } from 'ol/style';
import 'ol/ol.css';

interface Coordinate {
  lat: number;
  lng: number;
}

interface MarkerData {
  position: Coordinate;
  address: string;
}

interface MapProps {
  markers: MarkerData[];
  setMarkers: React.Dispatch<React.SetStateAction<MarkerData[]>>;
  route: Coordinate[] | null;
}

const MapComponent: React.FC<MapProps> = ({ markers, setMarkers, route }) => {
  const mapElement = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<Map | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  const [markerLayer, setMarkerLayer] = useState<VectorLayer<VectorSource>>();
  const [routeLayer, setRouteLayer] = useState<VectorLayer<VectorSource>>();

  useEffect(() => {
    if (mapRef.current || !mapElement.current) return;

    const markersSource = new VectorSource();
    const initialMarkerLayer = new VectorLayer({ source: markersSource });

    const routeSource = new VectorSource();
    const initialRouteLayer = new VectorLayer({ source: routeSource });

    const map = new Map({
      target: mapElement.current,
      layers: [
        new TileLayer({ source: new OSM() }),
        initialMarkerLayer,
        initialRouteLayer,
      ],
      view: new View({
        center: fromLonLat([0, 0]),
        zoom: 2,
      }),
    });

    // Click Event to place markers
    map.on('singleclick', (event) => {
      const coordinate = event.coordinate;
      const [lng, lat] = toLonLat(coordinate);

      fetch(`https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lng}&format=json`)
        .then((response) => response.json())
        .then((data) => {
          const address = data.display_name || 'Unknown location';
          setMarkers((prevMarkers) => [
            ...prevMarkers,
            { position: { lat, lng }, address },
          ]);
        })
        .catch((error) => {
          console.error('Error fetching address:', error);
          setMarkers((prevMarkers) => [
            ...prevMarkers,
            { position: { lat, lng }, address: 'Unknown location' },
          ]);
        });
    });

    mapRef.current = map;
    setMarkerLayer(initialMarkerLayer);
    setRouteLayer(initialRouteLayer);
  }, [setMarkers]);

  // Update Markers
  useEffect(() => {
    if (!markerLayer) return;

    const features = markers.map((marker, index) => {
      const feature = new Feature({
        geometry: new Point(fromLonLat([marker.position.lng, marker.position.lat])),
        name: marker.address,
      });
      feature.setStyle(
        new Style({
          image: new Icon({
            src: 'https://maps.google.com/mapfiles/ms/icons/red-dot.png',
            anchor: [0.5, 1],
          }),
          text: new Text({
            text: (index + 1).toString(),
            offsetY: -25,
            fill: new Stroke({ color: '#000', width: 2 }),
            stroke: new Stroke({ color: '#fff', width: 3 }),
          }),
        })
      );
      return feature;
    });

    markerLayer.getSource().clear();
    markerLayer.getSource().addFeatures(features);
  }, [markers, markerLayer]);

  // Update Route
  useEffect(() => {
    if (!routeLayer) return;

    routeLayer.getSource().clear();

    if (route) {
      const coordinates = route.map((coord) => fromLonLat([coord.lng, coord.lat]));
      const lineFeature = new Feature({
        geometry: new LineString(coordinates),
      });
      lineFeature.setStyle(
        new Style({
          stroke: new Stroke({
            color: 'blue',
            width: 3,
          }),
        })
      );
      routeLayer.getSource().addFeature(lineFeature);
    }
  }, [route, routeLayer]);

  const handleGoToMyLocation = () => {
    if (navigator.geolocation && mapRef.current) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const { latitude, longitude } = position.coords;
          mapRef.current!.getView().animate({
            center: fromLonLat([longitude, latitude]),
            zoom: 13,
            duration: 1000,
          });
        },
        (error) => {
          console.error('Error getting location:', error);
          alert('Unable to retrieve your location.');
        }
      );
    } else {
      alert('Geolocation is not supported by this browser.');
    }
  };

  const handleSearch = () => {
    if (!searchQuery || !mapRef.current) return;

    fetch(`https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(searchQuery)}&format=json&limit=1`)
      .then((response) => response.json())
      .then((data) => {
        if (data && data.length > 0) {
          const { lat, lon } = data[0];
          const latitude = parseFloat(lat);
          const longitude = parseFloat(lon);
          mapRef.current!.getView().animate({
            center: fromLonLat([longitude, latitude]),
            zoom: 13,
            duration: 1000,
          });
        } else {
          alert('Location not found.');
        }
      })
      .catch((error) => {
        console.error('Error searching location:', error);
        alert('Error searching location.');
      });
  };

  const handleClearMarkers = () => {
    setMarkers([]);
    if (markerLayer) markerLayer.getSource().clear();
    if (routeLayer) routeLayer.getSource().clear();
  };

  return (
    <div className='relative'>
    {/* Decrease the z-index here to ensure popup overlays this */}
    <div className='absolute top-4 left-4 z-10 flex flex-col space-y-2'> 
        <button
        onClick={handleGoToMyLocation}
        className='px-4 py-2 bg-blue-500 text-white rounded shadow hover:bg-blue-600'
        >
        Go to My Location
        </button>

        <div className='flex space-x-2'>
        <input
            type='text'
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder='Search location'
            className='px-2 py-1 border rounded w-48'
        />
        <button
            onClick={handleSearch}
            className='px-4 py-2 bg-green-500 text-white rounded shadow hover:bg-green-600'
        >
            Search
        </button>
        </div>

        <button
        onClick={handleClearMarkers}
        className='px-4 py-2 bg-red-500 text-white rounded shadow hover:bg-red-600'
        >
        Clear Markers
        </button>
    </div>

    <div
        ref={mapElement}
        className='map-container'
        style={{ height: '600px', width: '70vw' }}
    ></div>
    </div>

    );
    };

export default MapComponent;
