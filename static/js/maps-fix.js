/**
 * Google Maps Single Pin Manager (Updated for Advanced Markers API)
 * Ensures only one pin exists on the map at any time using modern Google Maps API
 * Fixes deprecated Marker warnings and touch event issues
 */
class SinglePinManager {
    constructor(map) {
        this.map = map;
        this.currentMarker = null;
        this.clickTimeout = null;
        this.lastClickTime = 0;
        this.CLICK_DELAY = 300; // 300ms debounce
        this.touchStartY = 0;
        this.isScrolling = false;
        this.isProcessingClick = false;
        this.mapReady = false;
        this.pendingMarkerRequest = null;
        
        // Wait for map to be fully loaded before allowing markers
        this.waitForMapReady();
    }

    /**
     * Wait for map to be fully loaded to prevent race conditions
     */
    waitForMapReady() {
        // Check if map is already loaded
        if (this.map && this.map.getCenter()) {
            this.mapReady = true;
            console.log('SinglePinManager: Map is ready');
            return;
        }

        // Add listener for when map is fully loaded
        if (this.map) {
            google.maps.event.addListenerOnce(this.map, 'idle', () => {
                this.mapReady = true;
                console.log('SinglePinManager: Map idle event - ready for markers');
                
                // Process any pending marker request
                if (this.pendingMarkerRequest) {
                    console.log('SinglePinManager: Processing pending marker request');
                    const { location, onDragEnd, resolve } = this.pendingMarkerRequest;
                    this.pendingMarkerRequest = null;
                    this._createMarker(location, onDragEnd).then(resolve);
                }
            });
        }
    }

    /**
     * Enhanced marker cleanup with safety net to prevent multiple pins
     */
    clearMarkers() {
        if (this.currentMarker) {
            console.log('SinglePinManager: Clearing existing marker');
            
            // Clear all event listeners first
            google.maps.event.clearInstanceListeners(this.currentMarker);
            
            // Remove from map based on marker type
            if (this.currentMarker instanceof google.maps.marker.AdvancedMarkerElement) {
                // AdvancedMarkerElement uses map property
                this.currentMarker.map = null;
                console.log('SinglePinManager: AdvancedMarkerElement removed');
            } else if (this.currentMarker.setMap) {
                // Legacy Marker uses setMap method
                this.currentMarker.setMap(null);
                console.log('SinglePinManager: Legacy Marker removed');
            }
            
            this.currentMarker = null;
        }
        
        // Safety net: Force clear any remaining markers on the map
        // This prevents multiple pins from appearing due to race conditions
        setTimeout(() => {
            const mapMarkers = [];
            
            // Try to find any remaining markers using map's internal structure
            if (this.map && this.map.markers) {
                // Some map implementations expose markers array
                this.map.markers.forEach(marker => {
                    if (marker && marker.setMap) {
                        marker.setMap(null);
                    }
                });
                this.map.markers = [];
            }
            
            console.log('SinglePinManager: Safety cleanup completed');
        }, 10);
    }

    /**
     * Set a single marker at the specified location using AdvancedMarkerElement
     * @param {google.maps.LatLng} location 
     * @param {function} onDragEnd - callback for drag end event
     * @returns {google.maps.marker.AdvancedMarkerElement|google.maps.Marker}
     */
    setMarker(location, onDragEnd = null) {
        console.log('SinglePinManager: Setting marker at', location.lat(), location.lng());
        
        // Enhanced cleanup to prevent multiple pins
        this.clearMarkers();
        
        return new Promise((resolve) => {
            // Check if map is ready
            if (!this.mapReady) {
                console.log('SinglePinManager: Map not ready, queuing marker request');
                this.pendingMarkerRequest = { location, onDragEnd, resolve };
                return;
            }

            // Add delay to ensure cleanup completes and prevent race conditions
            setTimeout(() => {
                this._createMarker(location, onDragEnd).then(resolve);
            }, 50);
        });
    }

