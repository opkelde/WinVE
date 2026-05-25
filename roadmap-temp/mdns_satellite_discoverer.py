"""
Zero-dependency Local Network Satellite Discovery Tool (mDNS and UDP Broadcast)
Designed for WinVE network coordination and multi-room satellite discovery.
"""
import socket
import struct
import select
import time
import json
import threading

class SatelliteDiscoverer:
    """Discovers and announces WinVE satellites on the local network using UDP multicast and broadcast."""
    
    MULTICAST_GRP = '224.0.0.251' # Standard mDNS group
    MULTICAST_PORT = 5353          # Standard mDNS port
    WINVE_DISCO_PORT = 19446       # WinVE custom discovery port
    
    def __init__(self, satellite_id="satellite_pc", display_name="Main Desktop", port=10446):
        self.satellite_id = satellite_id
        self.display_name = display_name
        self.port = port
        self.running = False
        self.discovered_satellites = {}
        self.lock = threading.Lock()
        
    def _create_multicast_socket(self):
        """Creates a socket joined to the local mDNS multicast group."""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(('', self.MULTICAST_PORT))
        except Exception:
            # Bind to specific port failed or address in use (another mDNS client)
            # Fall back to a random port but listen to custom WinVE broadcast
            s.bind(('', 0))
            
        mreq = struct.pack("4sl", socket.inet_aton(self.MULTICAST_GRP), socket.INADDR_ANY)
        s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        s.setblocking(False)
        return s

    def _create_broadcast_socket(self):
        """Creates a socket for custom WinVE UDP broadcast discovery."""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.bind(('', self.WINVE_DISCO_PORT))
        s.setblocking(False)
        return s

    def start_discovery(self):
        """Starts discovery and advertisement threads."""
        self.running = True
        self.listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.announce_thread = threading.Thread(target=self._announce_loop, daemon=True)
        self.listen_thread.start()
        self.announce_thread.start()
        print(f"📡 WinVE Discovery started. ID: {self.satellite_id}, Name: '{self.display_name}'")

    def stop_discovery(self):
        """Stops discovery processes."""
        self.running = False
        print("📡 Discovery stopped.")

    def _announce_loop(self):
        """Periodically broadcast presence to the local network."""
        send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        send_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        payload = {
            "type": "winve_announcement",
            "id": self.satellite_id,
            "name": self.display_name,
            "port": self.port,
            "timestamp": time.time()
        }
        message = json.dumps(payload).encode('utf-8')
        
        while self.running:
            try:
                # Custom WinVE Broadcast
                send_sock.sendto(message, ('<broadcast>', self.WINVE_DISCO_PORT))
                
                # Mock standard mDNS query response
                dns_query_resp = b'\x00\x00\x84\x00\x00\x00\x00\x01\x00\x00\x00\x00' # basic header
                send_sock.sendto(dns_query_resp, (self.MULTICAST_GRP, self.MULTICAST_PORT))
                
            except Exception as e:
                print(f"[Discovery Broadcast Error] {e}")
            time.sleep(10) # Announce every 10 seconds

    def _listen_loop(self):
        """Listens for announcements from other satellites."""
        bcast_sock = self._create_broadcast_socket()
        
        while self.running:
            try:
                r, _, _ = select.select([bcast_sock], [], [], 1.0)
                if not r:
                    continue
                    
                for sock in r:
                    data, addr = sock.recvfrom(1024)
                    try:
                        info = json.loads(data.decode('utf-8'))
                        if info.get("type") == "winve_announcement" and info.get("id") != self.satellite_id:
                            sat_id = info["id"]
                            with self.lock:
                                self.discovered_satellites[sat_id] = {
                                    "ip": addr[0],
                                    "name": info["name"],
                                    "port": info["port"],
                                    "last_seen": time.time()
                                }
                                print(f"✨ Found Satellite: {info['name']} ({addr[0]}:{info['port']})")
                    except Exception:
                        pass # Ignore non-JSON packets
            except Exception as e:
                if self.running:
                    print(f"[Discovery Listen Error] {e}")
                time.sleep(1)

        bcast_sock.close()

    def get_satellites(self):
        """Returns list of active satellites discovered, filtering out dead ones (>30s silence)."""
        now = time.time()
        with self.lock:
            # Clean expired
            self.discovered_satellites = {
                k: v for k, v in self.discovered_satellites.items()
                if now - v["last_seen"] < 30
            }
            return list(self.discovered_satellites.values())

if __name__ == "__main__":
    # Test execution
    disc1 = SatelliteDiscoverer("sat_desktop", "Living Room PC", 10446)
    disc1.start_discovery()
    
    try:
        for _ in range(5):
            time.sleep(2)
            sats = disc1.get_satellites()
            print(f"Active satellites online: {sats}")
    finally:
        disc1.stop_discovery()
