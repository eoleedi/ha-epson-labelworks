const CARD_NAME = "epson-labelworks-card";

class EpsonLabelWorksCard extends HTMLElement {
  static getConfigForm() {
    return {
      schema: [
        {
          name: "device",
          required: true,
          selector: { device: { integration: "epson_labelworks" } },
        },
        { name: "name", selector: { text: {} } },
        {
          type: "expandable",
          name: "entities",
          title: "Setting entities",
          flatten: true,
          schema: [
            { name: "tape_width_entity", selector: { entity: { domain: "number" } } },
            { name: "font_size_entity", selector: { entity: { domain: "number" } } },
            { name: "density_entity", selector: { entity: { domain: "number" } } },
            { name: "margin_entity", selector: { entity: { domain: "number" } } },
            { name: "cut_mode_entity", selector: { entity: { domain: "select" } } },
          ],
        },
      ],
      computeLabel: (schema) => ({
        device: "Label printer",
        name: "Card title",
        tape_width_entity: "Tape width",
        font_size_entity: "Font size",
        density_entity: "Print density",
        margin_entity: "Margin",
        cut_mode_entity: "Cut mode",
      })[schema.name],
    };
  }

  static getStubConfig(hass) {
    return {};
  }

  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._draft = "";
    this._printing = false;
    this._discoveryKey = undefined;
    this._discoveryPromise = undefined;
  }

  setConfig(config) {
    if (!config.device && !config.entity) {
      throw new Error("Select an Epson LabelWorks printer");
    }
    this._config = { ...config };
    this._entities = this._explicitEntityIds(config);
    this._discoveryKey = undefined;
    this._renderShell();
    this._discoverDeviceEntities();
    this._update();
  }

  set hass(hass) {
    this._hass = hass;
    if (this._config) {
      this._discoverDeviceEntities();
      this._update();
    }
  }

  getCardSize() {
    return 6;
  }

  getGridOptions() {
    return { rows: 6, columns: "full", min_rows: 5, min_columns: 6 };
  }

  _explicitEntityIds(config) {
    return {
      print: config.entity,
      tapeWidth: config.tape_width_entity,
      fontSize: config.font_size_entity,
      density: config.density_entity,
      margin: config.margin_entity,
      cutMode: config.cut_mode_entity,
    };
  }

  async _discoverDeviceEntities() {
    if (!this._hass || !this._config || this._discoveryPromise) return;
    const key = this._config.device || this._config.entity;
    if (!key || this._discoveryKey === key) return;

    this._discoveryPromise = this._resolveDeviceEntities(key);
    try {
      const discovered = await this._discoveryPromise;
      if ((this._config.device || this._config.entity) !== key) return;
      const explicit = this._explicitEntityIds(this._config);
      this._entities = Object.fromEntries(
        Object.keys(discovered).map((role) => [role, explicit[role] || discovered[role]]),
      );
      this._discoveryKey = key;
      this._update();
    } catch (error) {
      this._showError(error?.message || "Could not discover printer entities");
    } finally {
      this._discoveryPromise = undefined;
    }
  }

  async _resolveDeviceEntities(key) {
    const registry = await this._hass.callWS({ type: "config/entity_registry/list" });
    const selected = this._config.device
      ? registry.filter((entry) => entry.device_id === this._config.device)
      : registry.filter((entry) => entry.entity_id === this._config.entity);
    const deviceId = this._config.device || selected[0]?.device_id;
    if (!deviceId) throw new Error("The selected printer has no Home Assistant device");

    const entries = registry.filter(
      (entry) => entry.device_id === deviceId && entry.platform === "epson_labelworks",
    );
    const role = (suffix) => entries.find((entry) => entry.unique_id?.endsWith(suffix))?.entity_id;
    const entities = {
      print: role("-print"),
      tapeWidth: role("-tape_width_mm"),
      fontSize: role("-font_size"),
      density: role("-density"),
      margin: role("-margin_mm"),
      cutMode: role("-cut_mode"),
    };
    if (!entities.print) throw new Error("No print entity was found for this printer");
    return entities;
  }

  _renderShell() {
    if (!this.shadowRoot) return;
    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          --label-ink: var(--primary-text-color, #182026);
          --label-muted: var(--secondary-text-color, #667079);
          --label-accent: var(--primary-color, #0b7fab);
          --label-paper: #f7f3df;
          --label-edge: #d8d1ad;
        }
        * { box-sizing: border-box; }
        ha-card {
          overflow: hidden;
          color: var(--label-ink);
          background: var(--ha-card-background, var(--card-background-color, #fff));
        }
        .head {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          padding: 18px 20px 14px;
        }
        .identity { min-width: 0; }
        .eyebrow {
          color: var(--label-accent);
          font: 700 10px/1.2 var(--ha-font-family, sans-serif);
          letter-spacing: 0.16em;
          text-transform: uppercase;
        }
        h2 {
          margin: 4px 0 0;
          overflow: hidden;
          font: 600 20px/1.2 var(--ha-font-family, sans-serif);
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .status {
          display: flex;
          align-items: center;
          flex: 0 0 auto;
          gap: 7px;
          color: var(--label-muted);
          font-size: 12px;
        }
        .status-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: #9aa2a8;
        }
        .status[data-ready="true"] .status-dot {
          background: #29a36a;
          box-shadow: 0 0 0 4px color-mix(in srgb, #29a36a 16%, transparent);
        }
        .compose {
          padding: 0 20px 18px;
        }
        .tape-stage {
          position: relative;
          display: flex;
          min-height: 92px;
          align-items: center;
          padding: 14px 0;
          overflow: hidden;
          border-radius: 10px;
          background:
            linear-gradient(90deg, color-mix(in srgb, var(--label-accent) 9%, transparent), transparent 28%),
            var(--secondary-background-color, #eef1f3);
        }
        .tape-stage::before,
        .tape-stage::after {
          position: absolute;
          z-index: 2;
          width: 18px;
          height: 100%;
          content: "";
          background: repeating-linear-gradient(135deg, transparent 0 5px, color-mix(in srgb, var(--label-ink) 10%, transparent) 5px 6px);
        }
        .tape-stage::before { left: 0; }
        .tape-stage::after { right: 0; transform: scaleX(-1); }
        .tape {
          display: flex;
          width: calc(100% - 28px);
          min-height: 58px;
          align-items: center;
          justify-content: center;
          margin: auto;
          padding: 8px 20px;
          border: 1px solid var(--label-edge);
          background: var(--label-paper);
          box-shadow: 0 3px 8px rgb(20 28 33 / 14%);
          color: #161816;
          font-family: "Arial Narrow", "Roboto Condensed", sans-serif;
          font-size: clamp(18px, 7vw, 34px);
          font-weight: 600;
          line-height: 1;
          text-align: center;
          white-space: pre-wrap;
          word-break: break-word;
        }
        .tape.empty { color: #918e7b; font-weight: 400; }
        .input-row {
          display: grid;
          grid-template-columns: 1fr auto;
          gap: 10px;
          margin-top: 12px;
        }
        textarea {
          width: 100%;
          min-height: 58px;
          resize: vertical;
          border: 1px solid var(--divider-color, #d9dde0);
          border-radius: 9px;
          outline: none;
          padding: 10px 12px;
          background: var(--input-fill-color, transparent);
          color: var(--primary-text-color);
          font: 400 15px/1.4 var(--ha-font-family, sans-serif);
        }
        textarea:focus {
          border-color: var(--label-accent);
          box-shadow: 0 0 0 2px color-mix(in srgb, var(--label-accent) 20%, transparent);
        }
        .print {
          min-width: 86px;
          border: 0;
          border-radius: 9px;
          padding: 0 16px;
          background: var(--label-accent);
          color: var(--text-primary-color, #fff);
          cursor: pointer;
          font: 700 13px/1 var(--ha-font-family, sans-serif);
          letter-spacing: 0.02em;
        }
        .print:hover { filter: brightness(1.06); }
        .print:disabled { cursor: default; filter: grayscale(0.6); opacity: 0.55; }
        .settings {
          display: grid;
          grid-template-columns: repeat(5, minmax(0, 1fr));
          border-top: 1px solid var(--divider-color, #e2e5e7);
        }
        .setting {
          min-width: 0;
          padding: 13px 12px 15px;
          border-right: 1px solid var(--divider-color, #e2e5e7);
        }
        .setting:last-child { border-right: 0; }
        label {
          display: block;
          overflow: hidden;
          margin-bottom: 7px;
          color: var(--label-muted);
          font: 600 10px/1.2 var(--ha-font-family, sans-serif);
          letter-spacing: 0.05em;
          text-overflow: ellipsis;
          text-transform: uppercase;
          white-space: nowrap;
        }
        input[type="number"], select {
          width: 100%;
          height: 34px;
          border: 1px solid var(--divider-color, #d9dde0);
          border-radius: 7px;
          outline: none;
          padding: 0 7px;
          background: var(--card-background-color, #fff);
          color: var(--primary-text-color);
          font: 600 13px/1 var(--ha-font-family, sans-serif);
        }
        input:focus, select:focus { border-color: var(--label-accent); }
        .missing { opacity: 0.45; }
        .error {
          display: none;
          margin: 0 20px 16px;
          border-radius: 7px;
          padding: 9px 11px;
          background: color-mix(in srgb, var(--error-color, #db4437) 12%, transparent);
          color: var(--error-color, #b3261e);
          font-size: 12px;
        }
        .error.visible { display: block; }
        @media (max-width: 520px) {
          .settings { grid-template-columns: repeat(2, 1fr); }
          .setting { border-bottom: 1px solid var(--divider-color, #e2e5e7); }
          .setting:nth-child(2n) { border-right: 0; }
          .setting:last-child { grid-column: 1 / -1; border-bottom: 0; }
          .input-row { grid-template-columns: 1fr; }
          .print { min-height: 44px; }
        }
        @media (prefers-reduced-motion: no-preference) {
          .print { transition: filter 120ms ease, transform 120ms ease; }
          .print:active:not(:disabled) { transform: translateY(1px); }
        }
      </style>
      <ha-card>
        <header class="head">
          <div class="identity">
            <div class="eyebrow">LabelWorks</div>
            <h2></h2>
          </div>
          <div class="status"><span class="status-dot"></span><span class="status-text">Unavailable</span></div>
        </header>
        <main class="compose">
          <div class="tape-stage"><div class="tape empty">Label preview</div></div>
          <div class="input-row">
            <textarea maxlength="255" aria-label="Label text" placeholder="Type a label..."></textarea>
            <button class="print" type="button">Print</button>
          </div>
        </main>
        <div class="error" role="alert"></div>
        <section class="settings">
          ${this._numberControl("tapeWidth", "Tape", "mm")}
          ${this._numberControl("fontSize", "Font", "pt")}
          ${this._numberControl("density", "Density", "")}
          ${this._numberControl("margin", "Margin", "mm")}
          <div class="setting" data-control="cutMode">
            <label for="cutMode">Cut</label>
            <select id="cutMode" aria-label="Cut mode">
              <option value="each">Each label</option>
              <option value="after">After job</option>
              <option value="none">Do not cut</option>
            </select>
          </div>
        </section>
      </ha-card>
    `;

    this.shadowRoot.querySelector("textarea").addEventListener("input", (event) => {
      this._draft = event.target.value;
      this._updatePreview();
      this._updatePrintButton();
    });
    this.shadowRoot.querySelector("textarea").addEventListener("keydown", (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key === "Enter") this._print();
    });
    this.shadowRoot.querySelector(".print").addEventListener("click", () => this._print());
    for (const key of ["tapeWidth", "fontSize", "density", "margin"]) {
      this.shadowRoot.querySelector(`#${key}`).addEventListener("change", (event) =>
        this._setNumber(key, Number(event.target.value)),
      );
    }
    this.shadowRoot.querySelector("#cutMode").addEventListener("change", (event) =>
      this._setSelect(event.target.value),
    );
  }

  _numberControl(key, label, unit) {
    return `<div class="setting" data-control="${key}">
      <label for="${key}">${label}${unit ? ` / ${unit}` : ""}</label>
      <input id="${key}" type="number" aria-label="${label}" />
    </div>`;
  }

  _update() {
    if (!this.shadowRoot || !this._hass) return;
    const printState = this._hass.states[this._entities.print];
    const title = this._config.name || printState?.attributes?.friendly_name || "Epson LabelWorks";
    this.shadowRoot.querySelector("h2").textContent = title.replace(/ Print label$/, "");

    const status = printState?.attributes?.printer_status;
    const error = printState?.attributes?.printer_error;
    const available = Boolean(printState) && printState.state !== "unavailable";
    const ready = available && (!error || error === "no_error");
    const statusNode = this.shadowRoot.querySelector(".status");
    statusNode.dataset.ready = String(ready);
    this.shadowRoot.querySelector(".status-text").textContent = error && error !== "no_error"
      ? error.replaceAll("_", " ")
      : status || (available ? "Ready" : "Unavailable");

    this._syncNumber("tapeWidth");
    this._syncNumber("fontSize");
    this._syncNumber("density");
    this._syncNumber("margin");
    this._syncSelect();
    this._updatePrintButton();
  }

  _syncNumber(key) {
    const entity = this._hass.states[this._entities[key]];
    const input = this.shadowRoot.querySelector(`#${key}`);
    const wrapper = this.shadowRoot.querySelector(`[data-control="${key}"]`);
    wrapper.classList.toggle("missing", !entity);
    input.disabled = !entity;
    if (!entity || this.shadowRoot.activeElement === input) return;
    input.value = entity.state;
    input.min = entity.attributes.min ?? "";
    input.max = entity.attributes.max ?? "";
    input.step = entity.attributes.step ?? 1;
  }

  _syncSelect() {
    const entity = this._hass.states[this._entities.cutMode];
    const select = this.shadowRoot.querySelector("#cutMode");
    this.shadowRoot.querySelector('[data-control="cutMode"]').classList.toggle("missing", !entity);
    select.disabled = !entity;
    if (entity) select.value = entity.state;
  }

  _updatePreview() {
    const preview = this.shadowRoot.querySelector(".tape");
    preview.textContent = this._draft || "Label preview";
    preview.classList.toggle("empty", !this._draft);
  }

  _updatePrintButton() {
    const button = this.shadowRoot?.querySelector(".print");
    if (!button) return;
    const printState = this._hass?.states?.[this._entities.print];
    const available = Boolean(printState) && printState.state !== "unavailable";
    button.disabled = !available || !this._draft.trim() || this._printing;
    button.textContent = this._printing ? "Printing..." : "Print";
  }

  async _setNumber(key, value) {
    if (!Number.isFinite(value)) return;
    await this._callService("number", "set_value", {
      entity_id: this._entities[key],
      value,
    });
  }

  async _setSelect(option) {
    await this._callService("select", "select_option", {
      entity_id: this._entities.cutMode,
      option,
    });
  }

  async _print() {
    if (!this._draft.trim() || this._printing) return;
    this._printing = true;
    this._showError("");
    this._updatePrintButton();
    try {
      const printed = await this._callService("text", "set_value", {
        entity_id: this._entities.print,
        value: this._draft,
      });
      if (printed) {
        this._draft = "";
        this.shadowRoot.querySelector("textarea").value = "";
        this._updatePreview();
      }
    } finally {
      this._printing = false;
      this._updatePrintButton();
    }
  }

  async _callService(domain, service, data) {
    try {
      await this._hass.callService(domain, service, data);
      return true;
    } catch (error) {
      this._showError(error?.message || "Home Assistant could not complete the action");
      return false;
    }
  }

  _showError(message) {
    const node = this.shadowRoot.querySelector(".error");
    node.textContent = message;
    node.classList.toggle("visible", Boolean(message));
  }
}

if (!customElements.get(CARD_NAME)) {
  customElements.define(CARD_NAME, EpsonLabelWorksCard);
}

window.customCards = window.customCards || [];
window.customCards.push({
  type: CARD_NAME,
  name: "Epson LabelWorks",
  description: "Compose and print labels with a live tape preview and print settings.",
  preview: true,
  documentationURL: "https://github.com/eoleedi/ha-epson-labelworks",
  getEntitySuggestion: (_hass, entityId) =>
    entityId.startsWith("text.") && entityId.endsWith("_print_label")
      ? { config: { type: `custom:${CARD_NAME}`, entity: entityId } }
      : null,
});

console.info("%c EPSON LABELWORKS CARD ", "background:#0b7fab;color:white;font-weight:bold");
