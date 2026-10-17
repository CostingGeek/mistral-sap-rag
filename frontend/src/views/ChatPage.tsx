import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { useApi } from "../hooks/useApi";
import { ChatMessage, ChatResponse } from "../types";

export default function ChatPage() {
  const { chat, getObject } = useApi();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [graphData, setGraphData] = useState<any>(null);
  const [showGraph, setShowGraph] = useState(false);
  const [graphZoom, setGraphZoom] = useState(1);
  const [fullscreenGraph, setFullscreenGraph] = useState(false);
  const [showCitationPopup, setShowCitationPopup] = useState(false);
  const [citationContent, setCitationContent] = useState('');
  const [citationTitle, setCitationTitle] = useState('');
  const [isLoadingCitation, setIsLoadingCitation] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      role: "user",
      content: input.trim(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await chat({
        message: input.trim(),
        session_id: sessionId || undefined,
        history: messages.filter(
          (m) => m.role === "user" || m.role === "assistant",
        ),
      });

      if (response.data) {
        const chatResponse: ChatResponse = response.data;

        // Set session ID if this is the first message
        if (!sessionId && chatResponse.session_id) {
          setSessionId(chatResponse.session_id);
        }

        // Set graph data if available
        if (chatResponse.graph_data) {
          setGraphData(chatResponse.graph_data);
          setGraphZoom(1); // Reset zoom when new graph arrives
          setShowGraph(true);
        }

        const assistantMessage: ChatMessage = {
          role: "assistant",
          content: chatResponse.message,
          citations: chatResponse.citations,
        };

        setMessages((prev) => [...prev, assistantMessage]);
        setShowGraph(!!chatResponse.graph_data);
      }
    } catch (error) {
      console.error("Chat error:", error);
      const errorMessage: ChatMessage = {
        role: "assistant",
        content: "Sorry, I encountered an error processing your request.",
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleCitationClick = async (citation: any) => {
    setIsLoadingCitation(true);
    setShowCitationPopup(true);
    setCitationTitle(`${citation.title || 'Reference'} (${citation.object_id})`);
    setCitationContent('Loading reference details...\n\nPlease wait...');
    
    try {
      // Try to fetch full content from API
      const response = await getObject(citation.object_id);
      
      if (response.data) {
        const content = response.data;
        // Set the title from the actual content
        setCitationTitle(`${content.title || citation.title || 'Reference'} (${content.object_id || citation.object_id})`);
        
        // Format the content with bold section titles
        const sections = content.sections || {};
        
        let fullContent = '';
        
        // Add formatted sections with bold titles
        if (Object.keys(sections).length > 0) {
          for (const [sectionKey, sectionValue] of Object.entries(sections)) {
            if (typeof sectionValue === 'string' && sectionValue.trim()) {
              fullContent += `**${sectionKey}:**\n${sectionValue}\n\n`;
            }
          }
        }
        
        setCitationContent(fullContent);
      } else {
        // Fallback to basic info
        setCitationTitle(`${citation.title || 'Reference'} (${citation.object_id})`);
        const fullContent = citation?.content || citation?.text || citation.title || 'No content available';
        setCitationContent(fullContent);
      }
    } catch (error) {
      console.error('Error fetching citation details:', error);
      // Fallback to basic info
      setCitationTitle(`${citation.title || 'Reference'} (${citation.object_id})`);
      const fullContent = citation?.content || citation?.text || citation.title || 'No content available';
      setCitationContent(fullContent);
    } finally {
      setIsLoadingCitation(false);
    }
  };

  const formatCitation = (citation: any, index: number) => (
    <div key={index} className="citation">
      <strong>Source {index + 1}:</strong> {citation.title} (
      <button
        className="text-blue-600 hover:text-blue-800 underline cursor-pointer bg-transparent border-none p-0 font-mono"
        onClick={async (e) => {
          e.stopPropagation();
          await handleCitationClick(citation);
        }}
      >
        {citation.object_id}
      </button>) - {citation.section_type}
      <div className="text-xs mt-1 opacity-70">
        Similarity: {(1 - citation.distance).toFixed(3)}
      </div>
    </div>
  );

  // Markdown to React element renderer
  const renderMarkdown = (text: string): React.ReactNode => {
    if (!text || typeof text !== 'string') return text;

    // Split by lines and process each line
    const lines = text.split('\n');
    const elements: React.ReactNode[] = [];
    let inList = false;
    let listItems: React.ReactNode[] = [];
    let currentListType: 'ordered' | 'unordered' | null = null;
    let currentListIndent = '';
    let parentListType: 'ordered' | 'unordered' | null = null;
    let parentListIndent = '';
    let inTable = false;
    let inTableHeader = true;
    let tableRows: React.ReactNode[] = [];
    let headerRows: React.ReactNode[] = [];
    let bodyRows: React.ReactNode[] = [];
    let inCodeBlock = false;
    let codeBlockContent: string[] = [];
    let blankLineCount = 0;
    let lastWasList = false;

    const flushList = () => {
      if (listItems.length > 0) {
        elements.push(currentListType === 'ordered' ? <ol key={elements.length} className="list-decimal list-inside pl-6 space-y-2">{...listItems}</ol> : <ul key={elements.length} className="list-disc list-inside pl-6 space-y-2">{...listItems}</ul>);
        listItems = [];
        currentListType = null;
        currentListIndent = '';
      }
      inList = false;
      // Also clear parent list tracking when flushing
      parentListType = null;
      parentListIndent = '';
    };

    const flushTable = () => {
      if (tableRows.length > 0) {
        elements.push(<table key={elements.length} className="w-full border-collapse my-4 text-sm">
          {headerRows.length > 0 ? (
            <thead className="bg-gray-50">
              {headerRows}
            </thead>
          ) : null}
          <tbody>
            {bodyRows}
          </tbody>
        </table>);
        tableRows = [];
        headerRows = [];
        bodyRows = [];
      }
      inTable = false;
    };

    const flushCodeBlock = () => {
      if (inCodeBlock && codeBlockContent.length > 0) {
        elements.push(<pre key={elements.length} className="bg-gray-100 p-4 rounded my-4 overflow-x-auto text-sm font-mono"><code>{codeBlockContent.join('\n')}</code></pre>);
        codeBlockContent = [];
      }
      inCodeBlock = false;
    };

    for (const line of lines) {
      const trimmed = line.trim();
      
      if (!trimmed) {
        // Empty line - track it but don't immediately flush lists
        // This allows lists to continue after blank lines
        blankLineCount++;
        flushTable();
        flushCodeBlock();
        continue;
      }

      // Reset blank line tracking for non-empty lines
      if (blankLineCount > 0) {
        lastWasList = inList;
        blankLineCount = 0;
      }

      // Check for code block (lines starting with ```)
      if (trimmed.startsWith('```')) {
        flushList();
        flushTable();
        if (inCodeBlock) {
          // Closing code block
          flushCodeBlock();
        } else {
          // Opening code block
          inCodeBlock = true;
          codeBlockContent = [];
        }
        continue;
      }

      if (inCodeBlock) {
        codeBlockContent.push(line);
        continue;
      }

      // Check for horizontal rule (--- or ===)
      if (/^[-=]{3,}$/.test(trimmed)) {
        flushList();
        flushTable();
        elements.push(<hr key={elements.length} className="my-6 border-t border-gray-300" />);
        continue;
      }

      // Check for headers (lines starting with #)
      const headerMatch = trimmed.match(/^(#{1,6})\s+(.*)/);
      if (headerMatch) {
        flushList();
        flushTable();
        const level = headerMatch[1].length;
        const content = headerMatch[2];
        const HeaderTag = `h${Math.min(level, 6)}` as const;
        elements.push(<HeaderTag key={elements.length} className={`text-h${Math.min(level, 6)} font-bold mb-4 mt-6`}>{processInlineMarkdown(content)}</HeaderTag>);
        continue;
      }

      // Check for table row (starts with |)
      const isTableRow = trimmed.startsWith('|') && trimmed.includes('|');
      
      if (isTableRow) {
        flushList();
        if (!inTable) {
          flushTable();
          inTable = true;
        }
        
        // Parse table cells
        // Remove leading/trailing pipes and split by pipe
        const cells = trimmed.slice(1, -1).split('|').map(c => c.trim());
        
        // Check if this is a separator row (e.g., |---|---| or |:---:|:---:|)
        const isSeparator = cells.every(cell => /^:?-+:?$/.test(cell));
        
        if (isSeparator) {
          // Separator indicates previous row was header, next rows are body
          inTableHeader = false;
          continue;
        }
        
        const rowCells = cells.map((cell, i) => (
          <td key={i} className="border border-gray-300 p-2 text-left">
            {processInlineMarkdown(cell)}
          </td>
        ));
        
        const row = <tr key={tableRows.length}>{rowCells}</tr>;
        
        if (inTableHeader) {
          headerRows.push(row);
        } else {
          bodyRows.push(row);
        }
        
        tableRows.push(row);
      } else {
        // Not a table row, check for lists
        flushTable();
        inTable = false;
        
        // Check for ordered list items (e.g., "1. " or "2)" or indented "   1. ")
        const orderedMatch = trimmed.match(/^(\s*)(\d+)\.\s+(.*)/) || trimmed.match(/^(\s*)(\d+)\)\s+(.*)/);
        // Check for unordered list items (e.g., "- " or "* " or indented "   - ")
        const unorderedMatch = trimmed.match(/^(\s*)[-*•]\s+(.*)/);

        if (orderedMatch || unorderedMatch) {
          const isOrdered = !!orderedMatch;
          const content = isOrdered && orderedMatch ? orderedMatch[3] : unorderedMatch ? unorderedMatch[2] : '';
          const indent = isOrdered && orderedMatch ? orderedMatch[1] : unorderedMatch ? unorderedMatch[1] : '';
          const newListType = isOrdered ? 'ordered' : 'unordered';

          // Reset blank line tracking when we see a list item
          blankLineCount = 0;

          if (!inList) {
            // If we had a list before blank lines, check if we can continue it
            if (lastWasList) {
              // Check if this matches the parent list type and has same or less indentation
              if (parentListType === newListType && indent.length <= parentListIndent.length) {
                // Return to parent list
                currentListType = parentListType;
                currentListIndent = parentListIndent;
                parentListType = null;
                parentListIndent = '';
                inList = true;
              } else if (currentListType === newListType) {
                // Continue the same list
                inList = true;
              } else {
                // Start a new list
                flushList();
                currentListType = newListType;
                currentListIndent = indent;
                inList = true;
              }
            } else {
              // Start a new list
              flushList();
              currentListType = newListType;
              currentListIndent = indent;
              inList = true;
            }
          } else if (currentListType !== newListType) {
            // Type changed - check if this is a nested list or a parent list
            if (indent.length > currentListIndent.length) {
              // This is a nested list - remember current as parent
              parentListType = currentListType;
              parentListIndent = currentListIndent;
              flushList();
              currentListType = newListType;
              currentListIndent = indent;
            } else if (indent.length <= currentListIndent.length) {
              // This is same or less indentation - check if it matches parent
              flushList();
              if (parentListType === newListType && indent.length <= parentListIndent.length) {
                // Return to parent list
                currentListType = parentListType;
                currentListIndent = parentListIndent;
                parentListType = null;
                parentListIndent = '';
              } else {
                // Start new list at this level
                currentListType = newListType;
                currentListIndent = indent;
              }
            } else {
              // Same indentation, different type - start new list
              flushList();
              currentListType = newListType;
              currentListIndent = indent;
            }
          } else if (indent.length !== currentListIndent.length) {
            // Same type but different indentation - this shouldn't happen in valid markdown
            // but handle it gracefully
            flushList();
            currentListType = newListType;
            currentListIndent = indent;
          }

          // Process the content for inline markdown
          const processedContent = processInlineMarkdown(content);
          listItems.push(<li key={listItems.length} className={indent ? 'ml-6' : ''}>{processedContent}</li>);
        } else {
          // Only flush list if we're not in a list with blank lines
          if (!lastWasList || blankLineCount === 0) {
            flushList();
          }
          lastWasList = false;
          blankLineCount = 0;
          // Process as paragraph with inline markdown
          if (trimmed) {
            const processedContent = processInlineMarkdown(trimmed);
            elements.push(<p key={elements.length} className="mb-4">{processedContent}</p>);
          }
        }
      }
    }

    flushList();
    flushTable();
    flushCodeBlock();
    return <>{elements}</>;
  };

  // Process inline markdown (bold, italic, code)
  const processInlineMarkdown = (text: string): React.ReactNode => {
    if (!text) return text;

    // Clean up markdown link syntax [text](url) -> text, and [Source X] -> Source X
    let cleanedText = text.replace(/\[([^\]]+)\](\([^\)]+\))?/g, '$1'); // [text](url) -> text, [Source X] -> Source X

    // Process inline code first (backticks)
    const codeParts = cleanedText.split(/(`[^`\n]+`)/);
    const result: React.ReactNode[] = [];

    for (let i = 0; i < codeParts.length; i++) {
      const part = codeParts[i];
      if (!part) continue;

      // Check if this part is wrapped in backticks
      if (part.startsWith('`') && part.endsWith('`')) {
        result.push(<code key={i} className="bg-gray-100 px-1 rounded text-xs font-mono">{part.slice(1, -1)}</code>);
      } else {
        // Split by ** for bold
        const boldParts = part.split(/(\*\*.*?\*\*)/);
        
        for (let j = 0; j < boldParts.length; j++) {
          const boldPart = boldParts[j];
          if (!boldPart) continue;

          // Check if this part is wrapped in **
          if (boldPart.startsWith('**') && boldPart.endsWith('**')) {
            const boldText = boldPart.slice(2, -2);
            // Check for italic inside bold
            const italicParts = boldText.split(/(\*.*?\*)/);
            const boldContent: React.ReactNode[] = [];
            for (let k = 0; k < italicParts.length; k++) {
              const subPart = italicParts[k];
              if (!subPart) continue;
              if (subPart.startsWith('*') && subPart.endsWith('*')) {
                boldContent.push(<em key={k}>{subPart.slice(1, -1)}</em>);
              } else {
                boldContent.push(subPart);
              }
            }
            result.push(<strong key={`${i}-${j}`}>{boldContent}</strong>);
          } else {
            // Process italic in regular text
            const italicParts = boldPart.split(/(\*.*?\*)/);
            for (let k = 0; k < italicParts.length; k++) {
              const subPart = italicParts[k];
              if (!subPart) continue;
              if (subPart.startsWith('*') && subPart.endsWith('*')) {
                result.push(<em key={`${i}-${j}-${k}`}>{subPart.slice(1, -1)}</em>);
              } else {
                result.push(subPart);
              }
            }
          }
        }
      }
    }

    return <>{result}</>;
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">
          Chat with SAP Documentation
        </h1>
        <div className="flex gap-2">
          <button
            onClick={() => setShowGraph(!showGraph)}
            className="btn btn-secondary px-4 py-2 text-sm"
            disabled={!graphData}
          >
            {showGraph ? "Hide Graph" : "Show Graph"}
          </button>
          <button
            onClick={() => {
              setMessages([]);
              setSessionId(null);
              setGraphData(null);
              setShowGraph(false);
            }}
            className="btn btn-secondary px-4 py-2 text-sm"
          >
            New Chat
          </button>
        </div>
      </div>

      {showGraph && graphData && (
        <div className="card">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold">Knowledge Graph</h2>
            <div className="flex gap-2">
              <button
                onClick={() => setGraphZoom(z => Math.min(z + 0.2, 2))}
                className="p-1 rounded hover:bg-gray-100 transition-colors"
                title="Zoom in"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10"/>
                  <line x1="12" y1="8" x2="12" y2="16"/>
                  <line x1="8" y1="12" x2="16" y2="12"/>
                </svg>
              </button>
              <button
                onClick={() => setGraphZoom(z => Math.max(z - 0.2, 0.5))}
                className="p-1 rounded hover:bg-gray-100 transition-colors"
                title="Zoom out"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10"/>
                  <line x1="12" y1="8" x2="12" y2="16"/>
                </svg>
              </button>
              <button
                onClick={() => setGraphZoom(1)}
                className="p-1 rounded hover:bg-gray-100 transition-colors"
                title="Reset zoom"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
                  <path d="M3 3v5h5"/>
                </svg>
              </button>
              <button
                onClick={() => setFullscreenGraph(!fullscreenGraph)}
                className="p-1 rounded hover:bg-gray-100 transition-colors"
                title={fullscreenGraph ? "Exit fullscreen" : "Fullscreen"}
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  {fullscreenGraph ? (
                    <>
                      <line x1="18" y1="6" x2="6" y2="18"/>
                      <line x1="6" y1="6" x2="18" y2="18"/>
                    </>
                  ) : (
                    <path d="M14 11h-4v-4m0 0L8 7m6 4v4h4M6 13v4h4M18 11h4v-4M6 17h4v4"/>
                  )}
                </svg>
              </button>
            </div>
          </div>
          <div className={`graph-container ${fullscreenGraph ? 'fullscreen' : ''}`}>
            <GraphView nodes={graphData.nodes} edges={graphData.edges} zoom={graphZoom} />
            {fullscreenGraph && (
              <div className="graph-controls">
                <button
                  onClick={() => setGraphZoom(z => Math.min(z + 0.2, 3))}
                  title="Zoom in"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10"/>
                    <line x1="12" y1="8" x2="12" y2="16"/>
                    <line x1="8" y1="12" x2="16" y2="12"/>
                  </svg>
                </button>
                <button
                  onClick={() => setGraphZoom(z => Math.max(z - 0.2, 0.3))}
                  title="Zoom out"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10"/>
                    <line x1="12" y1="8" x2="12" y2="16"/>
                  </svg>
                </button>
                <button
                  onClick={() => setGraphZoom(1)}
                  title="Reset zoom"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
                    <path d="M3 3v5h5"/>
                  </svg>
                </button>
                <button
                  onClick={() => setFullscreenGraph(false)}
                  title="Exit fullscreen"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="18" y1="6" x2="6" y2="18"/>
                    <line x1="6" y1="6" x2="18" y2="18"/>
                  </svg>
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      <div className="card flex-1">
        <div className="h-[60vh] overflow-y-auto space-y-4">
          {messages.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <p className="text-lg">Start a conversation</p>
              <p className="text-sm mt-2">
                Ask questions about SAP Customizing, e.g., "What do I need to
                configure for dangerous goods transport?"
              </p>
            </div>
          ) : (
            messages.map((message, index) => (
              <div
                key={index}
                className={`chat-message ${message.role} animate-fade-in`}
              >
                <div className="font-medium text-sm mb-1">
                  {message.role === "user" ? "You" : "Assistant"}
                </div>
                <div className="whitespace-pre-wrap markdown-content">
                  {message.role === "assistant" ? renderMarkdown(message.content) : message.content}
                </div>
                {message.citations && message.citations.length > 0 && (
                  <div className="mt-3 space-y-2">
                    <div className="text-xs font-medium text-gray-500 mb-1">
                      Sources:
                    </div>
                    {message.citations.map((citation, i) =>
                      formatCitation(citation, i),
                    )}
                  </div>
                )}
              </div>
            ))
          )}
          {isLoading && (
            <div className="chat-message assistant">
              <div className="flex items-center gap-2">
                <div className="animate-spin h-5 w-5 border-2 border-blue-500 border-t-transparent rounded-full"></div>
                <span>Thinking...</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="mt-4 border-t pt-4">
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question about SAP Customizing..."
              className="input flex-1"
              disabled={isLoading}
            />
            <button
              onClick={handleSend}
              className="btn btn-primary px-6 py-2"
              disabled={!input.trim() || isLoading}
            >
              Send
            </button>
          </div>
          <p className="text-xs text-gray-500 mt-2">
            Press Enter to send, Shift+Enter for new line
          </p>
        </div>
      </div>
      
      {/* Citation popup */}
      {showCitationPopup && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
          onClick={() => !isLoadingCitation && setShowCitationPopup(false)}
        >
          <div 
            className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6 border-b border-gray-200 flex justify-between items-center sticky top-0 bg-white z-10">
              <h3 className="font-semibold text-lg">{citationTitle || 'Reference Details'}</h3>
              {isLoadingCitation && (
                <div className="flex items-center gap-2">
                  <div className="animate-spin h-5 w-5 border-2 border-blue-500 border-t-transparent rounded-full"></div>
                  <span className="text-sm text-gray-600">Loading...</span>
                </div>
              )}
              <button 
                className="text-gray-500 hover:text-gray-700 text-2xl font-bold"
                onClick={() => !isLoadingCitation && setShowCitationPopup(false)}
                disabled={isLoadingCitation}
              >
                &times;
              </button>
            </div>
            <div className="p-6">
              {isLoadingCitation ? (
                <div className="flex flex-col items-center justify-center py-12">
                  <div className="animate-spin h-12 w-12 border-4 border-blue-500 border-t-transparent rounded-full mb-4"></div>
                  <p className="text-gray-600">Loading reference details...</p>
                </div>
              ) : (
                // Format content with markdown rendering
                <div className="text-sm leading-relaxed markdown-content">
                  {renderMarkdown(citationContent)}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Simple graph visualization component
function GraphView({ nodes, edges, zoom: externalZoom }: { nodes: any[]; edges: any[]; zoom?: number }) {
  // Layout configuration
  const centerX = 400;
  const centerY = 200;
  const minRadius = 250;
  const maxRadius = 350;
  
  // Calculate node positions in a circle layout
  const nodePositions = useMemo(() => {
    const positions: Record<string, { x: number; y: number }> = {};
    const radius = Math.min(maxRadius, Math.max(minRadius, 400 - Math.min(100, nodes.length * 5)));
    
    nodes.forEach((node, i) => {
      const angle = (i * 2 * Math.PI) / nodes.length;
      positions[node.id] = {
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle)
      };
    });
    
    return positions;
  }, [nodes]);
  
  // Calculate bounding box for all nodes and edges
  const boundingBox = useMemo(() => {
    if (nodes.length === 0) {
      return { minX: 0, minY: 0, maxX: 800, maxY: 400 };
    }
    
    // Get all node positions
    const allX: number[] = [];
    const allY: number[] = [];
    
    Object.values(nodePositions).forEach(pos => {
      allX.push(pos.x - 40, pos.x + 40); // Account for node radius
      allY.push(pos.y - 40, pos.y + 40);
    });
    
    // Add edge endpoints
    edges.forEach(edge => {
      const sourcePos = nodePositions[edge.source];
      const targetPos = nodePositions[edge.target];
      if (sourcePos) {
        allX.push(sourcePos.x);
        allY.push(sourcePos.y);
      }
      if (targetPos) {
        allX.push(targetPos.x);
        allY.push(targetPos.y);
      }
    });
    
    const minX = Math.min(...allX);
    const minY = Math.min(...allY);
    const maxX = Math.max(...allX);
    const maxY = Math.max(...allY);
    
    // Add padding
    const padding = 60;
    return {
      minX: minX - padding,
      minY: minY - padding,
      maxX: maxX + padding,
      maxY: maxY + padding
    };
  }, [nodes, edges, nodePositions]);
  
  // Calculate viewBox dimensions
  const viewBoxWidth = boundingBox.maxX - boundingBox.minX;
  const viewBoxHeight = boundingBox.maxY - boundingBox.minY;
  const viewBox = `${boundingBox.minX} ${boundingBox.minY} ${viewBoxWidth} ${viewBoxHeight}`;
  
  // Calculate auto-zoom to fit all content
  const autoZoom = useMemo(() => {
    const containerWidth = 800;
    const containerHeight = 400;
    
    // Calculate scale factors for both dimensions
    const scaleX = containerWidth / viewBoxWidth;
    const scaleY = containerHeight / viewBoxHeight;
    
    // Use the smaller scale to ensure everything fits
    return Math.min(scaleX, scaleY) * 0.95; // Add 5% margin
  }, [viewBoxWidth, viewBoxHeight]);
  
  const effectiveZoom = externalZoom !== undefined ? externalZoom * autoZoom : autoZoom;

  return (
    <div className="w-full h-full p-4" style={{ overflow: 'visible' }}>
      <div style={{ 
        transform: `scale(${effectiveZoom})`, 
        transformOrigin: 'center center', 
        transition: 'transform 0.2s ease', 
        width: '100%', 
        height: '100%',
        overflow: 'visible'
      }}>
        <svg 
          width="100%" 
          height="100%" 
          viewBox={viewBox}
          preserveAspectRatio="xMidYMid meet"
          style={{ overflow: 'visible' }}
        >
          {/* Draw edges first (behind nodes) */}
          {edges.map((edge) => {
            const sourcePos = nodePositions[edge.source];
            const targetPos = nodePositions[edge.target];

            if (!sourcePos || !targetPos) return null;

            return (
              <line
                key={`${edge.source}-${edge.target}`}
                x1={sourcePos.x}
                y1={sourcePos.y}
                x2={targetPos.x}
                y2={targetPos.y}
                stroke="#666"
                strokeWidth="2"
                strokeDasharray="5,5"
              />
            );
          })}

          {/* Draw nodes */}
          {nodes.map((node) => {
            const pos = nodePositions[node.id];
            if (!pos) return null;

            // Split text into multiple lines for better readability
            const displayText = node.title || node.id;
            const lines: string[] = [];
            const maxCharsPerLine = 20;
            for (let i = 0; i < displayText.length; i += maxCharsPerLine) {
              lines.push(displayText.substring(i, i + maxCharsPerLine));
            }

            return (
              <g key={node.id} transform={`translate(${pos.x}, ${pos.y})`}>
                <circle cx="0" cy="0" r="40" fill="#3b82f6" />
                {lines.map((line, lineIndex) => (
                  <text
                    key={lineIndex}
                    x="0"
                    y={lineIndex * 16 - (lines.length * 16) / 2 + 8}
                    textAnchor="middle"
                    fill="black"
                    fontSize="11"
                    style={{ fontWeight: 500 }}
                  >
                    {line}
                  </text>
                ))}
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}
