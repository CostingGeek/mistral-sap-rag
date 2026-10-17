import { Outlet, Link } from 'react-router-dom';
import { useApi } from '../hooks/useApi';
import { useEffect, useState } from 'react';

export default function Layout() {
  const { healthCheck } = useApi();
  const [status, setStatus] = useState<string>('checking...');

  useEffect(() => {
    const checkHealth = async () => {
      const response = await healthCheck();
      if (response.data) {
        setStatus('✓ Backend is healthy');
      } else if (response.error) {
        setStatus('✗ Backend connection failed');
      }
    };
    checkHealth();
  }, [healthCheck]);

  return (
    <div className="h-screen bg-ivory flex flex-col">
      {/* Header with title */}
      <header className="bg-ivory border-b border-borderWarm sticky top-0 z-50">
        <div className="px-6 py-3">
          <div className="flex items-center gap-4">
            <Link to="/" className="underline flex-shrink-0 flex items-center gap-2">
              <div className="w-16 h-8 bg-block-gradient" style={{clipPath: 'polygon(0% 0%, 100% 0%, 80% 100%, 0% 100%)'}} />
            </Link>
            <h1 className="text-xl font-bold text-gray-900">Chat with SAP Documentation</h1>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="py-6 px-6 flex-1 w-full">
        <Outlet />
      </main>

      {/* Sunset stripe - brand signature */}
      <div className="sunset-stripe" aria-hidden="true" />

      {/* Footer */}
      <footer>
        <div className="py-6 px-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-center">
            <div className="text-left">
              <p className="text-xs text-ink-2">
                <a href="http://julien-delvat.com/" target="_blank" rel="noopener noreferrer" className="underline hover:text-gold transition-colors">
                  Julien Delvat
                </a>
                - Oct. 2026
              </p>
            </div>
            <div className="text-center">
              <p className="text-xs uppercase tracking-widest text-mistral">Demo Powered by Mistral AI</p>
            </div>
            <div className="flex flex-col items-end gap-2">
              <a href="http://127.0.0.1:8000/docs" className="underline text-xs text-ink-2 hover:text-gold transition-colors" target="_blank" rel="noopener noreferrer">Backend Status: {status}</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
