import React, { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';

const SearchIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
  </svg>
);

const ClearIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
  </svg>
);

const SearchBar = ({ onSelectLocation }) => {
  const { t } = useTranslation();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const debounceRef = useRef(null);
  const wrapperRef = useRef(null);

  /* Close dropdown when clicking outside */
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  /* Debounced search using Mapbox Geocoding API */
  const handleSearch = (value) => {
    setQuery(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);

    if (value.length < 2) {
      setResults([]);
      setIsOpen(false);
      return;
    }

    debounceRef.current = setTimeout(async () => {
      setIsLoading(true);
      try {
        const token = import.meta.env.VITE_MAPBOX_TOKEN;
        /* Bias search towards Flores Island / NTT region */
        const bbox = '119.5,-9.5,123.5,-7.5';
        const url = `https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(value)}.json?access_token=${token}&bbox=${bbox}&limit=6&language=id,en`;
        const res = await fetch(url);
        const data = await res.json();
        setResults(data.features || []);
        setIsOpen(true);
      } catch (err) {
        console.error('Search failed:', err);
      } finally {
        setIsLoading(false);
      }
    }, 350);
  };

  const handleSelect = (feature) => {
    const [lng, lat] = feature.center;
    setQuery(feature.place_name);
    setIsOpen(false);
    onSelectLocation({ longitude: lng, latitude: lat, name: feature.place_name, zoom: 14 });
  };

  return (
    <div ref={wrapperRef} className="relative w-72">
      <div className="flex items-center bg-slate-100 dark:bg-slate-800 rounded-xl px-3 py-2 border border-transparent focus-within:border-cyan-500/50 focus-within:ring-2 focus-within:ring-cyan-500/20 transition-all">
        <span className="text-slate-400 dark:text-slate-500 mr-2 rtl:mr-0 rtl:ml-2 flex-shrink-0">
          {isLoading ? (
            <div className="w-4 h-4 border-2 border-slate-300 dark:border-slate-600 border-t-cyan-500 rounded-full animate-spin" />
          ) : (
            <SearchIcon />
          )}
        </span>
        <input
          type="text"
          value={query}
          onChange={(e) => handleSearch(e.target.value)}
          onFocus={() => results.length > 0 && setIsOpen(true)}
          placeholder={t('search.placeholder')}
          className="flex-1 bg-transparent text-sm text-slate-700 dark:text-slate-300 placeholder-slate-400 dark:placeholder-slate-600 focus:outline-none"
        />
        {query && (
          <button onClick={() => { setQuery(''); setResults([]); setIsOpen(false); }}
            className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 ml-1 rtl:ml-0 rtl:mr-1">
            <ClearIcon />
          </button>
        )}
      </div>

      {/* Results dropdown */}
      {isOpen && results.length > 0 && (
        <div className="absolute top-full mt-1 w-full bg-white dark:bg-slate-800 rounded-xl shadow-2xl border border-slate-200/60 dark:border-slate-700/60 overflow-hidden z-50 backdrop-blur-xl">
          {results.map((feature) => (
            <button
              key={feature.id}
              onClick={() => handleSelect(feature)}
              className="w-full text-left rtl:text-right px-4 py-3 hover:bg-slate-50 dark:hover:bg-slate-700/50 border-b border-slate-100 dark:border-slate-700/50 last:border-b-0 transition-colors"
            >
              <p className="text-sm font-medium text-slate-800 dark:text-slate-200 truncate">
                {feature.text}
              </p>
              <p className="text-[11px] text-slate-400 dark:text-slate-500 truncate mt-0.5">
                {feature.place_name}
              </p>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default SearchBar;
