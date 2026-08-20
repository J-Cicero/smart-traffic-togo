# Contexte et Directives du Projet : Smart Traffic Lomé

## 🎯 Objectif Principal
Développer un MVP (Minimum Viable Product) de régulation intelligente des feux tricolores en temps réel pour un carrefour à Lomé (Togo), basé sur l'analyse de flux vidéo par IA et une pondération mathématique par Unités de Voitures Particulières (PCU).

## ⚠️ Règles d'Or et Sécurité (Safety First)
1. **La sécurité prime sur l'IA :** Le système de vision ne doit jamais piloter directement le matériel sans passer par des filtres de sécurité stricts ($T_{min}$ et $T_{max}$).
2. **Bornes temporelles obligatoires :** Aucun feu vert ne peut descendre sous $T_{min}$ (ex: 15s) ni dépasser $T_{max}$ (ex: 75s).
3. **Mode de repli (Fail-Safe) :** Si la caméra ou YOLOv8 plante, le système doit basculer automatiquement sur un mode de secours (cycle fixe ou clignotant de sécurité), sans bloquer le carrefour.

## 📊 Taxonomie et Coefficients PCU Validés
- `moto` : 0.30
- `tricycle_passager` : 0.55
- `tricycle_cargo` : 0.65
- `voiture` : 1.00 (regroupe voitures personnelles et taxis, officiels ou banalisés)
- `minibus` : 2.00
- `bus` : 2.75
- `camion` : 3.50

## 🏗️ Choix Architecturaux
- **Cœur de régulation :** Architecture modulaire et procédurale (pas de POO superflue) pour garantir le déterminisme, la simplicité et la lisibilité du chemin critique sur Raspberry Pi.
- **Découplage strict :** L'interface web / dashboard est totalement indépendante. Si le dashboard plante, le cœur de régulation continue de piloter les feux en arrière-plan.