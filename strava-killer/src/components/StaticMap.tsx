import React, { useEffect, useRef } from 'react';
import Map from 'ol/Map';
import View from 'ol/View';
import { fromLonLat } from 'ol/proj';
import TileLayer from 'ol/layer/Tile';
import OSM from 'ol/source/OSM';
import { LineString } from 'ol/geom';
import { Feature } from 'ol';
import VectorSource from 'ol/source/Vector';
import VectorLayer from 'ol/layer/Vector';
import { Stroke, Style } from 'ol/style';

interface Coordinate {
  lat: number;
  lon: number;
  ele: number;
}

interface StaticMapProps {
  route: Coordinate[];
}

const StaticMap: React.FC<StaticMapProps> = ({ route }) => {
  const mapRef = useRef<Map | null>(null);
  const mapElement = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!mapElement.current) return;
    if (mapRef.current) return; // Only initialize once

    const baseLayer = new TileLayer({
      source: new OSM(),
    });

    const map = new Map({
      target: mapElement.current,
      layers: [baseLayer],
      view: new View({
        center: fromLonLat([0,0]),
        zoom: 2,
      }),
      controls: [],
      interactions: [],
    });

    mapRef.current = map;
  }, []);

  useEffect(() => {
    if (!mapRef.current || route.length === 0) return;

    // Remove previous route layers if any
    const layers = mapRef.current.getLayers().getArray();
    const vectorLayers = layers.filter((l) => l instanceof VectorLayer);
    vectorLayers.forEach((vl) => mapRef.current?.removeLayer(vl));

    // Convert route to coordinates in lon/lat
    const coords = route.map(r => fromLonLat([r.lon, r.lat]));

    const line = new LineString(coords);

    const routeFeature = new Feature({ geometry: line });
    routeFeature.setStyle(
      new Style({
        stroke: new Stroke({
          color: 'red',
          width: 3,
        }),
      })
    );

    const routeSource = new VectorSource({
      features: [routeFeature],
    });

    const routeLayer = new VectorLayer({
      source: routeSource,
    });

    mapRef.current.addLayer(routeLayer);

    // Adjust view to fit route
    const extent = routeSource.getExtent();
    mapRef.current.getView().fit(extent, { padding: [20,20,20,20] });

  }, [route]);

  return <div ref={mapElement} style={{ width: '100%', height: '100%' }} />;
};

export default StaticMap;
