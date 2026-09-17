# AEP 010: A dedicated Graphical User Interface for AiiDA

| AEP number | 010                                                          |
|------------|--------------------------------------------------------------|
| Title      | 	A dedicated Graphical User Interface for AiiDA            |
| Authors    | [Xing Wang](mailto:xingwang1991@gmail.com) (superstar54)     |
| Champions  | [Xing Wang](mailto:xingwang1991@gmail.com) (superstar54), [Edan Bainglass](mailto:edan.bainglass@psi.ch) (edan-bainglass) [Kristjan Eimre](mailto:kristjaneimre@gmail.com) ( eimrek), [Bud Macaulay](mailto:bud.macaulay@psi.ch) (bud-macaulay)|
| Type       | S - Standard Track AEP                                       |
| Created    | 18-June-2025                                                 |
| Status     | Draft  

---

## Table of Contents

1. [Background](#background)
2. [Proposed Enhancement](#proposed-enhancement)

   * [Key Features](#key-features)
3. [Implementation Details](#implementation-details)

   * [Backend: FastAPI & aiida-restapi](#backend-fastapi--aiida-restapi)
   * [Frontend: React & Component Library](#frontend-react--component-library)
   * [Plugin Architecture](#plugin-architecture)
   * [Apps Integration](#apps-integration)
   * [CLI & Deployment](#cli--deployment)
   * [Security & Authentication](#security--authentication)
4. [Usage Examples](#usage-examples)
5. [Design Considerations](#design-considerations)

   * [Integration with AiiDA Core](#integration-with-aiida-core)
   * [Performance and Scalability](#performance-and-scalability)
   * [Extensibility and Maintainability](#extensibility-and-maintainability)
6. [Optional apps integration](#optional-apps-integration)
7. [Conclusion](#conclusion)

---

## Background

AiiDA’s command-line interface (CLI) is powerful and scriptable, yet many users, especially newcomers, find the text-based tools steep to learn and lacking in interactivity. Modern computational science benefits greatly from visual summaries of running processes, interactive data viewers (for crystal structures, band structures, arrays…), and plugin-driven dashboards that can be composed on the fly. While tools like AiiDAlab and Materials Cloud offer some GUI functionality, they either run within Jupyter notebooks or impose heavy deployment overhead. A dedicated, self-hosted AiiDA GUI would lower the barrier to entry, speed up common tasks, and provide a solid foundation for community-built extensions.


---

## Proposed Enhancement

Provide a standalone web-based graphical interface for AiiDA, **AiiDA GUI**, that allows users to inspect and control processes, explore data nodes in rich viewers, and extend its functionality through plugins.


### Key Features

* **Core Views**

  * **Process Table:** live view of running and completed processes, with filters, search, and status badges, and control buttons (pause, resume, kill, delete).
  * **Data nodes Table:** browse Data nodes with faceted filters and custom projections.
  * **Node Group Table:** create, edit, and query Groups of nodes or processes.
  * **Daemon Control:** start/stop/restart the AiiDA daemon and monitor logs in real time.
  * **Computer & code:** Configure and manage computers and codes.

* **Rich Data Viewers**

  * Raw JSON inspector for any node
  * Specialized renderers: crystal structure (using weas), band structure plots, array and dict, and more.

* **Rich Process Viewers**

  * Interactive WorkChain and workflow graphs (e.g., inspired by `WorkGraph`), as well as process report, summary etc.
  * `CalcJob` viewers similar to Materials Cloud.
  * Provenance graph visualization or table: inputs, outputs, and dependencies.

* **Plugin Ecosystem**

  * Load frontend dynamically into sidebar, new pages or data viewers.
  * Shared React component library (`aiida-react-components-base`) published to npm

* **CLI Integration**

  * `pip install aiida-gui` (or `verdi gui install`)
  * Commands: `aiida-gui start|stop|restart|status`
  * Mount the React frontend into FastAPI so only a single process is needed

* **Security & Multi-User Support**

  * Token-based access (`?token=…`) akin to Jupyter notebooks
  * Optional integration with JupyterHub deployment for centralized authentication

---

## Implementation Details

### Backend: FastAPI & aiida-restapi

* **Leverage** the existing [aiida-restapi](https://github.com/aiidateam/aiida-restapi) endpoints, adding new ones as needed.
* **Refactor** aiida-restapi to allow query-time projections and filters (e.g. selecting only certain columns).
* **Expose** new routes for plugin registration and discovery.
* **Mount** plugin routers automatically by scanning entry points under `aiida_gui.plugins`.

### Frontend: React & Component Library

* **Framework:** React (latest stable), built with Vite or Next.js in ESM mode.
* **Component Package:** `aiida-react-components-base` on npm, containing:

  * Data viewers, e.g., StructureViewer, BandsPlot, TableGrid.
  * Common UI elements, e.g., Code selection, process tree.
* **Build & Mount:**

  * Build output is a static bundle served by FastAPI at `/static/`.
  * FastAPI serves `index.html` at `/`, embedding the React app.

### Plugin Architecture

* **Backend:** Plugins declare entry points under `aiida_gui.plugins` which provide a FastAPI Router. On startup, the core app includes these routers under `/plugins/{name}`.
* **Frontend:** Plugins publish an ESM bundle, with its entry describing routes and components to mount in the sidebar or as standalone pages. The core React app loads and mounts these dynamically.

### CLI & Deployment

* **Entry Point:** `aiida-gui` console script
* **Commands:**

  * `aiida-gui start [--host HOST] [--port PORT] [--token TOKEN]`
  * `aiida-gui stop`
  * `aiida-gui restart`
  * `aiida-gui status`
* **Configuration:** `~/.config/aiida/gui-config.json` holds defaults for host/port, token, plugin enable/disable.

### Security & Deployment

* **Token Auth:** generate a random token at first run; all GUI requests must include `?token=` or `Authorization: Bearer`.
* **JupyterHub Integration:** provide optional flags to respect JupyterHub’s proxy authentication and mount under user’s namespace, e.g., under `/user/{name}/aiida-gui/`.


---

## Usage Examples

```bash
pip install aiida-gui
aiida-gui start --port 8080
```

* Open `http://localhost:8080?token=3f8d2a…` in your browser.
* Browse running processes, inspect nodes, and control the daemon.

To install a community plugin:

```bash
pip install aiida-gui-myplugin
aiida-gui restart
```

The plugin’s sidebar entry appears; clicking it loads its custom page and data viewers.

---

## Design Considerations

### Integration with AiiDA Core

* **Non-intrusive:** No changes to `aiida-core` are required beyond optional dependency mount the cli command to `verdi`.

### Performance and Scalability

* **Backend:** FastAPI + Uvicorn supports async concurrency; use caching where appropriate for heavy queries.
* **Frontend:** Code-splitting ensures only needed plugins are loaded.

### Extensibility and Maintainability

* **Plugin-First:** Every new feature should live as a plugin until it proves broadly useful for the core.
* **Shared Components:** Encourage reuse via the `aiida-react-components-base` package.
* **Documentation & Testing:** Provide cookie-cutter plugin template, and CI pipelines for core and plugins.

---

## Optional apps integration

Apps differ from standard plugins, which are JavaScript modules dynamically loaded into the core GUI. Instead, apps are collections of AiiDA GUI applications delivered as fully self-contained static bundles (HTML, JS, and CSS) that run independently of the main React router. They provide complete, task-specific frontends with their own UI and workflow logic, while still interacting with AiiDA via its REST API, e.g., a DFT app that submits Quantum Espresso calculations, streams job status, and visualizes results.

* **Packaging:** apps are static HTML/JS/CSS bundles under `/apps/{app_name}/` deployed alongside the core GUI.
* **Discovery and launch:** the GUI’s "Apps" page lists installed apps with names, icons, and metadata; users can launch them directly in a new tab or window.
* **Reuse:** apps may import shared components from `aiida-react-components-base` to maintain a consistent UX.

---

## Conclusion

The proposed AiiDA GUI brings a modern, user-friendly interface to AiiDA, reducing the learning curve and enabling rich, interactive exploration of workflows and data. By building on FastAPI and React, and embracing a plugin ecosystem, the GUI will be flexible, performant, and easily extensible by the community. This enhancement promises to accelerate AiiDA adoption and catalyze the development of domain-specific extensions.
