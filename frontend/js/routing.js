/**
 * Quản lý Tìm đường & Kiểm tra ngập trên OpenFreeMap (Hoàn toàn không cần API Key)
 * Tích hợp OSRM Routing và bộ tìm kiếm địa điểm TPHCM tức thời
 */
class RouteManager {
    constructor() {
        this.originPoint = null; // { lat, lng, name }
        this.destPoint = null;   // { lat, lng, name }
        this.currentRoutes = [];
        this.activeRouteIndex = 0;
        this.pickingMode = null; // 'origin' hoặc 'dest'
        this.tempMarkers = [];
    }

    init() {
        this.setupAutocomplete("originInput", "originDropdown", (item) => {
            this.originPoint = item;
            document.getElementById("originInput").value = item.name;
            this.addTempMarker(item.lat, item.lng, "origin", item.name);
        });

        this.setupAutocomplete("destinationInput", "destDropdown", (item) => {
            this.destPoint = item;
            document.getElementById("destinationInput").value = item.name;
            this.addTempMarker(item.lat, item.lng, "dest", item.name);
        });
    }

    /**
     * Thiết lập Autocomplete tìm kiếm địa điểm TPHCM tức thời không cần API Key bên ngoài
     */
    setupAutocomplete(inputId, dropdownId, onSelect) {
        const input = document.getElementById(inputId);
        const dropdown = document.getElementById(dropdownId);
        if (!input || !dropdown) return;

        input.addEventListener("input", () => {
            const val = input.value.trim().toLowerCase();
            if (val.length < 1) {
                dropdown.style.display = "none";
                return;
            }

            const matches = window.APP_CONFIG.HCM_PLACES.filter((p) =>
                p.name.toLowerCase().includes(val)
            ).slice(0, 6);

            if (matches.length === 0) {
                dropdown.style.display = "none";
                return;
            }

            dropdown.innerHTML = matches.map((m) => `
                <div class="autocomplete-item" data-name="${m.name}" data-lat="${m.lat}" data-lng="${m.lng}">
                    <span>📍</span>
                    <div>
                        <div style="font-weight:600; font-size:13px; color:#1e293b;">${m.name}</div>
                        <div style="font-size:11px; color:#64748b;">${m.lat.toFixed(4)}, ${m.lng.toFixed(4)}</div>
                    </div>
                </div>
            `).join("");

            dropdown.style.display = "block";

            dropdown.querySelectorAll(".autocomplete-item").forEach((el) => {
                el.addEventListener("click", () => {
                    const lat = parseFloat(el.getAttribute("data-lat"));
                    const lng = parseFloat(el.getAttribute("data-lng"));
                    const name = el.getAttribute("data-name");
                    dropdown.style.display = "none";
                    onSelect({ lat, lng, name });
                });
            });
        });

        // Ẩn dropdown khi click ra ngoài
        document.addEventListener("click", (e) => {
            if (!input.contains(e.target) && !dropdown.contains(e.target)) {
                dropdown.style.display = "none";
            }
        });
    }

    useCurrentLocationAsOrigin() {
        if (window.MapManager.userLocation) {
            const loc = window.MapManager.userLocation;
            this.originPoint = { lat: loc.lat, lng: loc.lng, name: "Vị trí hiện tại của tôi" };
            document.getElementById("originInput").value = "Vị trí hiện tại của tôi";
            this.addTempMarker(loc.lat, loc.lng, "origin", "Vị trí của bạn");
            window.App.showToast("Đã chọn vị trí hiện tại làm điểm đi (A)!", "success");
        } else {
            window.MapManager.locateUser(true);
            setTimeout(() => {
                if (window.MapManager.userLocation) {
                    this.useCurrentLocationAsOrigin();
                }
            }, 1200);
        }
    }

    startPickOnMap(mode) {
        this.pickingMode = mode;
        const msg = mode === "origin"
            ? "👉 Hãy CLICK vào một vị trí trên bản đồ để chọn Điểm đi (A)"
            : "👉 Hãy CLICK vào một vị trí trên bản đồ để chọn Điểm đến (B)";
        window.App.showToast(msg, "warning");

        const map = window.MapManager.map;
        if (map) {
            map.getCanvas().style.cursor = "crosshair";
            const clickHandler = (e) => {
                const { lng, lat } = e.lngLat;
                const name = `Tọa độ [${lat.toFixed(4)}, ${lng.toFixed(4)}]`;

                if (this.pickingMode === "origin") {
                    this.originPoint = { lat, lng, name };
                    document.getElementById("originInput").value = name;
                    this.addTempMarker(lat, lng, "origin", name);
                } else if (this.pickingMode === "dest") {
                    this.destPoint = { lat, lng, name };
                    document.getElementById("destinationInput").value = name;
                    this.addTempMarker(lat, lng, "dest", name);
                }

                map.getCanvas().style.cursor = "";
                map.off("click", clickHandler);
                this.pickingMode = null;
                window.App.showToast("Đã chọn điểm thành công!", "success");
            };
            map.once("click", clickHandler);
        }
    }

