const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { test } = require("node:test");
const ts = require("typescript");

// Exercise the shared browser client without installing a browser or new packages.
const source = fs.readFileSync(path.join(__dirname, "../src/app/api.ts"), "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText;
const loaded = { exports: {} };
new Function("exports", "module", compiled)(loaded.exports, loaded);
const { api, ApiFailure } = loaded.exports;

test("interrupted sign-in keeps credentials private and gives fresh-code guidance", async (t) => {
  let attempts = 0;
  t.mock.method(globalThis, "fetch", async (_url, init) => {
    attempts++;
    assert.equal(init.credentials, "same-origin");
    assert.equal(init.cache, "no-store");
    throw new TypeError("Failed to fetch");
  });
  await assert.rejects(api("/auth/login", {
    method: "POST", body: JSON.stringify({ password: "private-test-input", otp: "123456" }),
  }), (error) => {
    assert.ok(error instanceof ApiFailure);
    assert.equal(error.code, "NETWORK_UNAVAILABLE");
    assert.match(error.message, /fresh authenticator code/);
    assert.doesNotMatch(error.message, /draft|operation key|private-test-input|123456/i);
    return true;
  });
  assert.equal(attempts, 1, "never automatically replay an MFA submission");
});

test("sign-in deadline aborts a stalled connection and releases its timer", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  let signal;
  t.mock.method(globalThis, "fetch", (_url, init) => new Promise((_resolve, reject) => {
    signal = init.signal;
    signal.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")));
  }));
  const result = assert.rejects(api("/auth/login", { method: "POST" }), (error) => {
    assert.equal(error.code, "REQUEST_TIMEOUT");
    assert.match(error.message, /25 seconds/);
    return true;
  });
  t.mock.timers.tick(25_000);
  await result;
  assert.equal(signal.aborted, true);
});

test("deadline also covers a stalled sign-in response body", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  let signal;
  t.mock.method(globalThis, "fetch", async (_url, init) => {
    signal = init.signal;
    return { status: 200, ok: true, json: () => new Promise((_resolve, reject) => {
      signal.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")));
    }) };
  });
  const result = assert.rejects(api("/auth/login", { method: "POST" }), (error) => {
    assert.equal(error.code, "REQUEST_TIMEOUT");
    return true;
  });
  await Promise.resolve();
  t.mock.timers.tick(25_000);
  await result;
});

test("signed-out 401 stays an authentication response rather than a network error", async (t) => {
  t.mock.method(globalThis, "fetch", async () => new Response(JSON.stringify({
    error: { code: "AUTH_REQUIRED", message: "The sign-in details could not be verified" },
  }), { status: 401 }));
  await assert.rejects(api("/auth/login", { method: "POST" }), (error) => {
    assert.equal(error.status, 401);
    assert.equal(error.code, "AUTH_REQUIRED");
    assert.equal(error.message, "The sign-in details could not be verified");
    return true;
  });
});

test("successful sign-in clears the abort timer and retains the response", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  let signal;
  t.mock.method(globalThis, "fetch", async (_url, init) => {
    signal = init.signal;
    return new Response(JSON.stringify({ status: "AUTHENTICATED" }));
  });
  assert.deepEqual(await api("/auth/login", { method: "POST" }), { status: "AUTHENTICATED" });
  t.mock.timers.tick(25_000);
  assert.equal(signal.aborted, false);
});

test("failed session check gives session guidance without operation-key instructions", async (t) => {
  t.mock.method(globalThis, "fetch", async () => { throw new TypeError("Failed to fetch"); });
  await assert.rejects(api("/auth/me"), (error) => {
    assert.match(error.message, /session could not be checked/i);
    assert.doesNotMatch(error.message, /draft|operation key/i);
    return true;
  });
});

test("an unreadable sign-in response does not confirm authentication", async (t) => {
  t.mock.method(globalThis, "fetch", async () => new Response("<html>Gateway unavailable</html>", { status: 504 }));
  await assert.rejects(api("/auth/login", { method: "POST" }), (error) => {
    assert.equal(error.status, 504);
    assert.equal(error.code, "INVALID_RESPONSE");
    assert.match(error.message, /sign-in service/i);
    assert.doesNotMatch(error.message, /draft|operation key/i);
    return true;
  });
});

test("caller cancellation remains attached to the sign-in request", async (t) => {
  const controller = new AbortController();
  t.mock.method(globalThis, "fetch", (_url, init) => new Promise((_resolve, reject) => {
    init.signal.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")));
  }));
  const result = assert.rejects(api("/auth/login", { method: "POST", signal: controller.signal }), (error) => {
    assert.equal(error.code, "NETWORK_UNAVAILABLE");
    return true;
  });
  controller.abort();
  await result;
});
