import os
import shutil
import time
from typing import Set

class FileManager:
    def __init__(self, root_dir: str):
        self.root_dir = root_dir
        # Set of paths that are currently being processed by the system
        # to avoid infinite loops when the system moves files.
        self.pending_moves: Set[str] = set()

    def safe_move(self, src: str, dst: str):
        """
        Moves a file from src to dst safely.
        Adds the destination to pending_moves so the monitor knows to ignore it.
        """
        if src == dst:
            return

        try:
            # Create destination directory if it doesn't exist
            dst_dir = os.path.dirname(dst)
            if not os.path.exists(dst_dir):
                os.makedirs(dst_dir)

            print(f"[SYSTEM_MOVE] Moving {src} -> {dst}", flush=True)
            
            # Mark this move as internal
            self.pending_moves.add(dst)
            self.pending_moves.add(src)

            shutil.move(src, dst)
            
            # Clean up old directory if empty
            src_dir = os.path.dirname(src)
            if os.path.exists(src_dir) and src_dir != self.root_dir:
                try:
                    if not os.listdir(src_dir):  # Directory is empty
                        os.rmdir(src_dir)
                        print(f"[CLEANUP] Removed empty folder: {os.path.basename(src_dir)}", flush=True)
                except:
                    pass
            
            # Schedule cleanup of pending_moves
            import threading
            def clear_pending():
                time.sleep(2)  # Wait for watchdog events to settle
                self.pending_moves.discard(dst)
                self.pending_moves.discard(src)
            threading.Thread(target=clear_pending, daemon=True).start()
            
        except Exception as e:
            print(f"Error moving file: {e}", flush=True)
            self.pending_moves.discard(dst)
            self.pending_moves.discard(src)

    def is_system_operation(self, path: str) -> bool:
        """
        Checks if an event on 'path' is likely caused by the system.
        """
        if path in self.pending_moves:
            return True
        return False
    
    def clear_pending(self, path: str):
        if path in self.pending_moves:
            self.pending_moves.remove(path)
