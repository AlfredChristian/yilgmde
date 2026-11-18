# Modèles embarqués

`face_detection_yunet_2023mar.onnx` : détecteur de visages **YuNet** (230 Ko), du dépôt
[opencv/opencv_zoo](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet),
licence MIT. Utilisé par `backend/masquage.py` pour flouter les visages (D57). Sans ce fichier,
le masquage revient aux cascades de Haar fournies avec OpenCV.