    addTempMarker(lat, lng, type, title) {
        const map = window.MapManager.map;
        if (!map) return;

        // Xóa marker cũ cùng loại
        this.tempMarkers = this.tempMarkers.filter((m) => {
            if (m.type === type) {
                m.marker.remove();
                return false;
            }
            return true;
        });

        const el = document.createElement("div");
        el.className = "route-pin-marker";
        el.style.backgroundColor = type === "origin" ? "#10b981" : "#ef4444";
        el.innerHTML = type === "origin" ? "A" : "B";

        const marker = new maplibregl.Marker({
            element: el,
            anchor: "center",
        })
            .setLngLat([lng, lat])
            .setPopup(new maplibregl.Popup({ offset: 15 }).setHTML(`<b>${title}</b>`))
            .addTo(map);

        this.tempMarkers.push({ type, marker });
    }

    /**
     * Tìm đường miễn phí qua Open Source Routing Machine (OSRM)
     */
    async calculateRoute(forceAlternative = false) {
        if (!this.originPoint || !this.destPoint) {
            window.App.showToast("Vui lòng chọn đầy đủ Điểm đi (A) và Điểm đến (B).", "warning");
            return;
        }

        const o = this.originPoint;
        const d = this.destPoint;

        window.App.showLoading("Đang tính toán tuyến đường và quét điểm ngập...");

        try {
            // Gọi OSRM public API hoàn toàn miễn phí, không cần token/key
            const osrmUrl = `https://router.project-osrm.org/route/v1/driving/${o.lng},${o.lat};${d.lng},${d.lat}?overview=full&geometries=geojson&alternatives=true`;
            const res = await fetch(osrmUrl);

            if (!res.ok) throw new Error(`OSRM HTTP ${res.status}`);

            const data = await res.json();
            if (!data.routes || data.routes.length === 0) {
                window.App.showToast("Không tìm thấy đường đi giữa 2 điểm này.", "error");
                return;
            }

            this.currentRoutes = data.routes;
            let routeIndex = 0;

            // Nếu người dùng yêu cầu né ngập và có route phụ, chọn route thứ 2
            if (forceAlternative && data.routes.length > 1) {
                routeIndex = 1;
            }

            this.activeRouteIndex = routeIndex;
            const chosenRoute = data.routes[routeIndex];
            const coordinates = chosenRoute.geometry.coordinates; // [[lng, lat], ...]

            // Vẽ tuyến đường lên bản đồ OpenFreeMap
            this.drawRouteOnMap(coordinates, routeIndex === 1);

            // Gửi danh sách tọa độ về FastAPI backend để kiểm tra ngập (FR4.2 / Task 39, 40, 41)
            const pointsPayload = coordinates.map((c) => ({ lat: c[1], lng: c[0] }));
            await this.checkRouteFlood(pointsPayload, data.routes.length > 1);

        } catch (err) {
            console.warn("OSRM error, dùng đường bay trực tiếp dự phòng:", err);
            // Fallback vẽ đường nối trực tiếp
            const coords = [[o.lng, o.lat], [d.lng, d.lat]];
            this.drawRouteOnMap(coords, false);
            const pointsPayload = [{ lat: o.lat, lng: o.lng }, { lat: d.lat, lng: d.lng }];
            await this.checkRouteFlood(pointsPayload, false);
        } finally {
            window.App.hideLoading();
        }
    }

