import React from 'react';
import StaticMap from './StaticMap';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  TimeScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
} from 'chart.js';
import 'chartjs-adapter-date-fns';
import ShiftingTitle from './ShiftingTitle'; // Import the ShiftingTitle component

ChartJS.register(
  CategoryScale,
  LinearScale,
  TimeScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend
);

interface GPXDataResult {
  timestamps: string[]; // ISO strings
  bpmProfile: number[];
  paceProfile: number[];
  route: {
    lat: number;
    lon: number;
    ele: number;
  }[];
}

interface RouteAnalysisPopupProps {
  data: GPXDataResult;
  closePopup: () => void;
}

const RouteAnalysisPopup: React.FC<RouteAnalysisPopupProps> = ({ data, closePopup }) => {
  // Ensure all data arrays are the same length
  const minLength = Math.min(data.timestamps.length, data.bpmProfile.length, data.paceProfile.length);
  const sanitizedTimestamps = data.timestamps.slice(0, minLength);
  const sanitizedBPM = data.bpmProfile.slice(0, minLength);
  const sanitizedPace = data.paceProfile.slice(0, minLength);

  // Prepare data in { x: Date, y: value } format
  const bpmDataPoints = sanitizedTimestamps.map((timestamp, index) => ({
    x: new Date(timestamp),
    y: sanitizedBPM[index],
  }));

  const paceDataPoints = sanitizedTimestamps.map((timestamp, index) => ({
    x: new Date(timestamp),
    y: sanitizedPace[index],
  }));

  // Chart configurations
  const bpmChartData = {
    datasets: [
      {
        label: 'BPM',
        data: bpmDataPoints,
        borderColor: 'red',
        backgroundColor: 'rgba(255, 0, 0, 0.1)',
        borderWidth: 2,
        pointRadius: 0,
        fill: true,
        tension: 0.3,
      },
    ],
  };

  const paceChartData = {
    datasets: [
      {
        label: 'Pace (min/km)',
        data: paceDataPoints,
        borderColor: 'blue',
        backgroundColor: 'rgba(0, 0, 255, 0.1)',
        borderWidth: 2,
        pointRadius: 0,
        fill: true,
        tension: 0.3,
      },
    ],
  };

  const commonOptions = {
    responsive: true,
    maintainAspectRatio: false as const,
    plugins: {
      legend: {
        display: false,
      },
      tooltip: {
        mode: 'nearest' as const,
        intersect: false,
        backgroundColor: 'rgba(0,0,0,0.7)',
        titleColor: '#fff',
        bodyColor: '#fff',
        callbacks: {
          label: function (context: any) {
            return `${context.dataset.label}: ${context.parsed.y}`;
          },
        },
      },
    },
    scales: {
      x: {
        type: 'time' as const,
        time: {
          unit: 'minute',
          displayFormats: {
            minute: 'HH:mm',
            second: 'HH:mm:ss',
          },
          tooltipFormat: 'PPpp', // Pretty print format
        },
        ticks: {
          color: '#555',
          autoSkip: true,
          maxTicksLimit: 10,
        },
        grid: {
          display: false,
        },
      },
      y: {
        beginAtZero: false,
        ticks: {
          color: '#555',
        },
        grid: {
          display: false,
        },
      },
    },
  };

  // Titles to cycle through
  const titles = [
    'Evening Run',
    'Morning Run',
    'Chill Run around the Block',
    'Sunset Sprint',
    'Night Jog',
    'Weekend Long Run',
  ];

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex justify-center items-center">
      <div className="bg-white w-11/12 h-5/6 rounded-lg overflow-auto flex flex-col relative">
        {/* Shifting Title */}
        <ShiftingTitle titles={titles} interval={4000} />

        <div className="flex justify-end p-4">
          <button
            onClick={closePopup}
            className="text-black text-2xl font-bold hover:text-gray-700"
            aria-label="Close"
          >
            &times;
          </button>
        </div>
        <div className="flex-1 overflow-auto p-4 space-y-6">
          {/* Map Section */}
          <div className="h-80">
            <StaticMap route={data.route} />
          </div>

          {/* Charts Section */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* BPM Chart */}
            <div className="bg-gray-100 p-4 rounded-lg shadow">
              <h2 className="text-lg font-semibold mb-2">BPM over Time</h2>
              <div className="h-64">
                <Line data={bpmChartData} options={commonOptions} />
              </div>
            </div>

            {/* Pace Chart */}
            <div className="bg-gray-100 p-4 rounded-lg shadow">
              <h2 className="text-lg font-semibold mb-2">Pace over Time</h2>
              <div className="h-64">
                <Line data={paceChartData} options={commonOptions} />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RouteAnalysisPopup;
