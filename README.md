# Scribe

Scribe est un outil en ligne de commande qui transforme un enregistrement audio (réunion, cours, note vocale) en compte rendu écrit et structuré.

Il fonctionne en trois étapes, orchestrées par un agent chef d'orchestre :
1. **Transcription** : l'audio est converti en texte brut via un modèle Speech-to-Text.
2. **Modération** : la transcription est analysée pour détecter une éventuelle tentative de prompt injection avant d'être transmise à l'étape suivante.
3. **Compte rendu** : si la transcription est jugée saine, le texte brut est reformulé par un LLM en un compte rendu structuré (titre, résumé, points clés, décisions/actions), puis sauvegardé en Markdown.

Les deux modèles sont appelés via l'API serverless de [Groq](https://console.groq.com/docs/overview).

## Installation

```bash
git clone https://github.com/Loulou441/scribe
cd scribe
python -m venv .venv
source .venv/bin/activate  # sous Windows : venv\Scripts\activate
pip install -r requirements.txt
```

Créer un fichier `.env` à la racine du projet contenant la clé API Groq :

```
GROQ_API_KEY=votre_cle_ici
```

Si cette variable est absente, `config.py` lève une `ValueError` explicite au démarrage.

## Utilisation

Le point d'entrée du pipeline complet est `ManagerAgent`, qui enchaîne transcription puis compte rendu :

```bash
python src/manager_agent.py chemin/vers/mon_fichier.wav
```

Le chemin du fichier audio est passé en **argument de ligne de commande** (`audio_file_path`, optionnel). Si aucun argument n'est donné, le script retombe sur `./audio_samples/test_audio_stt.mp4` par défaut :

```bash
python src/manager_agent.py
```

Le programme :
1. transcrit l'audio via `SpeechToTextAgent.get_text_from_audio()` ;
2. soumet la transcription à `ModeratorAgent.moderate_transcript()` pour détecter une tentative de prompt injection ;
3. si aucune injection n'est détectée, génère le compte rendu structuré via `SummaryAgent.generate_report()`, le convertit en Markdown et le sauvegarde automatiquement dans `comptes_rendus/` (le chemin du fichier sauvegardé est affiché dans la console) ;
4. affiche le dict résultat (`titre`, `resume`, `points_cles`, `decisions_actions`) clé par clé dans la console.

Si le fichier audio n'existe pas, ou si l'appel à l'API Groq échoue, une exception explicite est levée (`FileNotFoundError` ou `RuntimeError`) : `manager_agent.py` l'intercepte, affiche le message d'erreur, puis quitte avec un code de sortie 1.

> **Point d'attention** : si le `ModeratorAgent` détecte une tentative de prompt injection, `ManagerAgent.summaries_audio()` lève une `Exception` générique (pas `FileNotFoundError`/`RuntimeError`). Le bloc `try/except` de `manager_agent.py` ne capture pas ce cas précis : le programme s'arrête alors avec une trace Python complète plutôt qu'un message d'erreur propre.

### Transcription audio (Speech-to-Text)

La transcription est gérée par `src/speech_to_text_agent.py`, qui définit la classe `SpeechToTextAgent` (héritant de `Agent`). Elle appelle le modèle STT de Groq (`STT_MODEL` défini dans `config.py`, actuellement `whisper-large-v3-turbo`).

```python
from speech_to_text_agent import SpeechToTextAgent

agent = SpeechToTextAgent()
texte = agent.get_text_from_audio("audio_samples/mon_fichier.wav")
print(texte)
```

**Formats audio acceptés par l'API Groq** : `flac`, `mp3`, `mp4`, `mpeg`, `mpga`, `m4a`, `ogg`, `wav`, `webm`

**Taille maximale** : 25 Mo (tier gratuit) / 100 Mo (tier payant)

**Gestion des erreurs** :
- `FileNotFoundError` si le chemin du fichier audio n'existe pas
- `RuntimeError` si l'appel à l'API Groq échoue (réseau, quota dépassé, erreur serveur...)

Un échantillon audio léger (~30 secondes), `test_audio_stt.mp4`, est disponible dans `audio_samples/` pour tester la fonction sans avoir à enregistrer sa propre voix.

### Modération (détection de prompt injection)

La modération est gérée par `src/moderator_agent.py`, qui définit la classe `ModeratorAgent` (héritant de `Agent`). Elle appelle le même modèle LLM (`LLM_MODEL`) via l'API "chat completions", mais cette fois avec `response_format={"type": "json_object"}` explicitement activé.

`moderate_transcript(transcription_text)` retourne un dict avec le schéma suivant :

```json
{
  "prompt_injection": false,
  "raison": ""
}
```

