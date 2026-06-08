import { Suspense } from 'react';
import { useRoutes } from 'react-router-dom';
import { Spin } from 'antd';
import { appRoutes } from './router';

const App: React.FC = () => {
  const element = useRoutes(appRoutes);

  return (
    <Suspense fallback={<div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}><Spin size="large" /></div>}>
      {element}
    </Suspense>
  );
};

export default App;
