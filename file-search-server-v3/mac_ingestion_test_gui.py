#!/usr/bin/env python3
"""
Native Mac App GUI for the document ingestion test script.
Provides a Cocoa-based interface for running the full_ingestion_test.py functionality.
"""

import asyncio
import sys
from pathlib import Path
import threading
from datetime import datetime
from typing import Optional

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from Cocoa import *
    from PyObjCTools import AppHelper
except ImportError:
    print("This GUI requires PyObjC to be installed.")
    print("Please install it with: pip install pyobjc")
    sys.exit(1)

from src.core.ingestion import IngestionOrchestrator
from src.core.events import FileEvent, FileEventType
from src.core.document_store import DocumentStore
from src.core.mcp_client import get_mcp_client
from src.core.logging_config import setup_logging
from clear_database import clear_database_file
from loguru import logger
import time

# Global variables for tracking test status
test_status = {
    "running": False,
    "stop_requested": False,
    "progress": 0,
    "files_processed": 0,
    "total_files": 0,
    "logs": [],
    "current_file": ""
}

# Lock for thread-safe updates
status_lock = threading.Lock()

# Setup logging
setup_logging()

class TestStopHandler:
    """Custom log handler that stops the test on WARNING or ERROR."""
    
    def __init__(self, gui_controller):
        self.gui_controller = gui_controller
        self.should_stop = False
    
    def emit(self, record):
        """Handle log records and check for stop conditions."""
        try:
            if hasattr(record, 'level'):
                level_name = record.level.name
            else:
                level_name = getattr(record, 'levelname', 'UNKNOWN')
                
            if level_name in ['WARNING', 'ERROR']:
                message = str(record.message) if hasattr(record, 'message') else str(record)
                self.gui_controller.log_message(f"[TestStopHandler] {level_name} detected - stopping test!")
                self.gui_controller.log_message(f"[TestStopHandler] Message: {message}")
                self.should_stop = True
                # Update UI on main thread
                AppHelper.callAfter(self.gui_controller.updateStopStatus)
        except Exception as e:
            self.gui_controller.log_message(f"[TestStopHandler] Error in handler: {e}")
            pass

