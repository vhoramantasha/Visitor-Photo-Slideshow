#!/usr/bin/env python3
"""
Test Suite Runner for Visitor Photo Slideshow
Discovers and executes all unit, integration, security, and concurrency tests.
"""
import sys
import unittest
import time

def run():
    print("=" * 70)
    print("  RUNNING VISITOR PHOTO SLIDESHOW TEST SUITE")
    print("=" * 70)

    start_time = time.time()
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir="tests", pattern="test_*.py")

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    duration = time.time() - start_time
    print("=" * 70)
    print(f"  Tests run: {result.testsRun}")
    print(f"  Failures:  {len(result.failures)}")
    print(f"  Errors:    {len(result.errors)}")
    print(f"  Duration:  {duration:.2f} seconds")
    print("=" * 70)

    if result.wasSuccessful():
        print("  RESULT: ALL TESTS PASSED SUCCESSFULLY! [OK]")
        sys.exit(0)
    else:
        print("  RESULT: TEST SUITE FAILED.")
        sys.exit(1)

if __name__ == "__main__":
    run()
