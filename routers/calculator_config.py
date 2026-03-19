from fastapi import APIRouter, HTTPException
from supabase import create_client
import os
from datetime import datetime

router = APIRouter(prefix="/api/calculator-config", tags=["Calculator Config"])

# Supabase client
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# Default configs (fallback jika DB kosong)
DEFAULT_CONFIGS = {
    'stan': {
        'year': 2024,
        'skd': {
            'tiu': {'soal': 35, 'bobot_benar': 5, 'max': 175, 'min': 80},
            'twk': {'soal': 30, 'bobot_benar': 5, 'max': 150, 'min': 75},
            'tkp': {'soal': 45, 'bobot_min': 1, 'bobot_max': 5, 'max': 225, 'min': 143},
            'total_max': 550,
            'passing_grade': 308
        }
    },
    'ipdn': {
        'year': 2024,
        'skd': {
            'tiu': {'soal': 35, 'bobot_benar': 5, 'max': 175, 'min': 80},
            'twk': {'soal': 30, 'bobot_benar': 5, 'max': 150, 'min': 75},
            'tkp': {'soal': 45, 'bobot_min': 1, 'bobot_max': 5, 'max': 225, 'min': 143},
            'total_max': 550,
            'passing_grade': 308
        }
    },
    'stis': {
        'year': 2024,
        'skd': {
            'tiu': {'soal': 35, 'bobot_benar': 5, 'max': 175, 'min': 80},
            'twk': {'soal': 30, 'bobot_benar': 5, 'max': 150, 'min': 75},
            'tkp': {'soal': 45, 'bobot_min': 1, 'bobot_max': 5, 'max': 225, 'min': 143},
            'total_max': 550,
            'passing_grade': 308
        },
        'lanjutan_i': {
            'matematika': {
                'soal': 40,
                'bobot_benar': 5,
                'bobot_salah': -1,
                'max': 200,
                'passing_grade_reguler': 65,
                'passing_grade_afirmasi': 55
            }
        }
    },
    'stin': {
        'year': 2024,
        'skd': {
            'tiu': {'soal': 35, 'bobot_benar': 5, 'max': 175, 'min': 80},
            'twk': {'soal': 30, 'bobot_benar': 5, 'max': 150, 'min': 75},
            'tkp': {'soal': 45, 'bobot_min': 1, 'bobot_max': 5, 'max': 225, 'min': 143},
            'total_max': 550,
            'passing_grade': 308
        }
    },
    'stmkg': {
        'year': 2024,
        'skd': {
            'tiu': {'soal': 35, 'bobot_benar': 5, 'max': 175, 'min': 80},
            'twk': {'soal': 30, 'bobot_benar': 5, 'max': 150, 'min': 75},
            'tkp': {'soal': 45, 'bobot_min': 1, 'bobot_max': 5, 'max': 225, 'min': 143},
            'total_max': 550,
            'passing_grade': 308
        }
    },
    'polri': {
        'year': 2024,
        'bobot': {'akademik': 40, 'psikologi': 30, 'kesamaptaan': 30},
        'passing_grade': 70
    },
    'cpns': {
        'year': 2024,
        'skd': {
            'tiu': {'max': 175},
            'twk': {'max': 150},
            'tkp': {'max': 175},
            'total_max': 500,
            'passing_grade': 308
        },
        'bobot_akhir': {'skd': 40, 'skb': 60}
    },
    'tni': {
        'year': 2024,
        'bobot': {'akademik': 30, 'psikologi': 25, 'kesehatan': 20, 'kesamaptaan': 25},
        'passing_grade': 70
    }
}

@router.get("/{calculator_type}")
async def get_calculator_config(calculator_type: str):
    """
    GET active calculator configuration
    Returns: config, year, metadata
    """
    try:
        # Fetch from database
        result = supabase.table('calculator_configs')\
            .select('*')\
            .eq('calculator_type', calculator_type)\
            .eq('is_active', True)\
            .execute()
        
        if result.data and len(result.data) > 0:
            config_data = result.data[0]
            return {
                "success": True,
                "calculator_type": calculator_type,
                "year": config_data['year'],
                "config": config_data['config'],
                "source_url": config_data.get('source_url'),
                "last_updated": config_data.get('updated_at'),
                "verified_by": config_data.get('verified_by'),
                "verified_at": config_data.get('verified_at')
            }
        else:
            # Return default config as fallback
            default = DEFAULT_CONFIGS.get(calculator_type)
            if not default:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Configuration not found for {calculator_type}"
                )
            
            return {
                "success": True,
                "calculator_type": calculator_type,
                "year": default['year'],
                "config": default,
                "source_url": None,
                "last_updated": None,
                "is_default": True,
                "message": "Using default configuration (no active config in database)"
            }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
async def get_all_configs():
    """
    GET all active calculator configurations
    """
    try:
        result = supabase.table('calculator_configs')\
            .select('calculator_type, year, config, source_url, updated_at')\
            .eq('is_active', True)\
            .execute()
        
        configs = {}
        for item in result.data:
            configs[item['calculator_type']] = {
                'year': item['year'],
                'config': item['config'],
                'source_url': item.get('source_url'),
                'last_updated': item.get('updated_at')
            }
        
        return {
            "success": True,
            "configs": configs,
            "count": len(configs)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))