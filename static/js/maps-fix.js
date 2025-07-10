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
        
        // Enhanced cleanup with delay to prevent race conditions
        this.clearMarkers();
        
        // Add small delay to ensure cleanup completes before creating new marker
        return new Promise((resolve) => {
            setTimeout(() => {
                try {
                    // Use modern AdvancedMarkerElement API with Map ID check
                    if (google.maps.marker && google.maps.marker.AdvancedMarkerElement && this.map.get('mapId')) {
                        console.log('SinglePinManager: Using AdvancedMarkerElement with Map ID:', this.map.get('mapId'));
                        
                        this.currentMarker = new google.maps.marker.AdvancedMarkerElement({
                            position: location,
                            map: this.map,
                            title: 'Selected Location',
                            gmpDraggable: true
                        });

                        // Enhanced drag end listener for AdvancedMarkerElement
                        if (onDragEnd && typeof onDragEnd === 'function') {
                            this.currentMarker.addListener('dragend', (event) => {
                                // For AdvancedMarkerElement, get position from marker.position
                                const position = this.currentMarker.position;
                                console.log('AdvancedMarkerElement dragend:', position.lat(), position.lng());
                                
                                // Create event object compatible with legacy API
                                const dragEvent = {
                                    latLng: position
                                };
                                onDragEnd(dragEvent);
                            });
                        }
                        
                        console.log('SinglePinManager: AdvancedMarkerElement created successfully');
                    } else {
                        throw new Error('AdvancedMarkerElement not available or no Map ID, using fallback');
                    }
                } catch (error) {
                    console.warn('SinglePinManager: AdvancedMarkerElement failed, using legacy Marker:', error.message);
                    
                    // Enhanced fallback to legacy API
                    this.currentMarker = new google.maps.Marker({
                        position: location,
                        map: this.map,
                        draggable: true,
                        title: 'Selected Location',
                        animation: google.maps.Animation.DROP,
                        optimized: false,
                        zIndex: 1000
                    });

                    // Add drag end listener for legacy marker
                    if (onDragEnd && typeof onDragEnd === 'function') {
                        this.currentMarker.addListener('dragend', onDragEnd);
                    }
                    
                    console.log('SinglePinManager: Legacy Marker created as fallback');
                }

                resolve(this.currentMarker);
            }, 50); // 50ms delay to ensure cleanup completion
        });
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