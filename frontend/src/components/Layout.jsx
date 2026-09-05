import React, { useState, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import Sidebar from './Sidebar';
import MapVisualizer from './MapVisualizer';
import ThemeToggle from './ThemeToggle';
import LanguageSwitcher from './LanguageSwitcher';
import AIPanel from './AIPanel';
import SearchBar from './SearchBar';
import {
  useGroundwaterPotential,
  useRestrictedZones,
  useCATBasins,
  useGeology,
  useRivers,
  useWMSConfig,
} from '../hooks/useMapData';

const WaterIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-cyan-500">
    <path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"/>
  </svg>
);

const AnalysisBtnIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
    <polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>
  </svg>
);

const MenuIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/>
  </svg>
);

const Layout = () => {
  const { t } = useTranslation();
  const [isSidebarOpen, setIsSidebarOpen] = useState(window.innerWidth >= 768);
  const [isAIPanelOpen, setIsAIPanelOpen] = useState(false);
  const [pinnedPoints, setPinnedPoints] = useState([]);
  const [aiPins, setAIPins] = useState([]);
  const [flyToTarget, setFlyToTarget] = useState(null);

  // All layers start disabled by default except restricted zones or as user toggles
  const [activeLayers, setActiveLayers] = useState({
    groundwaterPotential: false,
    restrictedZones: true,
    groundwaterBasins: false,
    geology: false,
    rivers: false,
    wmsGeology: false,
    wmsGroundwater: false,
  });

  const { data: potentialData } = useGroundwaterPotential();
  const { data: restrictedZonesData } = useRestrictedZones();
  const { data: catBasinsData } = useCATBasins();
  const { data: geologyData } = useGeology();
  const { data: riversData } = useRivers();
  const { data: wmsConfig } = useWMSConfig();

  // Resolve which official WMS layers are actually available (server-side discovery).
  const wmsLayers = useMemo(() => {
    const c = wmsConfig || {};
    const list = [];
    const firstReachable = (sources, key) => {
      for (const s of sources) {
        if (c[s]?.reachable && c[s][key]) return { source: s, layer: c[s][key] };
      }
      return null;
    };
    // Geology: USGS (global) -> ESDM -> OneGeology
    const geo = firstReachable(['usgs', 'esdm', 'onegeology'], 'geology_layer');
    if (geo) list.push({ id: 'wmsGeology', titleKey: 'sidebar.wmsGeology', color: 'bg-rose-500', ...geo });
    // Groundwater: BGR WHYMAP (global) -> ESDM -> BIG
    const gw = firstReachable(['bgr', 'esdm', 'big'], 'groundwater_layer');
    if (gw) list.push({ id: 'wmsGroundwater', titleKey: 'sidebar.wmsGroundwater', color: 'bg-blue-600', ...gw });
    return list;
  }, [wmsConfig]);

  const handleToggleLayer = useCallback((layerId) => {
    setActiveLayers(prev => ({ ...prev, [layerId]: !prev[layerId] }));
  }, []);

  const handlePinPoint = useCallback((pin) => {
    setPinnedPoints(prev => [...prev, pin]);
  }, []);

  const handleRemovePin = useCallback((pinId) => {
    setPinnedPoints(prev => prev.filter(p => p.id !== pinId));
    setAIPins(prev => prev.filter(p => p.id !== pinId));
  }, []);

  const handleAddAIPins = useCallback((newPins) => {
    setAIPins(prev => [...prev, ...newPins]);
    if (newPins && newPins.length > 0) {
      setFlyToTarget({
        latitude: newPins[0].latitude,
        longitude: newPins[0].longitude,
        zoom: 11
      });
    }
  }, []);

  const handleSelectLocation = useCallback((location) => {
    setFlyToTarget(location);
  }, []);

  return (
    <div className="flex flex-col h-[100dvh] w-full bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 font-sans">
      {/* Header */}
      <header className="flex-none h-14 bg-white/90 dark:bg-slate-900/90 backdrop-blur-xl border-b border-slate-200/70 dark:border-slate-800/70 px-2 md:px-6 flex items-center justify-between gap-1 md:gap-2 z-20">
        <div className="flex items-center gap-1.5 md:gap-3 min-w-0 flex-1 md:flex-none">
          {/* Sidebar toggle */}
          <button
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
            aria-label={t('sidebar.layers')}
            aria-expanded={isSidebarOpen}
            className="shrink-0 grid place-items-center w-11 h-11 rounded-xl text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 active:scale-95 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/60"
          >
            <MenuIcon />
          </button>
          {/* On phones the title carries the identity; the mark would only eat width. */}
          <div className="hidden sm:block shrink-0 p-2 rounded-xl bg-cyan-500/10 text-cyan-600 dark:text-cyan-400">
            <WaterIcon />
          </div>
          <div className="min-w-0">
            <h1 className="text-sm md:text-base font-bold text-slate-800 dark:text-white leading-tight tracking-tight truncate">
              <span className="md:hidden">{t('app.titleShort', t('app.title'))}</span>
              <span className="hidden md:inline">{t('app.title')}</span>
            </h1>
            <span className="hidden md:block text-[10px] md:text-xs text-slate-400 dark:text-slate-500 font-medium tracking-wide truncate">
              {t('app.subtitle')}
            </span>
          </div>
        </div>

        {/* Search Bar */}
        <div className="hidden md:flex flex-1 justify-center max-w-md px-4">
          <SearchBar onSelectLocation={handleSelectLocation} />
        </div>

        <div className="flex items-center gap-1 md:gap-2 shrink-0">
          {/* AI Analysis Toggle */}
          <button
            onClick={() => setIsAIPanelOpen(!isAIPanelOpen)}
            aria-label={t('ai.button')}
            aria-pressed={isAIPanelOpen}
            className={`flex items-center justify-center gap-2 min-w-11 h-11 px-3 sm:px-3.5 rounded-xl text-sm font-semibold transition-all duration-200 shadow-sm active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500/60 ${
              isAIPanelOpen
                ? 'bg-violet-600 text-white shadow-violet-600/30 ring-2 ring-violet-400/40'
                : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-700'
            }`}
          >
            <AnalysisBtnIcon />
            <span className="hidden sm:inline">{t('ai.button')}</span>
          </button>

          <div className="hidden sm:block w-px h-6 bg-slate-200 dark:bg-slate-700 mx-1" />
          <LanguageSwitcher />
          <ThemeToggle />
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex overflow-hidden relative">
        {/* Mobile backdrop */}
        {isSidebarOpen && (
          <div
            className="md:hidden fixed inset-0 top-14 bg-slate-900/40 backdrop-blur-sm z-30"
            onClick={() => setIsSidebarOpen(false)}
            aria-hidden="true"
          />
        )}
        <Sidebar
          activeLayers={activeLayers}
          onToggleLayer={handleToggleLayer}
          isOpen={isSidebarOpen}
          onClose={() => setIsSidebarOpen(false)}
          wmsLayers={wmsLayers}
          wmsConfig={wmsConfig}
        />
        <div className="flex-1 h-full relative">
          <div
            className={`md:hidden absolute top-3 left-3 right-3 z-30 transition-opacity duration-200 ${
              isSidebarOpen ? 'opacity-0 pointer-events-none' : 'opacity-100'
            }`}
          >
            <SearchBar onSelectLocation={handleSelectLocation} />
          </div>
          <MapVisualizer
            isSidebarOpen={isSidebarOpen}
            activeLayers={activeLayers}
            wmsLayers={wmsLayers}
            potentialData={potentialData}
            restrictedZonesData={restrictedZonesData}
            catBasinsData={catBasinsData}
            geologyData={geologyData}
            riversData={riversData}
            pinnedPoints={pinnedPoints}
            aiPins={aiPins}
            flyToTarget={flyToTarget}
            onPinPoint={handlePinPoint}
            onRemovePin={handleRemovePin}
          />
        </div>
        <AIPanel 
          isOpen={isAIPanelOpen} 
          onClose={() => setIsAIPanelOpen(false)} 
          onAddAIPins={handleAddAIPins}
        />
      </main>
    </div>
  );
};

export default Layout;
