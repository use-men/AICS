import { Suspense } from 'react';
import { useRoutes } from 'react-router-dom';
import { ConfigProvider, Spin } from 'antd';
import { appRoutes } from './router';

const App: React.FC = () => {
  const element = useRoutes(appRoutes);

  return (
    <ConfigProvider theme={{ token: { colorPrimary: '#667eea' } }}>
      <Suspense fallback={<div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}><Spin size="large" /></div>}>
        {element}
      </Suspense>
    </ConfigProvider>
  );
};

export default App;
