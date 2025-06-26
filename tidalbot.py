import tidalapi
import os
import time
import json
from datetime import datetime
from difflib import SequenceMatcher
from tqdm import tqdm
import sys

# --- 1. CONFIGURAZIONE ---
NOME_PLAYLIST = "Massano @ Arena Maipu, Mendoza, Argentina 19.11.23 (3 Hour Set)"

LISTA_CANZONI = """
Massano - Welcome To The Underworld 
Angelov - Skedo
Volar - Ronto
EdOne - Don't You Know
Enamour - Marquina
Fideles & N1RVAAN - Jai
The Yard Woman - Habibti 
AVIRA & Maxim Lany - Focus
Grigoré - Combination N22
Un:said & The Yard Woman - Nobody
Citizen Kain & Aroze - ID
Vomee - On My Mind
Massano - ANA
Bigfett - The Jungle
FOTN & Marsden - Sabre
Dyzen - Laser Game
Massano - Talking
Eden Shalev - Papi (Bhabi)
Rebūke - Along Came Polly (Konstantin Sibold & CARMEE & ZAC Remix)
Adriatique ft. Delhia De France - The Future Is Unknown
SOEL - Reverie
Depeche Mode - Ghosts Again (Massano Remix)
Skrillex & Boys Noize - Fine Day Anthem
Oscar L - Again
Massano - Cybernova
Massano - Faithless
Chris Avantgarde - Perception
Massano - Shutdown
Hollt - World's Perception
Paul Ursin & Afterwards - Let Me
Kid Cudi - Day 'n' Nite (Konstantin Sibold Remix)
ANOTR & Abel Balder - Relax My Eyes (Agents Of Time Remix)
Massano ft. braev - Fade Away
"""

def datetime_serializer(obj):
    """Serializza oggetti datetime per JSON."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError('Type not serializable')

def salva_sessione(session, session_file):
    """Salva i token di sessione in un file JSON."""
    token_data = {
        'token_type': session.token_type,
        'access_token': session.access_token,
        'refresh_token': session.refresh_token,
        'expiry_time': session.expiry_time
    }
    
    with open(session_file, 'w') as f:
        json.dump(token_data, f, default=datetime_serializer)

def carica_sessione(session_file):
    """Carica i token di sessione da un file JSON."""
    with open(session_file, 'r') as f:
        token_data = json.load(f)
    
    # Converti la stringa expiry_time in datetime se necessario
    if isinstance(token_data['expiry_time'], str):
        try:
            token_data['expiry_time'] = datetime.fromisoformat(token_data['expiry_time'])
        except ValueError:
            pass
    
    return token_data

def ottieni_titolo_completo(traccia):
    """Crea un titolo completo per la traccia, includendo l'artista."""
    try:
        artista_nome = traccia.artist.name if hasattr(traccia.artist, 'name') else str(traccia.artist)
        return f"{artista_nome} - {traccia.title}"
    except:
        return f"Traccia ID: {traccia.id}"

def cerca_traccia(session, query):
    """Cerca una traccia con diversi metodi disponibili."""
    metodi_ricerca = [
        lambda: session.search('tracks', query, limit=1),
        lambda: session.search(query, limit=1)
    ]
    
    for metodo in metodi_ricerca:
        try:
            risultato = metodo()
            # Gestisci diversi formati di risposta
            if isinstance(risultato, dict) and 'tracks' in risultato:
                return risultato['tracks']
            elif hasattr(risultato, '__iter__') and not isinstance(risultato, str):
                return list(risultato)
            else:
                return [risultato] if risultato else []
        except (ValueError, AttributeError, TypeError):
            continue
    
    return []

def ricerca_intelligente(session, query, max_results=3):
    """Ricerca con multiple strategie e ranking dei risultati."""
    strategie = [
        query,  # Query originale
        query.replace(" - ", " "),  # Senza separatore
        " ".join(query.split(" - ")[::-1]) if " - " in query else query  # Invertito
    ]
    
    risultati_unici = {}
    
    for strategia in strategie:
        tracce = cerca_traccia(session, strategia)
        for traccia in tracce[:max_results]:
            if traccia.id not in risultati_unici:
                # Calcola similarity score
                titolo_completo = ottieni_titolo_completo(traccia)
                similarity = SequenceMatcher(None, query.lower(), titolo_completo.lower()).ratio()
                risultati_unici[traccia.id] = (traccia, similarity)
    
    # Ordina per similarity score
    return [traccia for traccia, _ in sorted(risultati_unici.values(), key=lambda x: x[1], reverse=True)]

def trova_o_crea_playlist(session, nome_playlist):
    """Cerca una playlist per nome. Se non la trova, la crea."""
    try:
        # Recupera tutte le playlist dell'utente
        playlists_utente = session.user.playlists()
        for p in playlists_utente:
            if p.name == nome_playlist:
                print(f"✅ Playlist '{nome_playlist}' trovata.")
                return p
        
        # Se il ciclo finisce, la playlist non è stata trovata
        print(f"⚠️ Playlist '{nome_playlist}' non trovata. La creo ora...")
        descrizione = "Playlist creata automaticamente con uno script Python."
        nuova_playlist = session.user.create_playlist(nome_playlist, descrizione)
        print(f"✅ Playlist '{nome_playlist}' creata con successo.")
        return nuova_playlist

    except Exception as e:
        print(f"❌ Errore durante la gestione della playlist: {e}")
        return None

