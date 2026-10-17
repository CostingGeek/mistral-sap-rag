import { useState, useEffect, useCallback } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useApi } from '../hooks/useApi';
import { FitGapResult, Verdict } from '../types';

export default function ReportPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const { getReport, getSession } = useApi();
  const [report, setReport] = useState<FitGapResult | null>(null);
  const [session, setSession] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'summary' | 'requirements' | 'decisions'>('summary');

  const fetchData = useCallback(async () => {
    if (!sessionId) return;

    setIsLoading(true);
    setError(null);

    try {
      // Get session info
      const sessionResponse = await getSession(sessionId);
      if (sessionResponse.data) {
        setSession(sessionResponse.data);
      }

      // Get report
      const reportResponse = await getReport(sessionId);
      if (reportResponse.data) {
        setReport(reportResponse.data);
      } else if (reportResponse.error) {
        // Only set error if it's not a "not ready" message
        if (reportResponse.error && !reportResponse.error.toLowerCase().includes('not ready')) {
          setError(reportResponse.error);
        }
      }
    } catch (err) {
      setError('Failed to load report');
    } finally {
      setIsLoading(false);
    }
  }, [sessionId, getSession, getReport]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    // Poll for report if processing
    if (session?.status === 'processing') {
      const interval = setInterval(fetchData, 5000);
      return () => clearInterval(interval);
    }
  }, [session, fetchData]);

  const getVerdictBadge = (verdict: Verdict) => {
    const baseClasses = 'verdict-badge';
    
    switch (verdict) {
      case 'fit':
        return `${baseClasses} verdict-fit`;
      case 'partial':
        return `${baseClasses} verdict-partial`;
      case 'gap':
        return `${baseClasses} verdict-gap`;
      case 'question':
        return `${baseClasses} verdict-question`;
      default:
        return baseClasses;
    }
  };

  const formatPercentage = (value: number) => {
    return `${(value * 100).toFixed(1)}%`;
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900">Loading Report...</h1>
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
          <h1 className="text-2xl font-bold text-gray-900">Report Error</h1>
        </div>
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <p className="text-red-700">{error}</p>
        </div>
      </div>
    );
  }

  if (!report && session?.status === 'processing') {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900">Processing...</h1>
        </div>
        <div className="card text-center py-12">
          <div className="animate-spin h-12 w-12 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-4"></div>
          <p className="text-gray-600">Processing your PDF and generating fit-gap analysis...</p>
          <p className="text-sm text-gray-500 mt-2">This may take a few minutes</p>
        </div>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900">Report Not Found</h1>
        </div>
        <div className="card text-center py-12">
          <p className="text-gray-600">The report for this session could not be found.</p>
          <Link to="/sessions" className="btn btn-primary mt-4 inline-block">
            Back to Sessions
          </Link>
        </div>
      </div>
    );
  }

  const tabClasses = (tab: string) => `
    px-4 py-2 text-sm font-medium rounded-md transition-colors
    ${activeTab === tab 
      ? 'bg-blue-600 text-white' 
      : 'text-gray-600 hover:bg-gray-100'
    }
  `;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Fit-Gap Analysis Report
          </h1>
          <p className="text-gray-600 mt-1">
            Session: <span className="font-mono">{sessionId?.substring(0, 8)}...</span>
          </p>
        </div>
        <div className="flex gap-2">
          <Link to="/sessions" className="btn btn-secondary text-sm">
            Back to Sessions
          </Link>
          <button className="btn btn-secondary text-sm">
            Export CSV
          </button>
          <button className="btn btn-secondary text-sm">
            Export Markdown
          </button>
        </div>
      </div>

      {/* Status Bar */}
      <div className="card">
        <div className="grid grid-cols-4 gap-6">
          <div className="text-center">
            <div className="text-3xl font-bold text-gray-900">
              {report.stats.total_requirements || 0}
            </div>
            <div className="text-sm text-gray-600">Total Requirements</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-green-600">
              {formatPercentage(report.stats.coverage_percentage / 100)}
            </div>
            <div className="text-sm text-gray-600">Coverage</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-red-600">
              {formatPercentage(report.stats.gap_percentage / 100)}
            </div>
            <div className="text-sm text-gray-600">Gap Rate</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-purple-600">
              {report.decisions?.length || 0}
            </div>
            <div className="text-sm text-gray-600">Open Decisions</div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="card">
        <div className="border-b border-gray-200 mb-6">
          <nav className="flex space-x-2">
            <button
              onClick={() => setActiveTab('summary')}
              className={tabClasses('summary')}
            >
              Executive Summary
            </button>
            <button
              onClick={() => setActiveTab('requirements')}
              className={tabClasses('requirements')}
            >
              Requirements ({report.requirements?.length || 0})
            </button>
            <button
              onClick={() => setActiveTab('decisions')}
              className={tabClasses('decisions')}
            >
              Decisions ({report.decisions?.length || 0})
            </button>
          </nav>
        </div>

        {/* Tab Content */}
        {activeTab === 'summary' && (
          <div className="prose max-w-none">
            <h2 className="text-xl font-semibold mb-4">Executive Summary</h2>
            <div className="bg-gray-50 rounded-md p-6 whitespace-pre-wrap">
              {report.summary}
            </div>

            <h2 className="text-xl font-semibold mb-4 mt-8">Coverage Breakdown</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {Object.entries(report.stats.verdict_counts || {}).map(([verdict, count]) => (
                <div key={verdict} className="card text-center">
                  <div className="text-2xl font-bold">
                    {count as number}
                  </div>
                  <div className={`text-sm font-medium mt-1 ${getVerdictBadge(verdict as Verdict)}`}>
                    {verdict}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'requirements' && (
          <div className="space-y-4">
            <div className="table-container">
              <table className="table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Requirement</th>
                    <th>Verdict</th>
                    <th>Matched Objects</th>
                    <th>Rationale</th>
                  </tr>
                </thead>
                <tbody>
                  {report.requirements?.map((req) => {
                    const match = report.matches?.find(m => m.req_id === req.req_id);
                    return (
                      <tr key={req.req_id} className="animate-fade-in">
                        <td className="font-mono text-sm">{req.req_id}</td>
                        <td className="max-w-md">{req.text}</td>
                        <td>
                          {match && (
                            <span className={getVerdictBadge(match.verdict as Verdict)}>
                              {match.verdict}
                            </span>
                          )}
                        </td>
                        <td className="text-sm">
                          {match?.matched_objects?.join(', ') || '-'}<br />
                          {match?.matched_objects?.length && (
                            <span className="text-xs text-gray-500">
                              {match.matched_objects.length} objects
                            </span>
                          )}
                        </td>
                        <td className="text-sm text-gray-600 max-w-md">
                          {match?.rationale || '-'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === 'decisions' && (
          <div className="space-y-4">
            {report.decisions?.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                <p>No decisions identified in this analysis</p>
              </div>
            ) : (
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {report.decisions?.map((decision) => (
                  <div key={decision.decision_id} className="card">
                    <h3 className="font-semibold mb-2">{decision.question}</h3>
                    <div className="mb-3">
                      <span className="badge bg-purple-100 text-purple-800">
                        {decision.status}
                      </span>
                    </div>
                    {decision.options?.length > 0 && (
                      <div className="space-y-2">
                        <p className="text-sm font-medium text-gray-700">Options:</p>
                        <ul className="list-disc list-inside space-y-1 text-sm">
                          {decision.options.map((opt, i) => (
                            <li key={i}>{opt}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {decision.answer && (
                      <div className="mt-3 p-3 bg-green-50 rounded-md">
                        <p className="text-sm font-medium text-green-800">Answer:</p>
                        <p className="text-sm text-green-700">{decision.answer}</p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
