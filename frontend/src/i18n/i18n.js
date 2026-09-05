import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import ar from './ar.json';
import id from './id.json';

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      ar: { translation: ar },
      id: { translation: id },
    },
    fallbackLng: 'id',
    supportedLngs: ['ar', 'id'],
    interpolation: { escapeValue: false },
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage'],
    },
  });

// Keep <html dir/lang> in sync with the active language.
// This must also run for the language resolved at startup: the
// `languageChanged` event fires during init(), before the listener below is
// attached, so without the explicit call an Arabic first load stayed LTR.
const applyDirection = (lng) => {
  document.documentElement.dir = lng === 'ar' ? 'rtl' : 'ltr';
  document.documentElement.lang = lng === 'ar' ? 'ar' : 'id';
};

i18n.on('languageChanged', applyDirection);
applyDirection(i18n.resolvedLanguage || i18n.language || 'id');

export default i18n;
