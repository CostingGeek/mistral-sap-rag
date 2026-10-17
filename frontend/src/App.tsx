import { Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Layout from './components/Layout';
import HomePage from './views/HomePage';
import ObjectPage from './views/ObjectPage';
import DecisionsPage from './views/DecisionsPage';
import './App.css';

// Create a client
const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="object/:objectId" element={<ObjectPage />} />
          <Route path="decisions/:sessionId" element={<DecisionsPage />} />
        </Route>
      </Routes>
    </QueryClientProvider>
  );
}

export default App;
