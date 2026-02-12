import sqlite3
import numpy as np
import json
import os
from typing import Dict, Tuple, Optional
from config import MONITOR_ROOT, METADATA_DIR

class EmbeddingStorage:
    """Persistent storage for file embeddings and metadata."""
    
    def __init__(self):
        self.db_path = os.path.join(MONITOR_ROOT, METADATA_DIR, "embeddings.db")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_embeddings (
                filepath TEXT PRIMARY KEY,
                embedding BLOB NOT NULL,
                content TEXT,
                last_modified REAL NOT NULL,
                cluster_id INTEGER,
                topic_label TEXT,
                created_at REAL DEFAULT (julianday('now'))
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cluster 
            ON file_embeddings(cluster_id)
        """)
        
        conn.commit()
        conn.close()
    
    def save_embedding(self, filepath: str, embedding: np.ndarray, content: str, 
                       last_modified: float, cluster_id: int = -1, topic_label: str = ""):
        """Save or update file embedding."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Serialize embedding as JSON (more portable than pickle)
        embedding_blob = json.dumps(embedding.tolist())
        
        cursor.execute("""
            INSERT OR REPLACE INTO file_embeddings 
            (filepath, embedding, content, last_modified, cluster_id, topic_label)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (filepath, embedding_blob, content, last_modified, cluster_id, topic_label))
        
        conn.commit()
        conn.close()
    
    def get_embedding(self, filepath: str) -> Optional[Tuple[np.ndarray, str, float]]:
        """Get embedding if exists and file hasn't been modified."""
        if not os.path.exists(filepath):
            return None
        
        current_mtime = os.path.getmtime(filepath)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT embedding, content, last_modified 
            FROM file_embeddings 
            WHERE filepath = ?
        """, (filepath,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result is None:
            return None
        
        embedding_json, content, stored_mtime = result
        
        # Check if file was modified since last embedding
        if abs(current_mtime - stored_mtime) > 1.0:  # 1 second tolerance
            return None
        
        embedding = np.array(json.loads(embedding_json))
        return embedding, content, stored_mtime
    
    def load_all_embeddings(self) -> Tuple[Dict[str, np.ndarray], Dict[str, str]]:
        """Load all valid embeddings from database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT filepath, embedding, content, last_modified FROM file_embeddings")
        results = cursor.fetchall()
        conn.close()
        
        embeddings = {}
        contents = {}
        
        for filepath, embedding_json, content, stored_mtime in results:
            # Verify file still exists and hasn't been modified
            if not os.path.exists(filepath):
                continue
            
            current_mtime = os.path.getmtime(filepath)
            if abs(current_mtime - stored_mtime) > 1.0:
                continue
            
            embeddings[filepath] = np.array(json.loads(embedding_json))
            contents[filepath] = content
        
        return embeddings, contents
    
    def update_cluster(self, filepath: str, cluster_id: int, topic_label: str):
        """Update cluster assignment for a file."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE file_embeddings 
            SET cluster_id = ?, topic_label = ?
            WHERE filepath = ?
        """, (cluster_id, topic_label, filepath))
        
        conn.commit()
        conn.close()
    
    def delete_embedding(self, filepath: str):
        """Remove embedding from database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM file_embeddings WHERE filepath = ?", (filepath,))
        
        conn.commit()
        conn.close()
    
    def move_embedding(self, src: str, dest: str):
        """Move/rename embedding in database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE file_embeddings 
            SET filepath = ?
            WHERE filepath = ?
        """, (dest, src))
        
        conn.commit()
        conn.close()
    
    def get_stats(self) -> Dict:
        """Get database statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM file_embeddings")
        total_files = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT cluster_id) FROM file_embeddings WHERE cluster_id != -1")
        total_clusters = cursor.fetchone()[0]
        
        cursor.execute("SELECT AVG(length(content)) FROM file_embeddings")
        avg_content_length = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            "total_files": total_files,
            "total_clusters": total_clusters,
            "avg_content_length": int(avg_content_length)
        }
