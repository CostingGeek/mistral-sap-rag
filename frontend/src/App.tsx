import { Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Layout from './components/Layout';
import HomePage from './views/HomePage';
import ChatPage from './views/ChatPage';
import FitGapPage from './views/FitGapPage';
import SessionsPage from './views/SessionsPage';
import ReportPage from './views/ReportPage';
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
          <Route path="chat" element={<ChatPage />} />
          <Route path="chat/:sessionId" element={<ChatPage />} />
          <Route path="fit-gap" element={<FitGapPage />} />
          <Route path="sessions" element={<SessionsPage />} />
          <Route path="report/:sessionId" element={<ReportPage />} />
          <Route path="object/:objectId" element={<ObjectPage />} />
          <Route path="decisions/:sessionId" element={<DecisionsPage />} />
        </Route>
      </Routes>
    </QueryClientProvider>
  );
}

export default App;
