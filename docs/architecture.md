# Project Architecture

## 1. Overview

The project is a web-based system for 3D scene reconstruction using
Gaussian Splatting.

The main processing pipeline is:

User
→ FastAPI
→ Image Storage
→ Input Analysis
→ COLMAP
→ Gaussian Splatting
→ Result Storage
→ Web Viewer

The system allows users to create reconstruction projects, upload images,
process them, and view the reconstructed 3D scene in a browser.


## 2. Backend Architecture

The backend is implemented in Python using FastAPI.

The backend is divided into several layers:

API (FastAPI routers)
→ Services
→ Database / Storage
→ Processing pipeline

### API

The API receives HTTP requests from the client.

Examples:

- create project
- upload images
- get project information
- start reconstruction
- get reconstruction status
- get results

The API should contain as little business logic as possible.


### Services

Services contain the main application logic.

For example:

- creating projects
- validating uploaded images
- managing project state
- starting reconstruction jobs
- communicating with the processing pipeline


### Database

PostgreSQL is used to store structured data and metadata.

Examples:

- projects
- uploaded image metadata
- project status
- reconstruction status
- processing parameters
- quality metrics

SQLAlchemy is used as the ORM.

Alembic is used for database migrations.


### File Storage

Large files are not stored directly in PostgreSQL.

They are stored in the filesystem:

storage/projects/<project_id>/

Each project has its own directory:

storage/projects/<project_id>/
├── input/
├── analysis/
├── colmap/
├── gaussian/
├── result/
├── metrics/
└── logs/

The database stores metadata and paths to these files.


## 3. Processing Pipeline

The planned reconstruction pipeline is:

1. User creates a project.
2. User uploads multiple images.
3. Images are validated and analyzed.
4. COLMAP performs feature extraction, matching and camera reconstruction.
5. Gaussian Splatting creates the 3D representation.
6. Quality and performance metrics are collected.
7. The resulting scene is made available to the web viewer.


## 4. Backend Structure

backend/
├── main.py
├── database/
│   ├── database.py
│   └── models.py
├── routers/
├── services/
└── storage/

### database/

Database connection and SQLAlchemy models.

### routers/

FastAPI HTTP endpoints.

### services/

Application and business logic.

### storage/

Filesystem operations for project data.


## 5. Project Identification

Each reconstruction project has a unique UUID.

The same project ID is used by:

- the API
- PostgreSQL
- filesystem storage

Example:

API:
    /projects/550e8400-e29b-41d4-a716-446655440000

Database:
    projects.id = 550e8400-e29b-41d4-a716-446655440000

Filesystem:
    storage/projects/550e8400-e29b-41d4-a716-446655440000/


## 6. Database Strategy

The initial database will contain at least:

### projects

Stores information about reconstruction projects.

Planned fields:

- id
- status
- created_at
- updated_at

### images

Stores metadata about uploaded images.

Planned fields:

- id
- project_id
- filename
- path
- width
- height
- created_at

Additional tables for reconstructions and metrics will be added when
their exact requirements are defined.


## 7. Current Technology Stack

Backend:
- Python
- FastAPI
- SQLAlchemy
- PostgreSQL
- Alembic

Image processing:
- Pillow

3D reconstruction:
- COLMAP
- Gaussian Splatting

Frontend / Viewer:
- HTML
- CSS
- JavaScript
- Web-based Gaussian Splatting viewer

Development:
- Git
- GitHub
- Linux










project_service.py:
    post project >> main.py >> project_service