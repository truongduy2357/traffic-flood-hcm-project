/**
 * Quản lý Tìm đường & Kiểm tra ngập trên OpenFreeMap (Hoàn toàn không cần API Key)
 * Tích hợp OSRM Routing và bộ tìm kiếm địa điểm TPHCM tức thời
 */
class RouteManager {
  constructor() {
    this.originPoint = null; // { lat, lng, name }
    this.destPoint = null; // { lat, lng, name }
    this.currentRoutes = [];
    this.activeRouteIndex = 0;
    this.pickingMode = null; // 'origin' hoặc 'dest'
    this.tempMarkers = [];
  }

  init() {
    // Tích hợp Google Places Autocomplete API hỗ trợ gợi ý địa chỉ nhanh khi gõ (Task 37)
    const googleOriginOk = this.setupGooglePlacesAutocomplete(
      "originInput",
      (item) => {
        this.originPoint = item;
        this.addTempMarker(item.lat, item.lng, "origin", item.name);
        window.App.showToast(`Đã chọn điểm đi (A): ${item.name}`, "info");
      },
    );

    const googleDestOk = this.setupGooglePlacesAutocomplete(
      "destinationInput",
      (item) => {
        this.destPoint = item;
        this.addTempMarker(item.lat, item.lng, "dest", item.name);
        window.App.showToast(`Đã chọn điểm đến (B): ${item.name}`, "info");
      },
    );

    // Bộ gợi ý địa chỉ nhanh tức thời dự phòng (Instant Places Autocomplete tại TP.HCM)
    if (!googleOriginOk) {
      this.setupAutocomplete("originInput", "originDropdown", (item) => {
        this.originPoint = item;
        document.getElementById("originInput").value = item.name;
        this.addTempMarker(item.lat, item.lng, "origin", item.name);
      });
    }

    if (!googleDestOk) {
      this.setupAutocomplete("destinationInput", "destDropdown", (item) => {
        this.destPoint = item;
        document.getElementById("destinationInput").value = item.name;
        this.addTempMarker(item.lat, item.lng, "dest", item.name);
      });
    }
  }

  /**
   * Tích hợp Google Places Autocomplete API vào ô nhập điểm đi/đến (Task 37 - SRS FR4.1)
   */
  setupGooglePlacesAutocomplete(inputId, onSelect) {
    const input = document.getElementById(inputId);
    if (
      !input ||
      !window.google ||
      !window.google.maps ||
      !window.google.maps.places
    ) {
      return false;
    }

    try {
      // Giới hạn gợi ý trong phạm vi TP.HCM (Vĩ độ: 10.37-11.16, Kinh độ: 106.35-106.93)
      const hcmBounds = new google.maps.LatLngBounds(
        new google.maps.LatLng(
          window.APP_CONFIG.HCM_MAX_BOUNDS[0][1],
          window.APP_CONFIG.HCM_MAX_BOUNDS[0][0],
        ),
        new google.maps.LatLng(
          window.APP_CONFIG.HCM_MAX_BOUNDS[1][1],
          window.APP_CONFIG.HCM_MAX_BOUNDS[1][0],
        ),
      );

      const autocomplete = new google.maps.places.Autocomplete(input, {
        bounds: hcmBounds,
        componentRestrictions: { country: "vn" },
        fields: ["formatted_address", "geometry", "name"],
        strictBounds: false,
      });

      autocomplete.addListener("place_changed", () => {
        const place = autocomplete.getPlace();
        if (place.geometry && place.geometry.location) {
          const lat = place.geometry.location.lat();
          const lng = place.geometry.location.lng();
          const name = place.name || place.formatted_address;
          onSelect({ lat, lng, name });
        }
      });

      console.log(
        `📍 Google Places Autocomplete API đã sẵn sàng cho #${inputId}`,
      );
      return true;
    } catch (e) {
      console.warn(
        `Lỗi khởi tạo Google Places Autocomplete cho #${inputId}:`,
        e,
      );
      return false;
    }
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
        p.name.toLowerCase().includes(val),
      ).slice(0, 6);

