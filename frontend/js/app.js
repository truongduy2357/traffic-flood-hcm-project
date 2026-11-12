/**
 * Điều phối chính toàn bộ ứng dụng Frontend (Vanilla JS)
 * Hoạt động mượt mà với OpenFreeMap (Hoàn toàn miễn phí, KHÔNG CẦN API KEY)
 */
class Application {
  constructor() {
    this.config = window.APP_CONFIG;
  }

  async start() {
    console.log(
      "🌊 Khởi động ứng dụng Bản đồ Cảnh báo Kẹt xe & Ngập lụt TPHCM (OpenFreeMap)...",
    );

    // 1. Thử đồng bộ cấu hình từ Backend API
    await this.syncConfigFromBackend();

    // 2. Khởi tạo bản đồ OpenFreeMap ngay lập tức
    window.MapManager.init();

    // 3. Khởi tạo các sự kiện giao diện
    this.bindEvents();
  }

  async syncConfigFromBackend() {
    try {
      const res = await fetch(`${this.config.API_BASE_URL}/api/v1/config`);
      if (!res.ok) {
        throw new Error(`Lấy cấu hình backend thất bại: HTTP ${res.status}`);
      }
      const data = await res.json();
      if (data.openfreemap_style_url) {
        this.config.DEFAULT_STYLE = data.openfreemap_style_url;
      }
      this.config.TRAFFIC_AVAILABLE = data.traffic_available === true;

      const trafficSwitch = document.getElementById("trafficToggleSwitch");
      const trafficStatus = document.getElementById("trafficStatus");
      if (trafficSwitch) trafficSwitch.disabled = !this.config.TRAFFIC_AVAILABLE;
      if (trafficStatus) trafficStatus.hidden = this.config.TRAFFIC_AVAILABLE;
    } catch (e) {
      console.warn("Dùng cấu hình OpenFreeMap mặc định:", e);
      const trafficStatus = document.getElementById("trafficStatus");
      if (trafficStatus) trafficStatus.textContent = "Không kết nối backend";
    }
  }

  bindEvents() {
    // Công tắc bật/tắt Lớp giao thông kẹt xe (Traffic Switch)
    const trafficSwitch = document.getElementById("trafficToggleSwitch");
    if (trafficSwitch) {
      trafficSwitch.addEventListener("change", (e) => {
        window.MapManager.toggleTraffic(e.target.checked);
      });
    }

    // Chọn kiểu bản đồ OpenFreeMap (Style Selector)
    const styleSelect = document.getElementById("mapStyleSelect");
    if (styleSelect) {
      styleSelect.addEventListener("change", (e) => {
        window.MapManager.setStyle(e.target.value);
      });
    }

    // Nút nổi (FAB) Định vị GPS
    const locateBtn = document.getElementById("recenterFab");
    if (locateBtn) {
      locateBtn.addEventListener("click", () => {
        window.MapManager.locateUser(true);
      });
    }

    // Nút nổi (FAB) Báo cáo điểm ngập mới
    const reportFab = document.getElementById("reportFloodFab");
    if (reportFab) {
      reportFab.addEventListener("click", () => {
        window.ReportManager.openModal();
      });
    }

    // Mở / Đóng Sidebar điều hướng
    const sidebarToggleBtn = document.getElementById("sidebarToggleBtn");
    const sidebar = document.getElementById("sidebarPanel");
    if (sidebarToggleBtn) {
      sidebarToggleBtn.setAttribute(
        "aria-expanded",
        String(sidebar?.classList.contains("active") ?? false),
      );
      sidebarToggleBtn.addEventListener("click", () => this.toggleSidebar());
    }

    // Tabs: Danh sách ngập vs Tìm đường né ngập
    const tabList = document.getElementById("tabFloodListBtn");
    const tabRoute = document.getElementById("tabRouteBtn");
    const sectionList = document.getElementById("sectionFloodList");
    const sectionRoute = document.getElementById("sectionRoute");

    if (tabList && tabRoute) {
      tabList.addEventListener("click", () => {
        tabList.classList.add("btn-primary");
        tabList.classList.remove("btn-outline");
        tabRoute.classList.remove("btn-primary");
        tabRoute.classList.add("btn-outline");
        sectionList.style.display = "block";
        sectionRoute.style.display = "none";
      });

      tabRoute.addEventListener("click", () => {
        tabRoute.classList.add("btn-primary");
        tabRoute.classList.remove("btn-outline");
        tabList.classList.remove("btn-primary");
        tabList.classList.add("btn-outline");
        sectionRoute.style.display = "block";
        sectionList.style.display = "none";
      });
    }

    // Bộ lọc mức ngập (Tất cả, Lút bánh, Nửa bánh, Mắt cá)
    const filterPills = document.querySelectorAll(".filter-pill");
    filterPills.forEach((pill) => {
      pill.addEventListener("click", () => {
        filterPills.forEach((p) => p.classList.remove("active"));
        pill.classList.add("active");
        const level = pill.getAttribute("data-filter");
        window.FloodManager.renderSidebarList(level);
      });
    });
  }

  toggleSidebar(open) {
    const sidebar = document.getElementById("sidebarPanel");
    if (!sidebar) return;
    const shouldOpen =
      open === undefined ? !sidebar.classList.contains("active") : open;
    sidebar.classList.toggle("active", shouldOpen);

    const sidebarToggleBtn = document.getElementById("sidebarToggleBtn");
    if (sidebarToggleBtn) {
      sidebarToggleBtn.setAttribute("aria-expanded", String(shouldOpen));
    }
  }

  showToast(message, type = "info") {
    const container = document.getElementById("toastContainer");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast ${type}`;

    let icon = "ℹ️";
    if (type === "success") icon = "✅";
    if (type === "error") icon = "❌";
    if (type === "warning") icon = "⚠️";

    toast.innerHTML = `
            <span>${icon}</span>
            <div class="toast-message">${message}</div>
        `;

    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateX(20px)";
      toast.style.transition = "all 0.3s ease";
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }

  showLoading(text = "Đang xử lý...") {
    const spinner = document.getElementById("spinnerOverlay");
    const spinnerText = document.getElementById("spinnerText");
    if (spinner) {
      if (spinnerText) spinnerText.textContent = text;
      spinner.classList.add("active");
    }
  }

  hideLoading() {
    const spinner = document.getElementById("spinnerOverlay");
    if (spinner) spinner.classList.remove("active");
  }
}

window.App = new Application();

document.addEventListener("DOMContentLoaded", () => {
  window.App.start();
});
