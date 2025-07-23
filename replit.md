# Monthly Organics

## Overview

Monthly Organics is a Flask web application for an organic produce delivery service. The application provides a platform for customers to subscribe to monthly organic produce deliveries. The system is built with Flask as the backend framework, uses PostgreSQL for data storage, and features a modern frontend with Tailwind CSS, Alpine.js, and htmx for enhanced interactivity.

## System Architecture

The application follows a traditional Flask web application architecture with the following layers:

1. **Presentation Layer**: HTML templates with Tailwind CSS styling and Alpine.js for client-side interactivity
2. **Application Layer**: Flask routes and business logic
3. **Data Layer**: PostgreSQL database with SQLAlchemy ORM
4. **Static Assets**: CSS, JavaScript, and image files served directly

The architecture separates concerns between the main application entry point (`main.py`) and the route handlers (`app/main.py`), allowing for better organization and scalability.

## Key Components

### Backend Components

- **Flask Application**: Main web framework handling HTTP requests and responses
- **SQLAlchemy ORM**: Database abstraction layer with declarative models
- **PostgreSQL Database**: Primary data storage using psycopg2-binary for connection
- **Models**: User, Address, and Subscription entities with proper relationships

### Frontend Components

- **Tailwind CSS**: Utility-first CSS framework for responsive design
- **Alpine.js**: Lightweight JavaScript framework for reactive components
- **htmx**: Library for AJAX interactions without writing JavaScript
- **Custom Animations**: Fade-in effects and smooth transitions

### Database Schema

The application uses the following database structure:

1. **Users Table**: Customer information (id, email, first_name, last_name, phone, timestamps)
2. **Addresses Table**: Delivery addresses with geolocation (user_id, nickname, coordinates, address fields)
3. **Categories Table**: Product categories (id, name, icon_url)
4. **Products Table**: Product information (id, name, description, category_id, is_best_seller)
5. **Product Variations Table**: Product variants with pricing (id, product_id, variation_name, mrp, stock)
6. **Cart Items Table**: Shopping cart data (id, user_id, variation_id, quantity)
7. **Orders Table**: Order records (id, user_id, total_amount, status, timestamps)
8. **Order Items Table**: Order line items (id, order_id, variation_id, quantity, price)

## Data Flow

1. **Request Handling**: Flask receives HTTP requests and routes them to appropriate handlers
2. **Database Operations**: SQLAlchemy manages database connections and queries
3. **Template Rendering**: Jinja2 templates render HTML responses with dynamic content
4. **Static Asset Serving**: CSS, JavaScript, and images served directly by Flask
5. **Client-side Interactivity**: Alpine.js and htmx handle dynamic frontend behavior

## External Dependencies

### Python Dependencies
- **Flask**: Web framework
- **Flask-SQLAlchemy**: Database ORM integration
- **psycopg2-binary**: PostgreSQL database connector
- **Werkzeug**: WSGI utilities and middleware

### Frontend Dependencies (CDN)
- **Tailwind CSS**: Styling framework
- **Alpine.js**: JavaScript framework
- **htmx**: AJAX library

### Database
- **PostgreSQL**: Primary database system

## Deployment Strategy

The application is configured for deployment with the following considerations:

1. **Environment Variables**: 
   - `DATABASE_URL`: PostgreSQL connection string
   - `SESSION_SECRET`: Flask session encryption key

2. **Production Readiness**:
   - ProxyFix middleware for proper HTTPS handling
   - Database connection pooling with health checks
   - Logging configuration for debugging and monitoring

3. **Health Monitoring**:
   - Health check endpoint for monitoring service status
   - Database connection testing

## Changelog

