import pyautogui
import time

print("Dopo 2 secondi cattura lo screenshot della VM...")
time.sleep(2)

screenshot = pyautogui.screenshot()
screenshot.save("schermata_vm.png")

print("Fatto! Screenshot salvato con successo.")