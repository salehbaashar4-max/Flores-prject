import React, { useRef } from 'react';
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

  if (!isOpen) return null;

  const handleDownloadPDF = () => {
    if (!printRef.current) return;
    const element = printRef.current;
    
    const opt = {
      margin:       15,
      filename:     `Laporan_Hidrogeologi_Flores_${Date.now()}.pdf`,
      image:        { type: 'jpeg', quality: 0.98 },
      html2canvas:  { scale: 2, useCORS: true, logging: false },
      jsPDF:        { unit: 'mm', format: 'a4', orientation: 'portrait' }
    };

    html2pdf().set(opt).from(element).save();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4 bg-black/60 backdrop-blur-sm">
      <div className="bg-white rounded-2xl w-full max-w-3xl h-[90dvh] sm:h-[85dvh] flex flex-col shadow-2xl overflow-hidden">
        
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-gray-200 bg-gray-50">
          <h2 className="text-lg font-bold text-gray-800 flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#0ea5e9" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
            {t('report.title', 'التقرير الاستكشاري للمياه الجوفية')}
          </h2>
          <div className="flex items-center gap-3">
            {reportContent && (
              <button
                onClick={handleDownloadPDF}
                className="flex items-center gap-2 px-4 py-2 bg-sky-600 hover:bg-sky-700 text-white text-sm font-semibold rounded-lg transition-colors shadow-sm"
              >
                <DownloadIcon /> {t('report.download', 'تحميل PDF')}
              </button>
            )}
            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-gray-700 hover:bg-gray-200 rounded-lg transition-colors"
            >
              <CloseIcon />
            </button>
          </div>
        </div>

        {/* Content Body (Strict standard hex colors for html2canvas compatibility) */}
        <div className="flex-1 overflow-y-auto overscroll-contain p-4 sm:p-8 bg-white">
          {!reportContent ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-500">
              <div className="w-8 h-8 border-4 border-sky-500 border-t-transparent rounded-full animate-spin mb-4" />
              <p className="font-medium text-gray-600">{t('report.generating', 'جاري إعداد التقرير...')}</p>
            </div>
          ) : (
            <div 
              ref={printRef} 
              className="markdown-body"
              style={{
                color: '#1f2937', 
                backgroundColor: '#ffffff',
                fontFamily: 'system-ui, -apple-system, sans-serif',
                lineHeight: '1.6',
                direction: /[\u0600-\u06FF]/.test(reportContent) ? 'rtl' : 'ltr'
              }}
            >
              <style>{`
                .markdown-body h1 { color: #111827; font-size: 1.8rem; border-bottom: 2px solid #e5e7eb; padding-bottom: 0.5rem; margin-bottom: 1.5rem; }
                .markdown-body h2 { color: #1f2937; font-size: 1.4rem; margin-top: 1.5rem; margin-bottom: 0.75rem; border-bottom: 1px solid #f3f4f6; padding-bottom: 0.25rem;}
                .markdown-body h3 { color: #374151; font-size: 1.1rem; margin-top: 1.25rem; margin-bottom: 0.5rem;}
                .markdown-body p { margin-bottom: 1rem; color: #4b5563; }
                .markdown-body ul, .markdown-body ol { margin-bottom: 1rem; padding-inline-start: 2rem; color: #4b5563; }
                .markdown-body li { margin-bottom: 0.25rem; }
                .markdown-body strong { color: #111827; }
                .markdown-body table { width: 100%; border-collapse: collapse; margin-top: 1rem; margin-bottom: 1.5rem; font-size: 0.9rem;}
                .markdown-body th { background-color: #f3f4f6; font-weight: bold; text-align: right; padding: 10px; border: 1px solid #d1d5db; color: #1f2937;}
                .markdown-body td { padding: 10px; border: 1px solid #d1d5db; color: #4b5563;}
                .markdown-body hr { border: none; border-top: 1px solid #e5e7eb; margin: 2rem 0; }
              `}</style>
              
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{reportContent}</ReactMarkdown>
              
              {/* Footer for PDF */}
              <div style={{ marginTop: '4rem', paddingTop: '1rem', borderTop: '1px solid #e5e7eb', fontSize: '0.8rem', color: '#6b7280', textAlign: 'center' }}>
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
