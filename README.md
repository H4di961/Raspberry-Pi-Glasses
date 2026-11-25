# Raspberry-Pi-Glasses

Projet de lunettes avec Raspberry Pi Zero 2 W et Camera Module 3 Wide NoIR : interface mobile, analyse Gemini, suivi du plateau et reconnaissance expérimentale de pièces d'échecs sur PC.

## Contenu

- `src/` et `public/` : interface web React / TanStack Start.
- `chess-mode/` : serveur PC Flask, suivi du plateau, état de partie et intégration Stockfish.
- `chess-training/` : photos annotées, outil de revue et scripts d'entraînement YOLO.
- `docs/PI-project_glasses-guide.pdf` : guide détaillé des commandes et de l'architecture.

La reconnaissance des pièces reste expérimentale. Les essais ont trouvé des pièces mais confondent encore souvent leur type. Le contrôleur d'échecs actuel utilise une position initiale connue et des coups confirmés manuellement.

## Interface web

```sh
npm ci
npm run dev
```

Créer `.env.local` à partir de `.env.example` et renseigner sa propre clé Gemini côté serveur. Ne jamais publier ce fichier. L'accès au modèle Gemini dépend du compte et des modèles disponibles.

## Échecs sur PC

Consulter `chess-mode/README.md` pour les dépendances, Stockfish, la calibration et les commandes. Configurer `PI_CAMERA_URL` avec l'adresse actuelle du Pi ; une adresse locale codée par défaut peut ne pas correspondre à votre réseau.

Les poids des modèles, Stockfish, les environnements Python, les téléchargements de jeux de données externes et les sorties d'entraînement ne sont pas inclus. Les scripts et résultats documentés sont conservés. Les licences des dépendances et jeux de données s'appliquent séparément.

## Entraînement

Consulter `chess-training/README.md`. Les annotations actuelles se trouvent dans `chess-training/dataset/annotations-reviewed.json`. Ouvrir `chess-training/dataset/review.html` pour les revoir. Les scripts d'export produisent les labels YOLO à partir des images locales et vérifient leurs empreintes.

## Partie Raspberry Pi

Le serveur caméra actif se trouve sur le Pi dans `/home/hadi/lens-camera/server.py`. Ce fichier n'était pas disponible dans la copie PC au moment de cette publication et n'est donc pas inclus ici. Le guide PDF décrit son installation et le service `lens-camera.service`. Ce dépôt n'est pas encore une sauvegarde complète de la carte SD du Pi.
