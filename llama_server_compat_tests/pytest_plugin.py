"""
Pytest plugin for tracking test execution times.
"""

from datetime import datetime
import pytest


class TimingPlugin:
  """Plugin to track test execution times."""

  def __init__(self):
    self.test_starts = {}
    self.suite_start = None
    self.suite_end = None

  def pytest_sessionstart(self, session):
    """Called before test session starts."""
    self.suite_start = datetime.now()
    print("\nTest Suite Started:", self.suite_start.strftime("%Y-%m-%d %H:%M:%S"))

  def pytest_runtest_logstart(self, nodeid, location):
    """Called at the start of running the runtest protocol for a single test item."""
    self.test_starts[nodeid] = datetime.now()

  @pytest.hookimpl(trylast=True)
  def pytest_runtest_logfinish(self, nodeid, location):
    """Called at the end of running the runtest protocol for a single test item."""
    test_end = datetime.now()
    test_start = self.test_starts.get(nodeid)

    if test_start:
      duration = test_end - test_start
      # Print timing information immediately after test
      print(f"\nTest Timing - {nodeid}")
      print(f"  Started:  {test_start.strftime('%Y-%m-%d %H:%M:%S')}")
      print(f"  Finished: {test_end.strftime('%Y-%m-%d %H:%M:%S')}")
      print(f"  Duration: {duration}")

  def pytest_sessionfinish(self, session):
    """Called after whole test run finished."""
    self.suite_end = datetime.now()
    suite_duration = self.suite_end - self.suite_start
    print(f"\nTest Suite Completed:")
    print(f"  Started:  {self.suite_start.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Finished: {self.suite_end.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Duration: {suite_duration}\n")


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
  """Register the timing plugin."""
  timing_plugin = TimingPlugin()
  config.pluginmanager.register(timing_plugin, "timing_plugin")
