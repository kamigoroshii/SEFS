import os
import sys
import time
import shutil
from typing import Dict, List, Set, Tuple
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import uvicorn
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue
import threading

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Imports
try:
    from config import MONITOR_ROOT, MODEL_NAME, CLUSTER_EPS, CLUSTER_MIN_SAMPLES
    from analyzer import ContentAnalyzer
    from monitor import FSMonitor
    from file_ops import FileManager
    from storage import EmbeddingStorage
    from rag_engine import RAGEngine
except ImportError as e:
    # Fallback if running as module
    from .config import MONITOR_ROOT, MODEL_NAME, CLUSTER_EPS, CLUSTER_MIN_SAMPLES
    from .analyzer import ContentAnalyzer
    from .monitor import FSMonitor
    from .file_ops import FileManager
    from .storage import EmbeddingStorage
    from .rag_engine import RAGEngine

# Global State
file_embeddings: Dict[str, any] = {} 
file_contents: Dict[str, str] = {}
file_clusters: Dict[str, Tuple[int, str]] = {}
file_processing_queue: Queue = Queue()  # Queue for concurrent file processing
executor = ThreadPoolExecutor(max_workers=4)  # Process up to 4 files concurrently

analyzer = None
file_manager = None
monitor = None
storage = None
rag_engine = None

def process_file(filepath: str):
    global file_embeddings, file_contents, storage
    
    if os.path.basename(filepath).startswith('.'): return False
    if not (filepath.endswith('.txt') or filepath.endswith('.pdf')): return False

    print(f"[PROCESS] Analyzing: {filepath}", flush=True)
    
    # Check if cached embedding exists and file hasn't changed
    cached = storage.get_embedding(filepath)
    if cached:
        embedding, content, _ = cached
        file_embeddings[filepath] = embedding
        file_contents[filepath] = content
        print(f"[CACHE] Using cached embedding for: {filepath}", flush=True)
        return True
    
    # Generate new embedding
    max_retries = 3
    for attempt in range(max_retries):
        try:
            text = analyzer.extract_text(filepath)
            if text and len(text.strip()) > 10:
                print(f"[PROCESS] Extracted text. Generating embedding...", flush=True)
                emb = analyzer.generate_embedding(text)
                
                file_embeddings[filepath] = emb
                file_contents[filepath] = text
                
                # Save to persistent storage
                last_modified = os.path.getmtime(filepath)
                storage.save_embedding(filepath, emb, text, last_modified)
                
                # Add to RAG engine
                if rag_engine:
                    cluster_info = file_clusters.get(filepath, (-1, ""))
                    rag_engine.add_document(filepath, text, cluster_info[0], cluster_info[1])
                
                return True
            else:
                return False
        except Exception as e:
            print(f"[ERROR] Attempt {attempt + 1}: {e}", flush=True)
            time.sleep(0.5)  # Reduced from 1 second
    return False

def process_files_batch(filepaths: List[str]):
    """Process multiple files concurrently."""
    futures = []
    for filepath in filepaths:
        future = executor.submit(process_file, filepath)
        futures.append(future)
    
    # Wait for all to complete
    completed = 0
    for future in as_completed(futures):
        try:
            result = future.result()
            if result:
                completed += 1
        except Exception as e:
            print(f"[ERROR] Concurrent processing failed: {e}", flush=True)
    
    print(f"[BATCH] Processed {completed}/{len(filepaths)} files concurrently", flush=True)
    
    # Trigger reclustering after batch
    if completed > 0:
        recluster_and_organize()

