import React, { useState, useCallback, useRef, useEffect } from 'react';
import Map, { Source, Layer, NavigationControl, Popup, Marker } from 'react-map-gl/mapbox';
import 'mapbox-gl/dist/mapbox-gl.css';
import { useTranslation } from 'react-i18next';
import MapStyleSwitcher from './MapStyleSwitcher';
import ReportModal from './ReportModal';
import DrawControl from './DrawControl';
import length from '@turf/length';
import area from '@turf/area';

/* SVG Icons */
const PinIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="#06b6d4" stroke="#0e7490" strokeWidth="1.5">
    <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
    <circle cx="12" cy="10" r="3" fill="white" stroke="#0e7490"/>
  </svg>
);

const AIPinIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="#8b5cf6" stroke="#6d28d9" strokeWidth="1.5">
    <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
    <circle cx="12" cy="10" r="3" fill="white" stroke="#6d28d9"/>
  </svg>
);

const CameraIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/>
  </svg>
);

const CopyIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
  </svg>
);

const DownloadIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
  </svg>
);

const CrosshairIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10"/><line x1="22" y1="12" x2="18" y2="12"/><line x1="6" y1="12" x2="2" y2="12"/><line x1="12" y1="6" x2="12" y2="2"/><line x1="12" y1="22" x2="12" y2="18"/>
  </svg>
);

const TrashIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
  </svg>
);

const MapPinIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>
  </svg>
);

const wmsTileUrl = (w) =>
  `/api/wms/${w.source}?service=WMS&version=1.1.1&request=GetMap` +
  `&layers=${encodeURIComponent(w.layer)}&styles=&format=image%2Fpng` +
  `&transparent=true&srs=EPSG%3A3857&width=256&height=256&bbox={bbox-epsg-3857}`;

