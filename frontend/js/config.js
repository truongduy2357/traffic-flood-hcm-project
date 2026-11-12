/**
 * CẤU HÌNH FRONTEND HỆ THỐNG BẢN ĐỒ CẢNH BÁO KẸT XE & NGẬP LỤT TPHCM
 * Sử dụng OpenFreeMap (https://openfreemap.org/) - HOÀN TOÀN MIỄN PHÍ, KHÔNG CẦN API KEY!
 */
window.APP_CONFIG = {
    MAP_PROVIDER: "openfreemap",
    
    // Các kiểu hiển thị bản đồ OpenFreeMap miễn phí (No API Key)
    STYLES: {
        liberty: "https://tiles.openfreemap.org/styles/liberty",
        bright: "https://tiles.openfreemap.org/styles/bright",
        positron: "https://tiles.openfreemap.org/styles/positron",
    },
    DEFAULT_STYLE: "https://tiles.openfreemap.org/styles/liberty",
    TRAFFIC_AVAILABLE: false,

    // Đường dẫn Base URL tới Backend FastAPI
    API_BASE_URL: window.location.origin.includes("localhost") || window.location.origin.includes("127.0.0.1")
        ? window.location.origin
        : "http://localhost:8000",

    // Giới hạn bản đồ TP. Hồ Chí Minh theo SRS (FR1.1)
    // MapLibre format: [[minLng, minLat], [maxLng, maxLat]]
    HCM_MAX_BOUNDS: [
        [106.35, 10.37], // Tây - Nam (Southwest)
        [106.93, 11.16], // Đông - Bắc (Northeast)
    ],

    // Tâm bản đồ TPHCM mặc định [lng, lat]
    HCM_CENTER: [106.7009, 10.7769],

    DEFAULT_ZOOM: 12.8,
    MIN_ZOOM: 10,
    MAX_ZOOM: 19,

    // Cấu hình màu sắc theo 3 cấp độ ngập (SRS FR3.1 & Task 30)
    SEVERITY_CONFIG: {
        low: {
            label: "Mắt cá chân (< 20cm)",
            color: "#10b981", // Xanh lá
            badgeClass: "badge-low",
            icon: "💧",
        },
        medium: {
            label: "Nửa bánh xe (20 - 40cm)",
            color: "#f59e0b", // Cam hổ phách
            badgeClass: "badge-medium",
            icon: "⚠️",
        },
        high: {
            label: "Lút bánh xe (> 40cm)",
            color: "#ef4444", // Đỏ cảnh báo nguy hiểm
            badgeClass: "badge-high",
            icon: "⛔",
        },
    },

    // Danh bạ địa điểm & ngã tư nổi tiếng tại TPHCM phục vụ Autocomplete nhanh không cần API Key bên ngoài
    HCM_PLACES: [
        { name: "Chợ Bến Thành, Quận 1", lat: 10.7725, lng: 106.6980 },
        { name: "Nhà thờ Đức Bà, Quận 1", lat: 10.7798, lng: 106.6990 },
        { name: "Phố đi bộ Nguyễn Huệ, Quận 1", lat: 10.7743, lng: 106.7032 },
        { name: "Tòa nhà Landmark 81, Bình Thạnh", lat: 10.7951, lng: 106.7219 },
        { name: "Cầu vượt Nguyễn Hữu Cảnh, Bình Thạnh", lat: 10.7932, lng: 106.7153 },
        { name: "Ngã tư Hàng Xanh, Bình Thạnh", lat: 10.8015, lng: 106.7112 },
        { name: "Bến xe Miền Đông cũ (Đinh Bộ Lĩnh), Bình Thạnh", lat: 10.8142, lng: 106.7118 },
        { name: "Đường Ung Văn Khiêm, Bình Thạnh", lat: 10.8085, lng: 106.7168 },
        { name: "Đường Quốc Hương, Thảo Điền, TP. Thủ Đức", lat: 10.8041, lng: 106.7352 },
        { name: "Chợ Thủ Đức (Võ Văn Ngân), TP. Thủ Đức", lat: 10.8504, lng: 106.7651 },
        { name: "Khu Công Nghệ Cao TPHCM, TP. Thủ Đức", lat: 10.8544, lng: 106.7904 },
        { name: "Sân bay Tân Sơn Nhất, Tân Bình", lat: 10.8185, lng: 106.6588 },
        { name: "Ngã tư Bảy Hiền, Tân Bình", lat: 10.7925, lng: 106.6534 },
        { name: "Đường Phan Huy Ích, Gò Vấp / Tân Bình", lat: 10.8354, lng: 106.6341 },
        { name: "Đường Lê Đức Thọ, Gò Vấp", lat: 10.8422, lng: 106.6713 },
        { name: "Cầu Ánh Sao - Hồ Bán Nguyệt, Quận 7", lat: 10.7292, lng: 106.7208 },
        { name: "Đường Huỳnh Tấn Phát, Quận 7", lat: 10.7423, lng: 106.7354 },
        { name: "Đường Trần Xuân Soạn (ven kênh Tẻ), Quận 7", lat: 10.7512, lng: 106.7028 },
        { name: "Vòng xoay Cây Gõ, Quận 6 / Quận 11", lat: 10.7589, lng: 106.6508 },
        { name: "Chợ Lớn (Bình Tây), Quận 6", lat: 10.7495, lng: 106.6504 },
        { name: "Bến xe Miền Tây, Bình Tân", lat: 10.7397, lng: 106.6171 },
        { name: "Đường An Dương Vương, Quận 6 / Bình Tân", lat: 10.7471, lng: 106.6215 },
        { name: "Đường Nguyễn Văn Quá, Quận 12", lat: 10.8475, lng: 106.6189 },
        { name: "Khu Đô Thị Phú Mỹ Hưng, Quận 7", lat: 10.7288, lng: 106.7118 },
        { name: "Hầm Thủ Thiêm (Bờ Quận 1 sang TP. Thủ Đức)", lat: 10.7686, lng: 106.7077 },
        { name: "Đại học Bách Khoa TPHCM (Lý Thường Kiệt), Quận 10", lat: 10.7721, lng: 106.6579 },
    ]
};
