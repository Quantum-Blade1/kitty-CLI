import os
from dotenv import load_dotenv
load_dotenv(".env")
from bytez import Bytez

key = os.environ.get("BYTEZ_API_KEY")
if not key:
    print("No Bytez key")
    exit(1)

b = Bytez(key)
try:
    model = b.model("meta-llama/Meta-Llama-3-8B-Instruct")
    print("Model initialized")
    res = model.run("say hi")
    print("Success:", res)
except Exception as e:
    print("Error:", e)