class IngestionTestAppDelegate(NSObject):
    def applicationDidFinishLaunching_(self, notification):
        """Create and show the main window when the app launches."""
        self.createMainWindow()
    
    def applicationShouldTerminateAfterLastWindowClosed_(self, sender):
        """Terminate the app when the last window is closed."""
        return True
    
    def createMainWindow(self):
        """Create the main application window."""
        # Create the window
        frame = NSMakeRect(100, 100, 800, 600)
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            frame,
            NSTitledWindowMask | NSClosableWindowMask | NSMiniaturizableWindowMask | NSResizableWindowMask,
            NSBackingStoreBuffered,
            False
        )
        self.window.setTitle_("Document Ingestion Test")
        self.window.setMinSize_(NSMakeSize(600, 400))
        
        # Create the main view
        self.createMainView()
        
        # Show the window
        self.window.makeKeyAndOrderFront_(None)
        
    def createMainView(self):
        """Create the main view with all UI elements."""
        content_view = self.window.contentView()
        content_view.setWantsLayer_(True)
        
        # Create a scroll view for the log area
        scroll_view = NSScrollView.alloc().initWithFrame_(NSMakeRect(20, 20, 760, 200))
        scroll_view.setHasVerticalScroller_(True)
        
        # Create text view for logs
        self.log_text_view = NSTextView.alloc().init()
        self.log_text_view.setEditable_(False)
        self.log_text_view.setRichText_(False)
        
        # Configure the scroll view
        scroll_view.setDocumentView_(self.log_text_view)
        content_view.addSubview_(scroll_view)
        
        # Create directory selection
        dir_label = NSTextField.alloc().initWithFrame_(NSMakeRect(20, 500, 120, 24))
        dir_label.setStringValue_("Test Directory:")
        dir_label.setBezeled_(False)
        dir_label.setDrawsBackground_(False)
        dir_label.setEditable_(False)
        content_view.addSubview_(dir_label)
        
        self.dir_field = NSTextField.alloc().initWithFrame_(NSMakeRect(150, 500, 500, 24))
        self.dir_field.setStringValue_("/Users/aaron/Documents/Anke_docs_bak_19-07-24-0958")
        content_view.addSubview_(self.dir_field)
        
        dir_button = NSButton.alloc().initWithFrame_(NSMakeRect(660, 500, 100, 24))
        dir_button.setTitle_("Browse...")
        dir_button.setBezelStyle_(NSRoundedBezelStyle)
        dir_button.setAction_("browseDirectory:")
        dir_button.setTarget_(self)
        content_view.addSubview_(dir_button)
        
        # Create max files input
        max_label = NSTextField.alloc().initWithFrame_(NSMakeRect(20, 460, 150, 24))
        max_label.setStringValue_("Max Files (optional):")
        max_label.setBezeled_(False)
        max_label.setDrawsBackground_(False)
        max_label.setEditable_(False)
        content_view.addSubview_(max_label)
        
        self.max_files_field = NSTextField.alloc().initWithFrame_(NSMakeRect(180, 460, 100, 24))
        content_view.addSubview_(self.max_files_field)
        
        # Create no-clear checkbox
        self.no_clear_checkbox = NSButton.alloc().initWithFrame_(NSMakeRect(20, 420, 250, 24))
        self.no_clear_checkbox.setTitle_("Don't clear database (--no-clear)")
        self.no_clear_checkbox.setButtonType_(NSSwitchButton)
        content_view.addSubview_(self.no_clear_checkbox)
        
        # Create progress bar
        self.progress_bar = NSProgressIndicator.alloc().initWithFrame_(NSMakeRect(20, 380, 760, 20))
        self.progress_bar.setStyle_(NSProgressIndicatorBarStyle)
        self.progress_bar.setIndeterminate_(False)
        content_view.addSubview_(self.progress_bar)
        
        # Create file counter label
        self.file_counter_label = NSTextField.alloc().initWithFrame_(NSMakeRect(20, 350, 300, 24))
        self.file_counter_label.setStringValue_("Files processed: 0/0")
        self.file_counter_label.setBezeled_(False)
        self.file_counter_label.setDrawsBackground_(False)
        self.file_counter_label.setEditable_(False)
        content_view.addSubview_(self.file_counter_label)
        
        # Create current file label
        self.current_file_label = NSTextField.alloc().initWithFrame_(NSMakeRect(20, 320, 760, 24))
        self.current_file_label.setStringValue_("Current file: None")
        self.current_file_label.setBezeled_(False)
        self.current_file_label.setDrawsBackground_(False)
        self.current_file_label.setEditable_(False)
        content_view.addSubview_(self.current_file_label)
        
        # Create buttons
        self.start_button = NSButton.alloc().initWithFrame_(NSMakeRect(20, 240, 100, 30))
        self.start_button.setTitle_("Start Test")
        self.start_button.setBezelStyle_(NSRoundedBezelStyle)
        self.start_button.setAction_("startTest:")
        self.start_button.setTarget_(self)
        content_view.addSubview_(self.start_button)
        
        self.stop_button = NSButton.alloc().initWithFrame_(NSMakeRect(130, 240, 100, 30))
        self.stop_button.setTitle_("Stop Test")
        self.stop_button.setBezelStyle_(NSRoundedBezelStyle)
        self.stop_button.setAction_("stopTest:")
        self.stop_button.setTarget_(self)
        self.stop_button.setEnabled_(False)
        content_view.addSubview_(self.stop_button)
        
    def browseDirectory_(self, sender):
        """Open directory browser dialog."""
        panel = NSOpenPanel.openPanel()
        panel.setCanChooseFiles_(False)
        panel.setCanChooseDirectories_(True)
        panel.setAllowsMultipleSelection_(False)
        
        if panel.runModal() == NSOKButton:
            url = panel.URLs()[0]
            path = url.path()
            self.dir_field.setStringValue_(path)
    
    def startTest_(self, sender):
        """Start the ingestion test."""
        if test_status["running"]:
            return
            
        # Get values from UI
        test_dir = self.dir_field.stringValue()
        max_files_str = self.max_files_field.stringValue()
        no_clear = self.no_clear_checkbox.state() == NSOnState
        
        # Validate directory
        test_dir_path = Path(test_dir)
        if not test_dir_path.exists():
            self.showError_("Test directory does not exist")
            return
            
        # Parse max files
        max_files = None
        if max_files_str.strip():
            try:
                max_files = int(max_files_str.strip())
                if max_files <= 0:
                    raise ValueError("Max files must be positive")
            except ValueError as e:
                self.showError_(f"Invalid max files value: {e}")
                return
                
        # Update UI state
        self.start_button.setEnabled_(False)
        self.stop_button.setEnabled_(True)
        
        # Clear log
        self.log_text_view.setString_("")
        
        # Start test in separate thread
        test_thread = threading.Thread(
            target=self.run_test,
            args=(test_dir, max_files, no_clear),
            daemon=True
        )
        test_thread.start()
        
    def stopTest_(self, sender):
        """Request to stop the ingestion test."""
        if test_status["running"]:
            with status_lock:
                test_status["stop_requested"] = True
            self.log_message("Stop requested...")
            
    def run_test(self, test_dir, max_files, no_clear):
        """Run the ingestion test in a separate thread."""
        try:
            # Clear database if requested
            if not no_clear:
                self.log_message("Clearing database for a fresh test run...")
                clear_database_file()
            else:
                self.log_message("Skipping database clear (--no-clear specified)")
                
            # Run the ingestion test
            success = asyncio.run(self.run_ingestion_test_async(test_dir, max_files, no_clear))
            
            if success:
                # Verify database contents
                asyncio.run(self.verify_database())
                self.log_message("TEST PASSED: No warnings or errors detected")
            else:
                self.log_message("TEST FAILED: Stopped due to WARNING or ERROR")
                
        except Exception as e:
            self.log_message(f"Test failed with exception: {e}")
        finally:
            # Re-enable start button, disable stop button
            AppHelper.callAfter(self.testFinished)
            
    async def run_ingestion_test_async(self, test_dir: str, max_files: Optional[int], no_clear: bool):
        """
        Runs the full ingestion test, processing files in the specified
        directory and reporting on the results.
        """
        try:
            with status_lock:
                test_status["running"] = True
                test_status["stop_requested"] = False
                test_status["progress"] = 0
                test_status["files_processed"] = 0
                test_status["total_files"] = 0
                test_status["logs"] = []
                test_status["current_file"] = ""

            # Set up the test stop handler to capture all WARNING and ERROR messages
            test_handler = TestStopHandler(self)
            # Use DEBUG level to ensure we capture everything, then filter in the handler
            logger.add(test_handler.emit, level="DEBUG")
            
            test_dir_path = Path(test_dir)
            if not test_dir_path.exists():
                self.log_message(f"Test directory does not exist: {test_dir_path}")
                return False
                
            # Filter out hidden files and system files
            all_files = [f for f in test_dir_path.iterdir() if f.is_file() and not self.is_hidden_file(f)]
            
            # Limit files if max_files is specified
            if max_files is not None and max_files > 0:
                all_files = all_files[:max_files]
                self.log_message(f"Limited to first {max_files} files for testing")
            
            total_files = len(all_files)
            with status_lock:
                test_status["total_files"] = total_files
                
            self.log_message(f"Found {total_files} files to process in {test_dir_path} (hidden files filtered out)")
            
            # Show file types that will be processed
            file_types = {}
            for f in all_files:
                ext = f.suffix.lower()
                file_types[ext] = file_types.get(ext, 0) + 1
            
            self.log_message("File types to be processed:")
            for ext, count in sorted(file_types.items()):
                self.log_message(f"  {ext or '(no extension)'}: {count} files")

            # Update UI on main thread
            AppHelper.callAfter(self.updateFileCounter)

            document_store = DocumentStore()
            orchestrator = IngestionOrchestrator(document_store)
            
            start_time = time.time()
            self.log_message(f"Starting comprehensive ingestion test at {datetime.now()}")

            processed_files = 0
            failed_to_store = []
            failed_to_process = []

            for file_path in all_files:
                # Check if stop was requested
                with status_lock:
                    if test_status["stop_requested"]:
                        self.log_message("Test stopped by user request")
                        break
                        
                # Update current file
                with status_lock:
                    test_status["current_file"] = str(file_path.name)
                    
                # Update UI on main thread
                AppHelper.callAfter(self.updateCurrentFile)
                        
                # Check if test should stop due to critical warnings/errors
                if test_handler.should_stop:
                    self.log_message("Test stopped due to critical warnings/errors")
                    break
                    
                try:
                    event = FileEvent(
                        event_type=FileEventType.CREATED,
                        file_path=file_path,
                        timestamp=datetime.now()
                    )
                    doc_id = await orchestrator.process_file_event(event)
                    if doc_id:
                        processed_files += 1
                        self.log_message(f"({processed_files}/{total_files}) Successfully processed and stored: {file_path.name} (ID: {doc_id})")
                    else:
                        self.log_message(f"({processed_files}/{total_files}) Processed but failed to store: {file_path.name}")
                        failed_to_store.append(file_path.name)
                        self.log_message("Stopping test due to storage failure.")
                        break
                        
                    # Update progress
                    with status_lock:
                        test_status["files_processed"] = processed_files
                        test_status["progress"] = (processed_files / total_files) * 100 if total_files > 0 else 0

                    # Update UI on main thread
                    AppHelper.callAfter(self.updateProgress)
                    AppHelper.callAfter(self.updateFileCounter)

                except Exception as e:
                    self.log_message(f"Failed to process {file_path.name}: {e}")
                    failed_to_process.append(file_path.name)

            await orchestrator.cleanup()
            
            end_time = time.time()
            duration = end_time - start_time
            self.log_message(f"Ingestion test finished at {datetime.now()}")
            self.log_message(f"Total processing time: {duration:.2f} seconds")

            self.log_message("--- Comprehensive Test Summary ---")
            self.log_message(f"Total files in directory: {total_files}")
            self.log_message(f"Successfully processed and stored files: {processed_files}")
            self.log_message(f"Processed but failed to store: {len(failed_to_store)}")
            if failed_to_store:
                self.log_message("Files that failed to store:")
                for f in failed_to_store:
                    self.log_message(f"  - {f}")
            self.log_message(f"Failed to process: {len(failed_to_process)}")
            if failed_to_process:
                self.log_message("Files that failed to process:")
                for f in failed_to_process:
                    self.log_message(f"  - {f}")
            
            # Check if test was stopped due to warnings/errors
            success = not test_status["stop_requested"] and not test_handler.should_stop and len(failed_to_store) == 0
            return success
            
        except Exception as e:
            self.log_message(f"Test failed with exception: {e}")
            return False

    async def verify_database(self):
        """Verify the database contents after ingestion."""
        try:
            async with get_mcp_client() as client:
                result = await client.read_query("SELECT COUNT(*) as count FROM documents")
                total_docs = result[0]['count'] if result else 0
                self.log_message(f"Total entries in database: {total_docs}")

                result = await client.read_query("SELECT document_type, COUNT(*) as count FROM documents GROUP BY document_type")
                self.log_message("Database entries by document type:")
                for row in result:
                    self.log_message(f"  - {row['document_type']}: {row['count']}")
        except Exception as e:
            self.log_message(f"Failed to verify database: {e}")

    def is_hidden_file(self, file_path: Path) -> bool:
        """Check if a file is hidden or a system file."""
        # Hidden files (start with dot)
        if file_path.name.startswith('.'):
            return True
        
        # Common system files
        system_files = {
            '.DS_Store', '._.DS_Store', 'Thumbs.db', 'desktop.ini',
            '.directory', '.localized', '.fseventsd', '.Spotlight-V100',
            '.Trashes', '.TemporaryItems', '.DocumentRevisions-V100'
        }
        
        if file_path.name in system_files:
            return True
        
        # macOS resource fork files
        if file_path.name.startswith('._'):
            return True
        
        return False
        
    def log_message(self, message):
        """Add a message to the log."""
        # Update UI on main thread
        AppHelper.callAfter(self.updateLog_, message)
        
    def showError_(self, message):
        """Show an error message dialog."""
        alert = NSAlert.alloc().init()
        alert.setMessageText_("Error")
        alert.setInformativeText_(message)
        alert.setAlertStyle_(NSCriticalAlertStyle)
        alert.runModal()
        
    # UI Update Methods (called from main thread)
    def updateProgress(self):
        """Update the progress bar."""
        with status_lock:
            progress = test_status["progress"]
        self.progress_bar.setDoubleValue_(progress)
        
    def updateFileCounter(self):
        """Update the file counter label."""
        with status_lock:
            processed = test_status["files_processed"]
            total = test_status["total_files"]
        self.file_counter_label.setStringValue_(f"Files processed: {processed}/{total}")
        
    def updateCurrentFile(self):
        """Update the current file label."""
        with status_lock:
            current_file = test_status["current_file"]
        self.current_file_label.setStringValue_(f"Current file: {current_file}")
        
    def updateLog_(self, message):
        """Update the log text view."""
        # Add message to log
        with status_lock:
            test_status["logs"].append({
                "timestamp": datetime.now().isoformat(),
                "message": message
            })
            # Keep only the last 1000 log messages to prevent memory issues
            if len(test_status["logs"]) > 1000:
                test_status["logs"] = test_status["logs"][-1000:]
        
        # Update text view
        current_text = self.log_text_view.string()
        new_text = current_text + f"{message}\n"
        self.log_text_view.setString_(new_text)
        
        # Scroll to bottom
        text_length = len(new_text)
        range = NSMakeRange(text_length, 0)
        self.log_text_view.scrollRangeToVisible_(range)
        
    def updateStopStatus(self):
        """Update UI when stop is requested."""
        self.stop_button.setEnabled_(False)
        
    def testFinished(self):
        """Called when the test is finished."""
        with status_lock:
            test_status["running"] = False
            
        self.start_button.setEnabled_(True)
        self.stop_button.setEnabled_(False)
        self.progress_bar.setDoubleValue_(0)
        self.file_counter_label.setStringValue_("Files processed: 0/0")
        self.current_file_label.setStringValue_("Current file: None")

def main():
    """Main function to run the Mac app."""
    # Create the application
    app = NSApplication.sharedApplication()
    delegate = IngestionTestAppDelegate.alloc().init()
    app.setDelegate_(delegate)
    
    # Run the app
    AppHelper.runEventLoop()

if __name__ == "__main__":
    main()