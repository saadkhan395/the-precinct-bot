import os
from groq import Groq

client = Groq(api_key=os.environ["GROQ_API_KEY"])
models = client.models.list()
for m in models.data:
    print(m.id)
print("GROQ OK")
