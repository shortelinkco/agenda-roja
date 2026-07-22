import requests
import json
import base64
from datetime import datetime, timedelta, timezone
import re
import time
import urllib.parse 
import os

# ==========================================================
# 1. ENLACES Y RED DE RESPALDOS (FUENTES DE AGENDA)
# ==========================================================
# MODO "PRINCIPAL + RESPALDO": El bot intentará extraer de la primera fuente.
# Si funciona, se detiene ahí. Solo si falla, pasará a las siguientes.
FUENTES_AGENDA = [
    "https://agenda18.com/agenda.json",               # FUENTE PRINCIPAL (Pelota Libre)
    "https://la20hd.com/eventos/json/agenda123.json", # Respaldo 1
    "https://ftvhd.com/diaries.json",                # Respaldo 2 (Fubolazo)
]

API_BANDERAS = "https://agenda18.com/agenda.json"
BASE_DOMAIN_IMG = "https://img.agenda18.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}

# ==========================================================
# 2. TRUCO ANTI-ANUNCIOS (LIMPIEZA DE REPRODUCTORES)
# ==========================================================
# Si el bot tiene que usar una fuente de respaldo llena de pop-ups, 
# usará este dominio para limpiar los reproductores (iframes).
DOMINIO_LIMPIO_ACTUAL = "la20hd.com" 

# ==========================================================
# 3. LÓGICA DE BANDERAS Y LOGOS (CEREBRO VISUAL)
# ==========================================================
def obtener_bandera(liga, encuentro):
    texto = (liga + " " + encuentro).lower()
    
    # --- DEPORTES NO-FÚTBOL (Íconos especiales) ---
    if "f1 " in texto or "formula 1" in texto or "fórmula 1" in texto or "f2 " in texto: return "https://cdn-icons-png.flaticon.com/512/3753/3753230.png"
    if "motogp" in texto or "moto gp" in texto: return "https://cdn-icons-png.flaticon.com/512/3204/3204646.png"
    if "rugby" in texto: return "https://cdn-icons-png.flaticon.com/512/4163/4163653.png"
    if "golf" in texto: return "https://cdn-icons-png.flaticon.com/512/5751/5751090.png"
    if "knockout" in texto or "boxeo" in texto or "ufc" in texto: return "https://cdn-icons-png.flaticon.com/512/3349/3349372.png"
    if "hockey" in texto: return "https://cdn-icons-png.flaticon.com/512/6253/6253160.png"
    if "tenis" in texto or "tennis" in texto: return "https://cdn-icons-png.flaticon.com/512/3312/3312932.png"
    if "básquet" in texto or "baloncesto" in texto or "nba" in texto: return "https://cdn-icons-png.flaticon.com/512/3311/3311822.png"
    if "nfl" in texto or "fútbol americano" in texto: return "https://cdn-icons-png.flaticon.com/512/123/123969.png"
    if "béisbol" in texto or "mlb" in texto: return "https://cdn-icons-png.flaticon.com/512/3311/3311818.png"

    # --- COMPETICIONES DE FÚTBOL ---
    if "champions" in texto or "campeones de la uefa" in texto: return "https://cdn-icons-png.flaticon.com/512/520/520786.png"
    if "libertadores" in texto: return "https://cdn-icons-png.flaticon.com/512/1043/1043444.png"
    if "sudamericana" in texto: return "https://cdn-icons-png.flaticon.com/512/3112/3112946.png"
    if "concacaf" in texto: return "https://cdn-icons-png.flaticon.com/512/9903/9903672.png" 
    if "afc" in texto or "asia" in texto: return "https://cdn-icons-png.flaticon.com/512/6104/6104033.png"
    if "fifa" in texto or "mundial" in texto or "conmebol" in texto or "clasificatorias" in texto: return "https://cdn-icons-png.flaticon.com/512/323/323326.png"

    # --- PAÍSES ---
    if "perú" in texto or "liga 1" in texto or "peruano" in texto or "alianza" in texto or "cristal" in texto or "universitario" in texto: return "https://flagcdn.com/w40/pe.png"
    if "argentina" in texto or "liga profesional" in texto or "copa de la liga" in texto or "boca" in texto or "river" in texto or "reserva" in texto: return "https://flagcdn.com/w40/ar.png"
    if "mexic" in texto or "liga mx" in texto or "américa" in texto or "cruz azul" in texto or "chivas" in texto: return "https://flagcdn.com/w40/mx.png"
    if "colombia" in texto or "betplay" in texto or "primera a" in texto or "nacional" in texto or "millonarios" in texto: return "https://flagcdn.com/w40/co.png"
    if "chile" in texto or "campeonato nacional" in texto or "colo colo" in texto or "u de chile" in texto: return "https://flagcdn.com/w40/cl.png"
    if "uruguay" in texto or "peñarol" in texto or "nacional" in texto or "segunda división" in texto: return "https://flagcdn.com/w40/uy.png"
    if "ecuador" in texto or "ligapro" in texto or "barcelona sc" in texto or "emelec" in texto: return "https://flagcdn.com/w40/ec.png"
    if "brasil" in texto or "brasileirão" in texto or "paulista" in texto or "flamengo" in texto or "palmeiras" in texto: return "https://flagcdn.com/w40/br.png"
    if "usa" in texto or "mls" in texto or "estados unidos" in texto or "inter miami" in texto: return "https://flagcdn.com/w40/us.png"
    if "españa" in texto or "laliga" in texto or "copa del rey" in texto or "real madrid" in texto or "barcelona" in texto: return "https://flagcdn.com/w40/es.png"
    if "inglaterra" in texto or "premier" in texto or "championship" in texto or "fa cup" in texto or "liverpool" in texto or "city" in texto: return "https://flagcdn.com/w40/gb-eng.png"
    if "italia" in texto or "serie a" in texto or "juventus" in texto or "milan" in texto or "inter" in texto: return "https://flagcdn.com/w40/it.png"
    if "alemania" in texto or "bundesliga" in texto or "bayern" in texto: return "https://flagcdn.com/w40/de.png"
    if "francia" in texto or "ligue 1" in texto or "psg" in texto: return "https://flagcdn.com/w40/fr.png"
    if "arabia" in texto or "pro league" in texto or "al nassr" in texto: return "https://flagcdn.com/w40/sa.png"
    
    # Balón por defecto
    return "https://cdn-icons-png.flaticon.com/512/53/53283.png"