def processa_canzoni_con_progress(session, playlist_target, canzoni_da_aggiungere, id_tracce_esistenti):
    """Processa canzoni con progress bar e statistiche."""
    stats = {
        'aggiunte': 0,
        'duplicate': 0,
        'non_trovate': 0,
        'errori': 0
    }
    
    with tqdm(total=len(canzoni_da_aggiungere), desc="Processando canzoni") as pbar:
        for riga_canzone in canzoni_da_aggiungere:
            query_ricerca = riga_canzone.strip()
            if not query_ricerca:
                pbar.update(1)
                continue
            
            pbar.set_postfix_str(f"Ricerca: {query_ricerca[:30]}...")
            
            tracce_trovate = ricerca_intelligente(session, query_ricerca)

            if tracce_trovate:
                traccia_trovata = tracce_trovate[0]
                titolo_completo = ottieni_titolo_completo(traccia_trovata)
                
                if traccia_trovata.id in id_tracce_esistenti:
                    print(f"🟡 GIÀ PRESENTE: '{titolo_completo}' è già nella playlist.\n")
                    stats['duplicate'] += 1
                else:
                    try:
                        playlist_target.add([traccia_trovata.id])
                        id_tracce_esistenti.add(traccia_trovata.id)
                        print(f"🟢 AGGIUNTA: '{titolo_completo}' alla playlist '{NOME_PLAYLIST}'.\n")
                        stats['aggiunte'] += 1
                    except Exception as e:
                        print(f"🔴 ERRORE AGGIUNTA: Non è stato possibile aggiungere '{titolo_completo}'. Errore: {e}\n")
                        stats['errori'] += 1
            else:
                print(f"🔴 NON TROVATA: Nessuna canzone trovata per '{query_ricerca}'.\n")
                stats['non_trovate'] += 1
            
            pbar.update(1)
            time.sleep(1)
    
    print(f"""
📊 Statistiche finali:
   ✅ Aggiunte: {stats['aggiunte']}
   🟡 Duplicate: {stats['duplicate']}
   ❌ Non trovate: {stats['non_trovate']}
   🔴 Errori: {stats['errori']}
    """)

def main():
    """Funzione principale dello script."""
    # --- 2. AUTENTICAZIONE ---
    session = tidalapi.Session()
    
    session_file = 'tidal_session.json'
    try:
        if os.path.exists(session_file):
            # Carica la sessione esistente
            token_data = carica_sessione(session_file)
            success = session.load_oauth_session(
                token_data['token_type'],
                token_data['access_token'],
                token_data['refresh_token'],
                token_data['expiry_time']
            )
            
            if success:
                print("✅ Sessione Tidal caricata con successo.")
            else:
                print("⚠️ Sessione scaduta, richiesta nuova autenticazione...")
                raise Exception("Sessione scaduta")
        else:
            raise FileNotFoundError("Nessun file di sessione trovato")
            
    except (FileNotFoundError, Exception):
        print("➡️ Avvio del processo di autenticazione...")
        session.login_oauth_simple()
        
        # Salva la nuova sessione
        salva_sessione(session, session_file)
        print("✅ Autenticazione completata e sessione salvata.")
    
    # Verifica che il login sia andato a buon fine
    if not session.check_login():
        print("❌ Login fallito")
        return
        
    print("-" * 40)
    # Usa attributi esistenti
    try:
        if hasattr(session.user, 'username') and session.user.username:
            print(f"Login effettuato come: {session.user.username}")
        else:
            print(f"Login effettuato come utente ID: {session.user.id}")
    except Exception as e:
        print(f"Login effettuato con successo (ID: {session.user.id})")
    print("-" * 40)

    # --- 3. GESTIONE PLAYLIST E CANZONI ---
    playlist_target = trova_o_crea_playlist(session, NOME_PLAYLIST)
    if not playlist_target:
        return # Esce se non è stato possibile trovare o creare la playlist

    # Ottiene gli ID di tutte le tracce già presenti per un controllo rapido
    try:
        tracce_esistenti = playlist_target.tracks()
        # Usiamo un 'set' per controlli di duplicati super veloci
        id_tracce_esistenti = {t.id for t in tracce_esistenti}
        print(f"La playlist contiene già {len(id_tracce_esistenti)} tracce.")
        print("-" * 40)
    except Exception as e:
        print(f"❌ Errore nel recuperare le tracce dalla playlist: {e}")
        return

    # Processa la lista di canzoni da aggiungere
    canzoni_da_aggiungere = LISTA_CANZONI.strip().split('\n')

    processa_canzoni_con_progress(session, playlist_target, canzoni_da_aggiungere, id_tracce_esistenti)

    print("✅ Operazione completata.")

if __name__ == "__main__":
    main()
