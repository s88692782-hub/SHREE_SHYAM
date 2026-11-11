document.addEventListener("DOMContentLoaded", () => {
  const sidebar = document.getElementById("sidebar");
  const toggle = document.getElementById("menuToggle");
  if (toggle && sidebar) toggle.addEventListener("click", () => sidebar.classList.toggle("open"));

  document.querySelectorAll(".group-toggle").forEach(button => {
    const target = document.getElementById(button.dataset.target);
    if (!target) return;
    const key = "sidebar-" + button.dataset.target;
    const saved = localStorage.getItem(key);
    if (saved === "closed") target.classList.add("collapsed");
    button.addEventListener("click", () => {
      target.classList.toggle("collapsed");
      localStorage.setItem(key, target.classList.contains("collapsed") ? "closed" : "open");
    });
  });

  document.querySelectorAll(".flash-close").forEach(button => {
    button.addEventListener("click", () => button.parentElement.remove());
  });
});
