# GUI Agent prove varie

Lavoro svolto per lo sviluppo e il test di un **GUI Agent autonomo basato su Vision-Language Models (VLM)** in un ambiente virtuale Linux Lubuntu. 

---

## 📋 Resoconto Passo Passo delle Attività

### 1. Selezione del Modello Vision
Per evitare i costi legati alle API di modelli a pagamento come GPT-4o o analoghi commerciali, ho configurato l'ambiente per operare interamente con **modelli VLM gratuiti**. 
* ho trovato la piattaforma **OpenRouter.ai** e selezionato il modello visivo gratuito `nvidia/nemotron-3.5-super-vl:free`.

### 2. Primo Test 
Il primo test, servito a verificare la capacità d'analisi visiva del modello scelto:
* il VLM ha letto degli screenshot ed ha stampato a schermo l'analisi testuale del modello per confermare che fosse in grado di interpretare la schermata e suggerire le prossime azioni da compiere.

### 3. Configurazione dell'Ambiente di Lavoro (Lubuntu VM + SSH)
È stata predisposta un infrastruttura di esecuzione isolata:
* Configurazione di una macchina virtuale con **Lubuntu Linux** (perché ho poca RAM ed è più leggero di Ubuntu classico).
* Abilitazione e configurazione del server **SSH** all'interno della VM (per non scaricare VSCode in VM con la poca RAM ma comandarlo lato Windows tramtie collegamento remoto).
* Aggiornamento del sistema operativo e installazione di tutti i pacchetti di sistema necessari.

### 4. Configurazione Python e Virtual Environment
In conformità con le policy dei sistemi Debian/Ubuntu moderni (PEP 668), ho dovuto isolare l'ambiente di lavoro:
* Creazione di un ambiente virtuale Python (`python3 -m venv venv`).
* Installazione all'interno del `venv` delle dipendenze principali: `pyautogui`, `pillow`, `requests`, `opencv-python`.

### 5. Primo Test di Interazione GUI
Prima di procedere all'automazione complessa, abbiamo validato il controllo del display X11 (`DISPLAY=:0`):
* Avviato uno script di test Python tramite il terminale SSH di VS Code su Windows.
* Verificato che PyAutoGUI fosse in grado di catturare correttamente lo screenshot del desktop corrente della VM e di salvarlo (`schermata_vm.png`).

### 6. Sviluppo di una prima bozza di GUI-Agent
Prova di implementazione di un ciclo completo di **Visual Grounding**, **Hover/Verification** e **Action Execution**:
1. **Creazione Cartella:** L'agente effettua un clic destro sul desktop, individua il menu *Create New*, apre il sottomenu, clicca su *Folder*, digita il nome `Prova1234` e verifica la presenza della cartella a schermo.
2. **Apertura Cartella:** Esegue un doppio clic sulla cartella appena creata e verifica l'apertura della finestra del File Manager.
3. **Creazione File:** Effettua un clic destro all'interno della cartella, seleziona la voce per creare un file di testo (*Blank File*) e lo nomina `Prova1234.txt`.
4. **Scrittura Report:** Apre il file di testo, scrive automaticamente il report dettagliato delle operazioni svolte, salva con scorciatoia e chiude l'editor.
5. **Chiusura e Telemetria:** Chiude il File Manager, ripristina lo stato del desktop ed esporta il report finale in formato JSON (`gui_agent_report.json`) con i dati prestazionali dell'esperimento.

Questo però è ancora guidato, non riesce a capire che azioni fare se gli diamo un prompt, ma gli facciamo controllare lo schermo dopo ogni azione (e consuma anche molte richieste, NON ottimizzato, molto migliorabile). Il prossimo passo è provare un vero e proprio GUI-Agent che da un singolo prompt utente prova a fare le azioni da solo (senza essere guidato passo passo ed essere specializzato solo su un azione e se cambia leggermente un nome, una lettere maiuscola invece che minuscola se ne va in panico, ma riuscendo a capire comunque cosa può portare al risultato ottimale). Diviso in Planner, Executor, Contoller. 

Limite chiamate modelli FREE di OpenRouter è:
```json
  "is_free_tier": true,
  "free_model_daily_requests": {
    "used": 50,
    "limit": 50,
    "remaining": 0
  }
```
Quindi da vedere ed ottimizzare meglio il tutto. Per controllare quante chiamate hai a disposizione da terminale si digita:
```
curl https://openrouter.ai/api/v1/key \
  -H "Authorization: Bearer LA_TUA_API_KEY"
```

---

### 🛠️

1. **Attivare l'ambiente virtuale nella cartella di lavoro:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
   (Questa parte qua poi l'ho risolta senza usare venv ma sono riuscito ad installare i pacchetti direttamente su Lubuntu senza errori di sicurezza che dava prima)

2. **Verificare la presenza delle variabili d'ambiente per il display:**
   ```bash
   export DISPLAY=:0
   export XAUTHORITY=$HOME/.Xauthority
   ```
   (Queste senza rifarle ogni volta con export da terminale le ho aggiunte ad inizio Script così le legge ed esegue in automatico)

3. **Inserire la API Key di OpenRouter nei vari script:**
   ```python
   API_KEY = "la_tua_chiave_openrouter"
   ```

4. **Lanciare lo script dell'agente:**
   ```bash
   python3 GUI.py
   ```

---

## Configurazioni eseguite per l'ambiente di simulazione

Dalle impostazioni della VM, nella sezione rete ho configurato un Port Forwardin con Host 2222 e Guest 22.

Abilitato una volta avviata la VM il server SSH da terminale:
```
sudo apt update
sudo apt install -y openssh-server
sudo systemctl enable --now ssh
```

Da VSC invece:

F1 (o Ctrl+Shift+P) "Remote SSH: Connect to Host.."

```
ssh nomeutenteVM@localhost -p 2222
```


Tutti i pacchetti che sono serviti su python:
```
sudo apt install -y python3-full python3-venv python3-pip scrot python3-tk
pip install pyautogui pillow requests opencv-python openai

```

Altre configurazioni:

Crea materialmente il file nascosto .Xauthority nella cartella se non  presente o cancellato, evitando che Python crashasse cercando un file inesistente. 
```
touch ~/.Xauthority
xauth generate :0 . trusted
```
per fare in modo che il file non fosse solo un guscio vuoto ma contenesse il "cookie" di autenticazione del display :0, si usa solitamente il comando di generazione di xauth, oppure si copia il file dal display dell'utente principale (`cp /home/nomeutente/.Xauthority ~/.Xauthority`).
