"use strict";

const repository = "https://github.com/diegoanahuac/AWS_11-21";
const statusLabels = {
  verified: "Sandbox verified",
  local: "Local pass · AWS pending",
  pending: "Optional · pending",
};
const shortStatus = { verified: "Sandbox verified", local: "Local pass", pending: "Optional pending" };
const tabs = [...document.querySelectorAll("[role=tab]")];
const navigation = document.getElementById("module-navigation");
const progress = document.getElementById("progress-segments");
const picker = document.getElementById("module-picker");
const lesson = document.getElementById("module-panel");
const panel = document.getElementById("tab-content");
const pager = document.getElementById("module-pager");
let activeModuleId;

function element(tag, text = "", className = "") {
  const node = document.createElement(tag);
  if (text) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function link(text, href, className = "") {
  const node = element("a", text, className);
  node.href = href;
  return node;
}

function moduleHash(id, view = "overview") {
  return "#module-" + id + (view === "overview" ? "" : "/" + view);
}

function readRoute() {
  const match = location.hash.match(/^#module-([1-7])(?:\/(code|verification))?$/);
  return { id: match ? Number(match[1]) : 3, view: match?.[2] || "overview" };
}

function routeTo(id, view = "overview") {
  const next = moduleHash(id, view);
  if (location.hash !== next) history.pushState(null, "", next);
  render();
}

function moduleLink(text, id, className = "", focusDetails = false) {
  const node = link(text, moduleHash(id), className);
  node.addEventListener("click", (event) => {
    if (event.metaKey || event.shiftKey || event.altKey || event.ctrlKey) return;
    event.preventDefault();
    routeTo(id);
    if (focusDetails) {
      lesson.focus({ preventScroll: true });
      lesson.scrollIntoView({ block: "start" });
    }
  });
  return node;
}

function renderNavigation() {
  for (const module of workshopModules) {
    const button = moduleLink("", module.id, "module-nav");
    button.dataset.id = module.id;
    const title = element("span", "", "nav-copy");
    title.append(element("span", module.navTitle, "nav-title"), element("span", shortStatus[module.status], "nav-status"));
    button.append(element("span", String(module.id).padStart(2, "0"), "nav-number"), title);
    navigation.append(button);

    const option = element("option", String(module.id).padStart(2, "0") + "  " + module.navTitle);
    option.value = module.id;
    picker.append(option);

    const segment = moduleLink("", module.id, "segment " + module.status);
    segment.setAttribute("aria-label", "Module " + module.id + ", " + module.title + ", " + statusLabels[module.status]);
    segment.title = "Module " + module.id + " · " + shortStatus[module.status];
    progress.append(segment);
  }
}

function updateNavigation(id) {
  picker.value = String(id);
  for (const node of navigation.children) {
    if (Number(node.dataset.id) === id) node.setAttribute("aria-current", "true");
    else node.removeAttribute("aria-current");
  }
  if (activeModuleId !== id && navigation.scrollWidth > navigation.clientWidth) {
    const selected = navigation.querySelector("[aria-current]");
    const viewport = navigation.getBoundingClientRect();
    const boundary = selected.getBoundingClientRect();
    if (boundary.left < viewport.left || boundary.right > viewport.right) {
      navigation.scrollLeft += boundary.left - viewport.left - 4;
    }
  }
  activeModuleId = id;
}

function titledSection(title, text) {
  const section = element("section");
  section.append(element("h3", title, "section-title"), element("p", text, "section-copy"));
  return section;
}

function renderPractice(practice) {
  const card = element("section", "", "practice");
  const controls = element("div", "", "scenarios");
  const result = element("div", "", "practice-result");
  const resultTitle = element("strong");
  const explanation = element("p");
  result.setAttribute("aria-live", "polite");
  result.append(resultTitle, explanation);
  const buttons = practice.scenarios.map(([label], index) => {
    const button = element("button", label);
    button.type = "button";
    button.addEventListener("click", () => select(index));
    controls.append(button);
    return button;
  });
  function select(index) {
    const [, title, content, tone] = practice.scenarios[index];
    buttons.forEach((button, position) => button.setAttribute("aria-pressed", String(position === index)));
    result.dataset.tone = tone;
    resultTitle.textContent = title;
    explanation.textContent = content;
  }
  select(0);
  card.append(element("h3", practice.title, "section-title"), element("p", practice.prompt, "practice-intro"), controls, result);
  return card;
}

function renderOverview(module) {
  const grid = element("div", "", "lesson-grid");
  const summary = titledSection(module.workTitle, module.work);
  const steps = element("ol", "", "steps");
  for (const [index, [name, description]] of module.steps.entries()) {
    const step = element("li", "", "step");
    const body = element("div");
    body.append(element("strong", name, "step-name"), element("p", description));
    const number = element("span", String(index + 1), "step-number");
    number.setAttribute("aria-hidden", "true");
    step.append(number, body);
    steps.append(step);
  }
  summary.append(steps);
  grid.append(summary, renderPractice(module.practice));
  return grid;
}

function codeBlock(title, source) {
  const wrapper = element("div");
  const box = element("div", "", "code-box");
  const header = element("div", "", "code-head");
  const button = element("button", "Copy");
  const pre = element("pre");
  const code = element("code", source);
  const feedback = element("span", "", "copy-status");
  button.type = "button";
  button.setAttribute("aria-label", "Copy " + title);
  pre.tabIndex = 0;
  feedback.setAttribute("role", "status");
  header.append(element("span", title), button);
  pre.append(code);
  box.append(header, pre);
  wrapper.append(box, feedback);
  button.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(source);
      feedback.textContent = "Copied.";
    } catch {
      const range = document.createRange();
      range.selectNodeContents(code);
      const selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
      feedback.textContent = "Code selected. Press Command+C or Control+C to copy.";
    }
  });
  return wrapper;
}

