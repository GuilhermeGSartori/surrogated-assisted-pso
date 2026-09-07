import socket
import joblib
import numpy as np


HOST = "127.0.0.1"
PORT = 5000

MODEL_PATH = "rf_model.joblib"


model = joblib.load(MODEL_PATH)


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:

    server.bind((HOST, PORT))
    server.listen()

    print(f"RF inference server listening on {HOST}:{PORT}")

    while True:

        conn, addr = server.accept()

        with conn:

            print(f"Connected: {addr}")

            data = conn.recv(4096)

            if not data:
                continue

            message = data.decode().strip()

            # Example:
            # 10.2,30.1,80.0,55.2,140.3,100.0,...

            features = [
                float(value)
                for value in message.split(",")
            ]

            ## aqui vai ter q clusterizar tambem
            
            X = np.array(features).reshape(1, -1)

            prediction = model.predict(X)[0]

            conn.sendall(
                f"{prediction}\n".encode()
            )