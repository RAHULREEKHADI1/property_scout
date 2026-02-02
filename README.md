# 🏠 Estate-Scout - Autonomous Property Search Agent

Estate-Scout is an AI-powered autonomous agent that helps you find rental properties. It uses web search, browser automation, and AI to provide comprehensive property information with screenshots, lease drafts, and detailed dossiers.

## ✨ Features

- 🤖 **AI-Powered Search**: Natural language property search using GPT-4
- 🌐 **Web Search Integration**: Real-time property search using Tavily API
- 🖼️ **Property Screenshots**: Automated browser screenshots of property locations
- 📄 **Lease Drafts**: Auto-generated lease agreement templates
- 💾 **MongoDB Integration**: Persistent storage of properties and preferences
- 🎨 **Modern UI**: Beautiful React frontend with Tailwind CSS
- 📱 **Responsive Design**: Works on desktop, tablet, and mobile

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Node.js 16+
- MongoDB (local or Atlas)
- OpenAI API Key
- Tavily API Key

### Backend Setup

1. **Navigate to backend directory**
   ```bash
   cd backend
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Playwright browsers** (for screenshots)
   ```bash
   playwright install
   ```

5. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add your API keys:
   ```env
   OPENAI_API_KEY=sk-...
   TAVILY_API_KEY=tvly-...
   MONGODB_URI=mongodb://localhost:27017/
   MONGODB_DB=estate_scout
   ```

6. **Start the backend server**
   ```bash
   python app/main.py
   ```
   
   Backend will run on `http://localhost:8000`

### Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Start the development server**
   ```bash
   npm start
   ```
   
   Frontend will run on `http://localhost:3000`

## 🔑 API Keys Setup

### OpenAI API Key (REQUIRED)
1. Go to https://platform.openai.com/api-keys
2. Create a new API key
3. Add to `.env`: `OPENAI_API_KEY=sk-...`
4. Ensure you have credits in your OpenAI account

### Tavily API Key (REQUIRED)
1. Go to https://tavily.com
2. Sign up for a free account
3. Get your API key from dashboard
4. Add to `.env`: `TAVILY_API_KEY=tvly-...`

### MongoDB (REQUIRED)
**Option 1: Local MongoDB**
```bash
# Install MongoDB locally
# macOS: brew install mongodb-community
# Ubuntu: sudo apt-get install mongodb
# Windows: Download from mongodb.com

# Start MongoDB
mongod

# Set in .env:
MONGODB_URI=mongodb://localhost:27017/
```

**Option 2: MongoDB Atlas (Cloud)**
1. Go to https://www.mongodb.com/cloud/atlas
2. Create free cluster
3. Get connection string
4. Add to `.env`: `MONGODB_URI=mongodb+srv://...`

## 📖 Usage

1. **Start both servers** (backend on 8000, frontend on 3000)

2. **Open browser** to `http://localhost:3000`

3. **Chat with the agent** using natural language:
   ```
   "Find me a 2 bedroom apartment in Austin under $2000"
   "Show me pet-friendly studios in Brooklyn"
   "I need a 3BR house in San Francisco under $3500"
   ```

4. **View results** in the property grid with:
   - Property photos (screenshots)
   - Price, bedrooms, bathrooms
   - Location and description
   - Lease draft documents
   - Property information files

5. **Filter and search** using the search bar

6. **Load all properties** from database using "Show All DB" button

## 🏗️ Architecture

### Backend (FastAPI + LangGraph)
```
backend/
├── app/
│   └── main.py          # FastAPI server + API endpoints
├── graph/
│   ├── workflow.py      # LangGraph agent workflow
│   ├── nodes.py         # Agent nodes (Scout, Inspector, Broker, CRM)
│   └── state.py         # Agent state management
├── tools/
│   ├── search_tool.py   # Tavily web search
│   ├── browser_tool.py  # Playwright automation
│   ├── mongo_tool.py    # MongoDB operations
│   └── bash_tool.py     # File system operations
└── requirements.txt
```

