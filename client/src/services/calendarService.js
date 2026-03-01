import axios from 'axios';

const CALENDAR_ID = '9pp7p6nos1t3tca6sjo4g6hui0@group.calendar.google.com';
const API_KEY = import.meta.env.VITE_GOOGLE_API_KEY;
const BASE_URL = 'https://www.googleapis.com/calendar/v3/calendars';
const CACHE_TTL_MS = 24 * 60 * 60 * 1000;

// Simple in-memory cache to fallback if localStorage fails or for quick access
const memoryCache = new Map();

const getCacheKey = (dateStr) => `calendar_events_${dateStr}`;

const isFreshCacheEntry = (entry) => {
  if (!entry || typeof entry !== 'object') return false;
  if (typeof entry.cachedAt !== 'number') return false;
  return Date.now() - entry.cachedAt < CACHE_TTL_MS;
};

export const fetchSundayReadings = async (date) => {
  if (!API_KEY) {
    throw new Error('Google API Key is missing. Please set VITE_GOOGLE_API_KEY in your .env file.');
  }

  // Set time range for the given date (Sunday)
  const timeMin = new Date(date);
  timeMin.setHours(0, 0, 0, 0);
  
  const timeMax = new Date(date);
  timeMax.setHours(23, 59, 59, 999);

  const dateStr = timeMin.toISOString().split('T')[0];
  const cacheKey = getCacheKey(dateStr);

  // 1. Check Cache
  try {
    const cached = localStorage.getItem(cacheKey);
    if (cached) {
      const parsed = JSON.parse(cached);

      if (isFreshCacheEntry(parsed)) {
        return parsed.value;
      }

      localStorage.removeItem(cacheKey);
    }
  } catch (e) {
    // LocalStorage might be disabled or full
    if (memoryCache.has(cacheKey)) {
      const memoryEntry = memoryCache.get(cacheKey);
      if (isFreshCacheEntry(memoryEntry)) {
        return memoryEntry.value;
      }

      memoryCache.delete(cacheKey);
    }
  }

  try {
    const response = await axios.get(`${BASE_URL}/${encodeURIComponent(CALENDAR_ID)}/events`, {
      params: {
        key: API_KEY,
        timeMin: timeMin.toISOString(),
        timeMax: timeMax.toISOString(),
        singleEvents: true,
        orderBy: 'startTime',
      },
    });

    const items = response.data.items;
    const cachePayload = { cachedAt: Date.now(), value: items };

    // 2. Save to Cache
    try {
      localStorage.setItem(cacheKey, JSON.stringify(cachePayload));
    } catch (e) {
      console.warn('Failed to save to localStorage:', e);
      memoryCache.set(cacheKey, cachePayload);
    }

    return items;
  } catch (error) {
    console.error('Error fetching calendar events:', error);
    throw error;
  }
};

