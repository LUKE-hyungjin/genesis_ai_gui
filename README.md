# Genesis Interactive GUI

An interactive GUI for Genesis physics simulation integrating high-speed simulation (1000+ FPS) with a responsive Dear PyGui interface (60 FPS) using the "Init-Main, Run-Threaded" architecture.

## Features

- **Playback Control**: Start, pause, and step through simulations
- **Real-time 3D Viewport**: Continuously updating visualization at 60 FPS
- **Property Editing**: Interactive parameter tuning with Undo/Redo support
- **Live Signal Plotting**: Real-time plotting with intelligent downsampling
- **Viewport Raycasting**: Click entities to select them
- **Transform Gizmo**: Direct manipulation of entity transforms

## Prerequisites

- **Python**: 3.11 or later
- **GPU**: Metal (macOS), CUDA (NVIDIA), or Vulkan support
- **Operating System**: macOS 14+, Ubuntu 22.04+, or Windows 10+

## Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd genesis_ai_gui
```

### 2. Create virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # On macOS/Linux
# OR
.venv\Scripts\activate  # On Windows
```

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Verify installation

```bash
python -c "import genesis as gs; import dearpygui.dearpygui as dpg; print('✅ Installation successful!')"
```

## Project Structure

```
genesis_ai_gui/
├── src/
│   ├── core/           # Simulation thread logic
│   │   ├── sim_loop.py
│   │   ├── ipc.py
│   │   └── commands.py
│   ├── ui/             # GUI thread logic
│   │   ├── main.py
│   │   ├── viewport.py
│   │   ├── inspector.py
│   │   ├── scene_tree.py
│   │   ├── plots.py
│   │   └── gizmo.py
│   └── infra/          # Shared infrastructure
│       ├── bootstrap.py
│       ├── metrics.py
│       └── config.py
├── tests/              # Test suites
├── specs/              # Specification documents
└── requirements.txt    # Python dependencies
```

## Development

This project follows a phased implementation plan:

- **Phase 1**: Mock Thread + GUI Wiring
- **Phase 2**: Genesis Renderer Integration
- **Phase 3**: Dual-Loop Separation (Playback + Viewport)
- **Phase 4**: Property Editing + Undo/Redo
- **Phase 5**: Live Plotting
- **Phase 6**: Raycasting + Gizmo (Optional)
- **Phase 7**: Polish & Cross-Cutting Concerns

See [specs/001-genesis-interactive-gui/tasks.md](specs/001-genesis-interactive-gui/tasks.md) for the complete task breakdown.

## Running the Application

```bash
# Activate virtual environment
source .venv/bin/activate

# Run the application (once implemented)
python -m src
```

## Documentation

- [Feature Specification](specs/001-genesis-interactive-gui/spec.md)
- [Implementation Plan](specs/001-genesis-interactive-gui/plan.md)
- [Task List](specs/001-genesis-interactive-gui/tasks.md)
- [Quickstart Guide](specs/001-genesis-interactive-gui/quickstart.md)
- [Data Model](specs/001-genesis-interactive-gui/data-model.md)
- [Research Findings](specs/001-genesis-interactive-gui/research.md)

## Architecture

The application follows the "Init-Main, Run-Threaded" pattern:

- **Main Thread**: Dear PyGui GUI loop (60 FPS)
- **Background Thread**: Genesis simulation loop (maximum FPS)
- **Communication**: Commands via queue, frames via shared memory, events via queue

Key architectural principles:

1. All graphics/compute contexts initialized on main thread only
2. Threading-only concurrency (no asyncio)
3. Data pathway segregation (queues for commands/events, shared memory for frames)
4. Optimistic UI with commit-on-release pattern for property editing

See the [constitution](.specify/memory/constitution.md) for complete architectural invariants.

## Contributing

This project strictly adheres to the constitutional principles defined in `.specify/memory/constitution.md`. All contributions must comply with these architectural constraints.

## License

[Specify license here]

## Acknowledgments

- [Genesis](https://github.com/Genesis-Embodied-AI/Genesis) - Physics simulation engine
- [Dear PyGui](https://github.com/hoffstadt/DearPyGui) - GUI framework
- [tsdownsample](https://github.com/predict-idlab/tsdownsample) - Time-series downsampling
