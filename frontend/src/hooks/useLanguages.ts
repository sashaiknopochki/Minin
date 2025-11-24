import { useState, useEffect } from 'react';
import type { Language, LanguagesResponse } from '@/types/language';

const CACHE_KEY = 'minin_languages';
const CACHE_DURATION = 24 * 60 * 60 * 1000; // 24 hours in milliseconds

interface CachedData {
  timestamp: number;
  languages: Language[];
}

export function useLanguages() {
  const [languages, setLanguages] = useState<Language[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchLanguages = async () => {
      try {
        // Check localStorage cache first
        const cached = localStorage.getItem(CACHE_KEY);

        if (cached) {
          const cachedData: CachedData = JSON.parse(cached);
          const now = Date.now();

          // Use cache if it's less than 24 hours old
          if (now - cachedData.timestamp < CACHE_DURATION) {
            setLanguages(cachedData.languages);
            setLoading(false);
            return;
          }
        }

        // Fetch from API if no cache or cache expired
        // Uses relative URL - Vite proxy will forward to Flask backend
        const response = await fetch('/api/languages');

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data: LanguagesResponse = await response.json();

        if (data.success && data.data) {
          setLanguages(data.data);

          // Cache the result
          const cacheData: CachedData = {
            timestamp: Date.now(),
            languages: data.data,
          };
          localStorage.setItem(CACHE_KEY, JSON.stringify(cacheData));
        } else {
          throw new Error('Invalid response format');
        }

        setLoading(false);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch languages');
        setLoading(false);
      }
    };

    fetchLanguages();
  }, []);

  // Function to manually clear cache (useful for dev/testing)
  const clearCache = () => {
    localStorage.removeItem(CACHE_KEY);
  };

  return { languages, loading, error, clearCache };
}
