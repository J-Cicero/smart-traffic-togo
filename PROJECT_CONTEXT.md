# PROJECT_CONTEXT — Traffic Togo

## But
Système de régulation adaptative des feux de circulation pour Lomé (Togo). Des caméras observent chaque approche d'un carrefour. Un Raspberry Pi local compte les véhicules par classe. Un calcul propose les durées de vert. Un mécanisme de sécurité déterministe vérifie et applique. Si l'IA, les caméras ou le réseau échouent, le carrefour passe seul en mode classique (temps fixes). Des opérateurs humains supervisent.
État actuel : prototype logiciel V0, sans matériel ni vision. Tout est testé avec un simulateur de trafic.
Environnement : Windows, PowerShell, Python 3.12, .venv à la racine. Dépôt GitHub J-Cicero/smart-traffic-togo, branche restart.

## Règles de sécurité (non négociables)
- Jamais deux mouvements en conflit au vert en même temps.
- L'IA propose ; le module regulation borne et vérifie ; seul regulation commande les feux.
- Cycle d'une phase : VERT → JAUNE → TOUT_ROUGE → ROUGE. Jamais de passage direct du vert au rouge.
- Bascule automatique et locale vers le mode classique si les mesures manquent ou sont invalides. Retour à l'adaptatif seulement après plusieurs cycles de mesures valides, à un moment sûr.
- Les paramètres de sécurité sont dans une configuration, jamais en dur. Valeurs provisoires : vert min 10 s, vert max 60 s, jaune 3 s, tout-rouge entre 0 et 2 s (0 = passage direct d'un groupe au rouge et de l'autre au vert ; valeur à décider). À confirmer avec les autorités.

## Modèle métier
- Intersection → Branches (directions d'accès, azimut horaire : 0° Nord, 90° Est, 180° Sud, 270° Ouest) → Voies (ENTRANTE ou SORTANTE, avec une position).
- Décision du porteur du projet : angle_degres est obligatoire (nombre fini entre 0 et 360). Ce n'est pas hérité de l'ancien code.
- Phase = ensemble de branches servies ensemble, avec un ordre. Un carrefour peut avoir 2 phases (Nord-Sud / Est-Ouest) ou 4 phases (une par branche). Le code ne doit jamais supposer 2 phases.
- Conflit = deux branches qui ne doivent jamais être au vert ensemble. Les conflits sont déclarés dans la configuration. Une phase est invalide si elle contient deux branches en conflit.
- Premier périmètre : carrefours à 4 branches. Carrefours en T, à 6 ou 8 branches plus tard.
- Classes de véhicules : MOTO, TRICYCLE, VOITURE, MINIBUS, BUS, CAMION. Le poids n'est pas mesuré : la classe visuelle sert d'indicateur. Chaque classe a un temps de passage (intervalle entre deux véhicules) en dixièmes de seconde, entier naturel. Valeurs provisoires à calibrer sur le terrain.
- Mesure = comptes par classe et par voie sur une période, avec horodatage, durée, confiance et version du modèle. C'est l'entrée du calcul de durée. La vision la produira plus tard.
- Caméras : une caméra et un équipement Edge sont rattachés à un carrefour. Une ZoneComptage relie une caméra et une voie entrante. L'adresse du flux vidéo n'est jamais écrite dans un fichier : seulement le nom d'une variable d'environnement.
- Calcul de durée : fonction pure, formule initiale simple (délai de démarrage + temps de passage × file pondérée, bornée). Toute formule doit être validée en simulation contre les temps fixes avant d'être retenue. Aucune formule n'est définitive.

## Architecture
Monolithe modulaire FastAPI, Python 3.12, un seul dépôt.
- app/core : configuration, plus tard base de données.
- app/intersection : topologie, phases, conflits.
- app/regulation : machine à états des feux, sécurité, plan classique, modes.
- app/observation : classes de véhicules, mesures, équipements, caméras, zones (pas de YOLO ici).
- app/intelligence : calcul de durée.
- app/iam, app/supervision : plus tard.
- edge/ : code du Raspberry Pi (capture, YOLO). sim/ : simulateur. tests/ : miroir de app/.
- _legacy/ : ancien code, à consulter seulement. Tag git archive-avant-reset.

Fichiers par module (créés seulement quand ils servent) : entities.py (objets métier), validator.py, service.py (logique métier), exceptions.py ; plus tard models.py (tables), repository.py (CRUD et recherches), schemas.py (API), controller.py (routes).
Dépendances : controller → service → repository → models. entities.py et validator.py n'importent ni FastAPI, ni SQLAlchemy, ni Pydantic. Un module n'importe d'un autre que ses entities et son service. regulation et intelligence sont du Python pur. Aucune relation ORM OneToMany ou ManyToMany, aucune collection d'entités dans une entité : les liens sont des références par identifiant.
Identifiants : les entités utilisent des identifiants str (id_intersection, id_branche, id_voie). À la persistance, models.py portera un id entier interne et un tracking_id UUID, et repository.py fera la conversion. L'API n'expose que le tracking_id.

## Ordre de réalisation
- [x] T1 squelette FastAPI /health, config, pytest, import-linter
- [ ] T2 charger un carrefour depuis un JSON et le valider
- [ ] T3 phases et conflits
- [ ] T3b persistance et CRUD de intersection, branche, voie (par tracking_id)
- [ ] T4 machine à états des feux
- [ ] T5 bornes de durée
- [ ] T6 plan classique
- [ ] T7 modes adaptatif / classique
- [ ] T8 contrat Mesure
- [ ] T8b catalogue des équipements, caméras et zones
- [ ] T9 simulateur de trafic synthétique
- [ ] T10 calcul de durée v1
- [ ] T11 boucle complète en simulation

## Règles de travail pour l'agent
1. Lire ce fichier avant chaque tâche.
2. Faire uniquement la tâche demandée : aucune fonctionnalité, fichier ou abstraction non demandés.
3. Pas de code factice : pas de pass, de NotImplementedError ni de valeur inventée renvoyée comme réelle.
4. Chaque comportement ajouté a un test avec de vraies assertions, y compris les cas limites.
5. Exécuter réellement pytest -q et lint-imports, corriger, puis conclure. Ne jamais écrire « devrait passer ».
6. Ne pas modifier l'architecture ni ces règles sans le dire au porteur du projet.
7. Si une décision manque, la signaler et proposer une option plutôt que d'inventer.
8. Ne pas modifier _legacy/.
9. Compte rendu final : fichiers créés, modifiés, déplacés ; commandes exécutées avec leur sortie réelle copiée ; nombre de tests ; ce qui n'est pas fait ou reste incertain ; explication simple de chaque choix.
10. À la fin de chaque tâche réussie (pytest -q et lint-imports passent) : git add -A ; vérifier avec git status qu'aucun .venv, __pycache__ ni .pytest_cache n'est ajouté ; commit « Tn : <titre> » ; git push origin restart ; copier la sortie du push dans le compte rendu. Si le push échoue, le dire clairement : ne jamais écrire que c'est poussé sans preuve. Ne jamais faire de force push.
11. Environnement Windows, PowerShell : ne pas utiliser grep, tree ni export ; utiliser Select-String, Get-ChildItem, $env:PATH et .\.venv\Scripts\python.exe. Si une commande n'existe pas, le dire au lieu de la simuler.

## Hors périmètre actuel
IAM, supervision, vision, territoire, piétons, priorité bus, ondes vertes, apprentissage par renforcement.
