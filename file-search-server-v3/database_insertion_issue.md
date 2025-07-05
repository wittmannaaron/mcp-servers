# Analysis of Database Insertion Failures

## 1. Problem Description
The document ingestion pipeline is failing to store a significant number of documents in the database. The test script, which processes 144 files, consistently reports that it is "processed but failed to store" for every file. This indicates a systemic issue with the database insertion process.

## 2. Symptoms
The primary symptoms of the problem are:
- The `full_ingestion_test.py` script reports that it has "processed but failed to store" every file.
- The log contains the warning `Could not retrieve document ID for <filename>`.
- The log also contains the error `Database error executing query: unrecognized token: "#"` for some files, but not all.

## 3. Root Cause Analysis
The root cause of the problem is a combination of two factors:

**1. Lack of Parameterized Query Support in the MCP Server:** The SQLite MCP server does not support parameterized queries. This forces the client to manually format the SQL queries, which is error-prone and insecure.

**2. Inadequate Client-Side Escaping:** The `_format_query_safely` function in `src/core/ingestion_mcp_client.py` is attempting to manually escape special characters, but it is not comprehensive enough to handle all cases. This is leading to malformed SQL queries and database errors.

## 4. Detailed Error Analysis
The `unrecognized token: "#"` error is a clear indication that the `#` character is not being properly escaped. However, the `Could not retrieve document ID` warning is the more significant issue, as it indicates that the `INSERT` statement is failing for reasons other than just the `#` character.

The `_format_query_safely` function has been modified multiple times in an attempt to fix the issue, but each attempt has failed. The current implementation is still not robust enough to handle all special characters and edge cases.

## 5. Proposed Solution
The ideal solution is to add support for parameterized queries to the SQLite MCP server. This would eliminate the need for client-side escaping and would be the most secure and reliable solution.

However, if modifying the MCP server is not feasible, then a more robust client-side escaping mechanism is required. This would involve a more comprehensive implementation of the `_format_query_safely` function that can handle all special characters and edge cases.

## 6. Next Steps
The immediate next step is to implement a more robust client-side escaping mechanism. This will allow us to get the ingestion pipeline working, even if it is not the ideal solution. Once the pipeline is working, we can then investigate the possibility of adding support for parameterized queries to the MCP server.