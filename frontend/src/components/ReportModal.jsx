import React, { useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import html2pdf from 'html2pdf.js';

const CloseIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
  </svg>
);

const DownloadIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
  </svg>
);

const ReportModal = ({ isOpen, onClose, reportContent }) => {
  const { t } = useTranslation();
  const printRef = useRef(null);
  const [isSaving, setIsSaving] = useState(false);

  if (!isOpen) return null;

  const handleDownloadPDF = async () => {
    if (!printRef.current || isSaving) return;
    setIsSaving(true);
    try {
      await html2pdf().set({
        margin: [14, 12, 16, 12],
        filename: `Laporan_Hidrogeologi_Flores_${new Date().toISOString().slice(0, 10)}.pdf`,
        image: { type: 'jpeg', quality: 0.98 },
        html2canvas: { scale: 2, useCORS: true, logging: false, backgroundColor: '#ffffff' },
        jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
        /* Without this a cost table can be sliced across two pages. */
        pagebreak: { mode: ['css', 'legacy'], avoid: ['tr', 'h2', 'h3'] },
      }).from(printRef.current).save();
    } catch (err) {
      console.error('PDF export failed:', err);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4 bg-black/60 backdrop-blur-sm">
      <div className="bg-white rounded-2xl w-full max-w-3xl h-[90dvh] sm:h-[85dvh] flex flex-col shadow-2xl overflow-hidden">

        {/* Header */}
        <div className="shrink-0 flex items-center justify-between gap-2 p-3 sm:p-5 border-b border-gray-200 bg-gray-50">
          <h2 className="min-w-0 text-sm sm:text-lg font-bold text-gray-800 flex items-center gap-2">
            <svg className="shrink-0" xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#0ea5e9" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
            <span className="truncate">{t('report.title', 'التقرير الاستكشاري للمياه الجوفية')}</span>
          </h2>
          <div className="flex items-center gap-2 shrink-0">
            {reportContent && (
              <button
                onClick={handleDownloadPDF}
                disabled={isSaving}
                aria-label={t('report.download', 'تحميل PDF')}
                className="flex items-center justify-center gap-2 min-w-11 h-11 px-3 sm:px-4 bg-sky-600 hover:bg-sky-700 disabled:bg-sky-600/60 text-white text-sm font-semibold rounded-lg transition-colors shadow-sm active:scale-95"
              >
                {isSaving
                  ? <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                  : <DownloadIcon />}
                <span className="hidden sm:inline">{t('report.download', 'تحميل PDF')}</span>
              </button>
            )}
            <button
              onClick={onClose}
              aria-label={t('ai.close', 'إغلاق')}
              className="grid place-items-center w-11 h-11 text-gray-400 hover:text-gray-700 hover:bg-gray-200 rounded-lg transition-colors active:scale-95"
            >
              <CloseIcon />
            </button>
          </div>
        </div>

        {/* Body — kept on plain hex colours so html2canvas reproduces it faithfully */}
        <div className="flex-1 min-h-0 overflow-y-auto overscroll-contain p-4 sm:p-8 bg-white">
          {!reportContent ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-500">
              <div className="w-8 h-8 border-4 border-sky-500 border-t-transparent rounded-full animate-spin mb-4" />
              <p className="font-medium text-gray-600">{t('report.generating', 'جاري إعداد التقرير...')}</p>
            </div>
          ) : (
            /* `report-body` is styled in index.css. These rules used to sit in an
               inline <style> under the shared `markdown-body` class, where they
               leaked into the chat bubbles — right-aligned <th> included. */
            <div ref={printRef} className="report-body" dir="auto">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{reportContent}</ReactMarkdown>

              <div className="report-footer">
                {t('report.footer', 'تم إنشاء هذا التقرير تلقائياً بواسطة المولد الهيدروجيولوجي الذكي - منصة جزيرة فلوريس.')}
                <br />
                {t('report.generatedOn', 'تاريخ الإنشاء')}: {new Date().toLocaleString('en-GB')}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ReportModal;
