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

  function formatDay(date) {
    return date.toLocaleDateString(undefined, { weekday: "short" });
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
      const date = day.toISOString().slice(0, 10);
      const column = document.createElement("div");
      column.className = "prototype-timetable__day" + (date === new Date().toISOString().slice(0, 10) ? " prototype-timetable__day--today" : "");
      column.innerHTML = "<strong>" + formatDay(day) + "</strong><small>" +
        day.toLocaleDateString(undefined, { month: "short", day: "numeric" }) + "</small>";
      (byDate[date] || []).forEach(function (event) {
        const item = document.createElement("div");
        item.className = "prototype-timetable__event";
        item.innerHTML = "<b></b><span>" + event.start + " - " + event.end + "</span>";
        item.querySelector("b").textContent = event.title;
        column.appendChild(item);
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
        date: start.slice(0, 10),
        start: start.includes("T") ? new Date(start).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }) : "All day",
        end: end.includes("T") ? new Date(end).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }) : "",
      };
    });
    return {
      start_date: new Date().toISOString().slice(0, 10),
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
