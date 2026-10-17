import { Link } from 'react-router-dom';

export default function HomePage() {
  return (
    <div className="space-y-3">
      {/* Hero Section */}
      <section className="py-6">
        <div className="max-w-[1280px] mx-auto px-6">
          <h1 className="hero-title">
            SAP Customizing Fit-Gap RAG
          </h1>
          <p className="hero-subtitle mt-2">
            Analyze SAP Customizing requirements with AI-powered fit-gap analysis
          </p>
        </div>
      </section>

      {/* Features and How It Works - combined in a grid */}
      <section className="py-4">
        <div className="max-w-[1280px] mx-auto px-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Left side - Vertical feature cards */}
            <div className="space-y-3">
              {/* Chat Card */}
              <div className="card hover:shadow-warm transition-shadow p-4">
                <div className="flex items-center justify-between mb-3">
                  <span className="section-label"><strong>Scenario 1</strong></span>
                </div>
                <h2 className="text-h3 font-normal text-ink mb-3">
                  💬 Chat
                </h2>
                <p className="text-sm text-ink-2 mb-4 leading-relaxed">
                  Ask questions about SAP Customizing and get answers grounded in the documentation.
                </p>
                <Link to="/chat" className="btn-primary inline-block w-64 text-center">
                  Start Chat
                </Link>
              </div>

              {/* PDF Fit-Gap Card */}
              <div className="card hover:shadow-warm transition-shadow p-4">
                <div className="flex items-center justify-between mb-3">
                  <span className="section-label"><strong>Scenario 2</strong></span>
                </div>
                <h2 className="text-h3 font-normal text-ink mb-3">
                  📄 PDF Fit-Gap
                </h2>
                <p className="text-sm text-ink-2 mb-4 leading-relaxed">
                  Upload a requirements PDF and get a detailed fit-gap analysis with open decisions.
                </p>
                <Link to="/fit-gap" className="btn-primary inline-block w-64 text-center">
                  Upload PDF
                </Link>
              </div>

              {/* Sessions Card */}
              <div className="card hover:shadow-warm transition-shadow p-4">
                <div className="flex items-center justify-between mb-3">
                  <span className="section-label"><strong>History</strong></span>
                </div>
                <h2 className="text-h3 font-normal text-ink mb-3">
                  📋 Sessions
                </h2>
                <p className="text-sm text-ink-2 mb-4 leading-relaxed">
                  View and manage your previous analysis sessions.
                </p>
                <Link to="/sessions" className="btn-primary inline-block w-64 text-center">
                  View Sessions
                </Link>
              </div>
            </div>

            {/* Right side - How It Works full height */}
            <div className="bg-cream p-4 rounded-lg h-full">
                <div className="flex items-center justify-between mb-4">
                  <span className="section-label"><strong>How It Works</strong></span>
                </div>
                <div className="my-8">
                  <div className="flex items-center justify-center w-full">
                    <div className="flex-1 h-8 bg-mistral rounded-l flex items-center justify-center text-ivory font-bold text-xs px-2">
                      Agentic Retrieval
                    </div>
                    <div className="w-6 h-8 bg-mistral flex items-center justify-center">
                      <svg className="w-4 h-4 text-ivory" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clipRule="evenodd"/>
                      </svg>
                    </div>
                    <div className="flex-1 h-8 bg-flame flex items-center justify-center text-ivory font-bold text-xs px-2">
                      Fit-Gap Analysis
                    </div>
                    <div className="w-6 h-8 bg-flame flex items-center justify-center">
                      <svg className="w-4 h-4 text-ivory" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clipRule="evenodd"/>
                      </svg>
                    </div>
                    <div className="flex-1 h-8 bg-blockOrange rounded-r flex items-center justify-center text-ivory font-bold text-xs px-2">
                      Decision Tracking
                    </div>
                  </div>
                </div>
                <div className="space-y-8 pt-4">
                  <div className="flex items-start gap-3">
                    <div className="flex-shrink-0 w-8 h-8 bg-mistral rounded-md flex items-center justify-center text-ivory font-bold text-sm">
                      1
                    </div>
                    <div>
                      <h3 className="text-h3 font-normal text-ink mb-1">
                        Agentic Retrieval
                      </h3>
                      <p className="text-sm text-ink-2 leading-relaxed">
                        Questions are decomposed into sub-intents, each matched against the corpus.
                        Related objects are pulled in via deterministic graph edges.
                      </p>
                    </div>
                  </div>

                  <div className="flex items-start gap-3">
                    <div className="flex-shrink-0 w-8 h-8 bg-flame rounded-md flex items-center justify-center text-ivory font-bold text-sm">
                      2
                    </div>
                    <div>
                      <h3 className="text-h3 font-normal text-ink mb-1">
                        Fit-Gap Analysis
                      </h3>
                      <p className="text-sm text-ink-2 leading-relaxed">
                        Requirements are extracted from PDFs or transcripts and matched against
                        SAP Customizing activities to determine fit/partial/gap status.
                      </p>
                    </div>
                  </div>

                  <div className="flex items-start gap-3">
                    <div className="flex-shrink-0 w-8 h-8 bg-blockOrange rounded-md flex items-center justify-center text-ivory font-bold text-sm">
                      3
                    </div>
                    <div>
                      <h3 className="text-h3 font-normal text-ink mb-1">
                        Decision Tracking
                      </h3>
                      <p className="text-sm text-ink-2 leading-relaxed">
                        Open questions and scope ambiguities are tracked as decisions to be
                        discussed in workshops, with transcript matching to track resolution.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
          </div>
        </div>
      </section>


    </div>
  );
}
