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

The application defines the following core models:

1. **User Model**: Stores customer information including email, name, phone, and status
2. **Address Model**: Manages delivery addresses with support for multiple addresses per user
3. **Subscription Model**: (Referenced but not fully implemented in current codebase)

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
```

## User Preferences

```
Preferred communication style: Simple, everyday language.
Design approach: Mobile-first application design.
```