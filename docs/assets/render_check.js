// Проверка, что карта вообще открывается.
//
// Страница — такой же код, как остальной, только сломается она молча: откроешь
// файл, увидишь пустоту и решишь, что «что-то с браузером». Поэтому гоняем её
// в настоящем DOM и смотрим на то, ради чего она есть: нарисовались ли
// карточки, зажглись ли связи, работает ли переход по кнопке, собирается ли
// конфиг имён.
//
// Запуск (нужен node и один пакет):
//     npm install jsdom
//     node docs/assets/render_check.js
//
// В общий прогон `tests/run.sh` не входит намеренно: тот поднимает docker и
// ничего не требует от машины, а здесь нужен node. Проверка необязательная —
// но после правки страницы её стоит прогнать.

// jsdom ищем и рядом со скриптом, и там, откуда его запустили: ставят его
// обычно в корень проекта, а лежит проверка в docs/assets.
let jsdom;
try {
  jsdom = require("jsdom");
} catch (e) {
  try {
    jsdom = require(require("path").join(process.cwd(), "node_modules", "jsdom"));
  } catch (e2) {
    console.log("Нужен jsdom. Поставьте его и запустите снова:");
    console.log("    npm install jsdom");
    console.log("    node docs/assets/render_check.js");
    process.exit(2);
  }
}
const {JSDOM, VirtualConsole} = jsdom;
const fs = require("fs");
const path = require("path").posix.join(__dirname.split(String.fromCharCode(92)).join('/'), '') + '/';

const errors = [];
const dom = new JSDOM(fs.readFileSync(path + "frontmap.html", "utf8"), {
  runScripts: "dangerously",
  resources: undefined,
  url: "file:///" + path,
  virtualConsole: new VirtualConsole()
    .on("jsdomError", e => errors.push("jsdom: " + e.message))
    .on("error", (...a) => errors.push("error: " + a.join(" "))),
});
const w = dom.window;

// Данные грузим сами: jsdom не ходит за внешними файлами без resources-loader.
w.eval(fs.readFileSync(path + "frontmap.data.js", "utf8"));
// Скрипт страницы уже отработал (без данных показал заглушку) — запускаем заново.
const html = fs.readFileSync(path + "frontmap.html", "utf8");
const script = html.match(/<script>([\s\S]*?)<\/script>/g).pop()
  .replace(/^<script>/, "").replace(/<\/script>$/, "");
w.document.body.className = "branch";
w.document.body.innerHTML = html
  .split("<body class=\"branch\">")[1].split("<script src=")[0];
try { w.eval(script); } catch (e) { errors.push("запуск: " + e.message); }

function check(name, cond, detail) {
  console.log("  " + (cond ? "•" : "ПРОВАЛ:") + " " + name + (detail ? "  " + detail : ""));
  if (!cond) process.exitCode = 1;
}

const d = w.document;
console.log("=== ветка открывается ===");
const cards = d.querySelectorAll(".card");
check("карточки нарисованы", cards.length > 1, cards.length + " шт");
check("текущий экран помечен", !!d.querySelector(".card.cur"));
check("путь показан", (d.getElementById("trail").textContent || "").trim().length > 0);
check("связи проведены", d.querySelectorAll("#wires path").length > 0,
      d.querySelectorAll("#wires path").length + " линий");
check("исходящие связи зажжены", d.querySelectorAll("#wires path.lit").length > 0);
check("счётчик заполнен", /кнопок/.test(d.getElementById("count").textContent));

console.log();
console.log("=== переход по кнопке ===");
const link = d.querySelector(".card.cur .sub .to");
check("есть ссылка на соседний экран", !!link, link && link.textContent);
if (link) {
  const before = d.getElementById("trail").textContent;
  link.dispatchEvent(new w.MouseEvent("click", {bubbles: true}));
  check("путь пополнился", d.getElementById("trail").textContent !== before);
  check("карточки перерисовались", d.querySelectorAll(".card").length > 0);
}

console.log();
console.log("=== вся карта ===");
d.querySelector('#modes button[data-mode="map"]')
  .dispatchEvent(new w.MouseEvent("click", {bubbles: true}));
check("режим переключился", d.body.className === "map");
check("карточек много", d.querySelectorAll(".card").length > 50,
      d.querySelectorAll(".card").length + " шт");
check("колонки подписаны", d.querySelectorAll(".colhead").length > 2);

console.log();
console.log("=== клиентская сторона ===");
d.querySelector('#modes button[data-mode="branch"]')
  .dispatchEvent(new w.MouseEvent("click", {bubbles: true}));
d.querySelector('#sides button[data-side="client"]')
  .dispatchEvent(new w.MouseEvent("click", {bubbles: true}));
check("кабинет открылся", !!d.querySelector(".card.cur"));
check("это кабинет клиента",
      (d.querySelector(".card.cur .meta").textContent || "").indexOf("send_client_menu") >= 0,
      d.querySelector(".card.cur .meta").textContent);

console.log();
console.log("=== имена кнопок ===");
d.getElementById("openDiff").dispatchEvent(new w.MouseEvent("click", {bubbles: true}));
const dump = d.getElementById("dump");
check("панель открылась", d.getElementById("panel").className.indexOf("on") >= 0);
check("конфиг показан", !!dump && dump.value.indexOf("callback_data") > 0);
let cfg = null;
try { cfg = JSON.parse(dump.value); } catch (e) {}
check("это разбираемый JSON", !!cfg);

console.log();
if (errors.length) {
  console.log("ОШИБКИ СТРАНИЦЫ:");
  errors.forEach(e => console.log("  " + e));
  process.exitCode = 1;
} else {
  console.log("ошибок на странице нет");
}
console.log(process.exitCode ? "ЕСТЬ ПРОВАЛЫ" : "ВСЁ ПРОШЛО");
