import requests
import json
import time
import logging

# Konfiguration des Loggings
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Konstanten
SCRYFALL_API_BASE = "https://api.scryfall.com"
BULK_DATA_ENDPOINT = "/bulk-data"
OUTPUT_DB_PATH = "core/data/card_db.json"

def get_bulk_data_url() -> str:
    """
    Ruft die URL für die "Oracle Cards" Bulk-Daten von Scryfall ab.
    Diese Daten enthalten alle einzigartigen Karten-Drucke.
    """
    try:
        response = requests.get(SCRYFALL_API_BASE + BULK_DATA_ENDPOINT)
        response.raise_for_status()
        bulk_data_objects = response.json()['data']
        
        for obj in bulk_data_objects:
            if obj['type'] == 'oracle_cards':
                logging.info(f"Bulk-Daten URL gefunden: {obj['download_uri']}")
                return obj['download_uri']
        
        raise ValueError("Kein 'oracle_cards' Bulk-Datenobjekt gefunden.")

    except requests.exceptions.RequestException as e:
        logging.error(f"Fehler bei der API-Anfrage an Scryfall: {e}")
        raise
    except (KeyError, ValueError) as e:
        logging.error(f"Fehler bei der Verarbeitung der Scryfall-Antwort: {e}")
        raise

def download_and_process_bulk_data(url: str) -> None:
    """
    Lädt die Bulk-Daten herunter, verarbeitet sie und speichert sie als JSON-Datenbank.
    """
    logging.info("Starte den Download der Kartendaten. Dies kann einige Minuten dauern...")
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()

        logging.info("Download abgeschlossen. Verarbeite die Daten...")
        
        all_cards = response.json()
        card_database = {}

        for card_data in all_cards:
            # Wir verwenden die 'oracle_id' als eindeutigen Schlüssel, um Duplikate
            # durch verschiedene Drucke zu vermeiden.
            oracle_id = card_data.get('oracle_id')
            if not oracle_id:
                continue
            
            # Extraktion der relevanten Felder
            card_database[oracle_id] = {
                'name': card_data.get('name'),
                'mana_cost': card_data.get('mana_cost', ''),
                'cmc': card_data.get('cmc', 0.0),
                'type_line': card_data.get('type_line'),
                'oracle_text': card_data.get('oracle_text', ''),
                'power': card_data.get('power', None),
                'toughness': card_data.get('toughness', None),
                'colors': card_data.get('colors', []),
                'color_identity': card_data.get('color_identity', []),
                'keywords': card_data.get('keywords', []),
                'legalities': card_data.get('legalities', {}),
            }
        
        logging.info(f"{len(card_database)} einzigartige Karten wurden verarbeitet.")

        with open(OUTPUT_DB_PATH, 'w', encoding='utf-8') as f:
            json.dump(card_database, f, indent=4, ensure_ascii=False)
            
        logging.info(f"Kartendatenbank erfolgreich unter {OUTPUT_DB_PATH} gespeichert.")

    except requests.exceptions.RequestException as e:
        logging.error(f"Fehler beim Download der Bulk-Daten: {e}")
        raise
    except json.JSONDecodeError as e:
        logging.error(f"Fehler beim Parsen der JSON-Daten: {e}")
        raise
    except IOError as e:
        logging.error(f"Fehler beim Schreiben der Datenbankdatei: {e}")
        raise

def main():
    """Hauptfunktion zur Ausführung des Importers."""
    try:
        bulk_data_url = get_bulk_data_url()
        download_and_process_bulk_data(bulk_data_url)
    except (ValueError, requests.exceptions.RequestException) as e:
        logging.critical(f"Der Importprozess konnte nicht abgeschlossen werden: {e}")

if __name__ == "__main__":
    main()