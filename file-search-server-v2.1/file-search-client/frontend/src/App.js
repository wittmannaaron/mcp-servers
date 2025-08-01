import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [query, setQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [originalSearchResults, setOriginalSearchResults] = useState([]); // Store original results for filtering
  const [chatMessages, setChatMessages] = useState([]);
  const [currentMessage, setCurrentMessage] = useState('');
  const [sortBy, setSortBy] = useState('relevance'); // Default sort by relevance
  const [showMarkdownModal, setShowMarkdownModal] = useState(false);
  const [markdownContent, setMarkdownContent] = useState(null);

  // Simple markdown to HTML converter with table support
  const convertMarkdownToHtml = (markdown) => {
    if (!markdown) return '';
    
    // Split into lines for better processing
    const lines = markdown.split('\n');
    let html = '';
    let inList = false;
    let inTable = false;
    let tableHeaders = [];
    let tableRows = [];
    
    for (let i = 0; i < lines.length; i++) {
      let line = lines[i];
      
      // Check for table separator (e.g., | --- | --- |)
      const isTableSeparator = /^\s*\|?\s*-*\s*\|.*\|?\s*$/.test(line) && line.includes('---');
      
      // Check for table row (starts with |)
      const isTableRow = /^\s*\|.*\|\s*$/.test(line) && !isTableSeparator;
      
      // Handle table parsing
      if (isTableRow || isTableSeparator) {
        if (isTableRow) {
          if (!inTable) {
            inTable = true;
            // Parse header row
            tableHeaders = line.split('|').map(cell => cell.trim()).filter((cell, index, arr) => {
              // Filter out empty cells at the beginning and end
              return !(index === 0 && cell === '') && !(index === arr.length - 1 && cell === '');
            });
          } else if (!isTableSeparator) {
            // Parse data row
            const rowCells = line.split('|').map(cell => cell.trim()).filter((cell, index, arr) => {
              // Filter out empty cells at the beginning and end
              return !(index === 0 && cell === '') && !(index === arr.length - 1 && cell === '');
            });
            tableRows.push(rowCells);
          }
        }
        // Skip separator line
        continue;
      } else if (inTable) {
        // Close table and add to HTML
        html += '<table class="markdown-table">';
        if (tableHeaders.length > 0) {
          html += '<thead><tr>';
          tableHeaders.forEach(header => {
            html += `<th>${header}</th>`;
          });
          html += '</tr></thead>';
        }
        if (tableRows.length > 0) {
          html += '<tbody>';
          tableRows.forEach(row => {
            html += '<tr>';
            // Ensure row has enough cells to match headers
            const cellsToRender = Math.max(row.length, tableHeaders.length);
            for (let j = 0; j < cellsToRender; j++) {
              const cellContent = j < row.length ? row[j] : '';
              html += `<td>${cellContent}</td>`;
            }
            html += '</tr>';
          });
          html += '</tbody>';
        }
        html += '</table>';
        
        // Reset table state
        inTable = false;
        tableHeaders = [];
        tableRows = [];
      }
      
      // Headers
      if (line.startsWith('### ')) {
        html += `<h3>${line.substring(4)}</h3>`;
      } else if (line.startsWith('## ')) {
        html += `<h2>${line.substring(3)}</h2>`;
      } else if (line.startsWith('# ')) {
        html += `<h1>${line.substring(2)}</h1>`;
      }
      // List items
      else if (line.startsWith('- ')) {
        if (!inList) {
          html += '<ul>';
          inList = true;
        }
        html += `<li>${line.substring(2)}</li>`;
      }
      // Empty line
      else if (line.trim() === '') {
        if (inList) {
          html += '</ul>';
          inList = false;
        }
        html += '<br>';
      }
      // Regular text
      else {
        if (inList) {
          html += '</ul>';
          inList = false;
        }
        html += `<p>${line}</p>`;
      }
    }
    
    // Close any open list
    if (inList) {
      html += '</ul>';
    }
    
    // Close any open table
    if (inTable) {
      html += '<table class="markdown-table">';
      if (tableHeaders.length > 0) {
        html += '<thead><tr>';
        tableHeaders.forEach(header => {
          html += `<th>${header}</th>`;
        });
        html += '</tr></thead>';
      }
      if (tableRows.length > 0) {
        html += '<tbody>';
        tableRows.forEach(row => {
          html += '<tr>';
          // Ensure row has enough cells to match headers
          const cellsToRender = Math.max(row.length, tableHeaders.length);
          for (let j = 0; j < cellsToRender; j++) {
            const cellContent = j < row.length ? row[j] : '';
            html += `<td>${cellContent}</td>`;
          }
          html += '</tr>';
        });
        html += '</tbody>';
      }
      html += '</table>';
    }
    
    // Apply inline formatting
    html = html
      // Bold
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      // Italic
      .replace(/\*([^*]+)\*/g, '<em>$1</em>')
      // Code blocks (triple backticks)
      .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
      // Inline code
      .replace(/`(.*?)`/g, '<code>$1</code>')
      // Links
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>')
      // Clean up multiple br tags
      .replace(/<br><br>/g, '<br>');
    
    return html;
  };

  // Effect to re-sort results when sortBy changes
  useEffect(() => {
    if (originalSearchResults.length > 0) {
      let sortedResults = [...originalSearchResults];
      if (sortBy === 'name') {
        sortedResults.sort((a, b) => a.filename.localeCompare(b.filename));
      } else if (sortBy === 'date') {
        sortedResults.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
      }
      // Relevance is default and handled by the backend
      setSearchResults(sortedResults);
    }
  }, [sortBy, originalSearchResults]);

  // Function to handle search
  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    // If we already have search results, this is a drill-down search
    if (searchResults.length > 0 && originalSearchResults.length > 0) {
      // Filter existing results based on the query
      const filteredResults = originalSearchResults.filter(result => {
        // Check if query matches any of the result fields
        const queryLower = query.toLowerCase();
        return (
          (result.filename && result.filename.toLowerCase().includes(queryLower)) ||
          (result.file_path && result.file_path.toLowerCase().includes(queryLower)) ||
          (result.content_preview && result.content_preview.toLowerCase().includes(queryLower)) ||
          (result.first_date_in_document && result.first_date_in_document.toLowerCase().includes(queryLower))
        );
      });
      
      // Sort the filtered results
      let sortedResults = [...filteredResults];
      if (sortBy === 'name') {
        sortedResults.sort((a, b) => a.filename.localeCompare(b.filename));
      } else if (sortBy === 'date') {
        sortedResults.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
      }
      
      setSearchResults(sortedResults);
      return;
    }

    // Otherwise, perform a new search
    try {
      const response = await fetch('http://localhost:5001/api/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query }),
      });

      const data = await response.json();
      if (data.results) {
        // Store original results for filtering
        setOriginalSearchResults(data.results);
        
        // Sort results based on selected option
        let sortedResults = [...data.results];
        if (sortBy === 'name') {
          sortedResults.sort((a, b) => a.filename.localeCompare(b.filename));
        } else if (sortBy === 'date') {
          sortedResults.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        }
        // Relevance is default and handled by the backend
        setSearchResults(sortedResults);
      }
    } catch (error) {
      console.error('Search error:', error);
    }
  };

  // Function to reset drill-down filter
  const resetFilter = () => {
    // Reset to original search results
    let sortedResults = [...originalSearchResults];
    if (sortBy === 'name') {
      sortedResults.sort((a, b) => a.filename.localeCompare(b.filename));
    } else if (sortBy === 'date') {
      sortedResults.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    }
    setSearchResults(sortedResults);
    setQuery(''); // Clear the search query
  };

  // Function to handle chat
  const handleChat = async (e) => {
    e.preventDefault();
    if (!currentMessage.trim()) return;

    // Add user message to chat
    const userMessage = { sender: 'user', text: currentMessage };
    setChatMessages(prev => [...prev, userMessage]);
    
    try {
      const response = await fetch('http://localhost:5001/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: currentMessage }),
      });

      const data = await response.json();
      if (data.response) {
        // Add AI response to chat
        const aiMessage = { sender: 'ai', text: data.response };
        setChatMessages(prev => [...prev, aiMessage]);
        
        // If we got search results, also update the search results display
        if (data.results && data.results.length > 0) {
          // Store original results for filtering
          setOriginalSearchResults(data.results);
          
          // Sort results based on current sort option
          let sortedResults = [...data.results];
          if (sortBy === 'name') {
            sortedResults.sort((a, b) => a.filename.localeCompare(b.filename));
          } else if (sortBy === 'date') {
            sortedResults.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
          }
          setSearchResults(sortedResults);
        } else {
          // Clear search results if no results found
          setSearchResults([]);
          setOriginalSearchResults([]);
        }
      }
      
      // Clear input
      setCurrentMessage('');
    } catch (error) {
      console.error('Chat error:', error);
    }
  };

  // Function to open file with default application
  const handleOpenFile = async (filePath) => {
    try {
      const response = await fetch('http://localhost:5001/api/open-file', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ file_path: filePath }),
      });

      const data = await response.json();
      if (!data.success) {
        alert('Fehler beim Öffnen der Datei: ' + data.message);
      }
    } catch (error) {
      console.error('Error opening file:', error);
      alert('Fehler beim Öffnen der Datei: ' + error.message);
    }
  };

  // Function to open folder in Finder
  const handleOpenFolder = async (filePath) => {
    try {
      const response = await fetch('http://localhost:5001/api/open-folder', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ file_path: filePath }),
      });

      const data = await response.json();
      if (!data.success) {
        alert('Fehler beim Öffnen des Ordners: ' + data.message);
      }
    } catch (error) {
      console.error('Error opening folder:', error);
      alert('Fehler beim Öffnen des Ordners: ' + error.message);
    }
  };

  // Function to show markdown content
  const handleShowMarkdown = async (documentId, filename) => {
    try {
      const response = await fetch('http://localhost:5001/api/get-markdown', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ document_id: documentId }),
      });

      const data = await response.json();
      if (data.success) {
        setMarkdownContent({
          filename: data.filename,
          content: data.markdown_content || data.original_text || 'Kein Inhalt verfügbar'
        });
        setShowMarkdownModal(true);
      } else {
        alert('Fehler beim Laden des Inhalts: ' + data.message);
      }
    } catch (error) {
      console.error('Error loading markdown:', error);
      alert('Fehler beim Laden des Inhalts: ' + error.message);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Document Search Client</h1>
      </header>
      
      <main>
        <div className="search-section">
          <form onSubmit={handleSearch}>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={searchResults.length > 0 ? "Filter existing results..." : "Enter search query..."}
            />
            <button type="submit">Search</button>
            {searchResults.length > 0 && originalSearchResults.length > 0 && query && (
              <button type="button" onClick={resetFilter} style={{ marginLeft: '10px' }}>
                Reset Filter
              </button>
            )}
          </form>
        </div>
        
        {searchResults.length > 0 && (
          <div className="results-section">
            <h2>Search Results ({searchResults.length})</h2>
            <div className="sort-controls">
              <label>Sort by: </label>
              <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
                <option value="relevance">Relevance</option>
                <option value="name">Name</option>
                <option value="date">Date</option>
              </select>
            </div>
            <div className="results-container">
              {searchResults.map((result) => {
                // Format date properly (DD.MM.YYYY)
                const formatDate = (dateString) => {
                  if (!dateString) return 'N/A';
                  try {
                    const date = new Date(dateString);
                    return date.toLocaleDateString('de-DE', {
                      day: '2-digit',
                      month: '2-digit', 
                      year: 'numeric'
                    });
                  } catch {
                    return 'N/A';
                  }
                };

                // Truncate content to 300 characters
                const truncateContent = (content) => {
                  if (!content) return '';
                  return content.length > 300 ? content.substring(0, 300) + '...' : content;
                };

                return (
                  <table key={result.id} className="result-table">
                    <tbody>
                      {/* First row: creation date | first date in document | source type | filename */}
                      <tr className="header-row">
                        <td className="date-cell">{formatDate(result.created_at)}</td>
                        <td className="first-date-cell">
                          {result.first_date_in_document || 'N/A'}
                        </td>
                        <td className="source-type-cell">
                          {result.source_type === 'e-mail' ? 'E-Mail' : result.source_type === 'archive' ? 'Archiv' : 'Datei'}
                        </td>
                        <td className="filename-cell clickable"
                            onClick={() => handleOpenFile(result.file_path)}
                            title="Klicken zum Öffnen der Datei">
                          {result.filename}
                        </td>
                      </tr>
                      {/* Second row: file path (spans all columns) */}
                      <tr className="path-row">
                        <td className="filepath-cell clickable"
                            colSpan="4"
                            onClick={() => handleOpenFolder(result.file_path)}
                            title="Klicken zum Öffnen des Ordners im Finder">
                          {result.file_path}
                        </td>
                      </tr>
                      {/* Third row: truncated markdown content (spans all columns) */}
                      <tr className="content-row">
                        <td className="content-cell clickable"
                            colSpan="4"
                            onClick={() => handleShowMarkdown(result.id, result.filename)}
                            title="Klicken für Markdown-Vorschau">
                          <div className="content-preview">
                            {truncateContent(result.content_preview)}
                          </div>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                );
              })}
            </div>
          </div>
        )}
        
        <div className="chat-section">
          <h2>Chat with Assistant</h2>
          <div className="chat-messages">
            {chatMessages.map((msg, index) => (
              <div key={index} className={`message ${msg.sender}`}>
                <strong>{msg.sender === 'user' ? 'You: ' : 'Assistant: '}</strong>
                {msg.text}
              </div>
            ))}
          </div>
          <form onSubmit={handleChat} className="chat-input">
            <input
              type="text"
              value={currentMessage}
              onChange={(e) => setCurrentMessage(e.target.value)}
              placeholder="Ask a question..."
            />
            <button type="submit">Send</button>
          </form>
        </div>
      </main>

      {/* Markdown Preview Modal */}
      {showMarkdownModal && markdownContent && (
        <div className="modal-overlay" onClick={() => setShowMarkdownModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{markdownContent.filename}</h3>
              <button 
                className="modal-close" 
                onClick={() => setShowMarkdownModal(false)}
                title="Schließen"
              >
                ×
              </button>
            </div>
            <div className="modal-body">
              <div 
                className="markdown-content" 
                dangerouslySetInnerHTML={{ 
                  __html: convertMarkdownToHtml(markdownContent.content) 
                }}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;