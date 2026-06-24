import zmq
import time

context = zmq.Context()
socket = context.socket(zmq.PAIR)
socket.bind("ipc:///tmp/markov_shell.ipc")

print("Aşama 5: Ghost Text UI Test Sunucusu Başladı...")

# Basit bir kelime tamamlama sözlüğü (Sadece geri kalan kısmı gönderir)
mock_db = {
    "e": "cho",
    "ec": "ho",
    "ech": "o",
    "g": "it status",
    "gi": "t status",
    "git": " status",
    "l": "s -la",
    "ls": " -la"
}

while True:
    try:
        message = socket.recv_string(flags=zmq.NOBLOCK)
        
        # Eğer yazılan metin sözlüğümüzde varsa, kelimenin kalanını gönder
        if message in mock_db:
            socket.send_string(mock_db[message])
        else:
            socket.send_string("") # Eşleşme yoksa boşluk (Ghost text yok)
            
    except zmq.Again:
        time.sleep(0.01)