def desencriptar_enlace(iframe_str):
    try:
        if 'r=' in str(iframe_str):
            b64_texto = str(iframe_str).split('r=')[1].split('&')[0].split('"')[0]
            url_real = base64.b64decode(b64_texto).decode('utf-8')
            return url_real
    except Exception as e:
        pass
    return iframe_str

def procesar_fecha(fecha_str, hora_str):
    try:
        hora_str = str(hora_str)[:5] if hora_str else "00:00"
        fecha_hora_texto = f"{fecha_str} {hora_str}"
        fecha_obj = datetime.strptime(fecha_hora_texto, "%Y-%m-%d %H:%M")
        tz_origen = timezone(timedelta(hours=-5)) 
        fecha_obj = fecha_obj.replace(tzinfo=tz_origen)
        utc_obj = fecha_obj.astimezone(timezone.utc)
        return utc_obj.strftime("%Y-%m-%dT%H:%M:%SZ"), utc_obj
    except Exception as e:
        now_utc = datetime.now(timezone.utc)
        return now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"), now_utc

# Función auxiliar para extraer datos JSON anidados sin generar errores
def obtener_anidado(diccionario, *claves):
    for clave in claves:
        if isinstance(diccionario, dict):
            diccionario = diccionario.get(clave)
        else:
            return None
    return diccionario

