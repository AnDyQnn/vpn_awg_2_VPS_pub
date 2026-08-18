#!/usr/bin/env python3
"""Монитор GitHub Actions для Gateway Hub — без gh CLI, только токен + API.

Использование:
    GH_TOKEN=<token> python scripts/ci_watch.py            # статус последнего прогона
    GH_TOKEN=<token> python scripts/ci_watch.py --logs      # + хвост лога упавших джоб
    GH_TOKEN=<token> python scripts/ci_watch.py --watch     # опрос каждые 30с до завершения
    GH_TOKEN=<token> python scripts/ci_watch.py --download gatewayhub-windows  # скачать артефакт

Токен: fine-grained PAT на репо AnDyQnn/Custom_AmnesiaWG с правами
       Actions: Read, Contents: Read (этого хватает для статусов, логов, артефактов).
"""
import json, os, sys, time, urllib.request, urllib.error, zipfile, io
from urllib.parse import urlparse

REPO = os.environ.get("REPO", "AnDyQnn/Custom_AmnesiaWG")
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
API = "https://api.github.com"


class _NoAuthRedirect(urllib.request.HTTPRedirectHandler):
    """GitHub logs/artifacts 302-редиректят на Azure blob. urllib по умолчанию
    тащит туда же заголовок Authorization → Azure отвечает 401. Срезаем его при
    смене хоста."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is not None and urlparse(newurl).netloc != urlparse(req.full_url).netloc:
            new.headers = {k: v for k, v in new.headers.items() if k.lower() != "authorization"}
        return new


_opener = urllib.request.build_opener(_NoAuthRedirect)


def _req(path, raw=False):
    url = path if path.startswith("http") else API + path
    req = urllib.request.Request(url)
    req.add_header("Authorization", "Bearer " + (TOKEN or ""))
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    with _opener.open(req) as r:
        data = r.read()
    return data if raw else json.loads(data)


def latest_run():
    runs = _req(f"/repos/{REPO}/actions/runs?per_page=1")["workflow_runs"]
    return runs[0] if runs else None


def show(run, want_logs=False):
    print(f"Run #{run['run_number']}  '{run['display_title']}'")
    print(f"  status={run['status']}  conclusion={run['conclusion']}  {run['html_url']}")
    jobs = _req(f"/repos/{REPO}/actions/runs/{run['id']}/jobs")["jobs"]
    for j in jobs:
        mark = {"success": "OK", "failure": "FAIL", "cancelled": "CANC", None: ".."}.get(j["conclusion"], j["conclusion"])
        print(f"   [{mark:>4}] {j['name']:<10} {j['status']}")
        if want_logs and j["conclusion"] == "failure":
            try:
                log = _req(f"/repos/{REPO}/actions/jobs/{j['id']}/logs", raw=True).decode("utf-8", "replace")
                tail = "\n".join(log.splitlines()[-120:])
                print(f"   ----- last 120 log lines of '{j['name']}' -----\n{tail}\n   -----------------------------")
            except Exception as e:
                print(f"   (не удалось получить лог: {e})")
    arts = _req(f"/repos/{REPO}/actions/runs/{run['id']}/artifacts")["artifacts"]
    if arts:
        print("  artifacts:", ", ".join(f"{a['name']}({a['size_in_bytes']//1024}KB)" for a in arts))
    return jobs, arts


def download(run, name):
    arts = _req(f"/repos/{REPO}/actions/runs/{run['id']}/artifacts")["artifacts"]
    a = next((x for x in arts if x["name"] == name), None)
    if not a:
        print(f"артефакт '{name}' не найден"); return
    blob = _req(a["archive_download_url"], raw=True)
    out = f"_artifacts/{name}"
    os.makedirs(out, exist_ok=True)
    zipfile.ZipFile(io.BytesIO(blob)).extractall(out)
    print(f"распаковано в {out}/")


def main():
    if not TOKEN:
        sys.exit("нет GH_TOKEN в окружении")
    run = latest_run()
    if not run:
        sys.exit("прогонов не найдено")
    args = sys.argv[1:]
    if "--download" in args:
        download(run, args[args.index("--download") + 1]); return
    if "--watch" in args:
        while True:
            run = latest_run()
            show(run, want_logs="--logs" in args)
            if run["status"] == "completed":
                break
            print("... ещё идёт, жду 30с\n"); time.sleep(30)
        return
    show(run, want_logs="--logs" in args)


if __name__ == "__main__":
    main()
