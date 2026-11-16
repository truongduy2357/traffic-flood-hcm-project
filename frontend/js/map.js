/**
 * Quản lý Bản đồ OpenFreeMap với MapLibre GL JS
 * Định vị vị trí người dùng cố định, không kéo thả, không ghim rườm rà
 */
class MapManager {
    constructor() {
        this.map = null;
        this.userMarker = null;
        this.userLocation = null;
        this.isTrafficEnabled = false;
        this.trafficErrorNotified = false;
        this.isInitialized = false;
        this.currentStyle = window.APP_CONFIG.DEFAULT_STYLE;
    }

    /**
     * Khởi tạo bản đồ OpenFreeMap với MapLibre GL JS
     */
    init(containerId = "map") {
        const config = window.APP_CONFIG;

        try {
            this.map = new maplibregl.Map({
                container: containerId,
                style: this.currentStyle,
                center: config.HCM_CENTER, // [lng, lat]
                zoom: config.DEFAULT_ZOOM,
                minZoom: config.MIN_ZOOM,
                maxZoom: config.MAX_ZOOM,
                maxBounds: config.HCM_MAX_BOUNDS,
                attributionControl: true,
            });

            this.map.addControl(
                new maplibregl.NavigationControl({ visualizePitch: true }),
                "top-right"
            );

            this.map.on("load", () => {
                this.isInitialized = true;
                console.log(" Bản đồ OpenFreeMap đã khởi tạo thành công.");

                const notice = document.getElementById("mapLoadingNotice");
                if (notice) notice.style.display = "none";

                // Khởi tạo lớp kẹt xe giao thông TPHCM
                this.initTrafficLayer();

                // Vẽ điểm ngập lên bản đồ
                window.FloodManager.fetchAndRenderFloods();

                // Khởi tạo các quản lý tuyến đường và báo cáo
                window.RouteManager.init();
                window.ReportManager.init();

                // Tự động định vị GPS vị trí hiện tại
                this.locateUser(false);
            });

            this.map.on("error", (err) => {
                console.warn("MapLibre GL Notice:", err);
                if (
                    err.sourceId === "traffic-flow-source" &&
                    this.isTrafficEnabled &&
                    !this.trafficErrorNotified
                ) {
                    this.trafficErrorNotified = true;
                    window.App.showToast(
                        "Không tải được dữ liệu TomTom. Kiểm tra API key và kết nối mạng.",
                        "error"
                    );
                }
            });

            this.map.on("click", (e) => {
                const { lng, lat } = e.lngLat;
                if (window.ReportManager && window.ReportManager.isPickingLocation) {
                    window.ReportManager.handleMapClickLocation(lat, lng);
                }
            });
        } catch (e) {
            console.error("Lỗi khởi tạo MapLibre GL:", e);
        }
    }

    /** Khởi tạo lớp tile giao thông trực tiếp TomTom. */
    initTrafficLayer() {
        if (!this.map) return;

        if (!this.map.getSource("traffic-flow-source")) {
            this.map.addSource("traffic-flow-source", {
                type: "raster",
                tiles: [
                    `${window.APP_CONFIG.API_BASE_URL}/api/v1/traffic/flow/{z}/{x}/{y}.png`,
                ],
                tileSize: 256,
                minzoom: 0,
                maxzoom: 22,
                attribution: "© TomTom",
            });

            const firstSymbolLayer = this.map
                .getStyle()
                .layers.find((layer) => layer.type === "symbol")?.id;
            this.map.addLayer({
                id: "traffic-flow-layer",
                type: "raster",
                source: "traffic-flow-source",
                layout: {
                    visibility: "none",
                },
                paint: {
                    "raster-opacity": 0.9,
                },
            }, firstSymbolLayer);
        }
    }

