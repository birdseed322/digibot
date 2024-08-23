from .bot import Bot
from fastapi import FastAPI, Path
    
app = FastAPI()
bot = Bot()
# Establish connectivity

@app.get('/')
def index():
    return "Home"

@app.get('/{vessel_name}')
def query_vessel_vsip(vessel_name:str = Path(description="The name of the vessel you wish to retrieve the VSIP from")):
    vsip = bot.search(vessel_name)
    return vsip

@app.post('/otp')
def handle_otp(otp:str):
    try:
        print(otp)
        bot.handle_otp(otp)
        return {"Success": "Successfully handled OTP"}
    except:
        return {"Error": "Error handling OTP"}
