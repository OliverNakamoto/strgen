import React, { useState, useEffect } from 'react';
import './ShiftingTitle.css'; // Import the CSS for animations

interface ShiftingTitleProps {
  titles: string[];
  interval?: number; // Time between title changes in ms (default: 4000)
}

const ShiftingTitle: React.FC<ShiftingTitleProps> = ({ titles, interval = 4000 }) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [fade, setFade] = useState(true);

  useEffect(() => {
    const fadeOutTimeout = setTimeout(() => setFade(false), interval - 1000);
    const changeTitleTimeout = setTimeout(() => {
      setCurrentIndex((prevIndex) => (prevIndex + 1) % titles.length);
      setFade(true);
    }, interval);

    return () => {
      clearTimeout(fadeOutTimeout);
      clearTimeout(changeTitleTimeout);
    };
  }, [currentIndex, titles.length, interval]);

  return (
    <h2 className={`shifting-title ${fade ? 'fade-in' : 'fade-out'}`}>
      {titles[currentIndex]}
    </h2>
  );
};

export default ShiftingTitle;
