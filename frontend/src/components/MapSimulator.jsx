import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

const MapSimulator = () => {
  const [address, setAddress] = useState('');
  const [displayedAddress, setDisplayedAddress] = useState('');
  const navigate = useNavigate();

  const handleSearch = () => {
    if (address.trim()) {
      setDisplayedAddress(address);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50">
      <nav className="bg-white shadow-md">
        <div className="container mx-auto px-4 py-4">
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-2 text-primary-600 hover:text-primary-700 font-semibold transition-colors"
          >
            <span>←</span>
            <span>Back to Estate-Scout</span>
          </button>
        </div>
      </nav>

      <div className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-8">
            <h1 className="text-4xl font-bold text-gray-900 mb-2">
              🗺️ Map Simulator
            </h1>
            <p className="text-gray-600">
              Virtual map interface for property location verification
            </p>
          </div>

          <div className="card mb-6 p-6">
            <label htmlFor="address-input" className="block text-sm font-semibold text-gray-700 mb-2">
              Property Address
            </label>
            <div className="flex gap-3">
              <input
                id="address-input"
                type="text"
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Enter property address..."
                className="input-field"
              />
              <button
                id="search-button"
                onClick={handleSearch}
                className="btn-primary px-8 whitespace-nowrap"
              >
                🔍 Search
              </button>
            </div>
          </div>

          <div className="card overflow-hidden">
            <div className="bg-gradient-to-r from-primary-600 to-blue-600 text-white p-4">
              <h2 className="text-xl font-bold">Map View</h2>
            </div>
            
            <div 
              id="map-container"
              className="relative bg-gray-100 h-96 flex items-center justify-center"
            >
              {displayedAddress ? (
                <div className="text-center animate-fade-in">
                  <div className="text-6xl mb-4">📍</div>
                  <div className="bg-white rounded-xl shadow-lg p-6 max-w-md mx-4">
                    <h3 className="text-lg font-bold text-gray-900 mb-2">
                      Location Found
                    </h3>
                    <p className="text-gray-600 mb-4">
                      {displayedAddress}
                    </p>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div className="bg-blue-50 p-3 rounded-lg">
                        <p className="text-gray-600 mb-1">Distance</p>
                        <p className="font-bold text-blue-700">2.4 miles</p>
                      </div>
                      <div className="bg-green-50 p-3 rounded-lg">
                        <p className="text-gray-600 mb-1">Transit Score</p>
                        <p className="font-bold text-green-700">85/100</p>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center text-gray-400">
                  <div className="text-6xl mb-4">🗺️</div>
                  <p className="text-lg">Enter an address to view location</p>
                </div>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
            <div className="bg-white rounded-xl shadow-md p-4 text-center">
              <div className="text-3xl mb-2">🏢</div>
              <p className="text-sm font-semibold text-gray-700">Nearby Amenities</p>
              <p className="text-xs text-gray-500 mt-1">Schools, Shopping, Dining</p>
            </div>
            <div className="bg-white rounded-xl shadow-md p-4 text-center">
              <div className="text-3xl mb-2">🚇</div>
              <p className="text-sm font-semibold text-gray-700">Public Transit</p>
              <p className="text-xs text-gray-500 mt-1">Bus, Subway, Train</p>
            </div>
            <div className="bg-white rounded-xl shadow-md p-4 text-center">
              <div className="text-3xl mb-2">🌳</div>
              <p className="text-sm font-semibold text-gray-700">Parks & Recreation</p>
              <p className="text-xs text-gray-500 mt-1">Green Spaces Nearby</p>
            </div>
          </div>

          <div className="mt-6 bg-blue-50 border border-blue-200 rounded-xl p-4">
            <p className="text-sm text-blue-800">
              <span className="font-semibold">ℹ️ Note:</span> This is a simulated map interface for demonstration purposes. 
              In production, this would integrate with real mapping services like Google Maps or Mapbox.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MapSimulator;
