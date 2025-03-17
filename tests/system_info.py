import platform
import psutil
from datetime import datetime
import subprocess
import sys


def get_cpu_info():
  """Get CPU information using psutil and platform."""
  info = {
    "physical_cores": psutil.cpu_count(logical=False),
    "total_cores": psutil.cpu_count(logical=True),
    "max_frequency": psutil.cpu_freq().max if psutil.cpu_freq() else None,
    "current_frequency": psutil.cpu_freq().current if psutil.cpu_freq() else None,
    "cpu_usage_per_core": [percentage for percentage in psutil.cpu_percent(percpu=True)],
    "total_cpu_usage": psutil.cpu_percent(),
    "architecture": platform.machine(),
    "processor": platform.processor(),
    "cpu_brand": platform.processor(),
  }
  return info


def get_memory_info():
  """Get RAM information using psutil."""
  virtual_mem = psutil.virtual_memory()
  swap = psutil.swap_memory()

  return {
    "total": virtual_mem.total,
    "available": virtual_mem.available,
    "used": virtual_mem.used,
    "percentage": virtual_mem.percent,
    "swap_total": swap.total,
    "swap_used": swap.used,
    "swap_free": swap.free,
    "swap_percentage": swap.percent,
  }


def safe_run_command(command):
  """Safely run a command and return its output."""
  try:
    result = subprocess.run(command, capture_output=True, text=True, timeout=5)
    return result.stdout.strip() if result.returncode == 0 else None
  except (subprocess.SubprocessError, OSError):
    return None


def get_gpu_info():
  """
  Get basic GPU information using platform-agnostic methods.
  This function tries different approaches and returns what it can find.
  """
  gpu_info = {"detected_gpus": []}

  # macOS
  if platform.system() == "Darwin":
    system_profiler = safe_run_command(["system_profiler", "SPDisplaysDataType"])
    if system_profiler:
      gpu_info["raw_info"] = system_profiler
      # Basic parsing of system_profiler output
      for line in system_profiler.split("\n"):
        if "Chipset Model:" in line:
          gpu_info["detected_gpus"].append({"name": line.split(":")[1].strip()})

  # Linux
  elif platform.system() == "Linux":
    # Try lspci for graphics cards
    lspci = safe_run_command(["lspci", "-v"])
    if lspci:
      gpu_info["raw_info"] = lspci
      # Look for VGA and 3D controllers
      vga_devices = [line for line in lspci.split("\n") if "VGA" in line or "3D" in line]
      for device in vga_devices:
        gpu_info["detected_gpus"].append({"name": device.split(":")[-1].strip()})

  # Windows
  elif platform.system() == "Windows":
    wmic = safe_run_command(["wmic", "path", "win32_VideoController", "get", "name"])
    if wmic:
      gpu_info["raw_info"] = wmic
      # Parse WMIC output (skip header)
      gpu_names = [line.strip() for line in wmic.split("\n")[1:] if line.strip()]
      for name in gpu_names:
        gpu_info["detected_gpus"].append({"name": name})

  return gpu_info


def get_system_info():
  """Get comprehensive system information using cross-platform methods."""
  system_info = {
    "timestamp": datetime.now().isoformat(),
    "platform": {
      "system": platform.system(),
      "release": platform.release(),
      "version": platform.version(),
      "machine": platform.machine(),
      "processor": platform.processor(),
      "python_version": sys.version,
    },
    "cpu": get_cpu_info(),
    "memory": get_memory_info(),
    "gpu": get_gpu_info(),
  }

  return system_info


def format_bytes(bytes_value):
  """Format bytes into human readable format."""
  for unit in ["B", "KB", "MB", "GB", "TB"]:
    if bytes_value < 1024:
      return f"{bytes_value:.2f} {unit}"
    bytes_value /= 1024
  return f"{bytes_value:.2f} PB"


def format_system_info():
  """Format system information as human-readable text."""
  info = get_system_info()
  lines = []

  # Header
  lines.append("=" * 80)
  lines.append("SYSTEM INFORMATION")
  lines.append("=" * 80)

  # Platform Information
  lines.append("\nPLATFORM:")
  lines.append("-" * 40)
  platform_info = info["platform"]
  lines.append(f"OS: {platform_info['system']} {platform_info['release']}")
  lines.append(f"Version: {platform_info['version']}")
  lines.append(f"Architecture: {platform_info['machine']}")
  lines.append(f"Python Version: {platform_info['python_version'].split()[0]}")

  # CPU Information
  lines.append("\nCPU:")
  lines.append("-" * 40)
  cpu_info = info["cpu"]
  lines.append(f"Processor: {cpu_info['processor']}")
  lines.append(f"Physical Cores: {cpu_info['physical_cores']}")
  lines.append(f"Total Cores: {cpu_info['total_cores']}")
  if cpu_info["max_frequency"]:
    lines.append(f"Max Frequency: {cpu_info['max_frequency']:.2f} MHz")
  lines.append(f"Current CPU Usage: {cpu_info['total_cpu_usage']:.1f}%")

  # Memory Information
  lines.append("\nMEMORY:")
  lines.append("-" * 40)
  memory_info = info["memory"]
  lines.append(f"Total RAM: {format_bytes(memory_info['total'])}")
  lines.append(f"Available RAM: {format_bytes(memory_info['available'])}")
  lines.append(f"Used RAM: {format_bytes(memory_info['used'])} ({memory_info['percentage']:.1f}%)")
  lines.append(f"Swap Total: {format_bytes(memory_info['swap_total'])}")
  lines.append(f"Swap Used: {format_bytes(memory_info['swap_used'])} ({memory_info['swap_percentage']:.1f}%)")

  # GPU Information
  lines.append("\nGPU:")
  lines.append("-" * 40)
  gpu_info = info["gpu"]
  if gpu_info["detected_gpus"]:
    for i, gpu in enumerate(gpu_info["detected_gpus"], 1):
      lines.append(f"GPU {i}: {gpu['name']}")
  else:
    lines.append("No GPUs detected")

  # Footer
  lines.append("\n" + "=" * 80 + "\n")

  return "\n".join(lines)
