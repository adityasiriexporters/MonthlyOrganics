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