const MapVisualizer = ({
  isSidebarOpen,
  activeLayers,
  wmsLayers,
  potentialData,
  restrictedZonesData,
  catBasinsData,
  geologyData,
  riversData,
  pinnedPoints,
  aiPins,
  flyToTarget,
  onPinPoint,
  onRemovePin,
}) => {
  const { t, i18n } = useTranslation();
  const mapRef = useRef(null);
  const [mapStyle, setMapStyle] = useState('mapbox://styles/mapbox/outdoors-v12');
  const [viewState, setViewState] = useState({
    longitude: 121.3,
    latitude: -8.6,
    zoom: 8.5,
  });
  const [hoverInfo, setHoverInfo] = useState(null);
  const [selectedPin, setSelectedPin] = useState(null);
  const [isCapturing, setIsCapturing] = useState(false);
  const [copied, setCopied] = useState(false);
  
  const [reportModalOpen, setReportModalOpen] = useState(false);
  const [reportContent, setReportContent] = useState('');
  const [drawnFeatures, setDrawnFeatures] = useState({});

  const onDrawChange = useCallback((e) => {
    setDrawnFeatures(prev => {
      const newFeatures = { ...prev };
      // Depending on the event type, features might be created, updated, or deleted
      if (e.type === 'draw.delete') {
        e.features.forEach(f => delete newFeatures[f.id]);
      } else {
        e.features.forEach(f => {
          let measurementText = '';
          if (f.geometry.type === 'LineString') {
            const dist = length(f, { units: 'kilometers' });
            measurementText = `${dist.toFixed(2)} km`;
          } else if (f.geometry.type === 'Polygon') {
            const sqMeters = area(f);
            measurementText = sqMeters > 1000000 
              ? `${(sqMeters / 1000000).toFixed(2)} km²` 
              : `${sqMeters.toFixed(0)} m²`;
          }
          newFeatures[f.id] = { ...f, measurement: measurementText };
        });
      }
      return newFeatures;
    });
  }, []);

  const generatePointReport = async (pin) => {
    setReportContent('');
    setReportModalOpen(true);
    try {
      const res = await fetch(`${import.meta.env.VITE_API_BASE_URL || ''}/api/ai/generate-report`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          area_data: {
            bbox: `Point Coordinates: ${pin.latitude}°S, ${pin.longitude}°E`,
            potential_zones_count: pin.label || 'High Potential Area',
            restricted_zones_count: '0 (Safe from restricted areas)',
          },
          language: i18n.language
        })
      });
      const data = await res.json();
      setReportContent(data.report);
    } catch {
      setReportContent(t('map.reportError', 'حدث خطأ أثناء إعداد التقرير.'));
    }
  };

  /* Smooth Fly-To */
  useEffect(() => {
    if (flyToTarget && mapRef.current) {
      mapRef.current.flyTo({
        center: [flyToTarget.longitude, flyToTarget.latitude],
        zoom: flyToTarget.zoom || 12,
        duration: 1800,
        essential: true,
      });
    }
  }, [flyToTarget]);

  const onHover = useCallback((event) => {
    const { features, lngLat } = event;
    const hoveredFeature = features && features[0];
    setHoverInfo(hoveredFeature ? { lngLat, properties: hoveredFeature.properties } : null);
  }, []);

  const onMapClick = useCallback((event) => {
    const { lngLat } = event;
    if (onPinPoint) {
      const newPin = {
        id: Date.now(),
        longitude: parseFloat(lngLat.lng.toFixed(6)),
        latitude: parseFloat(lngLat.lat.toFixed(6)),
        timestamp: new Date().toISOString(),
        zoom: viewState.zoom,
        source: 'manual',
        label: t('map.customPin', 'موقع محدد يدوياً')
      };
      onPinPoint(newPin);
      setSelectedPin(newPin);
    }
  }, [onPinPoint, viewState.zoom, t]);

  const copyCoordinates = useCallback((pin) => {
    navigator.clipboard.writeText(`${pin.latitude}, ${pin.longitude}`).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, []);

  const captureScreenshot = useCallback(async (pin) => {
    setIsCapturing(true);
    try {
      const token = import.meta.env.VITE_MAPBOX_TOKEN;
      const url = `https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/${pin.longitude},${pin.latitude},15,0/1280x1280@2x?access_token=${token}`;
      const response = await fetch(url);
      const blob = await response.blob();
      const metadata = {
        location: { latitude: pin.latitude, longitude: pin.longitude, crs: 'EPSG:4326' },
        capture: { timestamp: new Date().toISOString(), resolution: '2560x2560', zoom: 15, style: 'satellite-v9' },
        region: { island: 'Flores', country: 'Indonesia', province: 'Nusa Tenggara Timur (NTT)' },
        active_layers: Object.entries(activeLayers).filter(([, v]) => v).map(([k]) => k),
      };
      // Download Image
      const imgUrl = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = imgUrl;
      link.download = `Flores_Well_Site_${pin.latitude}_${pin.longitude}.png`;
      link.click();
      URL.revokeObjectURL(imgUrl);
      // Download Metadata JSON
      const metaBlob = new Blob([JSON.stringify(metadata, null, 2)], { type: 'application/json' });
      const metaUrl = URL.createObjectURL(metaBlob);
      const mLink = document.createElement('a');
      mLink.href = metaUrl;
      mLink.download = `Flores_Site_Data_${pin.latitude}_${pin.longitude}.json`;
      mLink.click();
      URL.revokeObjectURL(metaUrl);
    } catch (err) {
      console.error(err);
    } finally {
      setIsCapturing(false);
    }
  }, [activeLayers]);

  const exportPinsAsGeoJSON = useCallback(() => {
    const allPins = [...(pinnedPoints || []), ...(aiPins || [])];
    if (allPins.length === 0) return;
    const geojson = {
      type: 'FeatureCollection',
      features: allPins.map(p => ({
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [p.longitude, p.latitude] },
        properties: {
          id: p.id,
          timestamp: p.timestamp,
          source: p.source || 'manual',
          label: p.label || '',
          reason: p.reason || ''
        },
      })),
    };
    const blob = new Blob([JSON.stringify(geojson, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `Flores_Water_Locations_${new Date().toISOString().slice(0, 10)}.geojson`;
    link.click();
    URL.revokeObjectURL(url);
  }, [pinnedPoints, aiPins]);

  const totalPins = (pinnedPoints?.length || 0) + (aiPins?.length || 0);

  return (
    <div className="w-full h-full relative overflow-hidden select-none">
      <Map
        ref={mapRef}
        {...viewState}
        onMove={evt => setViewState(evt.viewState)}
        mapStyle={mapStyle}
        mapboxAccessToken={import.meta.env.VITE_MAPBOX_TOKEN}
        interactiveLayerIds={[
          'groundwater-potential-fill',
          'restricted-zones-fill',
          'cat-basins-fill',
          'geology-fill'
        ]}
        onMouseMove={onHover}
        onClick={onMapClick}
        cursor="crosshair"
      >
        <NavigationControl position="top-right" showCompass={true} />
        
        <DrawControl
          position="top-right"
          displayControlsDefault={false}
          controls={{
            polygon: true,
            line_string: true,
            trash: true
          }}
          defaultMode="simple_select"
          onCreate={onDrawChange}
          onUpdate={onDrawChange}
          onDelete={onDrawChange}
        />

        {/* Display measurements for drawn features */}
        {Object.values(drawnFeatures).map(f => {
          if (!f.measurement) return null;
          // Put the marker at the last coordinate or center
          let coords = f.geometry.coordinates;
          if (f.geometry.type === 'Polygon') coords = coords[0];
          const lastCoord = coords[coords.length - 1] || coords[0];
          if (!lastCoord || !lastCoord[0]) return null;
          
          return (
            <Marker key={`measure-${f.id}`} longitude={lastCoord[0]} latitude={lastCoord[1]}>
              <div className="px-2 py-1 bg-white/90 dark:bg-slate-800/90 backdrop-blur-md rounded-md shadow-md text-xs font-bold text-slate-800 dark:text-slate-200 border border-slate-200 dark:border-slate-700 select-none">
                {f.measurement}
              </div>
            </Marker>
          );
        })}

        {/* 1. Groundwater Basins (CAT - Cekungan Air Tanah) */}
        {activeLayers.groundwaterBasins && catBasinsData && (
          <Source id="cat-basins-src" type="geojson" data={catBasinsData}>
            <Layer
              id="cat-basins-fill"
              type="fill"
              paint={{
                'fill-color': '#6366f1',
                'fill-opacity': 0.25,
              }}
            />
            <Layer
              id="cat-basins-line"
              type="line"
              paint={{
                'line-color': '#4f46e5',
                'line-width': 2,
                'line-dasharray': [2, 2],
              }}
            />
          </Source>
        )}

        {/* 2. Regional Geology & Lithology */}
        {activeLayers.geology && geologyData && (
          <Source id="geology-src" type="geojson" data={geologyData}>
            <Layer
              id="geology-fill"
              type="fill"
              paint={{
                'fill-color': '#f97316', /* Solid orange to match legend */
                'fill-opacity': 0.3,
              }}
            />
            <Layer
              id="geology-line"
              type="line"
              paint={{
                'line-color': '#ea580c',
                'line-width': 1.5,
              }}
            />
          </Source>
        )}

        {/* 3. Groundwater Potential Zones (Alluvial / High Yield) */}
        {activeLayers.groundwaterPotential && potentialData && (
          potentialData.type === 'raster' ? (
            <Source id="gw-pot-src-raster" type="raster" tiles={[potentialData.tile_url]} tileSize={256}>
              <Layer
                id="groundwater-potential-raster"
                type="raster"
                paint={{ 'raster-opacity': 0.6 }}
              />
            </Source>
          ) : (
            <Source id="gw-pot-src" type="geojson" data={potentialData}>
              <Layer
                id="groundwater-potential-fill"
                type="fill"
                paint={{
                  'fill-color': '#10b981',
                  'fill-opacity': 0.35,
                }}
              />
              <Layer
                id="gw-pot-line"
                type="line"
                paint={{
                  'line-color': '#059669',
                  'line-width': 2.5,
                }}
              />
            </Source>
          )
        )}

        {/* 4. Rivers Network */}
        {activeLayers.rivers && riversData && (
          <Source id="rivers-src" type="geojson" data={riversData}>
            <Layer
              id="rivers-line"
              type="line"
              paint={{
                'line-color': '#0284c7',
                'line-width': 3,
                'line-opacity': 0.85,
              }}
            />
          </Source>
        )}

        {/* 5. Restricted Zones (Cemeteries, Nature Reserves, Military) */}
        {activeLayers.restrictedZones && restrictedZonesData && (
          <Source id="rz-src" type="geojson" data={restrictedZonesData}>
            <Layer
              id="restricted-zones-fill"
              type="fill"
              paint={{
                'fill-color': [
                  'match',
                  ['get', 'type'],
                  'cemetery', '#ef4444',
                  'protected_area', '#f59e0b',
                  'military', '#64748b',
                  '#ef4444'
                ],
                'fill-opacity': 0.45,
              }}
            />
            <Layer
              id="rz-line"
              type="line"
              paint={{
                'line-color': [
                  'match',
                  ['get', 'type'],
                  'cemetery', '#dc2626',
                  'protected_area', '#d97706',
                  'military', '#475569',
                  '#dc2626'
                ],
                'line-width': 2,
              }}
            />
          </Source>
        )}

        {/* Official WMS raster layers (ESDM / BIG / OneGeology) via backend proxy */}
        {wmsLayers?.filter((w) => activeLayers[w.id]).map((w) => (
          <Source key={w.id} id={`${w.id}-src`} type="raster" tiles={[wmsTileUrl(w)]} tileSize={256}>
            <Layer id={`${w.id}-layer`} type="raster" paint={{ 'raster-opacity': 0.7 }} />
          </Source>
        ))}

        {/* Manual Click Pins */}
        {pinnedPoints?.map((pin) => (
          <Marker
            key={pin.id}
            longitude={pin.longitude}
            latitude={pin.latitude}
            anchor="bottom"
            onClick={(e) => {
              e.originalEvent.stopPropagation();
              setSelectedPin(pin);
            }}
          >
            <div className="cursor-pointer hover:scale-125 transition-transform duration-200">
              <PinIcon />
            </div>
          </Marker>
        ))}

        {/* AI Suggested Pins */}
        {aiPins?.map((pin) => (
          <Marker
            key={pin.id}
            longitude={pin.longitude}
            latitude={pin.latitude}
            anchor="bottom"
            onClick={(e) => {
              e.originalEvent.stopPropagation();
              setSelectedPin(pin);
            }}
          >
            <div className="cursor-pointer hover:scale-125 transition-transform duration-200 animate-pulse">
              <AIPinIcon />
            </div>
          </Marker>
        ))}

        {/* Pin Popup Modal on Map */}
        {selectedPin && (
          <Popup
            longitude={selectedPin.longitude}
            latitude={selectedPin.latitude}
            anchor="bottom"
            offset={35}
            maxWidth="300px"
            onClose={() => setSelectedPin(null)}
            closeOnClick={false}
          >
            <div className="p-4 w-[272px] max-w-full bg-white dark:bg-slate-900 rounded-xl">
              {/* Title + badge */}
              <div className="flex items-start justify-between gap-2 mb-3 pb-2.5 border-b border-slate-100 dark:border-slate-800">
                <h4 className="text-[13px] font-bold text-slate-800 dark:text-white flex items-start gap-1.5 leading-snug">
                  <span className="mt-0.5 shrink-0 text-cyan-600 dark:text-cyan-400"><CrosshairIcon /></span>
                  <span className="break-words">{selectedPin.label || t('map.pinDetails')}</span>
                </h4>
                {selectedPin.source === 'ai' ? (
                  <span className="shrink-0 text-[9px] px-2 py-0.5 rounded-full bg-violet-100 dark:bg-violet-900/40 text-violet-600 dark:text-violet-300 font-bold whitespace-nowrap">{t('map.aiRecommended', 'AI')}</span>
                ) : (
                  <span className="shrink-0 text-[9px] px-2 py-0.5 rounded-full bg-cyan-100 dark:bg-cyan-900/40 text-cyan-700 dark:text-cyan-300 font-bold whitespace-nowrap">{t('map.manual', 'Manual')}</span>
                )}
              </div>

              {/* Coordinates */}
              <div className="grid grid-cols-2 gap-2 mb-3">
                <div className="rounded-lg bg-slate-50 dark:bg-slate-800 px-2.5 py-1.5">
                  <div className="text-[9px] uppercase tracking-wide text-slate-400 mb-0.5">{t('map.latitude')}</div>
                  <div className="font-mono text-xs font-semibold text-slate-800 dark:text-slate-200" dir="ltr">{Number(selectedPin.latitude).toFixed(5)}°</div>
                </div>
                <div className="rounded-lg bg-slate-50 dark:bg-slate-800 px-2.5 py-1.5">
                  <div className="text-[9px] uppercase tracking-wide text-slate-400 mb-0.5">{t('map.longitude')}</div>
                  <div className="font-mono text-xs font-semibold text-slate-800 dark:text-slate-200" dir="ltr">{Number(selectedPin.longitude).toFixed(5)}°</div>
                </div>
              </div>

              {selectedPin.reason && (
                <p className="text-[11px] text-slate-600 dark:text-slate-300 bg-slate-50 dark:bg-slate-800 p-2.5 rounded-lg mb-3 leading-relaxed break-words">
                  {selectedPin.reason}
                </p>
              )}

              {/* Actions */}
              <div className="flex flex-col gap-1.5">
                {/* Open in Google Maps */}
                <a
                  href={`https://www.google.com/maps/search/?api=1&query=${selectedPin.latitude},${selectedPin.longitude}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-full flex items-center justify-center gap-1.5 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-xs text-white font-semibold shadow-sm transition-colors"
                >
                  <MapPinIcon /> {t('map.openInMaps', 'فتح في خرائط جوجل')}
                </a>

                <div className="flex gap-1.5">
                  <button
                    onClick={() => copyCoordinates(selectedPin)}
                    className="flex-1 flex items-center justify-center gap-1 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-xs text-slate-700 dark:text-slate-200 font-medium transition-colors"
                  >
                    <CopyIcon /> {copied ? '✓' : t('map.copy')}
                  </button>
                  <button
                    onClick={() => captureScreenshot(selectedPin)}
                    disabled={isCapturing}
                    className="flex-1 flex items-center justify-center gap-1 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-700 text-xs text-white font-medium disabled:opacity-50 transition-colors shadow-sm"
                  >
                    <CameraIcon /> {isCapturing ? '...' : t('map.capture')}
                  </button>
                  <button
                    onClick={() => {
                      onRemovePin?.(selectedPin.id);
                      setSelectedPin(null);
                    }}
                    aria-label={t('ai.close', 'حذف')}
                    className="p-1.5 rounded-lg bg-red-50 dark:bg-red-900/30 hover:bg-red-100 dark:hover:bg-red-900/50 text-red-600 dark:text-red-400 transition-colors"
                  >
                    <TrashIcon />
                  </button>
                </div>

                <button
                  onClick={() => generatePointReport(selectedPin)}
                  className="w-full flex items-center justify-center gap-1.5 py-2 rounded-lg bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-xs text-white font-semibold shadow-md shadow-emerald-500/20 transition-all"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
                  {t('map.generateReport', 'إنشاء تقرير جيولوجي PDF')}
                </button>
              </div>
            </div>
          </Popup>
        )}

        {/* Hover Tooltip for GeoJSON Features */}
        {hoverInfo && !selectedPin && (
          <Popup longitude={hoverInfo.lngLat.lng} latitude={hoverInfo.lngLat.lat} closeButton={false} offset={12}>
            <div className="p-2.5 min-w-[180px] bg-white/95 dark:bg-slate-800/95 backdrop-blur-md rounded-lg shadow-lg">
              {Object.entries(hoverInfo.properties)
                .filter(([k]) => !['source_tags', 'color', 'id', 'name_ar', 'name_id'].includes(k))
                .concat(
                  (hoverInfo.properties.name_ar || hoverInfo.properties.name_id) 
                    ? [['name', i18n.language.startsWith('ar') ? hoverInfo.properties.name_ar || hoverInfo.properties.name_id : hoverInfo.properties.name_id || hoverInfo.properties.name_ar]]
                    : []
                )
                .map(([k, v]) => (
                  <div key={k} className="flex justify-between gap-3 py-0.5 text-xs">
                    <span className="text-slate-500 capitalize">{k.replace(/_/g, ' ')}:</span>
                    <span className="text-slate-800 dark:text-slate-200 font-semibold">{String(v)}</span>
                  </div>
                ))}
            </div>
          </Popup>
        )}
      </Map>

      {/* Map Style Switcher Floating Control */}
      <MapStyleSwitcher currentStyle={mapStyle} onStyleChange={setMapStyle} isSidebarOpen={isSidebarOpen} />

      {/* Floating Bottom Coordinates & GeoJSON Exporter */}
      <div className="absolute bottom-6 left-6 rtl:left-auto rtl:right-6 flex flex-col gap-2 z-10">
        <div className="bg-white/90 dark:bg-slate-900/90 backdrop-blur-md rounded-xl px-3.5 py-2 shadow-lg border border-slate-200/60 dark:border-slate-700/60">
          <div className="flex items-center gap-2 text-xs font-mono text-slate-700 dark:text-slate-300">
            <CrosshairIcon />
            <span>{viewState.latitude.toFixed(4)}°, {viewState.longitude.toFixed(4)}°</span>
            <span className="text-slate-400">z{viewState.zoom.toFixed(1)}</span>
          </div>
        </div>
        {totalPins > 0 && (
          <button
            onClick={exportPinsAsGeoJSON}
            className="flex items-center gap-2 bg-white/90 dark:bg-slate-900/90 backdrop-blur-md rounded-xl px-3.5 py-2 shadow-lg border border-slate-200/60 dark:border-slate-700/60 hover:bg-cyan-50 dark:hover:bg-cyan-900/30 text-xs text-slate-800 dark:text-slate-200 font-semibold transition-colors"
          >
            <DownloadIcon /> {t('map.exportPins')} ({totalPins})
          </button>
        )}
      </div>

      {/* Report Modal */}
      <ReportModal
        isOpen={reportModalOpen}
        onClose={() => setReportModalOpen(false)}
        reportContent={reportContent}
      />
    </div>
  );
};

export default MapVisualizer;
