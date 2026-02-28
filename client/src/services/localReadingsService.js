import readingsData from '../assets/extracted_readings.json';

// Create a map for faster lookup by date string (MMDDYY)
const readingsMap = new Map();
readingsData.forEach(item => {
  readingsMap.set(item.Date, item);
});

export const getLocalReading = (date) => {
  const d = new Date(date);
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  const year = String(d.getFullYear()).slice(-2);
  const dateKey = `${month}${day}${year}`;
  
  return readingsMap.get(dateKey);
};

export const getHolyDays = (year) => {
  const yearStr = String(year);
  return readingsData
    .filter(item => item.Year === yearStr && item['Holy Day of Obligation'] === true)
    .map(item => item.Date); // Returns MMDDYY strings
};

export const isHolyDayDate = (jsDate) => {
  const month = String(jsDate.getMonth() + 1).padStart(2, '0');
  const day = String(jsDate.getDate()).padStart(2, '0');
  const year = String(jsDate.getFullYear()).slice(-2); // YY
  const dateKey = `${month}${day}${year}`;
  
  const reading = readingsMap.get(dateKey);
  return reading ? reading['Holy Day of Obligation'] === true : false;
};

export const getAllReadings = () => {
    return readingsData;
};
