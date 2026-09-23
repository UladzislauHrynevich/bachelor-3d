# Bachelor 3D — System Architecture

## 1. Project Overview

The project implements an interactive Novel View Synthesis (NVS) system
for telepresence.

The system receives a set of photographs of a real environment,
reconstructs a scene using 3D Gaussian Splatting (3DGS), and allows
a user to interactively explore the reconstructed environment from
novel virtual viewpoints through a web interface.

Computationally expensive reconstruction tasks are separated from the
main application server and may be executed on an external GPU worker.

The system also collects processing logs, configuration parameters,
performance metrics and reconstruction results. These data will be used
for the experimental evaluation of the system.


## 2. Main Goal

The main goal is to design and implement an interactive web-based
Novel View Synthesis system based on 3D Gaussian Splatting and evaluate
the trade-off between:

- visual quality,
- inference/rendering performance,
- resource requirements,
- interaction latency,
- user-perceived interactivity.

The analysis of input image quality itself is outside the primary
research scope of this project.


## 3. Project Scope

The project consists of two main parts:

### 3.1 Engineering Part

Development of an end-to-end system for:

1. creating reconstruction projects,
2. uploading images,
3. storing project metadata,
4. starting reconstruction jobs,
5. executing computationally expensive processing on a GPU worker,
6. collecting logs and metrics,
7. storing reconstruction results,
8. displaying reconstructed scenes in a web viewer,
9. controlling a virtual camera interactively.


### 3.2 Experimental Part

The implemented system will be used as an experimental platform for
evaluating 3D Gaussian Splatting in an interactive NVS/telepresence
scenario.

The primary research focus is the relationship between:

- reconstruction quality,
- inference/rendering performance,
- representation size and resource requirements,
- interaction latency and responsiveness.

The exact 3DGS parameters and optimization methods used in the
experiments will be selected after the processing implementation and
literature review are completed.


## 4. High-Level Architecture

```text
                         USER
                          │
                          ▼
                 ┌─────────────────┐
                 │  WEB FRONTEND   │
                 │                 │
                 │ Upload          │
                 │ Project status  │
                 │ Results         │
                 │ 3D Viewer       │
                 └────────┬────────┘
                          │
                       HTTP/API
                          │
                          ▼
                 ┌─────────────────┐
                 │     FASTAPI     │
                 │     BACKEND     │
                 └────────┬────────┘
                          │
          ┌───────────────┼────────────────┐
          │               │                │
          ▼               ▼                ▼
    ┌────────────┐  ┌────────────┐  ┌────────────┐
    │ PostgreSQL │  │  Storage   │  │ Job/       │
    │            │  │            │  │ Processing │
    │ metadata   │  │ files      │  │ Manager    │
    └────────────┘  └────────────┘  └─────┬──────┘
                                           │
                                      processing job
                                           │
                                           ▼
                                  ┌──────────────────┐
                                  │ EXTERNAL GPU     │
                                  │ WORKER           │
                                  │                  │
                                  │ Input processing │
                                  │ COLMAP           │
                                  │ 3DGS             │
                                  │ Evaluation       │
                                  └────────┬─────────┘
                                           │
                                  result / metrics /
                                        logs
                                           │
                                           ▼
                                       BACKEND
                                           │
                                           ▼
                                      WEB VIEWER
                                           │
                                           ▼
                                    VIRTUAL CAMERA
                                           │
                                           ▼
                                      NOVEL VIEWS
````

## 5. Main Components

### 5.1 Web Frontend

The frontend is the user-facing part of the system.

Responsibilities:

* create projects,
* upload input images,
* display processing status,
* display errors,
* display experiment/results information,
* load reconstructed scenes,
* provide interactive virtual camera controls.

The frontend should not perform reconstruction management or directly
communicate with GPU workers.

### 5.2 FastAPI Backend

The backend acts as the central control layer of the system.

Responsibilities:

* expose the HTTP API,
* validate requests,
* manage projects,
* manage uploaded images,
* manage processing jobs,
* communicate with the persistence layer,
* coordinate processing,
* collect processing results,
* provide reconstruction metadata to the frontend.

The backend should not contain implementation-specific COLMAP or 3DGS
logic directly inside API endpoints.

## 6. Backend Layering

The backend follows a layered structure.

```text
HTTP Request
     │
     ▼
