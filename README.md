# Semantic Entropy File System (SEFS)

An AI-powered, self-organizing file manager.

## Quick Start
Double-click `run_sefs.bat` to start both the backend and frontend.

## Manual Start

### Backend (Python)
1. Open a terminal.
2. Navigate to `backend`:
   ```sh
   cd F:\vibecode\backend
   ```
3. Run the server:
   ```sh
   python main.py
   ```
   The API will start at `http://localhost:8000`.

### Frontend (React)
1. Open a new terminal.
2. Navigate to `frontend`:
   ```sh
   cd F:\vibecode\frontend
   ```
3. Start the dev server:
   ```sh
   npm run dev
   ```
   Open `http://localhost:5173` in your browser.

## usage
1. The **Monitored Root** is `F:\vibecode\sefs_root`.
2. Drop PDF or Text files into this folder.
3. The system will automatically analyze, cluster, and move them into semantic folders (e.g., `Cluster_0`).
4. Watch the visualization update live on the web dashboard.
