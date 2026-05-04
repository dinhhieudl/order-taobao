"""Network info script — Hiển thị IP nội bộ để nhân viên kết nối LAN."""
import socket
import subprocess
import sys

def get_local_ips():
    """Get all local IP addresses."""
    ips = []
    try:
        # Method 1: Connect to external address (doesn't actually send data)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            if ip not in ips:
                ips.append(ip)
        except:
            pass
        finally:
            s.close()
    except:
        pass

    # Method 2: Get all interfaces
    try:
        if sys.platform == "win32":
            result = subprocess.run(["ipconfig"], capture_output=True, text=True, encoding="utf-8", errors="replace")
            for line in result.stdout.split("\n"):
                if "IPv4" in line:
                    ip = line.split(":")[-1].strip()
                    if ip and ip not in ips and not ip.startswith("127."):
                        ips.append(ip)
        else:
            result = subprocess.run(["hostname", "-I"], capture_output=True, text=True)
            for ip in result.stdout.strip().split():
                if ip not in ips and not ip.startswith("127."):
                    ips.append(ip)
    except:
        pass

    return ips

def main():
    port = 8000
    ips = get_local_ips()

    print("=" * 50)
    print("🌐 THÔNG TIN MẠNG — Truy cập từ LAN")
    print("=" * 50)
    print()
    print(f"  🖥️  Server: http://localhost:{port}")
    print()

    if ips:
        print("  📱 Cho nhân viên trong mạng LAN:")
        for ip in ips:
            print(f"     👉 http://{ip}:{port}")
        print()
        print("  💡 Đảm bảo firewall cho phép cổng {port}")
    else:
        print("  ⚠️  Không tìm thấy IP nội bộ.")
        print("  💡 Thử chạy: ipconfig (Windows) hoặc ifconfig (Mac/Linux)")

    print()
    print("=" * 50)

if __name__ == "__main__":
    main()
