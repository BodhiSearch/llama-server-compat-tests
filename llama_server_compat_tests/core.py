"""
Core functionality for LLaMA server compatibility testing.
"""


class LLaMAServerTestSuite:
  """
  Main test suite class for LLaMA server compatibility testing.
  This is a placeholder class to make the package installable.
  The actual testing functionality is implemented in the tests directory.
  """

  def __init__(self):
    self.name = "LLaMA Server Compatibility Tests"
    self.description = "Test suite for validating LLaMA server implementations"

  def get_info(self) -> dict:
    """Return basic information about the test suite."""
    return {"name": self.name, "description": self.description, "version": "0.1.0"}

  def __str__(self) -> str:
    return f"{self.name} - {self.description}"
