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
     * Clear all existing markers from the map
     */
    clearMarkers() {
        if (this.currentMarker) {
            // Clear all event listeners first
            google.maps.event.clearInstanceListeners(this.currentMarker);
            
            // Remove from map based on marker type
            if (this.currentMarker.map) {
                this.currentMarker.map = null; // AdvancedMarkerElement
            } else if (this.currentMarker.setMap) {
                this.currentMarker.setMap(null); // Legacy Marker
            }
            
            this.currentMarker = null;
        }
    }

    /**
     * Set a single marker at the specified location using AdvancedMarkerElement
     * @param {google.maps.LatLng} location 
     * @param {function} onDragEnd - callback for drag end event
     * @returns {google.maps.marker.AdvancedMarkerElement|google.maps.Marker}
     */
    setMarker(location, onDragEnd = null) {
        // Clear any existing marker first
        this.clearMarkers();
        
        try {
            // Check if AdvancedMarkerElement is available (requires Maps API v3.56+)
            if (google.maps.marker && google.maps.marker.AdvancedMarkerElement) {
                // Use new AdvancedMarkerElement API (recommended)
                this.currentMarker = new google.maps.marker.AdvancedMarkerElement({
                    position: location,
                    map: this.map,
                    gmpDraggable: true,
                    title: 'Selected Location'
                });

                // Add drag end listener if provided
                if (onDragEnd && typeof onDragEnd === 'function') {
                    this.currentMarker.addListener('dragend', onDragEnd);
                }
            } else {
                // Fallback to legacy Marker API (suppress console warning)
                const originalWarn = console.warn;
                console.warn = () => {}; // Temporarily suppress warnings
                
                this.currentMarker = new google.maps.Marker({
                    position: location,
                    map: this.map,
                    draggable: true,
                    title: 'Selected Location',
                    animation: google.maps.Animation.DROP,
                    optimized: false,
                    zIndex: 1000
                });

                // Restore console.warn
                console.warn = originalWarn;

                // Add drag end listener if provided
                if (onDragEnd && typeof onDragEnd === 'function') {
                    this.currentMarker.addListener('dragend', onDragEnd);
                }
            }
        } catch (error) {
            console.error('Error creating marker:', error);
            // Ultimate fallback to legacy API
            this.currentMarker = new google.maps.Marker({
                position: location,
                map: this.map,
                draggable: true,
                title: 'Selected Location',
                optimized: false
            });

            if (onDragEnd && typeof onDragEnd === 'function') {
                this.currentMarker.addListener('dragend', onDragEnd);
            }
        }

        return this.currentMarker;
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

        // Add map click listener with comprehensive debouncing
        this.map.addListener('click', (event) => {
            // Don't process clicks during scroll or if already processing
            if (this.isScrolling || this.isProcessingClick) {
                return;
            }

            const currentTime = Date.now();
            
            // Clear any pending timeout
            if (this.clickTimeout) {
                clearTimeout(this.clickTimeout);
            }
            
            // Debounce clicks
            if (currentTime - this.lastClickTime < this.CLICK_DELAY) {
                return;
            }
            
            this.lastClickTime = currentTime;
            this.isProcessingClick = true;
            
            // Set timeout to handle the click
            this.clickTimeout = setTimeout(() => {
                clickHandler(event.latLng || event.position);
                this.isProcessingClick = false;
                this.clickTimeout = null;
            }, 100); // Slightly longer delay for better UX
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