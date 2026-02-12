import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from collections import deque
from threading import Timer

class SEFSHandler(FileSystemEventHandler):
    def __init__(self, callback, file_manager):
        self.callback = callback
        self.file_manager = file_manager
        self.event_queue = deque()
        self.debounce_timer = None
        self.debounce_seconds = 2  # Batch events for 2 seconds

    def on_any_event(self, event):
        if event.is_directory:
            return

        # Ignore metadata folder and database files (prevents infinite loops)
        if '.sefs_metadata' in event.src_path or event.src_path.endswith(('.db-journal', '.db-wal')):
            return
        
        # For move events, also check destination
        if hasattr(event, 'dest_path'):
            if '.sefs_metadata' in event.dest_path or event.dest_path.endswith(('.db-journal', '.db-wal')):
                return

        # Check if system operation on source
        if self.file_manager.is_system_operation(event.src_path):
            print(f"Ignoring system event on: {event.src_path}", flush=True)
            return
        
        # For move events, also check destination
        if hasattr(event, 'dest_path') and self.file_manager.is_system_operation(event.dest_path):
            print(f"Ignoring system event on: {event.dest_path}", flush=True)
            return
        
        # Add to queue
        self.event_queue.append(event)
        
        # Reset debounce timer
        if self.debounce_timer:
            self.debounce_timer.cancel()
        
        # Process queue after debounce period
        self.debounce_timer = Timer(self.debounce_seconds, self._process_queue)
        self.debounce_timer.start()
    
    def _process_queue(self):
        """Process batched events."""
        if not self.event_queue:
            return
        
        print(f"[BATCH] Processing {len(self.event_queue)} queued events", flush=True)
        
        # Deduplicate events (keep latest per file)
        unique_events = {}
        while self.event_queue:
            event = self.event_queue.popleft()
            unique_events[event.src_path] = event
        
        # Process unique events
        for event in unique_events.values():
            self.callback(event)
        
        print(f"[BATCH] Processed {len(unique_events)} unique file operations", flush=True)

class FSMonitor:
    def __init__(self, path, callback, file_manager):
        self.observer = Observer()
        self.handler = SEFSHandler(callback, file_manager)
        self.path = path

    def start(self):
        print(f"Starting Monitor on {self.path}", flush=True)
        if not os.path.exists(self.path):
            os.makedirs(self.path)
        self.observer.schedule(self.handler, self.path, recursive=True)
        self.observer.start()

    def stop(self):
        self.observer.stop()
        self.observer.join()
