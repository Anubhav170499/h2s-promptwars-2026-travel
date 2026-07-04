import uvicorn
from travelpilot.api import create_app
from travelpilot import config

app = create_app()

if __name__ == "__main__":
    uvicorn.run("main:app", host=config.HOST, port=config.PORT, reload=True)
