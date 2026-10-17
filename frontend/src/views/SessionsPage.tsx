import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useApi } from '../hooks/useApi';
import { Session } from '../types';

export default function SessionsPage() {
  const { listSessions, clearAllSessions } = useApi();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isClearing, setIsClearing] = useState(false);

  const fetchSessions = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await listSessions(50);
      if (response.data) {
        setSessions(response.data);
      } else if (response.error) {
        setError(response.error);
      }
    } catch (err) {
      setError('Failed to fetch sessions');
    } finally {
      setIsLoading(false);
    }
  }, [listSessions]);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  const handleClearAll = useCallback(async () => {
    if (!window.confirm('Are you sure you want to delete ALL sessions? This cannot be undone.')) {
      return;
    }
    
    setIsClearing(true);
    try {
      const response = await clearAllSessions();
      if (response.data) {
        fetchSessions();
      } else if (response.error) {
        setError(response.error);
      }
    } catch (err) {
      setError('Failed to clear sessions');
    } finally {
      setIsClearing(false);
    }
  }, [clearAllSessions, fetchSessions]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'text-green-600';
      case 'processing':
        return 'text-yellow-600';
      case 'failed':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  const getStatusBadge = (status: string) => {
    const baseClasses = 'px-2 py-1 rounded-full text-xs font-medium';
    
    switch (status) {
      case 'completed':
        return `${baseClasses} bg-green-100 text-green-800`;
      case 'processing':
        return `${baseClasses} bg-yellow-100 text-yellow-800`;
      case 'failed':
        return `${baseClasses} bg-red-100 text-red-800`;
      default:
        return `${baseClasses} bg-gray-100 text-gray-800`;
    }
  };

  const getKindBadge = (kind: string) => {
    const baseClasses = 'px-2 py-1 rounded-full text-xs font-medium';
    
    switch (kind) {
      case 'chat':
        return `${baseClasses} bg-blue-100 text-blue-800`;
      case 'pdf':
        return `${baseClasses} bg-green-100 text-green-800`;
      case 'audio':
        return `${baseClasses} bg-purple-100 text-purple-800`;
      default:
        return `${baseClasses} bg-gray-100 text-gray-800`;
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  const getActionLink = (session: Session) => {
    switch (session.kind) {
      case 'chat':
        return `/chat/${session.session_id}`;
      case 'pdf':
        return `/report/${session.session_id}`;
      case 'audio':
        return `/decisions/${session.session_id}`;
      default:
        return `#`;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Analysis Sessions</h1>
        <div className="flex gap-2">
          <Link to="/fit-gap" className="btn btn-primary">
            New Analysis
          </Link>
          <button
            onClick={handleClearAll}
            className="btn btn-danger"
            disabled={isClearing}
          >
            {isClearing ? 'Clearing...' : 'Clear All'}
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <p className="text-red-700">{error}</p>
        </div>
      )}

      <div className="card">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin h-12 w-12 border-4 border-blue-500 border-t-transparent rounded-full"></div>
          </div>
        ) : sessions.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <p className="text-lg">No sessions found</p>
            <p className="text-sm mt-2">
              Start a new analysis to see sessions here
            </p>
          </div>
        ) : (
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>Session ID</th>
                  <th>Title</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {sessions.map((session) => (
                  <tr key={session.session_id} className="animate-fade-in">
                    <td className="font-mono text-sm">
                      {session.session_id.substring(0, 8)}...
                    </td>
                    <td className="max-w-xs truncate">{session.title}</td>
                    <td>
                      <span className={getKindBadge(session.kind)}>
                        {session.kind.toUpperCase()}
                      </span>
                    </td>
                    <td>
                      <span className={getStatusBadge(session.status)}>
                        {session.status.toUpperCase()}
                      </span>
                    </td>
                    <td className="text-sm text-gray-500">
                      {formatDate(session.created_at)}
                    </td>
                    <td>
                      <Link
                        to={getActionLink(session)}
                        className="text-blue-600 hover:text-blue-800 font-medium text-sm"
                      >
                        View
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
