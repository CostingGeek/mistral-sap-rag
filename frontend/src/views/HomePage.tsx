import { useState, useRef, useEffect, useCallback } from "react";
import { useApi } from "../hooks/useApi";
import { ChatMessage, ChatResponse } from "../types";

const EXAMPLE_QUERIES = [
  "What do I need to configure for dangerous goods transport?",
  "We ship lithium batteries internationally — what do we need to configure?",
  "What must be configured before assigning hazard statements to hazard classes?",
  "How does the system determine the packing instruction for lithium batteries?",
  "How is the tax calculation procedure assigned to a country?",
  "Which settings are specific to business places in Brazil?",
];


export default function HomePage() {
  const { chat, getObject } = useApi();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [scope, setScope] = useState<"standard" | "nova" | "both">("both");
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
        scope,
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
      </button>)
      <div className="text-xs mt-1 opacity-70">
        Similarity: {(1 - citation.distance).toFixed(3)}
      </div>
    </div>
  );

  // Helper to render nested list items
  interface ListItemNode {
    type: 'ordered' | 'unordered';
    number?: number;
    content: React.ReactNode;
    children: ListItemNode[];
  }

  const renderListTree = (items: ListItemNode[], keyPrefix: string = ''): React.ReactNode => {
    const orderedItems = items.filter(i => i.type === 'ordered');
    const unorderedItems = items.filter(i => i.type === 'unordered');
    
    if (orderedItems.length > 0 && unorderedItems.length === 0) {
      const numbers = orderedItems.map(i => i.number).filter((n): n is number => n !== undefined);
      const start = numbers.length > 0 ? Math.min(...numbers) : undefined;
      return (
        <ol key={keyPrefix} className="list-decimal list-inside pl-4 space-y-1" start={start}>
          {orderedItems.map((item, idx) => (
            <li key={`${keyPrefix}-item-${idx}`} className="mb-1">
              {item.content}
              {item.children.length > 0 && renderListTree(item.children, `${keyPrefix}-${idx}`)}
            </li>
          ))}
        </ol>
      );
    } else if (unorderedItems.length > 0) {
      return (
        <ul key={keyPrefix} className="list-disc list-inside pl-6 space-y-1">
          {unorderedItems.map((item, idx) => (
            <li key={`${keyPrefix}-item-${idx}`} className="mb-1">
              {item.content}
              {item.children.length > 0 && renderListTree(item.children, `${keyPrefix}-${idx}`)}
            </li>
          ))}
        </ul>
      );
    }
    return null;
  };

  // Fix list indentation and structure for markdown
  const fixListIndentation = (text: string): string => {
    const lines = text.split('\n');
    const result: string[] = [];
    let inOrderedList = false;
    let expectedNumber = 1;
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const trimmed = line.trim();
      
      // Check if this is an ordered list item
      const orderedMatch = trimmed.match(/^(\d+)\.\s+(.*)/) || trimmed.match(/^(\d+)\)\s+(.*)/);
      
      if (orderedMatch) {
        const number = parseInt(orderedMatch[1], 10);
        
        // Fix numbering gaps
        if (inOrderedList && number > expectedNumber) {
          // There's a gap - renumber to maintain sequence
          const originalIndent = line.substring(0, line.length - trimmed.length);
          result.push(originalIndent + expectedNumber + '. ' + orderedMatch[2]);
          expectedNumber++;
        } else {
          result.push(line);
          expectedNumber = number + 1;
        }
        
        inOrderedList = true;
      } else {
        // Check if this is an unordered list item
        const unorderedMatch = trimmed.match(/^[-*\u2022]\s+(.*)/);
        
        if (unorderedMatch && inOrderedList) {
          // Strip any existing indentation and add exactly 2 spaces
          // All bullets under ordered items should be at the same level
          result.push('  ' + trimmed);
        } else if (trimmed && inOrderedList && !unorderedMatch) {
          // Non-bullet line in ordered list context
          // Check if it's a label that should be a bullet
          if (/^[A-Z][a-zA-Z ]+:.*Source.*\d+/.test(trimmed) ||
              /^[A-Z][a-zA-Z ]+:.*\d+/.test(trimmed) ||
              /^Source[\s\u2013-]*.*\d+/.test(trimmed)) {
            // Convert labels with sources to bullets
            result.push('  - ' + trimmed);
          } else {
            result.push(line);
          }
        } else {
          // Not a list item or not in ordered list context
          result.push(line);
          
          if (trimmed && !unorderedMatch && !orderedMatch) {
            // Non-list content - check if it breaks the context
            if (/^<h[1-6]>/.test(trimmed) || /^#/.test(trimmed)) {
              inOrderedList = false;
            }
          }
        }
      }
    }
    
    return result.join('\n');
  };

  // Markdown to React element renderer
  const renderMarkdown = (text: string): React.ReactNode => {
    if (!text || typeof text !== 'string') return text;

    // Preprocess markdown to fix list indentation
    // When a bullet point follows a numbered list item (with blank lines), add indentation
    const preprocessedText = fixListIndentation(text);

    // Split by lines and process each line
    const lines = preprocessedText.split('\n');
    const elements: React.ReactNode[] = [];
    
    // List stack: each entry contains list items and their type
    type ListContext = {
      type: 'ordered' | 'unordered';
      items: ListItemNode[];
      indent: string;
      parentItem?: ListItemNode; // For nested lists, reference to parent item
    };
    
    const listStack: ListContext[] = [];
    let inTable = false;
    let inTableHeader = true;
    let tableRows: React.ReactNode[] = [];
    let headerRows: React.ReactNode[] = [];
    let bodyRows: React.ReactNode[] = [];
    let inCodeBlock = false;
    let codeBlockContent: string[] = [];
    let blankLineCount = 0;

    const flushLists = () => {
      // Render all lists in the stack from root to deepest
      if (listStack.length > 0) {
        // Get the root list
        const rootList = listStack[0];
        elements.push(renderListTree(rootList.items, `list-${elements.length}`));
        // Clear the stack
        while (listStack.length > 0) {
          listStack.pop();
        }
      }
    };

    const flushTable = () => {
      if (tableRows.length > 0) {
        elements.push(<table key={elements.length} className="w-full border-collapse my-4 text-sm bg-white">
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
        blankLineCount = 0;
      }

      // Check for code block (lines starting with ```)
      if (trimmed.startsWith('```')) {
        flushLists();
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
        flushLists();
        flushTable();
        elements.push(<hr key={elements.length} className="my-6 border-t border-gray-300" />);
        continue;
      }

      // Check for headers (lines starting with #)
      const headerMatch = trimmed.match(/^(#{1,6})\s+(.*)/);
      if (headerMatch) {
        flushLists();
        flushTable();
        const level = Math.min(headerMatch[1].length, 6);
        const content = headerMatch[2];
        const processedContent = processInlineMarkdown(content);
        const className = `text-h${level} font-bold mb-4 mt-6`;
        
        // Use a switch to handle the dynamic header tag
        switch (level) {
          case 1: elements.push(<h1 key={elements.length} className={className}>{processedContent}</h1>); break;
          case 2: elements.push(<h2 key={elements.length} className={className}>{processedContent}</h2>); break;
          case 3: elements.push(<h3 key={elements.length} className={className}>{processedContent}</h3>); break;
          case 4: elements.push(<h4 key={elements.length} className={className}>{processedContent}</h4>); break;
          case 5: elements.push(<h5 key={elements.length} className={className}>{processedContent}</h5>); break;
          case 6: elements.push(<h6 key={elements.length} className={className}>{processedContent}</h6>); break;
        }
        continue;
      }

      // Check for table row (starts with |)
      const isTableRow = trimmed.startsWith('|') && trimmed.includes('|');
      
      if (isTableRow) {
        flushLists();
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
        // Match against the raw line so indentation is preserved
        const orderedMatch = line.match(/^(\s*)(\d+)\.\s+(.*)/) || line.match(/^(\s*)(\d+)\)\s+(.*)/);
        // Check for unordered list items (e.g., "- " or "* " or indented "   - ")
        const unorderedMatch = line.match(/^(\s*)[-*\u2022]\s+(.*)/);

        if (orderedMatch || unorderedMatch) {
          const isOrdered = !!orderedMatch;
          const content = isOrdered && orderedMatch ? orderedMatch[3] : unorderedMatch ? unorderedMatch[2] : '';
          const indent = isOrdered && orderedMatch ? orderedMatch[1] : unorderedMatch ? unorderedMatch[1] : '';
          const newListType = isOrdered ? 'ordered' : 'unordered';
          const listNumber = isOrdered && orderedMatch ? parseInt(orderedMatch[2], 10) : undefined;
          const processedContent = processInlineMarkdown(content);

          // Determine the current indentation level
          const currentIndentLevel = indent.length;
          
          // Find the appropriate list in the stack
          let targetListIndex = listStack.length - 1;
          
          // Find the deepest list with indentation <= current
          while (targetListIndex >= 0 && listStack[targetListIndex].indent.length > currentIndentLevel) {
            targetListIndex--;
          }
          
          if (targetListIndex >= 0 && listStack[targetListIndex].type === newListType) {
            // Check if this should be nested (greater indentation)
            const targetIndent = listStack[targetListIndex].indent.length;
            if (currentIndentLevel > targetIndent) {
              // Deeper: child of the last item in the target list
              const parentList = listStack[targetListIndex];
              const lastParentItem = parentList.items[parentList.items.length - 1];
              const listItem: ListItemNode = {
                type: newListType,
                number: listNumber,
                content: processedContent,
                children: []
              };
              lastParentItem.children.push(listItem);
              
              // Pop everything above the parent list
              while (listStack.length > targetListIndex + 1) {
                listStack.pop();
              }
              
              // Push a context for this nesting level containing the item
              listStack.push({
                type: newListType,
                items: [listItem],
                indent: indent,
                parentItem: lastParentItem
              });
            } else {
              // Same level: sibling, add to this list
              const listItem: ListItemNode = {
                type: newListType,
                number: listNumber,
                content: processedContent,
                children: []
              };
              listStack[targetListIndex].items.push(listItem);
              // If this context has a parent item, also add to its children
              if (listStack[targetListIndex].parentItem) {
                listStack[targetListIndex].parentItem!.children.push(listItem);
              }
              
              // Pop deeper list contexts from the stack
              while (listStack.length > targetListIndex + 1) {
                listStack.pop();
              }
            }
          } else {
            // Different type - check if we should resume a parent list of the same type
            // For ordered lists, check if there's an ordered list at a higher level
            let parentOfSameTypeIndex = -1;
            if (newListType === 'ordered') {
              // Look for an ordered list in the stack
              for (let i = 0; i < listStack.length; i++) {
                if (listStack[i].type === 'ordered' && listStack[i].indent.length <= currentIndentLevel) {
                  parentOfSameTypeIndex = i;
                  break;
                }
              }
            }
            
            if (parentOfSameTypeIndex >= 0) {
              // Resume the parent list of the same type
              const parentList = listStack[parentOfSameTypeIndex];
              const listItem: ListItemNode = {
                type: newListType,
                number: listNumber,
                content: processedContent,
                children: []
              };
              parentList.items.push(listItem);
              // If this context has a parent item, also add to its children
              if (parentList.parentItem) {
                parentList.parentItem.children.push(listItem);
              }
              
              // Pop everything above the parent list
              while (listStack.length > parentOfSameTypeIndex + 1) {
                listStack.pop();
              }
            } else if (targetListIndex >= 0 && listStack[targetListIndex].items.length > 0 && currentIndentLevel > listStack[targetListIndex].indent.length) {
              // We have a parent list - add as nested child to last item
              const parentList = listStack[targetListIndex];
              const lastParentItem = parentList.items[parentList.items.length - 1];
              
              // Create new nested list context
              const newList: ListItemNode = {
                type: newListType,
                number: listNumber,
                content: processedContent,
                children: []
              };
              lastParentItem.children.push(newList);
              
              // Pop deeper contexts, then push a context for this nesting level
              while (listStack.length > targetListIndex + 1) {
                listStack.pop();
              }
              listStack.push({
                type: newListType,
                items: [newList],
                indent: indent,
                parentItem: lastParentItem
              });
            } else {
              // No parent list or empty parent - start fresh
              flushLists();
              const listItem: ListItemNode = {
                type: newListType,
                number: listNumber,
                content: processedContent,
                children: []
              };
              listStack.push({
                type: newListType,
                items: [listItem],
                indent: indent
              });
            }
          }
        } else {
          // Not a list item
          // Only flush lists if we have content
          if (trimmed) {
            const processedContent = processInlineMarkdown(trimmed);
            elements.push(<p key={elements.length} className="mb-4">{processedContent}</p>);
          }
        }
      }
    }

    flushLists();
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
          <div className="py-4 text-gray-700 flex-shrink-0 border-b">
            <p className="text-lg text-center">What do you want to configure?</p>
            <p className="text-xs text-gray-500 text-center mt-1">
              Grounded answers with citations — from the SAP standard, the
              company standard, or both (pick a scope below the input box).
            </p>
            <div className="flex flex-wrap gap-2 justify-center mt-3 px-4">
              {EXAMPLE_QUERIES.map((q) => (
                <button
                  key={q}
                  onClick={() => setInput(q)}
                  className="text-xs px-3 py-1.5 rounded-full border border-borderWarm bg-gray-50 hover:bg-gray-100 text-gray-700"
                >
                  {q}
                </button>
              ))}
            </div>
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
            <div className="flex items-center justify-between">
              <div className="flex gap-2 items-center">
                <label htmlFor="corpus-scope" className="text-xs text-gray-500">
                  Scope:
                </label>
                <select
                  id="corpus-scope"
                  value={scope}
                  onChange={(e) =>
                    setScope(e.target.value as "standard" | "nova" | "both")
                  }
                  className="input bg-gray-50 h-8 text-xs w-64"
                  disabled={isLoading}
                >
                  <option value="both">SAP standard + Company standard</option>
                  <option value="standard">SAP standard only</option>
                  <option value="nova">Company standard (NOVA) only</option>
                </select>
              </div>
              <p className="text-xs text-gray-500">
                Press Enter to send, Shift+Enter for new line
              </p>
            </div>
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

