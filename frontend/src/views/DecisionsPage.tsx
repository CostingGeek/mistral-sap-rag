import { useState, useEffect, useCallback } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useApi } from '../hooks/useApi';
import { Decision } from '../types';

export default function DecisionsPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const { getDecisions, updateDecision } = useApi();
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDecisions = useCallback(async () => {
    if (!sessionId) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await getDecisions(sessionId);
      if (response.data) {
        setDecisions(response.data);
      } else if (response.error) {
        setError(response.error);
      }
    } catch (err) {
      setError('Failed to load decisions');
    } finally {
      setIsLoading(false);
    }
  }, [sessionId, getDecisions]);

  useEffect(() => {
    fetchDecisions();
  }, [fetchDecisions]);

  const handleUpdateDecision = useCallback(async (decisionId: string, status: string, answer?: string) => {
    try {
      await updateDecision(decisionId, { status, answer });
      await fetchDecisions();
    } catch (err) {
      setError('Failed to update decision');
    }
  }, [updateDecision, fetchDecisions]);

  const getStatusBadge = (status: string) => {
    const baseClasses = 'px-2 py-1 rounded-full text-xs font-medium';
    
    switch (status) {
      case 'open':
        return `${baseClasses} bg-yellow-100 text-yellow-800`;
      case 'answered':
        return `${baseClasses} bg-green-100 text-green-800`;
      case 'resolved':
        return `${baseClasses} bg-blue-100 text-blue-800`;
      default:
        return `${baseClasses} bg-gray-100 text-gray-800`;
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900">Loading Decisions...</h1>
        </div>
        <div className="card flex items-center justify-center py-12">
          <div className="animate-spin h-12 w-12 border-4 border-blue-500 border-t-transparent rounded-full"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900">Error</h1>
        </div>
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <p className="text-red-700">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Decisions</h1>
          <p className="text-gray-600 mt-1">
            Session: <span className="font-mono">{sessionId?.substring(0, 8)}...</span>
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={fetchDecisions}
            className="btn btn-secondary text-sm"
          >
            Refresh
          </button>
        </div>
      </div>

      <div className="card">
        {decisions.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <p className="text-lg">No decisions found</p>
            <p className="text-sm mt-2">
              Decisions will appear here after fit-gap analysis
            </p>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {decisions.map((decision) => (
              <DecisionCard
                key={decision.decision_id}
                decision={decision}
                onUpdate={handleUpdateDecision}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

interface DecisionCardProps {
  decision: Decision;
  onUpdate: (decisionId: string, status: string, answer?: string) => void;
}

function DecisionCard({ decision, onUpdate }: DecisionCardProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [answer, setAnswer] = useState(decision.answer || '');

  const handleSave = () => {
    onUpdate(decision.decision_id, 'answered', answer);
    setIsEditing(false);
  };

  const handleMarkResolved = () => {
    onUpdate(decision.decision_id, 'resolved');
  };

  const handleReopen = () => {
    onUpdate(decision.decision_id, 'open');
  };

  return (
    <div className="card animate-fade-in">
      <div className="flex justify-between items-start mb-3">
        <span className={getStatusBadge(decision.status)}>
          {decision.status.toUpperCase()}
        </span>
        <div className="flex gap-1">
          {decision.status === 'open' && (
            <button
              onClick={() => onUpdate(decision.decision_id, 'answered')}
              className="text-green-600 hover:text-green-800 text-sm"
              title="Mark as answered"
            >
              ✓
            </button>
          )}
          {decision.status === 'answered' && (
            <button
              onClick={handleMarkResolved}
              className="text-blue-600 hover:text-blue-800 text-sm"
              title="Mark as resolved"
            >
              ✓✓
            </button>
          )}
          {decision.status !== 'open' && (
            <button
              onClick={handleReopen}
              className="text-gray-600 hover:text-gray-800 text-sm"
              title="Reopen"
            >
              ↻
            </button>
          )}
        </div>
      </div>

      <h3 className="font-semibold mb-3">{decision.question}</h3>

      {decision.options?.length > 0 && (
        <div className="mb-3">
          <p className="text-sm font-medium text-gray-700 mb-2">Options:</p>
          <ul className="list-disc list-inside space-y-1 text-sm">
            {decision.options.map((opt, i) => (
              <li key={i}>{opt}</li>
            ))}
          </ul>
        </div>
      )}

      {decision.status === 'answered' && !isEditing && decision.answer && (
        <div className="mt-3 p-3 bg-green-50 rounded-md">
          <p className="text-sm font-medium text-green-800">Answer:</p>
          <p className="text-sm text-green-700">{decision.answer}</p>
        </div>
      )}

      {decision.status === 'answered' && isEditing && (
        <div className="mt-3">
          <textarea
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            className="input w-full text-sm"
            rows={3}
            placeholder="Enter answer..."
          />
          <div className="flex justify-end gap-2 mt-2">
            <button onClick={() => setIsEditing(false)} className="btn btn-secondary text-sm">
              Cancel
            </button>
            <button onClick={handleSave} className="btn btn-primary text-sm">
              Save
            </button>
          </div>
        </div>
      )}

      {decision.status === 'open' && (
        <div className="mt-3">
          <button
            onClick={() => setIsEditing(true)}
            className="text-sm text-blue-600 hover:text-blue-800"
          >
            + Add Answer
          </button>
        </div>
      )}

      <div className="mt-3 pt-3 border-t border-gray-200">
        <p className="text-xs text-gray-500">
          ID: {decision.decision_id.substring(0, 16)}...
        </p>
      </div>
    </div>
  );
}