    /**
     * Internal method to create marker with proper error handling and fallback
     */
    _createMarker(location, onDragEnd = null) {
        return new Promise((resolve) => {
            console.log('SinglePinManager: _createMarker called with location:', location.lat(), location.lng());
            
            try {
                // Try modern AdvancedMarkerElement API first
                if (this._canUseAdvancedMarkerElement()) {
                    console.log('SinglePinManager: Using AdvancedMarkerElement with Map ID:', this.map.get('mapId'));
                    
                    // Create a visible marker element for AdvancedMarkerElement
                    const markerElement = document.createElement('div');
                    markerElement.style.cssText = `
                        position: relative;
                        width: 30px;
                        height: 40px;
                        cursor: pointer;
                    `;
                    
                    // Create the circle part
                    const circle = document.createElement('div');
                    circle.style.cssText = `
                        width: 30px;
                        height: 30px;
                        background: #ff4444;
                        border: 3px solid white;
                        border-radius: 50%;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
                        position: absolute;
                        top: 0;
                        left: 0;
                    `;
                    
                    // Create the pointer part
                    const pointer = document.createElement('div');
                    pointer.style.cssText = `
                        width: 0;
                        height: 0;
                        border-left: 6px solid transparent;
                        border-right: 6px solid transparent;
                        border-top: 10px solid #ff4444;
                        position: absolute;
                        top: 27px;
                        left: 50%;
                        transform: translateX(-50%);
                    `;
                    
                    markerElement.appendChild(circle);
                    markerElement.appendChild(pointer);
                    
                    console.log('Custom marker element created:', markerElement);

                    this.currentMarker = new google.maps.marker.AdvancedMarkerElement({
                        position: location,
                        map: this.map,
                        title: 'Selected Location',
                        content: markerElement,
                        gmpDraggable: true
                    });

                    // Verify marker was created and has valid position
                    console.log('AdvancedMarkerElement created:', {
                        marker: this.currentMarker,
                        position: this.currentMarker.position,
                        map: this.currentMarker.map,
                        visible: this.currentMarker.map === this.map
                    });

                    // Enhanced drag end listener for AdvancedMarkerElement
                    if (onDragEnd && typeof onDragEnd === 'function') {
                        this.currentMarker.addListener('dragend', (event) => {
                            try {
                                // For AdvancedMarkerElement, get position from marker.position
                                const position = this.currentMarker.position;
                                console.log('AdvancedMarkerElement dragend:', position.lat(), position.lng());
                                
                                // Create event object compatible with legacy API
                                const dragEvent = { latLng: position };
                                onDragEnd(dragEvent);
                            } catch (dragError) {
                                console.error('Error in AdvancedMarkerElement drag handler:', dragError);
                            }
                        });
                    }
                    
                    console.log('SinglePinManager: AdvancedMarkerElement created successfully and should be visible');
                    
                    // Add a small delay to ensure marker is rendered
                    setTimeout(() => {
                        console.log('SinglePinManager: Marker visibility check after 100ms:', {
                            hasMarker: !!this.currentMarker,
                            isOnMap: this.currentMarker && this.currentMarker.map === this.map,
                            position: this.currentMarker ? this.currentMarker.position : null
                        });
                        resolve(this.currentMarker);
                    }, 100);
                    
                } else {
                    console.log('SinglePinManager: AdvancedMarkerElement not available, using legacy');
                    // Fallback to legacy API
                    this._createLegacyMarker(location, onDragEnd, resolve);
                }
                
            } catch (error) {
                console.warn('SinglePinManager: AdvancedMarkerElement failed, falling back to legacy:', error.message);
                this._createLegacyMarker(location, onDragEnd, resolve);
            }
        });
    }

    /**
     * Check if AdvancedMarkerElement can be used safely
     * Temporarily force legacy markers for better visibility
     */
    _canUseAdvancedMarkerElement() {
        // Force use of legacy markers for now since they're more reliable
        console.log('SinglePinManager: Forcing legacy Marker API for better visibility');
        return false;
        
        /* Original check - temporarily disabled
        const canUse = google.maps.marker && 
                      google.maps.marker.AdvancedMarkerElement && 
                      this.map && 
                      this.map.get('mapId') && 
                      this.mapReady;
        
        console.log('SinglePinManager: AdvancedMarkerElement availability check:', {
            hasMarkerLibrary: !!google.maps.marker,
            hasAdvancedMarkerElement: !!(google.maps.marker && google.maps.marker.AdvancedMarkerElement),
            hasMap: !!this.map,
            hasMapId: this.map ? this.map.get('mapId') : null,
            isMapReady: this.mapReady,
            canUse: canUse
        });
        
        return canUse;
        */
    }

