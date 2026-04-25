param(
    [string]$AppUrl = "http://127.0.0.1:5000",
    [string]$ChromePath = "C:\Tools\ChromeForTesting\chrome-win64\chrome.exe",
    [int]$DebugPort = 9222
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Runtime = Join-Path $Root ".runtime"
$ChromeProfile = Join-Path $Runtime "chrome-for-testing-profile"
New-Item -ItemType Directory -Force $Runtime, $ChromeProfile | Out-Null

function Test-PortOpen {
    param([int]$Port)
    return (Test-NetConnection -ComputerName "127.0.0.1" -Port $Port -WarningAction SilentlyContinue).TcpTestSucceeded
}

if (-not (Test-Path $ChromePath)) {
    throw "Chrome for Testing not found at $ChromePath"
}

if (-not (Test-PortOpen -Port $DebugPort)) {
    Start-Process -FilePath $ChromePath -ArgumentList @(
        "--remote-debugging-port=$DebugPort",
        "--user-data-dir=$ChromeProfile",
        "--no-first-run",
        "--no-default-browser-check",
        $AppUrl
    ) -WindowStyle Hidden | Out-Null
    Start-Sleep -Seconds 2
}

$env:SEMANTIC_ROUTER_HARNESS_APP_URL = $AppUrl
$env:PYTHONIOENCODING = "utf-8"

@'
import json
import os
import time

app_url = os.environ["SEMANTIC_ROUTER_HARNESS_APP_URL"].rstrip("/")


def wait_until(predicate, timeout=20, interval=0.25):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        last = predicate()
        if last:
            return last
        time.sleep(interval)
    raise AssertionError(f"condition was not met, last={last!r}")


def login(username, password):
    reuse_or_new_tab(f"{app_url}/login")
    wait_for_load()
    username_json = json.dumps(username)
    password_json = json.dumps(password)
    js(
        f"""
        (() => {{
            document.querySelector("#username").value = {username_json};
            document.querySelector("#password").value = {password_json};
            document.querySelector("form").requestSubmit();
        }})()
        """
    )
    wait_until(lambda: "/dashboard" in page_info().get("url", ""), timeout=20)


def submit_query(query):
    reuse_or_new_tab(f"{app_url}/dashboard")
    wait_for_load()
    escaped = query.encode("unicode_escape").decode("ascii")
    js(
        f"""
        () => {{
            const input = document.querySelector("[data-semantic-router-input]");
            const form = document.querySelector("[data-semantic-router-form]");
            input.value = JSON.parse('"{escaped}"');
            input.dispatchEvent(new Event("input", {{ bubbles: true }}));
            form.dispatchEvent(new Event("submit", {{ bubbles: true, cancelable: true }}));
        }}
        """
    )
    wait_for_load()
    wait_until(lambda: page_info().get("url", "") != f"{app_url}/dashboard", timeout=40)
    return page_info().get("url", "")


checks = []
login("student", "123")
checks.append(("student courses", submit_query("покажи мои курсы"), "/courses"))
checks.append(("student upload", submit_query("куда прикрепить pdf с домашкой"), "/input_file/test"))

reuse_or_new_tab(f"{app_url}/logout")
wait_for_load()
login("admin", "admin")
checks.append(("admin builder", submit_query("создать курс и настроить структуру"), "/admin/course-builder"))

failures = []
for name, url, expected_path in checks:
    if expected_path not in url:
        failures.append({"name": name, "url": url, "expected_path": expected_path})

print(json.dumps({"status": "ok" if not failures else "failed", "checks": checks, "failures": failures}, ensure_ascii=False, indent=2))
if failures:
    raise SystemExit(1)
'@ | browser-harness
