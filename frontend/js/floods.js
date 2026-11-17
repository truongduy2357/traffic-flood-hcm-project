/**
 * Quản lý Hiển thị Điểm ngập trên Bản đồ (Hỗ trợ cả OpenFreeMap / MapLibre & Google Maps)
 * Sprint 3: Nhận dữ liệu từ API và vẽ điểm ngập dạng Marker hoặc Vùng đa giác (Polygon/Circle).
 */
class FloodManager {
    constructor() {
        this.floods = [];
        this.markers = [];
        this.googleCircles = [];
        this.activePopup = null;
    }

    async fetchAndRenderFloods() {
        try {
            window.App.showLoading("Đang tải dữ liệu điểm ngập...");
            // Gọi API Backend lấy danh sách các điểm ngập đang hoạt động
            const response = await fetch(`${window.APP_CONFIG.API_BASE_URL}/api/v1/floods`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            this.floods = await response.json();
            console.log(`Đã tải ${this.floods.length} điểm ngập từ máy chủ.`);

            this.clearMapElements();
            this.renderOnMap();
            this.renderSidebarList();
            this.updateBadgeCount();
        } catch (error) {
            console.warn("Lỗi khi tải từ API, sử dụng dữ liệu mẫu dự phòng TP.HCM:", error);
            // Dữ liệu mẫu dự phòng đảm bảo bản đồ luôn có điểm ngập hiển thị khi sinh viên test
            this.floods = this.getSampleFloods();
            this.clearMapElements();
            this.renderOnMap();
            this.renderSidebarList();
            this.updateBadgeCount();
        } finally {
            window.App.hideLoading();
        }
    }

    clearMapElements() {
        // Xóa các marker cũ (hỗ trợ cả MapLibre và Google Maps)
        this.markers.forEach((m) => {
            if (m.remove) m.remove();
            else if (m.setMap) m.setMap(null);
        });
        this.markers = [];

        // Xóa các hình tròn đa giác Google Maps nếu có
        if (this.googleCircles && this.googleCircles.length > 0) {
            this.googleCircles.forEach((c) => c.setMap(null));
            this.googleCircles = [];
        }

        if (this.activePopup) {
            this.activePopup.remove();
            this.activePopup = null;
        }

        // Xóa layer và source polygon vùng ngập nếu dùng MapLibre / OpenFreeMap
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
        // 1. Kiểm tra nếu dự án đang chạy với Google Maps API
        if (window.google && window.google.maps && window.MapManager && window.MapManager.googleMap) {
            this.renderOnGoogleMaps(window.MapManager.googleMap);
            return;
        }

        // 2. Chạy với MapLibre GL JS / OpenFreeMap (Mặc định của dự án)
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

            // 2. Nội dung Popup / InfoWindow chi tiết (Task 35 - SRS 3.2.3)
            // Hiển thị đầy đủ: mức nước, thời gian báo cáo, trạng thái xác minh
            const reportedDate = new Date(flood.reported_at);
            const timeFormatted = isNaN(reportedDate.getTime())
                ? "Vừa xong"
                : `${reportedDate.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" })} - ${reportedDate.toLocaleDateString("vi-VN")}`;

            const verifiedBadge = flood.is_verified
                ? '<span class="badge badge-low" style="background:#dcfce7;color:#166534;border:1px solid #bbf7d0;">✓ Đã xác minh (Admin)</span>'
                : '<span class="badge badge-medium" style="background:#fef3c7;color:#92400e;border:1px solid #fde68a;">⏳ Chờ duyệt (Dân báo)</span>';

            const depthText = flood.water_depth_cm ? `${flood.water_depth_cm} cm` : "Chưa ước tính";

            const popupHtml = `
                <div class="flood-popup" style="min-width:220px; font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;">
                    <div class="popup-title" style="font-weight:700; font-size:14px; color:#0f172a; margin-bottom:6px;">
                        🌊 ${flood.title}
                    </div>
                    <div class="popup-tags" style="display:flex; flex-wrap:wrap; gap:4px; margin-bottom:8px;">
                        <span class="badge ${sev.badgeClass}">${sev.icon} ${sev.label}</span>
                        ${verifiedBadge}
                    </div>
                    <p class="popup-desc" style="font-size:12px; color:#475569; margin:0 0 8px; line-height:1.4;">
                        ${flood.description || "Tình trạng đang được cộng đồng cập nhật."}
                    </p>
                    <div class="popup-meta" style="font-size:11px; color:#64748b; border-top:1px solid #f1f5f9; padding-top:6px; display:flex; flex-direction:column; gap:4px;">
                        <div>📏 <b>Mức nước:</b> <span style="color:#0f172a; font-weight:600;">${sev.label.split("(")[0]} (${depthText})</span></div>
                        <div>🕒 <b>Thời gian báo cáo:</b> <span style="color:#0f172a;">${timeFormatted}</span></div>
                        <div>📍 <b>Trạng thái:</b> ${flood.is_verified ? '<b style="color:#166534;">Đã xác minh</b>' : '<b style="color:#92400e;">Chờ quản trị duyệt</b>'}</div>
                        <div>🌐 <b>Bán kính ngập:</b> ${flood.radius_meters || 50} mét</div>
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

    /**
     * Hỗ trợ vẽ điểm ngập dạng Marker và Vùng đa giác (Circle/Polygon) trên Google Maps
     * (Đáp ứng yêu cầu Sprint 3 của đề bài)
     */
    renderOnGoogleMaps(gmap) {
        this.floods.forEach((flood) => {
            const sev = window.APP_CONFIG.SEVERITY_CONFIG[flood.severity_level] || window.APP_CONFIG.SEVERITY_CONFIG.low;
            const lat = flood.latitude;
            const lng = flood.longitude;

            // 1. Tạo Marker điểm ngập trên Google Maps
            const marker = new google.maps.Marker({
                position: { lat: lat, lng: lng },
                map: gmap,
                title: flood.title,
            });

            // Gắn cửa sổ thông tin InfoWindow chi tiết khi click vào Marker ngập (Task 35)
            // Hiển thị đầy đủ: mức nước, thời gian báo cáo, trạng thái xác minh
            const reportedDate = new Date(flood.reported_at);
            const timeFormatted = isNaN(reportedDate.getTime())
                ? "Vừa xong"
                : `${reportedDate.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" })} - ${reportedDate.toLocaleDateString("vi-VN")}`;

            const verifiedText = flood.is_verified
                ? '<span style="background:#dcfce7; color:#166534; padding:2px 6px; border-radius:10px; font-weight:bold; font-size:10px;">✓ Đã xác minh</span>'
                : '<span style="background:#fef3c7; color:#92400e; padding:2px 6px; border-radius:10px; font-weight:bold; font-size:10px;">⏳ Chờ duyệt</span>';

            const depthText = flood.water_depth_cm ? `${flood.water_depth_cm} cm` : "Chưa rõ";

            const infoWindow = new google.maps.InfoWindow({
                content: `
                    <div style="font-family: Arial, sans-serif; padding: 6px; max-width: 260px; line-height: 1.4;">
                        <h4 style="margin: 0 0 6px; color: #0f172a; font-size: 14px; font-weight: bold;">🌊 ${flood.title}</h4>
                        <div style="margin-bottom: 6px; display: flex; gap: 4px; align-items: center;">
                            <span style="color: ${sev.color}; font-weight: bold; font-size: 12px;">${sev.icon} ${sev.label}</span>
                            ${verifiedText}
                        </div>
                        <p style="margin: 0 0 6px; font-size: 12px; color: #475569;">${flood.description || "Điểm cảnh báo ngập lụt tại TP.HCM"}</p>
                        <div style="font-size: 11px; color: #64748b; border-top: 1px solid #e2e8f0; padding-top: 6px;">
                            <div>📏 <b>Mức nước:</b> <b style="color:#0f172a;">${sev.label.split("(")[0]} (${depthText})</b></div>
                            <div>🕒 <b>Thời gian báo cáo:</b> ${timeFormatted}</div>
                            <div>📍 <b>Trạng thái:</b> ${flood.is_verified ? '<span style="color:#166534;">Đã xác minh bởi Quản trị</span>' : '<span style="color:#92400e;">Báo cáo từ người dân</span>'}</div>
                            <div>🌐 <b>Bán kính:</b> ${flood.radius_meters || 50} mét</div>
                        </div>
                    </div>
                `,
            });

            marker.addListener("click", () => {
                infoWindow.open(gmap, marker);
            });

            this.markers.push(marker);

            // 2. Tạo Vùng đa giác hình tròn (Circle/Polygon) biểu thị bán kính ngập
            const floodCircle = new google.maps.Circle({
                map: gmap,
                center: { lat: lat, lng: lng },
                radius: flood.radius_meters || 50, // Bán kính ngập tính bằng mét
                fillColor: sev.color,
                fillOpacity: 0.22,
                strokeColor: sev.color,
                strokeWeight: 2,
            });

            this.googleCircles.push(floodCircle);
        });
    }

