import React, { useState, useRef, useEffect, useCallback } from 'react';
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

/* One glyph per OSM category, so a mosque does not look like a village. */
const CATEGORY_ICON = {
  place_of_worship: '🕌',
  mosque: '🕌',
  church: '⛪',
  school: '🏫',
  college: '🏫',
  university: '🏫',
  hospital: '🏥',
  clinic: '🏥',
  pharmacy: '💊',
  marketplace: '🏪',
  shop: '🏪',
  restaurant: '🍽️',
  fuel: '⛽',
  village: '🏘️',
  hamlet: '🏘️',
  town: '🏙️',
  city: '🏙️',
  suburb: '🏘️',
  island: '🏝️',
  peak: '⛰️',
  volcano: '🌋',
  water: '💧',
  spring: '💧',
  house: '🏠',
  yes: '🏠',
  grave_yard: '🪦',
  aerodrome: '✈️',
};

const iconFor = (category) => CATEGORY_ICON[category] || '📍';

const SearchBar = ({ onSelectLocation }) => {
  const { t } = useTranslation();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const debounceRef = useRef(null);
  const requestIdRef = useRef(0);
  const wrapperRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) setIsOpen(false);
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  /* One search path for both the as-you-type suggestions and the Enter key.
     The server queries a geocoder and OpenStreetMap at the same time, so a
     mosque or a single named building comes back, not only settlements. */
  const runSearch = useCallback(async (value) => {
    const text = value.trim();
    if (text.length < 2) return;
    const id = ++requestIdRef.current;
    setIsLoading(true);
    try {
      const baseUrl = import.meta.env.VITE_API_BASE_URL || '';
      const res = await fetch(`${baseUrl}/api/geo/search?q=${encodeURIComponent(text)}&limit=12`);
      const data = await res.json();
      if (id !== requestIdRef.current) return; // a newer keystroke won
      setResults(data.results || []);
      setSearched(true);
      setActiveIndex(-1);
      setIsOpen(true);
    } catch (err) {
      console.error('Search failed:', err);
      if (id === requestIdRef.current) {
        setResults([]);
        setSearched(true);
        setIsOpen(true);
      }
    } finally {
      if (id === requestIdRef.current) setIsLoading(false);
    }
  }, []);

  const handleChange = (value) => {
    setQuery(value);
    setSearched(false);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (value.trim().length < 2) {
      setResults([]);
      setIsOpen(false);
      return;
    }
    debounceRef.current = setTimeout(() => runSearch(value), 450);
  };

  const handleSelect = (item) => {
    setQuery(item.name);
    setIsOpen(false);
    onSelectLocation({
      longitude: item.lon,
      latitude: item.lat,
      name: item.name,
      zoom: 16,
    });
  };

  /* Enter searches immediately and jumps to the top hit — the way a map
     search is expected to behave, without hunting through suggestions. */
  const handleKeyDown = async (e) => {
    if (e.key === 'Escape') { setIsOpen(false); return; }
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveIndex(i => Math.min(i + 1, results.length - 1));
      return;
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveIndex(i => Math.max(i - 1, -1));
      return;
    }
    if (e.key !== 'Enter') return;

    e.preventDefault();
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (activeIndex >= 0 && results[activeIndex]) {
      handleSelect(results[activeIndex]);
      return;
    }
    const id = ++requestIdRef.current;
    setIsLoading(true);
    try {
      const baseUrl = import.meta.env.VITE_API_BASE_URL || '';
      const res = await fetch(`${baseUrl}/api/geo/search?q=${encodeURIComponent(query.trim())}&limit=12`);
      const data = await res.json();
      if (id !== requestIdRef.current) return;
      const hits = data.results || [];
      setResults(hits);
      setSearched(true);
      if (hits.length > 0) {
        handleSelect(hits[0]);
        setIsOpen(true);
      } else {
        setIsOpen(true);
      }
    } catch (err) {
      console.error('Search failed:', err);
    } finally {
      if (id === requestIdRef.current) setIsLoading(false);
    }
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
          onChange={(e) => handleChange(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => (results.length > 0 || searched) && setIsOpen(true)}
          placeholder={t('search.placeholder')}
          className="flex-1 bg-transparent text-sm text-slate-700 dark:text-slate-300 placeholder-slate-400 dark:placeholder-slate-600 focus:outline-none"
        />
        {query && (
          <button
            onClick={() => { setQuery(''); setResults([]); setSearched(false); setIsOpen(false); }}
            aria-label={t('search.clear', 'مسح')}
            className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 ml-1 rtl:ml-0 rtl:mr-1"
          >
            <ClearIcon />
          </button>
        )}
      </div>

      {isOpen && (
        <div className="absolute top-full mt-1 w-full max-h-80 overflow-y-auto bg-white dark:bg-slate-800 rounded-xl shadow-2xl border border-slate-200/60 dark:border-slate-700/60 z-50">
          {results.length > 0 ? (
            results.map((item, i) => (
              <button
                key={`${item.name}-${item.lat}-${item.lon}`}
                onClick={() => handleSelect(item)}
                onMouseEnter={() => setActiveIndex(i)}
                className={`w-full text-left rtl:text-right px-3 py-2.5 flex items-start gap-2.5 border-b border-slate-100 dark:border-slate-700/50 last:border-b-0 transition-colors ${
                  i === activeIndex ? 'bg-slate-100 dark:bg-slate-700/60' : 'hover:bg-slate-50 dark:hover:bg-slate-700/40'
                }`}
              >
                <span className="text-base leading-5 shrink-0">{iconFor(item.category)}</span>
                <span className="min-w-0 flex-1">
                  <span className="block text-sm font-medium text-slate-800 dark:text-slate-200 truncate">
                    {item.name}
                  </span>
                  <span className="block text-[11px] text-slate-400 dark:text-slate-500 truncate mt-0.5">
                    {item.label || item.category}
                    {!item.in_region && ` · ${t('search.outsideRegion', 'خارج نطاق فلوريس')}`}
                  </span>
                </span>
              </button>
            ))
          ) : (
            !isLoading && searched && (
              <p className="px-4 py-3 text-[12px] leading-relaxed text-slate-500 dark:text-slate-400">
                {t('search.noResults')}
              </p>
            )
          )}
        </div>
      )}
    </div>
  );
};

export default SearchBar;
