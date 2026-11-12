/**
 * Quản lý Hiển thị Điểm ngập trên MapLibre GL JS & OpenFreeMap
 */
class FloodManager {
    constructor() {
        this.floods = [];
        this.markers = [];
        this.activePopup = null;
    }

    async fetchAndRenderFloods() {
        try {
            window.App.showLoading("Đang tải dữ liệu điểm ngập...");
            const response = await fetch(`${window.APP_CONFIG.API_BASE_URL}/api/v1/floods`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            this.floods = await response.json();
            console.log(`Đã tải ${this.floods.length} điểm ngập từ server.`);

            this.clearMapElements();
            this.renderOnMap();
            this.renderSidebarList();
            this.updateBadgeCount();
        } catch (error) {
            console.error("Lỗi khi tải điểm ngập:", error);
            window.App.showToast("Không thể tải danh sách điểm ngập từ máy chủ.", "error");
        } finally {
            window.App.hideLoading();
        }
    }

    clearMapElements() {
        this.markers.forEach((m) => m.remove());
        this.markers = [];
        if (this.activePopup) {
            this.activePopup.remove();
            this.activePopup = null;
        }

        // Xóa layer và source polygon vùng ngập nếu có
        const map = window.MapManager.map;
        if (map) {
            if (map.getLayer("flood-circles-fill")) map.removeLayer("flood-circles-fill");
            if (map.getLayer("flood-circles-line")) map.removeLayer("flood-circles-line");
            if (map.getSource("flood-circles-source")) map.removeSource("flood-circles-source");
        }
    }

    /**
     * Tạo đa giác vòng tròn GeoJSON xấp xỉ từ tâm [lng, lat] và bán kính mét
     */
    createCirclePolygon(centerLng, centerLat, radiusMeters, points = 32) {
        const coords = [];
        const km = radiusMeters / 1000;
        const distanceX = km / (111.32 * Math.cos((centerLat * Math.PI) / 180));
        const distanceY = km / 110.574;

        for (let i = 0; i < points; i++) {
            const theta = (i / points) * (2 * Math.PI);
            const x = distanceX * Math.cos(theta);
            const y = distanceY * Math.sin(theta);
            coords.push([centerLng + x, centerLat + y]);
        }
        coords.push(coords[0]); // Đóng vòng
        return coords;
    }

    renderOnMap() {
        const map = window.MapManager.map;
        if (!map || !map.isStyleLoaded()) return;

        const circleFeatures = [];

        this.floods.forEach((flood, index) => {
            const sev = window.APP_CONFIG.SEVERITY_CONFIG[flood.severity_level] || window.APP_CONFIG.SEVERITY_CONFIG.low;
            const lng = flood.longitude;
            const lat = flood.latitude;

            // 1. Tạo phần tử DOM Marker
            const el = document.createElement("div");
            el.className = `flood-marker ${flood.severity_level}`;
            el.innerHTML = `
                <div class="marker-bubble" style="background-color: ${sev.color}">
                    <span>${sev.icon}</span>
                </div>
                ${flood.severity_level === "high" ? '<div class="high-pulse"></div>' : ''}
            `;

            // 2. Nội dung Popup chi tiết (Task 35)
            const popupHtml = `
                <div class="flood-popup">
                    <div class="popup-title">${flood.title}</div>
                    <div class="popup-tags">
                        <span class="badge ${sev.badgeClass}">${sev.icon} ${sev.label}</span>
                        ${flood.is_verified ? '<span class="badge badge-low"> Đã duyệt</span>' : '<span class="badge badge-medium"> Dân báo</span>'}
                    </div>
                    <p class="popup-desc">${flood.description || "Không có mô tả chi tiết."}</p>
                    <div class="popup-meta">
                        <div> <b>Độ sâu:</b> ${flood.water_depth_cm ? flood.water_depth_cm + ' cm' : 'Chưa rõ'}</div>
                        <div> <b>Bán kính:</b> ${flood.radius_meters || 50} mét</div>
                        <div>🕒 <b>Báo cáo:</b> ${new Date(flood.reported_at).toLocaleTimeString("vi-VN")} ${new Date(flood.reported_at).toLocaleDateString("vi-VN")}</div>
                    </div>
                </div>
            `;

            const popup = new maplibregl.Popup({ offset: 25, closeButton: true })
                .setHTML(popupHtml);

            const marker = new maplibregl.Marker({
                element: el,
                anchor: "bottom", // Cố định mũi ghim, không bị trôi khi phóng to thu nhỏ
            })
                .setLngLat([lng, lat])
                .setPopup(popup)
                .addTo(map);

            this.markers.push(marker);

            // 3. Tạo vùng đa giác ảnh hưởng bán kính ngập
            circleFeatures.push({
                type: "Feature",
                properties: {
                    severity: flood.severity_level,
                    color: sev.color,
                },
                geometry: {
                    type: "Polygon",
                    coordinates: [this.createCirclePolygon(lng, lat, flood.radius_meters || 50)],
                },
            });
        });

        // Vẽ lớp đa giác vùng ngập lên bản đồ
        if (circleFeatures.length > 0 && !map.getSource("flood-circles-source")) {
            map.addSource("flood-circles-source", {
                type: "geojson",
                data: {
                    type: "FeatureCollection",
                    features: circleFeatures,
                },
            });

            map.addLayer({
                id: "flood-circles-fill",
                type: "fill",
                source: "flood-circles-source",
                paint: {
                    "fill-color": ["get", "color"],
                    "fill-opacity": 0.22,
                },
            });

            map.addLayer({
                id: "flood-circles-line",
                type: "line",
                source: "flood-circles-source",
                paint: {
                    "line-color": ["get", "color"],
                    "line-width": 2,
                    "line-opacity": 0.7,
                },
            });
        }
    }

    renderSidebarList(filterLevel = "all") {
        const container = document.getElementById("floodListContainer");
        if (!container) return;

        const filtered = filterLevel === "all"
            ? this.floods
            : this.floods.filter((f) => f.severity_level === filterLevel);

        if (filtered.length === 0) {
            container.innerHTML = `
                <div style="text-align: center; padding: 40px 16px; color: #94a3b8;">
                    <div style="font-size: 36px; margin-bottom: 8px;">🎉</div>
                    <div style="font-weight: 600; font-size: 14px;">Không có điểm ngập nào</div>
                    <div style="font-size: 12px; margin-top: 4px;">Hiện tại không ghi nhận ngập thuộc bộ lọc này.</div>
                </div>
            `;
            return;
        }

        container.innerHTML = filtered.map((flood, index) => {
            const sev = window.APP_CONFIG.SEVERITY_CONFIG[flood.severity_level] || window.APP_CONFIG.SEVERITY_CONFIG.low;
            const timeStr = new Date(flood.reported_at).toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });

            return `
                <div class="flood-card" onclick="window.FloodManager.focusFlood(${flood.latitude}, ${flood.longitude}, ${index})">
                    <div class="flood-card-header">
                        <span class="flood-card-title">${flood.title}</span>
                        <span class="badge ${sev.badgeClass}">${sev.label.split(" ")[0]}</span>
                    </div>
                    <div class="flood-card-desc">${flood.description || "Tình trạng đang cập nhật..."}</div>
                    <div class="flood-card-footer">
                        <span>🕒 ${timeStr}</span>
                        <span>${flood.is_verified ? ' Đã duyệt' : ' Chờ duyệt'}</span>
                    </div>
                </div>
            `;
        }).join("");
    }

    focusFlood(lat, lng, index) {
        window.MapManager.panTo(lat, lng, 16);
        if (this.markers[index]) {
            this.markers[index].togglePopup();
        }
        if (window.innerWidth < 1024) {
            window.App.toggleSidebar(false);
        }
    }

    updateBadgeCount() {
        const badge = document.getElementById("floodTotalBadge");
        if (badge) badge.textContent = this.floods.length;
    }
}

window.FloodManager = new FloodManager();