    /**
     * Dữ liệu mẫu dự phòng tại TP.HCM (Tránh lỗi màn hình trắng khi chưa chạy Backend/MySQL)
     */
    getSampleFloods() {
        return [
            {
                id: 1,
                title: "Đường Nguyễn Hữu Cảnh, Bình Thạnh",
                description: "Ngập sâu đoạn chân cầu Thủ Thiêm, xe chết máy hàng loạt",
                latitude: 10.7932,
                longitude: 106.7214,
                severity_level: "high",
                water_depth_cm: 45,
                radius_meters: 80,
                is_verified: true,
                reported_at: new Date().toISOString(),
            },
            {
                id: 2,
                title: "Đường Huỳnh Tấn Phát, Quận 7",
                description: "Triều cường dâng cao ngập nửa bánh xe",
                latitude: 10.7428,
                longitude: 106.7325,
                severity_level: "medium",
                water_depth_cm: 30,
                radius_meters: 60,
                is_verified: true,
                reported_at: new Date().toISOString(),
            },
            {
                id: 3,
                title: "Đường Quốc Hương, Thảo Điền",
                description: "Nước ngập mắt cá chân, các phương tiện di chuyển chậm",
                latitude: 10.8045,
                longitude: 106.7321,
                severity_level: "low",
                water_depth_cm: 15,
                radius_meters: 40,
                is_verified: false,
                reported_at: new Date().toISOString(),
            },
        ];
    }
}

window.FloodManager = new FloodManager();
