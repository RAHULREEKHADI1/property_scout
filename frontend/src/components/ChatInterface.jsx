import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';

const ChatInterface = ({ onNewProperties }) => {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: '👋 Hello! I\'m your Estate-Scout AI agent. Tell me what kind of property you\'re looking for, and I\'ll search, verify, and organize everything for you!' }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };
  const API_URL = process.env.REACT_APP_API_URL;

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage = inputMessage.trim();
    setInputMessage('');
    
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setIsLoading(true);

    try {
      const response = await axios.post(`${API_URL}/api/chat`, {
        message: userMessage
      });

      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: response.data.response 
      }]);

      if (response.data.properties && response.data.properties.length > 0) {
        onNewProperties(response.data.properties);
      }
    } catch (error) {
      console.error('Chat error:', error);
      let errorMessage = ' Sorry, I encountered an error. ';
      
      if (error.response?.data?.detail) {
        errorMessage += error.response.data.detail;
      } else if (error.message.includes('Network Error')) {
        errorMessage += 'Cannot connect to the backend server. Make sure it\'s running on port 8000.';
      } else {
        errorMessage += 'Please try again.';
      }
      
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: errorMessage 
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const quickActions = [
    '2 bed apartment in Austin under $2000',
    '3 bed pet-friendly house in Brooklyn',
    'Studio in San Francisco under $2500'
  ];

  const handleQuickAction = (action) => {
    setInputMessage(action);
  };

  return (
    <div className="card h-[600px] flex flex-col shadow-xl">
      <div className="bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 text-white p-5 rounded-t-xl">
        <h2 className="text-2xl font-bold flex items-center gap-3 mb-2">
          <span className="text-3xl">🤖</span>
          <div>
            <div>Chat with AI Agent</div>
            <div className="text-sm font-normal opacity-90 mt-0.5">
              {isLoading ? 'Searching properties...' : 'Ready to help'}
            </div>
          </div>
        </h2>
      </div>

      <div className="flex-1 overflow-y-auto p-5 space-y-4 bg-gradient-to-br from-gray-50 to-white">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-fade-in`}
          >
            <div
              className={`max-w-[85%] rounded-2xl px-5 py-3 shadow-md ${
                msg.role === 'user'
                  ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white'
                  : 'bg-white text-gray-800 border-2 border-gray-100'
              }`}
            >
              {msg.role === 'assistant' && (
                <div className="flex items-center gap-2 mb-2 text-indigo-600 font-semibold">
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  <span className="text-xs">AI Agent</span>
                </div>
              )}
              <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
            </div>
          </div>
        ))}
        
        {isLoading && (
          <div className="flex justify-start animate-fade-in">
            <div className="bg-white text-gray-800 rounded-2xl px-5 py-4 shadow-md border-2 border-indigo-100">
              <div className="flex items-center gap-3">
                <div className="flex gap-1">
                  <div className="w-2.5 h-2.5 bg-indigo-600 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                  <div className="w-2.5 h-2.5 bg-purple-600 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                  <div className="w-2.5 h-2.5 bg-pink-600 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                </div>
                <span className="text-sm text-gray-700 font-medium">AI agent is working...</span>
              </div>
            </div>
          </div>
        )}
        
        {messages.length === 1 && !isLoading && (
          <div className="animate-fade-in">
            <p className="text-sm text-gray-600 mb-3 font-semibold">💡 Try these searches:</p>
            <div className="space-y-2">
              {quickActions.map((action, idx) => (
                <button
                  key={idx}
                  onClick={() => handleQuickAction(action)}
                  className="w-full text-left bg-white hover:bg-indigo-50 border-2 border-gray-200 hover:border-indigo-300 rounded-xl px-4 py-3 text-sm text-gray-700 transition-all duration-200 shadow-sm hover:shadow-md"
                >
                  <span className="mr-2">🔍</span>
                  {action}
                </button>
              ))}
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      <div className="p-4 bg-white border-t-2 border-gray-100 rounded-b-xl">
        <div className="flex gap-3">
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Describe your ideal property..."
            className="flex-1 px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 focus:outline-none transition-all duration-200 text-sm"
            disabled={isLoading}
          />
          <button
            onClick={handleSend}
            disabled={isLoading || !inputMessage.trim()}
            className={`px-6 py-3 rounded-xl font-semibold transition-all duration-200 flex items-center gap-2 ${
              isLoading || !inputMessage.trim()
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white shadow-lg hover:shadow-xl'
            }`}
          >
            {isLoading ? (
              <>
                <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span className="hidden sm:inline">Searching...</span>
              </>
            ) : (
              <>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
                <span className="hidden sm:inline">Send</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;
