import React, { useState } from 'react';
import MapComponent from '../components/MapComponent';
import InputForm from '../components/InputForm';
import { toast } from 'react-toastify';
import { generateSingleRoute, generateRoute } from '../services/api';
import RouteAnalysisPopup from '../components/RouteAnalysisPopup';

interface MarkerData {
  position: { lat: number; lng: number };
  address: string;
}

interface GPXDataResult {
  timestamps: string[];
  bpmProfile: number[];
  paceProfile: number[];
  route: { lat: number; lon: number; ele: number; }[];
}

const MainPage: React.FC = () => {
  const [markers, setMarkers] = useState<MarkerData[]>([]);
  const [speed, setSpeed] = useState<number>(50); // Default speed
  const [otherData, setOtherData] = useState<string>('');
  const [processedData, setProcessedData] = useState<GPXDataResult | null>(null);
  const [route, setRoute] = useState<{ lat: number; lng: number }[] | null>(null);
  const [showPopup, setShowPopup] = useState(false);

  const handleProcessRouteSingle = async () => {
    if (markers.length < 1) {
      toast.error('Please place at least one marker on the map.');
      return;
    }

    try {
      const data = await generateSingleRoute(markers[0].position.lat, markers[0].position.lng, 8000);
      console.log(data);
      setProcessedData(data);
      setShowPopup(true);
      // If the backend returns route coordinates separately, set them:
      // setRoute(data.route.map(coord => ({ lat: coord.lat, lng: coord.lon })));
    } catch (error) {
      toast.error('Server is down. Please try again later.');
      console.error('Error processing route:', error);
    }
  };

  const handleProcessRoute = async () => {
    if (markers.length < 1) {
      toast.error('Please place at least one marker on the map.');
      return;
    }
    if (markers.length > 100) {
      toast.error('Please place fewer than 100 markers on the map.');
      return;
    }

    try {
      const data = await generateRoute(
        markers.map((m) => ({ lat: m.position.lat, lon: m.position.lng })),
        10
      );
      console.log(data);
      setProcessedData(data);
      setShowPopup(true);
      // If needed, setRoute(data.route.map(coord => ({ lat: coord.lat, lng: coord.lon })));
    } catch (error) {
      toast.error('Server is down. Please try again later.');
      console.error('Error processing route:', error);
    }
  };

  return (
    <div className="p-5 h-screen">
      <h1 className="text-2xl font-bold mb-5">Ultimate Strava Jockey</h1>
      <div className="flex mb-5 h-full">
        <div className="flex-3 mr-5 w-3/4 h-full">
          <MapComponent markers={markers} setMarkers={setMarkers} route={route} />
        </div>
        <div className="flex-1 h-full">
          <InputForm
            speed={speed}
            setSpeed={setSpeed}
            otherData={otherData}
            setOtherData={setOtherData}
          />
          <button 
            onClick={handleProcessRouteSingle} 
            className="mt-5 bg-blue-500 text-white py-2 px-4 rounded"
          >
            Generate route
          </button>
        </div>
      </div>
      {processedData && showPopup && (
        <RouteAnalysisPopup data={processedData} closePopup={() => setShowPopup(false)} />
      )}
    </div>
  );
};

export default MainPage;
