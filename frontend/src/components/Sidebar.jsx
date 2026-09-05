import React from 'react';
import { useTranslation } from 'react-i18next';

const LayerToggle = ({ id, label, checked, onChange, color }) => (
  <button
    type="button"
    role="switch"
    aria-checked={checked}
    aria-label={label}
    onClick={() => onChange(id)}
    className="w-full flex items-center justify-between gap-3 min-h-11 py-2 px-3 rounded-xl hover:bg-slate-100/70 active:bg-slate-200/70 dark:active:bg-slate-700/70 dark:hover:bg-slate-800/70 cursor-pointer transition-colors duration-150 select-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/60"
  >
    <div className="flex items-center gap-3 min-w-0">
      <div className={`w-3 h-3 rounded-full ${color} shadow-sm`} />
      <span className="text-sm font-medium text-slate-700 dark:text-slate-200 text-start">
        {label}
      </span>
    </div>
    {/* Clean, fast iOS/Modern switch */}
    <div
      className={`w-10 h-5 flex items-center rounded-full p-0.5 transition-colors duration-200 ${
        checked ? 'bg-cyan-500 justify-end' : 'bg-slate-300 dark:bg-slate-700 justify-start'
      }`}
    >
      <div className="bg-white w-4 h-4 rounded-full shadow-md transform transition-transform duration-200" />
    </div>
  </button>
);

const CloseIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
  </svg>
);

const Sidebar = ({ activeLayers, onToggleLayer, isOpen = false, onClose, wmsLayers = [], wmsConfig }) => {
  const { t } = useTranslation();
  const wmsProbed = wmsConfig !== undefined; // discovery request has resolved

  const analysisLayers = [
    { id: 'groundwaterPotential', label: t('sidebar.groundwaterPotential'), color: 'bg-emerald-500' },
    { id: 'restrictedZones', label: t('sidebar.restrictedZones'), color: 'bg-red-500' },
  ];

  const geologicalLayers = [
    { id: 'groundwaterBasins', label: t('sidebar.groundwaterBasins'), color: 'bg-indigo-500' },
    { id: 'geology', label: t('sidebar.geology'), color: 'bg-orange-500' },
    { id: 'rivers', label: t('sidebar.rivers'), color: 'bg-sky-500' },
  ];

  return (
    <aside
      className={`absolute inset-y-0 left-0 rtl:left-auto rtl:right-0 z-40
        w-80 max-w-[85vw] overflow-hidden
        bg-white/95 dark:bg-slate-900/95 backdrop-blur-xl
        border-r rtl:border-r-0 rtl:border-l border-slate-200/70 dark:border-slate-800/70
        flex flex-col shadow-2xl
        transform transition-transform duration-300 ease-in-out
        ${isOpen ? 'translate-x-0' : '-translate-x-full rtl:translate-x-full'}`}
    >
      {/* Header */}
      <div className="shrink-0 p-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
        <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500">
          {t('sidebar.layers')}
        </h2>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-cyan-100 dark:bg-cyan-950 text-cyan-700 dark:text-cyan-400">
            GIS Active
          </span>
          {/* Mobile close */}
          <button
            onClick={onClose}
            aria-label={t('ai.close', 'إغلاق')}
            className="grid place-items-center w-11 h-11 -mr-1.5 rtl:-mr-0 rtl:-ml-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 active:scale-95 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/60"
          >
            <CloseIcon />
          </button>
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto overscroll-contain p-3 space-y-4">
        {/* Groundwater Analysis Section */}
        <div>
          <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 px-3 mb-1.5">
            {t('sidebar.analysis', 'التحليلات والمطابقة')}
          </p>
          <div className="space-y-0.5">
            {analysisLayers.map(layer => (
              <LayerToggle
                key={layer.id}
                {...layer}
                checked={!!activeLayers[layer.id]}
                onChange={onToggleLayer}
              />
            ))}
          </div>
        </div>

        {/* Geological & Hydrogeological Data Section */}
        <div>
          <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 px-3 mb-1.5">
            {t('sidebar.externalData', 'البيانات الجيولوجية والهيدرولوجية')}
          </p>
          <div className="space-y-0.5">
            {geologicalLayers.map(layer => (
              <LayerToggle
                key={layer.id}
                {...layer}
                checked={!!activeLayers[layer.id]}
                onChange={onToggleLayer}
              />
            ))}
          </div>
        </div>

        {/* Official WMS layers (ESDM / BIG) — appear only when the servers respond */}
        <div>
          <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 px-3 mb-1.5 flex items-center gap-1.5">
            {t('sidebar.wmsSection', 'طبقات رسمية (WMS)')}
            <span className="text-[9px] px-1.5 py-0.5 rounded bg-emerald-100 dark:bg-emerald-950 text-emerald-600 dark:text-emerald-400 normal-case font-semibold">
              {t('sidebar.wmsLive', 'حقيقية')}
            </span>
          </p>
          {wmsLayers.length > 0 ? (
            <div className="space-y-0.5">
              {wmsLayers.map(layer => (
                <LayerToggle
                  key={layer.id}
                  id={layer.id}
                  label={t(layer.titleKey)}
                  color={layer.color}
                  checked={!!activeLayers[layer.id]}
                  onChange={onToggleLayer}
                />
              ))}
            </div>
          ) : (
            <p className="text-[11px] text-slate-400 dark:text-slate-500 px-3 py-2 leading-relaxed">
              {wmsProbed
                ? t('sidebar.wmsUnavailable', 'الخوادم الرسمية (ESDM/BIG) غير متاحة حالياً من هذا الخادم.')
                : t('sidebar.wmsLoading', 'جارٍ فحص الخوادم الرسمية...')}
            </p>
          )}
        </div>
      </div>

      {/* Legend */}
      <div className="shrink-0 max-h-[45%] overflow-y-auto overscroll-contain p-4 pb-safe border-t border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/30">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 mb-3">
          {t('sidebar.legend')}
        </h3>

        {/* Groundwater Potential Bar */}
        <div className="mb-3.5">
          <div className="h-2 w-full rounded-full bg-gradient-to-r from-slate-200 via-teal-400 to-emerald-500 dark:from-slate-700 dark:via-teal-500 dark:to-emerald-400" />
          <div className="flex justify-between text-[10px] text-slate-500 dark:text-slate-400 mt-1 font-medium">
            <span>{t('sidebar.lowPotential')}</span>
            <span>{t('sidebar.highPotential')}</span>
          </div>
        </div>

        {/* Restricted and Geological Zones indicators */}
        <div className="grid grid-cols-2 gap-2 text-[11px]">
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-sm bg-red-500 shadow-sm" />
            <span className="text-slate-600 dark:text-slate-400">{t('sidebar.cemetery')}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-sm bg-amber-500 shadow-sm" />
            <span className="text-slate-600 dark:text-slate-400">{t('sidebar.protectedArea')}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-sm bg-slate-500 shadow-sm" />
            <span className="text-slate-600 dark:text-slate-400">{t('sidebar.military')}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-sm bg-indigo-500 shadow-sm" />
            <span className="text-slate-600 dark:text-slate-400">{t('sidebar.groundwaterBasins', 'حوض جوفي (CAT)')}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-sm bg-orange-500 shadow-sm" />
            <span className="text-slate-600 dark:text-slate-400">{t('sidebar.geology')}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-sm bg-sky-500 shadow-sm" />
            <span className="text-slate-600 dark:text-slate-400">{t('sidebar.rivers')}</span>
          </div>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
