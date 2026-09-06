import json
import requests

USER_AGENT = "Musixmatch/2025120901 CFNetwork/1404.0.5 Darwin/22.3.0"


class MusixMatchAPI:

    def __init__(self, proxies=None):
        self.base_url = "https://apic-appmobile.musixmatch.com/ws/1.1/"
        self.headers = {
            "x-mxm-app-version": "10.1.1",
            "User-Agent": USER_AGENT,
        }
        self.proxies = proxies
        self.usertoken = self.get_user_token()

    def get_user_token(self) -> str:
        url = f"{self.base_url}token.get"
        params = {"app_id": "mac-ios-v2.0"}
        try:
            response = requests.get(
                url,
                params=params,
                headers=self.headers,
                proxies=self.proxies,
                timeout=8,
            )
            data = response.json()
            if data.get("message", {}).get("header", {}).get("status_code") == 200:
                return data["message"]["body"]["user_token"]
        except Exception as e:
            print(f"[AVISO] Falha ao obter token automático: {e}")
        return ""

    def make_request(self, endpoint, params) -> dict:
        url = f"{self.base_url}{endpoint}"
        params.update({"format": "json", "app_id": "mac-ios-v2.0"})
        if self.usertoken:
            params["usertoken"] = self.usertoken

        response = requests.get(
            url, params=params, headers=self.headers, proxies=self.proxies, timeout=8
        )
        return response.json()

    def search_tracks(self, track_name, artist_name=None) -> dict:
        params = {"f_has_lyrics": "true", "page_size": 1, "page": 1}
        if track_name:
            params["q_track"] = track_name
        if artist_name:
            params["q_artist"] = artist_name
        return self.make_request("track.search", params)

    def get_track_translations(self, track_id, selected_language="pt") -> dict:
        params = {"track_id": track_id, "selected_language": selected_language}
        return self.make_request("crowd.track.translations.get", params)

    def get_track_subtitle(self, track_id) -> dict:
        params = {"track_id": track_id, "subtitle_format": "lrc"}
        return self.make_request("track.subtitle.get", params)


if __name__ == "__main__":
    api = MusixMatchAPI()

    nome_musica = "Blinding Lights"
    artista = "The Weeknd"
    print(f"Pesquisando pela música: '{artista} - {nome_musica}'...")

    search_result = api.search_tracks(track_name=nome_musica, artist_name=artista)
    track_list = search_result.get("message", {}).get("body", {}).get("track_list", [])

    if track_list:
        track = track_list[0]["track"]
        track_id = track["track_id"]
        print(
            f"Encontrado: {track['artist_name']} - {track['track_name']} (ID: {track_id})"
        )

        # 1. Busca as legendas sincronizadas (LRC)
        print("Baixando letras sincronizadas...")
        sub_data = api.get_track_subtitle(track_id)
        subtitle_body = (
            sub_data.get("message", {})
            .get("body", {})
            .get("subtitle", {})
            .get("subtitle_body", "")
        )

        # 2. Busca as traduções
        print("Baixando traduções para português...")
        trans_data = api.get_track_translations(track_id, "pt")
        translations_list = (
            trans_data.get("message", {}).get("body", {}).get("translations_list", [])
        )

        # Cria um dicionário de mapeamento: linha original -> tradução
        translation_map = {}
        for item in translations_list:
            trans = item.get("translation", {})
            original = trans.get("snippet", "").strip()
            translation = trans.get("description", "").strip()
            if original and translation:
                translation_map[original.lower()] = translation

        # 3. Processa o LRC e constrói o JSON bilíngue estruturado
        bilingual_lrc_json = []
        for line in subtitle_body.splitlines():
            if "]" in line:
                parts = line.split("]", 1)
                timestamp = parts[0] + "]"
                original_text = parts[1].strip() if len(parts) > 1 else ""

                # Procura a tradução correspondente (ignorando maiúsculas/minúsculas)
                translated_text = translation_map.get(original_text.lower(), "")

                bilingual_lrc_json.append(
                    {
                        "timestamp": timestamp,
                        "original": original_text,
                        "translation": translated_text,
                    }
                )

        # Salva o resultado em um arquivo JSON estruturado
        output_filename = "bilingual_lrc.json"
        with open(output_filename, "w", encoding="utf-8") as f:
            json.dump(bilingual_lrc_json, f, indent=4, ensure_ascii=False)

        print(f"\n--- Sucesso ---")
        print(f"JSON de LRC bilíngue gerado e salvo em: '{output_filename}'")
        print("\nExemplo das primeiras linhas geradas:")
        print(json.dumps(bilingual_lrc_json[:3], indent=4, ensure_ascii=False))

    else:
        print("Nenhuma música encontrada.")
