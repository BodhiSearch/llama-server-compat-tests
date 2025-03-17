import platform
import psutil
from datetime import datetime
import subprocess
import sys
import re
import ctypes
import struct


def get_cpu_features_linux():
  """Get CPU features on Linux using /proc/cpuinfo."""
  try:
    with open("/proc/cpuinfo", "r") as f:
      for line in f:
        if line.startswith("flags"):
          return line.split(":")[1].strip().split()
  except Exception:
    return None


def get_cpu_features_windows():
  """Get CPU features on Windows using CPUID instruction."""
  try:
    import cpuid

    features = set()

    # Get CPU vendor
    info = cpuid.CPUID(0)
    vendor = struct.pack("III", info[1], info[3], info[2]).decode("utf-8")

    # Get features
    info = cpuid.CPUID(1)
    if info[3] & (1 << 20):
      features.add("SSE4.2")
    if info[3] & (1 << 28):
      features.add("AVX")
    if info[3] & (1 << 29):
      features.add("F16C")
    if info[3] & (1 << 12):
      features.add("FMA")

    # Get extended features
    info = cpuid.CPUID(7)
    if info[1] & (1 << 5):
      features.add("AVX2")
    if info[1] & (1 << 16):
      features.add("AVX512F")
    if info[1] & (1 << 30):
      features.add("AVX512BW")
    if info[1] & (1 << 28):
      features.add("AVX512CD")
    if info[1] & (1 << 17):
      features.add("AVX512DQ")
    if info[1] & (1 << 31):
      features.add("AVX512VL")
    if info[2] & (1 << 1):
      features.add("AVX512VBMI")
    if info[2] & (1 << 11):
      features.add("AVX512VNNI")
    if info[2] & (1 << 5):
      features.add("AVX512_BF16")
    if info[3] & (1 << 24):
      features.add("AMX_TILE")
    if info[3] & (1 << 25):
      features.add("AMX_INT8")
    if info[3] & (1 << 22):
      features.add("AMX_BF16")

    return list(features)
  except Exception:
    return None


def get_cpu_features_darwin():
  """Get CPU features on macOS using sysctl."""
  try:
    result = subprocess.run(["sysctl", "-a"], capture_output=True, text=True)
    features = set()

    for line in result.stdout.split("\n"):
      if "hw.optional." in line:
        feature = line.split(":")[0].replace("hw.optional.", "").strip()
        value = line.split(":")[1].strip()
        if value == "1":
          features.add(feature)

    # Map macOS feature names to our standardized names
    feature_map = {"avx1_0": "AVX", "avx2_0": "AVX2", "sse4_2": "SSE4.2", "fma": "FMA", "f16c": "F16C"}

    return [feature_map.get(f, f) for f in features if f in feature_map]
  except Exception:
    return None


def get_cpu_features():
  """Get CPU features using platform-specific methods."""
  os_type = platform.system()

  if os_type == "Linux":
    return get_cpu_features_linux()
  elif os_type == "Windows":
    return get_cpu_features_windows()
  elif os_type == "Darwin":
    return get_cpu_features_darwin()
  return None


def determine_cpu_variant():
  """Determine which binary variant is suitable for this CPU."""
  features = set(get_cpu_features() or [])

  # Define feature requirements for each variant
  variants = {
    "llama-sapphirerapids": {
      "required": {
        "AVX",
        "F16C",
        "AVX2",
        "FMA",
        "AVX512F",
        "AVX512BW",
        "AVX512CD",
        "AVX512DQ",
        "AVX512VL",
        "AVX512VBMI",
        "AVX512VNNI",
        "AVX512_BF16",
        "AMX_TILE",
        "AMX_INT8",
        "AMX_BF16",
      },
      "description": "Sapphire Rapids",
    },
    "llama-zen4": {
      "required": {"AVX", "F16C", "AVX2", "FMA", "AVX512F"},
      "description": "AMD Zen 4 (Ryzen 7000 series)",
    },
    "llama-icelake": {
      "required": {
        "AVX",
        "F16C",
        "AVX2",
        "FMA",
        "AVX512F",
        "AVX512BW",
        "AVX512CD",
        "AVX512DQ",
        "AVX512VL",
        "AVX512VBMI",
        "AVX512VNNI",
      },
      "description": "Ice Lake, Tiger Lake",
    },
    "llama-skylakex": {
      "required": {"AVX", "F16C", "AVX2", "FMA", "AVX512F", "AVX512BW", "AVX512CD", "AVX512DQ", "AVX512VL"},
      "description": "Skylake-X, Cascade Lake, Cooper Lake",
    },
    "llama-alderlake": {
      "required": {"AVX", "F16C", "AVX2", "FMA", "AVX_VNNI"},
      "description": "Alder Lake, Raptor Lake",
    },
    "llama-haswell": {
      "required": {"AVX", "F16C", "AVX2", "FMA"},
      "description": "Haswell, Broadwell, Skylake (non-X), Zen 1-3",
    },
    "llama-sandybridge": {"required": {"AVX"}, "description": "Sandy Bridge, Ivy Bridge"},
    "llama-sse42": {"required": {"SSE4.2"}, "description": "Core 2, Nehalem, early AMD"},
    "llama-generic": {"required": set(), "description": "Any x86-64 CPU"},
  }

  # Find the most optimized variant that this CPU supports
  for variant, info in variants.items():
    if features.issuperset(info["required"]):
      return {
        "variant": variant,
        "description": info["description"],
        "supported_features": sorted(features),
        "required_features": sorted(info["required"]),
        "additional_features": sorted(features - info["required"]),
      }

  return {
    "variant": "llama-generic",
    "description": "Any x86-64 CPU",
    "supported_features": sorted(features),
    "required_features": [],
    "additional_features": sorted(features),
  }


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
    "features": get_cpu_features() or [],
    "optimal_binary": determine_cpu_variant(),
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

  # CPU Features and Optimal Binary
  optimal_binary = cpu_info.get("optimal_binary", {})
  if optimal_binary:
    lines.append("\nCPU Features and Optimization:")
    lines.append("-" * 40)
    lines.append(f"Optimal Binary: {optimal_binary['variant']}")
    lines.append(f"CPU Class: {optimal_binary['description']}")
    if optimal_binary["supported_features"]:
      lines.append("\nSupported CPU Features:")
      for feature in optimal_binary["supported_features"]:
        lines.append(f"  - {feature}")
    if optimal_binary["required_features"]:
      lines.append("\nRequired Features for Selected Binary:")
      for feature in optimal_binary["required_features"]:
        lines.append(f"  - {feature}")
    if optimal_binary["additional_features"]:
      lines.append("\nAdditional Available Features:")
      for feature in optimal_binary["additional_features"]:
        lines.append(f"  - {feature}")

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
