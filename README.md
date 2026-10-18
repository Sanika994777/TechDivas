### **Team Name : TechDivas**
### **Team Members :**
1. Vedika Kute 
2. Sanika Surange 

---

### **Project Details :**
# **CivicFix - Your City. Your Voice. Our Responsibility**.
**Live Demo:** (https://tech-divas-xi.vercel.app/)

CivicFix is a civic issue reporting and tracking platform that connects citizens with the teams responsible for resolving local infrastructure and sanitation problems. It enables citizens to report issues, explore nearby complaints, support existing reports, and track resolution progress with transparent status updates and photo evidence.

---

## **1. Problem Statement**

Citizens often struggle to report local civic issues, identify the appropriate authorities, and track whether their complaints have been resolved. Problems such as potholes, water leakage, overflowing garbage, damaged roads, drainage issues, and broken streetlights can remain unresolved due to poor communication, duplicate complaints, and a lack of transparency.

CivicFix aims to bridge this gap by providing a centralized platform for reporting, managing, prioritizing, and tracking civic issues.

## **2. Solution**

CivicFix provides a user-friendly digital platform where citizens can submit civic complaints with photos, descriptions, categories, and precise locations. They can explore nearby reports, support existing complaints, and track progress through a personal dashboard.

Responsible teams can manage assigned complaints, update their status, and upload resolution photos as evidence of completed work. An intelligent prioritization mechanism helps identify urgent issues based on severity, community impact, and time unresolved, while duplicate detection helps reduce redundant complaints.

## **3. Features**
### Citizen Portal
- Register and log in (JWT authentication)
- Report issues with 1-3 photos, category, description and a draggable map pin
- AI-assisted photo analysis that suggests a category and severity (editable by the citizen)
- Duplicate detection: "Similar Issues Nearby" before submitting
- "I'm Affected Too" upvote (one per user)
- Explore nearby reports on a map with radius, category and status filters
- Citizen dashboard with a status timeline and before/after photo comparison
- Satisfied / Reopen option after resolution
- Complaint status chatbot using the backend reference ID (e.g. `CF-2026-00125`)

### Worker / Admin Portal
- Role-based login (Worker, Admin)
- Admin assigns issues to teams and views issues sorted by priority
- Worker updates status (Reported → Assigned → In Progress → Resolved)
- Resolving an issue requires an "after" photo and a resolution note
- Admin duplicate review (Merge / Not duplicate)
- Statistics dashboard: totals, resolution times, overdue issues, and charts by category and status

### Innovation
- **Priority score (0-100)** = 40% severity + 35% community impact + 25% time unresolved
- A "Why this score?" breakdown shown for each issue
- Duplicate detection using location distance, category and text similarity

## **4. Tech Stack**

- Frontend: React, Vite, TypeScript, Tailwind CSS, React Router
- Maps & Geocoding: Leaflet, OpenStreetMap, Nominatim
- Data Visualization: Recharts
- Backend: Python, FastAPI, SQLAlchemy
- Database: Neon (Serverless PostgreSQL)
- Image Storage: Cloudinary
- AI & Image Analysis: Google Gemini API
- Authentication & Security: JWT, bcrypt, Role-Based Access Control (RBAC)
- Deployment: Vercel (Frontend), Render (Backend)

## **5. Tech Stack Justification**

- React, Vite, and TypeScript: Enable fast development, reusable UI components, and type safety, helping reduce errors and simplify maintenance under tight hackathon deadlines.

- Tailwind CSS: Supports rapid, consistent styling and responsive, mobile-first layouts without requiring extensive custom CSS.

- Leaflet and OpenStreetMap: Provide interactive maps and location visualization using open-source mapping tools, helping keep the project accessible and cost-effective.

- Nominatim: Enables address search and reverse geocoding, allowing users to find locations and convert geographic coordinates into readable addresses.

- FastAPI: Provides high-performance API development, automatic request validation through Pydantic, and interactive Swagger documentation for easier testing. Python also simplifies implementing text-similarity algorithms for duplicate complaint detection.

- Neon PostgreSQL: Offers a managed, serverless relational database suitable for structured data such as users, complaints, assignments, and status history, simplifying cloud deployment and database management.

- SQLAlchemy: Provides an Object-Relational Mapper (ORM) for interacting with PostgreSQL through Python models, making database operations more organized and maintainable.

- Cloudinary: Provides cloud-based image storage and CDN delivery for complaint photos and resolution evidence, avoiding dependence on temporary local storage in the deployed backend.

- Google Gemini API: Enables AI-assisted analysis of uploaded photos, including suggested issue categories, severity levels, and descriptions. A keyword-based fallback can maintain basic functionality when the AI service is unavailable.

- JWT and bcrypt: JWT supports stateless authentication, while bcrypt securely hashes passwords. Role-Based Access Control (RBAC) separates permissions for Citizens, Workers, and Administrators.

- Recharts: Simplifies the creation of interactive charts and visualizations for complaint statistics, resolution rates, pending issues, and average resolution times.

- Vercel and Render: Provide convenient cloud deployment for the frontend and backend, with Git-based workflows that simplify updates and integration.
## **6. Setup and Usage**
## **7. Links**
- **Live Link:** (https://tech-divas-xi.vercel.app/)
- **Video Link:** 
<!-- - **Backend API Docs:** <ADD_BACKEND_URL>/docs -->
