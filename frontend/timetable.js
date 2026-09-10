(function () {
  const state = { pending: null, confirmed: null };
  const apiBase = (window.DCSION3_CONFIG && window.DCSION3_CONFIG.API_BASE_URL) || "";
  const root = document.getElementById("prototypeTimetable");
  if (!root) return;

  const grid = root.querySelector("[data-timetable-grid]");
  const previewGrid = root.querySelector("[data-timetable-preview]");
  const status = root.querySelector("[data-timetable-status]");
  const hint = root.querySelector("[data-timetable-hint]");
  const refreshLink = root.querySelector("[data-timetable-refresh]");
  const modal = root.querySelector("[data-timetable-modal]");
  const drawer = root.querySelector("[data-timetable-drawer]");
  const drawerTitle = root.querySelector("[data-timetable-drawer-title]");
  const drawerBody = root.querySelector("[data-timetable-drawer-body]");
  const drawerClose = root.querySelectorAll("[data-timetable-drawer-close]");
  const MALAYSIA_TIME_ZONE = "Asia/Kuala_Lumpur";

  function malaysiaDateString(date) {
    return new Intl.DateTimeFormat("en-CA", {
      timeZone: MALAYSIA_TIME_ZONE,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).format(date);
  }

  function formatDay(date) {
    return date.toLocaleDateString(undefined, {
      timeZone: MALAYSIA_TIME_ZONE,
      weekday: "short",
    });
  }

  function formatEventTime(event) {
    if (event.start === "All day") return "All day";
    return event.start + (event.end ? " – " + event.end : "");
  }

  function openDrawer(day, events) {
    if (window.matchMedia("(max-width: 680px)").matches) return;
    drawerTitle.textContent = day.toLocaleDateString(undefined, {
      timeZone: MALAYSIA_TIME_ZONE,
      weekday: "long",
      month: "short",
      day: "numeric",
    });
    drawerBody.replaceChildren();
    if (!events.length) {
      const empty = document.createElement("p");
      empty.className = "timetable-drawer__empty";
      empty.textContent = "No events scheduled for this day.";
      drawerBody.appendChild(empty);
    } else {
      events.forEach(function (event) {
        const item = document.createElement("article");
        item.className = "timetable-drawer__event";
        item.innerHTML = "<time></time><strong></strong>";
        item.querySelector("time").textContent = formatEventTime(event);
        item.querySelector("strong").textContent = event.title;
        if (event.location) {
          const location = document.createElement("small");
          location.textContent = event.location;
          item.appendChild(location);
        }
        drawerBody.appendChild(item);
      });
    }
    drawer.classList.add("is-open");
    drawer.setAttribute("aria-hidden", "false");
  }

  function closeDrawer() {
    drawer.classList.remove("is-open");
    drawer.setAttribute("aria-hidden", "true");
  }

  function render(target, timetable) {
    target.replaceChildren();
    const byDate = {};
    timetable.events.forEach(function (event) {
      (byDate[event.date] || (byDate[event.date] = [])).push(event);
    });
    const start = new Date(timetable.start_date + "T00:00:00");
    for (let offset = 0; offset < 7; offset += 1) {
      const day = new Date(start);
      day.setDate(start.getDate() + offset);
      const date = malaysiaDateString(day);
      const column = document.createElement("div");
      column.className = "prototype-timetable__day" + (date === malaysiaDateString(new Date()) ? " prototype-timetable__day--today" : "");
      column.dataset.date = date;
      column.setAttribute("role", "button");
      column.setAttribute("tabindex", "0");
      column.setAttribute("aria-label", "View " + formatDay(day) + " timetable");
      column.innerHTML = "<strong>" + formatDay(day) + "</strong><small>" +
        day.toLocaleDateString(undefined, {
          timeZone: MALAYSIA_TIME_ZONE,
          month: "short",
          day: "numeric",
        }) + "</small>";
      (byDate[date] || []).forEach(function (event) {
        const item = document.createElement("div");
        item.className = "prototype-timetable__event";
        item.innerHTML = "<b></b><span>" + event.start + " - " + event.end + "</span>";
        item.querySelector("b").textContent = event.title;
        column.appendChild(item);
      });
      column.addEventListener("click", function () {
        openDrawer(day, byDate[date] || []);
      });
      column.addEventListener("keydown", function (event) {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          openDrawer(day, byDate[date] || []);
        }
      });
      target.appendChild(column);
    }
    if (!timetable.events.length) target.innerHTML = '<div class="prototype-timetable__empty">No events this week.</div>';
  }

  function normalizeCalendarResponse(payload) {
    const events = (payload.timetable || []).map(function (event) {
      const start = event.start || "";
      const end = event.end || "";
      return {
        id: event.id,
        title: event.title || "(Untitled event)",
        location: event.location || "",
        date: start.includes("T") ? malaysiaDateString(new Date(start)) : start,
        start: start.includes("T") ? new Date(start).toLocaleTimeString([], {
          timeZone: MALAYSIA_TIME_ZONE,
          hour: "numeric",
          minute: "2-digit",
        }) : "All day",
        end: end.includes("T") ? new Date(end).toLocaleTimeString([], {
          timeZone: MALAYSIA_TIME_ZONE,
          hour: "numeric",
          minute: "2-digit",
        }) : "",
      };
    });
    return {
      start_date: malaysiaDateString(new Date()),
      events: events,
    };
  }

  async function fetchPreview() {
    refreshLink.setAttribute("aria-busy", "true");
    refreshLink.style.pointerEvents = "none";
    status.textContent = "Fetching the next seven days from Google Calendar...";
    try {
      const response = await fetch(apiBase + "/api/v1/calendar/timetable");
      if (response.status === 401) {
        window.location.href = apiBase + "/api/v1/calendar/oauth/start";
        return;
      }
      if (!response.ok) {
        throw new Error(response.status === 503
          ? "Google Calendar is not configured"
          : "Unable to fetch timetable");
      }
      state.pending = normalizeCalendarResponse(await response.json());
      render(previewGrid, state.pending);
      modal.classList.add("is-open");
      status.textContent = "Preview ready. Confirm it to keep it in memory.";
    } catch (error) {
      status.textContent = error.message === "Google Calendar is not configured"
        ? "Google Calendar is not configured on the server."
        : "Could not fetch Google Calendar. Try again.";
      grid.innerHTML = '<div class="prototype-timetable__error">Try fetching again.</div>';
    } finally {
      refreshLink.removeAttribute("aria-busy");
      refreshLink.style.pointerEvents = "";
    }
  }

  refreshLink.addEventListener("click", function (event) {
    event.preventDefault();
    fetchPreview();
  });
  drawerClose.forEach(function (button) {
    button.addEventListener("click", closeDrawer);
  });
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") closeDrawer();
  });
  root.querySelector("[data-timetable-discard]").addEventListener("click", function () {
    fetch(apiBase + "/api/v1/calendar/timetable/pending", { method: "DELETE" })
      .then(function (response) {
        if (!response.ok) throw new Error("Unable to discard timetable");
        state.pending = null;
        modal.classList.remove("is-open");
        status.textContent = "Preview discarded. The current timetable is unchanged.";
      })
      .catch(function () {
        status.textContent = "Could not discard the preview. Try again.";
      });
  });
  root.querySelector("[data-timetable-confirm]").addEventListener("click", function () {
    fetch(apiBase + "/api/v1/calendar/timetable/confirm", { method: "POST" })
      .then(function (response) {
        if (!response.ok) throw new Error("Unable to confirm timetable");
        state.confirmed = state.pending;
        render(grid, state.confirmed);
        modal.classList.remove("is-open");
        status.textContent = "Confirmed. Stored in temporary memory only.";
        hint.textContent = "Calendar looks outdated?";
        refreshLink.textContent = "Fetch it manually";
      })
      .catch(function () {
        status.textContent = "Could not confirm the timetable. Try again.";
      });
  });
}());