def extraer_partidos():
    timestamp = int(time.time() * 1000)
    
    print(f"[*] FASE 1: Extrayendo imágenes originales (Banderas/Logos)...")
    diccionario_banderas = {}
    try:
        res_banderas = requests.get(f"{API_BANDERAS}?_={timestamp}", headers=HEADERS, timeout=15)
        if res_banderas.status_code == 200:
            datos_banderas = res_banderas.json()
            lista_fubolazo = datos_banderas if isinstance(datos_banderas, list) else datos_banderas.get("data", [])
            for item in lista_fubolazo:
                attrs = item.get("attributes", {})
                titulo = attrs.get("diary_description", "").strip().lower()
                try:
                    ruta_img = attrs.get("country", {}).get("data", {}).get("attributes", {}).get("image", {}).get("data", {}).get("attributes", {}).get("url", "")
                    if ruta_img and titulo:
                        diccionario_banderas[titulo] = ruta_img if ruta_img.startswith("http") else BASE_DOMAIN_IMG + ruta_img
                except:
                    pass
            print(f"    -> Se memorizaron {len(diccionario_banderas)} banderas en la memoria caché.")
    except Exception as e:
        print(f"[!] Advertencia: Error conectando al servidor de banderas ({e})")

    # =========================================================================
    # FASE 2: EXTRACCIÓN DE AGENDA (PRINCIPAL Y RESPALDOS)
    # =========================================================================
    print(f"[*] FASE 2: Buscando la agenda de partidos...")
    datos_json = None
    url_fuente_exitosa = ""
    
    for indice, url_fuente in enumerate(FUENTES_AGENDA):
        url_con_timestamp = f"{url_fuente}?_={timestamp}"
        
        # Diferenciamos visualmente la fuente principal de los respaldos
        if indice == 0:
            print(f"    -> [PRIORIDAD 1] Intentando actualizar desde FUENTE PRINCIPAL: {url_fuente} ...")
        else:
            print(f"    -> [RESPALDO {indice}] Intentando conectar a fuente alternativa: {url_fuente[:50]} ...")
            
        try:
            respuesta = requests.get(url_con_timestamp, headers=HEADERS, timeout=10)
            respuesta.raise_for_status() 
            posible_json = respuesta.json()
            
            # Soporte dual: Extrae datos tanto si es un Diccionario (Strapi) como si es una Lista directa
            if isinstance(posible_json, dict):
                posible_json = posible_json.get("data", posible_json.get("record", posible_json.get("response", [])))

            if isinstance(posible_json, list) and len(posible_json) > 0:
                print(f"    [+] ¡ÉXITO! Agenda descargada correctamente desde: {url_fuente}")
                datos_json = posible_json
                url_fuente_exitosa = url_fuente
                break # <--- Si funciona, rompe el bucle y no sigue buscando
            else:
                print(f"    [!] Conectó correctamente, pero el archivo JSON estaba vacío.")
                
        except Exception as e:
            print(f"    [X] Falló la conexión. Pasando a la siguiente fuente de respaldo... ({e})")
            continue 

    if not datos_json:
        print("[X] ERROR CRÍTICO: Todas las páginas (Principal y Respaldos) están caídas en este momento.")
        return None

    try:
        partidos_agrupados = {}
        
        # === NORMALIZACIÓN DEL DOMINIO PARA EXTRAER IMÁGENES EXACTAS ===
        if "pltvhd.com" in url_fuente_exitosa:
            url_fuente_base = "https://cdn.ftvhd.com" 
        elif "agenda18.com" in url_fuente_exitosa:
            url_fuente_base = "https://img.agenda18.com"
        else:
            url_fuente_base = "https://" + url_fuente_exitosa.split("/")[2] if url_fuente_exitosa else ""
        
        for item in datos_json:
            servers_temporales = []
            url_logo_directo = ""
            
            # --- Lógica para sitios modernos (CMS Strapi) ---
            if "attributes" in item:
                data_item = item["attributes"]
                titulo_completo = data_item.get("title", data_item.get("diary_description", "Partido en Vivo")).strip()
                
                fecha = data_item.get("date", data_item.get("diary_date", data_item.get("date_diary", "")))
                hora = data_item.get("time", data_item.get("diary_time", data_item.get("diary_hour", "")))
                estado = data_item.get("status", "").lower()
                
                rutas_img = [
                    obtener_anidado(data_item, "country", "data", "attributes", "image", "data", "attributes", "url"),
                    obtener_anidado(data_item, "league", "data", "attributes", "image", "data", "attributes", "url"),
                    obtener_anidado(data_item, "image", "data", "attributes", "url")
                ]
                for path in rutas_img:
                    if path and isinstance(path, str) and len(path) > 5:
                        if path.startswith("http"):
                            url_logo_directo = path
                        else:
                            url_logo_directo = url_fuente_base + path if path.startswith("/") else url_fuente_base + "/" + path
                        break
                
                if "embeds" in data_item and "data" in data_item["embeds"]:
                    for embed in data_item["embeds"]["data"]:
                        emb_attrs = embed.get("attributes", {})
                        e_name = emb_attrs.get("embed_name", "Opción")
                        e_iframe = emb_attrs.get("embed_iframe", "")
                        if e_iframe:
                            servers_temporales.append({"name": e_name, "iframe": e_iframe})
                            
                else:
                    link = data_item.get("link", data_item.get("url", data_item.get("embed_url", data_item.get("iframe", ""))))
                    canal = data_item.get("channel", data_item.get("diary_channel", data_item.get("canal", "")))
                    idioma = data_item.get("language", "Español")
                    if link:
                        c_name = str(canal).strip() if canal else f"Opción ({idioma})"
                        servers_temporales.append({"name": c_name, "iframe": link})
                        
            else:
                # --- Lógica para sitios con estructura clásica (Plana) ---
                titulo_completo = item.get("title", "Partido en Vivo").strip()
                fecha = item.get("date", item.get("date_diary", ""))
                hora = item.get("time", item.get("diary_hour", ""))
                estado = item.get("status", "").lower()
                
                rutas_img = [item.get("image"), item.get("country_image"), item.get("league_image")]
                for path in rutas_img:
                    if path and isinstance(path, str) and len(path) > 5:
                        if path.startswith("http"): url_logo_directo = path
                        else: url_logo_directo = url_fuente_base + path if path.startswith("/") else url_fuente_base + "/" + path
                        break

                link = item.get("link", item.get("url", item.get("embed_url", item.get("iframe", ""))))
                canal = item.get("channel", item.get("canal", ""))
                idioma = item.get("language", "Español")
                if link:
                    c_name = str(canal).strip() if canal else f"Opción ({idioma})"
                    servers_temporales.append({"name": c_name, "iframe": link})
            
            # Filtra partidos que ya dicen explícitamente "finalizado"
            if "finalizado" in estado or "terminado" in estado:
                 continue
                 
            datetime_utc, fecha_obj_utc = procesar_fecha(fecha, hora)
            
            # --- FILTRO POR TIEMPO: Borrar partidos después de 160 minutos ---
            ahora_utc = datetime.now(timezone.utc)
            minutos_transcurridos = (ahora_utc - fecha_obj_utc).total_seconds() / 60
            
            if minutos_transcurridos > 300:
                continue
            
            if not titulo_completo:
                continue
                
            # Crear una clave única para evitar partidos duplicados
            titulo_para_clave = re.sub(r'[^a-z0-9]', '', titulo_completo.lower())
            match_key = f"{datetime_utc}_{titulo_para_clave}"
            
            if match_key not in partidos_agrupados:
                liga = "Fútbol"
                encuentro = titulo_completo
                if ":" in titulo_completo:
                    partes = titulo_completo.split(":", 1)
                    liga = partes[0].strip()
                    encuentro = partes[1].strip()
                    
                home_team = encuentro
                away_team = ""
                if " vs " in encuentro.lower():
                    equipos = re.split(r'\s+vs\s+', encuentro, flags=re.IGNORECASE)
                    home_team = equipos[0].strip()
                    away_team = equipos[1].strip()
                
                bandera_magica = url_logo_directo
                
                # Asignación inteligente de banderas si la imagen cruda falló
                if not bandera_magica:
                    titulo_busqueda = titulo_completo.lower()
                    for clave_texto, url_logo in diccionario_banderas.items():
                         if (home_team.lower() in clave_texto and away_team.lower() in clave_texto) or (titulo_busqueda in clave_texto) or (clave_texto in titulo_busqueda):
                            bandera_magica = url_logo
                            break
                            
                if not bandera_magica:
                    bandera_magica = obtener_bandera(liga, encuentro)

                partidos_agrupados[match_key] = {
                    "datetime": datetime_utc,
                    "flagUrl": bandera_magica,
                    "league": liga,
                    "homeTeam": home_team,
                    "awayTeam": away_team,
                    "servers": []
                }

            # Procesamiento y limpieza de los reproductores
            for srv in servers_temporales:
                canal_nombre = srv["name"]
                link = srv["iframe"]
                
                # Intentar extraer un nombre de canal bonito de la URL si no viene bien definido
                if ("Opción" in canal_nombre or not canal_nombre) and "stream=" in str(link):
                    try:
                        canal_raw = str(link).split("stream=")[-1].split('"')[0].split('&')[0].replace("_", " ").upper()
                        canal_nombre = f"{canal_raw}"
                    except:
                        pass
                
                url_limpia = desencriptar_enlace(link)
                url_segura = url_limpia.replace("\\/", "/")
                
                # APLICACIÓN DEL TRUCO ANTI-ANUNCIOS
                if DOMINIO_LIMPIO_ACTUAL:
                    dominios_sucios = [
                        "pltvhd.com", "embed.pltvhd.com", 
                        "agenda18.com", "embed.agenda18.com",
                        "tiofutbol.com"
                    ]
                    for dominio in dominios_sucios:
                        if dominio in url_segura:
                            url_segura = url_segura.replace(dominio, DOMINIO_LIMPIO_ACTUAL)

                url_segura = url_segura.replace("canales.php", "canal.php")
                url_segura = url_segura.replace("embed.php", "canal.php")
                
                canal_nombre_norm = re.sub(r'[^a-z0-9]', '', canal_nombre.lower())
                url_segura_norm = re.sub(r'https?://', '', url_segura).strip('/')
                
                # Evitar insertar servidores duplicados (mismo link o mismo nombre exacto)
                existe = False
                for s in partidos_agrupados[match_key]["servers"]:
                    s_name_norm = re.sub(r'[^a-z0-9]', '', s["name"].lower())
                    s_url_norm = re.sub(r'https?://', '', s["url"]).strip('/')
                    
                    if url_segura_norm == s_url_norm or canal_nombre_norm == s_name_norm:
                        existe = True
                        break
                        
                if not existe:
                    partidos_agrupados[match_key]["servers"].append({
                        "name": canal_nombre,
                        "channel": canal_nombre,  
                        "url": url_segura,
                        "iframe": link 
                    })
                    
        # Ordenar partidos por hora de inicio cronológica
        partidos_extraidos = list(partidos_agrupados.values())
        partidos_extraidos.sort(key=lambda x: x["datetime"])
        
        for i, p in enumerate(partidos_extraidos):
            p["id"] = i + 1
            print(f"  -> {p['league']}: {p['homeTeam']} | {len(p['servers'])} links encontrados.")
            
        return partidos_extraidos
        
    except Exception as e:
        print(f"[X] ERROR al procesar los datos de la agenda (JSON): {e}")
        return None

