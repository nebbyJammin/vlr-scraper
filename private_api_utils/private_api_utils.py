from datetime import date, datetime
from enum import Enum
import json
import os
from typing import Dict, List
from scraper.entities import VLRResult

PRIVATE_API_BASE_URL = os.getenv("PRIVATE_API_BASE_URL")

def vlr_result_list_to_json(list: List[VLRResult]) -> str:
    return json.dumps([result.to_json() for result in list], default=str)

def vlr_result_list_to_dict(list: List[VLRResult]) -> List[Dict[str, any]]:
    return [result.to_dict() for result in list]

def serializer(o):
    if isinstance(o, datetime):
        if o.tzinfo is not None:
            o = o.replace(tzinfo=None) # TZ INFO not stored in DB
            
        return o.isoformat()

    if isinstance(o, date):
        return o.isoformat()

    if isinstance(o, Enum):
        return o.value
        
    return str(o)