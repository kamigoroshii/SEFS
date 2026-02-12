import os
import chromadb
from typing import List, Dict, Tuple
import numpy as np
from config import MONITOR_ROOT, CHUNK_SIZE, CHUNK_OVERLAP, TOP_K_CHUNKS, GEMINI_API_KEY
from google import genai

class RAGEngine:
    def __init__(self, embedding_model):
        """Initialize RAG engine with ChromaDB and Gemini."""
        self.embedding_model = embedding_model
        
        # Initialize ChromaDB
        chroma_path = os.path.join(MONITOR_ROOT, ".sefs_metadata", "chroma_db")
        self.chroma_client = chromadb.PersistentClient(path=chroma_path)
        
        # Get or create collection
        self.collection = self.chroma_client.get_or_create_collection(
            name="sefs_chunks",
            metadata={"description": "Document chunks for RAG"}
        )
        
        # Initialize Gemini
        if GEMINI_API_KEY:
            self.gemini_client = genai.Client(api_key=GEMINI_API_KEY)
            self.model_name = "models/gemini-2.5-flash"
            print(f"✓ Gemini API configured ({self.model_name})", flush=True)
        else:
            self.gemini_client = None
            self.model_name = None
            print("⚠ GEMINI_API_KEY not set - RAG answers disabled", flush=True)
    
    def chunk_text(self, text: str, filepath: str) -> List[Tuple[str, Dict]]:
        """Split text into overlapping chunks with metadata."""
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), CHUNK_SIZE - CHUNK_OVERLAP):
            chunk_words = words[i:i + CHUNK_SIZE]
            chunk_text = " ".join(chunk_words)
            
            if len(chunk_text.strip()) < 50:  # Skip very small chunks
                continue
            
            metadata = {
                "filepath": filepath,
                "filename": os.path.basename(filepath),
                "chunk_index": len(chunks),
                "word_count": len(chunk_words)
            }
            
            chunks.append((chunk_text, metadata))
        
        return chunks
    
    def add_document(self, filepath: str, text: str, cluster_id: int = -1, topic_label: str = ""):
        """Add document chunks to ChromaDB."""
        try:
            # Remove old chunks for this file
            self.remove_document(filepath)
            
            # Chunk the text
            chunks = self.chunk_text(text, filepath)
            
            if not chunks:
                return
            
            # Generate embeddings for each chunk
            chunk_texts = [chunk[0] for chunk in chunks]
            chunk_metadatas = [chunk[1] for chunk in chunks]
            
            # Add cluster info to metadata
            for meta in chunk_metadatas:
                meta["cluster_id"] = cluster_id
                meta["topic_label"] = topic_label
            
            # Generate embeddings
            embeddings = [self.embedding_model.encode(text).tolist() for text in chunk_texts]
            
            # Create unique IDs
            chunk_ids = [f"{filepath}__chunk_{i}" for i in range(len(chunks))]
            
            # Add to ChromaDB
            self.collection.add(
                embeddings=embeddings,
                documents=chunk_texts,
                metadatas=chunk_metadatas,
                ids=chunk_ids
            )
            
            print(f"[RAG] Added {len(chunks)} chunks for {os.path.basename(filepath)}", flush=True)
            
        except Exception as e:
            print(f"[RAG ERROR] Failed to add document: {e}", flush=True)
    
    def remove_document(self, filepath: str):
        """Remove all chunks for a document."""
        try:
            # Query for all chunks with this filepath
            results = self.collection.get(
                where={"filepath": filepath}
            )
            
            if results['ids']:
                self.collection.delete(ids=results['ids'])
                print(f"[RAG] Removed chunks for {os.path.basename(filepath)}", flush=True)
        except Exception as e:
            print(f"[RAG ERROR] Failed to remove document: {e}", flush=True)
    
    def update_cluster_info(self, filepath: str, cluster_id: int, topic_label: str):
        """Update cluster metadata for document chunks."""
        try:
            results = self.collection.get(where={"filepath": filepath})
            
            if results['ids']:
                # Update metadata for each chunk
                for chunk_id in results['ids']:
                    self.collection.update(
                        ids=[chunk_id],
                        metadatas=[{"cluster_id": cluster_id, "topic_label": topic_label}]
                    )
        except Exception as e:
            print(f"[RAG ERROR] Failed to update cluster info: {e}", flush=True)
    
    def search_chunks(self, query: str, top_k: int = TOP_K_CHUNKS, cluster_id: int = None) -> List[Dict]:
        """Search for relevant chunks using semantic similarity."""
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query).tolist()
            
            # Build where filter
            where_filter = None
            if cluster_id is not None:
                where_filter = {"cluster_id": cluster_id}
            
            # Search ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_filter
            )
            
            # Format results
            chunks = []
            if results['documents'][0]:
                for i in range(len(results['documents'][0])):
                    chunks.append({
                        "text": results['documents'][0][i],
                        "metadata": results['metadatas'][0][i],
                        "distance": results['distances'][0][i] if 'distances' in results else 0,
                        "similarity": 1 - results['distances'][0][i] if 'distances' in results else 1.0
                    })
            
            return chunks
            
        except Exception as e:
            print(f"[RAG ERROR] Search failed: {e}", flush=True)
            return []
    
    def generate_answer(self, query: str, chunks: List[Dict]) -> Dict:
        """Generate answer using Gemini based on retrieved chunks."""
        if not self.gemini_client:
            return {
                "answer": "⚠ Gemini API key not configured. Set GEMINI_API_KEY environment variable.",
                "sources": [],
                "error": "API_KEY_MISSING"
            }
        
        try:
            # Build context from chunks
            context_parts = []
            sources = []
            
            for i, chunk in enumerate(chunks):
                context_parts.append(f"[Source {i+1}: {chunk['metadata']['filename']}]\n{chunk['text']}\n")
                sources.append({
                    "filename": chunk['metadata']['filename'],
                    "filepath": chunk['metadata']['filepath'],
                    "similarity": chunk['similarity'],
                    "topic": chunk['metadata'].get('topic_label', 'Unknown'),
                    "preview": chunk['text'][:150] + "..."
                })
            
            context = "\n".join(context_parts)
            
            # Build prompt
            prompt = f"""Answer the following question based ONLY on the provided context. If the answer cannot be found in the context, say "I cannot answer this based on the available documents."

Context:
{context}

Question: {query}

Answer:"""
            
            # Generate response using new Gemini SDK
            response = self.gemini_client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            answer = response.text
            
            return {
                "answer": answer,
                "sources": sources,
                "query": query
            }
            
        except Exception as e:
            return {
                "answer": f"Error generating answer: {str(e)}",
                "sources": [],
                "error": str(e)
            }
    
    def ask(self, query: str, cluster_id: int = None) -> Dict:
        """Main RAG pipeline: search + generate answer."""
        # Search for relevant chunks
        chunks = self.search_chunks(query, top_k=TOP_K_CHUNKS, cluster_id=cluster_id)
        
        if not chunks:
            return {
                "answer": "No relevant documents found in the knowledge base.",
                "sources": [],
                "query": query
            }
        
        # Generate answer with Grok
        result = self.generate_answer(query, chunks)
        return result
    
    def get_stats(self) -> Dict:
        """Get RAG engine statistics."""
        try:
            all_chunks = self.collection.get()
            total_chunks = len(all_chunks['ids']) if all_chunks['ids'] else 0
            
            # Count unique documents
            unique_files = set()
            if all_chunks['metadatas']:
                for meta in all_chunks['metadatas']:
                    unique_files.add(meta.get('filepath', ''))
            
            return {
                "total_chunks": total_chunks,
                "total_documents": len(unique_files),
                "gemini_configured": self.gemini_client is not None
            }
        except:
            return {
                "total_chunks": 0,
                "total_documents": 0,
                "gemini_configured": False
            }
