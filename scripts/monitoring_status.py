import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'Monitoring'))

from Monitoring.hardware import CHardwareInfo

def get_monitoring_status():
    # Enable all switches for full info
    hw = CHardwareInfo(switchCPU=True, switchGPU=True, switchHDD=False, switchRAM=True, switchVRAM=True)
    status = hw.getStatus()
    # Format for display (first GPU only)
    gpu = status['gpus'][0] if status['gpus'] else {}
    gpu_util = gpu.get('gpu_utilization', None)
    vram_percent = gpu.get('vram_used_percent', None)
    try:
        vram_percent = round(float(vram_percent), 1)
    except (ValueError, TypeError):
        vram_percent = None

    # Improved feedback
    if gpu_util in (-1, None):
        gpu_str = "GPU: No NVIDIA GPU found"
    else:
        gpu_str = f"GPU: {gpu_util}%"

    if vram_percent in (-1, None):
        vram_str = "VRAM: N/A"
    else:
        vram_str = f"VRAM: {vram_percent}%"

    cpu_str = f"CPU: {status.get('cpu_utilization', '-')}%"
    ram_str = f"RAM: {status.get('ram_used_percent', '-')}%"
    return f"{gpu_str} | {vram_str} | {cpu_str} | {ram_str}"

if __name__ == "__main__":
    print(get_monitoring_status())
