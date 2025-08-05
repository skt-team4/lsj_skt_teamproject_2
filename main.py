from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Message(BaseModel):
    text: str

@app.get("/")
def read_root():
    return {"message": "lsj is running"}

@app.post("/send")
def send_message(message: Message):
    return {"lsj received_message": message.text}
