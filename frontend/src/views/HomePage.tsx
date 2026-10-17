import { useState, useRef, useEffect, useCallback } from "react";
import { useApi } from "../hooks/useApi";
import { ChatMessage, ChatResponse } from "../types";


export default function HomePage() {
  const { chat, getObject } = useApi();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
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

        const assistantMessage: ChatMessage = {
          role: "assistant",
          content: chatResponse.message,
          citations: chatResponse.citations,
        };

        setMessages((prev) => [...prev, assistantMessage]);
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

  const handleReset = () => {
    setMessages([]);
    setInput("");
    setSessionId(null);
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
    let listItems: {number?: number, content: React.ReactNode}[] = [];
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
        if (currentListType === 'ordered') {
          // For ordered lists, find the minimum number to use as start
          const numbers = listItems.map(item => item.number).filter((n): n is number => n !== undefined);
          const start = numbers.length > 0 ? Math.min(...numbers) : undefined;
          const olProps: any = { key: elements.length, className: "list-decimal list-inside pl-6 space-y-2" };
          if (start !== undefined) {
            olProps.start = start;
          }
          elements.push(<ol {...olProps}>{listItems.map(item => item.content)}</ol>);
        } else {
          elements.push(<ul key={elements.length} className="list-disc list-inside pl-6 space-y-2">{listItems.map(item => item.content)}</ul>);
        }
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
          const listNumber = isOrdered && orderedMatch ? parseInt(orderedMatch[2], 10) : undefined;

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
          listItems.push({ number: listNumber, content: <li key={listItems.length} className={indent ? 'ml-6' : ''}>{processedContent}</li> });
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
    <div className="flex flex-col h-[calc(100vh-200px)]">
      <div className="bg-white border border-borderWarm rounded-lg flex flex-col flex-1 min-h-0 overflow-hidden">
        {messages.length === 0 && (
          <div className="text-center py-4 text-gray-700 flex-shrink-0 border-b">
            <p className="text-lg">Start a conversation</p>
            <p className="text-sm mt-2">
              Ask questions about SAP Customizing, e.g., "What do I need to
              configure for dangerous goods transport?"
            </p>
          </div>
        )}
        <div className="overflow-y-auto space-y-4 p-4 flex-1 min-h-0">
          {messages.length > 0 && (
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
            <div className="chat-message assistant pr-4">
              <div className="flex items-center gap-2">
                <div className="animate-spin h-5 w-5 border-2 border-blue-500 border-t-transparent rounded-full"></div>
                <span>Thinking...</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="border-t p-4 flex-shrink-0">
          <div className="flex flex-col gap-1">
            <div className="flex gap-2 items-center">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask a question about SAP Customizing..."
                className="input flex-1 bg-gray-50 h-10"
                disabled={isLoading}
              />
              <button
                onClick={handleSend}
                className="btn btn-primary px-6 py-2 h-10"
                disabled={!input.trim() || isLoading}
              >
                Send
              </button>
              <button
                onClick={handleReset}
                className="btn btn-secondary px-6 py-2 h-10"
                disabled={messages.length === 0 && input.trim() === ""}
              >
                Reset
              </button>
            </div>
            <p className="text-xs text-gray-500 text-right">
              Press Enter to send, Shift+Enter for new line
            </p>
          </div>
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
              <div className="flex items-center gap-4">
                <div className="w-16 h-8 bg-block-gradient" style={{clipPath: 'polygon(0% 0%, 100% 0%, 80% 100%, 0% 100%)'}} />
                <h3 className="font-semibold text-lg">{citationTitle || 'Reference Details'}</h3>
              </div>
              <div className="flex items-center gap-4">
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

