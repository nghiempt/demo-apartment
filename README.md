# Apartment Search API

Ứng dụng tìm kiếm căn hộ với FastAPI Backend và Streamlit Frontend.

## 🚀 Quick Start với Docker

### 1. Setup Environment
```bash
# Copy và chỉnh sửa file .env
cp .env.example .env
# Thêm OpenAI API key vào file .env
```

### 2. Chạy ứng dụng

#### CÁCH 1: Docker Scripts (Khuyến nghị cho Ubuntu)
```bash
# Cấp quyền thực thi
chmod +x start-docker.sh stop-docker.sh

# Start cả Backend + Frontend
./start-docker.sh

# Dừng khi cần
./stop-docker.sh
```

#### CÁCH 2: Docker Compose (Nếu có version mới)
```bash
# Build và start cả Backend + Frontend
docker-compose up --build

# Hoặc chạy ở background
docker-compose up -d --build

# Dừng ứng dụng
docker-compose down
```

### 3. Truy cập ứng dụng
- **Frontend UI**: http://localhost:8501
- **Backend API**: http://localhost:8000  
- **API Docs**: http://localhost:8000/docs

### 4. Dừng ứng dụng
```bash
docker-compose down
```

## 🛠️ Development

### Local development (không dùng Docker)
```bash
# Setup virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Run Backend
python main.py

# Run Frontend (terminal khác)
streamlit run chat_ui.py --server.port 8501
```

## 📁 Project Structure
```
apartment-scope-demo/
├── main.py              # FastAPI Backend
├── chat_ui.py           # Streamlit Frontend  
├── data/                # CSV data files
├── images/              # Image files
├── Dockerfile           # Docker configuration
├── docker-compose.yml   # Multi-container setup
├── requirements.txt     # Python dependencies
└── .env                 # Environment variables
```