from .bot import Bot
from fastapi import FastAPI, Path, Query
from redis import Redis
from rq import Queue


app = FastAPI()
bot = Bot()
# Establish connectivity

@app.get('/')
def index():
    return "Home"

@app.get('/system/pulse-check')
def pulse_check():
    if not bot.check_login_status():
        bot.login()
        return "Not Logged in. Logging in now."
    return "Logged in."


@app.post('/vessel/{vessel_name}')
def query_vessel_vsip(vessel_name:str = Path(description="The name of the vessel you wish to retrieve the VSIP from"), callsign: str = Query(description="The callsign of the vessel you wish to retrieve the VSIP from")):
    # Add text validation before allowing search
    return bot.add_to_job_queue(vessel_name, callsign)

@app.post('/otp')
def handle_otp(otp:str):
    try:
        print(otp)
        bot.handle_otp(otp)
        return {"Success": "Successfully handled OTP"}
    except:
        return {"Error": "Error handling OTP"}