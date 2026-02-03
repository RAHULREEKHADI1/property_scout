import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import ChatInterface from './components/ChatInterface';
import PropertyGrid from './components/PropertyGrid';
import MapSimulator from './components/MapSimulator';

function App() {
  const [properties, setProperties] = useState([]);

  const handleNewProperties = (newProps) => {
    console.log('🆕 App: Received new properties, REPLACING old ones:', newProps.length);
    setProperties(newProps);
  };

  return (
    <Router>
      <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-purple-50 to-pink-50">
        <Routes>
          <Route path="/map-simulator" element={<MapSimulator />} />
          <Route path="/" element={
            <div className="container mx-auto px-4 py-8">
              <header className="text-center mb-10 animate-fade-in">
                <div className="inline-block bg-white rounded-2xl shadow-lg px-8 py-6 mb-4">
                  <h1 className="text-6xl font-extrabold bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 bg-clip-text text-transparent mb-3">
                    🏠 Estate-Scout
                  </h1>
                  <p className="text-gray-600 text-xl font-medium">Your AI-Powered Property Discovery Agent</p>
                  <div className="mt-4 flex items-center justify-center gap-4 text-sm text-gray-500">
                    <span className="flex items-center gap-1">
                      <svg className="w-4 h-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                      Real-time Search
                    </span>
                    <span className="flex items-center gap-1">
                      <svg className="w-4 h-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                      AI Verification
                    </span>
                    <span className="flex items-center gap-1">
                      <svg className="w-4 h-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                      Smart Matching
                    </span>
                  </div>
                </div>
              </header>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 max-w-7xl mx-auto">
                <div className="lg:col-span-1 animate-slide-up">
                  <ChatInterface onNewProperties={handleNewProperties} />
                </div>

                <div className="lg:col-span-1 animate-slide-up" style={{ animationDelay: '0.1s' }}>
                  <PropertyGrid properties={properties} />
                </div>
              </div>
            </div>
          } />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