def recluster_and_organize():
    global file_clusters, storage
    
    if not file_embeddings: 
        file_clusters.clear()
        return

    print(f"[GRAVITY] Recalculating Semantic Gravity...", flush=True)
    
    # Prune missing files from all dictionaries
    existing_files = {k: v for k, v in file_embeddings.items() if os.path.exists(k)}
    file_embeddings.clear()
    file_embeddings.update(existing_files)
    
    file_contents_clean = {k: v for k, v in file_contents.items() if k in existing_files}
    file_contents.clear()
    file_contents.update(file_contents_clean)
    
    file_clusters_clean = {k: v for k, v in file_clusters.items() if k in existing_files}
    file_clusters.clear()
    file_clusters.update(file_clusters_clean)

    if not file_embeddings: return

    # Cluster with Topics
    new_clusters = analyzer.cluster_files_with_topics(file_embeddings, file_contents, eps=CLUSTER_EPS, min_samples=CLUSTER_MIN_SAMPLES)
    
    # Organize files
    for filepath, (cluster_id, topic_label) in new_clusters.items():
        if cluster_id == -1: continue
        
        folder_name = f"{topic_label}_{cluster_id}" 
        filename = os.path.basename(filepath)
        parent_name = os.path.basename(os.path.dirname(filepath))
        
        if parent_name == folder_name:
            file_clusters[filepath] = (cluster_id, topic_label)
            storage.update_cluster(filepath, cluster_id, topic_label)
            continue
            
        target_dir = os.path.join(MONITOR_ROOT, folder_name)
        target_path = os.path.join(target_dir, filename)
        
        if filepath != target_path:
            print(f"[GRAVITY] File drifted to stronger semantic center: {folder_name}", flush=True)
            
            emb = file_embeddings.pop(filepath, None)
            content = file_contents.pop(filepath, None)
            
            if emb is not None: file_embeddings[target_path] = emb
            if content is not None: file_contents[target_path] = content
            
            file_clusters[target_path] = (cluster_id, topic_label)
            if filepath in file_clusters: del file_clusters[filepath]
            
            # Update storage with new path
            storage.update_cluster(target_path, cluster_id, topic_label)
            
            # Update RAG engine cluster info
            if rag_engine:
                rag_engine.update_cluster_info(target_path, cluster_id, topic_label)
            
            file_manager.safe_move(filepath, target_path)
    
    # Clean up empty cluster folders
    try:
        for item in os.listdir(MONITOR_ROOT):
            item_path = os.path.join(MONITOR_ROOT, item)
            if os.path.isdir(item_path) and item != '.sefs_metadata':
                if not os.listdir(item_path):  # Empty folder
                    os.rmdir(item_path)
                    print(f"[CLEANUP] Removed empty cluster folder: {item}", flush=True)
    except Exception as e:
        pass

def calculate_entropy() -> Dict:
    """Calculate semantic entropy metrics."""
    if len(file_embeddings) < 2:
        return {"entropy": 0.0, "cohesion": 1.0, "separation": 0.0}
    
    from sklearn.metrics import silhouette_score
    
    embeddings_array = np.array(list(file_embeddings.values()))
    
    # Get cluster labels
    cluster_labels = []
    for filepath in file_embeddings.keys():
        if filepath in file_clusters:
            cluster_labels.append(file_clusters[filepath][0])
        else:
            cluster_labels.append(-1)
    
    # Calculate silhouette score
    if len(set(cluster_labels)) > 1:
        try:
            silhouette = silhouette_score(embeddings_array, cluster_labels, metric='cosine')
            entropy = (1.0 - silhouette) / 2  # Normalize to 0-1
            return {
                "entropy": max(0.0, min(1.0, entropy)),
                "cohesion": (silhouette + 1) / 2,
                "separation": abs(silhouette)
            }
        except:
            pass
    
    return {"entropy": 0.5, "cohesion": 0.5, "separation": 0.0}

