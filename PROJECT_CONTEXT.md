# TRAFFIC TOGO — CONTEXTE ET DIRECTIVES DU PROJET

> **Document de référence permanent.** Ce fichier doit être lu avant toute intervention importante et maintenu à jour uniquement lorsque des décisions structurantes sont explicitement validées.

---

## 1. Vision Globale de Traffic Togo

**Traffic Togo** est un système intelligent de surveillance, d'analyse et de régulation du trafic routier au Togo.

Son objectif global à moyen et long terme est de permettre une gestion coordonnée et sécurisée de la circulation à travers de multiples intersections de géométries variées (3, 4, 5 branches ou davantage), en s'appuyant sur :
1. **Modélisation métier complète et configurable des intersections** (branches, voies d'entrée/sortie, mouvements directionnels, incompatibilités entre mouvements, groupes de feux et phases de circulation).
2. **Moteur déterministe de gestion des phases et de régulation sécurisée** (filtrage de sécurité indépendant des agents IA).
3. **Observation du trafic** et traitement des données issues des caméras et de la vision par ordinateur.
4. **Agent intelligent local** pour chaque intersection (analyse locale et propositions de régulation).
5. **Agent central de coordination** à l'échelle du réseau (supervision des agents locaux et cohérence inter-carrefours).
6. **Modes de fonctionnement multiples** :
   - Régulation intelligente automatique.
   - Fonctionnement classique préconfiguré.
   - Modes de secours, de défaillance et de maintenance.
7. **Supervision humaine** permettant aux opérateurs de consulter, valider ou corriger les décisions dans le cadre de leurs habilitations.
8. **Organisation territoriale** rattachant les intersections aux régions et aux services techniques responsables.

---

## 2. État Actuel et Périmètre de Développement Actif

**Périmètre actif : BACKEND UNIQUEMENT — Socle Architectural & Domaine Métier `intersection` (Étape 1 : Topologie à entités indépendantes).**

### Ce qui est implémenté et opérationnel à ce stade :
- **Socle technique (`app/core/`)** : configuration technique globale de l'application (`ConfigurationApplication`, `Environnement`, `ErreurConfiguration`) et point d'entrée simple (`main.py` avec `charger_configuration`).
- **Topologie du domaine `app/intersection/` (Entités indépendantes)** :
  - Modèles métier purs et autonomes dans `app/intersection/models/topology.py` :
    - `Intersection` (`id_intersection`, `nom`, `description`)
    - `Branche` (`id_branche`, `id_intersection`, `nom`, `angle_degres`)
    - `Voie` (`id_voie`, `id_branche`, `nom`, `direction`, `position`)
    - `DirectionVoie` (`ENTRANTE`, `SORTANTE`)
  - Service de validation évolutive dans `app/intersection/services/intersection_validator.py` (`ValidateurIntersection`, `RapportValidationIntersection`, `AnomalieValidationIntersection`, `GraviteValidation`, `valider_intersection`, `obtenir_voies_entrantes`, `obtenir_voies_sortantes`) et exception métier `ErreurValidationIntersection`.
  - Trois étapes de validation sont actives :
    1. `"identite"` : identifiant, nom et description de l'intersection.
    2. `"topologie"` : cohérence du rattachement `Branche.id_intersection`, au moins 3 branches rattachées, unicité des `id_branche`, validité des angles.
    3. `"voies"` : cohérence du rattachement `Voie.id_branche`, au moins 1 voie par branche, unicité globale des `id_voie`, unicité des positions par `(id_branche, direction)`, validité de la direction et de la position.

### Prochaine sous-étape à concevoir/implémenter dans `app/intersection/` :
- Modélisation sous forme d'entités indépendantes des mouvements, des incompatibilités, des groupes de feux et des phases, ainsi que l'activation des étapes correspondantes dans `intersection_validator.py`.

---

## 3. Fonctionnalités Hors Périmètre Actuel (Phases Ultérieures)

Ne **pas** créer ni anticiper tant que l'étape correspondante n'est pas engagée :
- Les futurs domaines métier : `regulation` (dont $T_{min}$, $T_{max}$, durées de transition, calcul PCU), `vision` (caméras, OpenCV, YOLO), `agents` (locaux et central), `supervision` (opérateurs, régions).
- Les couches techniques non encore requises dans `intersection` : `repositories/`, `schemas/`, `routers/`.
- Un dossier `app/shared/` tant qu'aucun composant n'est réellement partagé entre plusieurs domaines actifs.
- Une base de données ou un ORM.
- Toute interface frontend, dashboard ou pilotage matériel de feux physiques.

---

## 4. Décisions Architecturales et Techniques Validées

1. **Architecture Modulithique structurée par Domaine Métier :**
   - Chaque domaine métier possède son propre périmètre (`app/intersection/` actuellement).
   - Séparation interne par couches : `models/` (modèles métier purs) et `services/` (règles et validations métier du domaine).
2. **Indépendance stricte des entités métier (Absence de relations One-to-Many / Many-to-Many imbriquées) :**
   - Chaque entité métier est autonome et possède son propre identifiant.
   - Aucune entité ne contient directement d'instances ou de collections d'autres entités.
   - Les associations entre entités sont représentées exclusivement par des identifiants explicites (`id_intersection`, `id_branche`, etc.).
   - La cohérence des associations est garantie par des services métier dédiés.
   - Dans la future couche de persistance, nous n'utiliserons pas de relations ORM (`OneToMany` / `ManyToMany` / `relationship()`).
3. **Convention de nommage Francophone (DDD en français) :**
   - Les noms des classes métier, de leurs attributs, méthodes et codes d'anomalies sont rédigés en français (`Intersection`, `Branche`, `Voie`, `DirectionVoie`, `ValidateurIntersection`, `valider_intersection`, etc.).
4. **Périmètre strict de `app/core/` :**
   - Réservé exclusivement à la configuration technique globale de l'application (`nom_application`, `environnement`, `mode_debug`).
5. **Indépendance absolue des modèles métier :**
   - Écrits en Python 3.10+ natif typé (`dataclasses(frozen=True, slots=True)`), sans dépendance envers un framework web ou un SGBD.
6. **Principe de sécurité routière (Safety First) :**
   - Les agents IA futurs ne commanderont jamais directement les feux ; toute décision passera par une validation déterministe.

---

## 5. Règles de Travail Obligatoires

1. Lire ce fichier avant toute intervention importante.
2. Respecter strictement le périmètre de l'étape active (aucun dossier vide, aucun domaine futur anticipé).
3. Appliquer systématiquement la **règle de contradiction constructive** : signaler toute proposition qui contredit une décision validée, mélange les responsabilités ou introduit une complexité prématurée.
4. Suivre le cycle progressif : Comprendre → Examiner → Proposer la conception → Attendre la validation → Implémenter le périmètre validé → Tester → Présenter les résultats.
