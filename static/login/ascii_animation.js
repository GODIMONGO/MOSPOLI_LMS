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

    const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

    function getCharWeight(ch) {
        if (ch === "@" || ch === "#" || ch === "%") {
            return 1;
        }
        if (ch === "*" || ch === "+" || ch === "=") {
            return 0.72;
        }
        if (ch === ":" || ch === "-" || ch === ".") {
            return 0.42;
        }
        return 0.58;
    }

    function rotatePoint(point, angleY, angleX) {
        const cosY = Math.cos(angleY);
        const sinY = Math.sin(angleY);
        const x1 = point.x * cosY + point.z * sinY;
        const z1 = -point.x * sinY + point.z * cosY;

        const cosX = Math.cos(angleX);
        const sinX = Math.sin(angleX);
        const y2 = point.y * cosX - z1 * sinX;
        const z2 = point.y * sinX + z1 * cosX;

        return { x: x1, y: y2, z: z2 };
    }

    function parseAsciiPoints(text) {
        const lines = text
            .replace(/\r/g, "")
            .split("\n")
            .filter((line, idx, arr) => !(idx === arr.length - 1 && line === ""));

        const width = lines.reduce((max, line) => Math.max(max, line.length), 0);
        const padded = lines.map((line) => line.padEnd(width, " "));
        const centerX = (width - 1) / 2;
        const centerY = (padded.length - 1) / 2;
        const radiusX = Math.max(1, width / 2);
        const radiusY = Math.max(1, padded.length / 2);
        const points = [];

        for (let y = 0; y < padded.length; y += 1) {
            const row = padded[y];

            for (let x = 0; x < row.length; x += 1) {
                const ch = row[x];
                if (ch === " ") {
                    continue;
                }

                let occupiedNeighbors = 0;
                let neighborCount = 0;
                for (let dy = -1; dy <= 1; dy += 1) {
                    for (let dx = -1; dx <= 1; dx += 1) {
                        if (dx === 0 && dy === 0) {
                            continue;
                        }

                        const nextY = y + dy;
                        const nextX = x + dx;
                        if (nextY < 0 || nextY >= padded.length || nextX < 0 || nextX >= width) {
                            continue;
                        }

                        neighborCount += 1;
                        if (padded[nextY][nextX] !== " ") {
                            occupiedNeighbors += 1;
                        }
                    }
                }

                const normalizedX = (x - centerX) / radiusX;
                const normalizedY = (y - centerY) / radiusY;
                const radialCore = Math.max(0, 1 - Math.hypot(normalizedX * 0.9, normalizedY * 1.1));
                const charWeight = getCharWeight(ch);
                const localDensity = neighborCount ? occupiedNeighbors / neighborCount : charWeight;
                const z =
                    localDensity * 2.5 +
                    charWeight * 1.8 +
                    radialCore * 1.15;

                points.push({
                    x: x - centerX,
                    y: (y - centerY) * 0.94,
                    z,
                    ch,
                    weight: charWeight,
                    phase: ((x * 17 + y * 31) % 360) * (Math.PI / 180),
                    snapX: null,
                    snapY: null
                });
            }
        }

        return {
            points,
            bounds: {
                width: Math.max(1, width),
                height: Math.max(1, padded.length)
            }
        };
    }

    function estimateProjectionEnvelope(points, cameraDistance) {
        if (!points.length) {
            return { x: 1, y: 1 };
        }

        let maxNormX = 0;
        let maxNormY = 0;
        const steps = 84;
        const angleXVariants = [-0.22, -0.08, 0.08, 0.18];

        for (let step = 0; step < steps; step += 1) {
            const angleY = (step / steps) * Math.PI * 2;

            for (let i = 0; i < angleXVariants.length; i += 1) {
                const angleX = angleXVariants[i];

                for (let j = 0; j < points.length; j += 1) {
                    const projected = rotatePoint(points[j], angleY, angleX);
                    const depth = projected.z + cameraDistance;
                    if (depth <= 0) {
                        continue;
                    }

                    const normX = Math.abs(projected.x / depth);
                    const normY = Math.abs(projected.y / depth);
                    if (normX > maxNormX) {
                        maxNormX = normX;
                    }
                    if (normY > maxNormY) {
                        maxNormY = normY;
                    }
                }
            }
        }

        return {
            x: Math.max(maxNormX, 0.01),
            y: Math.max(maxNormY, 0.01)
        };
    }

    function resolveMetrics(canvas) {
        const styles = window.getComputedStyle(canvas);
        const probe = document.createElement("span");
        probe.textContent = "0000000000";
        probe.style.position = "absolute";
        probe.style.visibility = "hidden";
        probe.style.pointerEvents = "none";
        probe.style.whiteSpace = "pre";
        probe.style.fontFamily = styles.fontFamily;
        probe.style.fontSize = styles.fontSize;
        probe.style.fontWeight = styles.fontWeight;
        probe.style.letterSpacing = styles.letterSpacing;
        document.body.appendChild(probe);

        const probeRect = probe.getBoundingClientRect();
        document.body.removeChild(probe);

        const fontBits = [styles.fontStyle, styles.fontWeight, styles.fontSize, styles.fontFamily]
            .filter(Boolean)
            .join(" ");
        const parsedLineHeight = parseFloat(styles.lineHeight);
        const lineHeight = Number.isFinite(parsedLineHeight) ? parsedLineHeight : probeRect.height || 12;
        const charWidth = probeRect.width / 10 || 7;
        const colorMatch = styles.color.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);

        return {
            charWidth,
            lineHeight,
            font: fontBits,
            color: colorMatch ? `${colorMatch[1]}, ${colorMatch[2]}, ${colorMatch[3]}` : "17, 24, 39"
        };
    }

    function init() {
        const asciiRoot = document.querySelector(".ascii-background");
        if (!(asciiRoot instanceof HTMLElement)) {
            return;
        }

        const canvas = asciiRoot.querySelector("[data-ascii-canvas]");
        const prePrimary = asciiRoot.querySelector('[data-ascii-fallback="primary"]');
        const preSecondary = asciiRoot.querySelector('[data-ascii-fallback="secondary"]');
        const ctx = canvas instanceof HTMLCanvasElement ? canvas.getContext("2d", { alpha: true }) : null;
        const hideAsciiOnMobile = window.matchMedia("(max-width: 560px)");
        const loginForm = document.querySelector(".login-form");
        const inputs = Array.from(document.querySelectorAll(".login-input"));
        const hasError = Boolean(document.querySelector(".alert"));

        const state = {
            points: [],
            bounds: { width: 80, height: 40 },
            cols: 80,
            rows: 32,
            cameraDistance: 34,
            envelope: { x: 0.3, y: 0.3 },
            zoom: 72,
            anchorX: 0.5,
            anchorY: 0.52,
            angleY: 0.22,
            angleX: -0.025,
            angleXTarget: -0.025,
            spin: 0.48,
            spinTarget: 0.48,
            focusEnergy: hasError ? 0.24 : 0,
            focusTarget: hasError ? 0.24 : 0,
            errorPhase: 0,
            metrics: resolveMetrics(canvas || asciiRoot),
            buffers: {
                chars: [],
                depths: new Float32Array(0)
            },
            frameId: 0,
            lastTime: 0,
            isRunning: false,
            needsMeasure: true,
            fallbackMode: true,
            zeroDrawFrames: 0,
            frameCache: [],
            frameCount: 240,
            renderedPrimaryIndex: -1,
            renderedSecondaryIndex: -1
        };

        asciiRoot.classList.add("is-fallback");

        function ensureBuffers() {
            const size = state.cols * state.rows;
            if (state.buffers.chars.length !== size) {
                state.buffers.chars = new Array(size).fill("");
                state.buffers.depths = new Float32Array(size);
            } else {
                state.buffers.chars.fill("");
            }
            state.buffers.depths.fill(-Infinity);
        }

        function switchToFallback() {
            if (state.fallbackMode || !(prePrimary instanceof HTMLElement) || !(preSecondary instanceof HTMLElement)) {
                return;
            }

            state.fallbackMode = true;
            asciiRoot.classList.add("is-fallback");
        }

        function measureViewport() {
            const rect = asciiRoot.getBoundingClientRect();
            if (!rect.width || !rect.height) {
                return false;
            }

            state.metrics = resolveMetrics(prePrimary || canvas || asciiRoot);
            state.cols = Math.max(64, Math.floor(rect.width / state.metrics.charWidth));
            state.rows = Math.max(24, Math.floor(rect.height / state.metrics.lineHeight));

            const margin = 3;
            const halfAvailableX = Math.max(8, state.cols / 2 - margin);
            const halfAvailableY = Math.max(7, state.rows / 2 - margin);
            const boundZoomX = halfAvailableX / state.envelope.x;
            const boundZoomY = halfAvailableY / state.envelope.y;
            state.zoom = Math.max(54, Math.min(boundZoomX, boundZoomY) * 2.18);

            if (canvas instanceof HTMLCanvasElement && ctx) {
                const dpr = Math.min(window.devicePixelRatio || 1, 2);
                canvas.width = Math.max(1, Math.round(rect.width * dpr));
                canvas.height = Math.max(1, Math.round(rect.height * dpr));
                ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
                ctx.textAlign = "left";
                ctx.textBaseline = "top";
                ctx.font = state.metrics.font;
            }

            state.needsMeasure = false;
            buildFrameCache();
            return true;
        }

        function applyFieldState(activeInput) {
            if (!activeInput) {
                state.focusTarget = hasError ? 0.24 : 0;
                state.spinTarget = 0.48;
                return;
            }

            const index = Math.max(0, inputs.indexOf(activeInput));
            state.focusTarget = 1;
            state.spinTarget = 0.6 + index * 0.06;
        }

        function renderProjectedBuffer(angleY) {
            ensureBuffers();

            const spinSin = Math.sin(angleY);
            const spinCos = Math.cos(angleY);
            const flatScale = state.zoom / state.cameraDistance;
            const squash = 0.18 + Math.abs(spinCos) * 0.82;
            const sway = spinSin * 0.14;
            const tilt = Math.sin(-0.025) * 0.12;
            const rollHint = spinSin * 0.04;
            const yScale = 0.965 + Math.abs(spinCos) * 0.035;

            for (let i = 0; i < state.points.length; i += 1) {
                const point = state.points[i];
                const transformedX = point.x * spinCos * squash + point.z * sway;
                const transformedY = point.y * yScale + point.x * (tilt + rollHint) * spinSin - point.z * 0.018;
                const transformedZ = point.z * (0.26 + 0.18 * spinCos) + point.x * spinSin * 0.5;

                const screenX = Math.round(state.cols * state.anchorX + transformedX * flatScale);
                const screenY = Math.round(state.rows * state.anchorY + transformedY * flatScale);

                if (screenX < 0 || screenX >= state.cols || screenY < 0 || screenY >= state.rows) {
                    continue;
                }

                const bufferIndex = screenY * state.cols + screenX;
                if (transformedZ <= state.buffers.depths[bufferIndex]) {
                    continue;
                }

                state.buffers.depths[bufferIndex] = transformedZ;
                state.buffers.chars[bufferIndex] = point.ch;
            }
        }

        function bufferToText() {
            const lines = [];
            for (let row = 0; row < state.rows; row += 1) {
                const start = row * state.cols;
                lines.push(state.buffers.chars.slice(start, start + state.cols).map((ch) => ch || " ").join(""));
            }
            return lines.join("\n");
        }

        function buildFrameCache() {
            if (!state.points.length || !state.cols || !state.rows) {
                state.frameCache = [];
                state.renderedPrimaryIndex = -1;
                state.renderedSecondaryIndex = -1;
                return;
            }

            const frames = new Array(state.frameCount);
            for (let frameIndex = 0; frameIndex < state.frameCount; frameIndex += 1) {
                const angleY = (frameIndex / state.frameCount) * Math.PI * 2;
                renderProjectedBuffer(angleY);
                frames[frameIndex] = bufferToText();
            }

            state.frameCache = frames;
            state.renderedPrimaryIndex = -1;
            state.renderedSecondaryIndex = -1;
        }

        function updateMotion(now) {
            if (!state.points.length) {
                return -1;
            }

            if (state.needsMeasure && !measureViewport()) {
                return -1;
            }

            if (!state.frameCache.length) {
                return -1;
            }

            const delta = state.lastTime ? Math.min(0.05, (now - state.lastTime) / 1000) : 1 / 60;
            state.lastTime = now;

            const easing = 1 - Math.exp(-delta * 8);
            state.spin += (state.spinTarget - state.spin) * easing;
            state.focusEnergy += (state.focusTarget - state.focusEnergy) * easing;
            state.angleY += state.spin * delta;
            state.errorPhase += delta * (hasError ? 4.2 : 1.8);

            const normalizedAngle = ((state.angleY % (Math.PI * 2)) + Math.PI * 2) % (Math.PI * 2);
            return (normalizedAngle / (Math.PI * 2)) * state.frameCount;
        }

        function renderCanvas(rect) {
            if (!(canvas instanceof HTMLCanvasElement) || !ctx) {
                switchToFallback();
                return;
            }

            ctx.clearRect(0, 0, rect.width, rect.height);
            ctx.font = state.metrics.font;
            ctx.fillStyle = `rgb(${state.metrics.color})`;

            for (let row = 0; row < state.rows; row += 1) {
                const y = row * state.metrics.lineHeight;

                for (let col = 0; col < state.cols; col += 1) {
                    const index = row * state.cols + col;
                    const ch = state.buffers.chars[index];
                    if (!ch) {
                        continue;
                    }

                    ctx.globalAlpha = 1;
                    ctx.fillText(ch, col * state.metrics.charWidth, y);
                }
            }

            ctx.globalAlpha = 1;
        }

        function renderFallback(framePosition) {
            if (!(prePrimary instanceof HTMLElement) || !(preSecondary instanceof HTMLElement)) {
                return;
            }

            if (framePosition < 0 || !state.frameCache.length) {
                return;
            }

            const frameBase = Math.floor(framePosition) % state.frameCache.length;
            const frameNext = (frameBase + 1) % state.frameCache.length;
            const blend = framePosition - Math.floor(framePosition);

            if (state.renderedPrimaryIndex !== frameBase) {
                prePrimary.textContent = state.frameCache[frameBase];
                state.renderedPrimaryIndex = frameBase;
            }

            if (state.renderedSecondaryIndex !== frameNext) {
                preSecondary.textContent = state.frameCache[frameNext];
                state.renderedSecondaryIndex = frameNext;
            }

            prePrimary.style.opacity = `${1 - blend}`;
            preSecondary.style.opacity = `${blend}`;
        }

        function renderFrame(now) {
            if (hideAsciiOnMobile.matches) {
                return;
            }

            const framePosition = updateMotion(now);
            if (framePosition < 0) {
                return;
            }

            if (state.fallbackMode) {
                renderFallback(framePosition);
            } else {
                const rect = asciiRoot.getBoundingClientRect();
                renderCanvas(rect);
            }
        }

        function animationLoop(now) {
            if (!state.isRunning) {
                return;
            }

            renderFrame(now);
            state.frameId = window.requestAnimationFrame(animationLoop);
        }

        function renderStill() {
            if (!hideAsciiOnMobile.matches) {
                state.lastTime = 0;
                renderFrame(window.performance.now());
            }
        }

        function startAnimation() {
            if (state.isRunning || hideAsciiOnMobile.matches) {
                return;
            }

            state.isRunning = true;
            state.lastTime = 0;
            state.frameId = window.requestAnimationFrame(animationLoop);
        }

        function stopAnimation() {
            state.isRunning = false;
            state.lastTime = 0;
            if (state.frameId) {
                window.cancelAnimationFrame(state.frameId);
                state.frameId = 0;
            }
        }

        async function loadAscii() {
            const artUrl = asciiRoot.dataset.artUrl;
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
        }

        let resizeTimer = 0;
        window.addEventListener("resize", () => {
            window.clearTimeout(resizeTimer);
            resizeTimer = window.setTimeout(() => {
                state.needsMeasure = true;
                renderStill();
            }, 120);
        });

        document.addEventListener("visibilitychange", () => {
            if (document.hidden) {
                stopAnimation();
                return;
            }

            startAnimation();
        });

        const handleMobileVisibility = () => {
            if (hideAsciiOnMobile.matches) {
                stopAnimation();
                return;
            }

            renderStill();
            if (!document.hidden) {
                startAnimation();
            }
        };

        if (typeof hideAsciiOnMobile.addEventListener === "function") {
            hideAsciiOnMobile.addEventListener("change", handleMobileVisibility);
        } else if (typeof hideAsciiOnMobile.addListener === "function") {
            hideAsciiOnMobile.addListener(handleMobileVisibility);
        }

        if (loginForm) {
            loginForm.addEventListener("focusin", (event) => {
                const activeInput = event.target instanceof Element ? event.target.closest(".login-input") : null;
                applyFieldState(activeInput);
                renderStill();
            });

            loginForm.addEventListener("focusout", () => {
                window.requestAnimationFrame(() => {
                    const activeElement = document.activeElement instanceof Element
                        ? document.activeElement.closest(".login-input")
                        : null;
                    applyFieldState(activeElement);
                    renderStill();
                });
            });

            loginForm.addEventListener("submit", () => {
                state.focusTarget = 1.15;
                state.spinTarget = 0.92;
                renderStill();
            });
        }

        loadAscii().then((artText) => {
            const parsed = parseAsciiPoints(artText);
            state.points = parsed.points;
            state.bounds = parsed.bounds;
            state.envelope = estimateProjectionEnvelope(state.points, state.cameraDistance);
            state.needsMeasure = true;

            renderStill();
            startAnimation();
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
