"""
Quick script to verify ChromaDB is working and has data
"""
import os
import chromadb
from pathlib import Path

# Path to ChromaDB
MONITOR_ROOT = r"F:\vibecode\sefs_root"
chroma_path = os.path.join(MONITOR_ROOT, ".sefs_metadata", "chroma_db")

print("=" * 60)
print("ChromaDB Verification Tool")
print("=" * 60)
print(f"\nChromaDB path: {chroma_path}")
print(f"Path exists: {os.path.exists(chroma_path)}")

if not os.path.exists(chroma_path):
    print("\n❌ ChromaDB directory not found!")
    exit(1)

# Initialize ChromaDB client
client = chromadb.PersistentClient(path=chroma_path)

# Get collection
try:
    collection = client.get_collection(name="sefs_chunks")
    print(f"\n✅ Collection 'sefs_chunks' found!")
    
    # Get all chunks
    all_data = collection.get()
    
    total_chunks = len(all_data['ids']) if all_data['ids'] else 0
    print(f"\n📊 Total chunks stored: {total_chunks}")
    
    if total_chunks > 0:
        # Count unique files
        unique_files = set()
        if all_data['metadatas']:
            for meta in all_data['metadatas']:
                unique_files.add(meta.get('filepath', 'unknown'))
        
        print(f"📄 Unique documents: {len(unique_files)}")
        print(f"\n📂 Documents in ChromaDB:")
        for i, filepath in enumerate(sorted(unique_files), 1):
            filename = os.path.basename(filepath)
            # Count chunks for this file
            chunks_for_file = sum(1 for m in all_data['metadatas'] if m.get('filepath') == filepath)
            print(f"   {i}. {filename} ({chunks_for_file} chunks)")
        
        # Show sample chunk
        if all_data['documents']:
            print(f"\n💬 Sample chunk (first 200 chars):")
            print(f"   {all_data['documents'][0][:200]}...")
            print(f"\n   Metadata: {all_data['metadatas'][0]}")
    else:
        print("\n⚠️  No chunks found in ChromaDB!")
        print("\nPossible reasons:")
        print("   1. Backend hasn't processed any files yet")
        print("   2. Files don't contain enough text")
        print("   3. RAG engine initialization failed")
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\nCollection might not exist yet. Run the backend first to initialize.")

print("\n" + "=" * 60)
