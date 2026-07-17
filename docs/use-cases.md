# Ramses Virtual Client Use Cases and Test Plan

## Overview
The Ramses Virtual Client is a Python-based simulator for testing the Ramses system across various hardware configurations, particularly for the CYD (Cheap Yellow Display) proof-of-concept in Sprint 1. It supports dynamic screen sizes from 1.5" ePaper to 7" displays, configuration management, data modes (dummy vs real), and monetization tiers.

## Key Features Simulated
- **Dynamic Screen Emulation**: Different physical sizes, resolutions, color depths (1-bit ePaper B&W, 16-bit color).
- **Configuration Testing**: JSON/YAML configs for device profiles, UI layouts that adapt to screen size.
- **Data Modes**:
  - Dummy mode: Static test data for consistent testing (weather, notifications, metrics).
  - Real mode: Mock API responses or simulated live data feeds.
- **Monetization Edge Cases**:
  - Free tier: Limited to 1 active virtual instance, basic features.
  - Paid tier: Multiple instances, advanced features, priority support.
- **Rendering & Interaction**: Simulate display output (text, images, layouts), input events.

## Use Cases

### 1. Screen Size Adaptation
- **UC1.1**: Initialize client with 1.5" ePaper (200x200, 1-bit B&W). Verify content scales to fit without overflow.
- **UC1.2**: Switch to 2.8" CYD (320x240, color). Verify UI elements reposition for larger canvas.
- **UC1.3**: 7" display (800x480, high color). Test rich layouts with images and multiple widgets.
- **UC1.4**: Edge case - Invalid size (e.g. 0.5"). Should raise ConfigurationError.
- **UC1.5**: Dynamic resize during runtime, trigger re-layout.

### 2. Configuration Testing
- **UC2.1**: Load device profile from config (resolution, dpi, type: ePaper/LCD).
- **UC2.2**: Validate config against schema (required fields: width, height, color_mode).
- **UC2.3**: Test config overrides for custom themes, fonts, update intervals.
- **UC2.4**: Hot-reload config without restarting simulator.

### 3. Data Modes
- **UC3.1**: Dummy mode - Return predefined datasets (e.g., sample weather: 72°F, sunny; notifications list).
- **UC3.2**: Real data mode - Simulate API calls with realistic latency and variable data.
- **UC3.3**: Toggle between modes at runtime.
- **UC3.4**: Test data validation and fallback (invalid real data -> dummy).

### 4. Monetization and Licensing
- **UC4.1**: Free tier - Create 1 instance successfully; 2nd instance raises TierLimitError ("Free tier limited to 1 instance").
- **UC4.2**: Paid tier - Support unlimited instances.
- **UC4.3**: Check feature flags based on tier (e.g., advanced analytics only for paid).
- **UC4.4**: Trial mode edge case, expiration simulation.
- **UC4.5**: License key validation (mock).

### 5. Rendering and Display Simulation
- **UC5.1**: Render text, shapes, bitmaps to virtual framebuffer.
- **UC5.2**: Simulate ePaper refresh (slow, partial updates).
- **UC5.3**: Generate ASCII/ANSI preview or PIL image output for visual verification.
- **UC5.4**: Test for content clipping, font scaling across sizes.

### 6. Interaction and Events
- **UC6.1**: Simulate button presses (next/prev, select).
- **UC6.2**: Touch events for larger displays.
- **UC6.3**: Battery level simulation and low-power mode.
- **UC6.4**: Network connectivity simulation (online/offline).

### 7. Integration with CYD POC
- **UC7.1**: Emulate exact CYD specs (ESP32, 2.8" ILI9341 display).
- **UC7.2**: Generate code snippets or data payloads compatible with embedded firmware.
- **UC7.3**: Test end-to-end data flow from simulator to mock device.

## QA Checklist
- [ ] All screen sizes render without errors (1.5", 2.8", 4", 7").
- [ ] Config loading/validation passes for valid/invalid inputs.
- [ ] Dummy mode produces consistent, deterministic output.
- [ ] Real mode simulates latency (50-500ms) and variability.
- [ ] Free tier enforces 1-instance limit strictly.
- [ ] Paid tier allows multiple instances.
- [ ] Layout adaptation works for portrait/landscape.
- [ ] Error handling for edge cases (OOM on small screens, invalid configs).
- [ ] Performance: Simulator initializes < 100ms, renders < 50ms.
- [ ] Test coverage > 85% for core classes.
- [ ] Cross-platform compatibility (Windows, Linux for dev).

## Test Scripts
See `tests/` directory for:
- `test_virtual_client.py`: Unit tests (pytest)
- `test_simulator.py`: Integration and e2e tests
- `run_tests.sh`: Execution script
- `virtual_client_simulator.py`: Main simulator implementation

## TDD Approach Used
1. Wrote failing tests first (red).
2. Implemented minimal code to pass tests (green).
3. Refactored for robustness.

**Next Steps**: Integrate with actual Ramses backend, add visual diff testing for rendered frames.

Last updated: July 2026 (Sprint 1 POC)
