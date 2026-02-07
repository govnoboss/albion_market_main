import subprocess
import hashlib

def demo_hwid():
    print("--- HWID Generation Demo ---")
    
    try:
        # 1. Motherboard Serial (via PowerShell - wmic is deprecated)
        cmd_mb = 'powershell -Command "Get-WmiObject Win32_BaseBoard | Select-Object -ExpandProperty SerialNumber"'
        print(f"\nRunning: {cmd_mb}")
        mb_serial = subprocess.check_output(cmd_mb, shell=True, stderr=subprocess.DEVNULL).decode().strip()
        print(f"-> Extracted MB Serial: '{mb_serial}'")
        
        if not mb_serial or mb_serial == "None":
            mb_serial = "UNKNOWN_MB"
            print("   (Using fallback: UNKNOWN_MB)")

        # 2. CPU ID (via PowerShell)
        cmd_cpu = 'powershell -Command "Get-WmiObject Win32_Processor | Select-Object -ExpandProperty ProcessorId"'
        print(f"\nRunning: {cmd_cpu}")
        cpu_id = subprocess.check_output(cmd_cpu, shell=True, stderr=subprocess.DEVNULL).decode().strip()
        print(f"-> Extracted CPU ID:    '{cpu_id}'")
        
        if not cpu_id or cpu_id == "None":
            cpu_id = "UNKNOWN_CPU"
            print("   (Using fallback: UNKNOWN_CPU)")
        
        # 3. Windows Machine GUID (Registry) - The most reliable one
        print(f"\nReading Registry: HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Cryptography -> MachineGuid")
        try:
             import winreg
             key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\Microsoft\\Cryptography", 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
             machine_guid, _ = winreg.QueryValueEx(key, "MachineGuid")
             winreg.CloseKey(key)
        except Exception as e:
             machine_guid = "UNKNOWN_GUID"
             print(f"Registry Error: {e}")
             
        print(f"-> Extracted GUID:      '{machine_guid}'")
        
        # 4. Combination
        raw_id = f"{mb_serial}_{cpu_id}_{machine_guid}"
        print(f"\nRaw String to Hash:   '{raw_id}'")
        
        # 5. Hashing
        hashed = hashlib.sha256(raw_id.encode()).hexdigest().upper()[:32]
        print(f"Final HWID (SHA256):  {hashed}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    demo_hwid()