┌──────────────┐
│ API Endpoint │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   Service    │
│    Layer     │
└──────┬───────┘
       │
       ├─────────────────┐
       ▼                 ▼
┌──────────────┐   ┌──────────────┐
│  Database    │   │   Storage    │
│  / ORM       │   │   Manager    │
└──────────────┘   └──────────────┘
```

### API Layer

Responsible for HTTP-specific behavior:

* request parsing,
* dependency injection,
* HTTP status codes,
* response serialization.

### Service Layer

Responsible for application/business operations.

Examples:

* create a project,
* register an uploaded image,
* start a processing job,
* update job state,
* register processing results.

A service operation may coordinate multiple resources such as
PostgreSQL and filesystem storage.

### Persistence Layer

Responsible for persistent metadata stored in PostgreSQL.

SQLAlchemy is used as the ORM.

Alembic is used for database schema migrations.

### Storage Layer

Responsible for large files and processing artifacts.

Examples:

* uploaded photographs,
* COLMAP files,
* 3DGS models,
* evaluation outputs,
* raw processing logs.

Large binary processing artifacts are not intended to be stored
directly in PostgreSQL.

## 7. Data Model

The exact database schema will evolve during development.

The main conceptual entities are:

```text
Project
   │
   ├──────────< Image
   │
   ├──────────< ProcessingJob
   │
   └──────────< Experiment
                    │
                    └──────────< Metric
```

### 7.1 Project

Represents one reconstructed real-world scene.

Possible attributes:

```text
id
status
created_at
updated_at
```

The project UUID is the primary identifier connecting the API,
database records and project storage.

### 7.2 Image

Represents metadata about an uploaded input image.

Possible attributes:

```text
id
project_id
original_name
storage_path
size_bytes
created_at
```

The image itself is stored in filesystem/object storage.

The database stores only its metadata and location.

### 7.3 ProcessingJob

Represents execution of a computational processing task.

Possible attributes:

```text
id
project_id
status
worker
created_at
started_at
finished_at
error
```

Possible states:

```text
queued
   ↓
processing
   ↓
completed

or

failed
```

### 7.4 Experiment

Represents one reproducible experimental run/configuration.

A single Project may have multiple experiments.

Example:

```text
Project: Room A

├── Experiment A
│   ├── configuration A
│   └── result A
│
├── Experiment B
│   ├── configuration B
│   └── result B
│
└── Experiment C
    ├── configuration C
    └── result C
```

An experiment should preserve enough information to reproduce the
processing configuration.

### 7.5 Metric

Represents a structured measurement produced during an experiment.

Potential metrics include:

```text
PSNR
SSIM
LPIPS

FPS
frame_time

model_size
GPU_memory

scene_load_time
interaction_latency

COLMAP_time
training_time
```

The final set of metrics will be determined during implementation and
experimental design.

## 8. Storage Architecture

Large project files are stored separately from structured metadata.

Initial local storage layout:

```text
storage/
└── projects/
    └── <project_uuid>/
        ├── input/
        ├── analysis/
        ├── colmap/
        ├── gaussian/
        ├── result/
        ├── metrics/
        └── logs/
```

Conceptually:

```text
PostgreSQL                  File Storage