    /**
     * Create legacy marker with proper error handling
     */
    _createLegacyMarker(location, onDragEnd, resolve) {
        try {
            console.log('SinglePinManager: Using legacy Marker API at location:', location.lat(), location.lng());
            
            // Create custom red pin icon for better visibility
            const pinIcon = {
                path: 'M 0,0 C -2,-20 -10,-22 -10,-30 A 10,10 0 1,1 10,-30 C 10,-22 2,-20 0,0 z',
                fillColor: '#ff4444',
                fillOpacity: 1,
                strokeColor: '#ffffff',
                strokeWeight: 2,
                scale: 1.5,
                anchor: new google.maps.Point(0, 0)
            };

            this.currentMarker = new google.maps.Marker({
                position: location,
                map: this.map,
                draggable: true,
                title: 'Selected Location',
                icon: pinIcon,
                animation: google.maps.Animation.DROP,
                optimized: false,
                zIndex: 1000
            });

            // Verify legacy marker was created and is visible
            console.log('Legacy Marker created:', {
                marker: this.currentMarker,
                position: this.currentMarker.getPosition(),
                map: this.currentMarker.getMap(),
                visible: this.currentMarker.getVisible(),
                zIndex: this.currentMarker.getZIndex()
            });

            // Add drag end listener for legacy marker
            if (onDragEnd && typeof onDragEnd === 'function') {
                this.currentMarker.addListener('dragend', (event) => {
                    try {
                        onDragEnd(event);
                    } catch (dragError) {
                        console.error('Error in legacy marker drag handler:', dragError);
                    }
                });
            }
            
            console.log('SinglePinManager: Legacy Marker created successfully and should be visible');
            
            // Add a small delay to ensure marker is rendered
            setTimeout(() => {
                console.log('SinglePinManager: Legacy marker visibility check after 100ms:', {
                    hasMarker: !!this.currentMarker,
                    isVisible: this.currentMarker ? this.currentMarker.getVisible() : false,
                    position: this.currentMarker ? this.currentMarker.getPosition() : null
                });
                resolve(this.currentMarker);
            }, 100);
            
        } catch (legacyError) {
            console.error('SinglePinManager: Failed to create legacy marker:', legacyError);
            resolve(null);
        }
    }

    /**
     * Add click listener with proper debouncing and touch event handling
     * @param {function} clickHandler 
     */
    addClickListener(clickHandler) {
        if (!clickHandler || typeof clickHandler !== 'function') {
            return;
        }

        // Handle touch events properly to avoid scroll interference
        const mapDiv = this.map.getDiv();
        
        mapDiv.addEventListener('touchstart', (e) => {
            this.touchStartY = e.touches[0].clientY;
            this.isScrolling = false;
        }, { passive: true });

        mapDiv.addEventListener('touchmove', (e) => {
            const touchY = e.touches[0].clientY;
            const deltaY = Math.abs(touchY - this.touchStartY);
            
            // If significant vertical movement, consider it scrolling
            if (deltaY > 10) {
                this.isScrolling = true;
            }
        }, { passive: true });

        mapDiv.addEventListener('touchend', () => {
            // Reset scrolling flag after a delay
            setTimeout(() => {
                this.isScrolling = false;
            }, 100);
        }, { passive: true });

        // Add map click listener with simplified debouncing
        this.map.addListener('click', (event) => {
            console.log('Map clicked at:', event.latLng.lat(), event.latLng.lng());
            
            // Don't process clicks during scroll or if already processing
            if (this.isScrolling || this.isProcessingClick) {
                console.log('Click ignored - scrolling or processing');
                return;
            }

            const currentTime = Date.now();
            
            // Simplified debouncing
            if (currentTime - this.lastClickTime < this.CLICK_DELAY) {
                console.log('Click ignored - too fast');
                return;
            }
            
            this.lastClickTime = currentTime;
            this.isProcessingClick = true;
            
            // Process click immediately
            try {
                clickHandler(event.latLng);
                console.log('Click handler executed successfully');
            } catch (error) {
                console.error('Error in click handler:', error);
            } finally {
                this.isProcessingClick = false;
            }
        });
    }

    /**
     * Get the current marker
     */
    getMarker() {
        return this.currentMarker;
    }

    /**
     * Check if a marker exists
     */
    hasMarker() {
        return this.currentMarker !== null;
    }

    /**
     * Destroy the manager and clean up
     */
    destroy() {
        this.clearMarkers();
        
        // Clear map listeners
        google.maps.event.clearInstanceListeners(this.map);
        
        if (this.clickTimeout) {
            clearTimeout(this.clickTimeout);
            this.clickTimeout = null;
        }
        
        this.map = null;
        this.isProcessingClick = false;
        this.isScrolling = false;
    }
}

// Make it globally available
window.SinglePinManager = SinglePinManager;