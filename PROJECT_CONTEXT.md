# PROJECT_CONTEXT  Traffic Togo
## But
Système de régulation adaptative des feux de circulation pour Lomé (Togo). Des caméras observent chaque approche d'un carrefour. Un Raspberry Pi local compte les véhicules par classe. Un calcul propose les durées de vert. Un mécanisme de sécurité déterministe vérifie et applique. Si l'IA, les caméras ou le réseau échouent, le carrefour passe seul en mode classique (temps fixes). Des opérateurs humains supervisent.
État actuel : prototype logiciel V0, sans matériel ni vision. Tout est testé avec un simulateur de trafic.
Environnement : Windows, PowerShell, Python 3.12, .venv à la racine. Dépôt GitHub J-Cicero/smart-traffic-togo, branche restart.
## Règles de sécurité (non négociables)
- Jamais deux mouvements en conflit au vert en même temps.
- L' Cycle d'une phase : VERT  JAUNE  TOUT_ROUGE  ROUGE. Jamais de passage direct du vert au rouge.
- Bascule automatique et locale vers le mode classique si les mesures manquent ou sont invalides. Retour à l'adaptatif seulement après plusieurs cycles de mesures valides, à un moment sûr.
- Les paramètres de sécurité sont dans une configuration, jamais en dur. Valeurs provisoires : vert min 10 s, vert max 60 s, jaune 3 s, tout-rouge entre 0 et 2 s (0 = passage direct d'un groupe au rouge et de l'autre au vert ; valeur à décider). À confirmer avec les autorités.
## Modèle métier
- Intersection  Branches (directions d'accès, azimut horaire : 0° Nord, 90° Est, 180° Sud, 270° Ouest)  Voies (ENTRANTE ou SORTANTE, avec une position).
- Décision du porteur du projet : angle_degres est obligatoire (nombre fini entre 0 et 360). Ce n'est pas hérité de l'ancien code.
- Phase = ensemble de branches servies ensemble, avec un ordre. Un carrefour peut avoir 2 phases (Nord-Sud / Est-Ouest) ou 4 phases (une par branche). Le code ne doit jamais supposer 2 phases.
- Conflit = deux branches qui ne doivent jamais être au vert ensemble. Les conflits sont déclarés dans la configuration. Une phase est invalide si elle contient deux branches en conflit.
- Premier périmètre : carrefours à 4 branches. Carrefours en T, à 6 ou 8 branches plus tard.
- Classes de véhicules : MOTO, TRICYCLE, VOITURE, MINIBUS, BUS, CAMION. Le poids n'est pas mesuré : la classe visuelle sert d'indicateur. Chaque classe a un temps de passage (intervalle entre deux véhicules) en dixièmes de seconde, entier naturel. Valeurs provisoires à calibrer sur le terrain.
- Mesure = comptes par classe et par voie sur une période, avec horodatage, durée, confiance et version du modèle. C'est l'entrée du calcul de durée. La vision la produira plus tard.
