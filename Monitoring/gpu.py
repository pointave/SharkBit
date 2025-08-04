import torch
import pynvml
from Monitoring.core import logger
# from ctypes import *
# from pyrsmi import rocml

class CGPUInfo:
    """
    This class is responsible for getting information from GPU (ONLY).
    """
    cuda = False
    pynvmlLoaded = False
    # pyamdLoaded = False
    # anygpuLoaded = False
    cudaAvailable = False
    torchDevice = 'cpu'
    cudaDevice = 'cpu'
    cudaDevicesFound = 0
    switchGPU = True
    switchVRAM = True
    switchTemperature = True
    gpus = []
    gpusUtilization = []
    gpusVRAM = []
    gpusTemperature = []

    def __init__(self):
        try:
            pynvml.nvmlInit()
            self.pynvmlLoaded = True
        except Exception as e:
            logger.error(f'Could not init pynvml: {e}')
            self.pynvmlLoaded = False

        # if not self.pynvmlLoaded:
        #     try:
        #         rocml.smi_initialize()
        #         self.pyamdLoaded = True
        #         logger.info('Pyrsmi (AMD) initialized.')
        #     except Exception as e:
        #         logger.error('Could not init pyrsmi (AMD).' + str(e))

        # self.anygpuLoaded = self.pynvmlLoaded or self.pyamdLoaded
        self.anygpuLoaded = self.pynvmlLoaded

        try:
            torch_available = torch.cuda.is_available()
            torch_count = torch.cuda.device_count()
            self.torchDevice = 'cuda' if torch_available else 'cpu'
        except Exception as e:
            logger.error(f'Could not check torch.cuda: {e}')
            self.torchDevice = 'cpu'

        # ZLUDA Check, self.torchDevice has 'ZLUDA' in it.
        if 'zluda' in self.torchDevice or 'ZLUDA' in self.torchDevice or 'Zluda' in self.torchDevice:
            logger.warn('ZLUDA detected. GPU monitoring will be disabled.')
            self.anygpuLoaded = False
            # self.pyamdLoaded = False
            self.pynvmlLoaded = False

        if self.anygpuLoaded and self.deviceGetCount() > 0:
            self.cudaDevicesFound = self.deviceGetCount()

            logger.info(f"GPU/s:")

            # for simulate multiple GPUs (for testing) interchange these comments:
            # for deviceIndex in range(3):
            #     deviceHandle = pynvml.nvmlDeviceGetHandleByIndex(0)
            for deviceIndex in range(self.cudaDevicesFound):
                deviceHandle = self.deviceGetHandleByIndex(deviceIndex)

                gpuName = self.deviceGetName(deviceHandle, deviceIndex)

                logger.info(f"{deviceIndex}) {gpuName}")

                self.gpus.append({
                    'index': deviceIndex,
                    'name': gpuName,
                })

                # same index as gpus, with default values
                self.gpusUtilization.append(True)
                self.gpusVRAM.append(True)
                self.gpusTemperature.append(True)

            self.cuda = True
            logger.info(f"Driver version: {self.systemGetDriverVersion()}")
        else:
            logger.info('No GPU with CUDA detected.')

        self.cudaDevice = 'cpu' if self.torchDevice == 'cpu' else 'cuda'
        self.cudaAvailable = torch.cuda.is_available()

        if self.cuda and self.cudaAvailable and self.torchDevice == 'cpu':
            logger.info('CUDA is available, but torch is using CPU.')

    def getInfo(self):
        logger.debug('Getting GPUs info...')
        return self.gpus

    def getStatus(self):
        # logger.debug('CGPUInfo getStatus')
        gpuUtilization = -1
        gpuTemperature = -1
        vramUsed = -1
        vramTotal = -1
        vramPercent = -1

        gpuType = ''
        gpus = []

        # Use pynvml if available and GPU detected, regardless of PyTorch CUDA status
        if self.anygpuLoaded and self.cuda and self.cudaDevicesFound > 0:
            gpuType = 'cuda'  # Use 'cuda' even if PyTorch doesn't detect it
            
            # for simulate multiple GPUs (for testing) interchange these comments:
            # for deviceIndex in range(3):
            #     deviceHandle = self.deviceGetHandleByIndex(0)
            for deviceIndex in range(self.cudaDevicesFound):
                deviceHandle = self.deviceGetHandleByIndex(deviceIndex)

                gpuUtilization = -1
                vramPercent = -1
                vramUsed = -1
                vramTotal = -1
                gpuTemperature = -1

                # GPU Utilization
                if self.switchGPU and self.gpusUtilization[deviceIndex]:
                    try:
                        gpuUtilization = self.deviceGetUtilizationRates(deviceHandle)
                    except Exception as e:
                        if str(e) == "Unknown Error":
                            logger.error('For some reason, pynvml is not working in a laptop with only battery, try to connect and turn on the monitor')
                        else:
                            logger.error('Could not get GPU utilization.' + str(e))

                        logger.error('Monitor of GPU is turning off (not on UI!)')
                        self.switchGPU = False

                # VRAM
                if self.switchVRAM and self.gpusVRAM[deviceIndex]:
                    # Torch or pynvml?, pynvml is more accurate with the system, torch is more accurate with comfyUI
                    memory = self.deviceGetMemoryInfo(deviceHandle)
                    vramUsed = memory['used']
                    vramTotal = memory['total']

                    # device = torch.device(gpuType)
                    # vramUsed = torch.cuda.memory_allocated(device)
                    # vramTotal = torch.cuda.get_device_properties(device).total_memory

                    # check if vramTotal is not zero or None
                    if vramTotal and vramTotal != 0:
                        vramPercent = vramUsed / vramTotal * 100

                # Temperature
                if self.switchTemperature and self.gpusTemperature[deviceIndex]:
                    try:
                        gpuTemperature = self.deviceGetTemperature(deviceHandle)
                    except Exception as e:
                        logger.error('Could not get GPU temperature. Turning off this feature. ' + str(e))
                        self.switchTemperature = False

                gpus.append({
                    'gpu_utilization': gpuUtilization,
                    'gpu_temperature': gpuTemperature,
                    'vram_total': vramTotal,
                    'vram_used': vramUsed,
                    'vram_used_percent': vramPercent,
                })
        else:
            # Fallback to CPU if no GPU detected
            gpuType = 'cpu'
            gpus.append({
                'gpu_utilization': -1,
                'gpu_temperature': -1,
                'vram_total': -1,
                'vram_used': -1,
                'vram_used_percent': -1,
            })

        return {
            'device_type': gpuType,
            'gpus': gpus,
        }

    def deviceGetCount(self):
        if self.pynvmlLoaded:
            return pynvml.nvmlDeviceGetCount()
        # elif self.pyamdLoaded:
        #     return rocml.smi_get_device_count()
        else:
            return 0

    def deviceGetHandleByIndex(self, index):
        if self.pynvmlLoaded:
            return pynvml.nvmlDeviceGetHandleByIndex(index)
        # elif self.pyamdLoaded:
        #     return index
        else:
            return 0

    def deviceGetName(self, deviceHandle, deviceIndex):
        if self.pynvmlLoaded:
            gpuName = 'Unknown GPU'

            try:
                gpuName = pynvml.nvmlDeviceGetName(deviceHandle)
                try:
                    gpuName = gpuName.decode('utf-8', errors='ignore')
                except AttributeError as e:
                    pass

            except UnicodeDecodeError as e:
                gpuName = 'Unknown GPU (decoding error)'
                print(f"UnicodeDecodeError: {e}")

            return gpuName
        # elif self.pyamdLoaded:
        #     return rocml.smi_get_device_name(deviceIndex)
        else:
            return ''

    def systemGetDriverVersion(self):
        if self.pynvmlLoaded:
            return f'NVIDIA Driver: {pynvml.nvmlSystemGetDriverVersion()}'
        # elif self.pyamdLoaded:
        #     ver_str = create_string_buffer(256)
        #     rocml.rocm_lib.rsmi_version_str_get(0, ver_str, 256)
        #     return f'AMD Driver: {ver_str.value.decode()}'
        else:
            return 'Driver unknown'

    def deviceGetUtilizationRates(self, deviceHandle):
        if self.pynvmlLoaded:
            return pynvml.nvmlDeviceGetUtilizationRates(deviceHandle).gpu
        # elif self.pyamdLoaded:
        #     return rocml.smi_get_device_utilization(deviceHandle)
        else:
            return 0

    def deviceGetMemoryInfo(self, deviceHandle):
        if self.pynvmlLoaded:
            mem = pynvml.nvmlDeviceGetMemoryInfo(deviceHandle)
            return {'total': mem.total, 'used': mem.used}
        # elif self.pyamdLoaded:
        #     mem_used = rocml.smi_get_device_memory_used(deviceHandle)
        #     mem_total = rocml.smi_get_device_memory_total(deviceHandle)
        #     return {'total': mem_total, 'used': mem_used}
        else:
            return {'total': 1, 'used': 1}

    def deviceGetTemperature(self, deviceHandle):
        if self.pynvmlLoaded:
            return pynvml.nvmlDeviceGetTemperature(deviceHandle, pynvml.NVML_TEMPERATURE_GPU)
        # elif self.pyamdLoaded:
        #     temp = c_int64(0)
        #     rocml.rocm_lib.rsmi_dev_temp_metric_get(deviceHandle, 1, 0, byref(temp))
        #     return temp.value / 1000
        else:
            return 0
