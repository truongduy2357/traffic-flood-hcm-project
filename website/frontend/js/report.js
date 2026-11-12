/**
 * Quản lý Báo cáo Điểm ngập từ Cộng đồng (Crowdsourcing Reporter)
 * Hoạt động mượt mà với MapLibre GL JS & OpenFreeMap
 */
class ReportManager {
    constructor() {
        this.selectedSeverity = "low";
        this.selectedLat = null;
        this.selectedLng = null;
        this.isPickingLocation = false;
        this.tempPickerMarker = null;
    }

    init() {
        // Lắng nghe chọn mức ngập: Mắt cá chân, Nửa bánh xe, Lút bánh xe (FR3.2)
        const sevButtons = document.querySelectorAll(".severity-btn");
        sevButtons.forEach((btn) => {
            btn.addEventListener("click", () => {
                sevButtons.forEach((b) => b.classList.remove("selected"));
                btn.classList.add("selected");
                this.selectedSeverity = btn.getAttribute("data-level");
            });
        });

        // Form submit
        const form = document.getElementById("reportFloodForm");
        if (form) {
            form.addEventListener("submit", (e) => this.handleSubmit(e));
        }
    }

    openModal() {
        if (window.MapManager.userLocation) {
            this.setLocation(window.MapManager.userLocation.lat, window.MapManager.userLocation.lng);
        }
        document.getElementById("reportModal").classList.add("active");
    }

    closeModal() {
        document.getElementById("reportModal").classList.remove("active");
        this.stopPickingLocation();
    }

    useCurrentLocation() {
        if (window.MapManager.userLocation) {
            this.setLocation(window.MapManager.userLocation.lat, window.MapManager.userLocation.lng);
            window.App.showToast("Đã lấy vị trí GPS hiện tại của bạn!", "success");
        } else {
            window.MapManager.locateUser(true);
            setTimeout(() => {
                if (window.MapManager.userLocation) {
                    this.setLocation(window.MapManager.userLocation.lat, window.MapManager.userLocation.lng);
                }
            }, 1200);
        }
    }

    startPickOnMap() {
        this.isPickingLocation = true;
        this.closeModal();
        window.App.showToast("👉 Hãy CLICK vào một vị trí trên bản đồ để chọn tọa độ điểm ngập", "warning");

        const map = window.MapManager.map;
        if (map) {
            map.getCanvas().style.cursor = "crosshair";
        }
    }

    stopPickingLocation() {
        this.isPickingLocation = false;
        const map = window.MapManager.map;
        if (map) {
            map.getCanvas().style.cursor = "";
        }
    }

    handleMapClickLocation(lat, lng) {
        if (!this.isPickingLocation) return;
        this.setLocation(lat, lng);
        this.stopPickingLocation();

        const map = window.MapManager.map;
        if (map) {
            if (this.tempPickerMarker) {
                this.tempPickerMarker.setLngLat([lng, lat]);
            } else {
                const el = document.createElement("div");
                el.className = "report-picker-pin";
                el.innerHTML = "📍";
                this.tempPickerMarker = new maplibregl.Marker({
                    element: el,
                    anchor: "bottom",
                })
                    .setLngLat([lng, lat])
                    .addTo(map);
            }
        }

        this.openModal();
        window.App.showToast("Đã chọn tọa độ từ bản đồ!", "success");
    }

    setLocation(lat, lng) {
        this.selectedLat = parseFloat(lat.toFixed(6));
        this.selectedLng = parseFloat(lng.toFixed(6));

        const coordsInput = document.getElementById("reportCoordsDisplay");
        if (coordsInput) {
            coordsInput.value = `${this.selectedLat}, ${this.selectedLng}`;
        }
    }

    async handleSubmit(e) {
        e.preventDefault();

        const title = document.getElementById("reportTitle").value.trim();
        const description = document.getElementById("reportDesc").value.trim();
        const depth = document.getElementById("reportDepth").value;
        const radius = document.getElementById("reportRadius").value || 50;

        if (!title) {
            window.App.showToast("Vui lòng nhập tên đường hoặc khu vực ngập.", "warning");
            return;
        }

        if (!this.selectedLat || !this.selectedLng) {
            window.App.showToast("Vui lòng chọn vị trí điểm ngập (qua GPS hoặc click bản đồ).", "warning");
            return;
        }

        const payload = {
            title: title,
            description: description || null,
            severity_level: this.selectedSeverity,
            water_depth_cm: depth ? parseInt(depth, 10) : null,
            radius_meters: parseInt(radius, 10),
            latitude: this.selectedLat,
            longitude: this.selectedLng,
        };

        try {
            window.App.showLoading("Đang gửi báo cáo điểm ngập...");

            const res = await fetch(`${window.APP_CONFIG.API_BASE_URL}/api/v1/floods`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });

            const data = await res.json();

            if (res.status === 201) {
                window.App.showToast(" Gửi báo cáo ngập thành công! Cảm ơn bạn đã đóng góp cho cộng đồng.", "success");
                this.closeModal();
                document.getElementById("reportFloodForm").reset();
                if (this.tempPickerMarker) {
                    this.tempPickerMarker.remove();
                    this.tempPickerMarker = null;
                }
                // Tải lại danh sách điểm ngập
                window.FloodManager.fetchAndRenderFloods();
            } else if (res.status === 429) {
                window.App.showToast(data.message || "Bạn gửi quá nhanh! Vui lòng đợi 1 phút trước khi gửi tiếp.", "error");
            } else if (res.status === 422) {
                window.App.showToast("Tọa độ nằm ngoài phạm vi TP. Hồ Chí Minh.", "error");
            } else {
                window.App.showToast(data.message || "Có lỗi xảy ra khi gửi báo cáo.", "error");
            }
        } catch (err) {
            console.error("Lỗi khi submit báo cáo:", err);
            window.App.showToast("Không thể gửi dữ liệu tới máy chủ. Vui lòng kiểm tra lại mạng.", "error");
        } finally {
            window.App.hideLoading();
        }
    }
}

window.ReportManager = new ReportManager();
