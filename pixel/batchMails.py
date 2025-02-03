import time
import re
import csv
import requests

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ---------------------------------------------------------------------
# Configuration MailSlurp
# ---------------------------------------------------------------------
MAILSLURP_API_KEY = "FILL_IT"
MAILSLURP_BASE_URL = "https://api.mailslurp.com"

def create_temp_inbox():
    """Crée une boîte mail temporaire via MailSlurp et renvoie (adresse_email, inbox_id)."""
    headers = {"x-api-key": MAILSLURP_API_KEY}
    response = requests.post(f"{MAILSLURP_BASE_URL}/inboxes", headers=headers)
    response.raise_for_status()
    data = response.json()
    return data['emailAddress'], data['id']

def wait_for_email(inbox_id, timeout=60):
    """Attend la réception d'un email dans la boîte MailSlurp (jusqu'à 'timeout' secondes)."""
    headers = {"x-api-key": MAILSLURP_API_KEY}
    end_time = time.time() + timeout
    while time.time() < end_time:
        response = requests.get(f"{MAILSLURP_BASE_URL}/inboxes/{inbox_id}/emails", headers=headers)
        response.raise_for_status()
        emails = response.json()
        if emails:
            return emails[0]
        time.sleep(2)
    return None

def get_email_body(email_id):
    """Récupère le contenu (body) d'un email précis dans MailSlurp."""
    headers = {"x-api-key": MAILSLURP_API_KEY}
    response = requests.get(f"{MAILSLURP_BASE_URL}/emails/{email_id}", headers=headers)
    response.raise_for_status()
    return response.json()['body']

def extract_login_token(email_body):
    """
    Extrait le token dans l’URL :
      https://saloon.reniti.fr/api/v1/auth/login-by-email/<TOKEN>
    On arrête la capture à un espace, guillemet ou < (pour éviter d'inclure le HTML).
    """
    pattern = r"https://saloon\.reniti\.fr/api/v1/auth/login-by-email/([^\s\"<]+)"
    match = re.search(pattern, email_body)
    if match:
        return match.group(1)
    return None

# ---------------------------------------------------------------------
# Script Principal
# ---------------------------------------------------------------------
def test_reniti_site(nombre_iterations=1, output_csv="session_tokens.csv"):
    """
    Lance 'nombre_iterations' tests. Chaque test :
      - Génère une email via MailSlurp
      - Remplit le champ 'Email' dans saloon.reniti.fr en saisie lente
      - Récupère le token (extrait de l'URL) dans l'email reçu
    Puis ajoute chaque token récupéré dans le fichier CSV 'output_csv' (en mode append).
    """

    # Installer et initialiser le driver Chrome
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)


    try:
        for i in range(nombre_iterations):
            print(f"\n=== Test {i+1} / {nombre_iterations} ===")

            # 1) Générer une nouvelle adresse e-mail via MailSlurp
            email, inbox_id = create_temp_inbox()
            print("Email temporaire généré :", email)

            # 2) Ouvrir la page principale
            driver.get("https://saloon.reniti.fr/")
            print("==> Page chargée.")

            # 3) Cliquer sur "Accepter"
            accept_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accepter')]"))
            )
            accept_button.click()
            print("==> Bouton 'Accepter' cliqué.")

            # 4) Cliquer sur "COMMENCER À PLACER DES PIXELS"
            start_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//button[contains(@class, 'MuiButtonBase-root') and contains(@class, 'MuiButton-containedPrimary')]"
                ))
            )
            start_button.click()
            print("==> Bouton 'COMMENCER À PLACER DES PIXELS' cliqué.")

            # 5) Localiser le champ email
            email_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((
                    By.XPATH,
                    "//label[contains(text(), 'Email')]/following-sibling::div//input"
                ))
            )

            # 6) Saisir l'email lentement, caractère par caractère
            for char in email:
                email_input.send_keys(char)
                time.sleep(0.02)  # Ajustez la vitesse de frappe si besoin

            # Optionnel : Supprimer le dernier caractère puis le remettre (aide à la validation front-end)
            email_input.send_keys("\b")
            time.sleep(0.1)
            email_input.send_keys(email[-1])
            print(f"==> Champ Email rempli avec {email}")

            # 7) Attendre la validation front-end
            time.sleep(0.05)

            # 8) Cliquer sur "Valider"
            validate_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Valider')]"))
            )
            validate_button.click()
            print("==> Bouton 'Valider' cliqué.")

            # 9) Attendre la réception du mail dans MailSlurp
            mail_info = wait_for_email(inbox_id, timeout=60)
            if mail_info is None:
                print("==> Aucun email reçu dans le délai imparti.")
                continue

            # 10) Extraire le token dans le corps de l’email
            body = get_email_body(mail_info['id'])
            token = extract_login_token(body)

            # 11) Enregistrer dans le CSV (en mode append)
            if token:
                print("==> Token de connexion récupéré :", token)
                with open(output_csv, "a", newline="", encoding="utf-8") as csvfile:
                    csvfile.write(f"\"{token}\",\n")
            else:
                print("==> Impossible d'extraire le token de connexion.")

            time.sleep(1)

    finally:
        # Fermer le navigateur
        driver.quit()
        print(f"\nLes tokens extraits ont été ajoutés à '{output_csv}'.")

# ---------------------------------------------------------------------
# Exécution du script
# ---------------------------------------------------------------------
if __name__ == "__main__":
    # Par défaut, 1 itération => vous pouvez lancer ce script plusieurs fois d'affilée
    # ou augmenter 'nombre_iterations' pour tout faire en une seule exécution.
    test_reniti_site(nombre_iterations=1, output_csv="session_tokens.csv")
