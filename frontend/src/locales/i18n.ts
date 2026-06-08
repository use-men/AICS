import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import zh from './zh';
import en from './en';

// 从 localStorage 读取语言偏好，默认中文
const savedLang = localStorage.getItem('smartdesk_lang') || 'zh';

i18n.use(initReactI18next).init({
  resources: {
    zh: { translation: zh },
    en: { translation: en },
  },
  lng: savedLang,
  fallbackLng: 'zh',
  interpolation: {
    escapeValue: false,
  },
});

// 语言切换时持久化
i18n.on('languageChanged', (lng) => {
  localStorage.setItem('smartdesk_lang', lng);
});

export default i18n;
