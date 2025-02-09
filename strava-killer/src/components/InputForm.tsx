import React from 'react';

interface InputFormProps {
  speed: number;
  setSpeed: React.Dispatch<React.SetStateAction<number>>;
  otherData: string;
  setOtherData: React.Dispatch<React.SetStateAction<string>>;
}

const InputForm: React.FC<InputFormProps> = ({ speed, setSpeed, otherData, setOtherData }) => {
  return (
    <div>
      <h2>Input Parameters</h2>
      <div>
        <label>
          Average Speed (km/h):
          <input
            type='number'
            value={speed}
            onChange={(e) => setSpeed(Number(e.target.value))}
            min='0'
          />
        </label>
      </div>
      <div>
        <label>
          Other Data:
          <input
            type='text'
            value={otherData}
            onChange={(e) => setOtherData(e.target.value)}
          />
        </label>
      </div>
    </div>
  );
};

export default InputForm;
