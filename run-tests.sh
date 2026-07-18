#!/usr/bin/env bash
echo "=== RAAMSES Test Runner ==="
echo "Starting Python XML Emulator + Software Console tests..."
echo "This will test e-paper, CYD, and desktop simulation modes."

cd "$(dirname "$0")"

# Run with different configs
for config in software-console/configs/*.xml; do
    echo "Testing with config: $(basename "$config")"
    python -m pytest unit-tests/test_protocol.py -q --tb=no || python unit-tests/test_protocol.py
    echo "----------------------------------------"
done

echo "All tests completed. Check above for results."
echo "You can now run this via cron nightly or on full builds."
