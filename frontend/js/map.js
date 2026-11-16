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

    /**
     * Khởi tạo đối tượng TrafficLayer để tải dữ liệu kẹt xe và mật độ giao thông theo thời gian thực.
     * Hỗ trợ chuẩn Google Maps API (new google.maps.TrafficLayer()) và MapLibre / OpenFreeMap raster flow.
     * (Task 24 & FR2.1 SRS)
     */
    initTrafficLayer() {
        // 1. Nếu tích hợp Google Maps API: khởi tạo đối tượng google.maps.TrafficLayer
        if (window.google && window.google.maps) {
            try {
                this.googleTrafficLayer = new google.maps.TrafficLayer();
                console.log("🚦 google.maps.TrafficLayer đã được khởi tạo thành công.");
            } catch (e) {
                console.warn("Không thể khởi tạo google.maps.TrafficLayer:", e);
            }
        }

        // 2. Nếu chạy trên MapLibre GL / OpenFreeMap:
        if (this.map && !this.map.getSource("traffic-flow-source")) {
            const config = window.APP_CONFIG;
            const apiKey = config.TOMTOM_API_KEY || "";
            const tileUrl = apiKey
                ? `https://api.tomtom.com/traffic/map/4/tile/flow/relative0/{z}/{x}/{y}.png?key=${apiKey}&tileSize=256`
                : `${config.API_BASE_URL}/api/v1/traffic/flow/{z}/{x}/{y}.png`;

            this.map.addSource("traffic-flow-source", {
                type: "raster",
                tiles: [tileUrl],
                tileSize: 256,
                minzoom: 0,
                maxzoom: 22,
                attribution: "© TomTom / Google Traffic Flow",
            });

            const firstSymbolLayer = this.map
                .getStyle()
                .layers.find((layer) => layer.type === "symbol")?.id;

            this.map.addLayer({
                id: "traffic-flow-layer",
                type: "raster",
                source: "traffic-flow-source",
                layout: {
                    visibility: "none", // Mặc định ẩn, điều khiển bằng nút công tắc Toggle switch
                },
                paint: {
                    "raster-opacity": 0.85,
                },
            }, firstSymbolLayer);

            console.log("🚦 Traffic Layer (MapLibre/OpenFreeMap) đã sẵn sàng.");
        }

        // Kích hoạt Toggle Switch trên giao diện
        const trafficSwitch = document.getElementById("trafficToggleSwitch");
        const trafficStatus = document.getElementById("trafficStatus");
        if (trafficSwitch) {
            trafficSwitch.disabled = false;
        }
        if (trafficStatus) {
            trafficStatus.textContent = "Sẵn sàng";
        }
    }

    /**
     * Nút công tắc (Toggle switch) cho phép người dùng chủ động ẩn hoặc hiển thị thông tin kẹt xe trên bản đồ.
     * (Task 25 & FR2.1 SRS)
     * @param {boolean} [enable] - true: hiển thị, false: ẩn, undefined: đảo trạng thái
     */
    toggleTraffic(enable) {
        this.isTrafficEnabled = (enable !== undefined) ? enable : !this.isTrafficEnabled;
        this.trafficErrorNotified = false;

        // 1. Toggle trên Google Maps nếu có đối tượng google.maps.TrafficLayer
        if (this.googleTrafficLayer) {
            // Hiển thị: gán map, Ẩn: gán null
            this.googleTrafficLayer.setMap(this.isTrafficEnabled ? this.googleMap : null);
        }

        // 2. Toggle trên MapLibre / OpenFreeMap
        if (this.map && this.map.getLayer("traffic-flow-layer")) {
            const visibility = this.isTrafficEnabled ? "visible" : "none";
            this.map.setLayoutProperty("traffic-flow-layer", "visibility", visibility);
        }

        // Cập nhật giao diện Legend và layout
        const trafficLegend = document.getElementById("trafficLegend");
        if (trafficLegend) trafficLegend.hidden = !this.isTrafficEnabled;

        const mainContent = document.querySelector(".main-content");
        if (mainContent) {
            mainContent.classList.toggle("traffic-enabled", this.isTrafficEnabled);
        }

        // Cập nhật trạng thái checkbox switch nếu gọi bằng hàm
        const trafficSwitch = document.getElementById("trafficToggleSwitch");
        if (trafficSwitch && trafficSwitch.checked !== this.isTrafficEnabled) {
            trafficSwitch.checked = this.isTrafficEnabled;
        }

        if (this.isTrafficEnabled) {
            window.App.showToast("🚦 Đã hiển thị lớp thông tin kẹt xe thời gian thực.", "success");
        } else {
            window.App.showToast("Đã ẩn lớp kẹt xe.", "info");
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
 * Định vị GPS vị trí hiện tại của người dùng.
 * Có thông báo dự phòng khi Geolocation không hoạt động.
 */
locateUser(showAlertOnSuccess = true) {

    // 1. Kiểm tra trình duyệt có hỗ trợ Geolocation không
    if (!navigator.geolocation) {
        window.App.showToast(
            "Thiết bị hoặc trình duyệt không hỗ trợ định vị GPS. Bạn vẫn có thể chọn vị trí trực tiếp trên bản đồ.",
            "warning"
        );
        return;
    }

    // 2. Yêu cầu trình duyệt cung cấp vị trí hiện tại
    navigator.geolocation.getCurrentPosition(

        // Trường hợp lấy vị trí thành công
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
                window.App.showToast(
                    "Vị trí hiện tại nằm ngoài ranh giới TP. Hồ Chí Minh.",
                    "warning"
                );
            }

            // Hiển thị marker vị trí người dùng
            this.renderUserMarker(lat, lng);

            // Di chuyển bản đồ đến vị trí GPS
            this.map.easeTo({
                center: [lng, lat],
                zoom: 15,
                duration: 1200,
            });

            if (showAlertOnSuccess) {
                window.App.showToast(
                    "🎯 Đã xác định vị trí hiện tại của bạn!",
                    "success"
                );
            }
        },

        // Trường hợp xảy ra lỗi Geolocation
        (error) => {
            console.warn("Geolocation error:", error);

            if (!showAlertOnSuccess) return;

            let title = "Không thể xác định vị trí";
            let message = "";

            switch (error.code) {

                // Người dùng từ chối quyền truy cập vị trí
                case 1:
                    title = "Bạn chưa cấp quyền vị trí";
                    message =
                        "Vui lòng cho phép trình duyệt truy cập vị trí trong cài đặt quyền riêng tư. Bạn vẫn có thể chọn vị trí thủ công trên bản đồ.";
                    break;

                // Không thể xác định vị trí thiết bị
                case 2:
                    title = "Không tìm thấy vị trí";
                    message =
                        "Thiết bị chưa cung cấp được thông tin GPS. Vui lòng kiểm tra kết nối hoặc thử lại sau. Bạn có thể chọn vị trí trên bản đồ.";
                    break;

                // Quá thời gian chờ lấy vị trí
                case 3:
                    title = "Yêu cầu định vị quá thời gian";
                    message =
                        "Hệ thống chưa nhận được vị trí trong thời gian chờ. Vui lòng thử lại hoặc chọn vị trí trực tiếp trên bản đồ.";
                    break;

                // Lỗi không xác định
                default:
                    title = "Đã xảy ra lỗi định vị";
                    message =
                        "Không thể lấy vị trí hiện tại. Bạn vẫn có thể tiếp tục sử dụng bản đồ và chọn vị trí thủ công.";
                    break;
            }

            // Hiển thị thông báo thân thiện
            window.App.showToast(
                `${title}. ${message}`,
                "warning"
            );
        },

        // Cấu hình định vị
        {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 30000,
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
