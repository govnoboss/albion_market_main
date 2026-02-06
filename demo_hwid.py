import subprocess
import hashlib

def demo_hwid():
    print("--- HWID Generation Demo ---")
    
    try:
        # 1. Motherboard Serial
        cmd_mb = "wmic baseboard get serialnumber"
        print(f"\nRunning: {cmd_mb}")
        mb_output = subprocess.check_output(cmd_mb, shell=True).decode()
        print(f"Output:\n{mb_output}")
        
        mb_serial = mb_output.split('\n')[1].strip()
        print(f"-> Extracted MB Serial: '{mb_serial}'")
        

        # 2. CPU ID
        cmd_cpu = "wmic cpu get processorid"
        print(f"\nRunning: {cmd_cpu}")
        cpu_output = subprocess.check_output(cmd_cpu, shell=True).decode()
        print(f"Output:\n{cpu_output}")
        
        cpu_id = cpu_output.split('\n')[1].strip()
        print(f"-> Extracted CPU ID:    '{cpu_id}'")
        
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
