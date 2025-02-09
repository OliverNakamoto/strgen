import React from 'react';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import MainPage from './pages/MainPage';

const App: React.FC = () => {
  return (
    <>
      <MainPage />
      <ToastContainer />
    </>
  );
};

export default App;
