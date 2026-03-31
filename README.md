# 🧠 Python Remote Shell (Windows)

> A simple educational project demonstrating remote command execution using Python sockets.

---

## 📌 Overview

This project shows how a **client machine connects to a listener (server)** and executes commands remotely.

* 🔹 Client connects to listener
* 🔹 Listener sends commands
* 🔹 Client executes and returns output

---

## ⚙️ Important Configuration

Before running the project, you **must update the target address** inside the code.

### 🔧 Replace This Value

```python
target_mac = "LISTNER_MAC-ADDR"
```

👉 Replace `LISTNER_MAC-ADDR` with the **MAC address of the listener device** on your network.

### 💡 Example

```python
target_mac = "00:1A:2B:3C:4D:5E"
```

---

## 🚀 Getting Started

### 1️⃣ Install Requirements

```bash
pip install -r requirements.txt
```

---

### 2️⃣ Start Listener (Server)

You can use a tool like netcat:

```bash
nc -lvnp 4455
```

---

### 3️⃣ Run Client

```bash
python client.py
```

---

## 🔄 How It Works

```text
[ Listener ] ---> sends command ---> [ Client ]
[ Listener ] <--- receives output <--- [ Client ]
```

* Client scans network to find listener using MAC address
* Establishes connection
* Executes commands sent by listener

---

## 🧪 Features

* Remote command execution
* Network discovery via MAC address
* Automatic connection handling
* Basic client-server communication

---

## 📦 Requirements

* Python 3.x

---

## ⚠️ Disclaimer

This project is intended for:

* Educational purposes
* Networking and cybersecurity learning
* Controlled and authorized environments only

❌ Do NOT use this on systems without permission.

---

## 💡 Notes for Beginners

* Make sure both devices are on the **same network**
* Ensure firewall allows connections on the chosen port
* Double-check the MAC address format

---

## 🔮 Future Improvements

* Add encryption
* Improve error handling
* Support multiple clients
* Build a GUI interface

---

## 🙌 Author

Created for learning and experimentation.
