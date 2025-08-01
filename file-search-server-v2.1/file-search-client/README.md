# File Search Client

A comprehensive document research assistant with specialized search tools for a document corpus.

## Features
- Natural Language Queries in German
- Multi-Step Search with tool chaining
- Fuzzy Matching for OCR error correction
- Semantic Search capabilities
- Date Filtering (creation dates and mentioned dates)
- Duplicate Detection
- Result Ranking by relevance
- Session Memory for progressive search refinement

## Requirements
- Python 3.8+
- Node.js 14+
- Ollama with latest model
- SQLite database with documents

## Installation
1. Install Python dependencies: `pip install -r requirements.txt`
2. Install Node.js dependencies: `cd frontend && npm install`
3. Ensure Ollama is running with the latest model

## Usage
1. Start backend server: `python backend/app.py`
2. Start frontend: `cd frontend && npm start`