import os
try:
    import pypdf
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False
from typing import List, Dict, Optional, Tuple
from sentence_transformers import SentenceTransformer
from sklearn.cluster import DBSCAN
from sklearn.feature_extraction.text import CountVectorizer
from keybert import KeyBERT
import numpy as np

class ContentAnalyzer:
    def __init__(self, model_name: str):
        print(f"Loading embedding model: {model_name}...", flush=True)
        self.model = SentenceTransformer(model_name)
        self.kw_model = KeyBERT(model=self.model)
        self.cluster_centroids: Dict[Tuple[int, str], np.ndarray] = {}  # Track centroids for stability
        print("Model loaded.", flush=True)

    def extract_text(self, file_path: str) -> Optional[str]:
        """Extracts text from PDF or Text files."""
        try:
            _, ext = os.path.splitext(file_path)
            ext = ext.lower()

            if ext == '.txt':
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
            elif ext == '.pdf':
                if not HAS_PYPDF:
                    print(f"Warning: pypdf not installed, skipping PDF: {file_path}", flush=True)
                    return None
                text = ""
                with open(file_path, 'rb') as f:
                    reader = pypdf.PdfReader(f)
                    for page in reader.pages:
                        extracted = page.extract_text()
                        if extracted:
                            text += extracted + "\n"
                return text
            return None
        except Exception as e:
            print(f"Error reading {file_path}: {e}", flush=True)
            return None

    def generate_embedding(self, text: str) -> np.ndarray:
        """Generates a vector embedding for the given text."""
        return self.model.encode(text, convert_to_numpy=True)
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[np.ndarray]:
        """Generates embeddings for multiple texts efficiently (batched)."""
        embeddings = self.model.encode(texts, batch_size=32, convert_to_numpy=True, show_progress_bar=False)
        return embeddings if isinstance(embeddings, list) else embeddings.tolist()

    def extract_topic_label(self, texts: List[str]) -> str:
        """
        Extracts a representative topic label using KeyBERT for semantic keyword extraction.
        Returns a string like "Quantum_Physics" or "Machine_Learning".
        """
        try:
            if not texts: return "Misc"
            
            # Combine all texts for better context
            combined_text = " ".join(texts[:3])  # Use first 3 docs to avoid token limits
            
            # Use KeyBERT to extract semantically meaningful keywords
            keywords = self.kw_model.extract_keywords(
                combined_text,
                keyphrase_ngram_range=(1, 2),
                stop_words='english',
                top_n=1,
                use_mmr=True,
                diversity=0.7
            )
            
            if keywords and len(keywords) > 0:
                # Get the top keyword and clean it
                keyword = keywords[0][0]  # (keyword, score) tuple
                topic = keyword.replace(' ', '_').title()
                
                # Filter out weak words
                weak_words = ['like', 'consists', 'include', 'contains', 'called', 'known']
                if any(weak in topic.lower() for weak in weak_words):
                    # Fallback to second keyword if available
                    if len(keywords) > 1:
                        topic = keywords[1][0].replace(' ', '_').title()
                    else:
                        topic = "General_Topic"
                
                return topic
            return "General_Topic"
        except Exception as e:
            print(f"Topic extraction failed: {e}")
            return "Cluster"

    def cluster_files_with_topics(self, file_embeddings: Dict[str, np.ndarray], file_contents: Dict[str, str], eps: float = 0.3, min_samples: int = 1) -> Dict[str, Tuple[int, str]]:
        """
        Clusters files and assigns a TOPIC LABEL to each cluster with centroid tracking for stability.
        Returns: {filepath: (cluster_id, topic_label)}
        """
        if not file_embeddings:
            return {}

        filenames = list(file_embeddings.keys())
        embeddings = list(file_embeddings.values())
        
        if len(embeddings) == 0:
            return {}

        X = np.array(embeddings)
        clustering = DBSCAN(eps=eps, min_samples=min_samples, metric='cosine').fit(X)
        labels = clustering.labels_
        
        # Group files by cluster to determine topic
        cluster_docs: Dict[int, List[str]] = {}
        cluster_embeddings: Dict[int, List[np.ndarray]] = {}
        
        for i, label in enumerate(labels):
            if label == -1: continue # Noise
            if label not in cluster_docs: 
                cluster_docs[label] = []
                cluster_embeddings[label] = []
            
            fname = filenames[i]
            if fname in file_contents:
                cluster_docs[label].append(file_contents[fname])
            cluster_embeddings[label].append(embeddings[i])

        # Generate labels for each cluster and track centroids
        cluster_labels: Dict[int, str] = {}
        new_centroids: Dict[Tuple[int, str], np.ndarray] = {}
        
        for label, docs in cluster_docs.items():
            topic = self.extract_topic_label(docs)
            cluster_labels[label] = topic
            
            # Calculate centroid for stability tracking
            if label in cluster_embeddings and len(cluster_embeddings[label]) > 0:
                centroid = np.mean(cluster_embeddings[label], axis=0)
                new_centroids[(label, topic)] = centroid
        
        # Update centroid memory
        self.cluster_centroids.update(new_centroids)

        # Build result
        result = {}
        for i, fname in enumerate(filenames):
            label = int(labels[i])
            topic = cluster_labels.get(label, "Uncategorized")
            if label == -1: topic = "Uncategorized"
            
            result[fname] = (label, topic)
            
        return result
