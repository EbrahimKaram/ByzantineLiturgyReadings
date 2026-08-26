// Fetches the pre-built Maronite calendar from the public/ folder (not bundled).
// Returns null for dates outside the covered range.

let calendarData = null;

const pad = (n) => String(n).padStart(2, '0');

const toDateKey = (date) => {
  const d = new Date(date);
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
};

const load = async () => {
  if (calendarData) return calendarData;
  // Served from public/ so Vite's base URL prefix applies
  const url = `${import.meta.env.BASE_URL}maronite_calendar.json`;
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`Failed to load Maronite calendar: ${resp.status}`);
  calendarData = await resp.json();
  return calendarData;
};

export const getMaroniteReadings = async (date) => {
  const calendar = await load();
  return calendar[toDateKey(date)] ?? null;
};