Project                     input/*.jpg
Image metadata              colmap/*
Job state                   gaussian/*
Experiment config           result/*
Metrics                     metrics/*
                            logs/*
```

PostgreSQL answers:

> What exists and what is its state?

Storage answers:

> Where is the actual data?

## 9. Processing Architecture

Heavy reconstruction processing is separated from the main backend.

```text
Backend
   │
   │ Processing Job
   ▼
GPU Worker
   │
   ├── obtain input data
   │
   ▼
Input preparation
   │
   ▼
COLMAP
   │
   ▼
3D Gaussian Splatting
   │
   ▼
Evaluation
   │
   ▼
Result
   │
   ├── reconstructed representation
   ├── metrics
   └── logs
   │
   ▼
Backend
```

The processing interface should be designed so that the GPU execution
environment can be changed without redesigning the main application.

Possible execution environments may include:

* university GPU infrastructure,
* cloud GPU server,
* development/prototyping environment.

The final execution environment is TBD.

## 10. COLMAP and 3DGS Pipeline

The reconstruction pipeline is conceptually:

```text
Input Images
     │
     ▼
Feature Extraction
     │
     ▼
Feature Matching
     │
     ▼
Camera Pose Estimation /
Sparse Reconstruction
     │
     ▼
COLMAP Output
     │
     ▼
3D Gaussian Splatting
Training / Optimization
     │
     ▼
Gaussian Scene Representation
     │
     ▼
Novel View Rendering
```

COLMAP provides the camera/reconstruction information required by the
selected 3DGS implementation.

3DGS creates a representation that can subsequently be rendered from
new virtual camera viewpoints.

## 11. Logging and Metrics

Two different kinds of information are collected.

### Raw Logs

Raw execution logs are stored as files.

Example:

```text
logs/
├── colmap.log
├── gaussian.log
└── evaluation.log
```

They are primarily used for:

* debugging,
* error analysis,
* reproducibility.

### Structured Metrics

Measurements required for analysis are stored in structured form.

Example:

```text
experiment_id
PSNR
SSIM
FPS
frame_time
model_size
GPU_memory
training_time
```

These values can later be queried and exported for experimental
analysis.

## 12. Interactive Rendering

After reconstruction is completed, the user should be able to explore
the generated scene using a virtual camera.

Conceptually:

```text
3DGS Scene
     │
     ▼
Renderer
     │
     ▲
     │ camera pose
     │
User Input
     │
     ▼
Virtual Camera
```

The user can modify:

```text
position:
x, y, z

orientation:
yaw, pitch
```

The renderer generates novel views corresponding to the current virtual
camera pose.

The exact rendering architecture is TBD.

Possible approaches include:

1. client-side rendering of the 3DGS representation,
2. server-side rendering and transmission of rendered output.

The final architecture will be selected based on implementation
feasibility and interactive performance.

## 13. Experimental Architecture

Input-data-quality analysis is not the primary research objective of
this project.

Experiments therefore use controlled/fixed input data when evaluating
3DGS configurations.

```text
                    FIXED DATASET
                         │
             ┌───────────┼───────────┐
             ▼           ▼           ▼
          Config A    Config B    Config C
             │           │           │
             ▼           ▼           ▼
           3DGS        3DGS        3DGS
             │           │           │
             ▼           ▼           ▼
          Result A    Result B    Result C
             │           │           │
             └───────────┼───────────┘
                         ▼
                    COMPARISON
```

The primary relationship to investigate is:

```text
                 VISUAL QUALITY
                       ▲
                      / \
                     /   \
                    /     \
                   ▼       ▼
        COMPUTATIONAL     INTERACTIVITY
             COST
```

The purpose is not necessarily to find the configuration with the
highest visual quality.

Instead, the experiments investigate the trade-off between visual
quality and interactive performance in the context of telepresence.

## 14. Experimental Measurements

### Visual Quality

Candidate metrics:

```text
PSNR
SSIM
LPIPS
```

### Rendering / Inference Performance

Candidate metrics:

```text
FPS
frame time
```

### Resource Requirements

Candidate metrics:

```text
model size
GPU memory usage
number of Gaussian primitives
```

### System Interactivity

Candidate metrics:

```text
scene loading time
interaction latency
responsiveness
```

### Processing

Secondary measurements may include:

```text
COLMAP processing time
3DGS training time
```

## 15. User Evaluation

A user evaluation may be performed to connect technical performance
with perceived interactivity.

Example interaction:

```text
Load Scene
    ↓
Navigate
    ↓
Rotate Camera
    ↓
Move Through Scene
    ↓
Complete Navigation Task
    ↓
Evaluate Experience
```

Possible measurements:

```text
task completion time
perceived smoothness
responsiveness
ease of navigation
visual quality
overall experience
```

The exact evaluation protocol and number of participants are TBD.

## 16. MVP Definition

The Minimum Viable Product is an end-to-end implementation of the main
NVS workflow.

```text
Create Project
      ↓
Upload Images
      ↓
Store Images + Metadata
      ↓
Create Processing Job
      ↓
Execute Processing
      ↓
COLMAP
      ↓
3DGS
      ↓
Return Result
      ↓
Load Result in Web Viewer
      ↓
Interactively Move Virtual Camera
      ↓
Render Novel Views
```

The MVP is considered complete when a user can upload a dataset,
process it and interactively explore the reconstructed scene through
the application.

## 17. Bachelor Thesis Complete Version

The final bachelor project extends the MVP with systematic evaluation.

```text
MVP
 │
 ├── experiment management
 │
 ├── reproducible configurations
 │
 ├── automatic metrics collection
 │
 ├── processing logs
 │
 ├── quality evaluation
 │
 ├── rendering performance evaluation
 │
 ├── latency/interactivity evaluation
 │
 └── user evaluation
 │
 ▼
Experimental Results
 │
 ▼
Analysis
 │
 ▼
Conclusions
```

The final result therefore consists of both:

1. a functional software system,
2. experimentally validated conclusions about interactive NVS using
   3D Gaussian Splatting.

## 18. Optional Extensions

The following features are considered optional and are not required
for the initial MVP:

* automatic optimization of 3DGS configurations,
* model pruning/compression,
* level-of-detail techniques,
* automatic selection of processing parameters,
* ML-based prediction of performance/quality,
* comparison of client-side and server-side rendering architectures.

These extensions should only be implemented after the complete
end-to-end MVP is functional.

## 19. Out of Scope

The following tasks are currently outside the primary scope:

* development of a new NVS algorithm from scratch,
* development of a new COLMAP replacement,
* development of a new neural rendering architecture,
* distributed GPU cluster management,
* Kubernetes infrastructure,
* complex microservice architecture,
* full production authentication/authorization system,
* mobile application,
* detailed research into input-image quality.

The project should remain focused on interactive NVS and its
experimental evaluation.

## 20. Current Implementation Status

Currently implemented:

```text
[x] Git repository
[x] FastAPI application
[x] PostgreSQL connection
[x] SQLAlchemy
[x] Alembic migrations
[x] Project database model
[x] Project creation
[x] Project filesystem structure
[x] Basic image upload

[ ] Image database model
[ ] ProcessingJob model
[ ] Experiment model
[ ] Metrics model
[ ] Processing worker
[ ] COLMAP integration
[ ] 3DGS integration
[ ] Result management
[ ] Web frontend
[ ] Interactive viewer
[ ] Experimental automation
[ ] Experimental evaluation
[ ] User evaluation
```

## 21. Development Roadmap

```text
Phase 1
Architecture + Backend Foundation
        ↓
Project + Image persistence
        ↓

Phase 2
Processing Job Architecture
        ↓
Worker interface
        ↓

Phase 3
Reconstruction Pipeline
        ↓
COLMAP
        ↓
3DGS
        ↓

Phase 4
End-to-End MVP
        ↓
Web Viewer
        ↓
Interactive Virtual Camera
        ↓

Phase 5
Experiment Infrastructure
        ↓
Experiments + Metrics + Logs
        ↓

Phase 6
Experimental Evaluation
        ↓
Quality / Performance / Latency
        ↓

Phase 7
User Evaluation
        ↓

Phase 8
Optional Optimizations
```

## 22. Open Questions

The following questions must still be resolved during development and
consultation with the supervisor:

1. Which 3D Gaussian Splatting implementation will be used?
2. What exactly is expected by the thesis assignment regarding
   AI model training for fast inference?
3. Which 3DGS parameters or optimization methods will be selected for
   the experimental evaluation?
4. Will final rendering be client-side or server-side?
5. Which GPU infrastructure will be used for final experiments?
6. Which quality metrics will be used in the final evaluation?
7. How will interaction latency be defined and measured?
8. What user-testing protocol will be used?

````

### Почему именно так

Здесь есть важный принцип: **мы специально не выдаём неизвестное за уже принятое решение**. Например, `client-side vs server-side rendering`, конкретный 3DGS implementation, AI requirement и конкретные параметры экспериментов остаются `TBD`. Это вопросы, которые реально надо решить через литературу, прототип и консультацию с руководителем.

При этом документ уже фиксирует нашу главную границу:

```text
Input-quality research
        ≠
твоя основная research problem

ТВОЯ:
3DGS/NVS
quality ↔ inference ↔ interactivity
````

И архитектура поддерживает это с самого начала.

Ещё мне нравится, что `architecture.md` теперь разделяет **MVP** и **готовую BP**. Это не одно и то же:

```text
MVP
= доказать, что вся цепочка работает

BP
= MVP
  + воспроизводимые эксперименты
  + измерения
  + анализ
  + выводы
```

