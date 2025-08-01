from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import ollama

from database import get_db_connection, search_documents_fts, get_document_by_id

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Ollama model name
MODEL_NAME = "catalog-browser:latest"

@app.route('/api/search', methods=['POST'])
def search_documents():
    """Search documents using FTS."""
    data = request.get_json()
    query = data.get('query', '')
    
    if not query:
        return jsonify({'error': 'Query parameter is required'}), 400
    
    try:
        results = search_documents_fts(query)
        return jsonify({'results': results})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/document/<int:document_id>', methods=['GET'])
def get_document(document_id):
    """Get full content of a document by ID."""
    try:
        document = get_document_by_id(document_id)
        if document:
            return jsonify({'document': document})
        else:
            return jsonify({'error': 'Document not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat_with_llm():
    """Process natural language queries with multi-step LLM approach."""
    data = request.get_json()
    user_message = data.get('message', '')
    
    if not user_message:
        return jsonify({'error': 'Message parameter is required'}), 400
    
    try:
        # Step 1: Extract keywords using direct Ollama API call
        keyword_prompt = f'Extrahiere nur die wichtigsten Substantive und Namen aus dieser deutschen Anfrage: "{user_message}". Ignoriere Wörter wie "Dateien", "Inhalt", "alle", "zeige", "mit", "dem", "Wort". Antworte nur mit den relevanten Suchbegriffen, getrennt durch Leerzeichen:'
        
        keyword_response = ollama.generate(
            model=MODEL_NAME,
            prompt=keyword_prompt
        )
        
        # Extract keywords from response and clean them for FTS5
        keywords_text = keyword_response.get('response', '').strip()
        print(f"Raw extracted keywords: '{keywords_text}'")  # Debug output
        
        # Clean keywords: remove commas, semicolons, and other problematic characters
        import re
        cleaned_keywords = re.sub(r'[,;.!?]+', ' ', keywords_text)
        cleaned_keywords = re.sub(r'\s+', ' ', cleaned_keywords).strip()
        print(f"Cleaned keywords: '{cleaned_keywords}'")  # Debug output
        
        if not cleaned_keywords:
            return jsonify({'response': 'Ich konnte keine Suchbegriffe in Ihrer Anfrage identifizieren. Könnten Sie Ihre Suche bitte präzisieren?'})
        
        # Step 2: Use extracted keywords for search
        # First try direct search
        search_results = search_documents_fts(cleaned_keywords)
        print(f"Direct search results: {len(search_results)} documents found")  # Debug output
        
        # If no results with direct search, try OR search with individual keywords
        if not search_results and len(cleaned_keywords.split()) > 1:
            or_query = " OR ".join(cleaned_keywords.split())
            search_results = search_documents_fts(or_query)
            print(f"OR search results: {len(search_results)} documents found")  # Debug output
        
        # Step 3: Return structured data for table display
        if search_results:
            response_message = f"Ich habe {len(search_results)} Dokumente gefunden."
            return jsonify({
                'response': response_message,
                'results': search_results,
                'total_count': len(search_results)
            })
        else:
            # Step 4: If no results, try alternative search strategies
            # Try with individual words
            words = cleaned_keywords.split()
            alternative_results = []
            for word in words[:3]:  # Try up to 3 words
                if len(word) > 2:  # Only meaningful words
                    alt_results = search_documents_fts(word)
                    alternative_results.extend(alt_results)
            
            if alternative_results:
                # Remove duplicates
                seen_ids = set()
                unique_results = []
                for result in alternative_results:
                    if result['id'] not in seen_ids:
                        unique_results.append(result)
                        seen_ids.add(result['id'])
                
                response_message = f"Keine direkten Treffer für '{cleaned_keywords}', aber {len(unique_results)} ähnliche Dokumente gefunden."
                return jsonify({
                    'response': response_message,
                    'results': unique_results,
                    'total_count': len(unique_results)
                })
            else:
                return jsonify({
                    'response': f"Leider konnte ich keine Dokumente zu '{cleaned_keywords}' finden.",
                    'results': [],
                    'total_count': 0
                })
        
    except Exception as e:
        print(f"Error in chat_with_llm: {str(e)}")  # Debug output
        return jsonify({'error': str(e)}), 500

@app.route('/api/open-file', methods=['POST'])
def open_file():
    """Open file with default macOS application"""
    data = request.get_json()
    file_path = data.get('file_path', '')
    
    if not file_path:
        return jsonify({'error': 'File path is required'}), 400
    
    try:
        import subprocess
        # Use macOS 'open' command to open file with default application
        subprocess.run(["open", file_path], check=True)
        return jsonify({
            'success': True,
            'message': f'Datei geöffnet: {file_path}'
        })
    except subprocess.CalledProcessError as e:
        return jsonify({
            'success': False,
            'message': f'Fehler beim Öffnen der Datei: {e}'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Unbekannter Fehler: {e}'
        }), 500

@app.route('/api/open-folder', methods=['POST'])
def open_folder():
    """Open folder containing the file in Finder"""
    data = request.get_json()
    file_path = data.get('file_path', '')
    
    if not file_path:
        return jsonify({'error': 'File path is required'}), 400
    
    try:
        import subprocess
        # Use macOS 'open' command to reveal file in Finder
        subprocess.run(["open", "-R", file_path], check=True)
        return jsonify({
            'success': True,
            'message': f'Ordner geöfffnet: {file_path}'
        })
    except subprocess.CalledProcessError as e:
        return jsonify({
            'success': False,
            'message': f'Fehler beim Öffnen des Ordners: {e}'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Unbekannter Fehler: {e}'
        }), 500

@app.route('/api/get-markdown', methods=['POST'])
def get_markdown():
    """Get full markdown content for document by ID"""
    data = request.get_json()
    document_id = data.get('document_id')
    
    if not document_id:
        return jsonify({'error': 'Document ID is required'}), 400
    
    try:
        document = get_document_by_id(document_id)
        if document:
            return jsonify({
                'success': True,
                'filename': document.get('filename', 'Unbekannt'),
                'markdown_content': document.get('markdown_content', ''),
                'original_text': document.get('original_text', '')
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Dokument nicht gefunden'
            }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Fehler beim Laden des Dokuments: {e}'
        }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)