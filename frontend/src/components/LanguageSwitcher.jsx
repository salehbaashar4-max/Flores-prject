import React from 'react';
import { useTranslation } from 'react-i18next';

const LanguageSwitcher = () => {
  const { i18n } = useTranslation();
  const currentLang = i18n.language;

  const languages = [
    { code: 'id', label: 'ID', fullName: 'Indonesia' },
    { code: 'ar', label: 'ع', fullName: 'العربية' },
  ];

  return (
    <div className="flex items-center rounded-xl overflow-hidden border border-slate-200 dark:border-slate-700">
      {languages.map((lang) => (
        <button
          key={lang.code}
          onClick={() => i18n.changeLanguage(lang.code)}
          className={`px-3 py-1.5 text-sm font-semibold transition-all duration-200 ${
            currentLang === lang.code || currentLang.startsWith(lang.code)
              ? 'bg-cyan-500 text-white shadow-sm'
              : 'bg-white dark:bg-slate-800 text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-750'
          }`}
          title={lang.fullName}
        >
          {lang.label}
        </button>
      ))}
    </div>
  );
};

export default LanguageSwitcher;
