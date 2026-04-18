// Pattern Table rendering.

export class PatternTable {
  constructor(tbodyEl, handlers) {
    this.tbody = tbodyEl;
    this.handlers = handlers;
    this.rowsById = new Map();
  }

  render(patterns, selectedId) {
    this.tbody.innerHTML = "";
    this.rowsById.clear();
    patterns.forEach((p, idx) => {
      const tr = document.createElement("tr");
      tr.dataset.id = p.id;
      if (p.id === selectedId) tr.classList.add("selected");

      const roleClass = p.role === "template" ? "role-template" : "role-match";
      tr.innerHTML = `
        <td>${idx + 1}</td>
        <td><code>${p.id.slice(0, 10)}</code></td>
        <td class="${roleClass}">${p.role}</td>
        <td>${p.shape}</td>
        <td>${Math.round(p.cx)}</td>
        <td>${Math.round(p.cy)}</td>
        <td>${Math.round(p.w)}</td>
        <td>${Math.round(p.h)}</td>
        <td>${p.angle.toFixed(1)}</td>
        <td>${p.score == null ? "-" : p.score.toFixed(3)}</td>
        <td><button class="btn danger" data-action="delete">×</button></td>
      `;

      tr.addEventListener("click", (e) => {
        if (e.target?.dataset?.action === "delete") {
          e.stopPropagation();
          this.handlers.onDelete?.(p.id);
          return;
        }
        this.handlers.onSelect?.(p.id);
      });

      this.tbody.appendChild(tr);
      this.rowsById.set(p.id, tr);
    });
  }

  highlight(id) {
    for (const [pid, tr] of this.rowsById) {
      tr.classList.toggle("selected", pid === id);
    }
  }
}
