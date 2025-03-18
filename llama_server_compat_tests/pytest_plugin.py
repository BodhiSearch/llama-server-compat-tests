"""
Pytest plugin for tracking test execution times.
"""
from datetime import datetime
import pytest


class TimingPlugin:
  """Plugin to track test execution times."""

  def __init__(self):
    self.test_starts = {}
    self.test_ends = {}
    self.suite_start = None
    self.suite_end = None

  def pytest_sessionstart(self, session):
    """Called before test session starts."""
    self.suite_start = datetime.now()

  def pytest_sessionfinish(self, session):
    """Called after whole test run finished."""
    self.suite_end = datetime.now()

  def pytest_runtest_logstart(self, nodeid, location):
    """Called at the start of running the runtest protocol for a single test item."""
    self.test_starts[nodeid] = datetime.now()

  def pytest_runtest_logfinish(self, nodeid, location):
    """Called at the end of running the runtest protocol for a single test item."""
    self.test_ends[nodeid] = datetime.now()

  def pytest_terminal_summary(self, terminalreporter):
    """Add timing information to terminal summary."""
    if not self.suite_start or not self.suite_end:
      return

    tr = terminalreporter
    tr.section("Test Execution Times")
    
    # Overall suite timing
    suite_duration = self.suite_end - self.suite_start
    tr.write_line(f"\nTest Suite:")
    tr.write_line(f"  Started:  {self.suite_start.strftime('%Y-%m-%d %H:%M:%S')}")
    tr.write_line(f"  Finished: {self.suite_end.strftime('%Y-%m-%d %H:%M:%S')}")
    tr.write_line(f"  Duration: {suite_duration}")
    
    # Individual test timings
    tr.write_line("\nIndividual Test Timings:")
    for nodeid in sorted(self.test_starts.keys()):
      if nodeid in self.test_ends:
        start = self.test_starts[nodeid]
        end = self.test_ends[nodeid]
        duration = end - start
        tr.write_line(f"  {nodeid}:")
        tr.write_line(f"    Started:  {start.strftime('%Y-%m-%d %H:%M:%S')}")
        tr.write_line(f"    Finished: {end.strftime('%Y-%m-%d %H:%M:%S')}")
        tr.write_line(f"    Duration: {duration}")


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
  """Register the timing plugin."""
  timing_plugin = TimingPlugin()
  config.pluginmanager.register(timing_plugin, "timing_plugin") 