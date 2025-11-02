import torch

def check_gpu_availability():
    """
    GPU 가속 가능 여부를 확인하고, 디바이스 정보를 반환합니다.
    
    Returns:
        dict: {
            'gpu_available': bool,  # GPU 사용 가능 여부
            'device_type': str,     # 'cuda' (NVIDIA), 'hip' (AMD ROCm), 또는 'cpu'
            'recommended_device': str,  # 추천 디바이스 ('cuda' 또는 'cpu')
            'details': str          # 추가 정보
        }
    """
    try:
        if torch.cuda.is_available():
            # ROCm-enabled PyTorch builds remap torch.cuda to use HIP backend,
            # but PyTorch itself exposes it as 'cuda'.
            device_type = 'cuda'
            recommended_device = 'cuda'
            details = f"AMD ROCm GPU 감지됨. 디바이스 수: {torch.cuda.device_count()}"
        else:
            device_type = 'cpu'
            recommended_device = 'cpu'
            details = "GPU 미감지. CPU 모드로 실행."
        
        gpu_available = device_type != 'cpu'
        
        return {
            'gpu_available': gpu_available,
            'device_type': device_type,
            'recommended_device': recommended_device,
            'details': details
        }
    except ImportError:
        return {
            'gpu_available': False,
            'device_type': 'cpu',
            'recommended_device': 'cpu',
            'details': "PyTorch가 설치되지 않음. CPU 모드로 실행."
        }

def get_device():
    """
    추천 디바이스를 torch.device 객체로 반환합니다.
    
    Returns:
        torch.device: 추천 디바이스 객체.
    """
    gpu_info = check_gpu_availability()
    return torch.device(gpu_info['recommended_device'])