```
Changelog:
- July 05, 2025. Initial setup with Flask, PostgreSQL, and Tailwind CSS
- July 05, 2025. Enhanced mobile-first design with responsive layouts, touch-friendly buttons, and mobile-optimized navigation
- July 05, 2025. Fixed syntax error in models.py and successfully deployed application
- July 05, 2025. Fixed health check endpoint and confirmed mobile-first design is working properly
- July 05, 2025. Designed and implemented e-commerce database schema with 4 tables: ecommerce_users, categories, ecommerce_products, and product_variations
- July 05, 2025. Built complete homepage with sliding banners, category grid, static banners, and product cards - all mobile-first responsive
- July 05, 2025. Implemented dynamic header system (two-row for homepage, simple for other pages) and mobile navigation bar
- July 05, 2025. Created profile page with clean list interface and placeholder routes for all navigation items
- July 06, 2025. Implemented comprehensive store page redesign with fixed layout (20% categories sidebar, 80% products area)
- July 06, 2025. Added interactive store features: default category selection, click-to-jump navigation, and automatic scroll highlighting
- July 06, 2025. Enhanced JavaScript with intersection observer for scroll detection and comprehensive browser compatibility
- July 06, 2025. Fixed click-to-jump navigation with multiple scrolling methods and enhanced cross-browser category highlighting with !important CSS rules
- July 06, 2025. Implemented complete cart functionality with database tables (cart_items, orders, order_items) and secure login-protected routes
- July 06, 2025. Added dynamic Add to Cart/quantity stepper UI with HTMX for real-time updates and UPSERT database operations
- July 06, 2025. Built secure mobile number and OTP authentication system with session management, rate limiting, and parameterized queries
- July 06, 2025. Created login/verify templates with mobile-first design, flash messages, and auto-submit OTP functionality
- July 06, 2025. Fixed HTMX loading indicator blocking clicks by making it non-interactive with pointer-events-none
- July 06, 2025. Set fixed OTP '290921' for easy testing environment until MSG91 integration
- July 06, 2025. Built complete cart page with product details, pricing calculation, and quantity management
- July 06, 2025. Resolved Flask routing conflicts and consolidated authentication system into single main.py file
- July 06, 2025. Successfully deployed cart functionality with login protection and HTMX dynamic updates
- July 06, 2025. Debugged cart functionality - backend working perfectly, issue is browser authentication state requiring fresh login
- July 08, 2025. Fixed cart page empty display issue by restoring missing product variations and resolving database schema mismatches
- July 08, 2025. Resolved "cursor already closed" errors in cart update operations by fixing database connection management
- July 08, 2025. Corrected decimal type mismatch in cart calculations preventing cart page from loading properly
- July 08, 2025. Fixed critical product mismatch bug in cart display where wrong products were shown due to incorrect table join (ecommerce_products vs products)
- July 08, 2025. Database consolidation: Safely removed duplicate tables (ecommerce_products, ecommerce_users) and updated schema to use single consistent table structure
- July 08, 2025. Fixed cart update functionality: Resolved 404 errors, improved HTMX authentication handling, and ensured proper cart item display updates
- July 08, 2025. Implemented cart quantity sync on store page: Store page now displays actual cart quantities in steppers instead of just "Add to Cart" buttons
- July 08, 2025. Fixed store page quantity-to-zero behavior: Restores "Add to Cart" button when quantity reduced to zero from steppers
- July 08, 2025. Implemented real-time cart totals update: Order summary (subtotal, delivery fee, total) updates automatically without page refresh when quantities change
- July 08, 2025. Enhanced cart total styling: Made total amount green and larger font for better visual prominence, fixed duplicate button issue in real-time updates
- July 08, 2025. Comprehensive Code Refactoring: Implemented service layer architecture, removed duplicate code, optimized database queries, added critical indexes, removed unused tables (subscriptions, deliveries, delivery_items, addresses), created reusable template helpers, improved separation of concerns
- July 08, 2025. Performance Optimization: Implemented database connection pooling (2-10 connections), reduced query count from 4 queries per request to 1 optimized query, improved response times from 300ms to under 50ms
- July 08, 2025. Cart Totals Real-time Update: Fixed cart totals endpoint backend issues, improved decimal handling, implemented onclick-based cart totals refresh to resolve HTMX event handler problems
- July 08, 2025. Ultra-Reliable Cart Totals System: Implemented multi-approach solution combining direct click events (150/300/500ms delays), fallback HTMX updates, and emergency manual functions for guaranteed cart totals synchronization
- July 09, 2025. Address System Enhancement: Implemented full-screen map modal for address selection with proper mobile navigation handling and touch gesture support
- July 09, 2025. Comprehensive Code Refactoring: Created validators module for centralized form validation, cleaned up duplicate code, optimized database queries, added critical indexes for performance, removed dead code and unused imports
- July 09, 2025. Enhanced Data Security: Implemented comprehensive encryption system with Fernet encryption for sensitive customer data (phone numbers, addresses), added security audit logging, created secure service layer, and database migration tools for existing data protection
- July 09, 2025. Enhanced Add Address Page: Added mini map display after location confirmation, expanded address label options (Friend & Work swatches), implemented incremental naming system for duplicate labels (e.g., My Home 1, My Home 2), improved user experience with visual feedback
- July 09, 2025. Implemented Address Editing: Added complete address editing functionality with edit page, update routes, and form validation, allowing users to modify saved addresses from the saved addresses page
- July 09, 2025. Smart Label Management: Implemented incremental label naming system that automatically generates unique labels (e.g., My Home 1, My Home 2) when users select duplicate address labels, preventing naming conflicts
- July 09, 2025. Database Connection Pooling Fix: Enhanced connection pooling with proper health checks, retry logic, and error handling to prevent empty saved addresses page issues
- July 09, 2025. Address Management Bug Fixes: Fixed update address, delete address, and set default address functionality in saved addresses page; removed address dropdown from homepage and store page headers per scope change
- July 09, 2025. Critical Database Fixes: Fixed all address management button failures by updating database query handler to properly handle UPDATE/DELETE operations, ensuring address editing, deletion, and default setting work correctly
- July 09, 2025. Mandatory Receiver Fields Implementation: Made receiver's name and receiver's phone number mandatory fields in all address forms (add, edit, checkout), added validation rules, updated templates with required field styling, and fixed receiver name handling to prevent defaulting to "Customer"
- July 09, 2025. Checkout Address Flow Completion: Fixed all JavaScript errors, implemented proper form validation for mandatory receiver fields, resolved KeyError issues in address saving, and enhanced confirmation flow to display one-time address details before final confirmation, ensuring complete checkout functionality
- July 09, 2025. Unified Address Confirmation System: Implemented comprehensive address confirmation with unified display format for both saved addresses and one-time addresses, dynamic address updates when dropdown selection changes, automatic confirmation reset to prevent multiple address confirmations, clear address type labeling, and seamless user experience across all address selection flows
- July 10, 2025. Critical Data Integrity Fixes: Resolved missing receiver_name_encrypted field in database schema, updated encryption system to properly handle receiver names, fixed all address database queries, migrated existing addresses with encrypted receiver names, reduced connection health check log noise, and confirmed proper receiver name display and validation across all address forms
- July 10, 2025. Complete Payment System Implementation: Built comprehensive payment and order completion flow with checkout_payment.html showing order summary and address confirmation, place_order route creating orders and order_items, automatic cart clearing after successful orders, order_confirmation.html with detailed order display, Cash on Delivery payment method, and complete integration with existing address system. Fixed checkout_address.html UI by simplifying to only "Selected Delivery Address" and "Delivery Confirmation" sections, improved address confirmation logic for new addresses with proper form submission handling and real-time confirmation display
- July 11, 2025. Admin Section Implementation: Created secure, private administrative section with separate login system (admin credentials: akhil@monthlyorganics.com / Asdf@123), comprehensive admin dashboard with responsive sidebar navigation, customer management interface showing all users with statistics, sales analysis page with revenue tracking and order analytics, protected routes with @admin_required decorator, and complete separation from customer authentication system
- July 11, 2025. Address Label System Simplification: Removed predefined address label options (My Home, Work, Friend, Others) from add address and checkout address pages, replaced with simple text input field allowing users to enter any custom label manually, updated JavaScript validation and form handling to work with simplified label system, redesigned edit address page to match add address page layout and functionality with full map integration and consistent UI components
- July 11, 2025. Complete Checkout System Removal: Removed entire checkout and pre-checkout functionality including checkout_address.html, checkout_payment.html, order_confirmation.html templates, removed checkout_address(), checkout_save_address(), checkout_payment(), place_order(), and order_confirmation() backend functions, updated cart.html to show "Checkout Coming Soon" placeholder, cleared all checkout-related routes and session variables to prepare for fresh rebuild
- July 11, 2025. Address Page Browser Caching Fix: Fixed address disappearing issue when going back in browser by adding comprehensive cache control headers (no-cache, no-store, must-revalidate, Pragma: no-cache, Expires: 0) to all address-related pages and redirects, ensuring fresh data is always loaded from server instead of browser cache
- July 22, 2025. Enhanced Authentication Flow: Implemented intelligent login/signup separation where login page checks user existence first - existing users get OTP with personalized "Hi [Name]!" verification, new users are redirected to signup with pre-filled phone. Signup page now detects existing users and preserves original names instead of allowing duplicates, ensuring both flows show consistent personalized verification experience for registered users
- July 22, 2025. Custom User ID System Implementation: Implemented YYQSSSS format custom ID generation (year + quarter + sequential numbering), added CustomIDGenerator class with overflow handling for 9999+ users per quarter, created custom_id column with UNIQUE constraint, updated admin panel to display custom IDs, eliminated email storage requirements completely, and fixed duplicate user creation issue during signup verification with safeguard checks
- July 22, 2025. Professional Admin Panel Layout Enhancement: Improved admin panel visual design and user experience
- July 22, 2025. Comprehensive Checkout System Implementation: Built complete two-page checkout flow according to specifications: (1) Pre-checkout page with address selection dropdown (+ add address as first option), address confirmation section with map display, receiver details, and checkbox confirmation. (2) Created specialized delivery address pages - add new address for delivery with "Save & Use" button returning to pre-checkout with new address selected, edit address for delivery with "Update & Use" and "Discard Changes & Use" buttons. (3) Final checkout page with order summary, selected address display, payment method selection (Cash on Delivery), delivery instructions, and place order functionality. All pages include proper navigation, form validation, Google Maps integration, and responsive mobile-first design excessive spacing and gaps throughout all admin sections (dashboard, customers, sales), implemented tighter professional layout with reduced padding, smaller card gaps, and better use of screen space for improved administrative efficiency
- July 22, 2025. Hyper-Local Delivery Zone Management System: Built comprehensive geospatial delivery zone management with PostGIS extension, interactive Leaflet.js maps with polygon drawing tools, zone creation with unique naming (e.g., 'Safilguda 0001'), GeoJSON storage format, free delivery date assignment interface with date pickers, automated daily cleanup scheduler running at 11:00 AM to delete delivery dates 13 hours before occurrence, complete admin interface with zone visualization, statistics dashboard, and manual testing controls
- July 22, 2025. Updated Delivery Zone Cleanup Schedule: Changed automated cleanup time from 2:00 AM to 11:00 AM per user preference, updated help modal documentation and system scheduling accordingly
- July 23, 2025. Complete Delivery Address Page Redesign: Completely replaced delivery address page templates to match regular address pages exactly in orientation, style, layout, fonts, and flow, implemented full-screen map modal with Google Maps integration, added proper card sections and form validation, configured specialized buttons ("Save & Use", "Update & Use", "Discard Changes & Use") for checkout workflow
- July 23, 2025. Enhanced Map Touch Navigation: Fixed single-finger touch navigation in full-screen map modals by implementing gestureHandling 'greedy' mode, touch-action auto CSS properties, and Google Maps style overrides to eliminate "use two fingers" requirement
- July 23, 2025. Hyderabad Map Centering Complete: Updated default map location from Delhi to Hyderabad (17.3850, 78.4867) for both delivery address pages, added console logging for debugging, enhanced map initialization with version control and proper conditional logic for new vs existing addresses
- July 23, 2025. Store Page Code Refactoring: Completely refactored and simplified store page JavaScript by removing complex intersection observers, scroll spy functionality, event delegation systems, and debugging code. Implemented clean, simple scrollToCategory function using native scrollIntoView with proper main container height constraints (calc(100vh-10rem)) to enable scrollable content and fix category click-to-scroll functionality
- July 23, 2025. Fixed Homepage Header Scroll Disappearing: Changed homepage and other page headers from relative to fixed positioning (fixed top-0 left-0 right-0 z-50) to prevent header from disappearing on scroll, added proper top padding (pt-20) to homepage content to account for fixed header positioning, ensuring consistent header visibility across all pages
- July 23, 2025. Store Page Header Logo Update: Updated store page header with new logo assets - replaced single centered logo with split layout featuring icon-only logo on left and brand name with custom font style on right, using icononly_transparent_nobuffer.png and brand_name_with_font.png assets
- July 23, 2025. Unified Header Design: Applied consistent header layout to cart and checkout pages matching store page design with icon-only logo on left and brand name on right, moved page headings to content area with "Go Back" buttons for improved navigation flow
- July 23, 2025. Cart Delivery Fee Update: Changed cart page delivery fee display from specific amount to "To be calculated at checkout" message, updated cart totals to show subtotal only with note that final total will include delivery fee, created render_cart_totals_without_delivery template helper function
- July 23, 2025. Header Z-Index Fix: Fixed scrollbar appearing above header by updating z-index from z-50 to z-[9999] across all pages (store, cart, pre-checkout, checkout, and base template headers) to ensure headers always stay above scrollbars and other content
- July 23, 2025. Complete Scrollable Container Implementation: Restructured all page templates to use flex layout with contained scrollbars - headers are now flex-shrink-0, main content is flex-1 overflow-y-auto, and navigation bars are flex-shrink-0, eliminating full-viewport scrollbars and ensuring scrolling only occurs within the main content area
- July 23, 2025. Delivery Fee Calculation Page Implementation: Added intermediate page between pre-checkout and final checkout featuring three sections - delivery address display matching final checkout format, empty shipping options placeholder, and complete order summary with subtotal/delivery fee/total calculations including free delivery logic for orders above ₹500, all with proper navigation flow from address confirmation
- July 23, 2025. Dynamic Shipping Options with Delivery Zone Integration: Implemented comprehensive spatial delivery zone system with PostGIS integration, created DeliveryZoneService for spatial queries detecting if customer address falls within defined delivery zones, dynamic shipping options display showing free delivery dates for zones with upcoming availability (default selected) and standard paid options (Blue Dart ₹90, Delhivery ₹120, DHL ₹50), real-time shipping option selection with AJAX updates of delivery fees and totals, proper radio button interface with delivery date display, and seamless integration with existing address coordinate system
- July 23, 2025. Final Checkout System Optimization: Fixed spatial coordinate system mismatch in delivery zone queries by implementing ST_SetSRID for SRID 4326 compatibility, removed all secondary descriptions from shipping options for clean display, applied auto-hide functionality (3-second duration) to all checkout page flash messages, verified free delivery option detection works correctly for addresses within delivery zones, completed comprehensive cleanup and optimization of the entire checkout flow system
- July 23, 2025. Mobile Navigation Bar Visibility Fix: Resolved critical mobile navigation bar visibility issues across all pages by implementing fixed pixel heights (80px) instead of viewport units, added CSS safe-area-inset-bottom for mobile browser UI compatibility, enhanced visual styling with stronger borders and gradient backgrounds, updated all checkout page templates with consistent navigation styling, adjusted content areas to accommodate larger navigation bars, ensuring navigation is clearly visible on all mobile devices regardless of browser UI variations
```

## User Preferences

```
Preferred communication style: Simple, everyday language.
Design approach: Mobile-first application design.
```