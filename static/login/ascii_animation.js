(() => {
    const FALLBACK_ART = `
            ..........            
         ...:=++**++=-..          
       ..:*%@@@@@@@@@@@#-.        
      .-#@@@%*+=--=+#@@@#..       
      .+@@@*.        :%@@+        
      .+@@@+          #@@+        
      ..*@@@#-......-*@@#.        
       ..-*%@@@@@@@@@%*=..        
          ...::--::...            
`;

    function parseAsciiPoints(text) {
        const lines = text
            .replace(/\r/g, "")
            .split("\n")
            .filter((line, idx, arr) => !(idx === arr.length - 1 && line === ""));
        const width = lines.reduce((max, line) => Math.max(max, line.length), 0);
        const centerX = (width - 1) / 2;
        const centerY = (lines.length - 1) / 2;
        const points = [];

        for (let y = 0; y < lines.length; y += 1) {
            const row = lines[y];
            for (let x = 0; x < row.length; x += 1) {
                const ch = row[x];
                if (ch !== " ") {
                    points.push({ x: x - centerX, y: y - centerY, z: 0, ch });
                }
            }
        }
        return {
            points,
            bounds: {
                width: Math.max(1, width),
                height: Math.max(1, lines.length)
            }
        };
    }

    function createBuffers(rows, cols) {
        const chars = [];
        const zBuffer = [];
        for (let y = 0; y < rows; y += 1) {
            chars.push(new Array(cols).fill(" "));
            zBuffer.push(new Array(cols).fill(-Infinity));
        }
        return { chars, zBuffer };
    }

    function estimateProjectionEnvelope(points, cameraDistance) {
        if (!points.length) {
            return { x: 1, y: 1 };
        }

        let maxNormX = 0;
        let maxNormY = 0;
        const steps = 96;

        for (let step = 0; step < steps; step += 1) {
            const angle = (step / steps) * Math.PI * 2;
            const cosY = Math.cos(angle);
            const sinY = Math.sin(angle);

            for (let i = 0; i < points.length; i += 1) {
                const p = points[i];
                const rotatedX = p.x * cosY + p.z * sinY;
                const rotatedY = p.y * 0.92;
                const rotatedZ = -p.x * sinY + p.z * cosY;
                const depth = rotatedZ + cameraDistance;
                if (depth <= 0) {
                    continue;
                }

                const normX = Math.abs(rotatedX / depth);
                const normY = Math.abs(rotatedY / depth);
                if (normX > maxNormX) {
                    maxNormX = normX;
                }
                if (normY > maxNormY) {
                    maxNormY = normY;
                }
            }
        }

        return {
            x: Math.max(maxNormX, 0.01),
            y: Math.max(maxNormY, 0.01)
        };
    }

    function init() {
        const pre = document.querySelector("[data-ascii-art]");
        if (!pre) {
            return;
        }

        const state = {
            points: [],
            bounds: { width: 80, height: 40 },
            cols: 80,
            rows: 32,
            cameraDistance: 52,
            envelope: { x: 0.3, y: 0.3 },
            zoom: 70,
            anchorX: 0.5,
            anchorY: 0.5,
            angleY: 0,
            timer: null
        };

        const measureGrid = () => {
            const rect = pre.getBoundingClientRect();
            if (!rect.width || !rect.height) {
                return;
            }

            const probe = document.createElement("span");
            probe.textContent = "0000000000";
            probe.style.position = "absolute";
            probe.style.visibility = "hidden";
            probe.style.whiteSpace = "pre";
            probe.style.fontFamily = window.getComputedStyle(pre).fontFamily;
            probe.style.fontSize = window.getComputedStyle(pre).fontSize;
            document.body.appendChild(probe);

            const probeRect = probe.getBoundingClientRect();
            document.body.removeChild(probe);

            const charWidth = probeRect.width / 10 || 7;
            const lineHeight = probeRect.height || 12;

            state.cols = Math.max(58, Math.floor(rect.width / charWidth));
            state.rows = Math.max(20, Math.floor(rect.height / lineHeight));

            const margin = 2;
            const availableLeft = Math.max(6, state.cols * state.anchorX - margin);
            const availableRight = Math.max(6, state.cols * (1 - state.anchorX) - margin);
            const halfAvailableX = Math.max(6, Math.min(availableLeft, availableRight));
            const halfAvailableY = Math.max(6, state.rows / 2 - margin);

            const boundZoomX = halfAvailableX / state.envelope.x;
            const boundZoomY = halfAvailableY / state.envelope.y;
            state.zoom = Math.max(18, Math.min(boundZoomX, boundZoomY) * 0.985);
        };

        const render = () => {
            if (!state.points.length) {
                return;
            }

            state.angleY += 0.055;
            const cosY = Math.cos(state.angleY);
            const sinY = Math.sin(state.angleY);
            const { chars, zBuffer } = createBuffers(state.rows, state.cols);

            for (let i = 0; i < state.points.length; i += 1) {
                const point = state.points[i];
                const rotatedX = point.x * cosY + point.z * sinY;
                const rotatedY = point.y * 0.92;
                const rotatedZ = -point.x * sinY + point.z * cosY;
                const depth = rotatedZ + state.cameraDistance;

                if (depth <= 0) {
                    continue;
                }

                const invDepth = 1 / depth;
                const screenX = (state.cols * state.anchorX + rotatedX * state.zoom * invDepth) | 0;
                const screenY = (state.rows * state.anchorY + rotatedY * state.zoom * invDepth) | 0;

                if (
                    screenX >= 0 &&
                    screenX < state.cols &&
                    screenY >= 0 &&
                    screenY < state.rows &&
                    invDepth > zBuffer[screenY][screenX]
                ) {
                    zBuffer[screenY][screenX] = invDepth;
                    chars[screenY][screenX] = point.ch;
                }
            }

            pre.textContent = chars.map((line) => line.join("")).join("\n");
        };

        const startAnimation = () => {
            if (state.timer !== null) {
                return;
            }
            state.timer = window.setInterval(render, 50);
        };

        const stopAnimation = () => {
            if (state.timer === null) {
                return;
            }
            window.clearInterval(state.timer);
            state.timer = null;
        };

        const loadAscii = async () => {
            const artUrl = pre.dataset.artUrl;
            if (!artUrl) {
                return FALLBACK_ART;
            }
            try {
                const response = await fetch(artUrl);
                if (!response.ok) {
                    throw new Error("ASCII file was not found");
                }
                return await response.text();
            } catch (_err) {
                return FALLBACK_ART;
            }
        };

        let resizeTimer;
        window.addEventListener("resize", () => {
            window.clearTimeout(resizeTimer);
            resizeTimer = window.setTimeout(() => {
                measureGrid();
                render();
            }, 120);
        });

        document.addEventListener("visibilitychange", () => {
            if (document.hidden) {
                stopAnimation();
            } else {
                startAnimation();
            }
        });

        loadAscii().then((artText) => {
            const parsed = parseAsciiPoints(artText);
            state.points = parsed.points;
            state.bounds = parsed.bounds;
            state.envelope = estimateProjectionEnvelope(state.points, state.cameraDistance);
            measureGrid();
            render();
            startAnimation();
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
