# Smart Traffic Management System - Lomé (MVP)

Système embarqué de régulation dynamique des feux tricolores optimisé pour les conditions de circulation urbaine à Lomé.

## 🚀 Fonctionnalités de la V1
- **Vision par Ordinateur Edge Computing :** Détection et comptage par classes fonctionnelles via YOLOv8.
- **Moteur de Charge PCU :** Pondération intelligente de l'encombrement réel des voies (motos, tricycles, bus SOTRAL, camions).
- **Régulation Sécurisée :** Algorithme encadré par des fenêtres d'observation glissantes et des seuils stricts ($T_{min}$, $T_{max}$).
- **Découplage Matériel / Supervision :** Séparation étanche entre le script critique de contrôle des feux et l'interface de visualisation optionnelle.

## 🛠️ Stack Technique
- **Langage :** Python 3.10+
- **Vision :** Ultralytics YOLOv8, OpenCV
- **Matériel cibles :** Raspberry Pi / Jetson Nano, cartes de relais GPIO