    drawRouteOnMap(coordinates, isAlternative = false) {
        const map = window.MapManager.map;
        if (!map) return;

        const routeColor = isAlternative ? "#10b981" : "#2563eb";

        const routeGeoJSON = {
            type: "Feature",
            properties: {},
            geometry: {
                type: "LineString",
                coordinates: coordinates,
            },
        };

        if (map.getSource("user-route-source")) {
            map.getSource("user-route-source").setData(routeGeoJSON);
            map.setPaintProperty("user-route-line", "line-color", routeColor);
        } else {
            map.addSource("user-route-source", {
                type: "geojson",
                data: routeGeoJSON,
            });

            // Viền ngoài phát sáng
            map.addLayer({
                id: "user-route-casing",
                type: "line",
                source: "user-route-source",
                layout: { "line-join": "round", "line-cap": "round" },
                paint: {
                    "line-color": "#ffffff",
                    "line-width": 9,
                    "line-opacity": 0.6,
                },
            });

            // Đường dẫn chính
            map.addLayer({
                id: "user-route-line",
                type: "line",
                source: "user-route-source",
                layout: { "line-join": "round", "line-cap": "round" },
                paint: {
                    "line-color": routeColor,
                    "line-width": 6,
                    "line-opacity": 0.9,
                },
            });
        }

        // Tự động zoom vừa vặn tuyến đường
        const bounds = new maplibregl.LngLatBounds();
        coordinates.forEach((c) => bounds.extend(c));
        map.fitBounds(bounds, { padding: 60, maxZoom: 16 });
    }

    async checkRouteFlood(points, hasAlternatives) {
        try {
            window.App.showLoading("Đang phân tích dữ liệu không gian né ngập...");

            const response = await fetch(`${window.APP_CONFIG.API_BASE_URL}/api/v1/routes/check-flood`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    points: points,
                    buffer_meters: 60,
                }),
            });

            const data = await response.json();
            this.renderWarningUI(data, hasAlternatives);
        } catch (error) {
            console.error("Lỗi khi kiểm tra ngập trên tuyến đường:", error);
            window.App.showToast("Không thể kết nối đến máy chủ kiểm tra ngập.", "warning");
        } finally {
            window.App.hideLoading();
        }
    }

    renderWarningUI(checkResult, hasAlternatives) {
        const warningBanner = document.getElementById("routeWarningBanner");
        const safeBanner = document.getElementById("routeSafeBanner");
        const warningDesc = document.getElementById("routeWarningDesc");
        const warningAction = document.getElementById("routeWarningAction");
        const interceptedList = document.getElementById("interceptedFloodsList");
        const avoidBtn = document.getElementById("avoidRouteBtn");

        if (!warningBanner || !safeBanner) return;

        if (checkResult.is_safe) {
            warningBanner.classList.remove("active");
            safeBanner.classList.add("active");
            safeBanner.innerHTML = `
                <div style="font-weight: 700; margin-bottom: 4px;"> Tuyến đường AN TOÀN!</div>
                <div>${checkResult.warning_message}</div>
            `;
            window.App.showToast("Lộ trình an toàn, không có điểm ngập nguy hiểm!", "success");
        } else {
            safeBanner.classList.remove("active");
            warningBanner.classList.add("active");

            warningDesc.textContent = checkResult.warning_message;
            warningAction.textContent = checkResult.suggested_action;

            if (interceptedList) {
                interceptedList.innerHTML = checkResult.intercepted_floods.map((item) => `
                    <div style="font-size: 12px; margin-top: 6px; padding: 6px; background: #fff5f5; border-radius: 4px; border-left: 3px solid #ef4444;">
                        <b>• ${item.title}</b> (${item.severity_level.toUpperCase()})
                        - Cách lộ trình: <b>${item.distance_to_route_meters}m</b>
                    </div>
                `).join("");
            }

            if (avoidBtn) {
                if (hasAlternatives && this.activeRouteIndex === 0) {
                    avoidBtn.style.display = "block";
                    avoidBtn.textContent = "🔄 Chuyển sang lộ trình né ngập";
                } else {
                    avoidBtn.style.display = "none";
                }
            }

            window.App.showToast(" CẢNH BÁO: Tuyến đường cắt qua điểm ngập!", "error");
        }
    }

    clearRoute() {
        const map = window.MapManager.map;
        if (map) {
            if (map.getLayer("user-route-line")) map.removeLayer("user-route-line");
            if (map.getLayer("user-route-casing")) map.removeLayer("user-route-casing");
            if (map.getSource("user-route-source")) map.removeSource("user-route-source");
        }

        this.tempMarkers.forEach((m) => m.marker.remove());
        this.tempMarkers = [];
        this.originPoint = null;
        this.destPoint = null;

        document.getElementById("originInput").value = "";
        document.getElementById("destinationInput").value = "";
        document.getElementById("routeWarningBanner").classList.remove("active");
        document.getElementById("routeSafeBanner").classList.remove("active");
    }
}

window.RouteManager = new RouteManager();
