import time
import threading
import queue
import os
import pandas as pd
from PIL import Image
import requests
import matplotlib.pyplot as plt

# ============================================================
# 1) Configuration générale
# ============================================================
url_place_pixel = "https://saloon.reniti.fr/api/v1/map/place"
COOLDOWN = 21  # Secondes entre chaque pixel

# Tokens de session (à ajuster selon votre configuration)
session_tokens = [
    "slQSKdRZvMa5QPo1d6HVAMwaTag8FMBpyfFNjKhpCBY2bKpcECjxfGdHF870NsKj",
    "jpmzKfYwqm6e7QTpMVrlaYkE7ICpWKncFDHOhFFXbrvcrE9fJsWabnoSsKZHxITh"
]

# Valeur du cookie cf_clearance
CLEARANCE = (
    "UCKQ3GWmBVXHb4EAk.cFUs97OXStvYRAn0hzFyqnuqc-1738597486-1.2.1.1-xfLgl7iWOhLm5.CI_FlVYUmuL_wwMlzHsKYT5Dx6ZuBRJ32USVha.3DAZcYRuSDy437J_ACYbRwNSkTZyZprot0h5HlWT6D0XJmn1UJLm76ufUTHkJSk_mCvo_gp4UbWJqArkwfPvf1xa8isoy4JTpO3i9eNOo.fehXkqfVJTYVlw5eqAaeXhCnEzE58Zj6GJWUz7kvEQFZlqHLmf9P56vOy6qEX5hCxvFR81gom3erwzWsRf9Zn8Fx2bLQ_7S3fM0IWgSmTL6Nw1UjheOmbBXgO6pisu5yrsRlbPl8eFgo"
)

headers = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Origin": "https://saloon.reniti.fr",
    "Referer": "https://saloon.reniti.fr/",
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/132.0.0.0 Safari/537.36")
}

# Fichier CSV contenant les pixels redimensionnés
CSV_FILE = "final_resized_mapped_pixels.csv"

# ============================================================
# 2) Chargement des pixels depuis le CSV
# ============================================================
def load_pixels_from_csv():
    """Charge les pixels à partir du fichier CSV."""
    if not os.path.exists(CSV_FILE):
        raise FileNotFoundError(f"Le fichier {CSV_FILE} est introuvable.")
    df = pd.read_csv(CSV_FILE)
    return df.values.tolist()

# ============================================================
# 3) Visualisation des pixels
# ============================================================
def visualize_pixels(pixels):
    """Affiche les pixels sous forme d'image."""
    max_x = max(p[0] for p in pixels)
    max_y = max(p[1] for p in pixels)

    canvas = Image.new("RGB", (max_x + 1, max_y + 1), (255, 255, 255))
    for x, y, color in pixels:
        r, g, b = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
        canvas.putpixel((x, y), (r, g, b))

    plt.figure(figsize=(8, 8))
    plt.imshow(canvas)
    plt.axis("off")
    plt.title("Visualization of Resized Logo")
    plt.show()

# ============================================================
# 4) Placement des pixels
# ============================================================
PLACED_PIXELS_FILE = "placed_pixels.txt"
file_lock = threading.Lock()

def load_placed_pixels():
    placed = set()
    if os.path.exists(PLACED_PIXELS_FILE):
        with open(PLACED_PIXELS_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    parts = line.split(",")
                    if len(parts) == 3:
                        try:
                            x = int(parts[0])
                            y = int(parts[1])
                            color = parts[2]
                            placed.add((x, y, color))
                        except:
                            continue
    return placed

def save_placed_pixel(pixel):
    with file_lock:
        with open(PLACED_PIXELS_FILE, "a") as f:
            x, y, color = pixel
            f.write(f"{x},{y},{color}\n")

def build_pixel_queue(pixels):
    """Construit la file de pixels à partir de la liste et exclut ceux déjà posés."""
    placed = load_placed_pixels()
    remaining = [p for p in pixels if tuple(p) not in placed]
    q = queue.Queue()
    for p in remaining:
        q.put(p)
    print(f"Nombre total de pixels à poser : {len(pixels)}")
    print(f"Pixels déjà posés : {len(placed)}")
    print(f"Pixels restants : {q.qsize()}")
    return q

def place_pixel(token, thread_id, pixel_queue):
    """Place les pixels en utilisant une requête POST."""
    while not pixel_queue.empty():
        try:
            pixel = pixel_queue.get_nowait()
            x, y, color_hex = pixel
        except queue.Empty:
            break

        cookies = {
            "session.token": token,
            "termsAccepted": "true",
            "cf_clearance": CLEARANCE
        }
        data = {"x": x, "y": y, "hexColor": color_hex}
        try:
            resp = requests.post(url_place_pixel, headers=headers, cookies=cookies, json=data)
        except Exception as e:
            print(f"[Worker {thread_id}] Exception à ({x},{y}): {e}")
            pixel_queue.task_done()
            time.sleep(COOLDOWN)
            continue

        if resp.status_code == 200:
            print(f"[Worker {thread_id}] OK pixel ({x},{y}) => {color_hex}")
            time.sleep(0.1)
            save_placed_pixel(pixel)
        else:
            print(f"[Worker {thread_id}] ERREUR {resp.status_code}: {resp.text} (x={x}, y={y})")
        pixel_queue.task_done()
        time.sleep(COOLDOWN)
    print(f"[Worker {thread_id}] terminé.")

# ============================================================
# 5) Boucle de dessin
# ============================================================
def draw_loop():
    pixels = load_pixels_from_csv()
    pix_queue = build_pixel_queue(pixels)
    threads = []
    for i, token in enumerate(session_tokens, start=1):
        t = threading.Thread(target=place_pixel, args=(token, i, pix_queue))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()
    print("=== Fin de la passe de dessin ===")

# ============================================================
# 6) Programme principal
# ============================================================
if __name__ == '__main__':
    pixels = load_pixels_from_csv()  # Charger les pixels
    visualize_pixels(pixels)         # Visualiser le logo
    draw_loop()                      # Lancer le placement des pixels
