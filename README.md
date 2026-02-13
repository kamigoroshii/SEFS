# 🧠 Semantic Entropy File System (SEFS)

> An intelligent, AI-powered file organization system that automatically categorizes and organizes your documents based on semantic content understanding.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![React](https://img.shields.io/badge/React-18.2.0-61DAFB.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-latest-009688.svg)](https://fastapi.tiangolo.com/)

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [How to Run](#-how-to-run)
- [Usage](#-usage)
- [Project Structure](#-project-structure)
- [Configuration](#-configuration)
- [Demo](#-demo)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🎯 Overview

**SEFS (Semantic Entropy File System)** is an innovative file management system that leverages AI and machine learning to automatically organize your documents. Instead of manually sorting files into folders, SEFS analyzes the semantic content of your documents using state-of-the-art NLP models and intelligently groups similar files together.

The system monitors a designated folder in real-time, processes new files as they arrive, and organizes them into semantic clusters. A beautiful web dashboard provides live visualization of your document clusters, making it easy to understand how your files are organized.

---

## ✨ Features

- 🤖 **AI-Powered Semantic Analysis** - Uses advanced sentence transformers to understand document content
- 📊 **Automatic Clustering** - Groups similar documents using DBSCAN clustering algorithm
- 🔄 **Real-Time Monitoring** - Watches for new files and processes them automatically
- 📈 **Interactive Visualization** - Beautiful 2D/3D force-directed graph showing document relationships
- 🗂️ **Auto-Organization** - Moves files into semantically meaningful folders
- 💬 **RAG-Powered Q&A** - Query your documents using natural language (powered by Google Gemini)
- 📄 **Multi-Format Support** - Handles PDF and text files
- ⚡ **Fast Processing** - Concurrent file processing with ThreadPoolExecutor
- 💾 **Vector Storage** - Uses ChromaDB for efficient embedding storage and retrieval

---

## 🛠️ Tech Stack

### Backend
- **[Python 3.8+](https://www.python.org/)** - Core programming language
- **[FastAPI](https://fastapi.tiangolo.com/)** - High-performance web framework
- **[Uvicorn](https://www.uvicorn.org/)** - ASGI server
- **[Sentence Transformers](https://www.sbert.net/)** - State-of-the-art text embeddings
- **[Scikit-learn](https://scikit-learn.org/)** - Machine learning (DBSCAN clustering)
- **[ChromaDB](https://www.trychroma.com/)** - Vector database for embeddings
- **[Google Gemini API](https://ai.google.dev/)** - RAG-powered Q&A
- **[Watchdog](https://pythonhosted.org/watchdog/)** - File system monitoring
- **[PyPDF](https://pypdf.readthedocs.io/)** - PDF text extraction
- **NumPy** - Numerical computing

### Frontend
- **[React 18](https://react.dev/)** - UI library
- **[TypeScript](https://www.typescriptlang.org/)** - Type-safe JavaScript
- **[Vite](https://vitejs.dev/)** - Next-generation build tool
- **[React Force Graph](https://github.com/vasturiano/react-force-graph)** - Interactive graph visualization
- **[Axios](https://axios-http.com/)** - HTTP client
- **[Three.js](https://threejs.org/)** - 3D graphics (for 3D graph mode)

---

## 📦 Prerequisites

Before running SEFS, ensure you have the following installed:

- **Python 3.8 or higher** - [Download Python](https://www.python.org/downloads/)
- **Node.js 16+ and npm** - [Download Node.js](https://nodejs.org/)
- **Git** - [Download Git](https://git-scm.com/)

### Optional
- **Google Gemini API Key** - For RAG Q&A functionality ([Get API Key](https://ai.google.dev/))

---

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/vibecode.git
cd vibecode
```

### 2. Install Backend Dependencies

```bash
cd backend
pip install -r ../requirements.txt
```

**Backend Dependencies:**
```
fastapi
uvicorn
python-multipart
watchdog
sentence-transformers
scikit-learn
numpy
pypdf
protobuf<4.0.0
requests
chromadb
google-genai
python-dotenv
```

### 3. Install Frontend Dependencies

```bash
cd ../frontend
npm install
```

### 4. Configure Environment (Optional)

Create a `.env` file in the `backend` directory for Google Gemini API:

```env
GOOGLE_API_KEY=your_api_key_here
```

---

## ▶️ How to Run

### Option 1: Quick Start (Windows)

Simply double-click `run_sefs.bat` in the project root directory. This will:
- Start the FastAPI backend server on `http://localhost:8000`
- Start the React frontend dev server on `http://localhost:5173`

### Option 2: Manual Start

#### Start Backend

```bash
cd backend
python main.py
```

The API will be available at `http://localhost:8000`

#### Start Frontend

Open a new terminal:

```bash
cd frontend
npm run dev
```

The web interface will open at `http://localhost:5173`

---

## 📖 Usage

### Basic Workflow

1. **Start the Application** - Use `run_sefs.bat` or start manually
2. **Open the Dashboard** - Navigate to `http://localhost:5173` in your browser
3. **Add Files** - Drop PDF or text files into the `sefs_root` folder
4. **Watch the Magic** 🎩✨
   - Files are automatically analyzed
   - Semantic embeddings are generated
   - Files are clustered with similar documents
   - Files are moved to `sefs_root/ClusterName_X/` folders
   - Dashboard updates in real-time

### Monitored Directory

By default, SEFS monitors: `F:\vibecode\sefs_root`

You can change this in `backend/config.py`:

```python
MONITOR_ROOT = r"F:\vibecode\sefs_root"
```

### Dashboard Features

- **Graph Visualization** - See how your documents relate to each other
- **Live Updates** - Real-time graph updates as files are processed
- **Node Information** - Click nodes to see file details
- **Cluster Colors** - Each cluster has a unique color

---

## 📁 Project Structure

```
vibecode/
├── backend/                    # Python FastAPI backend
│   ├── main.py                # Main server & API endpoints
│   ├── analyzer.py            # Content analysis & embeddings
│   ├── monitor.py             # File system monitoring
│   ├── file_ops.py            # File operations & clustering
│   ├── storage.py             # ChromaDB vector storage
│   ├── rag_engine.py          # RAG Q&A engine
│   ├── config.py              # Configuration settings
│   └── verify_chromadb.py     # Database verification tool
├── frontend/                   # React TypeScript frontend
│   ├── src/
│   │   ├── App.tsx            # Main app component
│   │   ├── main.tsx           # Entry point
│   │   └── components/
│   │       └── GraphView.tsx  # Graph visualization component
│   ├── public/
│   │   ├── manifest.json      # PWA manifest
│   │   └── sw.js              # Service worker
│   ├── package.json           # Node dependencies
│   ├── vite.config.ts         # Vite configuration
│   └── tsconfig.json          # TypeScript configuration
├── sefs_root/                  # Monitored directory for files
│   ├── Cluster_0/             # Auto-created semantic folders
│   ├── Cluster_1/
│   └── ...
├── requirements.txt            # Python dependencies
├── run_sefs.bat               # Quick start script (Windows)
└── README.md                  # This file
```

---

## ⚙️ Configuration

### Backend Configuration (`backend/config.py`)

```python
MONITOR_ROOT = r"F:\vibecode\sefs_root"  # Folder to monitor
MODEL_NAME = "all-MiniLM-L6-v2"          # Sentence transformer model
CLUSTER_EPS = 0.5                        # DBSCAN epsilon parameter
CLUSTER_MIN_SAMPLES = 2                  # Minimum cluster size
```

### Clustering Parameters

- **CLUSTER_EPS**: Distance threshold for clustering (lower = tighter clusters)
- **CLUSTER_MIN_SAMPLES**: Minimum files needed to form a cluster

---

## 🎬 Demo

### Demo Videos

> 📹 **Coming Soon!** - MVP demo video will be added here
**https://drive.google.com/file/d/1FAYYxMVeyy23qQOKIPdhyAQtLUjPj-hW/view?usp=sharing**

### Demo Screenshots

#### Graph Visualization
The main dashboard shows an interactive force-directed graph where each node represents a document and edges show semantic relationships. Files are automatically clustered by similarity.

<img width="1919" height="1029" alt="image" src="https://github.com/user-attachments/assets/2c8d6070-c88f-4ed8-9d2f-08d8b7f9361f" />


#### Semantic Search
Search your documents using natural language queries. The system finds semantically similar content across all your files.

<img width="1919" height="1029" alt="image" src="https://github.com/user-attachments/assets/d4f16de5-d9af-4a02-bbc5-cc43c9cf7d23" />


#### Document Viewer
Click on any node to view the file content directly in the interface, making it easy to browse through your organized documents.

<img width="1919" height="1029" alt="image" src="https://github.com/user-attachments/assets/8c38c180-51b6-4f6a-84cb-4eb43fb27580" />


#### File System Integration
SEFS automatically organizes your files into semantically meaningful folders based on content analysis.

<img width="1915" height="1020" alt="image" src="https://github.com/user-attachments/assets/384232d0-b723-4090-bf5e-299df3a5fe80" />

<img width="1919" height="1029" alt="image" src="https://github.com/user-attachments/assets/108e573a-d9d5-4497-8731-0b298fc7f2d4" />

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Sentence Transformers for powerful embedding models
- FastAPI for the excellent web framework
- React Force Graph for beautiful visualizations
- ChromaDB for efficient vector storage

---

## 📧 Contact

For questions or support, please open an issue on GitHub.

---

<p align="center">Made with ❤️ by the SEFS Team</p>


