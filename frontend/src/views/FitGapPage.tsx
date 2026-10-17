import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApi } from '../hooks/useApi';
import { Session } from '../types';

export default function FitGapPage() {
  const { uploadPdf, processPdf, createSession } = useApi();
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [session, setSession] = useState<Session | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
      setTitle(e.target.files[0].name.replace('.pdf', ''));
    }
  }, []);

  const handleUpload = useCallback(async () => {
    if (!file) {
      setError('Please select a file first');
      return;
    }

    setIsUploading(true);
    setError(null);
    setProgress(0);

    try {
      // Create session first
      const sessionResponse = await createSession('pdf', title || file.name);
      
      if (sessionResponse.error) {
        throw new Error(sessionResponse.error);
      }
      
      const newSession = sessionResponse.data;
      setSession(newSession);
      
      // Upload PDF with the session_id
      const uploadResponse = await uploadPdf(file, newSession.title, newSession.session_id);
      
      if (uploadResponse.error) {
        throw new Error(uploadResponse.error);
      }
      
      // Start processing
      const processResponse = await processPdf(newSession.session_id);
      
      if (processResponse.error) {
        throw new Error(processResponse.error);
      }
      
      // Redirect to report page
      setTimeout(() => {
        navigate(`/report/${newSession.session_id}`);
      }, 1000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setIsUploading(false);
    }
  }, [file, title, createSession, uploadPdf, processPdf, navigate]);

  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && droppedFile.type === 'application/pdf') {
      setFile(droppedFile);
      setTitle(droppedFile.name.replace('.pdf', ''));
    }
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">PDF Fit-Gap Analysis</h1>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <p className="text-gray-600 mb-6">
            Upload a requirements PDF to perform a fit-gap analysis against the SAP Customizing documentation.
            The system will extract requirements, match them against the corpus, and generate a detailed report
            with coverage statistics and open decisions.
          </p>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-md p-4 mb-4">
              <p className="text-red-700">{error}</p>
            </div>
          )}

          <div
            className={`upload-area ${file ? 'border-blue-500 bg-blue-50' : ''}`}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragOver}
          >
            <input
              type="file"
              accept=".pdf"
              onChange={handleFileChange}
              className="hidden"
              id="pdf-upload"
            />
            <label htmlFor="pdf-upload" className="cursor-pointer">
              {file ? (
                <div className="text-center">
                  <svg
                    className="mx-auto h-12 w-12 text-blue-500 mb-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                    />
                  </svg>
                  <p className="text-lg font-medium text-gray-900">{file.name}</p>
                  <p className="text-sm text-gray-500 mt-1">
                    {(file.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                  <p className="text-sm text-blue-600 mt-2">
                    Click to change or drag another file
                  </p>
                </div>
              ) : (
                <div className="text-center">
                  <svg
                    className="mx-auto h-12 w-12 text-gray-400 mb-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                    />
                  </svg>
                  <p className="text-lg font-medium text-gray-900">
                    Drop your PDF here or click to browse
                  </p>
                  <p className="text-sm text-gray-500 mt-1">
                    Only PDF files are accepted
                  </p>
                </div>
              )}
            </label>
          </div>

          <div className="mt-6">
            <label htmlFor="title" className="block text-sm font-medium text-gray-700 mb-2">
              Analysis Title
            </label>
            <input
              type="text"
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="input"
              placeholder="Enter a title for this analysis"
            />
          </div>

          <div className="mt-6">
            <button
              onClick={handleUpload}
              className="btn btn-primary w-full py-3 text-lg"
              disabled={!file || isUploading}
            >
              {isUploading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="animate-spin h-5 w-5 border-2 border-white border-t-transparent rounded-full"></span>
                  Processing...
                </span>
              ) : (
                'Start Fit-Gap Analysis'
              )}
            </button>
          </div>

          {progress > 0 && progress < 100 && (
            <div className="mt-4">
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full"
                  style={{ width: `${progress}%` }}
                ></div>
              </div>
              <p className="text-sm text-gray-500 mt-1">Processing: {progress}%</p>
            </div>
          )}

          {session && (
            <div className="mt-4 bg-gray-50 rounded-md p-4">
              <p className="text-sm text-gray-600">
                Session created: <span className="font-medium">{session.session_id}</span>
              </p>
            </div>
          )}
        </div>

        <div className="card">
          <h2 className="text-lg font-semibold mb-4">How Fit-Gap Analysis Works</h2>
          <div className="space-y-4">
          <div className="flex items-start gap-4">
            <div className="flex-shrink-0 w-10 h-10 bg-brandYellow rounded-md flex items-center justify-center text-ink font-bold text-sm">
              1
            </div>
            <div>
              <h3 className="font-medium">OCR Extraction</h3>
              <p className="text-gray-600 text-sm">
                The PDF is converted to text using Mistral OCR, which handles both digital and scanned documents.
              </p>
            </div>
          </div>

          <div className="flex items-start gap-4">
            <div className="flex-shrink-0 w-10 h-10 bg-blockOrange rounded-md flex items-center justify-center text-ink font-bold text-sm">
              2
            </div>
            <div>
              <h3 className="font-medium">Requirement Extraction</h3>
              <p className="text-gray-600 text-sm">
                Discrete, testable requirements are extracted from the text using Mistral Medium.
              </p>
            </div>
          </div>

          <div className="flex items-start gap-4">
            <div className="flex-shrink-0 w-10 h-10 bg-flame rounded-md flex items-center justify-center text-ivory font-bold text-sm">
              3
            </div>
            <div>
              <h3 className="font-medium">Matching & Verdict</h3>
              <p className="text-gray-600 text-sm">
                Each requirement is matched against the SAP Customizing corpus and assigned a verdict
                (fit, partial, gap, or question) with rationale.
              </p>
            </div>
          </div>

          <div className="flex items-start gap-4">
            <div className="flex-shrink-0 w-10 h-10 bg-mistral rounded-md flex items-center justify-center text-ivory font-bold text-sm">
              4
            </div>
            <div>
              <h3 className="font-medium">Decision Generation</h3>
              <p className="text-gray-600 text-sm">
                Open questions and scope ambiguities are identified as decisions to be discussed in workshops.
              </p>
            </div>
          </div>

          <div className="flex items-start gap-4">
            <div className="flex-shrink-0 w-10 h-10 bg-mistral rounded-md flex items-center justify-center text-ivory font-bold text-sm">
              5
            </div>
            <div>
              <h3 className="font-medium">Report Generation</h3>
              <p className="text-gray-600 text-sm">
                A comprehensive report is generated with coverage statistics, gap analysis, and workshop agenda.
              </p>
            </div>
          </div>
          </div>
        </div>
      </div>
    </div>
  );
}
