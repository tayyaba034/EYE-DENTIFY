import cv2
import numpy as np
from ultralytics import YOLO
from collections import deque, Counter
import time


class ClothingColorDetector:
    def __init__(self):
        self.conf_threshold = 0.5
        self.history_len = 30

        # -------- USER INPUT COLOR --------
        self.target_color = input(
            "Enter color to find (Red, Green, Blue, Maroon, Black, etc): "
        ).strip().capitalize()
        print(f"[INFO] Target Color Set To: {self.target_color}")

        # -------- YOLOv8 --------
        self.model = YOLO("yolov8n.pt")

        # -------- FACE CASCADE --------
        haar_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.face_cascade = cv2.CascadeClassifier(haar_path)
        self.use_face_anchor = not self.face_cascade.empty()

        self.color_history = deque(maxlen=self.history_len)

        # -------- COLOR PROTOTYPES (BGR) --------
        self.colors_bgr = {
            "Red": (0, 0, 255),
            "Green": (0, 128, 0),
            "Blue": (255, 0, 0),
            "Yellow": (0, 255, 255),
            "Orange": (0, 165, 255),
            "Purple": (128, 0, 128),
            "Pink": (203, 192, 255),
            "White": (255, 255, 255),
            "Black": (0, 0, 0),
            "Grey": (128, 128, 128),
            "Cyan": (255, 255, 0),
            "Maroon": (0, 0, 128),
            "Navy": (128, 0, 0)
        }

        # -------- CONVERT TO LAB --------
        self.colors_lab = {}
        for name, bgr in self.colors_bgr.items():
            pixel = np.uint8([[bgr]])
            lab = cv2.cvtColor(pixel, cv2.COLOR_BGR2LAB)[0][0]
            self.colors_lab[name] = lab

    # -------- TORSO ROI --------
    def get_torso_roi(self, frame, px1, py1, px2, py2):
        person = frame[py1:py2, px1:px2]
        if person.size == 0:
            return None, None, "ERR"

        h, w, _ = person.shape
        mode = "Body"

        if self.use_face_anchor:
            gray = cv2.cvtColor(person, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
            if len(faces) > 0:
                fx, fy, fw, fh = faces[0]
                mode = "Face"
                y1 = int(fy + fh)
                y2 = min(h, y1 + int(4 * fh))
                x1 = max(0, int(fx - fw))
                x2 = min(w, int(fx + 2 * fw))
            else:
                y1, y2 = int(0.25 * h), int(0.75 * h)
                x1, x2 = int(0.2 * w), int(0.8 * w)
        else:
            y1, y2 = int(0.25 * h), int(0.75 * h)
            x1, x2 = int(0.2 * w), int(0.8 * w)

        roi = person[y1:y2, x1:x2]
        coords = (px1 + x1, py1 + y1, px1 + x2, py1 + y2)
        return roi, coords, mode

    # -------- WHITE BALANCE (FIXED) --------
    def apply_white_balance(self, image):
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB).astype(np.float32)

        avg_a = np.mean(lab[:, :, 1])
        avg_b = np.mean(lab[:, :, 2])

        lab[:, :, 1] -= (avg_a - 128)
        lab[:, :, 2] -= (avg_b - 128)

        lab[:, :, 1] = np.clip(lab[:, :, 1], 0, 255)
        lab[:, :, 2] = np.clip(lab[:, :, 2], 0, 255)

        lab = lab.astype(np.uint8)
        return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    # -------- COLOR CLASSIFICATION --------
    def classify_color(self, roi):
        # 🛑 Early black detection (stability)
        if np.mean(roi) < 40:
            return "Black"

        roi = self.apply_white_balance(roi)
        roi = cv2.resize(roi, (64, 64))

        data = roi.reshape((-1, 3)).astype(np.float32)

        _, labels, centers = cv2.kmeans(
            data, 3, None,
            (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0),
            10, cv2.KMEANS_RANDOM_CENTERS
        )

        labels_img = labels.reshape((64, 64))
        center_area = labels_img[16:48, 16:48]
        target_idx = Counter(center_area.flatten()).most_common(1)[0][0]

        target_bgr = np.uint8([[centers[target_idx]]])
        target_lab = cv2.cvtColor(target_bgr, cv2.COLOR_BGR2LAB)[0][0]

        min_dist = float("inf")
        final_color = "Unknown"

        for name, lab in self.colors_lab.items():
            dist = np.linalg.norm(target_lab - lab)
            if dist < min_dist:
                min_dist = dist
                final_color = name

        return final_color

    def smooth_prediction(self, color):
        self.color_history.append(color)
        return Counter(self.color_history).most_common(1)[0][0]

    # -------- MAIN LOOP --------
    def run(self):
        cap = cv2.VideoCapture(0)
        prev_time = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            curr_time = time.time()
            fps = int(1 / (curr_time - prev_time)) if prev_time else 0
            prev_time = curr_time

            cv2.putText(frame, f"FPS: {fps}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            results = self.model(frame, stream=True, classes=[0], verbose=False)

            main_box = None
            max_area = 0
            for r in results:
                for b in r.boxes:
                    x1, y1, x2, y2 = map(int, b.xyxy[0])
                    area = (x2 - x1) * (y2 - y1)
                    if area > max_area:
                        max_area = area
                        main_box = (x1, y1, x2, y2)

            if main_box:
                px1, py1, px2, py2 = main_box
                cv2.rectangle(frame, (px1, py1), (px2, py2), (0, 255, 0), 2)

                roi, coords, mode = self.get_torso_roi(frame, px1, py1, px2, py2)
                if roi is not None:
                    color = self.smooth_prediction(self.classify_color(roi))

                    match = color == self.target_color
                    match_text = "MATCH FOUND" if match else "MATCH NOT FOUND"
                    match_color = (0, 255, 0) if match else (0, 0, 255)

                    cv2.putText(frame, f"Detected: {color}",
                                (px1, py1 - 50), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                    cv2.putText(frame, f"Target: {self.target_color}",
                                (px1, py1 - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
                    cv2.putText(frame, match_text,
                                (px1, py1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, match_color, 2)

            cv2.imshow("Clothing Color Match System", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    ClothingColorDetector().run()
