// Applies rotation to direction arrows via the CSSOM instead of inline
// style="transform:..." attributes, so the page has zero inline styles and
// the CSP style-src can stay 'self' only (no 'unsafe-inline').
document.querySelectorAll("[data-rotate-deg]").forEach((element) => {
  const degrees = Number(element.dataset.rotateDeg);
  if (!Number.isNaN(degrees)) {
    element.style.transform = `rotate(${degrees}deg)`;
  }
});

const form = document.getElementById("search-form");
const locationInput = document.getElementById("location-query");
const originLatInput = document.getElementById("origin-lat");
const originLonInput = document.getElementById("origin-lon");
const originSourceInput = document.getElementById("origin-source");
const resolvedLabelInput = document.getElementById("resolved-location-label");
const useMyLocationButton = document.getElementById("use-my-location-btn");
const statusText = document.getElementById("location-status");
const loadingScreen = document.getElementById("loading-screen");
const loadingMessage = document.getElementById("loading-message");
const primarySubmitButton = form.querySelector('button[type="submit"]');
const metricUnitsButton = document.getElementById("metric-units-btn");
const usUnitsButton = document.getElementById("us-units-btn");
const skillLevelInfoButton = document.getElementById("skill-level-info-btn");
const skillLevelHelp = document.getElementById("skill-level-help");
const autocompletePanel = document.getElementById("location-autocomplete");
let activeSuggestionIndex = -1;
let filteredSuggestions = [];
let autocompleteRequestTimer = null;
let activeAutocompleteController = null;

function clearResolvedOrigin() {
  originLatInput.value = "";
  originLonInput.value = "";
  originSourceInput.value = "manual";
  resolvedLabelInput.value = "";
}

function setStatus(message, isError = false) {
  statusText.textContent = message;
  statusText.style.color = isError ? "var(--danger)" : "var(--muted)";
}

function roundToOne(value) {
  return Math.round(value * 10) / 10;
}

function formatUnitValue(kind, value, system) {
  const numericValue = Number(value);
  if (Number.isNaN(numericValue)) {
    return "N/A";
  }

  if (system === "us") {
    if (kind === "distance") {
      return `${roundToOne(numericValue * 0.621371)} mi`;
    }
    if (kind === "wave") {
      return `${roundToOne(numericValue * 3.28084)} ft`;
    }
    if (kind === "wind") {
      return `${roundToOne(numericValue * 0.621371)} mph`;
    }
    if (kind === "temperature") {
      return `${roundToOne((numericValue * 9) / 5 + 32)} °F`;
    }
  }

  if (kind === "distance") {
    return `${numericValue} km`;
  }
  if (kind === "wave") {
    return `${numericValue} m`;
  }
  if (kind === "wind") {
    return `${numericValue} km/h`;
  }
  if (kind === "temperature") {
    return `${numericValue} °C`;
  }

  return String(value);
}

function applyUnitSystem(system) {
  const unitValues = document.querySelectorAll(".unit-value");
  unitValues.forEach((element) => {
    const kind = element.dataset.kind;
    const value = element.dataset.value;
    element.textContent = formatUnitValue(kind, value, system);
  });

  metricUnitsButton.classList.toggle("active", system === "metric");
  usUnitsButton.classList.toggle("active", system === "us");
  window.localStorage.setItem("surfspot-units", system);
}

function closeAutocomplete() {
  autocompletePanel.classList.remove("visible");
  autocompletePanel.innerHTML = "";
  locationInput.setAttribute("aria-expanded", "false");
  activeSuggestionIndex = -1;
}

function applySuggestion(suggestion) {
  locationInput.value = suggestion.value;
  clearResolvedOrigin();
  closeAutocomplete();
}

function renderAutocomplete() {
  autocompletePanel.innerHTML = "";

  if (!filteredSuggestions.length) {
    closeAutocomplete();
    return;
  }

  filteredSuggestions.forEach((suggestion, index) => {
    const option = document.createElement("button");
    option.type = "button";
    option.className = `autocomplete-option${index === activeSuggestionIndex ? " active" : ""}`;
    option.setAttribute("role", "option");
    option.setAttribute("aria-selected", index === activeSuggestionIndex ? "true" : "false");
    option.innerHTML = `
      <span class="autocomplete-label">${suggestion.label}</span>
      <span class="autocomplete-meta">${suggestion.meta}</span>
    `;
    option.addEventListener("mousedown", (event) => {
      event.preventDefault();
      applySuggestion(suggestion);
    });
    autocompletePanel.appendChild(option);
  });

  autocompletePanel.classList.add("visible");
  locationInput.setAttribute("aria-expanded", "true");
}

