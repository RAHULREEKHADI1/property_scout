#!/bin/bash

# Estate-Scout Setup Script
# This script helps you set up the Estate-Scout application

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║          🏠 Estate-Scout Setup Script v2.0                ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "ℹ️  $1"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

echo "Checking prerequisites..."
echo ""

# Check Python
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version)
    print_success "Python found: $PYTHON_VERSION"
else
    print_error "Python 3 not found. Please install Python 3.8 or higher."
    exit 1
fi

# Check Node.js
if command_exists node; then
    NODE_VERSION=$(node --version)
    print_success "Node.js found: $NODE_VERSION"
else
    print_error "Node.js not found. Please install Node.js 16 or higher."
    exit 1
fi

# Check npm
if command_exists npm; then
    NPM_VERSION=$(npm --version)
    print_success "npm found: v$NPM_VERSION"
else
    print_error "npm not found. Please install npm."
    exit 1
fi

# Check MongoDB
if command_exists mongod; then
    print_success "MongoDB found"
else
    print_warning "MongoDB not found locally. You'll need MongoDB Atlas or install MongoDB."
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "Backend Setup"
echo "═══════════════════════════════════════════════════════════"
echo ""

cd backend

# Create virtual environment
if [ ! -d "venv" ]; then
    print_info "Creating Python virtual environment..."
    python3 -m venv venv
    print_success "Virtual environment created"
else
    print_info "Virtual environment already exists"
fi

# Activate virtual environment
print_info "Activating virtual environment..."
source venv/bin/activate

# Install Python dependencies
print_info "Installing Python dependencies..."
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1
print_success "Python dependencies installed"

# Install Playwright browsers
print_info "Installing Playwright browsers (this may take a moment)..."
playwright install > /dev/null 2>&1
print_success "Playwright browsers installed"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    print_info "Creating .env file from template..."
    cp .env.example .env
    print_warning ".env file created. You MUST add your API keys!"
    echo ""
    echo "Edit backend/.env and add:"
    echo "  - OPENAI_API_KEY (get from https://platform.openai.com/api-keys)"
    echo "  - TAVILY_API_KEY (get from https://tavily.com)"
    echo "  - MONGODB_URI (local: mongodb://localhost:27017/ or Atlas connection string)"
    echo ""
else
    print_info ".env file already exists"
fi

cd ..

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "Frontend Setup"
echo "═══════════════════════════════════════════════════════════"
echo ""

cd frontend

# Install Node dependencies
print_info "Installing Node.js dependencies (this may take a minute)..."
npm install > /dev/null 2>&1
print_success "Node.js dependencies installed"

cd ..

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "Setup Complete! 🎉"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Check if API keys are configured
if [ -f "backend/.env" ]; then
    if grep -q "your_openai_api_key_here" backend/.env; then
        print_warning "OpenAI API key not configured yet!"
    else
        print_success "OpenAI API key configured"
    fi
    
    if grep -q "your_tavily_api_key_here" backend/.env; then
        print_warning "Tavily API key not configured yet!"
    else
        print_success "Tavily API key configured"
    fi
fi

echo ""
echo "Next steps:"
echo ""
echo "1. Configure API keys in backend/.env:"
echo "   nano backend/.env"
echo ""
echo "2. Start MongoDB (if using local):"
echo "   mongod"
echo ""
echo "3. Start the backend (in one terminal):"
echo "   cd backend"
echo "   source venv/bin/activate"
echo "   python app/main.py"
echo ""
echo "4. Start the frontend (in another terminal):"
echo "   cd frontend"
echo "   npm start"
echo ""
echo "5. Open your browser to:"
echo "   http://localhost:3000"
echo ""
echo "═══════════════════════════════════════════════════════════"
echo ""

print_info "For more information, see README.md"
print_info "For migration help, see MIGRATION.md"

echo ""