def actualizar_nube(datos):
    if not datos:
        print("[!] No hay datos para subir. La agenda está vacía.")
        datos = []
        
    try:
        # Guardar en el servidor virtual de GitHub Actions
        with open('agenda.json', 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=4)
        print("[+] Documento local agenda.json guardado correctamente.")
        
        print("[*] Conectando con la API de GitHub para subir los cambios...")
        
        # === CONFIGURACIÓN GITHUB ========================================
        # Se obtiene el token de los secretos. Si no lo encuentra, usa un string de respaldo.
        github_token = os.environ.get("TOKEN_GITHUB", "TU_TOKEN_PERSONAL_AQUI") 
        
        # ⚠️ IMPORTANTE: DEBES PONER EL NOMBRE DE TU NUEVO REPOSITORIO AQUÍ
        repo = "shortelinkco/agenda-roja" # <---- CORREGIDO CON TU USUARIO REAL
        # =================================================================
        
        file_path = "agenda.json"
        url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
        
        headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        with open('agenda.json', 'rb') as file:
            content = file.read()
            encoded_content = base64.b64encode(content).decode('utf-8')
            
        get_res = requests.get(url, headers=headers)
        sha = ""
        if get_res.status_code == 200:
            sha = get_res.json()['sha']
            
        data = {
            "message": "Actualización automática de agenda 🔄 (Pirlo TV)",
            "content": encoded_content,
            "branch": "main"
        }
        if sha:
            data["sha"] = sha
            
        put_res = requests.put(url, headers=headers, data=json.dumps(data))
        
        if put_res.status_code in [200, 201]:
             print("[+] ¡ÉXITO! Agenda publicada en tu repositorio de GitHub directamente.")
        else:
             print(f"[X] Error al intentar subir a GitHub: {put_res.status_code} - {put_res.text}")
             
    except Exception as e:
        print(f"[X] Error general en el proceso de guardado: {e}")

if __name__ == "__main__":
    print("===================================================================")
    print("   BOT GITHUB ACTIONS: EJECUCIÓN AUTOMÁTICA (SITIO SATÉLITE)       ")
    print("===================================================================")
    
    ahora = datetime.now().strftime("%H:%M:%S")
    print(f"\n--- INICIANDO ESCANEO A LAS: {ahora} ---")
    
    datos = extraer_partidos()
    
    if datos is None: 
        datos = []
        
    actualizar_nube(datos)
    
    print("\n[i] El módulo de alertas por Telegram se ha desactivado intencionalmente para evitar spam.")
        
    print(f"\n[*] Escaneo finalizado a las: {datetime.now().strftime('%H:%M:%S')}.")
