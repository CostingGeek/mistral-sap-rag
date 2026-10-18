import { useState, useEffect } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useApi } from '../hooks/useApi';

export default function ObjectPage() {
  const { objectId } = useParams<{ objectId: string }>();
  const { getObject, getObjectGraph } = useApi();
  const [objectInfo, setObjectInfo] = useState<any>(null);
  const [graphData, setGraphData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      if (!objectId) return;

      setIsLoading(true);
      setError(null);

      try {
        const [objResponse, graphResponse] = await Promise.all([
          getObject(objectId),
          getObjectGraph(objectId),
        ]);

        if (objResponse.data) {
          setObjectInfo(objResponse.data);
        }
        if (graphResponse.data) {
          setGraphData(graphResponse.data);
        }
      } catch (err) {
        setError('Failed to load object');
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [objectId, getObject, getObjectGraph]);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900">Loading...</h1>
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
          <Link to="/" className="btn btn-primary mt-4 inline-block">
            Back to Home
          </Link>
        </div>
      </div>
    );
  }

  if (!objectInfo) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900">Object Not Found</h1>
        </div>
        <div className="card text-center py-12">
          <p className="text-gray-600">
            The SAP object "{objectId}" could not be found.
          </p>
          <Link to="/" className="btn btn-primary mt-4 inline-block">
            Back to Home
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            {objectInfo.title || objectId}
          </h1>
          <p className="text-gray-600 mt-1 font-mono text-sm">
            {objectId}
          </p>
        </div>
        <Link to="/" className="btn btn-secondary text-sm">
          Back
        </Link>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Object Details */}
        <div className="lg:col-span-2">
          <div className="card">
            <h2 className="text-lg font-semibold mb-4">Documentation</h2>
            <div className="space-y-4">
              {Object.entries<string>(objectInfo.sections || {}).map(([sectionType, content]) => (
                <div key={sectionType} className="border-b border-gray-200 pb-4 last:border-0">
                  <h3 className="font-medium text-gray-700 mb-2">
                    {sectionType}
                  </h3>
                  <div className="prose prose-sm max-w-none">
                    <p className="whitespace-pre-wrap">{content}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Graph */}
        <div>
          <div className="card">
            <h2 className="text-lg font-semibold mb-4">Related Objects</h2>
            {graphData?.nodes?.length ? (
              <div className="space-y-3">
                {graphData.nodes.map((node: any) => (
                  <div
                    key={node.id}
                    className="p-3 bg-gray-50 rounded-md hover:bg-gray-100 transition-colors"
                  >
                    <Link
                      to={`/object/${encodeURIComponent(node.id)}`}
                      className="block"
                    >
                      <div className="font-medium text-blue-600 truncate">
                        {node.title || node.id}
                      </div>
                      <div className="text-xs text-gray-500 font-mono mt-1">
                        {node.id}
                      </div>
                    </Link>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 text-sm">No related objects found</p>
            )}
          </div>

          <div className="card mt-4">
            <h2 className="text-lg font-semibold mb-4">References</h2>
            {objectInfo.element_refs?.length ? (
              <div className="space-y-2">
                {objectInfo.element_refs.map((ref: string, index: number) => (
                  <div
                    key={index}
                    className="text-sm text-gray-600 flex items-center gap-2"
                  >
                    <span className="w-2 h-2 bg-gray-400 rounded-full"></span>
                    {ref}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 text-sm">No references</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
