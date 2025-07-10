/**
 * Google Maps Single Pin Manager
 * Ensures only one pin exists on the map at any time
 */
class SinglePinManager {
    constructor(map) {
        this.map = map;
        this.marker = null;
        this.isProcessingClick = false;
        this.clickTimeout = null;
    }

    /**
     * Clear all existing markers from the map
     */
    clearMarkers() {
        if (this.marker) {
            // Clear all event listeners
            google.maps.event.clearInstanceListeners(this.marker);
            // Remove from map
            this.marker.setMap(null);
            this.marker = null;
        }
    }

    /**
     * Set a single marker at the specified location
     * @param {google.maps.LatLng} location 
     * @param {function} onDragEnd - callback for drag end event
     * @returns {google.maps.Marker}
     */
    setMarker(location, onDragEnd = null) {
        // Clear existing marker first
        this.clearMarkers();

        // Create new marker
        this.marker = new google.maps.Marker({
            position: location,
            map: this.map,
            draggable: true,
            animation: google.maps.Animation.DROP,
            title: 'Selected Location',
            optimized: false,
            zIndex: 1000
        });

        // Add drag event listener if provided
        if (onDragEnd) {
            this.marker.addListener('dragend', onDragEnd);
        }

        return this.marker;
    }

    /**
     * Add click listener with proper debouncing
     * @param {function} clickHandler 
     */
    addClickListener(clickHandler) {
        this.map.addListener('click', (event) => {
            // Prevent multiple simultaneous clicks
            if (this.isProcessingClick) {
                return;
            }

            this.isProcessingClick = true;

            // Clear any pending timeouts
            if (this.clickTimeout) {
                clearTimeout(this.clickTimeout);
            }

            this.clickTimeout = setTimeout(() => {
                clickHandler(event.latLng);
                this.isProcessingClick = false;
            }, 200); // Increased timeout for better debouncing
        });
    }

    /**
     * Get the current marker
     */
    getMarker() {
        return this.marker;
    }

    /**
     * Check if a marker exists
     */
    hasMarker() {
        return this.marker !== null;
    }

    /**
     * Destroy the manager and clean up
     */
    destroy() {
        this.clearMarkers();
        google.maps.event.clearInstanceListeners(this.map);
        if (this.clickTimeout) {
            clearTimeout(this.clickTimeout);
        }
    }
}

// Make it globally available
window.SinglePinManager = SinglePinManager;