    toggleTraffic(enable) {
        if (!this.map || !this.map.getLayer("traffic-flow-layer")) return;
        if (enable && !window.APP_CONFIG.TRAFFIC_AVAILABLE) {
            const trafficSwitch = document.getElementById("trafficToggleSwitch");
            if (trafficSwitch) trafficSwitch.checked = false;
            window.App.showToast("Cần cấu hình TOMTOM_API_KEY để bật giao thông.", "warning");
            return false;
        }
        this.isTrafficEnabled = (enable !== undefined) ? enable : !this.isTrafficEnabled;
        this.trafficErrorNotified = false;

        const visibility = this.isTrafficEnabled ? "visible" : "none";
        this.map.setLayoutProperty("traffic-flow-layer", "visibility", visibility);
        const trafficLegend = document.getElementById("trafficLegend");
        if (trafficLegend) trafficLegend.hidden = !this.isTrafficEnabled;
        const mainContent = document.querySelector(".main-content");
        if (mainContent) {
            mainContent.classList.toggle("traffic-enabled", this.isTrafficEnabled);
        }

        if (this.isTrafficEnabled) {
            window.App.showToast("Đã bật lớp giao thông trực tiếp TomTom.", "success");
        } else {
            window.App.showToast("Đã tắt lớp giao thông", "warning");
        }
        return this.isTrafficEnabled;
    }

    setStyle(styleKey) {
        const styleUrl = window.APP_CONFIG.STYLES[styleKey] || window.APP_CONFIG.STYLES.liberty;
        this.currentStyle = styleUrl;
        this.map.setStyle(styleUrl);
        this.map.once("style.load", () => {
            this.initTrafficLayer();
            if (this.isTrafficEnabled) this.toggleTraffic(true);
            window.FloodManager.renderOnMap();
            if (this.userLocation) {
                this.renderUserMarker(this.userLocation.lat, this.userLocation.lng);
            }
        });
        window.App.showToast(`Đã chuyển kiểu bản đồ sang ${styleKey.toUpperCase()}`, "info");
    }

    /**
     * Định vị GPS vị trí hiện tại của người dùng
     */
    locateUser(showAlertOnSuccess = true) {
        if (!navigator.geolocation) {
            window.App.showToast("Thiết bị hoặc trình duyệt không hỗ trợ định vị.", "error");
            return;
        }

        navigator.geolocation.getCurrentPosition(
            (position) => {
                const lat = position.coords.latitude;
                const lng = position.coords.longitude;

                this.userLocation = { lat, lng };

                const bounds = window.APP_CONFIG.HCM_MAX_BOUNDS;
                const isInsideHCM = (
                    lng >= bounds[0][0] && lng <= bounds[1][0] &&
                    lat >= bounds[0][1] && lat <= bounds[1][1]
                );

                if (!isInsideHCM) {
                    window.App.showToast("Vị trí ước tính của bạn nằm ngoài ranh giới TP. Hồ Chí Minh.", "warning");
                }

                this.renderUserMarker(lat, lng);

                // Di chuyển êm ái tới vị trí hiện tại
                this.map.easeTo({
                    center: [lng, lat],
                    zoom: 15,
                    duration: 1200,
                });

                if (showAlertOnSuccess) {
                    window.App.showToast("🎯 Đã định vị vị trí hiện tại của bạn!", "success");
                }
            },
            (error) => {
                console.warn("Geolocation error:", error);
                if (showAlertOnSuccess) {
                    let errMsg = "Không thể lấy vị trí GPS.";
                    if (error.code === error.PERMISSION_DENIED) {
                        errMsg = "Bạn đã từ chối quyền truy cập vị trí. Hãy bật lại quyền trong cài đặt trình duyệt.";
                    }
                    window.App.showToast(errMsg, "warning");
                }
            },
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 30000, // Bộ nhớ đệm 30s tránh quét liên tục
            }
        );
    }

    /**
     * Render Marker vị trí người dùng cố định, tĩnh, không rung lắc
     */
    renderUserMarker(lat, lng) {
        if (this.userMarker) {
            this.userMarker.setLngLat([lng, lat]);
            return;
        }

        const el = document.createElement("div");
        el.className = "user-location-marker";
        el.innerHTML = `
            <div class="user-halo"></div>
            <div class="user-dot"></div>
        `;

        this.userMarker = new maplibregl.Marker({
            element: el,
            anchor: "center",
            draggable: false, // Cố định tâm tại vị trí, không trôi khi zoom
        })
            .setLngLat([lng, lat])
            .setPopup(new maplibregl.Popup({ offset: 12 }).setHTML("<b>🎯 Vị trí của bạn</b>"))
            .addTo(this.map);
    }

    panTo(lat, lng, zoom = 15.5) {
        if (!this.map) return;
        this.map.easeTo({
            center: [lng, lat],
            zoom: zoom,
            duration: 800,
        });
    }
}

window.MapManager = new MapManager();