def event_callback(events):
    """Handle batched file system events for concurrent processing."""
    if not isinstance(events, list):
        # Single event passed (backwards compatibility)
        events = [events]
    
    files_to_process = []
    files_to_delete = []
    moved_files = {}  # {src: dest}
    
    for event in events:
        if event.is_directory: 
            continue
        
        src = event.src_path
        etype = event.event_type
        
        if etype == 'created' or etype == 'modified':
            if src not in files_to_process and src not in files_to_delete:
                files_to_process.append(src)
                
        elif etype == 'moved':
            dest = event.dest_path
            moved_files[src] = dest
            if src in file_embeddings:
                # Move embeddings
                if src in file_embeddings:
                    file_embeddings[dest] = file_embeddings.pop(src)
                if src in file_contents:
                    file_contents[dest] = file_contents.pop(src)
                if src in file_clusters:
                    file_clusters[dest] = file_clusters.pop(src)
                storage.move_embedding(src, dest)
                if rag_engine:
                    rag_engine.remove_document(src)
                    rag_engine.add_document(dest, file_contents.get(dest, ""))
            else:
                files_to_process.append(dest)
                
        elif etype == 'deleted':
            if src not in files_to_process:
                files_to_delete.append(src)
    
    # Process files concurrently
    if files_to_process:
        try:
            process_files_batch(files_to_process)
        except Exception as e:
            print(f"[ERROR] Batch processing {files_to_process}: {e}", flush=True)
    
    # Delete files
    for filepath in files_to_delete:
        try:
            if filepath in file_embeddings: 
                del file_embeddings[filepath]
            if filepath in file_contents: 
                del file_contents[filepath]
            if filepath in file_clusters:
                del file_clusters[filepath]
            storage.delete_embedding(filepath)
            if rag_engine:
                rag_engine.remove_document(filepath)
            recluster_and_organize()
        except Exception as e:
            print(f"[ERROR] Deleting {filepath}: {e}", flush=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global analyzer, file_manager, monitor, storage, rag_engine
    print("="*60, flush=True)
    print("Initializing Semantic Gravity Engine...", flush=True)
    print("="*60, flush=True)
    
    # Initialize storage first
    storage = EmbeddingStorage()
    print("✓ Storage initialized", flush=True)
    
    # Initialize analyzer
    analyzer = ContentAnalyzer(MODEL_NAME)
    print("✓ Analyzer ready", flush=True)
    
    # Initialize RAG engine
    rag_engine = RAGEngine(analyzer.model)
    print("✓ RAG engine initialized", flush=True)
    
    # Initialize file manager
    file_manager = FileManager(MONITOR_ROOT)
    print("✓ File manager ready", flush=True)
    
    # Scan and index all existing files (use concurrent processing)
    print("Scanning workspace for files...", flush=True)
    files_to_process = []
    for root, dirs, files in os.walk(MONITOR_ROOT):
        # Skip metadata folder
        if '.sefs_metadata' in root:
            continue
        for filename in files:
            if filename.endswith('.txt') or filename.endswith('.pdf'):
                filepath = os.path.join(root, filename)
                files_to_process.append(filepath)
    
    # Process all files concurrently in batches
    batch_size = 8
    for i in range(0, len(files_to_process), batch_size):
        batch = files_to_process[i:i+batch_size]
        process_files_batch(batch)
    
    print(f"✓ Indexed {len(file_embeddings)} files", flush=True)
    
    # Perform initial clustering
    if file_embeddings:
        print(f"Performing initial clustering...", flush=True)
        recluster_and_organize()
        print(f"✓ Initial clustering complete: {len(file_clusters)} files organized", flush=True)
    
    # Start monitoring
    monitor = FSMonitor(MONITOR_ROOT, event_callback, file_manager)
    monitor.start()
    print("✓ File system monitor active", flush=True)
    
    print("="*60, flush=True)
    print("🚀 SEFS is ONLINE", flush=True)
    print("="*60, flush=True)
    
    yield
    
    print("\nShutting down...", flush=True)
    monitor.stop()

# Middleware to prevent caching
class NoCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

app = FastAPI(lifespan=lifespan)
app.add_middleware(NoCacheMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/graph")
def get_graph():
    nodes = []
    links = []
    
    # Calculate entropy metrics
    entropy_metrics = calculate_entropy()
    
    nodes.append({
        "id": "ROOT", 
        "group": "root", 
        "val": 30, 
        "label": "Semantic Core",
        "entropy": entropy_metrics["entropy"]
    })

    # Unique clusters
    seen_clusters = {}
    
    for _, (cid, topic) in file_clusters.items():
        if cid == -1: continue
        key = (cid, topic)
        if key not in seen_clusters:
            node_id = f"{topic}_{cid}"
            seen_clusters[key] = node_id
            nodes.append({"id": node_id, "group": "topic", "val": 20, "label": topic})
            links.append({"source": "ROOT", "target": node_id})

    for filepath, (cid, topic) in file_clusters.items():
        fname = os.path.basename(filepath)
        if cid != -1:
            target_node = seen_clusters.get((cid, topic))
            nodes.append({"id": fname, "group": "file", "val": 5, "label": fname, "filepath": filepath})
            links.append({"source": fname, "target": target_node})
        else:
            nodes.append({"id": fname, "group": "noise", "val": 3, "label": fname, "filepath": filepath})
            links.append({"source": fname, "target": "ROOT"})
        
    return {
        "nodes": nodes, 
        "links": links,
        "entropy": entropy_metrics
    }

@app.get("/stats")
def get_stats():
    """Get system statistics."""
    db_stats = storage.get_stats()
    entropy = calculate_entropy()
    rag_stats = rag_engine.get_stats() if rag_engine else {}
    
    return {
        **db_stats,
        "cached_files": len(file_embeddings),
        "active_clusters": len(set(c[0] for c in file_clusters.values() if c[0] != -1)),
        "entropy_score": entropy["entropy"],
        "cohesion": entropy["cohesion"],
        **rag_stats
    }

@app.get("/clusters")
def get_clusters():
    """Get list of available clusters/topics."""
    clusters = {}
    for filepath, (cid, topic) in file_clusters.items():
        if cid != -1:
            cluster_id = f"{topic}_{cid}"
            if cluster_id not in clusters:
                clusters[cluster_id] = {"id": cid, "topic": topic, "files": []}
            clusters[cluster_id]["files"].append(os.path.basename(filepath))
    return {"clusters": list(clusters.values())}

@app.post("/move-file")
def move_file(request: dict):
    """Move a file to a different cluster when dragged in UI."""
    filepath = request.get("filepath")
    target_cluster = request.get("target_cluster")
    
    if not filepath or not os.path.exists(filepath):
        return {"success": False, "error": "File not found"}
    
    # Parse target cluster name
    parts = target_cluster.rsplit('_', 1)
    if len(parts) != 2:
        return {"success": False, "error": "Invalid cluster format"}
    
    topic_label = parts[0]
    try:
        cluster_id = int(parts[1])
    except ValueError:
        return {"success": False, "error": "Invalid cluster ID"}
    
    # Update cluster assignment
    file_clusters[filepath] = (cluster_id, topic_label)
    
    # Move file physically
    filename = os.path.basename(filepath)
    target_dir = os.path.join(MONITOR_ROOT, target_cluster)
    target_path = os.path.join(target_dir, filename)
    
    if filepath != target_path:
        # Update embeddings cache
        if filepath in file_embeddings:
            file_embeddings[target_path] = file_embeddings.pop(filepath)
        if filepath in file_contents:
            file_contents[target_path] = file_contents.pop(filepath)
        
        file_clusters[target_path] = file_clusters.pop(filepath)
        
        # Update storage
        storage.update_cluster(target_path, cluster_id, topic_label)
        
        file_manager.safe_move(filepath, target_path)
        
        return {"success": True, "new_path": target_path}
    
    return {"success": True, "message": "Already in target cluster"}

@app.post("/search")
def semantic_search(request: dict):
    """Semantic search: find files similar to a query."""
    query = request.get("query", "")
    top_k = request.get("top_k", 5)
    
    if not query or not file_embeddings:
        return {"results": []}
    
    # Generate query embedding
    query_embedding = analyzer.generate_embedding(query)
    
    # Calculate cosine similarity with all files
    from sklearn.metrics.pairwise import cosine_similarity
    
    results = []
    for filepath, file_emb in file_embeddings.items():
        similarity = cosine_similarity(
            query_embedding.reshape(1, -1),
            file_emb.reshape(1, -1)
        )[0][0]
        
        # Get cluster info
        cluster_info = file_clusters.get(filepath, (-1, "Uncategorized"))
        
        results.append({
            "filepath": filepath,
            "filename": os.path.basename(filepath),
            "similarity": float(similarity),
            "cluster_id": cluster_info[0],
            "topic": cluster_info[1],
            "preview": file_contents.get(filepath, "")[:200] + "..."
        })
    
    # Sort by similarity and return top K
    results.sort(key=lambda x: x["similarity"], reverse=True)
    return {"results": results[:top_k], "query": query}

@app.post("/ask")
def ask_question(request: dict):
    """RAG endpoint: answer questions using document knowledge."""
    query = request.get("query", "")
    cluster_id = request.get("cluster_id", None)  # Optional: search within specific cluster
    
    if not query or not rag_engine:
        return {"error": "RAG engine not initialized or empty query"}
    
    # Use RAG pipeline
    result = rag_engine.ask(query, cluster_id=cluster_id)
    return result

@app.post("/open-file")
def open_file_in_os(request: dict):
    """Open file in OS default application."""
    filepath = request.get("filepath", "")
    
    if not filepath or not os.path.exists(filepath):
        return {"error": "File not found", "filepath": filepath}
    
    try:
        import subprocess
        import platform
        
        system = platform.system()
        if system == "Windows":
            os.startfile(filepath)
        elif system == "Darwin":  # macOS
            subprocess.run(["open", filepath])
        else:  # Linux
            subprocess.run(["xdg-open", filepath])
        
        return {"success": True, "filepath": filepath}
    except Exception as e:
        return {"error": str(e), "filepath": filepath}

if __name__ == "__main__":
    if not os.path.exists(MONITOR_ROOT): 
        os.makedirs(MONITOR_ROOT)
    uvicorn.run(app, host="127.0.0.1", port=8000)
