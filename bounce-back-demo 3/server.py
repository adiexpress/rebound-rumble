"""Local Bounce Back demo: webcam card scanning + static game UI."""
from pathlib import Path
import cv2
import numpy as np
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

ROOT=Path(__file__).parent
app=FastAPI(title='Bounce Back Demo')
app.mount('/static',StaticFiles(directory=str(ROOT/'static')),name='static')
from scanner import detect_card, detect_guided_card

@app.get('/data/cards')
async def card_database():
    return FileResponse(ROOT/'data/cards.json',media_type='application/json')

@app.get('/')
async def home():return FileResponse(ROOT/'static/index.html')

@app.post('/api/scan')
async def scan(request:Request):
    data=await request.body()
    if len(data)>9_000_000:return JSONResponse({'ok':False,'message':'Image too large.'},status_code=413)
    frame=cv2.imdecode(np.frombuffer(data,dtype=np.uint8),cv2.IMREAD_COLOR)
    if frame is None:return JSONResponse({'ok':False,'message':'Could not decode camera image.'},status_code=400)
    result=detect_guided_card(frame) if request.query_params.get("guided")=="1" else detect_card(frame)
    return result
