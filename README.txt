# Camera System Qt Conversion Project

## Overview
Migration of 8-camera Tkinter system to Qt (PyQt6/PySide6) for professional-grade performance.

## Current Status
- **Source**: Tkinter v1.0.0 (functional but 200-500ms GUI lag)
- **Target**: Qt-based GUI (<100ms response time)
- **Timeline**: Dec 2025 - Mar 2026 (4 months, 190-300 hours)
- **Launch**: April 2026 (DiSSCo UK Deployment)

## Development Strategy

### MacBook-First Testing Protocol
1. Build Qt GUI framework on MacBook with mock camera data
2. Test all UI interactions locally without Pi hardware
3. Deploy to Pi only for integration validation
4. Minimize deployment cycles through thorough local testing

### Directory Structure
- `src/` - Qt conversion source code
- `tests/` - Unit tests and mock data generators
- `docs/` - Technical documentation
- `reference_tkinter/` - Original Tkinter code (READ-ONLY reference)

## Key Features to Migrate
- 8-camera live preview grid
- Still capture with timestamp overlay
- Video stream display
- Camera health monitoring
- Network status indicators
- Error handling and recovery

## Performance Goals
- GUI response time: <100ms (vs 200-500ms current)
- Frame rate: 90-95% lag reduction
- Smooth multi-camera switching
- Responsive during network operations

## Dependencies
- PyQt6 or PySide6 (TBD after evaluation)
- Python 3.9+
- OpenCV for image processing
- Existing camera communication protocols

## Testing Approach
1. Mock camera data generator for MacBook testing
2. Unit tests for each Qt component
3. Integration tests with simulated network delays
4. Final validation on Pi hardware

## Session Continuity
All work logged in: `/Users/andrew1/Desktop/QT_CONVERSION_LOG.txt`
Use GERTIE protocol for session recovery after timeouts.

## Reference Code
Original Tkinter implementation: `reference_tkinter/`
- still_capture.py (41,847 lines)
- video_stream.py (30,181 lines)
- Offline versions for testing
- Total: ~2,827 lines of reference code

## Automation Level
Target: 70-80% via Claude + Desktop Commander
Human oversight for: Architecture decisions, UI/UX design, Pi integration testing

---
Last Updated: 2025-11-12
Project Phase: Initialization Complete
