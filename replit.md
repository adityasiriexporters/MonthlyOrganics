# Monthly Organics

## Overview

Monthly Organics is a Flask web application designed for an organic produce delivery service. It provides a platform for customers to subscribe to monthly organic produce deliveries, offering a seamless experience from product selection to delivery. The project aims to deliver a modern, user-friendly interface for managing organic produce subscriptions.

## User Preferences

Preferred communication style: Simple, everyday language.
Design approach: Mobile-first application design.

## System Architecture

The application adheres to a Flask web application architecture, emphasizing separation of concerns.

**Core Principles:**
- **Layered Design:** Presentation, Application, and Data layers are distinct.
- **Responsiveness:** Mobile-first design is a core principle, ensuring optimal experience across devices.
- **Interactivity:** Utilizes modern frontend tools for dynamic user interactions without heavy JavaScript.

**Key Architectural Components:**

-   **Backend (Flask):** Serves as the primary web framework, managing HTTP requests, routing, and business logic.
-   **Database (PostgreSQL with SQLAlchemy):** Provides robust data storage and an ORM for efficient data management. The schema includes entities for Users, Addresses, Categories, Products, Product Variations, Cart Items, Orders, and Order Items.
-   **Frontend (Tailwind CSS, Alpine.js, htmx):**
    -   **Tailwind CSS:** For utility-first styling and responsive layouts.
    -   **Alpine.js:** For lightweight, reactive client-side interactivity.
    -   **htmx:** For AJAX interactions, minimizing custom JavaScript.
-   **Authentication:** Features a secure mobile number and OTP authentication system with session management and rate limiting. It also includes an intelligent login/signup flow, checking user existence and redirecting appropriately, and a custom user ID system (YYQSSSS format).
-   **Cart & Checkout:** Implements comprehensive cart functionality with real-time updates and a two-page checkout flow including address selection (with map integration), order summary, delivery options (including free delivery based on zones), and payment (Cash on Delivery).
-   **Address Management:** Supports adding, editing, and deleting addresses with geolocation, custom labels, and secure encryption for sensitive data. It includes a unified address confirmation system for both saved and one-time addresses.
-   **Admin Panel:** A secure administrative section for managing customers, sales analysis, and a hyper-local delivery zone management system with PostGIS, Leaflet.js, and polygon drawing tools. It includes dynamic delivery date assignment and automated cleanup.
-   **Performance & Security:** Employs database connection pooling, query optimization, critical indexing, comprehensive data encryption (Fernet) for all sensitive customer data including phone numbers, and comprehensive cache control.

**Recent Changes (August 2025):**
-   **Phone Number Encryption Migration:** Successfully migrated all user phone numbers from plaintext to encrypted storage. The system now uses `phone_encrypted` and `phone_hash` columns for secure storage and fast lookup, while maintaining backwards compatibility through SQLAlchemy property methods. The plaintext `phone` column has been removed from the database.
-   **Admin Panel Encryption Support:** Updated all admin customer management functions to work with encrypted phone data. Fixed SQL queries in `get_all_customers_with_stats()` and `get_filtered_customers()` to use `phone_encrypted` column and properly decrypt data for display.
-   **Unified Service Layer:** Consolidated phone lookup functionality across both UserService (ORM) and SecureUserService (raw SQL) to use consistent encryption methods. Both services now provide identical results for phone-based user searches.
-   **Email Column Removal:** Successfully removed the email column from the users table per user requirements. Updated all code references, SQL queries, admin panel functions, and database exports to no longer depend on email data. Users are now identified by phone numbers and custom IDs only.
-   **IST Timezone Implementation:** Implemented comprehensive Indian Standard Time (IST) handling across the entire application. All timestamps now display in the format "07 Jan 2025, 06:24 PM" in IST. This includes database exports, admin panel displays, CSV exports, and all template rendering. Created timezone utility module with automatic UTC-to-IST conversion and consistent formatting.
-   **Complete Custom_ID Migration (August 2025):** Successfully completed comprehensive migration to use custom_id (YYQSSSS format) as the primary user identifier across all related tables. Updated all service layers including UserService.create_user(), CartService, AddressService, SecureAddressService, QueryOptimizer, and admin panel functions. Dropped old user_id foreign key columns from addresses, cart_items, and orders tables. All database operations now use custom_id for user identification, ensuring consistency and supporting the custom ID system requirements.
-   **Session Management & Cart Fixes (August 2025):** Fixed critical add-to-cart functionality issues caused by stale session data. Added proper session validation to handle cases where session contains non-existent user_ids. Implemented database constraints for cart_items UPSERT operations. Added comprehensive error handling that clears stale sessions and redirects users to login when needed. All cart operations now work correctly with the custom_id system.
-   **Address Management System Fixes (August 2025):** Resolved all address-related functionality issues in the custom_id migration. Fixed type mismatch errors in pre-checkout address loading, address editing, delivery fee calculation, and default address setting. Updated all SecureAddressService methods (set_default_address, update_address, delete_address) to use user_custom_id instead of user_id. Fixed pre-checkout dropdown address loading that was preventing checkout flow completion. Corrected redirect flow for adding/editing addresses during checkout to properly return to pre-checkout page with the new/updated address selected. Implemented default address status preservation during updates - addresses that are set as default remain default after editing, preventing users from losing their default address status. Fixed "Discard Changes & Use Original" button to correctly redirect to pre-checkout page. Implemented no-addresses checkout flow - when users have no saved addresses, clicking "Proceed to Checkout" now redirects directly to "Add Delivery Address" page with clear guidance message. All address operations now function correctly with encrypted data and custom_id system.
-   **Deployment Health Check Fixes (August 2025):** Resolved deployment health check failures by implementing comprehensive fixes. Added dedicated `/health` endpoint with database connectivity testing for deployment verification. Fixed all critical type errors that could cause runtime crashes, especially null-safety issues with `get_user_custom_id()` returning `Optional[str]` but service functions expecting non-null strings. Added robust error handling with proper session validation and cleanup for stale sessions. Optimized application startup by implementing graceful database initialization with error recovery. Added comprehensive logging for debugging deployment issues. All routes now properly handle edge cases and respond within expected timeframes for deployment health checks.

## External Dependencies

**Python Libraries:**
-   Flask
-   Flask-SQLAlchemy
-   psycopg2-binary
-   Werkzeug

**Frontend Libraries (CDN-based):**
-   Tailwind CSS
-   Alpine.js
-   htmx

**Database:**
-   PostgreSQL
-   PostGIS (for geospatial delivery zone management)

**APIs/Services:**
-   Google Maps API (for address geolocation and map display)
-   MSG91 (planned for OTP delivery - currently uses a fixed OTP for testing)