function renderCode(module) {
  const grid = element("div", "", "lesson-grid");
  const left = titledSection(module.codeTitle, module.codeNote);
  left.append(codeBlock(module.codeFile, module.code));
  const right = element("section");
  right.append(element("h3", "Source and references", "section-title"));
  const links = element("ul", "", "links-list");
  const base = repository + "/blob/main/samples/" + module.directory + "/";
  for (const [label, path] of module.resources) {
    const row = element("li");
    row.append(link(label, path.startsWith("https://") ? path : base + path));
    links.append(row);
  }
  const directoryLink = element("li");
  directoryLink.append(link("Browse the module folder", repository + "/tree/main/samples/" + module.directory));
  links.append(directoryLink);
  right.append(links);
  grid.append(left, right);
  return grid;
}

function renderVerification(module) {
  const grid = element("div", "", "lesson-grid");
  const observed = element("section");
  observed.append(element("h3", "Results", "section-title"));
  const evidence = element("ul", "", "evidence");
  for (const [title, description] of module.evidence) {
    const item = element("li");
    item.append(element("strong", title), element("p", description));
    evidence.append(item);
  }
  observed.append(evidence);
  const next = element("section");
  if (module.command) {
    const header = module.id === 2 ? "Explore the sample" : "Reproduce the check";
    const note = module.id === 2
      ? "The starter chat uses its default cap. The five-attempt sandbox check set max_calls=2."
      : "From the repository root, use the workshop Python environment. Live chat uses your AWS credentials.";
    next.append(element("h3", header, "section-title"), element("p", note, "section-copy"), codeBlock("Terminal", module.command));
  } else {
    const resource = repository + "/tree/main/samples/" + module.directory;
    next.append(element("h3", "Optional starter", "section-title"));
    const list = element("ul", "", "links-list");
    const row = element("li");
    row.append(link("Open the module notebook and guide", resource));
    list.append(row);
    next.append(list);
  }
  grid.append(observed, next);
  return grid;
}

function renderPager(id) {
  const links = [];
  if (id > 1) links.push(moduleLink("Previous module", id - 1, "", true));
  if (id < workshopModules.length) links.push(moduleLink("Next module", id + 1, "", true));
  pager.replaceChildren(...links);
}

function render() {
  const { id, view } = readRoute();
  const module = workshopModules[id - 1];
  updateNavigation(id);
  document.getElementById("module-kicker").textContent = "MODULE " + String(id).padStart(2, "0") + " · " + module.section.toUpperCase();
  document.getElementById("module-title").textContent = module.title;
  document.getElementById("module-summary").textContent = module.summary;
  const status = document.getElementById("module-status");
  status.className = "tag " + module.status;
  status.textContent = statusLabels[module.status];
  for (const tab of tabs) {
    const selected = tab.dataset.view === view;
    tab.setAttribute("aria-selected", String(selected));
    tab.tabIndex = selected ? 0 : -1;
  }
  panel.setAttribute("aria-labelledby", "tab-" + view);
  const content = view === "code" ? renderCode(module)
    : view === "verification" ? renderVerification(module)
    : renderOverview(module);
  panel.replaceChildren(content);
  renderPager(id);
}

for (const [index, tab] of tabs.entries()) {
  tab.addEventListener("click", () => routeTo(readRoute().id, tab.dataset.view));
  tab.addEventListener("keydown", (event) => {
    const destination = {
      ArrowLeft: (index + tabs.length - 1) % tabs.length,
      ArrowRight: (index + 1) % tabs.length,
      Home: 0,
      End: tabs.length - 1,
    }[event.key];
    if (destination === undefined) return;
    event.preventDefault();
    const selected = tabs[destination];
    routeTo(readRoute().id, selected.dataset.view);
    selected.focus();
  });
}

picker.addEventListener("change", () => routeTo(Number(picker.value)));
window.addEventListener("popstate", render);
window.addEventListener("hashchange", () => {
  if (location.hash !== "#module-panel") render();
});
renderNavigation();
render();
