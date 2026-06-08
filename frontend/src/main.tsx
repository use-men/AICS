import React from 'react';
import ReactDOM from 'react-dom/client';
import { Provider } from 'react-redux';
import { BrowserRouter } from 'react-router-dom';
import { ConfigProvider, App as AntdApp, theme as antdTheme } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import enUS from 'antd/locale/en_US';
import { store } from './store';
import { ThemeProvider, useTheme } from './locales/theme';
import i18n from './locales/i18n';
import App from './App';
import './shared/styles/global.css';

const AppWithProviders: React.FC = () => {
  const { mode } = useTheme();
  const lang = i18n.language;

  return (
    <ConfigProvider
      locale={lang === 'en' ? enUS : zhCN}
      theme={{
        token: { colorPrimary: '#667eea' },
        algorithm: mode === 'dark' ? antdTheme.darkAlgorithm : undefined,
      }}
    >
      <AntdApp>
        <App />
      </AntdApp>
    </ConfigProvider>
  );
};

ReactDOM.createRoot(document.getElementById('root')!).render(
  <Provider store={store}>
    <BrowserRouter>
      <ThemeProvider>
        <AppWithProviders />
      </ThemeProvider>
    </BrowserRouter>
  </Provider>,
);
