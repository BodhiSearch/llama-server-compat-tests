import platform
import psutil
from datetime import datetime
import subprocess
import sys
import re
import ctypes
import struct
import warnings


def get_cpu_features_linux():
  """Get CPU features on Linux using /proc/cpuinfo."""
  try:
    with open("/proc/cpuinfo", "r") as f:
      raw_info = f.read()
      for line in raw_info.split("\n"):
        if line.startswith("flags"):
          flags = line.split(":")[1].strip().split()
          features = set()

          # Map CPU flags to our feature set
          flag_map = {
            "sse4_2": "SSE4.2",
            "avx": "AVX",
            "avx2": "AVX2",
            "fma": "FMA",
            "f16c": "F16C",
            "avx512f": "AVX512F",
            "avx512bw": "AVX512BW",
            "avx512cd": "AVX512CD",
            "avx512dq": "AVX512DQ",
            "avx512vl": "AVX512VL",
            "avx512vbmi": "AVX512VBMI",
            "avx512vnni": "AVX512VNNI",
            "avx512_bf16": "AVX512_BF16",
            "amx_tile": "AMX_TILE",
            "amx_int8": "AMX_INT8",
            "amx_bf16": "AMX_BF16",
            "avx_vnni": "AVX_VNNI",
          }

          for flag in flags:
            if flag in flag_map:
              features.add(flag_map[flag])

          if not features:
            warnings.warn("No CPU features detected in /proc/cpuinfo flags")
          return sorted(features), raw_info
  except Exception as e:
    warnings.warn(f"Failed to read CPU features from /proc/cpuinfo: {str(e)}")
    return None, None


def get_cpu_features_windows():
  """Get CPU features on Windows using wmic."""
  try:
    result = subprocess.run(
      ["wmic", "cpu", "get", "Caption,Name,ProcessorId,Manufacturer"], capture_output=True, text=True, timeout=5
    )

    if result.returncode == 0:
      features = set()
      raw_info = result.stdout
      cpu_info = raw_info.lower()

      # Intel processors
      if "intel" in cpu_info:
        if any(x in cpu_info for x in ["sapphire rapids", "spr"]):
          features.update(
            [
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
            ]
          )
        elif any(x in cpu_info for x in ["ice lake", "tiger lake"]):
          features.update(
            [
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
            ]
          )
        elif any(x in cpu_info for x in ["skylake-x", "cascade lake", "cooper lake"]):
          features.update(["AVX", "F16C", "AVX2", "FMA", "AVX512F", "AVX512BW", "AVX512CD", "AVX512DQ", "AVX512VL"])
        elif any(x in cpu_info for x in ["alder lake", "raptor lake"]):
          features.update(["AVX", "F16C", "AVX2", "FMA", "AVX_VNNI"])
        elif any(x in cpu_info for x in ["haswell", "broadwell", "skylake"]):
          features.update(["AVX", "F16C", "AVX2", "FMA"])
        elif any(x in cpu_info for x in ["sandy bridge", "ivy bridge"]):
          features.add("AVX")
        elif any(x in cpu_info for x in ["nehalem", "westmere"]):
          features.add("SSE4.2")
        else:
          warnings.warn(f"Unknown Intel CPU model: {cpu_info}")

      # AMD processors
      elif "amd" in cpu_info:
        if "ryzen" in cpu_info and any(x in cpu_info for x in ["7000", "zen4"]):
          features.update(["AVX", "F16C", "AVX2", "FMA", "AVX512F"])
        elif any(x in cpu_info for x in ["zen", "ryzen"]):
          features.update(["AVX", "F16C", "AVX2", "FMA"])
        else:
          warnings.warn(f"Unknown AMD CPU model: {cpu_info}")
      else:
        warnings.warn(f"Unknown CPU manufacturer: {cpu_info}")

      if not features:
        warnings.warn("No CPU features detected from CPU model information")
      return sorted(features), raw_info
    else:
      warnings.warn("Failed to get CPU information using wmic command")
      return None, None
  except Exception as e:
    warnings.warn(f"Failed to detect CPU features on Windows: {str(e)}")
    return None, None


