from c2.plugins.internal.plugins import BasePlugin


class DeviceInfoPlugin(BasePlugin):
    name = "deviceinfo"

    async def capture(self) -> dict:
        """Returns a snapshot of the client's device and browser environment.

        Collected fields:
        - userAgent, language, languages, platform
        - cookieEnabled, onLine
        - hardwareConcurrency, deviceMemory
        - screen  (width/height/availWidth/availHeight/colorDepth/pixelRatio)
        - window  (innerWidth/innerHeight)
        - timezone
        - connection (type, effectiveType, downlink, rtt, saveData) — if available
        - battery   (level, charging, chargingTime, dischargingTime) — if available

        :return: Device/browser info dict
        :rtype: dict
        """
        return await self.methods.eval_js('''
            return (async function() {
                var info = {
                    userAgent:           navigator.userAgent,
                    language:            navigator.language,
                    languages:           Array.from(navigator.languages || []),
                    platform:            navigator.platform,
                    cookieEnabled:       navigator.cookieEnabled,
                    onLine:              navigator.onLine,
                    hardwareConcurrency: navigator.hardwareConcurrency || null,
                    deviceMemory:        navigator.deviceMemory        || null,
                    screen: {
                        width:       screen.width,
                        height:      screen.height,
                        availWidth:  screen.availWidth,
                        availHeight: screen.availHeight,
                        colorDepth:  screen.colorDepth,
                        pixelRatio:  window.devicePixelRatio
                    },
                    window: {
                        innerWidth:  window.innerWidth,
                        innerHeight: window.innerHeight
                    },
                    timezone:   Intl.DateTimeFormat().resolvedOptions().timeZone,
                    connection: null,
                    battery:    null
                };

                if (navigator.connection) {
                    var c = navigator.connection;
                    info.connection = {
                        type:          c.type          || null,
                        effectiveType: c.effectiveType || null,
                        downlink:      c.downlink      || null,
                        rtt:           c.rtt           || null,
                        saveData:      c.saveData      || false
                    };
                }

                if (navigator.getBattery) {
                    try {
                        var bat = await navigator.getBattery();
                        info.battery = {
                            level:           bat.level,
                            charging:        bat.charging,
                            chargingTime:    bat.chargingTime,
                            dischargingTime: bat.dischargingTime
                        };
                    } catch(e) {}
                }

                return info;
            })();
        ''')
