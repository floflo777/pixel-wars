import requests
import time
import threading
import queue

# ------------------------------------------------------------
# 1) Police minimaliste 2×5 (chaque caractère = 2 colonnes × 5 lignes)
#    '1' => pixel coloré (FG), '0' => pixel de fond (BG)
# ------------------------------------------------------------
CHAR_MAP_2x5 = {
    '0': ["11","10","10","10","11"],
    '1': ["01","01","01","01","01"],
    '2': ["11","01","11","10","11"],
    '3': ["11","01","11","01","11"],
    '4': ["10","10","11","01","01"],
    '5': ["11","10","11","01","11"],
    '6': ["11","10","11","10","11"],
    '7': ["11","01","01","01","01"],
    '8': ["11","10","11","10","11"],
    '9': ["11","10","11","01","11"],
    'A': ["11","10","11","10","10"],
    'C': ["11","10","10","10","11"],
    'D': ["10","10","10","10","10"],  # Ex. minimal
    'E': ["11","10","11","10","11"],
    'F': ["11","10","11","10","10"],
    'a': ["00","01","11","10","11"],
    'c': ["00","01","10","10","01"],
    'd': ["01","01","11","10","11"],
    'e': ["00","10","11","10","01"],
    'f': ["01","10","11","10","10"],
    'x': ["00","10","01","10","00"]
    # Ajoute d'autres caractères si nécessaire
}

# ------------------------------------------------------------
# 2) Configuration : tokens, URL, couleurs, etc.
#    Mets tous tes comptes pour poser en parallèle.
# ------------------------------------------------------------
session_tokens = [
    "mUJRdKpDhJrnScmNsJWk04Z0phGLocr94jHFByD5jFbuGyAGgzM8nhcWUDY84jPG",  # compte 1
    "yAJkpYg7fIxNfGbbICcZhx0LW284l46ZPXELejTHGhH5SNpsGR9s2Yf9BOvAvoy1",  # compte 2
    "ID7vM8zmF5oA1Q4yns6aDBhRFnDBUxgmb1yTwJYIMzTDZMyKksb4medSgC9mGMkU",  # compte 3
    "MkDAt3p0XVOa3e85S3gx5jneG5GEswmInHFMS4itYKGuDO5FB6LwNOEunebO5I7O",  # compte 4
    "fBHu99d1e4VRS9BwERaIxjhKvP9noPLphmfDIxiiTgVpLBrUykaC7TZdEPWtAwQm",  # compte 5
    "epcPq6gPqfAxOZiJHmUtOacYq0S633V3752OM3mMYPC1LstCyP3kYCP32FHBrGZu",  # compte 6
    "3ic1cVbRsZjaKYisfFlfoTpKQ1ICoR5pw5aIRQOBe3oKjJNMGIxYHDSDYgFTb3kF",  # compte 7
    "pfxWDPUtxcx0A1Z0cc3eJn355Jn3eBH8fsQL3h4sZmiY3VxqcvxIWhcS305MXFDJ",  # compte 8
    "eVlAGAy3caPO64NmfPv4VTJProzPXplSi6ktNXfi4fRfHF7G1adUrR1CphGt539s",  # compte 9
    "mIw8wGgQ7Bv7rEca9tWtf3jK4liWHB6TS0en1BPR7T1wIEYZz9pWdAuWlhFVrb4I",  # compte 10
    "ZgDbWkhrkUu99OyP8W043dFa2MGPFsim6ZHHgY7IgKPyU4bh7bdabRyhaW5yQcTY",  # compte 11
    "U4AwY0K9ZnDcw8krlUWxbikk6EKIg3ngyyq5qderMqNv3MeJIfi9aUhWNDRUpA3R",  # compte 12
    "frNQeu4vBNste1467xDf1rgJvvI9Cm1ZPd9dAwhxjGYEsv8GSaFgkRDSJaS8S75A",  # compte 13
    "bmA6ndJa6TKVINqar9hEQXLJyp0KHvMCctNGF9SmU1NEc9MSoQANtH8ojoMUxcTg",  # compte 14
    "vPkDCHK5QPzhzfvJ0A34gsqs2QPLEcXNKBPqyyw4UOAlpCT8hOIo5eUfw1XzhgkD",  # compte 15
    "GIeeI13X0ZkRky2xCvnsQtQtVYVbjQ74K9rhJx1AybhHmh6wF5cqdME1vnLPViuB",  # compte 16
    "FzG7IbepNGqVSE0OUxkLOOH0pliZWEQ8MKD2QMAGdbRgCGh9BJ8vtzfptOpFeE7X",  # compte 17
    "YHVW0AdoVX4laVlnddTEU3jnDbiDSHgNrs5nkcyP0ZZKnM2qI1TtwhhbllmROraj",  # compte 18
    "ygRnOpLNIgoGJEE5bkf8LSKYXlEw0ha5Gy85RNiUttlEeHt5Il9JLNOKkVAic2dk"   # compte 19
]

