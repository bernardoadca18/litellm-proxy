import os 
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

master_key = os.getenv("LITELLM_MASTER_KEY")

if not master_key:
    raise ValueError("A chave LITELLM_MASTER_KEY não foi encontrada no arquivo .env!")

client = OpenAI(

    base_url="http://localhost:4000/v1",

    api_key=master_key

)


try:

    print("Enviando requisição para o gemini-flash-lite...\n")

    

    response = client.chat.completions.create(

        model="gemini-flash",

        messages=[

            {"role": "system", "content": "Você é um assistente útil e direto."},

            {"role": "user", "content": "Me dê uma ideia de nome para um projeto de proxy de IA."}

        ]

    )

    

    print("Resposta da IA:")

    print(response.choices[0].message.content)


except Exception as e:

    print(f"Ocorreu um erro: {e}")
