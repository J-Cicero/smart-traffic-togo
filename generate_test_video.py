# generate_test_video.py - Generateur de video de test de trafic pour validation local
import cv2
import numpy as np

def create_sample_traffic_video(output_path="test_traffic.mp4", num_frames=300, width=640, height=480, fps=30):
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    for frame_idx in range(num_frames):
        # Fond sombre type asphalte
        frame = np.full((height, width, 3), (40, 40, 40), dtype=np.uint8)

        # Tracer marquages routiers (lignes jaunes au centre)
        cv2.line(frame, (width // 2, 0), (width // 2, height), (0, 255, 255), 2)
        cv2.rectangle(frame, (50, 50), (width - 50, height - 50), (100, 100, 100), 2) # Zone ROI

        # Titre d'affichage
        cv2.putText(frame, f"Flux Video Test Trafic - Frame {frame_idx+1}/{num_frames}", (20, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # Simulation visuelle de vehicules en mouvement
        pos_y_car = (frame_idx * 4) % height
        pos_y_moto = (frame_idx * 6) % height
        pos_y_truck = (frame_idx * 2) % height

        # Rectangle representant une voiture
        cv2.rectangle(frame, (150, pos_y_car), (220, pos_y_car + 60), (0, 0, 255), -1)
        cv2.putText(frame, "Voiture", (150, pos_y_car - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

        # Rectangle representant une moto
        cv2.rectangle(frame, (350, pos_y_moto), (380, pos_y_moto + 30), (0, 255, 0), -1)
        cv2.putText(frame, "Moto", (350, pos_y_moto - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

        # Rectangle representant un camion
        cv2.rectangle(frame, (450, pos_y_truck), (550, pos_y_truck + 120), (255, 0, 0), -1)
        cv2.putText(frame, "Camion", (450, pos_y_truck - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

        out.write(frame)

    out.release()
    print(f"[OK] Video de test generee avec succes: {output_path}")

if __name__ == "__main__":
    create_sample_traffic_video()