Le prompt système, stocké dans `src/prompts_LLM/moderator_prompt_system.txt`, définit précisément ce qui constitue une tentative de détournement (instructions visant à faire ignorer les consignes de l'agent d'analyse, changement de rôle, demande de révéler le prompt système, injection de fausses balises système, demande d'exécuter une action externe, contenu obscurci...) par opposition à du contenu légitime rapporté dans une transcription vocale (consignes adressées à des tiers, impératifs faisant partie du propos). En cas de doute réel, le prompt demande au modèle de considérer le contenu comme légitime (`prompt_injection: false`).

Un second échantillon audio, `audio_samples/test_injection_text.mp4`, est fourni pour tester la détection sur un cas de tentative d'injection.

### Compte rendu structuré (chat completions)

La génération du compte rendu est gérée par `src/summary_agent.py`, qui définit la classe `SummaryAgent` (héritant de `Agent`). Elle appelle le modèle LLM de Groq (`LLM_MODEL` défini dans `config.py`, actuellement `llama-3.1-8b-instant`) via l'API "chat completions".

`generate_report()` retourne un **dict Python** avec le schéma suivant :

```json
{
  "titre": "Point d'avancement projet Scribe",
  "resume": "L'équipe a fait le point sur l'avancement du module de transcription...",
  "points_cles": [
    "Le modèle whisper-large-v3-turbo est retenu pour la transcription",
    "Le module de compte rendu utilise désormais le JSON mode de Groq"
  ],
  "decisions_actions": []
}
```

Le comportement du modèle est piloté par un **prompt système** stocké dans `src/prompts_LLM/summary_generator_prompt.txt`, qui impose au modèle de ne répondre qu'avec un JSON valide respectant ce schéma.

**Format de sortie imposé** :
- `titre` : titre du compte rendu
- `resume` : résumé de 3 à 5 lignes
- `points_cles` : liste des points clés
- `decisions_actions` : liste des décisions/actions **uniquement si elles sont explicitement présentes** dans l'audio — sinon un tableau **vide** (`[]`), le modèle n'invente rien pour la remplir.

**Gestion des erreurs** :
- `FileNotFoundError` si `src/prompts_LLM/summary_generator_prompt.txt` est introuvable
- `RuntimeError` si l'appel à l'API Groq échoue, ou si la réponse n'est pas un JSON valide

### Mise en forme Markdown datée

La mise en forme et la sauvegarde sont également portées par `SummaryAgent`, via deux méthodes :
- `format_as_markdown(report)` : transforme le dict JSON en Markdown lisible et daté ;
- `save_markdown_report(markdown_text, output_dir="comptes_rendus")` : sauvegarde ce Markdown dans un fichier nommé `AAAA-MM-JJ_HHMMSS_compte-rendu.md`.

Exemple de rendu :

```markdown
# Point d'avancement projet Scribe

*Généré le 06/07/2026 à 09:32 par Scribe*

---

## 📝 Résumé

L'équipe a fait le point sur l'avancement du module de transcription...

## 🔑 Points clés

- whisper-large-v3-turbo retenu pour la transcription
- Le module de compte rendu utilise désormais le JSON mode de Groq

## ✅ Décisions et actions

*Aucune décision ou action explicite mentionnée dans cet enregistrement.*
```

Si `decisions_actions` (ou `points_cles`) est vide, la section affiche une note en italique plutôt qu'une liste — aucun contenu n'est inventé, c'est uniquement un texte de mise en forme.

### Orchestration (ManagerAgent)

`src/manager_agent.py` définit la classe `ManagerAgent`, qui instancie un `SpeechToTextAgent`, un `ModeratorAgent` et un `SummaryAgent`, et expose une seule méthode `summaries_audio(audio_file_path)` :
1. transcription de l'audio ;
2. modération de la transcription ;
3. si une injection est détectée, une `Exception` est levée avec la raison fournie par `ModeratorAgent` (aucun compte rendu n'est généré) ;
4. sinon, génération du compte rendu, mise en forme Markdown et sauvegarde automatique dans `comptes_rendus/` (le chemin du fichier est affiché), puis retour du dict du compte rendu.

## Structure du projet

```
scribe/
├── src/
│   ├── agent.py                 # classe de base Agent (client Groq, lecture de fichier)
│   ├── speech_to_text_agent.py  # SpeechToTextAgent : transcription audio via Groq
│   ├── moderator_agent.py       # ModeratorAgent : détection de prompt injection dans la transcription
│   ├── summary_agent.py         # SummaryAgent : génération + mise en forme + sauvegarde du compte rendu
│   ├── manager_agent.py         # ManagerAgent : orchestre transcription → modération → compte rendu
│   ├── config.py                # clé API et noms de modèles
│   └── prompts_LLM/
│       ├── moderator_prompt_system.txt
│       └── summary_generator_prompt.txt
├── audio_samples/               # fichiers audio (dont les échantillons de test)
├── comptes_rendus/              # comptes rendus générés (ignorés sauf l'exemple)
├── .env
├── .gitignore
├── LICENSE
├── requirements.txt
└── README.md
```

## Licence

Ce projet est distribué sous licence Apache 2.0. Voir le fichier `LICENSE` pour le texte complet.

## Statut

Projet en cours de développement dans le cadre du TP M2 MD5 — Git, GitHub et intégration d'IA serverless.

## Question de réflexion

1. pourquoi le .gitignore doit-il exister avant d'écrire la moindre ligne de code
manipulant des secrets ?

Il est important de mettre en place le gitignore le plus rapidement possible dans le projet car cea permet d'éviter toute erreur de push. En effet, il est facile d'oublier de ne pas push certaines données importantes (ex: clé groq) lors de commit. Il convient don de les exclure dès le départ afin de ne plus s'en préoccuper.

2. Quels modèles STT et LLM propose Groq aujourd'hui, et lesquels choisissez-vous ? Justifiez (qualité, vitesse, coût) dans le README.

- Le STT
Aujourd'hui, Groq propose deux modèles, `whisper-large-v3` et `whisper-large-v3-turbo`. Si on en croit la documentation, la différence entre les deux au niveau du WER est minime, pour un prix plus élevé et une vitesse plus lente au niveau de `whisper-large-v3`. 
Nous prendrons donc `whisper-large-v3-turbo` pour ce projet.

- Le LLM
Pour ce qui est du LLM, Groq propose de nombreux modèes comme `llama-3.1-8b-instant`, `llama-3.3-70b-versatile`, `openai/gpt-oss-20b` ou encore `openai/gpt-oss-120b`. Pour la tâche simple qui est de transformer la sortie brute du STT en rapport, `llama-3.1-8b-instant` est le plus adapté selon le rapport prix/ efficacité sur ce type de tâches.

3. Que renvoie exactement l'API en plus du texte (langue détectée, segments, horodatage...) ? Qu'est-ce qui pourrait être utile pour une évolution future de Scribe ?

Selon la documentation de Groq, la réponse contient, en plus du texte (`text`) dans le json de sortie donc il y a un exemple juste dessous:

```json
{
  "id": 8,
  "seek": 3000,
  "start": 43.92,
  "end": 50.16,
  "text": "document that the functional specification that you started to read through that isn't just the",
  "tokens": [51061, 4166, 300, 264, 11745, 31256],
  "temperature": 0,
  "avg_logprob": -0.097569615,
  "compression_ratio": 1.6637554,
  "no_speech_prob": 0.012814695
}
```

| Champ | Signification |
|---|---|
| `id` | numéro du segment dans l'audio |
| `seek` | position interne utilisée par le modèle (en centièmes de seconde) |
| `start` / `end` | horodatage de début/fin du segment, en secondes |
| `text` | texte transcrit pour ce segment |
| `tokens` | tokens internes du modèle (peu utile en pratique) |
| `temperature` | valeur de température utilisée pour ce segment (0 = déterministe) |
| `avg_logprob` | confiance moyenne du modèle sur ce segment (proche de 0 = bonne confiance) |
| `compression_ratio` | détecte les répétitions/bégaiements anormaux (valeur normale ≈ 1–2) |
| `no_speech_prob` | probabilité qu'il n'y ait pas de parole dans ce segment (silence, musique...) |

4. Quelle température choisissez-vous pour cet usage, et pourquoi ?

Vu qu'il est demandé à ce que le LLM n'hallicine en aucun cas, une température de 0 est requise.

5. Votre prompt système est envoyé à chaque requête : quel lien avec la notion de tokens en cache vue en cours ?

Vu que le prompt prompt système stocké dans `src/prompts_LLM/summary_generator_prompt.txt` est identique à chaque appel, Groq va mettre en cache les tokens du préfixe d'une requête lorsqu'il est réutilisé à l'identique entre plusieurs appels, pour éviter de le retraiter entièrement à chaque fois. Par conséquence, on aura temporairement un cout réduit vu que les tokens du prompt ne sont facturés/traités en entier que la première fois si le cache est actif ; les appels suivants avec le même préfixe bénéficient d'un tarif réduit sur ces tokens en cache. Et le modèle n'a pas besoin de recalculer l'attention sur tout le prompt système à chaque fois, ce qui accélère le temps de réponse.