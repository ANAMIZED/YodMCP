(function () {
  "use strict";
  var W = window.ANAMIZEDWebMCP;
  var logEl = document.getElementById("webmcp-log");
  var statusEl = document.getElementById("webmcp-status");
  function authHeaders() {
    var key = (document.getElementById("api-key") || {}).value;
    return key ? { "X-API-Key": key } : {};
  }
  var tools = [
    { name: "health", description: "YodMCP API health. Public. Read-only.", inputSchema: { type: "object", properties: {} }, annotations: { readOnlyHint: true },
      execute: async function () { return W.rest("/health"); } },
    { name: "ready", description: "Substrate readiness. Public. Read-only.", inputSchema: { type: "object", properties: {} }, annotations: { readOnlyHint: true },
      execute: async function () { return W.rest("/ready"); } },
    { name: "discovery", description: "Machine surfaces for this origin.", inputSchema: { type: "object", properties: {} }, annotations: { readOnlyHint: true },
      execute: async function () {
        return { mcp: "/mcp or stdio yodmcp", api: "/api/*", health: "/health", ready: "/ready", dashboard: "/dashboard", docs: "/docs", registry: "io.github.ANAMIZED/yodmcp" };
      } },
    { name: "list_skills", description: "List loaded skills. Uses X-API-Key from the page if set.", inputSchema: { type: "object", properties: {} }, annotations: { readOnlyHint: true },
      execute: async function () { return W.rest("/api/skills", authHeaders()); } },
    { name: "audit_recent", description: "Recent audit events. Uses X-API-Key from the page if set.", inputSchema: { type: "object", properties: { limit: { type: "number" } } }, annotations: { readOnlyHint: true },
      execute: async function (p) { return W.rest("/api/audit?limit=" + ((p && p.limit) || 20), authHeaders()); } }
  ];
  async function boot() {
    statusEl.textContent = W.supported() ? "WebMCP available — YodMCP tools registered" : "WebMCP API not in this browser.";
    W.log(logEl, JSON.stringify(await W.registerAll(tools)));
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot); else boot();
})();
