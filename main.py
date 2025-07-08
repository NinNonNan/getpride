import hashlib
import json
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, constr

# Carica dati da file
with open("types.json", "r", encoding="utf-8") as f:
    types = json.load(f)

with open("affinity_table.json", "r", encoding="utf-8") as f:
    affinity_table = json.load(f)

app = FastAPI(title="Barcode Pride API")

# Monta la cartella 'static' su /static
app.mount("/static", StaticFiles(directory="static"), name="static")

class BarcodeRequest(BaseModel):
    barcode: constr(min_length=1, max_length=50)

def barcode_to_pride(barcode: str) -> dict:
    barcode = ''.join(filter(str.isdigit, barcode))
    barcode = barcode.zfill(13)[:13]

    blocks = [
        barcode[0:2],   
        barcode[2:4],   
        barcode[4:6],   
        barcode[6:8],   
        barcode[8:]     
    ]

    def norm(val, scale=255):
        return int((int(val) % 1000) / 1000 * scale)

    pride = {
        "Power": norm(blocks[0]),
        "Resistence": norm(blocks[1]),
        "Intelligence": norm(blocks[2]),
        "Determination": norm(blocks[3]),
        "Energy": norm(blocks[4])
    }

    checksum = sum(int(c) for c in barcode) % 256
    primary_type_index = checksum % len(types)
    primary_type = types[primary_type_index]

    mutation_flag = any(v == 0 or v == 255 for v in pride.values())

    h = hashlib.sha256(barcode.encode()).hexdigest()
    secondary_type_index = int(h[:2], 16) % len(types)
    secondary_type = types[secondary_type_index]

    if secondary_type == primary_type:
        secondary_type_index = (secondary_type_index + 1) % len(types)
        secondary_type = types[secondary_type_index]

    name_seed = hashlib.md5(barcode.encode()).hexdigest()[:6].upper()
    name = f"Specimen-{name_seed}"

    primary_affinity = affinity_table.get(primary_type, {})
    secondary_affinity = affinity_table.get(secondary_type, {})

    affinity = {
        "Primary": primary_affinity,
        "Secondary": secondary_affinity
    }

    return {
        "barcode": barcode,
        "name": name,
        "pride": pride,
        "types": [primary_type, secondary_type],
        "mutation_flag": mutation_flag,
        "affinity": affinity
    }

@app.post("/pride")
async def get_pride(data: BarcodeRequest):
    try:
        result = barcode_to_pride(data.barcode)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/pride")
async def read_pride():
    return {"message": "Usa POST su questo endpoint con un payload JSON contenente il barcode."}
