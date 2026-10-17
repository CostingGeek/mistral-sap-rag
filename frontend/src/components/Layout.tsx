import { Outlet, Link, useLocation } from 'react-router-dom';
import { useApi } from '../hooks/useApi';
import { useEffect, useState } from 'react';

export default function Layout() {
  const location = useLocation();
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

  const navItems = [
    { path: '/', label: 'Home' },
    { path: '/chat', label: 'Chat' },
    { path: '/fit-gap', label: 'Fit-Gap' },
    { path: '/sessions', label: 'Sessions' },
  ];

  return (
    <div className="min-h-screen bg-ivory">
      {/* Navigation */}
      <nav className="bg-ivory border-b border-borderWarm sticky top-0 z-50">
        <div className="max-w-[1280px] mx-auto px-6 py-3">
          <div className="flex justify-between items-center">
            <div className="flex items-center">
              <Link to="/" className="flex-shrink-0 flex items-center gap-2">
                <div className="w-16 h-8 bg-block-gradient" style={{clipPath: 'polygon(0% 0%, 100% 0%, 80% 100%, 0% 100%)'}} />
              </Link>
              <div className="hidden md:ml-6 md:flex md:space-x-6">
                {navItems.map((item) => (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`text-sm uppercase tracking-widest transition-colors duration-150 ${
                      location.pathname === item.path
                        ? 'text-mistral font-medium'
                        : 'text-ink-2 hover:text-mistral'
                    }`}
                  >
                    {item.label}
                  </Link>
                ))}
              </div>
            </div>
            <Link to="/chat" className="btn-primary hidden md:inline-block">
              Start Chat
            </Link>
          </div>
        </div>
      </nav>

      {/* Main content */}
      <main className="max-w-[1280px] mx-auto py-6 px-6">
        <Outlet />
      </main>

      {/* Sunset stripe - brand signature */}
      <div className="sunset-stripe" aria-hidden="true" />

      {/* Footer */}
      <footer>
        <div className="max-w-[1280px] mx-auto py-6 px-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-center">
            <div className="text-left">
              <p className="text-xs text-ink-2">Julien Delvat - Oct. 2026</p>
            </div>
            <div className="text-center">
              <p className="text-xs uppercase tracking-widest text-mistral">Powered by Mistral AI</p>
              <p className="text-sm uppercase tracking-widest text-ink">Demo for Mistral.ai</p>
            </div>
            <div className="flex flex-col items-end gap-2">
              <p className="text-xs text-ink-2">Backend Status: {status}</p>
              <a href="http://127.0.0.1:8000/docs" className="hover:text-gold transition-colors text-sm" target="_blank" rel="noopener noreferrer">Documentation</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