### Frontend (React + Tailwind CSS)
```
frontend/
├── src/
│   ├── components/
│   │   ├── ChatInterface.js    # Chat UI
│   │   ├── PropertyGrid.js     # Property listings
│   │   └── MapSimulator.js     # Map interface
│   ├── App.js                  # Main app component
│   └── index.css               # Tailwind styles
├── package.json
└── tailwind.config.js
```

## 🤖 Agent Workflow

The Estate-Scout agent follows a 4-node workflow:

1. **Scout Node** 🔍
   - Extracts search criteria from user message
   - Uses Tavily API to search for properties
   - Returns raw property listings

2. **Inspector Node** 📸
   - Uses browser automation (Playwright)
   - Navigates to map simulator
   - Captures screenshots of property locations

3. **Broker Node** 📄
   - Creates property dossiers
   - Generates lease agreement drafts
   - Writes property information files

4. **CRM Node** 💾
   - Saves properties to MongoDB
   - Updates user preferences
   - Maintains search history

## 🎨 Key Improvements (v2.0)

### Frontend
✅ **Fully converted to Tailwind CSS** - No more separate CSS files
✅ **Modern component design** - Cards, gradients, animations
✅ **Better image handling** - Proper screenshot URLs from backend
✅ **Improved UX** - Loading states, animations, error handling
✅ **Responsive layout** - Works on all screen sizes

### Backend
✅ **No mock data** - Always uses real Tavily API
✅ **Proper API key validation** - Clear error messages
✅ **Image URL generation** - Converts screenshot paths to URLs
✅ **Better error handling** - Descriptive error messages
✅ **Health check endpoint** - Monitor API key configuration

## 🔧 Troubleshooting

### "Invalid OpenAI API key" error
- Check `.env` file has correct `OPENAI_API_KEY`
- Verify key starts with `sk-`
- Check OpenAI account has credits

### "Tavily API key not configured" error
- Check `.env` file has correct `TAVILY_API_KEY`
- Verify key starts with `tvly-`
- Sign up at https://tavily.com if needed

### "Cannot connect to MongoDB" error
- Ensure MongoDB is running (local or Atlas)
- Check `MONGODB_URI` in `.env` file
- For local: `mongod` should be running
- For Atlas: Check connection string and IP whitelist

### No images showing
- Backend server must be running on port 8000
- Check `data/listings/` folder exists
- Browser screenshots should be in property folders
- Check browser console for image loading errors

### Frontend not connecting to backend
- Backend must be running on `http://localhost:8000`
- Check CORS settings in `backend/app/main.py`
- Clear browser cache and restart frontend

## 📝 Environment Variables Reference

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `OPENAI_API_KEY` | ✅ Yes | OpenAI API key for GPT-4 | `sk-proj-...` |
| `TAVILY_API_KEY` | ✅ Yes | Tavily API key for web search | `tvly-...` |
| `MONGODB_URI` | ✅ Yes | MongoDB connection string | `mongodb://localhost:27017/` |
| `MONGODB_DB` | ⚠️ Optional | Database name | `estate_scout` (default) |
| `CLOUDINARY_*` | ⚠️ Optional | For image uploads | Not required |

## 🚀 Production Deployment

### Backend
1. Set environment variables on your server
2. Use production ASGI server: `gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app`
3. Set up MongoDB Atlas for production database
4. Configure proper CORS origins

### Frontend
1. Build production bundle: `npm run build`
2. Serve `build/` folder with nginx or serve
3. Update API endpoint to production backend URL
4. Configure environment variables for production

## 📄 License

MIT License - See LICENSE file for details

## 🤝 Contributing

Contributions welcome! Please read CONTRIBUTING.md first.

## 💬 Support

For issues or questions:
- Open an issue on GitHub
- Check existing issues for solutions
- Review troubleshooting section above

---

Built with ❤️ using React, Tailwind CSS, FastAPI, LangGraph, and AI
