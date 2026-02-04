import React, { useEffect, useState } from 'react';
import axios from 'axios';

const PropertyGrid = ({ properties }) => {
  const [displayedProperties, setDisplayedProperties] = useState([]);
  const [allProperties, setAllProperties] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [showNewOnly, setShowNewOnly] = useState(true);
  const [viewMode, setViewMode] = useState('grid');

  const API_URL = process.env.REACT_APP_API_URL;

  useEffect(() => {
    if (properties && properties.length > 0) {
      console.log('🎯 NEW SEARCH RESULTS - Showing ONLY these:', properties);
      setAllProperties(properties);
      setDisplayedProperties(properties);
      setShowNewOnly(true);
      setSearchQuery('');
    }
  }, [properties]);

  useEffect(() => {
    if (searchQuery.trim() === '') {
      setDisplayedProperties(allProperties);
    } else {
      const query = searchQuery.toLowerCase();
      const filtered = allProperties.filter(property => {
        const symbol = property.currency_symbol || '$';
        const displayedPrice = symbol + property.price.toLocaleString() + '/mo';

        return (
          (property.title && property.title.toLowerCase().includes(query)) ||
          (property.address && property.address.toLowerCase().includes(query)) ||
          (property.description && property.description.toLowerCase().includes(query)) ||
          (property.bedrooms && property.bedrooms.toString().includes(query)) ||
          (property.price && property.price.toString().includes(query)) ||
          (property.currency_symbol && property.currency_symbol.includes(query)) ||
          (property.currency_code && property.currency_code.toLowerCase().includes(query)) ||
          displayedPrice.toLowerCase().includes(query)
        );
      });
      setDisplayedProperties(filtered);
    }
  }, [searchQuery, allProperties]);

  const fetchAllFromDB = async () => {
    try {
      console.log('🔄 Loading ALL properties from database...');
      const response = await axios.get(`${API_URL}/api/listings`);
      if (response.data.listings && response.data.listings.length > 0) {
        setAllProperties(response.data.listings);
        setDisplayedProperties(response.data.listings);
        setShowNewOnly(false);
        setSearchQuery('');
      }
    } catch (error) {
      console.error('⚠️ Error fetching listings:', error);
    }
  };

  const getImageUrl = (property) => {
    if (property.cloudinary_url) {
      return property.cloudinary_url;
    }
    
    if (property.image_url) {
      return property.image_url;
    }
    
    if (property.screenshot_path) {
      return `${API_URL}/${property.screenshot_path}`;
    }
    
    return null; 
  };

  const handleClearSearch = () => {
    setSearchQuery('');
  };

  const PropertyCard = ({ property, idx }) => {
    const imageUrl = getImageUrl(property);
    
    return (
      <div
        className={`bg-gradient-to-br from-slate-800/90 to-slate-900/90 backdrop-blur-xl rounded-2xl shadow-2xl overflow-hidden hover:shadow-purple-500/20 transition-all duration-300 border border-purple-500/20 ${
          viewMode === 'grid' ? '' : 'flex'
        }`}
        style={{ 
          animationDelay: `${idx * 50}ms`,
          animation: 'fadeIn 0.5s ease-out forwards'
        }}
      >
        <div className="p-4 pb-0 flex justify-between items-start gap-2">
          {property.pet_friendly && (
            <div className="bg-gradient-to-r from-emerald-500 to-teal-600 text-white px-3 py-1.5 rounded-full font-semibold text-sm shadow-lg flex items-center gap-1.5 flex-shrink-0">
              <span>🐾</span>
              <span>Pet Friendly</span>
            </div>
          )}
          
          <div className="bg-gradient-to-r from-purple-600 to-cyan-600 text-white px-4 py-1.5 rounded-full font-bold text-lg shadow-lg flex-shrink-0 ml-auto">
            {property.currency_symbol}{property.price.toLocaleString()}/mo
          </div>
        </div>

        <div className={`relative overflow-hidden ${viewMode === 'grid' ? 'h-56' : 'w-64 h-full'} mt-2`}>
          {imageUrl ? (
            <img
              src={imageUrl}
              alt={property.title}
              className="w-full h-full object-cover transition-transform duration-300 hover:scale-110"
              onError={(e) => {
                e.target.style.display = 'none';
                e.target.nextSibling.style.display = 'flex';
              }}
            />
          ) : null}
          <div 
            className="w-full h-full bg-gradient-to-br from-purple-600 via-cyan-600 to-pink-600 flex items-center justify-center"
            style={{ display: imageUrl ? 'none' : 'flex' }}
          >
            <div className="text-center text-white">
              <div className="text-6xl mb-2">🏠</div>
              <p className="text-sm font-medium opacity-90">Property Image</p>
            </div>
          </div>
        </div>

        <div className={`p-6 ${viewMode === 'list' ? 'flex-1' : ''}`}>
          <h3 className="text-xl font-bold text-gray-100 mb-2 line-clamp-2 hover:text-purple-400 transition-colors">
            {property.title}
          </h3>
          
          <div className="flex items-center gap-2 text-gray-400 mb-4">
            <svg className="w-5 h-5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            <span className="line-clamp-1 text-sm font-medium">{property.address}</span>
          </div>

          <div className="flex items-center gap-6 mb-4">
            <div className="flex items-center gap-2 text-gray-300 bg-slate-700/50 px-3 py-2 rounded-lg border border-purple-500/20">
              <svg className="w-5 h-5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
              </svg>
              <span className="font-semibold">{property.bedrooms} BD</span>
            </div>
            <div className="flex items-center gap-2 text-gray-300 bg-slate-700/50 px-3 py-2 rounded-lg border border-cyan-500/20">
              <svg className="w-5 h-5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 14v3m4-3v3m4-3v3M3 21h18M3 10h18M3 7l9-4 9 4M4 10h16v11H4V10z" />
              </svg>
              <span className="font-semibold">{property.bathrooms} BA</span>
            </div>
          </div>

          <p className="text-gray-400 text-sm line-clamp-3 mb-4 leading-relaxed">
            {property.description}
          </p>

          {property.folder_path && (
            <div className="flex gap-2 pt-4 border-t border-purple-500/20">
              <a
                href={`${API_URL}/${property.folder_path}/lease_draft.txt`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1 text-center bg-gradient-to-r from-purple-600/20 to-cyan-600/20 hover:from-purple-600/30 hover:to-cyan-600/30 text-purple-300 py-2.5 px-4 rounded-xl font-semibold text-sm transition-all duration-200 flex items-center justify-center gap-2 border border-purple-500/20"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Lease Draft
              </a>
              <a
                href={`${API_URL}/${property.folder_path}/info.txt`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1 text-center bg-gradient-to-r from-slate-700/50 to-slate-800/50 hover:from-slate-600/50 hover:to-slate-700/50 text-gray-300 py-2.5 px-4 rounded-xl font-semibold text-sm transition-all duration-200 flex items-center justify-center gap-2 border border-slate-600/20"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Details
              </a>
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="bg-gradient-to-br from-slate-800/90 to-slate-900/90 backdrop-blur-xl rounded-2xl shadow-2xl min-h-[600px] flex flex-col border border-purple-500/20">
      <div className="flex-shrink-0 bg-gradient-to-r from-purple-600 via-cyan-600 to-pink-600 text-white p-5 rounded-t-2xl">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold flex items-center gap-3">
            <div className="w-10 h-10 bg-white/20 rounded-xl flex items-center justify-center backdrop-blur-sm">
              <span className="text-2xl">{showNewOnly ? '🎯' : '📋'}</span>
            </div>
            <div>
              <div>{showNewOnly ? 'Search Results' : 'All Properties'}</div>
              <div className="text-sm font-normal opacity-90 mt-0.5">
                {displayedProperties.length} {displayedProperties.length === 1 ? 'property' : 'properties'} found
              </div>
            </div>
          </h2>
          
          <div className="flex items-center gap-3">
            <div className="bg-white/20 backdrop-blur-sm rounded-lg p-1 flex gap-1">
              <button
                onClick={() => setViewMode('grid')}
                className={`px-3 py-2 rounded-md font-semibold text-sm transition-all duration-200 ${
                  viewMode === 'grid' 
                    ? 'bg-white text-purple-600 shadow-lg' 
                    : 'text-white hover:bg-white/20'
                }`}
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
                </svg>
              </button>
              <button
                onClick={() => setViewMode('list')}
                className={`px-3 py-2 rounded-md font-semibold text-sm transition-all duration-200 ${
                  viewMode === 'list' 
                    ? 'bg-white text-purple-600 shadow-lg' 
                    : 'text-white hover:bg-white/20'
                }`}
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              </button>
            </div>
            
            <button
              onClick={fetchAllFromDB}
              className="bg-white/20 hover:bg-white/30 text-white px-5 py-2.5 rounded-lg font-semibold transition-all duration-200 flex items-center gap-2 backdrop-blur-sm shadow-lg"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
              </svg>
              <span>All Saved</span>
            </button>
          </div>
        </div>

        <div className="relative">
          <svg className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            placeholder="Filter by location, price, bedrooms..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-12 pr-12 py-3 rounded-xl bg-white/90 backdrop-blur-sm text-gray-800 placeholder-gray-500 focus:ring-2 focus:ring-white focus:outline-none shadow-lg"
          />
          {searchQuery && (
            <button
              onClick={handleClearSearch}
              className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700 font-bold"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 bg-gradient-to-br from-slate-900/50 to-slate-800/50">
        {displayedProperties.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center py-12">
            {searchQuery ? (
              <>
                <div className="text-7xl mb-4">🔍</div>
                <p className="text-gray-300 text-xl mb-4 font-semibold">
                  No properties match "{searchQuery}"
                </p>
                <button
                  onClick={handleClearSearch}
                  className="bg-gradient-to-r from-purple-600 to-cyan-600 text-white px-6 py-3 rounded-xl font-semibold hover:shadow-lg hover:shadow-purple-500/50 transition-all duration-200"
                >
                  Clear Filter
                </button>
              </>
            ) : (
              <>
                <div className="text-8xl mb-4 animate-bounce">🏠</div>
                <p className="text-gray-300 text-xl mb-2 font-semibold">No properties yet</p>
                <p className="text-gray-500 text-lg">Start chatting to discover amazing properties!</p>
              </>
            )}
          </div>
        ) : (
          <div className={viewMode === 'grid' ? 'grid grid-cols-1 gap-6' : 'flex flex-col gap-6'}>
            {displayedProperties.map((property, idx) => (
              <PropertyCard 
                key={`prop-${idx}-${property.id || property.address}`} 
                property={property} 
                idx={idx} 
              />
            ))}
          </div>
        )}
      </div>
      
      <style jsx>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </div>
  );
};

export default PropertyGrid;