      if (matches.length === 0) {
        dropdown.style.display = "none";
        return;
      }

      dropdown.innerHTML = matches
        .map(
          (m) => `
                <div class="autocomplete-item" data-name="${m.name}" data-lat="${m.lat}" data-lng="${m.lng}">
                    <span>📍</span>
                    <div>
                        <div style="font-weight:600; font-size:13px; color:#1e293b;">${m.name}</div>
                        <div style="font-size:11px; color:#64748b;">${m.lat.toFixed(4)}, ${m.lng.toFixed(4)}</div>
                    </div>
                </div>
            `,
        )
        .join("");

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
      this.originPoint = {
        lat: loc.lat,
        lng: loc.lng,
        name: "Vị trí hiện tại của tôi",
      };
      document.getElementById("originInput").value = "Vị trí hiện tại của tôi";
      this.addTempMarker(loc.lat, loc.lng, "origin", "Vị trí của bạn");
      window.App.showToast(
        "Đã chọn vị trí hiện tại làm điểm đi (A)!",
        "success",
      );
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
    const msg =
      mode === "origin"
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
      window.App.showToast(
        "Vui lòng chọn đầy đủ Điểm đi (A) và Điểm đến (B).",
        "warning",
      );
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
        window.App.showToast(
          "Không tìm thấy đường đi giữa 2 điểm này.",
          "error",
        );
        return;
      }

      this.currentRoutes = data.routes;
      let routeIndex = 0;
      let chosenRoute = data.routes[0];

      // Nếu người dùng yêu cầu né ngập
      if (forceAlternative) {
        if (data.routes.length > 1) {
          routeIndex = 1;
          chosenRoute = data.routes[1];
        } else {
          // Khi OSRM chỉ có 1 tuyến, tự động tính toán điểm trung chuyển né ngập
          const detourLat = (o.lat + d.lat) / 2 + 0.008;
          const detourLng = (o.lng + d.lng) / 2 - 0.008;
          try {
            const detourUrl = `https://router.project-osrm.org/route/v1/driving/${o.lng},${o.lat};${detourLng.toFixed(5)},${detourLat.toFixed(5)};${d.lng},${d.lat}?overview=full&geometries=geojson`;
            const detourRes = await fetch(detourUrl);
            if (detourRes.ok) {
              const detourData = await detourRes.json();
              if (detourData.routes && detourData.routes.length > 0) {
                chosenRoute = detourData.routes[0];
                routeIndex = 1;
              }
            }
          } catch (e) {
            console.warn("Không thể tải tuyến tránh OSRM:", e);
          }
        }
      }

      this.activeRouteIndex = routeIndex;
      const coordinates = chosenRoute.geometry.coordinates; // [[lng, lat], ...]

      // Vẽ tuyến đường lên bản đồ OpenFreeMap
      this.drawRouteOnMap(coordinates, routeIndex === 1);

      // Gửi danh sách tọa độ và polyline về FastAPI backend để giải mã LINESTRING và chạy ST_Intersects, ST_Distance_Sphere (Task 39 & 40)
      const pointsPayload = coordinates.map((c) => ({
        latitude: c[1],
        longitude: c[0],
      }));

      // Nếu OSRM/Google trả về chuỗi polyline thì gửi kèm
      const polylineStr =
        typeof chosenRoute.geometry === "string" ? chosenRoute.geometry : null;
      await this.checkRouteFlood(
        pointsPayload,
        polylineStr,
        data.routes.length > 1,
      );
    } catch (err) {
      console.warn("OSRM error, dùng đường bay trực tiếp dự phòng:", err);
      // Fallback vẽ đường nối trực tiếp
      const coords = [
        [o.lng, o.lat],
        [d.lng, d.lat],
      ];
      this.drawRouteOnMap(coords, false);
      const pointsPayload = [
        { latitude: o.lat, longitude: o.lng },
        { latitude: d.lat, longitude: d.lng },
      ];
      await this.checkRouteFlood(pointsPayload, null, false);
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

  async checkRouteFlood(points, encodedPolyline, hasAlternatives) {
    try {
      window.App.showLoading(
        "Đang giải mã LINESTRING và kiểm tra giao cắt không gian (ST_Intersects)...",
      );

      const response = await fetch(
        `${window.APP_CONFIG.API_BASE_URL}/api/v1/routes/check-flood`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            encoded_polyline: encodedPolyline,
            points: points,
            buffer_meters: 60,
          }),
        },
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      this.renderWarningUI(data, hasAlternatives);
    } catch (error) {
      console.error("Lỗi khi kiểm tra ngập trên tuyến đường:", error);
      window.App.showToast(
        "Không thể kết nối đến API kiểm tra không gian tuyến đường.",
        "warning",
      );
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

    // Tương thích cả has_flood và is_safe
    const isDangerous =
      checkResult.has_flood === true || checkResult.is_safe === false;
    const floodsList =
      checkResult.floods || checkResult.intercepted_floods || [];

    if (!isDangerous) {
      warningBanner.classList.remove("active");
      safeBanner.classList.add("active");
      safeBanner.innerHTML = `
                <div style="font-weight: 700; margin-bottom: 4px;">✅ Tuyến đường AN TOÀN!</div>
                <div>${checkResult.warning_message || "Không phát hiện điểm ngập nào trên lộ trình di chuyển."}</div>
                ${checkResult.linestring_wkt ? `<div style="font-size:11px; color:#166534; margin-top:4px; font-family:monospace;">ST_Intersects OK (${checkResult.total_points} điểm)</div>` : ""}
            `;
      window.App.showToast(
        "Lộ trình an toàn, không có điểm ngập nguy hiểm!",
        "success",
      );
    } else {
      safeBanner.classList.remove("active");
      warningBanner.classList.add("active");

      if (warningDesc) {
        warningDesc.textContent =
          checkResult.warning_message ||
          "CẢNH BÁO: Tuyến đường cắt qua vùng ngập!";
      }
      if (warningAction) {
        warningAction.textContent =
          checkResult.suggested_action ||
          (checkResult.max_severity === "high"
            ? "Khuyến cáo: Mức ngập lút bánh xe, phương tiện không thể lưu thông! Vui lòng chọn lộ trình khác."
            : "Khuyến cáo: Đường ngập nước, nên giảm tốc độ hoặc chuyển sang tuyến đường né ngập.");
      }

      if (interceptedList) {
        interceptedList.innerHTML = floodsList
          .map(
            (item) => `
                    <div style="font-size: 12px; margin-top: 6px; padding: 6px; background: #fff5f5; border-radius: 4px; border-left: 3px solid #ef4444;">
                        <b>• ${item.title || `Điểm ngập #${item.id}`}</b> (${(item.severity_level || "low").toUpperCase()})
                        - Cách lộ trình: <b>${item.distance_to_route_meters || 0}m</b>
                    </div>
                `,
          )
          .join("");
      }

      if (avoidBtn) {
        if (hasAlternatives && this.activeRouteIndex === 0) {
          avoidBtn.style.display = "block";
          avoidBtn.textContent = "🔄 Chuyển sang lộ trình né ngập";
        } else {
          avoidBtn.style.display = "none";
          if (isDangerous && !hasAlternatives) {
            window.App.showToast("Không tìm được đường né ngập thay thế. Hãy cẩn thận khi lưu thông.", "warning");
          }
        }
      }

      window.App.showToast(
        "⚠️ CẢNH BÁO: Tuyến đường cắt qua điểm ngập!",
        "error",
      );
    }
  }

  clearRoute() {
    const map = window.MapManager.map;
    if (map) {
      if (map.getLayer("user-route-line")) map.removeLayer("user-route-line");
      if (map.getLayer("user-route-casing"))
        map.removeLayer("user-route-casing");
      if (map.getSource("user-route-source"))
        map.removeSource("user-route-source");
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