def get_cpu_features_darwin():
  """Get CPU features on macOS using sysctl."""
  try:
    result = subprocess.run(["sysctl", "-a"], capture_output=True, text=True)
    features = set()

    if result.returncode == 0:
      raw_info = result.stdout
      # Map macOS feature names to our standardized names
      feature_map = {
        "hw.optional.avx1_0": "AVX",
        "hw.optional.avx2_0": "AVX2",
        "hw.optional.sse4_2": "SSE4.2",
        "hw.optional.fma": "FMA",
        "hw.optional.f16c": "F16C",
      }

      for line in raw_info.split("\n"):
        for macos_feature, std_feature in feature_map.items():
          if macos_feature in line and line.strip().endswith("1"):
            features.add(std_feature)

      # For Apple Silicon, we might want to add equivalent features
      if "hw.optional.arm" in raw_info:
        features.update(["NEON", "FMA"])  # ARM equivalent features

      if not features:
        warnings.warn("No CPU features detected from sysctl output")
      return sorted(features), raw_info
    else:
      warnings.warn("Failed to get CPU information using sysctl command")
      return None, None
  except Exception as e:
    warnings.warn(f"Failed to detect CPU features on macOS: {str(e)}")
    return None, None


def get_cpu_features():
  """Get CPU features using platform-specific methods."""
  os_type = platform.system()

  if os_type == "Linux":
    features, raw_info = get_cpu_features_linux()
  elif os_type == "Windows":
    features, raw_info = get_cpu_features_windows()
  elif os_type == "Darwin":
    features, raw_info = get_cpu_features_darwin()
  else:
    warnings.warn(f"Unsupported operating system: {os_type}")
    return None, None

  return features, raw_info


def determine_cpu_variant():
  """Determine which binary variant is suitable for this CPU."""
  features = set(get_cpu_features()[0] or [])

  if not features:
    warnings.warn("No CPU features detected, cannot determine optimal binary variant")
    return None

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

  warnings.warn("CPU does not meet minimum requirements for any optimized binary variant")
  return None


def get_cpu_info():
  """Get CPU information using psutil and platform."""
  features, raw_info = get_cpu_features()

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
    "features": features or [],
    "raw_info": raw_info,
    "optimal_binary": determine_cpu_variant() if features else None,
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

  # Raw CPU Information
  if cpu_info.get("raw_info"):
    lines.append("\nRaw CPU Information:")
    lines.append("-" * 40)
    # Format raw info for better readability
    raw_lines = cpu_info["raw_info"].strip().split("\n")
    for line in raw_lines:
      if line.strip():  # Skip empty lines
        lines.append(line.rstrip())

  # CPU Features and Optimal Binary
  optimal_binary = cpu_info.get("optimal_binary")
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
  else:
    lines.append("\nWARNING: Could not determine optimal binary variant")
    if cpu_info["features"]:
      lines.append("\nDetected CPU Features:")
      for feature in sorted(cpu_info["features"]):
        lines.append(f"  - {feature}")
    else:
      lines.append("No CPU features detected")

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
  if gpu_info.get("raw_info"):
    lines.append("Raw GPU Information:")
    for line in gpu_info["raw_info"].strip().split("\n"):
      if line.strip():  # Skip empty lines
        lines.append(line.rstrip())
    lines.append("")

  if gpu_info["detected_gpus"]:
    lines.append("Detected GPUs:")
    for i, gpu in enumerate(gpu_info["detected_gpus"], 1):
      lines.append(f"GPU {i}: {gpu['name']}")
  else:
    lines.append("No GPUs detected")

  # Footer
  lines.append("\n" + "=" * 80 + "\n")

  return "\n".join(lines)