function updateAutocomplete() {
  clearResolvedOrigin();
  setStatus("");

  const query = locationInput.value.trim();
  if (query.length < 2) {
    if (autocompleteRequestTimer) {
      window.clearTimeout(autocompleteRequestTimer);
      autocompleteRequestTimer = null;
    }
    if (activeAutocompleteController) {
      activeAutocompleteController.abort();
      activeAutocompleteController = null;
    }
    closeAutocomplete();
    return;
  }

  if (autocompleteRequestTimer) {
    window.clearTimeout(autocompleteRequestTimer);
  }

  autocompleteRequestTimer = window.setTimeout(async () => {
    if (activeAutocompleteController) {
      activeAutocompleteController.abort();
    }

    activeAutocompleteController = new AbortController();

    try {
      const response = await fetch(`/api/location-autocomplete?q=${encodeURIComponent(query)}`, {
        signal: activeAutocompleteController.signal,
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.error || "Google Places autocomplete failed.");
      }
      filteredSuggestions = Array.isArray(payload.suggestions) ? payload.suggestions : [];
      activeSuggestionIndex = filteredSuggestions.length ? 0 : -1;
      renderAutocomplete();
    } catch (error) {
      if (error.name !== "AbortError") {
        filteredSuggestions = [];
        closeAutocomplete();
        setStatus(error.message || "Autocomplete is unavailable right now.", true);
      }
    } finally {
      activeAutocompleteController = null;
    }
  }, 180);
}

locationInput.addEventListener("input", updateAutocomplete);

locationInput.addEventListener("keydown", (event) => {
  if (!filteredSuggestions.length || !autocompletePanel.classList.contains("visible")) {
    return;
  }

  if (event.key === "ArrowDown") {
    event.preventDefault();
    activeSuggestionIndex = (activeSuggestionIndex + 1) % filteredSuggestions.length;
    renderAutocomplete();
  } else if (event.key === "ArrowUp") {
    event.preventDefault();
    activeSuggestionIndex = (activeSuggestionIndex - 1 + filteredSuggestions.length) % filteredSuggestions.length;
    renderAutocomplete();
  } else if (event.key === "Enter" && activeSuggestionIndex >= 0) {
    event.preventDefault();
    applySuggestion(filteredSuggestions[activeSuggestionIndex]);
  } else if (event.key === "Escape") {
    closeAutocomplete();
  }
});

locationInput.addEventListener("blur", () => {
  window.setTimeout(closeAutocomplete, 120);
});

document.addEventListener("click", (event) => {
  if (!autocompletePanel.contains(event.target) && event.target !== locationInput) {
    closeAutocomplete();
  }

  if (
    skillLevelHelp &&
    !skillLevelHelp.contains(event.target) &&
    event.target !== skillLevelInfoButton
  ) {
    skillLevelHelp.classList.remove("visible");
    skillLevelInfoButton.setAttribute("aria-expanded", "false");
  }
});

if (skillLevelInfoButton && skillLevelHelp) {
  skillLevelInfoButton.addEventListener("click", () => {
    const isVisible = skillLevelHelp.classList.toggle("visible");
    skillLevelInfoButton.setAttribute("aria-expanded", String(isVisible));
  });
}

metricUnitsButton.addEventListener("click", () => {
  applyUnitSystem("metric");
});

usUnitsButton.addEventListener("click", () => {
  applyUnitSystem("us");
});

function showLoadingScreen(message) {
  loadingMessage.textContent = message || "Finding nearby beaches and checking waves, wind and weather.";
  loadingScreen.classList.add("visible");
  loadingScreen.setAttribute("aria-hidden", "false");
  document.body.classList.add("loading");
  primarySubmitButton.disabled = true;
  useMyLocationButton.disabled = true;
}

function hideLoadingScreen() {
  loadingScreen.classList.remove("visible");
  loadingScreen.setAttribute("aria-hidden", "true");
  document.body.classList.remove("loading");
  primarySubmitButton.disabled = false;
  useMyLocationButton.disabled = false;
}

async function reverseGeocode(lat, lon) {
  const response = await fetch("/api/reverse-geocode", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ lat, lon })
  });

  const payload = await response.json();

  if (!response.ok) {
    throw new Error(payload.error || "Could not resolve your current location.");
  }

  return payload;
}

form.addEventListener("submit", () => {
  showLoadingScreen("Finding nearby beaches and checking waves, wind and weather.");
});

useMyLocationButton.addEventListener("click", () => {
  if (!navigator.geolocation) {
    setStatus("This browser does not support geolocation.", true);
    return;
  }

  setStatus("Getting your current location...");
  useMyLocationButton.disabled = true;

  navigator.geolocation.getCurrentPosition(async (position) => {
    try {
      const lat = position.coords.latitude;
      const lon = position.coords.longitude;
      const resolved = await reverseGeocode(lat, lon);

      originLatInput.value = String(lat);
      originLonInput.value = String(lon);
      originSourceInput.value = "browser";
      resolvedLabelInput.value = resolved.formatted_address;
      locationInput.value = resolved.formatted_address;

      setStatus("Location found. Loading beaches...");
      showLoadingScreen("Using your current location and loading the best nearby surf options.");
      form.submit();
    } catch (error) {
      setStatus(error.message, true);
      hideLoadingScreen();
      useMyLocationButton.disabled = false;
    }
  }, (error) => {
    const errorMessages = {
      1: "Location permission was denied. You can still type a location manually.",
      2: "Your location is unavailable right now. Try again or type a location.",
      3: "Location request timed out. Try again or type a location."
    };

    setStatus(errorMessages[error.code] || "Could not get your current location.", true);
    hideLoadingScreen();
    useMyLocationButton.disabled = false;
  }, {
    enableHighAccuracy: true,
    timeout: 10000,
    maximumAge: 0
  });
});

window.addEventListener("pageshow", () => {
  hideLoadingScreen();
});

applyUnitSystem(window.localStorage.getItem("surfspot-units") || "metric");
