# Coefficients PCU (Passenger Car Unit) valides pour le trafic local
PCU_WEIGHTS = {
    "moto": 0.30,
    "tricycle_passager": 0.55,
    "tricycle_cargo": 0.65,
    "voiture": 1.00,  # Regroupe voitures et taxis
    "minibus": 2.00,
    "bus": 2.75,
    "camion": 3.50,
    "urgence": 10.0,  # Poids tres eleve pour declenchement prioritaire
}

# Vehicles d'urgence declenchant la priorite absolue
EMERGENCY_CLASSES = ["ambulance", "pompier", "police", "urgence"]
EMERGENCY_GREEN_TIME = 25  # Duree prioritaire d'urgence (secondes)

# Configuration de la topologie du carrefour (3 voies en T ou 4 voies en croix)
INTERSECTION_TYPE = "3_WAY_T"  # Options : "4_WAY_CROSS" ou "3_WAY_T"


TOPOLOGY_CONFIGS = {
    "4_WAY_CROSS": {
        "name": "Carrefour en Croix (4 voies)",
        "lanes": ["Voie Nord", "Voie Sud", "Voie Est", "Voie Ouest"],
        "phases": [
            {
                "phase_id": "phase_nord_sud",
                "name": "Axe Nord-Sud",
                "green_lanes": ["Voie Nord", "Voie Sud"],
                "red_lanes": ["Voie Est", "Voie Ouest"],
            },
            {
                "phase_id": "phase_est_ouest",
                "name": "Axe Est-Ouest",
                "green_lanes": ["Voie Est", "Voie Ouest"],
                "red_lanes": ["Voie Nord", "Voie Sud"],
            },
        ],
    },
    "3_WAY_T": {
        "name": "Intersection en T (3 voies)",
        "lanes": ["Voie Nord", "Voie Sud", "Voie Est"],
        "phases": [
            {
                "phase_id": "phase_axe_principal",
                "name": "Axe Principal (Nord-Sud)",
                "green_lanes": ["Voie Nord", "Voie Sud"],
                "red_lanes": ["Voie Est"],
            },
            {
                "phase_id": "phase_voie_secondaire",
                "name": "Insertion Voie Secondaire (Est)",
                "green_lanes": ["Voie Est"],
                "red_lanes": ["Voie Nord", "Voie Sud"],
            },
        ],
    },
}

# Parametres de vision et de flux video
VISION_CONFIG = {
    "CONF_THRESHOLD": 0.35,  # Seuil minimal de confiance YOLO
    "ENABLE_TRACKING": True,  # Activer le tracking simple
    "ENABLE_GUI_PREVIEW": False,  # True pour afficher la fenetre OpenCV (si ecran disponible)
}

# Sources video par voie : dynamique selon la topologie choisie
CAMERA_SOURCES = {
    "Voie Nord": "test_traffic.mp4",
    "Voie Sud": "test_traffic.mp4",
    "Voie Est": "test_traffic.mp4",
    "Voie Ouest": "test_traffic.mp4",
}



# Zones d'interet (ROI) normalisees [ymin, xmin, ymax, xmax] (0.0 a 1.0)
# Permet de filtrer uniquement les vehicules dans la zone d'approche de la voie
ROI_CONFIG = {
    "Voie Nord": [0.2, 0.1, 0.9, 0.9],
    "Voie Sud": [0.2, 0.1, 0.9, 0.9],
    "Voie Est": [0.1, 0.2, 0.9, 0.9],
    "Voie Ouest": [0.1, 0.2, 0.9, 0.9],
}

# Seuils de securite temporelle (en secondes) pour les feux tricolores
TIME_LIMITS = {
    "T_MIN": 15,  # Temps minimal syndical
    "T_MAX": 75,  # Plafond maximal pour eviter l'asphyxie
    "T_BASE": 10,  # Constante de depart
    "K_FACTOR": 2.5,  # Facteur de conversion de la charge en secondes
}

# Facteur de lissage temporel (Moyenne mobile exponentielle)
SMOOTHING_ALPHA = 0.4

# Mode de repli de securite en cas de panne camera/IA
FAILSAFE_CONFIG = {
    "fallback_action": "fixed_timer",
    "default_duration": 30,
}

# Configuration du serveur API embarque et de la persistance
SERVER_CONFIG = {
    "ENABLE_API": True,
    "HOST": "0.0.0.0",
    "PORT": 8080,
    "LOG_FILE": "traffic_events.jsonl",
}