url_place_pixel = "https://saloon.reniti.fr/api/v1/map/place"

COOLDOWN = 21  # en secondes (cooldown individuel par compte)
COLOR_BG = "0000ea"  # bleu (fond), sans le '#'
COLOR_FG = "ffffff"  # blanc (trait), sans le '#'

headers = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Origin": "https://saloon.reniti.fr",
    "Referer": "https://saloon.reniti.fr/",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/132.0.0.0 Safari/537.36"
    )
}

# ------------------------------------------------------------
# 3) Texte à dessiner et position de départ
# ------------------------------------------------------------
text_to_draw = "0xE5acF664aA782fE26695a53F0392a9cCD080e54A"
start_x = 0
start_y = 0

# ------------------------------------------------------------
# 4) Génération de la queue de pixels (x, y, color)
#    => tous les pixels nécessaires pour dessiner le texte
# ------------------------------------------------------------
pixel_queue = queue.Queue()

current_x = start_x
for char in text_to_draw:
    matrix = CHAR_MAP_2x5.get(char)
    if not matrix:
        # Caractère non défini -> saute 3 colonnes (2 + 1 espace)
        current_x += 3
        continue
    
    # matrix = 5 lignes (row), chaque ligne = 2 colonnes (col)
    for row in range(len(matrix)):       # row : 0..4
        line = matrix[row]              # ex. "11"
        for col in range(len(line)):    # col : 0..1
            pixel_val = line[col]       # '0' ou '1'
            color = COLOR_FG if pixel_val == '1' else COLOR_BG
            x_coord = current_x + col
            y_coord = start_y + row
            pixel_queue.put((x_coord, y_coord, color))
    
    # On avance de 2 colonnes + 1 espace = 3
    current_x += 3

# ------------------------------------------------------------
# 5) Fonction thread : un compte place un pixel puis dort 21s
# ------------------------------------------------------------
def worker_func(token, thread_id):
    """Récupère des pixels dans la queue, place un pixel, attend 21s, etc."""
    while not pixel_queue.empty():
        try:
            x, y, color_hex = pixel_queue.get_nowait()
        except queue.Empty:
            break  # plus rien à faire
        
        cookies = {
            "session.token": token,
            "termsAccepted": "true"
        }
        data = {
            "x": x,
            "y": y,
            "hexColor": color_hex
        }
        
        resp = requests.post(url_place_pixel, headers=headers, cookies=cookies, json=data)
        
        if resp.status_code == 200:
            print(f"[Thread {thread_id}] OK pixel ({x},{y}) color={color_hex}")
        else:
            print(f"[Thread {thread_id}] ERREUR {resp.status_code} => {resp.text} "
                  f"pour pixel({x},{y})")

        pixel_queue.task_done()
        
        # Cooldown individuel
        time.sleep(COOLDOWN)

    print(f"[Thread {thread_id}] terminé : plus de pixels dans la queue ou queue vide.")

# ------------------------------------------------------------
# 6) Lancement des threads
# ------------------------------------------------------------
threads = []
for i, token in enumerate(session_tokens, start=1):
    t = threading.Thread(target=worker_func, args=(token, i))
    threads.append(t)
    t.start()

# ------------------------------------------------------------
# 7) Attendre la fin
# ------------------------------------------------------------
for t in threads:
    t.join()

print("Tous les pixels ont été posés. Fin du script.")
