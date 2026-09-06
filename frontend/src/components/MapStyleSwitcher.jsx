import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';

const MAP_STYLES = [
  {
    id: 'google-hybrid',
    style: {
      version: 8,
      sources: {
        'google-hybrid': {
          type: 'raster',
          tiles: ['https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}'],
          tileSize: 256,
        },
      },
      layers: [
        {
          id: 'google-hybrid-layer',
          type: 'raster',
          source: 'google-hybrid',
          paint: {},
        },
      ],
    },
    icon: '🌍',
    labelKey: 'Google Satellite',
  },
  {
    id: 'google-streets',
    style: {
      version: 8,
      sources: {
        'google-streets': {
          type: 'raster',
          tiles: ['https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}'],
          tileSize: 256,
        },
      },
      layers: [
        {
          id: 'google-streets-layer',
          type: 'raster',
          source: 'google-streets',
          paint: {},
        },
      ],
    },
    icon: '🗺️',
    labelKey: 'Google Maps',
  },
  {
    id: 'streets',
    style: 'mapbox://styles/mapbox/streets-v12',
    icon: '🏘️',
    labelKey: 'mapStyles.streets',
  },
  {
    id: 'satellite',
    style: 'mapbox://styles/mapbox/satellite-streets-v12',
    icon: '🛰️',
    labelKey: 'mapStyles.satellite',
  },
  {
    id: 'terrain',
    style: 'mapbox://styles/mapbox/outdoors-v12',
    icon: '⛰️',
    labelKey: 'mapStyles.terrain',
  },
];

const LayersIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>
  </svg>
);

const MapStyleSwitcher = ({ currentStyle, onStyleChange, isSidebarOpen }) => {
  const { t } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);

  const currentStyleObj = MAP_STYLES.find(s => 
    (typeof currentStyle === 'string' && s.style === currentStyle) ||
    (typeof currentStyle === 'object' && typeof s.style === 'object' && s.id === 'google-hybrid')
  ) || MAP_STYLES[0];

  return (
    <div 
      className={`absolute top-4 z-10 transition-all duration-300 ease-in-out ${
        isSidebarOpen 
          ? 'left-80 rtl:left-auto rtl:right-80 ml-4 rtl:ml-0 rtl:mr-4' 
          : 'left-4 rtl:left-auto rtl:right-4'
      }`}
    >
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 bg-white/90 dark:bg-slate-800/90 backdrop-blur-md rounded-xl px-3 py-2.5 shadow-lg border border-slate-200/50 dark:border-slate-700/50 hover:bg-white dark:hover:bg-slate-800 transition-all text-sm font-medium text-slate-700 dark:text-slate-300"
      >
        <LayersIcon />
        <span className="hidden sm:inline">{t(currentStyleObj.labelKey)}</span>
      </button>

      {isOpen && (
        <div className="mt-2 bg-white/95 dark:bg-slate-800/95 backdrop-blur-xl rounded-xl shadow-2xl border border-slate-200/60 dark:border-slate-700/60 overflow-hidden min-w-[180px]">
          {MAP_STYLES.map((s) => {
            const isActive = typeof currentStyle === 'object' && typeof s.style === 'object'
                            ? currentStyle.sources?.[s.id] !== undefined
                            : currentStyle === s.style;
            
            return (
              <button
                key={s.id}
                onClick={() => { onStyleChange(s.style); setIsOpen(false); }}
                className={`w-full flex items-center gap-3 px-4 py-2.5 text-left rtl:text-right transition-colors ${
                  isActive
                    ? 'bg-cyan-50 dark:bg-cyan-900/20 text-cyan-700 dark:text-cyan-300'
                    : 'hover:bg-slate-50 dark:hover:bg-slate-700/50 text-slate-700 dark:text-slate-300'
                }`}
              >
                <span className="text-base">{s.icon}</span>
                <span className="text-sm font-medium">{t(s.labelKey)}</span>
                {isActive && (
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" className="ml-auto rtl:ml-0 rtl:mr-auto text-cyan-500">
                    <polyline points="20 6 9 17 4 12"/>
                  </svg>
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};

export { MAP_STYLES };
export default MapStyleSwitcher;
