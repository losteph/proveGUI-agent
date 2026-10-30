import os
import base64
from openai import OpenAI

# 1. Inserisci qui la tua API Key di OpenRouter
OPENROUTER_API_KEY = "KEY" #inserire qua la chiave Personale

# Configurazione del client OpenAI puntato su OpenRouter
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# Il modello gratuito che abbiamo scelto
MODELLO = "nvidia/nemotron-3.5-super-vl:free"

def analizza_interfaccia(immagine_path, prompt_istruzione):
    # Leggiamo l'immagine locale e la convertiamo in Base64 per inviarla via API
    with open(immagine_path, "rb") as img_file:
        base64_image = base64.b64encode(img_file.read()).decode('utf-8')

    print(f"Invio dello screenshot al modello {MODELLO}...")

    response = client.chat.completions.create(
        model=MODELLO,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text", 
                        "text": prompt_istruzione
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}"
                        }
                    }
                ]
            }
        ]
    )
    
    return response.choices[0].message.content

# Test pratico
if __name__ == "__main__":
    # Assicurati di avere un'immagine chiamata "schermata_test.png" nella stessa cartella
    if os.path.exists("schermata_test.png"):
        istruzione = "Analizza questa GUI. Dimmi quali elementi vedi e scrivi il comando in Python con PyAutoGUI per cliccare sul bottone principale."
        risposta_ia = analizza_interfaccia("schermata_test2.png", istruzione)
        
        print("\n--- RISPOSTA DELL'IA ---")
        print(risposta_ia)
    else:
        print("Metti un'immagine 'schermata_test.png' nella cartella del progetto per fare il test visivo!")