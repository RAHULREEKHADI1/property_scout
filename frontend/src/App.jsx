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
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 relative overflow-hidden">
        {/* Animated background elements */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-0 left-1/4 w-96 h-96 bg-purple-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob"></div>
          <div className="absolute top-0 right-1/4 w-96 h-96 bg-cyan-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob animation-delay-2000"></div>
          <div className="absolute bottom-0 left-1/3 w-96 h-96 bg-pink-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob animation-delay-4000"></div>
        </div>

        <Routes>
          <Route path="/map-simulator" element={<MapSimulator />} />
          <Route path="/" element={
            <div className="container mx-auto px-4 py-8 relative z-10">
              <header className="text-center mb-10 animate-fade-in">
                <div className="inline-block bg-gradient-to-br from-slate-800/90 to-slate-900/90 backdrop-blur-xl rounded-3xl shadow-2xl px-8 py-6 mb-4 border border-purple-500/20">
                  <div className="flex items-center justify-center gap-4 mb-2">
                    <div className="w-16 h-16 bg-gradient-to-br from-purple-600 to-cyan-600 rounded-2xl flex items-center justify-center shadow-lg shadow-purple-500/50">
                      <span className="text-4xl">🏠</span>
                    </div>
                    <h1 className="text-6xl font-extrabold bg-gradient-to-r from-purple-400 via-cyan-400 to-pink-400 bg-clip-text text-transparent">
                      Estate-Scout
                    </h1>
                  </div>
                  <p className="text-gray-300 text-xl font-medium mb-4">Your AI-Powered Property Discovery Agent</p>
                  <div className="mt-4 flex items-center justify-center gap-4 text-sm text-gray-400">
                    <span className="flex items-center gap-2 px-3 py-1.5 bg-purple-500/10 rounded-full border border-purple-500/20">
                      <svg className="w-4 h-4 text-purple-400" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                      Real-time Search
                    </span>
                    <span className="flex items-center gap-2 px-3 py-1.5 bg-cyan-500/10 rounded-full border border-cyan-500/20">
                      <svg className="w-4 h-4 text-cyan-400" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                      AI Verification
                    </span>
                    <span className="flex items-center gap-2 px-3 py-1.5 bg-pink-500/10 rounded-full border border-pink-500/20">
                      <svg className="w-4 h-4 text-pink-400" fill="currentColor" viewBox="0 0 20 20">
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